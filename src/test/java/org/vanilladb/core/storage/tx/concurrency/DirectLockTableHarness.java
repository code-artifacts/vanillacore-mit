package org.vanilladb.core.storage.tx.concurrency;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

import org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSink;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTrace;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEventType;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceSink;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceSnapshot;

public final class DirectLockTableHarness implements AutoCloseable {

	public enum LockMode {
		IS,
		IX,
		S,
		SIX,
		X
	}

	private final LockTable lockTable;
	private final AwaitableSink sink;
	private final ExecutorService workers;
	private final Set<Long> activeTransactions =
			ConcurrentHashMap.newKeySet();
	private final Set<String> workerNames = ConcurrentHashMap.newKeySet();
	private volatile boolean closed;

	public DirectLockTableHarness(String runId, int traceCapacity,
			int workerCount) {
		this(runId, traceCapacity, workerCount, false);
	}

	public DirectLockTableHarness(String runId, int traceCapacity,
			int workerCount, boolean lowMode) {
		if (workerCount <= 0)
			throw new IllegalArgumentException("workerCount must be positive");
		lockTable = new LockTable();
		sink = new AwaitableSink(runId, traceCapacity, lowMode);
		AtomicInteger sequence = new AtomicInteger();
		ThreadFactory threadFactory = task -> {
			Thread thread = new Thread(task,
					"vc-mit-direct-" + sequence.incrementAndGet());
			workerNames.add(thread.getName());
			return thread;
		};
		workers = Executors.newFixedThreadPool(workerCount, threadFactory);
		LockTrace.install(sink);
	}

	public void lock(long transactionId, Object resource, LockMode mode) {
		ensureOpen();
		activeTransactions.add(transactionId);
		switch (mode) {
		case IS:
			lockTable.isLock(resource, transactionId);
			break;
		case IX:
			lockTable.ixLock(resource, transactionId);
			break;
		case S:
			lockTable.sLock(resource, transactionId);
			break;
		case SIX:
			lockTable.sixLock(resource, transactionId);
			break;
		case X:
			lockTable.xLock(resource, transactionId);
			break;
		default:
			throw new IllegalArgumentException("unsupported mode " + mode);
		}
	}

	public Future<Void> submitLock(long transactionId, Object resource,
			LockMode mode) {
		ensureOpen();
		return workers.submit(() -> {
			lock(transactionId, resource, mode);
			return null;
		});
	}

	public void release(long transactionId, Object resource, LockMode mode) {
		ensureOpen();
		lockTable.release(resource, transactionId, lockType(mode));
	}

	public void end(long transactionId) {
		ensureOpen();
		lockTable.releaseAll(transactionId, false);
		activeTransactions.remove(transactionId);
	}

	public LockTraceEvent awaitEvent(long transactionId,
			LockTraceEventType eventType, Object resource, long timeout,
			TimeUnit unit) throws InterruptedException, TimeoutException {
		return sink.await(transactionId, eventType, String.valueOf(resource),
				timeout, unit);
	}

	public void awaitCompletion(Future<?> operation, long timeout,
			TimeUnit unit) throws Exception {
		operation.get(timeout, unit);
	}

	public LockTraceSnapshot snapshot() {
		return sink.snapshot();
	}

	public LockTableTestProbe.ResidueSnapshot residueSnapshot() {
		return LockTableTestProbe.residueSnapshot(lockTable);
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
		for (Long transactionId : new ArrayList<Long>(activeTransactions)) {
			lockTable.releaseAll(transactionId, false);
		}
		activeTransactions.clear();
		workers.shutdownNow();
		try {
			if (!workers.awaitTermination(5, TimeUnit.SECONDS))
				throw new IllegalStateException("harness workers did not stop");
		} catch (InterruptedException exception) {
			Thread.currentThread().interrupt();
			throw new IllegalStateException("interrupted while closing harness",
					exception);
		} finally {
			LockTrace.reset();
			closed = true;
		}
	}

	private int lockType(LockMode mode) {
		switch (mode) {
		case IS:
			return LockTable.IS_LOCK;
		case IX:
			return LockTable.IX_LOCK;
		case S:
			return LockTable.S_LOCK;
		case SIX:
			return LockTable.SIX_LOCK;
		case X:
			return LockTable.X_LOCK;
		default:
			throw new IllegalArgumentException("unsupported mode " + mode);
		}
	}

	private void ensureOpen() {
		if (closed)
			throw new IllegalStateException("harness is closed");
	}

	private static final class AwaitableSink implements LockTraceSink {
		private final BoundedLockTraceSink delegate;
		private final Object eventMonitor = new Object();

		private AwaitableSink(String runId, int capacity, boolean lowMode) {
			delegate = lowMode ? BoundedLockTraceSink.low(runId, capacity)
					: new BoundedLockTraceSink(runId, capacity);
		}

		@Override
		public void record(LockTraceEventType eventType, long transactionId,
				String sourceMethod, String sourceSite, String resourceKind,
				String resourceId, String requestedMode) {
			delegate.record(eventType, transactionId, sourceMethod, sourceSite,
					resourceKind, resourceId, requestedMode);
			synchronized (eventMonitor) {
				eventMonitor.notifyAll();
			}
		}

		private LockTraceEvent await(long transactionId,
				LockTraceEventType eventType, String resourceId, long timeout,
				TimeUnit unit) throws InterruptedException, TimeoutException {
			long deadline = System.nanoTime() + unit.toNanos(timeout);
			synchronized (eventMonitor) {
				while (true) {
					for (LockTraceEvent event : delegate.snapshot().events()) {
						if (event.transactionId() == transactionId
								&& event.eventType() == eventType
								&& equals(resourceId, event.resourceId()))
							return event;
					}
					long remaining = deadline - System.nanoTime();
					if (remaining <= 0)
						throw new TimeoutException("event not observed: "
								+ eventType + " tx=" + transactionId + " resource="
								+ resourceId);
					TimeUnit.NANOSECONDS.timedWait(eventMonitor, remaining);
				}
			}
		}

		private LockTraceSnapshot snapshot() {
			return delegate.snapshot();
		}

		private boolean equals(String expected, String actual) {
			return expected == null ? actual == null : expected.equals(actual);
		}
	}
}
