package org.vanilladb.core.storage.tx.concurrency.trace;

public final class LockTraceEvent {
	public static final String SCHEMA_VERSION = "vc-locktrace-0";

	private final String runId;
	private final long eventId;
	private final long threadId;
	private final long threadSequence;
	private final long transactionId;
	private final LockTraceEventType eventType;
	private final String sourceMethod;
	private final String sourceSite;
	private final String resourceKind;
	private final String resourceId;
	private final String requestedMode;
	private final long nanoTime;

	LockTraceEvent(String runId, long eventId, long threadId, long threadSequence,
			long transactionId, LockTraceEventType eventType, String sourceMethod,
			String sourceSite, String resourceKind, String resourceId,
			String requestedMode, long nanoTime) {
		this.runId = runId;
		this.eventId = eventId;
		this.threadId = threadId;
		this.threadSequence = threadSequence;
		this.transactionId = transactionId;
		this.eventType = eventType;
		this.sourceMethod = sourceMethod;
		this.sourceSite = sourceSite;
		this.resourceKind = resourceKind;
		this.resourceId = resourceId;
		this.requestedMode = requestedMode;
		this.nanoTime = nanoTime;
	}

	public String schemaVersion() {
		return SCHEMA_VERSION;
	}

	public String runId() {
		return runId;
	}

	public long eventId() {
		return eventId;
	}

	public long threadId() {
		return threadId;
	}

	public long threadSequence() {
		return threadSequence;
	}

	public long transactionId() {
		return transactionId;
	}

	public LockTraceEventType eventType() {
		return eventType;
	}

	public String sourceMethod() {
		return sourceMethod;
	}

	public String sourceClass() {
		return "LockTable";
	}

	public String sourceSite() {
		return sourceSite;
	}

	public String resourceKind() {
		return resourceKind;
	}

	public String resourceId() {
		return resourceId;
	}

	public String resourceRole() {
		return "UNKNOWN";
	}

	public String parentResourceId() {
		return null;
	}

	public String lockPurpose() {
		return "UNKNOWN";
	}

	public String requestedMode() {
		return requestedMode;
	}

	public String evidence() {
		return "OBSERVED";
	}

	public long nanoTime() {
		return nanoTime;
	}
}
