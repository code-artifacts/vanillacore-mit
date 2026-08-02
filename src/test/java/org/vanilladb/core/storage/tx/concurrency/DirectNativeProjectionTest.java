package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.file.BlockId;
import org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarness.LockMode;
import org.vanilladb.core.storage.tx.concurrency.NativeTransactionHarness.Access;
import org.vanilladb.core.storage.tx.concurrency.NativeTransactionHarness.Lifecycle;
import org.vanilladb.core.storage.tx.concurrency.NativeTransactionHarness.WorkerOutcome;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;

public class DirectNativeProjectionTest {

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(DirectNativeProjectionTest.class);
	}

	@Test
	public void sharedSharedProjectsToSameL1Actions() throws Exception {
		assertPrefixProjection("projection-ss", LockMode.S, Access.READ,
				LockMode.S, Access.READ);
	}

	@Test
	public void sharedExclusiveAndExclusiveExclusiveProjectToSameL1Actions()
			throws Exception {
		assertPrefixProjection("projection-sx", LockMode.S, Access.READ,
				LockMode.X, Access.MODIFY);
		assertPrefixProjection("projection-xx", LockMode.X, Access.MODIFY,
				LockMode.X, Access.MODIFY);
	}

	@Test
	public void commitReleaseWakeGrantProjectsToSameL1Actions()
			throws Exception {
		assertTerminalProjection("projection-commit", "COMMIT", Lifecycle.COMMIT);
	}

	@Test
	public void rollbackReleaseWakeGrantProjectsToSameL1Actions()
			throws Exception {
		assertTerminalProjection("projection-rollback", "ROLLBACK",
				Lifecycle.ROLLBACK);
	}

	private void assertPrefixProjection(String name, LockMode directFirst,
			Access nativeFirst, LockMode directSecond, Access nativeSecond)
			throws Exception {
		long first = 10101;
		long second = 10102;
		String directResource = name;
		L1TraceProjection.Result direct;
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				name + "-direct", 64, 1)) {
			harness.lock(first, directResource, directFirst);
			Future<Void> operation = harness.submitLock(second, directResource,
					directSecond);
			if (directFirst == LockMode.S && directSecond == LockMode.S)
				harness.awaitCompletion(operation, 5, TimeUnit.SECONDS);
			else
				harness.awaitEvent(second, LockTraceEventType.WAIT_BEGIN,
						directResource, 5, TimeUnit.SECONDS);
			direct = L1TraceProjection.project(harness.snapshot().events(),
					directResource, "r1", Collections.emptyMap());
			harness.end(first);
			harness.awaitCompletion(operation, 5, TimeUnit.SECONDS);
			harness.end(second);
		}

		BlockId nativeResource = new BlockId(name, 1);
		L1TraceProjection.Result nativeResult;
		try (NativeTransactionHarness harness = new NativeTransactionHarness(
				name + "-native", 128, 1, false)) {
			harness.newTransaction(first);
			harness.newTransaction(second);
			harness.access(first, nativeResource, nativeFirst);
			Future<WorkerOutcome> operation = harness.submitAccess(second,
					nativeResource, nativeSecond);
			if (nativeFirst == Access.READ && nativeSecond == Access.READ)
				operation.get(5, TimeUnit.SECONDS);
			else
				harness.awaitEvent(second, LockTraceEventType.WAIT_BEGIN,
						nativeResource, 5, TimeUnit.SECONDS);
			nativeResult = L1TraceProjection.project(harness.snapshot().events(),
					nativeResource.toString(), "r1", Collections.emptyMap());
			harness.lifecycle(first, Lifecycle.COMMIT);
			operation.get(5, TimeUnit.SECONDS);
			harness.lifecycle(second, Lifecycle.COMMIT);
		}
		assertEquals(direct.actions(), nativeResult.actions());
		assertFalse(nativeResult.contextEvents().isEmpty());
	}

	private void assertTerminalProjection(String name, String terminalAction,
			Lifecycle nativeLifecycle) throws Exception {
		long holder = 10201;
		long waiter = 10202;
		Map<Long, String> terminal = new HashMap<Long, String>();
		terminal.put(holder, terminalAction);
		L1TraceProjection.Result direct;
		try (DirectLockTableHarness harness = new DirectLockTableHarness(
				name + "-direct", 64, 1)) {
			harness.lock(holder, name, LockMode.X);
			Future<Void> waiting = harness.submitLock(waiter, name, LockMode.S);
			harness.awaitEvent(waiter, LockTraceEventType.WAIT_BEGIN, name, 5,
					TimeUnit.SECONDS);
			harness.end(holder);
			harness.awaitCompletion(waiting, 5, TimeUnit.SECONDS);
			direct = L1TraceProjection.project(harness.snapshot().events(), name,
					"r1", terminal);
			harness.end(waiter);
		}

		BlockId resource = new BlockId(name, 1);
		L1TraceProjection.Result nativeResult;
		try (NativeTransactionHarness harness = new NativeTransactionHarness(
				name + "-native", 128, 1, false)) {
			harness.newTransaction(holder);
			harness.newTransaction(waiter);
			harness.access(holder, resource, Access.MODIFY);
			Future<WorkerOutcome> waiting = harness.submitAccess(waiter, resource,
					Access.READ);
			harness.awaitEvent(waiter, LockTraceEventType.WAIT_BEGIN, resource, 5,
					TimeUnit.SECONDS);
			harness.lifecycle(holder, nativeLifecycle);
			waiting.get(5, TimeUnit.SECONDS);
			nativeResult = L1TraceProjection.project(harness.snapshot().events(),
					resource.toString(), "r1", terminal);
			harness.lifecycle(waiter, Lifecycle.COMMIT);
		}
		assertEquals(direct.actions(), nativeResult.actions());
		assertFalse(nativeResult.contextEvents().isEmpty());
	}
}
