package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.fail;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import org.junit.Ignore;
import org.junit.Test;
import org.vanilladb.core.storage.file.BlockId;

@Ignore("VCMIT-001 requires a deterministic waiter and abort-state probe")
public class LockTableDeadlockTest {

	@Test(timeout = 5000)
	public void olderRequesterAbortsYoungerHolderAndContinuesAfterRelease() throws Exception {
		LockTable lockTable = new LockTable();
		BlockId firstResource = new BlockId("_deadlock_skeleton.0", 1);
		BlockId secondResource = new BlockId("_deadlock_skeleton.0", 2);
		long olderTransaction = 40;
		long youngerTransaction = 41;
		ExecutorService executor = Executors.newSingleThreadExecutor();

		lockTable.xLock(firstResource, olderTransaction);
		lockTable.xLock(secondResource, youngerTransaction);
		Future<Void> olderRequest = executor.submit(() -> {
			lockTable.xLock(secondResource, olderTransaction);
			return null;
		});

		try {
			awaitOlderWaitAndYoungerAbortMark(lockTable, secondResource, olderTransaction, youngerTransaction);
			try {
				lockTable.xLock(firstResource, youngerTransaction);
				fail("The marked younger transaction acquired the conflicting lock");
			} catch (LockAbortException expected) {
				lockTable.releaseAll(youngerTransaction, false);
			}
			olderRequest.get(2, TimeUnit.SECONDS);
		} finally {
			olderRequest.cancel(true);
			executor.shutdownNow();
			lockTable.releaseAll(olderTransaction, false);
			lockTable.releaseAll(youngerTransaction, false);
		}
	}

	private void awaitOlderWaitAndYoungerAbortMark(LockTable lockTable, Object resource,
			long olderTransaction, long youngerTransaction) {
		throw new UnsupportedOperationException("VCMIT-001 deterministic state probe is not implemented");
	}
}
