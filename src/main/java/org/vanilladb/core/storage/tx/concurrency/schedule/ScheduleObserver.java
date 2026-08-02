package org.vanilladb.core.storage.tx.concurrency.schedule;

public interface ScheduleObserver {
	void observe(ScheduleEvent event);
}
