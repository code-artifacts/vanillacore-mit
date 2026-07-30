package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarness.LockMode;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;

public class LockTableReplayScenarioTest {
	private static final int REPETITIONS =
			Integer.getInteger("vanillacore.mit.repetitions", 1);
	private static final Path TRACE_DIRECTORY = Paths.get(
			System.getProperty("vanillacore.mit.traceDir", "target/mit-traces"));

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(LockTableReplayScenarioTest.class);
	}

	@Test
	public void replaySharedShared() throws Exception {
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				"week02-ss", REPETITIONS * 16, 1)) {
			for (int repetition = 0; repetition < REPETITIONS; repetition++) {
				String resource = "ss-" + repetition;
				long first = 410000 + repetition * 2;
				long second = first + 1;
				harness.lock(first, resource, LockMode.S);
				Future<Void> secondLock =
						harness.submitLock(second, resource, LockMode.S);
				harness.awaitCompletion(secondLock, 5, TimeUnit.SECONDS);
				harness.end(first);
				harness.end(second);

				List<LockTraceEvent> iteration = eventsForResource(harness,
						resource);
				assertEquals(2, count(iteration, LockTraceEventType.GRANT));
				assertEquals(0, count(iteration, LockTraceEventType.WAIT_BEGIN));
			}
			writeTrace("s-s", harness);
		}
	}

	@Test
	public void replaySharedExclusive() throws Exception {
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				"week02-sx", REPETITIONS * 16, 1)) {
			for (int repetition = 0; repetition < REPETITIONS; repetition++) {
				String resource = "sx-" + repetition;
				long holder = 420000 + repetition * 2;
				long waiter = holder + 1;
				harness.lock(holder, resource, LockMode.S);
				Future<Void> waitingLock =
						harness.submitLock(waiter, resource, LockMode.X);
				LockTraceEvent wait = harness.awaitEvent(waiter,
						LockTraceEventType.WAIT_BEGIN, resource, 5,
						TimeUnit.SECONDS);
				harness.end(holder);
				harness.awaitCompletion(waitingLock, 5, TimeUnit.SECONDS);
				LockTraceEvent grant = harness.awaitEvent(waiter,
						LockTraceEventType.GRANT, resource, 1, TimeUnit.SECONDS);
				harness.end(waiter);

				assertTrue(wait.eventId() < grant.eventId());
			}
			writeTrace("s-x", harness);
		}
	}

	@Test
	public void replayExclusiveExclusive() throws Exception {
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				"week02-xx", REPETITIONS * 16, 1)) {
			for (int repetition = 0; repetition < REPETITIONS; repetition++) {
				String resource = "xx-" + repetition;
				long holder = 430000 + repetition * 2;
				long waiter = holder + 1;
				harness.lock(holder, resource, LockMode.X);
				Future<Void> waitingLock =
						harness.submitLock(waiter, resource, LockMode.X);
				LockTraceEvent wait = harness.awaitEvent(waiter,
						LockTraceEventType.WAIT_BEGIN, resource, 5,
						TimeUnit.SECONDS);
				harness.end(holder);
				harness.awaitCompletion(waitingLock, 5, TimeUnit.SECONDS);
				LockTraceEvent grant = harness.awaitEvent(waiter,
						LockTraceEventType.GRANT, resource, 1, TimeUnit.SECONDS);
				harness.end(waiter);

				assertTrue(wait.eventId() < grant.eventId());
			}
			writeTrace("x-x", harness);
		}
	}

	@Test
	public void replayReverseTwoResource() throws Exception {
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				"week02-reverse-two-resource", REPETITIONS * 32, 2)) {
			for (int repetition = 0; repetition < REPETITIONS; repetition++) {
				String firstResource = "reverse-a-" + repetition;
				String secondResource = "reverse-b-" + repetition;
				long older = 440000 + repetition * 2;
				long younger = older + 1;
				harness.lock(older, firstResource, LockMode.X);
				harness.lock(younger, secondResource, LockMode.X);

				Future<Void> olderSecond = harness.submitLock(older,
						secondResource, LockMode.X);
				LockTraceEvent olderWait = harness.awaitEvent(older,
						LockTraceEventType.WAIT_BEGIN, secondResource, 5,
						TimeUnit.SECONDS);
				Future<Void> youngerSecond = harness.submitLock(younger,
						firstResource, LockMode.X);
				assertLockAbort(youngerSecond);
				harness.end(younger);
				harness.awaitCompletion(olderSecond, 5, TimeUnit.SECONDS);
				LockTraceEvent olderGrant = harness.awaitEvent(older,
						LockTraceEventType.GRANT, secondResource, 1,
						TimeUnit.SECONDS);
				harness.end(older);

				assertTrue(olderWait.eventId() < olderGrant.eventId());
			}
			writeTrace("reverse-two-resource", harness);
		}
	}

	private static void assertLockAbort(Future<Void> operation) throws Exception {
		try {
			operation.get(5, TimeUnit.SECONDS);
			fail("younger transaction should be aborted");
		} catch (ExecutionException exception) {
			assertTrue(exception.getCause() instanceof LockAbortException);
		}
	}

	private static List<LockTraceEvent> eventsForResource(
			DirectLockTableHarness harness, String resource) {
		return harness.snapshot().events().stream()
				.filter(event -> resource.equals(event.resourceId()))
				.collect(Collectors.toList());
	}

	private static long count(List<LockTraceEvent> events,
			LockTraceEventType eventType) {
		return events.stream()
				.filter(event -> event.eventType() == eventType)
				.count();
	}

	private static void writeTrace(String scenario,
			DirectLockTableHarness harness) throws Exception {
		assertTrue("trace loss in " + scenario, harness.snapshot().isComplete());
		LockTraceJsonlWriter.write(TRACE_DIRECTORY.resolve(scenario + ".jsonl"),
				harness.snapshot().events());
	}
}
