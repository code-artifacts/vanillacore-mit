package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.tx.concurrency.LockTableTestProbe.ResidueSnapshot;

public class LockTableStressMatrixTest {
	private static final String VARIANT = System.getProperty(
			"vanillacore.mit.stressVariant", "unspecified");
	private static final int ITERATIONS = Integer.getInteger(
			"vanillacore.mit.stressIterations", 62500);
	private static final int[] WORKERS = parseWorkers(System.getProperty(
			"vanillacore.mit.stressWorkers", "2,4,8,16"));
	private static final Path OUTPUT = Paths.get(System.getProperty(
			"vanillacore.mit.stressOutput",
			"target/mit-traces/l1-stress-matrix.csv"));

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(LockTableStressMatrixTest.class);
	}

	@Test
	public void runWorkerAndWorkloadMatrix() throws Exception {
		assertTrue("iterations must be positive", ITERATIONS > 0);
		List<Cell> cells = new ArrayList<Cell>();
		for (int workers : WORKERS) {
			cells.add(runCell(workers, "compatible"));
			cells.add(runCell(workers, "conflict"));
		}
		write(cells);
		assertEquals(WORKERS.length * 2, cells.size());
	}

	private Cell runCell(int workers, String workload) throws Exception {
		LockTable lockTable = new LockTable();
		String[] resources = resources(1, workload);
		ExecutorService executor = Executors.newFixedThreadPool(workers,
				runnable -> {
					Thread thread = new Thread(runnable,
							"week03-lock-stress-" + workers + "-" + workload);
					thread.setDaemon(true);
					return thread;
				});
		CountDownLatch start = new CountDownLatch(1);
		List<Future<WorkerResult>> futures = new ArrayList<Future<WorkerResult>>();
		int baseIterations = ITERATIONS / workers;
		int remainder = ITERATIONS % workers;
		long transactionBase = transactionBase(workers, workload);
		for (int worker = 0; worker < workers; worker++) {
			int assigned = baseIterations + (worker < remainder ? 1 : 0);
			long workerTransactionBase = transactionBase;
			futures.add(executor.submit(() -> runWorker(lockTable, start,
					resources, workload, workerTransactionBase, workers, assigned)));
			transactionBase += assigned;
		}

		long started = System.nanoTime();
		start.countDown();
		WorkerResult aggregate = new WorkerResult();
		int timedOutWorkers = 0;
		long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(120);
		for (int index = 0; index < futures.size(); index++) {
			Future<WorkerResult> future = futures.get(index);
			long remaining = deadline - System.nanoTime();
			if (remaining <= 0) {
				for (int pending = index; pending < futures.size(); pending++) {
					if (!futures.get(pending).isDone()) {
						timedOutWorkers++;
						futures.get(pending).cancel(true);
					}
				}
				break;
			}
			try {
				aggregate.add(future.get(remaining, TimeUnit.NANOSECONDS));
			} catch (TimeoutException exception) {
				timedOutWorkers++;
				future.cancel(true);
			} catch (ExecutionException exception) {
				aggregate.unexpectedErrors++;
			}
		}
		executor.shutdownNow();
		executor.awaitTermination(10, TimeUnit.SECONDS);
		long duration = System.nanoTime() - started;
		ResidueSnapshot residue = LockTableTestProbe.residueSnapshot(lockTable);
		return new Cell(VARIANT, workers, workload, ITERATIONS, duration,
				aggregate, timedOutWorkers, residue);
	}

	private WorkerResult runWorker(LockTable lockTable, CountDownLatch start,
			String[] resources, String workload, long firstTransaction,
			int workers, int iterations) {
		WorkerResult result = new WorkerResult();
		try {
			start.await();
		} catch (InterruptedException exception) {
			Thread.currentThread().interrupt();
			result.unexpectedErrors++;
			return result;
		}
		for (int iteration = 0; iteration < iterations; iteration++) {
			long transaction = firstTransaction + iteration;
			String resource = resources[(iteration * 31 + workers)
					% resources.length];
			try {
				result.acquireCalls++;
				lock(lockTable, workload, resource, transaction);
				result.firstGrants++;
				result.acquireCalls++;
				lock(lockTable, workload, resource, transaction);
				result.reentrantReturns++;
				if (LockTableTestProbe.hasWaitRegistration(lockTable,
						transaction))
					result.reentrantWaitLeakObservations++;
			} catch (LockAbortException exception) {
				result.aborts++;
			} catch (RuntimeException exception) {
				result.unexpectedErrors++;
			} finally {
				lockTable.releaseAll(transaction, false);
				result.releaseAllCalls++;
			}
		}
		return result;
	}

	private void lock(LockTable lockTable, String workload, String resource,
			long transaction) {
		if (workload.equals("compatible"))
			lockTable.sLock(resource, transaction);
		else
			lockTable.xLock(resource, transaction);
	}

	private void write(List<Cell> cells) throws Exception {
		Files.createDirectories(OUTPUT.getParent());
		try (BufferedWriter writer = Files.newBufferedWriter(OUTPUT,
				StandardCharsets.UTF_8, StandardOpenOption.CREATE,
				StandardOpenOption.TRUNCATE_EXISTING)) {
			writer.write("variant,workers,workload,iterations,lockOperations,"
					+ "acquireCalls,firstGrants,reentrantReturns,aborts,"
					+ "reentrantWaitLeakObservations,unexpectedErrors,"
					+ "timedOutWorkers,durationNanos,lockerMapEntries,"
					+ "ownerReferences,requestReferences,lockByMapEntries,"
					+ "waitMapEntries,abortRegistryEntries");
			writer.newLine();
			for (Cell cell : cells) {
				writer.write(cell.toCsv());
				writer.newLine();
			}
		}
	}

	private static int[] parseWorkers(String text) {
		String[] parts = text.split(",");
		int[] workers = new int[parts.length];
		for (int index = 0; index < parts.length; index++) {
			workers[index] = Integer.parseInt(parts[index].trim());
			if (workers[index] <= 0)
				throw new IllegalArgumentException("workers must be positive");
		}
		return workers;
	}

	private static long transactionBase(int workers, String workload) {
		long workloadOffset = workload.equals("compatible") ? 0 : 100000000L;
		return 600000000L + workloadOffset + workers * 1000000L;
	}

	private static String[] resources(int count, String workload) {
		String[] resources = new String[count];
		for (int index = 0; index < count; index++)
			resources[index] = "week03-" + workload + "-" + index;
		return resources;
	}

	private static final class WorkerResult {
		private long acquireCalls;
		private long firstGrants;
		private long reentrantReturns;
		private long aborts;
		private long reentrantWaitLeakObservations;
		private long unexpectedErrors;
		private long releaseAllCalls;

		private void add(WorkerResult other) {
			acquireCalls += other.acquireCalls;
			firstGrants += other.firstGrants;
			reentrantReturns += other.reentrantReturns;
			aborts += other.aborts;
			reentrantWaitLeakObservations += other.reentrantWaitLeakObservations;
			unexpectedErrors += other.unexpectedErrors;
			releaseAllCalls += other.releaseAllCalls;
		}
	}

	private static final class Cell {
		private final String variant;
		private final int workers;
		private final String workload;
		private final int iterations;
		private final long durationNanos;
		private final WorkerResult result;
		private final int timedOutWorkers;
		private final ResidueSnapshot residue;

		private Cell(String variant, int workers, String workload,
				int iterations, long durationNanos, WorkerResult result,
				int timedOutWorkers, ResidueSnapshot residue) {
			this.variant = variant;
			this.workers = workers;
			this.workload = workload;
			this.iterations = iterations;
			this.durationNanos = durationNanos;
			this.result = result;
			this.timedOutWorkers = timedOutWorkers;
			this.residue = residue;
		}

		private String toCsv() {
			long lockOperations = result.acquireCalls + result.releaseAllCalls;
			return variant + "," + workers + "," + workload + "," + iterations
					+ "," + lockOperations + "," + result.acquireCalls + ","
					+ result.firstGrants + "," + result.reentrantReturns + ","
					+ result.aborts + "," + result.reentrantWaitLeakObservations
					+ "," + result.unexpectedErrors + "," + timedOutWorkers + ","
					+ durationNanos + "," + residue.lockerMapEntries + ","
					+ residue.ownerReferences + "," + residue.requestReferences
					+ "," + residue.transactionLockSetEntries + ","
					+ residue.waitRegistrationEntries + ","
					+ residue.abortRegistryEntries;
		}
	}
}
