package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import org.junit.After;
import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSink;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTrace;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceSink;

public class LockTableTraceInstrumentationTest {

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(LockTableTraceInstrumentationTest.class);
	}

	@After
	public void resetSink() {
		LockTrace.reset();
	}

	@Test
	public void emitsCallGrantReleaseAndTransactionEnd() {
		LockTable lockTable = new LockTable();
		BoundedLockTraceSink sink = new BoundedLockTraceSink("step-02-basic", 16);
		LockTrace.install(sink);
		long transactionId = 2101;

		lockTable.sLock("step-02-basic-resource", transactionId);
		lockTable.releaseAll(transactionId, false);

		List<LockTraceEvent> events = sink.snapshot().events();
		assertEquals(Arrays.asList(LockTraceEventType.LOCK_CALL,
				LockTraceEventType.GRANT, LockTraceEventType.RELEASE,
				LockTraceEventType.TX_END), eventTypes(events));
		assertEquals("FILE", events.get(0).resourceKind());
		assertEquals("S", events.get(0).requestedMode());
		assertEquals("locktable.s.call", events.get(0).sourceSite());
	}

	@Test
	public void emitsWaitBeforeReleaseAndGrant() throws Exception {
		LockTable lockTable = new LockTable();
		SignalingSink sink = new SignalingSink("step-02-wait", 32);
		LockTrace.install(sink);
		String resource = "step-02-wait-resource";
		long holder = 2201;
		long waiter = 2202;
		ExecutorService executor = Executors.newSingleThreadExecutor();

		try {
			lockTable.xLock(resource, holder);
			Future<?> waitingRequest = executor.submit(() ->
					lockTable.sLock(resource, waiter));
			assertTrue(sink.awaitWait(5, TimeUnit.SECONDS));
			lockTable.releaseAll(holder, false);
			waitingRequest.get(5, TimeUnit.SECONDS);
			lockTable.releaseAll(waiter, false);

			List<LockTraceEvent> events = sink.snapshot();
			long waitId = eventId(events, waiter, LockTraceEventType.WAIT_BEGIN);
			long holderReleaseId = eventId(events, holder,
					LockTraceEventType.RELEASE);
			long waiterGrantId = eventId(events, waiter, LockTraceEventType.GRANT);
			assertTrue(waitId < holderReleaseId);
			assertTrue(holderReleaseId < waiterGrantId);
		} finally {
			lockTable.releaseAll(holder, false);
			lockTable.releaseAll(waiter, false);
			executor.shutdownNow();
		}
	}

	private static List<LockTraceEventType> eventTypes(
			List<LockTraceEvent> events) {
		return events.stream().map(LockTraceEvent::eventType)
				.collect(Collectors.toList());
	}

	private static long eventId(List<LockTraceEvent> events, long transactionId,
			LockTraceEventType eventType) {
		return events.stream()
				.filter(event -> event.transactionId() == transactionId)
				.filter(event -> event.eventType() == eventType)
				.findFirst()
				.orElseThrow(() -> new AssertionError(
						"missing " + eventType + " for transaction " + transactionId))
				.eventId();
	}

	private static final class SignalingSink implements LockTraceSink {
		private final BoundedLockTraceSink delegate;
		private final CountDownLatch waitObserved = new CountDownLatch(1);

		private SignalingSink(String runId, int capacity) {
			delegate = new BoundedLockTraceSink(runId, capacity);
		}

		@Override
		public void record(LockTraceEventType eventType, long transactionId,
				String sourceMethod, String sourceSite, String resourceKind,
				String resourceId, String requestedMode) {
			delegate.record(eventType, transactionId, sourceMethod, sourceSite,
					resourceKind, resourceId, requestedMode);
			if (eventType == LockTraceEventType.WAIT_BEGIN)
				waitObserved.countDown();
		}

		private boolean awaitWait(long timeout, TimeUnit unit)
				throws InterruptedException {
			return waitObserved.await(timeout, unit);
		}

		private List<LockTraceEvent> snapshot() {
			return delegate.snapshot().events();
		}
	}
}
