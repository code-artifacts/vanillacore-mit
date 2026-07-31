package org.vanilladb.core.storage.tx.concurrency.trace;

public interface LockTraceSink {
	default boolean accepts(LockTraceEventType eventType) {
		return true;
	}

	void record(LockTraceEventType eventType, long transactionId, String sourceMethod,
			String sourceSite, String resourceKind, String resourceId,
			String requestedMode);
}
