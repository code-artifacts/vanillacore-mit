package org.vanilladb.core.storage.tx.concurrency;

import java.sql.Connection;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

import org.vanilladb.core.server.VanillaDb;
import org.vanilladb.core.storage.file.BlockId;
import org.vanilladb.core.storage.record.RecordId;
import org.vanilladb.core.storage.tx.Transaction;
import org.vanilladb.core.storage.tx.concurrency.schedule.ScheduleControl;
import org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSink;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTrace;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceSnapshot;

public final class NativeTransactionHarness implements AutoCloseable {

	public enum Access {
		READ,
		MODIFY
	}

	public enum Lifecycle {
		COMMIT,
		ROLLBACK,
		END_STATEMENT
	}

	public static final class WorkerOutcome {
		private final long transactionId;
		private final String operation;
		private final Throwable failure;

		private WorkerOutcome(long transactionId, String operation,
				Throwable failure) {
			this.transactionId = transactionId;
			this.operation = operation;
			this.failure = failure;
		}

		public long transactionId() {
			return transactionId;
		}

		public String operation() {
			return operation;
		}

		public boolean succeeded() {
			return failure == null;
		}

		public Throwable failure() {
			return failure;
		}
	}

	private final BoundedLockTraceSink sink;
	private final ExecutorService workers;
	private final Map<Long, Transaction> transactions =
			new ConcurrentHashMap<Long, Transaction>();
	private final Set<String> workerNames = ConcurrentHashMap.newKeySet();
	private volatile boolean closed;

	public NativeTransactionHarness(String runId, int traceCapacity,
			int workerCount, boolean lowMode) {
		if (workerCount <= 0)
			throw new IllegalArgumentException("workerCount must be positive");
		sink = lowMode ? BoundedLockTraceSink.low(runId, traceCapacity)
				: new BoundedLockTraceSink(runId, traceCapacity);
		AtomicInteger sequence = new AtomicInteger();
		ThreadFactory threadFactory = task -> {
			Thread thread = new Thread(task,
					"vc-mit-native-" + sequence.incrementAndGet());
			workerNames.add(thread.getName());
			return thread;
		};
		workers = Executors.newFixedThreadPool(workerCount, threadFactory);
		LockTrace.install(sink);
	}

	public Transaction newTransaction(long transactionId) {
		ensureOpen();
		Transaction transaction = VanillaDb.txMgr().newTransaction(
				Connection.TRANSACTION_SERIALIZABLE, false, transactionId);
		if (transactions.putIfAbsent(transactionId, transaction) != null)
			throw new IllegalArgumentException(
					"duplicate transaction id " + transactionId);
		return transaction;
	}

	public void access(long transactionId, Object resource, Access access) {
		ensureOpen();
		Transaction transaction = requireTransaction(transactionId);
		ConcurrencyMgr concurrency = transaction.concurrencyMgr();
		if (resource instanceof String) {
			if (access == Access.READ)
				concurrency.readFile((String) resource);
			else
				concurrency.modifyFile((String) resource);
		} else if (resource instanceof BlockId) {
			if (access == Access.READ)
				concurrency.readBlock((BlockId) resource);
			else
				concurrency.modifyBlock((BlockId) resource);
		} else if (resource instanceof RecordId) {
			if (access == Access.READ)
				concurrency.readRecord((RecordId) resource);
			else
				concurrency.modifyRecord((RecordId) resource);
		} else {
			throw new IllegalArgumentException(
					"unsupported native resource " + resource);
		}
	}

	public Future<WorkerOutcome> submitAccess(long transactionId,
			Object resource, Access access) {
		return workers.submit(() -> capture(transactionId,
				access.name() + " " + resource,
				() -> access(transactionId, resource, access)));
	}

