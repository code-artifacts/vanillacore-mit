package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import org.vanilladb.core.storage.tx.concurrency.schedule.ScheduleDivergence.Kind;

public final class StrictScheduleController implements ScheduleObserver {
	private final List<ScheduleEvent> expected;
	private final Set<String> ignoredSourceSites;
	private final long timeoutNanos;
	private final List<ScheduleEvent> actual = new ArrayList<ScheduleEvent>();
	private int nextIndex;
	private ScheduleDivergence divergence;

	public StrictScheduleController(List<ScheduleEvent> expected, long timeout,
			TimeUnit unit) {
		this(expected, Collections.emptySet(), timeout, unit);
	}

	public StrictScheduleController(List<ScheduleEvent> expected,
			Set<String> ignoredSourceSites, long timeout, TimeUnit unit) {
		if (expected == null || expected.isEmpty())
			throw new IllegalArgumentException("expected schedule must not be empty");
		if (timeout <= 0)
			throw new IllegalArgumentException("timeout must be positive");
		this.expected = Collections.unmodifiableList(
				new ArrayList<ScheduleEvent>(expected));
		this.ignoredSourceSites = Collections.unmodifiableSet(
				new HashSet<String>(ignoredSourceSites));
		this.timeoutNanos = unit.toNanos(timeout);
	}

	@Override
	public synchronized void observe(ScheduleEvent event) {
		Objects.requireNonNull(event, "event");
		if (ignoredSourceSites.contains(event.sourceSite()))
			return;
		throwIfDiverged();
		long deadline = System.nanoTime() + timeoutNanos;
		while (true) {
			if (nextIndex >= expected.size())
				throw fail(Kind.EXTRA_EVENT, "extra event " + event, event, null);
			ScheduleEvent next = expected.get(nextIndex);
			if (next.equals(event)) {
				actual.add(event);
				nextIndex++;
				notifyAll();
				return;
			}
			if (!expected.subList(nextIndex + 1, expected.size()).contains(event))
				throw fail(classify(next, event),
						"expected " + next + " but observed " + event, event, null);
			ScheduleGateAudit.requireBlockingSafe(event.sourceSite());
			long remaining = deadline - System.nanoTime();
			if (remaining <= 0)
				throw fail(Kind.TIMEOUT,
						"timed out before gate became enabled: " + event, event, null);
			try {
				TimeUnit.NANOSECONDS.timedWait(this, remaining);
			} catch (InterruptedException exception) {
				Thread.currentThread().interrupt();
				throw fail(Kind.HARNESS_EXCEPTION,
						"schedule gate was interrupted", event, exception);
			}
			throwIfDiverged();
		}
	}

	public synchronized void recordHarnessException(Throwable exception) {
		if (divergence == null)
			divergence = new ScheduleDivergence(Kind.HARNESS_EXCEPTION,
					"harness exception: " + exception, expectedPrefix(nextIndex),
					actual, exception);
		notifyAll();
	}

	public synchronized void assertComplete() {
		throwIfDiverged();
		if (nextIndex != expected.size())
			throw fail(Kind.MISSING_EVENT,
					"missing event " + expected.get(nextIndex), null, null);
	}

	public synchronized List<ScheduleEvent> actualLinearization() {
		return Collections.unmodifiableList(
				new ArrayList<ScheduleEvent>(actual));
	}

	public synchronized void awaitObserved(ScheduleEvent event, long timeout,
			TimeUnit unit) throws InterruptedException {
		long deadline = System.nanoTime() + unit.toNanos(timeout);
		while (!actual.contains(event)) {
			throwIfDiverged();
			long remaining = deadline - System.nanoTime();
			if (remaining <= 0)
				throw new ScheduleDivergence(Kind.TIMEOUT,
						"event was not observed before harness timeout: " + event,
						expectedPrefix(nextIndex), actual, null);
			TimeUnit.NANOSECONDS.timedWait(this, remaining);
		}
	}

	private Kind classify(ScheduleEvent expectedEvent, ScheduleEvent actualEvent) {
		if (!expectedEvent.eventType().equals(actualEvent.eventType()))
			return Kind.WRONG_EVENT;
		if (!expectedEvent.sourceSite().equals(actualEvent.sourceSite()))
			return Kind.WRONG_SOURCE_SITE;
		if (expectedEvent.transactionId() != actualEvent.transactionId())
			return Kind.WRONG_TRANSACTION;
		if (!Objects.equals(expectedEvent.resourceId(), actualEvent.resourceId())
				|| !Objects.equals(expectedEvent.resourceKind(), actualEvent.resourceKind()))
			return Kind.WRONG_RESOURCE;
		return Kind.WRONG_MODE;
	}

	private ScheduleDivergence fail(Kind kind, String message,
			ScheduleEvent attempted, Throwable cause) {
		List<ScheduleEvent> actualPrefix = new ArrayList<ScheduleEvent>(actual);
		if (attempted != null)
			actualPrefix.add(attempted);
		divergence = new ScheduleDivergence(kind, message,
				expectedPrefix(nextIndex), actualPrefix, cause);
		notifyAll();
		return divergence;
	}

	private List<ScheduleEvent> expectedPrefix(int index) {
		return expected.subList(0, Math.min(index + 1, expected.size()));
	}

	private void throwIfDiverged() {
		if (divergence != null)
			throw divergence;
	}
}
