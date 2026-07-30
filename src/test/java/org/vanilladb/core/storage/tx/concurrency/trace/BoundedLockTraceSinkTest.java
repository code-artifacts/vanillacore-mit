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
	public void recordsConcurrentWritersWithoutDuplicateIds() throws Exception {
		int workerCount = 4;
		int eventsPerWorker = 100;
		BoundedLockTraceSink sink = new BoundedLockTraceSink("run-concurrent",
				workerCount * eventsPerWorker);
		ExecutorService executor = Executors.newFixedThreadPool(workerCount);
		CountDownLatch start = new CountDownLatch(1);

		for (int worker = 0; worker < workerCount; worker++) {
			final long transactionId = worker + 1;
			executor.submit(() -> {
				start.await();
				for (int event = 0; event < eventsPerWorker; event++) {
					sink.record(LockTraceEventType.LOCK_CALL, transactionId,
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