	public WorkerOutcome lifecycle(long transactionId, Lifecycle lifecycle) {
		return capture(transactionId, lifecycle.name(), () -> {
			Transaction transaction = requireTransaction(transactionId);
			ScheduleControl.observeHarness("HARNESS_OPERATION", transactionId,
					lifecycleSourceSite(lifecycle));
			switch (lifecycle) {
			case COMMIT:
				transaction.commit();
				transactions.remove(transactionId);
				break;
			case ROLLBACK:
				transaction.rollback();
				transactions.remove(transactionId);
				break;
			case END_STATEMENT:
				transaction.endStatement();
				break;
			default:
				throw new IllegalArgumentException("unsupported lifecycle " + lifecycle);
			}
		});
	}

	public Future<WorkerOutcome> submitLifecycle(long transactionId,
			Lifecycle lifecycle) {
		return workers.submit(() -> lifecycle(transactionId, lifecycle));
	}

	public LockTraceEvent awaitEvent(long transactionId,
			LockTraceEventType eventType, Object resource, long timeout,
			TimeUnit unit) throws InterruptedException, TimeoutException {
		String resourceId = resource == null ? null : String.valueOf(resource);
		long deadline = System.nanoTime() + unit.toNanos(timeout);
		while (true) {
			for (LockTraceEvent event : sink.snapshot().events())
				if (event.transactionId() == transactionId
						&& event.eventType() == eventType
						&& equals(resourceId, event.resourceId()))
					return event;
			long remaining = deadline - System.nanoTime();
			if (remaining <= 0)
				throw new TimeoutException("native event not observed: " + eventType
						+ " tx=" + transactionId + " resource=" + resourceId);
			TimeUnit.NANOSECONDS.sleep(Math.min(remaining,
					TimeUnit.MILLISECONDS.toNanos(5)));
		}
	}

	public LockTraceSnapshot snapshot() {
		return sink.snapshot();
	}

	public LockTableTestProbe.ResidueSnapshot residueSnapshot() {
		return LockTableTestProbe.residueSnapshot(ConcurrencyMgr.lockTbl);
	}

	public List<String> liveWorkerNames() {
		List<String> live = new ArrayList<String>();
		for (Thread thread : Thread.getAllStackTraces().keySet())
			if (thread.isAlive() && workerNames.contains(thread.getName()))
				live.add(thread.getName());
		Collections.sort(live);
		return live;
	}

	@Override
	public void close() {
		if (closed)
			return;
		for (Map.Entry<Long, Transaction> entry :
				new ArrayList<Map.Entry<Long, Transaction>>(transactions.entrySet())) {
			entry.getValue().rollback();
			transactions.remove(entry.getKey());
		}
		workers.shutdownNow();
		try {
			if (!workers.awaitTermination(5, TimeUnit.SECONDS))
				throw new IllegalStateException("native harness workers did not stop");
		} catch (InterruptedException exception) {
			Thread.currentThread().interrupt();
			throw new IllegalStateException(
					"interrupted while closing native harness", exception);
		} finally {
			LockTrace.reset();
			closed = true;
		}
	}

	private WorkerOutcome capture(long transactionId, String operation,
			Runnable action) {
		try {
			action.run();
			return new WorkerOutcome(transactionId, operation, null);
		} catch (Throwable failure) {
			return new WorkerOutcome(transactionId, operation, failure);
		}
	}

	private Transaction requireTransaction(long transactionId) {
		Transaction transaction = transactions.get(transactionId);
		if (transaction == null)
			throw new IllegalArgumentException(
					"unknown transaction " + transactionId);
		return transaction;
	}

	private void ensureOpen() {
		if (closed)
			throw new IllegalStateException("native harness is closed");
	}

	private boolean equals(String expected, String actual) {
		return expected == null ? actual == null : expected.equals(actual);
	}

	private String lifecycleSourceSite(Lifecycle lifecycle) {
		switch (lifecycle) {
		case COMMIT:
			return "harness.transaction.commit";
		case ROLLBACK:
			return "harness.transaction.rollback";
		case END_STATEMENT:
			return "harness.transaction.endStatement";
		default:
			throw new IllegalArgumentException("unsupported lifecycle " + lifecycle);
		}
	}
}
