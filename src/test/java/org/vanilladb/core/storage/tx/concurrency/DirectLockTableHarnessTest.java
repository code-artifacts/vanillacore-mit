package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarness.LockMode;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;

public class DirectLockTableHarnessTest {

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(DirectLockTableHarnessTest.class);
	}

	@Test
	public void wrapsSynchronousLifecycle() {
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				"step-03-sync", 16, 1)) {
			harness.lock(3101, "step-03-sync-resource", LockMode.S);
			harness.end(3101);

			assertEquals(Arrays.asList(LockTraceEventType.LOCK_CALL,
					LockTraceEventType.GRANT, LockTraceEventType.RELEASE,
					LockTraceEventType.TX_END), eventTypes(harness.snapshot().events()));
			assertTrue(harness.snapshot().isComplete());
		}
	}

	@Test
	public void controlsBlockedRequestWithoutSleeps() throws Exception {
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				"step-03-blocked", 32, 1)) {
			String resource = "step-03-blocked-resource";
			harness.lock(3201, resource, LockMode.X);
			Future<Void> waiter = harness.submitLock(3202, resource, LockMode.S);

			LockTraceEvent waitEvent = harness.awaitEvent(3202,
					LockTraceEventType.WAIT_BEGIN, resource, 5, TimeUnit.SECONDS);
			harness.end(3201);
			harness.awaitCompletion(waiter, 5, TimeUnit.SECONDS);
			harness.end(3202);

			LockTraceEvent grantEvent = harness.awaitEvent(3202,
					LockTraceEventType.GRANT, resource, 1, TimeUnit.SECONDS);
			assertTrue(waitEvent.eventId() < grantEvent.eventId());
			assertTrue(harness.snapshot().isComplete());
		}
	}

	private static List<LockTraceEventType> eventTypes(
			List<LockTraceEvent> events) {
		return events.stream().map(LockTraceEvent::eventType)
				.collect(Collectors.toList());
	}
}
