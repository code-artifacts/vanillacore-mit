package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.Objects;

public final class ScheduleEvent {
	private final String eventType;
	private final long transactionId;
	private final String sourceSite;
	private final String resourceKind;
	private final String resourceId;
	private final String requestedMode;

	public ScheduleEvent(String eventType, long transactionId, String sourceSite,
			String resourceKind, String resourceId, String requestedMode) {
		this.eventType = Objects.requireNonNull(eventType, "eventType");
		this.transactionId = transactionId;
		this.sourceSite = Objects.requireNonNull(sourceSite, "sourceSite");
		this.resourceKind = resourceKind;
		this.resourceId = resourceId;
		this.requestedMode = requestedMode;
	}

	public String eventType() {
		return eventType;
	}

	public long transactionId() {
		return transactionId;
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

	public String requestedMode() {
		return requestedMode;
	}

	@Override
	public boolean equals(Object other) {
		if (this == other)
			return true;
		if (!(other instanceof ScheduleEvent))
			return false;
		ScheduleEvent event = (ScheduleEvent) other;
		return transactionId == event.transactionId
				&& eventType.equals(event.eventType)
				&& sourceSite.equals(event.sourceSite)
				&& Objects.equals(resourceKind, event.resourceKind)
				&& Objects.equals(resourceId, event.resourceId)
				&& Objects.equals(requestedMode, event.requestedMode);
	}

	@Override
	public int hashCode() {
		return Objects.hash(eventType, transactionId, sourceSite, resourceKind,
				resourceId, requestedMode);
	}

	@Override
	public String toString() {
		return eventType + "@" + sourceSite + "(tx=" + transactionId
				+ ",resource=" + resourceId + ",mode=" + requestedMode + ")";
	}
}
