package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertTrue;
import static org.junit.Assume.assumeTrue;

import java.util.concurrent.ConcurrentMap;

import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;

public class LockTablePr95WitnessTest {

	@BeforeClass
	public static void requireExplicitActivation() {
		assumeTrue("Set vanillacore.mit.pr95Witnesses=true to run expected-failure witnesses",
				Boolean.getBoolean("vanillacore.mit.pr95Witnesses"));
		ServerInit.init(LockTablePr95WitnessTest.class);
	}

	@Test
	public void lockerRegistrySupportsUpdatesFromDistinctAnchors() {
		LockTable lockTable = new LockTable();
		LockResource firstResource = new LockResource(1);
		LockResource secondResource = new LockResource(2);

		assertNotSame(LockTableTestProbe.anchor(lockTable, firstResource),
				LockTableTestProbe.anchor(lockTable, secondResource));
		assertTrue("lockerMap is shared across distinct resource monitors and must be concurrent",
				LockTableTestProbe.lockerMap(lockTable) instanceof ConcurrentMap);
	}

	@Test
	public void reentrantGrantRemovesWaitRegistration() {
		LockTable lockTable = new LockTable();
		LockResource resource = new LockResource(3);
		long transactionNumber = 95;

		try {
			lockTable.sLock(resource, transactionNumber);
			assertFalse(LockTableTestProbe.hasWaitRegistration(lockTable, transactionNumber));
			lockTable.sLock(resource, transactionNumber);
			assertFalse("A reentrant grant returned without clearing txWaitMap",
					LockTableTestProbe.hasWaitRegistration(lockTable, transactionNumber));
		} finally {
			lockTable.releaseAll(transactionNumber, false);
		}
	}

	private static final class LockResource {
		private final int hashCode;

		private LockResource(int hashCode) {
			this.hashCode = hashCode;
		}

		@Override
		public int hashCode() {
			return hashCode;
		}
	}
}
