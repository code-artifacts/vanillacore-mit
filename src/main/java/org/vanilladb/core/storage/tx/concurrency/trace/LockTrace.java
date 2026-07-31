package org.vanilladb.core.storage.tx.concurrency.trace;

import java.util.concurrent.atomic.AtomicReference;

public final class LockTrace {
	private static final LockTraceSink OFF = new LockTraceSink() {
		@Override
		public boolean accepts(LockTraceEventType eventType) {
			return false;
		}

		@Override
		public void record(LockTraceEventType eventType, long transactionId,
				String sourceMethod, String sourceSite, String resourceKind,
				String resourceId, String requestedMode) {
		}
	};
	private static final AtomicReference<LockTraceSink> SINK =
			new AtomicReference<LockTraceSink>(OFF);

	private LockTrace() {
	}

	public static boolean isEnabled() {
		return SINK.get() != OFF;
	}

	public static boolean accepts(LockTraceEventType eventType) {
		return SINK.get().accepts(eventType);
	}

	public static void install(LockTraceSink sink) {
		if (sink == null) {
			throw new IllegalArgumentException("sink must not be null");
		}
		if (!SINK.compareAndSet(OFF, sink)) {
			throw new IllegalStateException("a lock trace sink is already installed");
		}
	}

	public static void reset() {
		SINK.set(OFF);
	}

	public static void record(LockTraceEventType eventType, long transactionId,
			String sourceMethod, String sourceSite, String resourceKind,
			String resourceId, String requestedMode) {
		SINK.get().record(eventType, transactionId, sourceMethod, sourceSite,
				resourceKind, resourceId, requestedMode);
	}
}
