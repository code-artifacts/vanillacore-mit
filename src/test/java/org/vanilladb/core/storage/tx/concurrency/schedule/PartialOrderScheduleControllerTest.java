package org.vanilladb.core.storage.tx.concurrency.schedule;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.Arrays;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

import org.junit.Test;

public class PartialOrderScheduleControllerTest {

	@Test
	public void acceptsBothLegalIndependentLinearizations() {
		ScheduleNode first = node("a", 8101);
		ScheduleNode second = node("b", 8102);
		ScheduleNode join = node("c", 8103);
		ScheduleEdge firstJoin = edge("a", "c");
		ScheduleEdge secondJoin = edge("b", "c");

		PartialOrderScheduleController ab = controller(first, second, join,
				firstJoin, secondJoin);
		ab.observe(first.event());
		ab.observe(second.event());
		ab.observe(join.event());
		ab.assertComplete();
		assertEquals(Arrays.asList("a", "b", "c"), ab.actualLinearization());

		PartialOrderScheduleController ba = controller(first, second, join,
				firstJoin, secondJoin);
		ba.observe(second.event());
		ba.observe(first.event());
		ba.observe(join.event());
		ba.assertComplete();
		assertEquals(Arrays.asList("b", "a", "c"), ba.actualLinearization());
	}

	@Test
	public void blocksSafeNodeUntilPredecessorCompletes() throws Exception {
		ScheduleNode first = node("a", 8201);
		ScheduleNode second = node("b", 8202);
		PartialOrderScheduleController controller = new PartialOrderScheduleController(
				Arrays.asList(first, second), Arrays.asList(edge("a", "b")), 11,
				5, TimeUnit.SECONDS);
		Thread later = new Thread(() -> controller.observe(second.event()),
				"partial-order-later");
		later.start();
		Thread.sleep(25);
		assertTrue(later.isAlive());
		controller.observe(first.event());
		later.join(1000);
		controller.assertComplete();
	}

	@Test
	public void rejectsCyclesAndUnknownEdges() {
		ScheduleNode first = node("a", 8301);
		ScheduleNode second = node("b", 8302);
		assertRejected(() -> new PartialOrderScheduleController(
				Arrays.asList(first, second),
				Arrays.asList(edge("a", "b"), edge("b", "a")), 1, 1,
				TimeUnit.SECONDS), "cycle");
		assertRejected(() -> new PartialOrderScheduleController(
				Arrays.asList(first, second), Arrays.asList(edge("missing", "b")),
				1, 1, TimeUnit.SECONDS), "unknown node");
	}

	private PartialOrderScheduleController controller(ScheduleNode first,
			ScheduleNode second, ScheduleNode join, ScheduleEdge firstJoin,
			ScheduleEdge secondJoin) {
		return new PartialOrderScheduleController(Arrays.asList(first, second, join),
				Arrays.asList(firstJoin, secondJoin), 20260802, 1,
				TimeUnit.SECONDS);
	}

	private ScheduleNode node(String id, long transactionId) {
		return new ScheduleNode(id, new ScheduleEvent("LOCK_CALL", transactionId,
				"locktable.s.call", "FILE", "partial-r", "S"));
	}

	private ScheduleEdge edge(String before, String after) {
		return new ScheduleEdge(before, after, "FIXTURE_CAUSALITY");
	}

	private void assertRejected(Runnable action, String message) {
		try {
			action.run();
			fail("expected rejection");
		} catch (IllegalArgumentException exception) {
			assertTrue(exception.getMessage().contains(message));
		}
	}
}
