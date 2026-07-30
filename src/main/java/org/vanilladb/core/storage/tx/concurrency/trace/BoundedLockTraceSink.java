package org.vanilladb.core.storage.tx.concurrency.trace;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.List;
import java.util.concurrent.atomic.AtomicReferenceArray;
import java.util.concurrent.atomic.AtomicLong;

public final class BoundedLockTraceSink implements LockTraceSink {
	private final String runId;
	private final int capacity;
	private final AtomicReferenceArray<LockTraceEvent> events;
	private final EnumSet<LockTraceEventType> acceptedEventTypes;
	private final AtomicLong nextEventId = new AtomicLong();
	private final AtomicLong droppedEvents = new AtomicLong();
	private final ThreadLocal<Long> threadSequence = new ThreadLocal<Long>() {
		@Override
		protected Long initialValue() {
			return 0L;
		}
	};

	public BoundedLockTraceSink(String runId, int capacity) {
		this(runId, capacity, EnumSet.allOf(LockTraceEventType.class));
	}

	public static BoundedLockTraceSink low(String runId, int capacity) {
		return new BoundedLockTraceSink(runId, capacity,
				EnumSet.of(LockTraceEventType.GRANT, LockTraceEventType.RELEASE,
						LockTraceEventType.TX_END));
	}

	private BoundedLockTraceSink(String runId, int capacity,
			EnumSet<LockTraceEventType> acceptedEventTypes) {
		if (runId == null || runId.isEmpty()) {
			throw new IllegalArgumentException("runId must not be empty");
		}
		if (capacity <= 0) {
			throw new IllegalArgumentException("capacity must be positive");
		}
		this.runId = runId;
		this.capacity = capacity;
		this.events = new AtomicReferenceArray<LockTraceEvent>(capacity);
		this.acceptedEventTypes = acceptedEventTypes;
	}

	@Override
	public void record(LockTraceEventType eventType, long transactionId,
			String sourceMethod, String sourceSite, String resourceKind,
			String resourceId, String requestedMode) {
		if (eventType == null) {
			throw new IllegalArgumentException("eventType must not be null");
		}
		if (!acceptedEventTypes.contains(eventType))
			return;
		long sequence = threadSequence.get() + 1;
		threadSequence.set(sequence);
		long eventId = nextEventId.incrementAndGet();
		if (eventId > capacity) {
			droppedEvents.incrementAndGet();
			return;
		}
		LockTraceEvent event = new LockTraceEvent(runId, eventId,
				Thread.currentThread().getId(), sequence, transactionId, eventType,
				sourceMethod, sourceSite, resourceKind, resourceId, requestedMode,
				System.nanoTime());
		events.set((int) eventId - 1, event);
	}

	public LockTraceSnapshot snapshot() {
		int eventCount = (int) Math.min(nextEventId.get(), capacity);
		List<LockTraceEvent> snapshot = new ArrayList<LockTraceEvent>(eventCount);
		for (int index = 0; index < eventCount; index++) {
			LockTraceEvent event = events.get(index);
			if (event != null)
				snapshot.add(event);
		}
		snapshot.sort(Comparator.comparingLong(LockTraceEvent::eventId));
		return new LockTraceSnapshot(snapshot, droppedEvents.get());
	}

	public long recordedEvents() {
		return nextEventId.get() - droppedEvents.get();
	}

	public long droppedEvents() {
		return droppedEvents.get();
	}
}
