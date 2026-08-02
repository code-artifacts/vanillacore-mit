package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.List;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.file.BlockId;
import org.vanilladb.core.storage.record.RecordId;
import org.vanilladb.core.storage.tx.concurrency.NativeTransactionHarness.Access;
import org.vanilladb.core.storage.tx.concurrency.NativeTransactionHarness.Lifecycle;
import org.vanilladb.core.storage.tx.concurrency.NativeTransactionHarness.WorkerOutcome;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;

public class NativeTransactionHarnessTest {

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(NativeTransactionHarnessTest.class);
	}

	@Test
	public void observesFileBlockRecordHierarchyAndStatementLifecycle() {
		try (NativeTransactionHarness harness = new NativeTransactionHarness(
				"native-hierarchy", 128, 1, false)) {
			long transactionId = 9101;
			BlockId block = new BlockId("native-hierarchy.tbl", 1);
			RecordId record = new RecordId(block, 3);
			harness.newTransaction(transactionId);
			harness.access(transactionId, block.fileName(), Access.READ);
			harness.access(transactionId, block, Access.READ);
			harness.access(transactionId, record, Access.READ);
			assertTrue(harness.lifecycle(transactionId,
					Lifecycle.END_STATEMENT).succeeded());
			assertTrue(harness.lifecycle(transactionId, Lifecycle.COMMIT).succeeded());

			List<String> resourceKinds = harness.snapshot().events().stream()
					.map(LockTraceEvent::resourceKind).filter(value -> value != null)
					.collect(Collectors.toList());
			assertTrue(resourceKinds.contains("FILE"));
			assertTrue(resourceKinds.contains("BLOCK"));
			assertTrue(resourceKinds.contains("RECORD"));
			assertTrue(harness.snapshot().isComplete());
			assertNoResidue(harness.residueSnapshot());
		}
	}

	@Test
	public void coversSharedSharedAndCommitReleaseGrant() throws Exception {
		try (NativeTransactionHarness harness = new NativeTransactionHarness(
				"native-ss-sx", 256, 2, false)) {
			BlockId shared = new BlockId("native-ss.tbl", 1);
			harness.newTransaction(9201);
			harness.newTransaction(9202);
			harness.access(9201, shared, Access.READ);
			assertTrue(harness.submitAccess(9202, shared, Access.READ)
					.get(5, TimeUnit.SECONDS).succeeded());
			assertTrue(harness.lifecycle(9201, Lifecycle.COMMIT).succeeded());
			assertTrue(harness.lifecycle(9202, Lifecycle.COMMIT).succeeded());

			BlockId conflict = new BlockId("native-sx.tbl", 2);
			harness.newTransaction(9211);
			harness.newTransaction(9212);
			harness.access(9211, conflict, Access.MODIFY);
			Future<WorkerOutcome> waiter = harness.submitAccess(9212, conflict,
					Access.READ);
			harness.awaitEvent(9212, LockTraceEventType.WAIT_BEGIN, conflict, 5,
					TimeUnit.SECONDS);
			assertTrue(harness.lifecycle(9211, Lifecycle.COMMIT).succeeded());
			assertTrue(waiter.get(5, TimeUnit.SECONDS).succeeded());
			assertTrue(harness.lifecycle(9212, Lifecycle.COMMIT).succeeded());
			assertNoResidue(harness.residueSnapshot());
		}
	}

	@Test
	public void coversExclusiveExclusiveAndRollbackGrant() throws Exception {
		try (NativeTransactionHarness harness = new NativeTransactionHarness(
				"native-xx-rollback", 256, 2, false)) {
			RecordId record = new RecordId(new BlockId("native-xx.tbl", 3), 5);
			harness.newTransaction(9301);
			harness.newTransaction(9302);
			harness.access(9301, record, Access.MODIFY);
			Future<WorkerOutcome> waiter = harness.submitAccess(9302, record,
					Access.MODIFY);
			harness.awaitEvent(9302, LockTraceEventType.WAIT_BEGIN, record, 5,
					TimeUnit.SECONDS);
			assertTrue(harness.lifecycle(9301, Lifecycle.ROLLBACK).succeeded());
			assertTrue(waiter.get(5, TimeUnit.SECONDS).succeeded());
			assertTrue(harness.lifecycle(9302, Lifecycle.COMMIT).succeeded());
			assertNoResidue(harness.residueSnapshot());
		}
	}

	@Test
	public void returnsWorkerExceptionsAndStopsWorkers() throws Exception {
		NativeTransactionHarness harness = new NativeTransactionHarness(
				"native-failure", 64, 1, false);
		try {
			harness.newTransaction(9401);
			WorkerOutcome outcome = harness.submitAccess(9401, Integer.valueOf(7),
					Access.READ).get(5, TimeUnit.SECONDS);
			assertFalse(outcome.succeeded());
			assertTrue(outcome.failure() instanceof IllegalArgumentException);
			assertEquals(9401, outcome.transactionId());
		} finally {
			harness.close();
		}
		assertEquals(0, harness.liveWorkerNames().size());
	}

	private void assertNoResidue(LockTableTestProbe.ResidueSnapshot residue) {
		assertEquals(0, residue.lockerMapEntries);
		assertEquals(0, residue.ownerReferences);
		assertEquals(0, residue.requestReferences);
		assertEquals(0, residue.transactionLockSetEntries);
		assertEquals(0, residue.waitRegistrationEntries);
		assertEquals(0, residue.abortRegistryEntries);
	}
}
