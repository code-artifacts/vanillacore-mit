package org.vanilladb.core.storage.tx.concurrency.trace;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.junit.After;
import org.junit.Test;

public class BoundedLockTraceSinkTest {

	@After
	public void resetGlobalSink() {
		LockTrace.reset();
	}

	@Test
	public void recordsSchemaAndMonotonicSequences() {
		BoundedLockTraceSink sink = new BoundedLockTraceSink("run-sequence", 4);
		LockTrace.install(sink);

		LockTrace.record(LockTraceEventType.LOCK_CALL, 7, "sLock",
				"lock.s.call", "STRING", "resource-1", "S");
		LockTrace.record(LockTraceEventType.GRANT, 7, "sLock",
				"lock.s.grant", "STRING", "resource-1", "S");

		LockTraceSnapshot snapshot = sink.snapshot();
		assertTrue(snapshot.isComplete());
		assertEquals(2, snapshot.events().size());
		assertEquals(LockTraceEvent.SCHEMA_VERSION,
				snapshot.events().get(0).schemaVersion());
		assertEquals(1, snapshot.events().get(0).eventId());
		assertEquals(2, snapshot.events().get(1).eventId());
		assertEquals(1, snapshot.events().get(0).threadSequence());
		assertEquals(2, snapshot.events().get(1).threadSequence());
		assertEquals("run-sequence", snapshot.events().get(0).runId());
	}

	@Test
	public void reportsCapacityLossExplicitly() {
		BoundedLockTraceSink sink = new BoundedLockTraceSink("run-loss", 1);
		sink.record(LockTraceEventType.LOCK_CALL, 1, "xLock", "lock.x.call",
				"STRING", "resource-1", "X");
		sink.record(LockTraceEventType.GRANT, 1, "xLock", "lock.x.grant",
				"STRING", "resource-1", "X");

		LockTraceSnapshot snapshot = sink.snapshot();
		assertFalse(snapshot.isComplete());
		assertEquals(1, snapshot.events().size());
		assertEquals(1, snapshot.droppedEvents());
	}

	@Test
	public void lowModeAdvertisesOnlyRetainedEventTypes() {
		assertFalse(LockTrace.accepts(LockTraceEventType.GRANT));

		BoundedLockTraceSink sink = BoundedLockTraceSink.low("run-accepts", 4);
		LockTrace.install(sink);

		assertFalse(LockTrace.accepts(LockTraceEventType.LOCK_CALL));
		assertFalse(LockTrace.accepts(LockTraceEventType.WAIT_BEGIN));
		assertTrue(LockTrace.accepts(LockTraceEventType.GRANT));
		assertTrue(LockTrace.accepts(LockTraceEventType.RELEASE));
		assertTrue(LockTrace.accepts(LockTraceEventType.TX_END));
	}

	@Test
	public void lowModeRetainsOnlyLifecycleStateChanges() {
		BoundedLockTraceSink sink = BoundedLockTraceSink.low("run-low", 4);
		sink.record(LockTraceEventType.LOCK_CALL, 1, "sLock", "lock.s.call",
				"STRING", "resource-1", "S");
		sink.record(LockTraceEventType.WAIT_BEGIN, 1, "sLock", "lock.s.wait",
				"STRING", "resource-1", "S");
		sink.record(LockTraceEventType.GRANT, 1, "sLock", "lock.s.grant",
				"STRING", "resource-1", "S");
		sink.record(LockTraceEventType.RELEASE, 1, "release", "lock.release.s",
				"STRING", "resource-1", "S");
		sink.record(LockTraceEventType.TX_END, 1, "releaseAll",
				"lock.releaseAll.txEnd", null, null, null);

		LockTraceSnapshot snapshot = sink.snapshot();
		assertEquals(3, snapshot.events().size());
		assertEquals(LockTraceEventType.GRANT,
				snapshot.events().get(0).eventType());
		assertEquals(LockTraceEventType.RELEASE,
				snapshot.events().get(1).eventType());
		assertEquals(LockTraceEventType.TX_END,
				snapshot.events().get(2).eventType());
		assertEquals("run-low", snapshot.events().get(0).runId());
		assertEquals(1, snapshot.events().get(0).eventId());
		assertEquals(1, snapshot.events().get(0).transactionId());
		assertEquals("sLock", snapshot.events().get(0).sourceMethod());
		assertEquals("lock.s.grant", snapshot.events().get(0).sourceSite());
		assertEquals("STRING", snapshot.events().get(0).resourceKind());
		assertEquals("resource-1", snapshot.events().get(0).resourceId());
		assertEquals("S", snapshot.events().get(0).requestedMode());
		assertTrue(snapshot.events().get(0).nanoTime() > 0);
	}

	@Test
	public void recordsConcurrentWritersWithoutDuplicateIds() throws Exception {
		assertConcurrentWritersWithoutDuplicateIds(
				new BoundedLockTraceSink("run-concurrent", 400),
				LockTraceEventType.LOCK_CALL);
	}

	@Test
	public void recordsConcurrentLowWritersWithoutDuplicateIds() throws Exception {
		assertConcurrentWritersWithoutDuplicateIds(
				BoundedLockTraceSink.low("run-concurrent-low", 400),
				LockTraceEventType.GRANT);
	}

	private void assertConcurrentWritersWithoutDuplicateIds(
			BoundedLockTraceSink sink, LockTraceEventType eventType) throws Exception {
		int workerCount = 4;
		int eventsPerWorker = 100;
		ExecutorService executor = Executors.newFixedThreadPool(workerCount);
		CountDownLatch start = new CountDownLatch(1);

		for (int worker = 0; worker < workerCount; worker++) {
			final long transactionId = worker + 1;
			executor.submit(() -> {
				start.await();
				for (int event = 0; event < eventsPerWorker; event++) {
					sink.record(eventType, transactionId,
							"sLock", "lock.s.call", "STRING", "resource-1", "S");
				}
				return null;
			});
		}

		start.countDown();
		executor.shutdown();
		assertTrue(executor.awaitTermination(10, TimeUnit.SECONDS));

		LockTraceSnapshot snapshot = sink.snapshot();
		Set<Long> eventIds = new HashSet<Long>();
		for (LockTraceEvent event : snapshot.events()) {
			eventIds.add(event.eventId());
		}
		assertTrue(snapshot.isComplete());
		assertEquals(workerCount * eventsPerWorker, snapshot.events().size());
		assertEquals(snapshot.events().size(), eventIds.size());
	}
}
