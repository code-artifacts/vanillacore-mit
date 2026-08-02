package org.vanilladb.core.storage.tx.concurrency;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;

final class L1TraceProjection {

	static final class Result {
		private final List<String> actions;
		private final List<String> contextEvents;

		private Result(List<String> actions, List<String> contextEvents) {
			this.actions = Collections.unmodifiableList(actions);
			this.contextEvents = Collections.unmodifiableList(contextEvents);
		}

		List<String> actions() {
			return actions;
		}

		List<String> contextEvents() {
			return contextEvents;
		}
	}

	private L1TraceProjection() {
	}

	static Result project(List<LockTraceEvent> events, String focusResourceId,
			String logicalResource, Map<Long, String> terminalActions) {
		List<String> actions = new ArrayList<String>();
		List<String> context = new ArrayList<String>();
		Map<Long, String> heldMode = new HashMap<Long, String>();
		Set<Long> waited = new HashSet<Long>();
		Set<Long> projectedTerminals = new HashSet<Long>();
		boolean terminalReleaseObserved = false;
		for (LockTraceEvent event : events) {
			if (event.eventType() == LockTraceEventType.RELEASE
					&& terminalActions.containsKey(event.transactionId())
					&& projectedTerminals.add(event.transactionId())) {
				actions.add(action(terminalActions.get(event.transactionId()),
						event.transactionId(), "NO_RESOURCE", "NONE"));
				actions.add(action("RELEASE_ALL", event.transactionId(),
						"NO_RESOURCE", "NONE"));
				terminalReleaseObserved = true;
			}
			if (event.eventType() == LockTraceEventType.TX_END) {
				if (projectedTerminals.add(event.transactionId())) {
					String terminal = terminalActions.get(event.transactionId());
					if (terminal != null)
						actions.add(action(terminal, event.transactionId(),
								"NO_RESOURCE", "NONE"));
					actions.add(action("RELEASE_ALL", event.transactionId(),
							"NO_RESOURCE", "NONE"));
					terminalReleaseObserved = true;
				}
				continue;
			}
			if (!focusResourceId.equals(event.resourceId())) {
				if (event.resourceId() != null)
					context.add(event.eventType().name() + ":" + event.resourceKind()
							+ ":" + event.resourceId() + ":" + event.requestedMode());
				continue;
			}
			switch (event.eventType()) {
			case LOCK_CALL:
				String request = "S".equals(event.requestedMode()) ? "REQUEST_S"
						: "S".equals(heldMode.get(event.transactionId()))
								? "UPGRADE_REQUEST" : "REQUEST_X";
				actions.add(action(request, event.transactionId(), logicalResource,
						event.requestedMode()));
				break;
			case WAIT_BEGIN:
				waited.add(event.transactionId());
				actions.add(action("WAIT", event.transactionId(), logicalResource,
						event.requestedMode()));
				break;
			case GRANT:
				if (waited.remove(event.transactionId()) && terminalReleaseObserved)
					actions.add(action("WAKE", event.transactionId(), logicalResource,
							event.requestedMode()));
				actions.add(action("GRANT", event.transactionId(), logicalResource,
						event.requestedMode()));
				heldMode.put(event.transactionId(), event.requestedMode());
				break;
			case RELEASE:
				break;
			default:
				throw new IllegalArgumentException(
						"unsupported focus event " + event.eventType());
			}
		}
		return new Result(actions, context);
	}

	private static String action(String action, long transactionId,
			String resource, String mode) {
		return action + "(t" + transactionId + "," + resource + "," + mode + ")";
	}
}
