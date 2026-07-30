package org.vanilladb.core.storage.tx.concurrency.trace;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.atomic.AtomicLong;

public final class BoundedLockTraceSink implements LockTraceSink {
	private final String runId;
	private final ArrayBlockingQueue<LockTraceEvent> events;
	private final AtomicLong nextEventId = new AtomicLong();
	private final AtomicLong droppedEvents = new AtomicLong();
	private final ThreadLocal<Long> threadSequence = new ThreadLocal<Long>() {
		@Override
		protected Long initialValue() {
			return 0L;
		}
	};

	public BoundedLockTraceSink(String runId, int capacity) {
		if (runId == null || runId.isEmpty()) {
			throw new IllegalArgumentException("runId must not be empty");
		}
		if (capacity <= 0) {
			throw new IllegalArgumentException("capacity must be positive");
		}
		this.runId = runId;
		this.events = new ArrayBlockingQueue<LockTraceEvent>(capacity);
	}

	@Override
	public void record(LockTraceEventType eventType, long transactionId,
			String sourceMethod, String sourceSite, String resourceId,
			String requestedMode) {
		if (eventType == null) {
			throw new IllegalArgumentException("eventType must not be null");
		}
		long sequence = threadSequence.get() + 1;
		threadSequence.set(sequence);
		LockTraceEvent event = new LockTraceEvent(runId, nextEventId.incrementAndGet(),
				Thread.currentThread().getId(), sequence, transactionId, eventType,
				sourceMethod, sourceSite, resourceId, requestedMode, System.nanoTime());
		if (!events.offer(event)) {
			droppedEvents.incrementAndGet();
		}
	}

	public LockTraceSnapshot snapshot() {
		List<LockTraceEvent> snapshot = new ArrayList<LockTraceEvent>(events);
		snapshot.sort(Comparator.comparingLong(LockTraceEvent::eventId));
		return new LockTraceSnapshot(snapshot, droppedEvents.get());
	}
}
