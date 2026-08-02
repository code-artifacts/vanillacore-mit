package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.Objects;

public final class ScheduleNode {
	private final String id;
	private final ScheduleEvent event;

	public ScheduleNode(String id, ScheduleEvent event) {
		this.id = Objects.requireNonNull(id, "id");
		this.event = Objects.requireNonNull(event, "event");
	}

	public String id() {
		return id;
	}

	public ScheduleEvent event() {
		return event;
	}
}
