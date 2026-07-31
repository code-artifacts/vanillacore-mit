package org.vanilladb.core.storage.tx.concurrency.trace;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.List;
import java.util.concurrent.atomic.AtomicIntegerArray;
import java.util.concurrent.atomic.AtomicReferenceArray;
import java.util.concurrent.atomic.AtomicLong;

public final class BoundedLockTraceSink implements LockTraceSink {
	private final String runId;
	private final int capacity;
	private final AtomicReferenceArray<LockTraceEvent> events;
	private final DeferredEventBuffer deferredEvents;
	private final EnumSet<LockTraceEventType> acceptedEventTypes;
	private final AtomicLong nextEventId = new AtomicLong();
	private final AtomicLong droppedEvents = new AtomicLong();
	private final ThreadLocal<ThreadState> threadState = new ThreadLocal<ThreadState>() {
		@Override
		protected ThreadState initialValue() {
			return new ThreadState(Thread.currentThread().getId());
		}
	};

	public BoundedLockTraceSink(String runId, int capacity) {
		this(runId, capacity, EnumSet.allOf(LockTraceEventType.class), false);
	}

	public static BoundedLockTraceSink low(String runId, int capacity) {
		return new BoundedLockTraceSink(runId, capacity,
				EnumSet.of(LockTraceEventType.GRANT, LockTraceEventType.RELEASE,
						LockTraceEventType.TX_END), true);
	}

	private BoundedLockTraceSink(String runId, int capacity,
			EnumSet<LockTraceEventType> acceptedEventTypes, boolean deferEvents) {
		if (runId == null || runId.isEmpty()) {
			throw new IllegalArgumentException("runId must not be empty");
		}
		if (capacity <= 0) {
			throw new IllegalArgumentException("capacity must be positive");
		}
		this.runId = runId;
		this.capacity = capacity;
		this.events = deferEvents ? null
				: new AtomicReferenceArray<LockTraceEvent>(capacity);
		this.deferredEvents = deferEvents ? new DeferredEventBuffer(capacity) : null;
		this.acceptedEventTypes = acceptedEventTypes;
	}

	@Override
	public boolean accepts(LockTraceEventType eventType) {
		return eventType != null && acceptedEventTypes.contains(eventType);
	}

	@Override
	public void record(LockTraceEventType eventType, long transactionId,
			String sourceMethod, String sourceSite, String resourceKind,
			String resourceId, String requestedMode) {
		if (eventType == null) {
			throw new IllegalArgumentException("eventType must not be null");
		}
		if (!accepts(eventType))
			return;
		ThreadState currentThread = threadState.get();
		long sequence = ++currentThread.sequence;
		long eventId = nextEventId.incrementAndGet();
		if (eventId > capacity) {
			droppedEvents.incrementAndGet();
			return;
		}
		long nanoTime = System.nanoTime();
		int index = (int) eventId - 1;
		if (deferredEvents != null) {
			deferredEvents.record(index, currentThread.threadId, sequence,
					transactionId, eventType, sourceMethod, sourceSite, resourceKind,
					resourceId, requestedMode, nanoTime);
		} else {
			LockTraceEvent event = new LockTraceEvent(runId, eventId,
					currentThread.threadId, sequence, transactionId, eventType,
					sourceMethod, sourceSite, resourceKind, resourceId, requestedMode,
					nanoTime);
			events.set(index, event);
		}
	}

	public LockTraceSnapshot snapshot() {
		int eventCount = (int) Math.min(nextEventId.get(), capacity);
		List<LockTraceEvent> snapshot = new ArrayList<LockTraceEvent>(eventCount);
		for (int index = 0; index < eventCount; index++) {
			LockTraceEvent event = deferredEvents == null ? events.get(index)
					: deferredEvents.materialize(runId, index);
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

	private static final class ThreadState {
		private final long threadId;
		private long sequence;

		private ThreadState(long threadId) {
			this.threadId = threadId;
		}
	}

	private static final class DeferredEventBuffer {
		private final AtomicIntegerArray eventTypes;
		private final long[] threadIds;
		private final long[] threadSequences;
		private final long[] transactionIds;
		private final long[] nanoTimes;
		private final String[] sourceMethods;
		private final String[] sourceSites;
		private final String[] resourceKinds;
		private final String[] resourceIds;
		private final String[] requestedModes;

		private DeferredEventBuffer(int capacity) {
			eventTypes = new AtomicIntegerArray(capacity);
			threadIds = new long[capacity];
			threadSequences = new long[capacity];
			transactionIds = new long[capacity];
			nanoTimes = new long[capacity];
			sourceMethods = new String[capacity];
			sourceSites = new String[capacity];
			resourceKinds = new String[capacity];
			resourceIds = new String[capacity];
			requestedModes = new String[capacity];
		}

		private void record(int index, long threadId, long threadSequence,
				long transactionId, LockTraceEventType eventType,
				String sourceMethod, String sourceSite, String resourceKind,
				String resourceId, String requestedMode, long nanoTime) {
			threadIds[index] = threadId;
			threadSequences[index] = threadSequence;
			transactionIds[index] = transactionId;
			nanoTimes[index] = nanoTime;
			sourceMethods[index] = sourceMethod;
			sourceSites[index] = sourceSite;
			resourceKinds[index] = resourceKind;
			resourceIds[index] = resourceId;
			requestedModes[index] = requestedMode;
			eventTypes.set(index, eventType.ordinal() + 1);
		}

		private LockTraceEvent materialize(String runId, int index) {
			int encodedEventType = eventTypes.get(index);
			if (encodedEventType == 0)
				return null;
			LockTraceEventType eventType = LockTraceEventType.values()[encodedEventType - 1];
			return new LockTraceEvent(runId, index + 1, threadIds[index],
					threadSequences[index], transactionIds[index], eventType,
					sourceMethods[index], sourceSites[index], resourceKinds[index],
					resourceIds[index], requestedModes[index], nanoTimes[index]);
		}
	}
}
