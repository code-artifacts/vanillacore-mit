package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class ScheduleDivergence extends RuntimeException {
	private static final long serialVersionUID = 1L;

	public enum Kind {
		MISSING_EVENT,
		EXTRA_EVENT,
		WRONG_EVENT,
		WRONG_SOURCE_SITE,
		WRONG_TRANSACTION,
		WRONG_RESOURCE,
		WRONG_MODE,
		TIMEOUT,
		HARNESS_EXCEPTION
	}

	private final Kind kind;
	private final List<ScheduleEvent> expectedPrefix;
	private final List<ScheduleEvent> actualPrefix;

	ScheduleDivergence(Kind kind, String message,
			List<ScheduleEvent> expectedPrefix,
			List<ScheduleEvent> actualPrefix, Throwable cause) {
		super(message, cause);
		this.kind = kind;
		this.expectedPrefix = immutableCopy(expectedPrefix);
		this.actualPrefix = immutableCopy(actualPrefix);
	}

	public Kind kind() {
		return kind;
	}

	public List<ScheduleEvent> expectedPrefix() {
		return expectedPrefix;
	}

	public List<ScheduleEvent> actualPrefix() {
		return actualPrefix;
	}

	private static List<ScheduleEvent> immutableCopy(
			List<ScheduleEvent> source) {
		return Collections.unmodifiableList(
				new ArrayList<ScheduleEvent>(source));
	}
}
