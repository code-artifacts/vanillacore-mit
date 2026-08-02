package org.vanilladb.core.storage.tx.concurrency.schedule;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public final class ScheduleGateAudit {

	public enum Safety {
		BLOCKING_ALLOWED,
		OBSERVE_ONLY
	}

	private static final Map<String, Safety> POINTS;

	static {
		Map<String, Safety> points = new HashMap<String, Safety>();
		for (String mode : new String[] { "is", "ix", "s", "six", "x" }) {
			points.put("locktable." + mode + ".call", Safety.BLOCKING_ALLOWED);
			points.put("locktable." + mode + ".wait", Safety.OBSERVE_ONLY);
			points.put("locktable." + mode + ".grant", Safety.OBSERVE_ONLY);
			points.put("locktable.release." + mode, Safety.OBSERVE_ONLY);
			points.put("locktable.releaseAll." + mode, Safety.OBSERVE_ONLY);
		}
		points.put("locktable.releaseAll.txEnd", Safety.BLOCKING_ALLOWED);
		points.put("harness.transaction.commit", Safety.BLOCKING_ALLOWED);
		points.put("harness.transaction.rollback", Safety.BLOCKING_ALLOWED);
		points.put("harness.transaction.endStatement", Safety.BLOCKING_ALLOWED);
		points.put("harness.barrier", Safety.BLOCKING_ALLOWED);
		POINTS = Collections.unmodifiableMap(points);
	}

	private ScheduleGateAudit() {
	}

	public static Safety safety(String sourceSite) {
		Safety safety = POINTS.get(sourceSite);
		if (safety == null)
			throw new IllegalArgumentException(
					"unaudited schedule gate: " + sourceSite);
		return safety;
	}

	public static void requireBlockingSafe(String sourceSite) {
		if (safety(sourceSite) != Safety.BLOCKING_ALLOWED)
			throw new IllegalArgumentException(
					"schedule gate may not block at audited observe-only site: "
							+ sourceSite);
	}

	public static Map<String, Safety> points() {
		return POINTS;
	}
}
