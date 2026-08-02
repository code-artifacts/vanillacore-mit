package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;

import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarness.LockMode;
import org.vanilladb.core.storage.tx.concurrency.schedule.ScheduleControl;
import org.vanilladb.core.storage.tx.concurrency.schedule.ScheduleEvent;
import org.vanilladb.core.storage.tx.concurrency.schedule.StrictScheduleController;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceSnapshot;

public class Week04ScheduleReplayTest {
	private static final String SCENARIO = System.getProperty(
			"vanillacore.mit.schedule", "shared-shared-compatible");
	private static final String MODE = System.getProperty(
			"vanillacore.mit.traceMode", "high");
	private static final long SEED = Long.getLong("vanillacore.mit.seed", 20260802L);
	private static final Path OUTPUT = Paths.get(System.getProperty(
			"vanillacore.mit.result", "target/week04-replay.json"));
	private static final long FIRST = 11101;
	private static final long SECOND = 11102;

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(Week04ScheduleReplayTest.class);
	}

	@Test
	public void replaySelectedSchedule() throws Exception {
		if (!MODE.equals("high") && !MODE.equals("low"))
			throw new IllegalArgumentException("unsupported trace mode " + MODE);
		String resource = "week04-" + SCENARIO;
		List<ScheduleEvent> expected = expected(resource);
		Set<String> ignored = SCENARIO.startsWith("writer-")
				? Collections.singleton("locktable.releaseAll.txEnd")
				: Collections.emptySet();
		StrictScheduleController controller = new StrictScheduleController(
				expected, ignored, 5, TimeUnit.SECONDS);
		DirectLockTableHarness harness = null;
		Throwable failure = null;
		List<ScheduleEvent> linearization = Collections.emptyList();
		LockTraceSnapshot snapshot = null;
		LockTableTestProbe.ResidueSnapshot residue = null;
		List<String> liveWorkers = Collections.emptyList();
		try {
			ScheduleControl.install(controller);
			harness = new DirectLockTableHarness(
					"week04-" + MODE + "-" + SCENARIO, 128, 2,
					MODE.equals("low"));
			replay(harness, controller, resource);
			controller.assertComplete();
			linearization = controller.actualLinearization();
		} catch (Throwable throwable) {
			failure = throwable;
		} finally {
			linearization = controller.actualLinearization();
			ScheduleControl.reset();
			if (harness != null) {
				try {
					harness.close();
				} catch (Throwable closeFailure) {
					if (failure == null)
						failure = closeFailure;
				}
				snapshot = harness.snapshot();
				residue = harness.residueSnapshot();
				liveWorkers = harness.liveWorkerNames();
			}
		}
		writeResult(expected, linearization, snapshot, residue, liveWorkers,
				failure);
		if (failure != null)
			rethrow(failure);
		assertEquals(expected, linearization);
		assertEquals(0, snapshot.droppedEvents());
		assertClean(residue, liveWorkers);
	}

	private void replay(DirectLockTableHarness harness,
			StrictScheduleController controller, String resource) throws Exception {
		switch (SCENARIO) {
		case "shared-shared-compatible":
			harness.lock(FIRST, resource, LockMode.S);
			harness.lock(SECOND, resource, LockMode.S);
			controller.assertComplete();
			ScheduleControl.reset();
			harness.end(FIRST);
			harness.end(SECOND);
			break;
		case "shared-exclusive-conflict":
			replayConflict(harness, controller, resource, LockMode.S, LockMode.X);
			break;
		case "exclusive-shared-conflict":
			replayConflict(harness, controller, resource, LockMode.X, LockMode.S);
			break;
		case "exclusive-exclusive-conflict":
			replayConflict(harness, controller, resource, LockMode.X, LockMode.X);
			break;
		case "single-upgrader":
			harness.lock(FIRST, resource, LockMode.S);
			harness.lock(FIRST, resource, LockMode.X);
			controller.assertComplete();
			ScheduleControl.reset();
			harness.end(FIRST);
			break;
		case "double-upgrader":
			replayDoubleUpgrade(harness, controller, resource);
			break;
		case "writer-commit-reader-grant":
			replayTerminal(harness, controller, resource, "commit");
			break;
		case "writer-rollback-reader-grant":
			replayTerminal(harness, controller, resource, "rollback");
			break;
		default:
			throw new IllegalArgumentException("unknown schedule " + SCENARIO);
		}
	}

	private void replayConflict(DirectLockTableHarness harness,
			StrictScheduleController controller, String resource, LockMode firstMode,
			LockMode secondMode) throws Exception {
		harness.lock(FIRST, resource, firstMode);
		Future<Void> waiting = harness.submitLock(SECOND, resource, secondMode);
		controller.awaitObserved(lock("WAIT_BEGIN", SECOND, secondMode, "wait",
				resource), 5, TimeUnit.SECONDS);
		controller.assertComplete();
		ScheduleControl.reset();
		harness.end(FIRST);
		harness.awaitCompletion(waiting, 5, TimeUnit.SECONDS);
		harness.end(SECOND);
	}

	private void replayDoubleUpgrade(DirectLockTableHarness harness,
			StrictScheduleController controller, String resource) throws Exception {
		harness.lock(FIRST, resource, LockMode.S);
		harness.lock(SECOND, resource, LockMode.S);
		Future<Void> firstUpgrade = harness.submitLock(FIRST, resource, LockMode.X);
		controller.awaitObserved(lock("WAIT_BEGIN", FIRST, LockMode.X, "wait",
				resource), 5, TimeUnit.SECONDS);
		Future<Void> secondUpgrade = harness.submitLock(SECOND, resource, LockMode.X);
		controller.awaitObserved(lock("WAIT_BEGIN", SECOND, LockMode.X, "wait",
				resource), 5, TimeUnit.SECONDS);
		controller.assertComplete();
		ScheduleControl.reset();
		harness.end(FIRST);
		harness.awaitCompletion(secondUpgrade, 5, TimeUnit.SECONDS);
		harness.end(SECOND);
		harness.awaitCompletion(firstUpgrade, 5, TimeUnit.SECONDS);
		harness.end(FIRST);
	}

	private void replayTerminal(DirectLockTableHarness harness,
			StrictScheduleController controller, String resource, String terminal)
			throws Exception {
		harness.lock(FIRST, resource, LockMode.X);
		Future<Void> waiting = harness.submitLock(SECOND, resource, LockMode.S);
		controller.awaitObserved(lock("WAIT_BEGIN", SECOND, LockMode.S, "wait",
				resource), 5, TimeUnit.SECONDS);
		ScheduleControl.observeHarness("HARNESS_OPERATION", FIRST,
				"harness.transaction." + terminal);
		harness.end(FIRST);
		harness.awaitCompletion(waiting, 5, TimeUnit.SECONDS);
		controller.assertComplete();
		ScheduleControl.reset();
		harness.end(SECOND);
	}

	private List<ScheduleEvent> expected(String resource) {
		switch (SCENARIO) {
		case "shared-shared-compatible":
			return Arrays.asList(
					lock("LOCK_CALL", FIRST, LockMode.S, "call", resource),
					lock("GRANT", FIRST, LockMode.S, "grant", resource),
					lock("LOCK_CALL", SECOND, LockMode.S, "call", resource),
					lock("GRANT", SECOND, LockMode.S, "grant", resource));
		case "shared-exclusive-conflict":
			return conflictExpected(resource, LockMode.S, LockMode.X);
		case "exclusive-shared-conflict":
			return conflictExpected(resource, LockMode.X, LockMode.S);
		case "exclusive-exclusive-conflict":
			return conflictExpected(resource, LockMode.X, LockMode.X);
		case "single-upgrader":
			return Arrays.asList(
					lock("LOCK_CALL", FIRST, LockMode.S, "call", resource),
					lock("GRANT", FIRST, LockMode.S, "grant", resource),
					lock("LOCK_CALL", FIRST, LockMode.X, "call", resource),
					lock("GRANT", FIRST, LockMode.X, "grant", resource));
		case "double-upgrader":
			return Arrays.asList(
					lock("LOCK_CALL", FIRST, LockMode.S, "call", resource),
					lock("GRANT", FIRST, LockMode.S, "grant", resource),
					lock("LOCK_CALL", SECOND, LockMode.S, "call", resource),
					lock("GRANT", SECOND, LockMode.S, "grant", resource),
					lock("LOCK_CALL", FIRST, LockMode.X, "call", resource),
					lock("WAIT_BEGIN", FIRST, LockMode.X, "wait", resource),
					lock("LOCK_CALL", SECOND, LockMode.X, "call", resource),
					lock("WAIT_BEGIN", SECOND, LockMode.X, "wait", resource));
		case "writer-commit-reader-grant":
			return terminalExpected(resource, "commit");
		case "writer-rollback-reader-grant":
			return terminalExpected(resource, "rollback");
		default:
			throw new IllegalArgumentException("unknown schedule " + SCENARIO);
		}
	}

	private List<ScheduleEvent> conflictExpected(String resource,
			LockMode firstMode, LockMode secondMode) {
		return Arrays.asList(
				lock("LOCK_CALL", FIRST, firstMode, "call", resource),
				lock("GRANT", FIRST, firstMode, "grant", resource),
				lock("LOCK_CALL", SECOND, secondMode, "call", resource),
				lock("WAIT_BEGIN", SECOND, secondMode, "wait", resource));
	}

	private List<ScheduleEvent> terminalExpected(String resource,
			String terminal) {
		List<ScheduleEvent> events = new ArrayList<ScheduleEvent>(
				conflictExpected(resource, LockMode.X, LockMode.S));
		events.add(new ScheduleEvent("HARNESS_OPERATION", FIRST,
				"harness.transaction." + terminal, null, null, null));
		events.add(lock("RELEASE", FIRST, LockMode.X, "releaseAll", resource));
		events.add(lock("GRANT", SECOND, LockMode.S, "grant", resource));
		return events;
	}

	private ScheduleEvent lock(String eventType, long transactionId,
			LockMode mode, String phase, String resource) {
		String normalized = mode.name().toLowerCase();
		String sourceSite = phase.equals("releaseAll")
				? "locktable.releaseAll." + normalized
				: "locktable." + normalized + "." + phase;
		return new ScheduleEvent(eventType, transactionId, sourceSite, "FILE",
				resource, mode.name());
	}

	private void assertClean(LockTableTestProbe.ResidueSnapshot residue,
			List<String> liveWorkers) {
		assertEquals(0, residue.lockerMapEntries);
		assertEquals(0, residue.ownerReferences);
		assertEquals(0, residue.requestReferences);
		assertEquals(0, residue.transactionLockSetEntries);
		assertEquals(0, residue.waitRegistrationEntries);
		assertEquals(0, residue.abortRegistryEntries);
		assertEquals(Collections.emptyList(), liveWorkers);
	}

	private void writeResult(List<ScheduleEvent> expected,
			List<ScheduleEvent> linearization, LockTraceSnapshot snapshot,
			LockTableTestProbe.ResidueSnapshot residue, List<String> liveWorkers,
			Throwable failure) throws Exception {
		Files.createDirectories(OUTPUT.getParent());
		try (BufferedWriter writer = Files.newBufferedWriter(OUTPUT,
				StandardCharsets.UTF_8, StandardOpenOption.CREATE,
				StandardOpenOption.TRUNCATE_EXISTING)) {
			writer.write("{");
			field(writer, "schedule", SCENARIO);
			field(writer, "mode", MODE);
			number(writer, "seed", SEED);
			field(writer, "status", failure == null ? "PASS" : "FAIL");
			number(writer, "expectedEvents", expected.size());
			number(writer, "actualEvents", linearization.size());
			number(writer, "recordedTraceEvents",
					snapshot == null ? -1 : snapshot.events().size());
			number(writer, "droppedEvents",
					snapshot == null ? -1 : snapshot.droppedEvents());
			number(writer, "lockerMapEntries",
					residue == null ? -1 : residue.lockerMapEntries);
			number(writer, "ownerReferences",
					residue == null ? -1 : residue.ownerReferences);
			number(writer, "requestReferences",
					residue == null ? -1 : residue.requestReferences);
			number(writer, "transactionLockSetEntries",
					residue == null ? -1 : residue.transactionLockSetEntries);
			number(writer, "waitRegistrationEntries",
					residue == null ? -1 : residue.waitRegistrationEntries);
			number(writer, "abortRegistryEntries",
					residue == null ? -1 : residue.abortRegistryEntries);
			number(writer, "liveWorkerThreads", liveWorkers.size());
			field(writer, "failureClass",
					failure == null ? null : failure.getClass().getName());
			field(writer, "failureMessage",
					failure == null ? null : failure.getMessage());
			writer.write("\"linearization\":[");
			for (int index = 0; index < linearization.size(); index++) {
				if (index > 0)
					writer.write(",");
				writer.write("\"" + escape(linearization.get(index).toString())
						+ "\"");
			}
			writer.write("]}");
		}
	}

	private void field(BufferedWriter writer, String name, String value)
			throws Exception {
		writer.write("\"" + name + "\":");
		writer.write(value == null ? "null" : "\"" + escape(value) + "\"");
		writer.write(",");
	}

	private void number(BufferedWriter writer, String name, long value)
			throws Exception {
		writer.write("\"" + name + "\":" + value + ",");
	}

	private String escape(String value) {
		return value.replace("\\", "\\\\").replace("\"", "\\\"")
				.replace("\n", "\\n").replace("\r", "\\r");
	}

	private void rethrow(Throwable failure) throws Exception {
		if (failure instanceof Exception)
			throw (Exception) failure;
		if (failure instanceof Error)
			throw (Error) failure;
		throw new RuntimeException(failure);
	}
}
