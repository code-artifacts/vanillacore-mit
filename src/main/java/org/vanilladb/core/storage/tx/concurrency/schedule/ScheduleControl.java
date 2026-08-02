package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.concurrent.atomic.AtomicReference;

import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;

public final class ScheduleControl {
	private static final AtomicReference<ScheduleObserver> OBSERVER =
			new AtomicReference<ScheduleObserver>();

	private ScheduleControl() {
	}

	public static boolean isEnabled() {
		return OBSERVER.get() != null;
	}

	public static void install(ScheduleObserver observer) {
		if (observer == null)
			throw new IllegalArgumentException("observer must not be null");
		if (!OBSERVER.compareAndSet(null, observer))
			throw new IllegalStateException("a schedule observer is already installed");
	}

	public static void reset() {
		OBSERVER.set(null);
	}

	public static void observeLock(LockTraceEventType eventType,
			long transactionId, String sourceSite, String resourceKind,
			String resourceId, String requestedMode) {
		ScheduleObserver observer = OBSERVER.get();
		if (observer != null)
			observer.observe(new ScheduleEvent(eventType.name(), transactionId,
					sourceSite, resourceKind, resourceId, requestedMode));
	}

	public static void observeHarness(String eventType, long transactionId,
			String sourceSite) {
		ScheduleGateAudit.requireBlockingSafe(sourceSite);
		ScheduleObserver observer = OBSERVER.get();
		if (observer != null)
			observer.observe(new ScheduleEvent(eventType, transactionId, sourceSite,
					null, null, null));
	}
}
