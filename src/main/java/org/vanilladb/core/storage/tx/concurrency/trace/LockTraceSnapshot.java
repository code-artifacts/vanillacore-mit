package org.vanilladb.core.storage.tx.concurrency.trace;

import java.util.Collections;
import java.util.List;

public final class LockTraceSnapshot {
	private final List<LockTraceEvent> events;
	private final long droppedEvents;

	LockTraceSnapshot(List<LockTraceEvent> events, long droppedEvents) {
		this.events = Collections.unmodifiableList(events);
		this.droppedEvents = droppedEvents;
	}

	public List<LockTraceEvent> events() {
		return events;
	}

	public long droppedEvents() {
		return droppedEvents;
	}

	public boolean isComplete() {
		return droppedEvents == 0;
	}
}
