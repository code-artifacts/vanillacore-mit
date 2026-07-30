package org.vanilladb.core.storage.tx.concurrency.trace;

public interface LockTraceSink {

	void record(LockTraceEventType eventType, long transactionId, String sourceMethod,
			String sourceSite, String resourceId, String requestedMode);
}
