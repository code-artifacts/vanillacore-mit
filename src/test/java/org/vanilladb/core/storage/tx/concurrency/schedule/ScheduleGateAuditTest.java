package org.vanilladb.core.storage.tx.concurrency.schedule;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

import org.junit.Test;
import org.vanilladb.core.storage.tx.concurrency.schedule.ScheduleGateAudit.Safety;

public class ScheduleGateAuditTest {

	@Test
	public void allowsOnlyMonitorFreeBlockingSites() {
		assertEquals(Safety.BLOCKING_ALLOWED,
				ScheduleGateAudit.safety("locktable.s.call"));
		assertEquals(Safety.BLOCKING_ALLOWED,
				ScheduleGateAudit.safety("locktable.releaseAll.txEnd"));
		assertEquals(Safety.BLOCKING_ALLOWED,
				ScheduleGateAudit.safety("harness.transaction.commit"));
		assertEquals(Safety.OBSERVE_ONLY,
				ScheduleGateAudit.safety("locktable.s.wait"));
		assertEquals(Safety.OBSERVE_ONLY,
				ScheduleGateAudit.safety("locktable.release.x"));
	}

	@Test
	public void rejectsObserveOnlyAndUnknownBlockingGates() {
		assertRejected("locktable.x.grant", "observe-only");
		assertRejected("locktable.unknown.call", "unaudited");
	}

	private void assertRejected(String sourceSite, String message) {
		try {
			ScheduleGateAudit.requireBlockingSafe(sourceSite);
			fail("expected gate rejection for " + sourceSite);
		} catch (IllegalArgumentException exception) {
			if (!exception.getMessage().contains(message))
				throw exception;
		}
	}
}
