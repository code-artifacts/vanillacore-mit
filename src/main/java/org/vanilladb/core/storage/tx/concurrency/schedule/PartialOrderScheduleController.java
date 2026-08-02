package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import org.vanilladb.core.storage.tx.concurrency.schedule.ScheduleDivergence.Kind;

public final class PartialOrderScheduleController implements ScheduleObserver {
	private final Map<String, ScheduleNode> nodes;
	private final Map<String, Set<String>> predecessors;
	private final Set<String> completed = new HashSet<String>();
	private final List<String> actualLinearization = new ArrayList<String>();
	private final List<ScheduleEvent> actualEvents = new ArrayList<ScheduleEvent>();
	private final long seed;
	private final long timeoutNanos;

	public PartialOrderScheduleController(Collection<ScheduleNode> nodes,
			Collection<ScheduleEdge> edges, long seed, long timeout, TimeUnit unit) {
		if (nodes == null || nodes.isEmpty())
			throw new IllegalArgumentException("nodes must not be empty");
		if (timeout <= 0)
			throw new IllegalArgumentException("timeout must be positive");
		this.nodes = new LinkedHashMap<String, ScheduleNode>();
		this.predecessors = new HashMap<String, Set<String>>();
		for (ScheduleNode node : nodes) {
			if (this.nodes.put(node.id(), node) != null)
				throw new IllegalArgumentException("duplicate schedule node: " + node.id());
			predecessors.put(node.id(), new HashSet<String>());
		}
		for (ScheduleEdge edge : edges) {
			if (!this.nodes.containsKey(edge.before())
					|| !this.nodes.containsKey(edge.after()))
				throw new IllegalArgumentException("edge references unknown node: "
						+ edge.before() + " -> " + edge.after());
			predecessors.get(edge.after()).add(edge.before());
		}
		verifyAcyclic(edges);
		this.seed = seed;
		this.timeoutNanos = unit.toNanos(timeout);
	}

	@Override
	public synchronized void observe(ScheduleEvent event) {
		long deadline = System.nanoTime() + timeoutNanos;
		while (true) {
			List<ScheduleNode> matching = matchingUnfinished(event);
			if (matching.isEmpty())
				throw divergence(Kind.EXTRA_EVENT, "event has no unfinished DAG node", event);
			List<ScheduleNode> enabled = new ArrayList<ScheduleNode>();
			for (ScheduleNode node : matching)
				if (completed.containsAll(predecessors.get(node.id())))
					enabled.add(node);
			if (!enabled.isEmpty()) {
				enabled.sort((left, right) -> left.id().compareTo(right.id()));
				int selected = (int) Math.floorMod(seed + actualLinearization.size(),
						enabled.size());
				ScheduleNode node = enabled.get(selected);
				completed.add(node.id());
				actualLinearization.add(node.id());
				actualEvents.add(event);
				notifyAll();
				return;
			}
			ScheduleGateAudit.requireBlockingSafe(event.sourceSite());
			long remaining = deadline - System.nanoTime();
			if (remaining <= 0)
				throw divergence(Kind.TIMEOUT,
						"DAG predecessors were not satisfied", event);
			try {
				TimeUnit.NANOSECONDS.timedWait(this, remaining);
			} catch (InterruptedException exception) {
				Thread.currentThread().interrupt();
				throw new ScheduleDivergence(Kind.HARNESS_EXCEPTION,
						"partial-order gate was interrupted", expectedPrefix(),
						actualEvents, exception);
			}
		}
	}

	public synchronized void assertComplete() {
		if (completed.size() != nodes.size())
			throw new ScheduleDivergence(Kind.MISSING_EVENT,
					"unfinished DAG nodes: " + unfinishedIds(), expectedPrefix(),
					actualEvents, null);
	}

	public synchronized List<String> actualLinearization() {
		return Collections.unmodifiableList(new ArrayList<String>(actualLinearization));
	}

	public long seed() {
		return seed;
	}

	private List<ScheduleNode> matchingUnfinished(ScheduleEvent event) {
		List<ScheduleNode> matching = new ArrayList<ScheduleNode>();
		for (ScheduleNode node : nodes.values())
			if (!completed.contains(node.id()) && node.event().equals(event))
				matching.add(node);
		return matching;
	}

	private void verifyAcyclic(Collection<ScheduleEdge> edges) {
		Map<String, Integer> indegree = new HashMap<String, Integer>();
		Map<String, List<String>> successors = new HashMap<String, List<String>>();
		for (String id : nodes.keySet()) {
			indegree.put(id, 0);
			successors.put(id, new ArrayList<String>());
		}
		for (ScheduleEdge edge : edges) {
			indegree.put(edge.after(), indegree.get(edge.after()) + 1);
			successors.get(edge.before()).add(edge.after());
		}
		ArrayDeque<String> ready = new ArrayDeque<String>();
		for (Map.Entry<String, Integer> entry : indegree.entrySet())
			if (entry.getValue() == 0)
				ready.add(entry.getKey());
		int visited = 0;
		while (!ready.isEmpty()) {
			String current = ready.remove();
			visited++;
			for (String successor : successors.get(current)) {
				int remaining = indegree.get(successor) - 1;
				indegree.put(successor, remaining);
				if (remaining == 0)
					ready.add(successor);
			}
		}
		if (visited != nodes.size())
			throw new IllegalArgumentException("schedule edges contain a cycle");
	}

	private List<String> unfinishedIds() {
		List<String> unfinished = new ArrayList<String>();
		for (String id : nodes.keySet())
			if (!completed.contains(id))
				unfinished.add(id);
		return unfinished;
	}

	private List<ScheduleEvent> expectedPrefix() {
		List<ScheduleEvent> prefix = new ArrayList<ScheduleEvent>();
		for (String id : actualLinearization)
			prefix.add(nodes.get(id).event());
		for (String id : unfinishedIds()) {
			prefix.add(nodes.get(id).event());
			break;
		}
		return prefix;
	}

	private ScheduleDivergence divergence(Kind kind, String message,
			ScheduleEvent attempted) {
		List<ScheduleEvent> prefix = new ArrayList<ScheduleEvent>(actualEvents);
		prefix.add(attempted);
		return new ScheduleDivergence(kind, message, expectedPrefix(), prefix, null);
	}
}
