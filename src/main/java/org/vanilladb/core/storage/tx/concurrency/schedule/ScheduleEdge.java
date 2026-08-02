package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.Objects;

public final class ScheduleEdge {
	private final String before;
	private final String after;
	private final String kind;

	public ScheduleEdge(String before, String after, String kind) {
		this.before = Objects.requireNonNull(before, "before");
		this.after = Objects.requireNonNull(after, "after");
		this.kind = Objects.requireNonNull(kind, "kind");
	}

	public String before() {
		return before;
	}

	public String after() {
		return after;
	}

	public String kind() {
		return kind;
	}
}
