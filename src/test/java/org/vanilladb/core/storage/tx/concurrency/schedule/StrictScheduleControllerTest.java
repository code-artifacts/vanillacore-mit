package org.vanilladb.core.storage.tx.concurrency.schedule;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import org.junit.After;
import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarness;
import org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarness.LockMode;
import org.vanilladb.core.storage.tx.concurrency.schedule.ScheduleDivergence.Kind;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;

public class StrictScheduleControllerTest {

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(StrictScheduleControllerTest.class);
	}

	@After
	public void resetSchedule() {
		ScheduleControl.reset();
	}

	@Test
	public void replaysRealContendedLockSequence() throws Exception {
		String resource = "strict-contended";
		long holder = 7101;
		long waiter = 7102;
		StrictScheduleController controller = new StrictScheduleController(
				Arrays.asList(
						lock("LOCK_CALL", holder, "locktable.x.call", resource, "X"),
						lock("GRANT", holder, "locktable.x.grant", resource, "X"),
						lock("LOCK_CALL", waiter, "locktable.s.call", resource, "S"),
						lock("WAIT_BEGIN", waiter, "locktable.s.wait", resource, "S"),
						lock("RELEASE", holder, "locktable.releaseAll.x", resource, "X"),
						lock("TX_END", holder, "locktable.releaseAll.txEnd", null, null),
						lock("GRANT", waiter, "locktable.s.grant", resource, "S"),
						lock("RELEASE", waiter, "locktable.releaseAll.s", resource, "S"),
						lock("TX_END", waiter, "locktable.releaseAll.txEnd", null, null)),
				5, TimeUnit.SECONDS);
		ScheduleControl.install(controller);

		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				"strict-contended", 32, 1)) {
			harness.lock(holder, resource, LockMode.X);
			Future<Void> waiting = harness.submitLock(waiter, resource, LockMode.S);
			harness.awaitEvent(waiter, LockTraceEventType.WAIT_BEGIN, resource, 5,
					TimeUnit.SECONDS);
			harness.end(holder);
			harness.awaitCompletion(waiting, 5, TimeUnit.SECONDS);
			harness.end(waiter);
		}
		controller.assertComplete();
		assertEquals(9, controller.actualLinearization().size());
	}

	@Test
	public void gatesLaterSafeEventUntilEnabled() throws Exception {
		ScheduleEvent first = lock("LOCK_CALL", 7201, "locktable.s.call", "r", "S");
		ScheduleEvent second = lock("LOCK_CALL", 7202, "locktable.s.call", "r", "S");
		StrictScheduleController controller = new StrictScheduleController(
				Arrays.asList(first, second), 5, TimeUnit.SECONDS);
		Thread later = new Thread(() -> controller.observe(second), "later-gate");
		later.start();
		Thread.sleep(25);
		assertTrue(later.isAlive());
		controller.observe(first);
		later.join(1000);
		controller.assertComplete();
	}

	@Test
	public void classifiesRequiredDivergenceKinds() {
		ScheduleEvent expected = lock("LOCK_CALL", 7301, "locktable.s.call", "r1", "S");
		assertKind(Kind.WRONG_TRANSACTION, expected,
				lock("LOCK_CALL", 7302, "locktable.s.call", "r1", "S"));
		assertKind(Kind.WRONG_RESOURCE, expected,
				lock("LOCK_CALL", 7301, "locktable.s.call", "r2", "S"));

		StrictScheduleController missing = controller(expected);
		assertDivergence(Kind.MISSING_EVENT, missing::assertComplete);

		StrictScheduleController extra = controller(expected);
		extra.observe(expected);
		assertDivergence(Kind.EXTRA_EVENT, () -> extra.observe(expected));

		StrictScheduleController harness = controller(expected);
		harness.recordHarnessException(new IllegalStateException("worker failed"));
		assertDivergence(Kind.HARNESS_EXCEPTION, harness::assertComplete);
	}

	@Test
	public void classifiesGateTimeoutAndPreservesShortestPrefixes() {
		ScheduleEvent first = lock("LOCK_CALL", 7401, "locktable.s.call", "r", "S");
		ScheduleEvent second = lock("LOCK_CALL", 7402, "locktable.s.call", "r", "S");
		StrictScheduleController controller = new StrictScheduleController(
				Arrays.asList(first, second), 10, TimeUnit.MILLISECONDS);
		try {
			controller.observe(second);
			fail("expected timeout");
		} catch (ScheduleDivergence divergence) {
			assertEquals(Kind.TIMEOUT, divergence.kind());
			assertEquals(Arrays.asList(first), divergence.expectedPrefix());
			assertEquals(Arrays.asList(second), divergence.actualPrefix());
		}
	}

	private StrictScheduleController controller(ScheduleEvent expected) {
		return new StrictScheduleController(Arrays.asList(expected), 1,
				TimeUnit.SECONDS);
	}

	private void assertKind(Kind kind, ScheduleEvent expected,
			ScheduleEvent actual) {
		assertDivergence(kind, () -> controller(expected).observe(actual));
	}

	private void assertDivergence(Kind kind, Runnable action) {
		try {
			action.run();
			fail("expected " + kind);
		} catch (ScheduleDivergence divergence) {
			assertEquals(kind, divergence.kind());
		}
	}

	private static ScheduleEvent lock(String eventType, long transactionId,
			String sourceSite, String resourceId, String mode) {
		return new ScheduleEvent(eventType, transactionId, sourceSite,
				resourceId == null ? null : "FILE", resourceId, mode);
	}
}
