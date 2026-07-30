package org.vanilladb.core.storage.tx.concurrency;

import static org.junit.Assert.assertEquals;

import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;

import org.junit.After;
import org.junit.BeforeClass;
import org.junit.Test;
import org.vanilladb.core.server.ServerInit;
import org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSink;
import org.vanilladb.core.storage.tx.concurrency.trace.LockTrace;

public class LockTraceOverheadBenchmarkTest {
	private static final String MODE = System.getProperty(
			"vanillacore.mit.benchmarkMode", "off");
	private static final int OPERATIONS = Integer.getInteger(
			"vanillacore.mit.operations", 100000);
	private static final int SAMPLES = Integer.getInteger(
			"vanillacore.mit.samples", 5);
	private static final int WARMUP_OPERATIONS = Integer.getInteger(
			"vanillacore.mit.warmupOperations", 20000);
	private static final Path OUTPUT = Paths.get(System.getProperty(
			"vanillacore.mit.benchmarkOutput",
			"target/mit-traces/lock-trace-overhead.csv"));

	@BeforeClass
	public static void initializeServer() {
		ServerInit.init(LockTraceOverheadBenchmarkTest.class);
	}

	@After
	public void resetSink() {
		LockTrace.reset();
	}

	@Test
	public void measureLockTraceMode() throws Exception {
		if (!MODE.equals("off") && !MODE.equals("low"))
			throw new IllegalArgumentException("unsupported mode " + MODE);
		if (OPERATIONS <= 0 || SAMPLES <= 0 || WARMUP_OPERATIONS < 0)
			throw new IllegalArgumentException("invalid benchmark dimensions");

		LockTable lockTable = new LockTable();
		String[] resources = resources(100);
		run(lockTable, resources, 500000, WARMUP_OPERATIONS, false);
		List<Sample> samples = new ArrayList<Sample>();
		for (int sample = 0; sample < SAMPLES; sample++) {
			samples.add(run(lockTable, resources, 510000 + sample, OPERATIONS,
					true));
		}
		write(samples);
	}

	private Sample run(LockTable lockTable, String[] resources,
			long transactionId, int operations, boolean measured) {
		BoundedLockTraceSink sink = null;
		if (MODE.equals("low")) {
			sink = BoundedLockTraceSink.low(
					"overhead-" + transactionId, operations * 2 + 1);
			LockTrace.install(sink);
		}

		long start = System.nanoTime();
		for (int operation = 0; operation < operations; operation++) {
			String resource = resources[operation % resources.length];
			lockTable.sLock(resource, transactionId);
			lockTable.release(resource, transactionId, LockTable.S_LOCK);
		}
		lockTable.releaseAll(transactionId, false);
		long duration = System.nanoTime() - start;

		long events = sink == null ? 0 : sink.recordedEvents();
		long dropped = sink == null ? 0 : sink.droppedEvents();
		if (sink != null) {
			assertEquals((long) operations * 2 + 1, events);
			assertEquals(0, dropped);
			LockTrace.reset();
		}
		assertEquals(0, LockTableTestProbe.lockerCount(lockTable));
		assertEquals(0, LockTableTestProbe.transactionLockSetCount(lockTable));
		assertEquals(0, LockTableTestProbe.waitRegistrationCount(lockTable));
		return measured ? new Sample(operations, duration, events, dropped) : null;
	}

	private void write(List<Sample> samples) throws Exception {
		Files.createDirectories(OUTPUT.getParent());
		try (BufferedWriter writer = Files.newBufferedWriter(OUTPUT,
				StandardCharsets.UTF_8, StandardOpenOption.CREATE,
				StandardOpenOption.TRUNCATE_EXISTING)) {
			writer.write("mode,sample,operations,durationNanos,events,dropped,"
					+ "lockerMapSize,lockByMapSize,waitMapSize");
			writer.newLine();
			for (int index = 0; index < samples.size(); index++) {
				Sample sample = samples.get(index);
				writer.write(MODE + "," + (index + 1) + "," + sample.operations
						+ "," + sample.durationNanos + "," + sample.events + ","
						+ sample.dropped + ",0,0,0");
				writer.newLine();
			}
		}
	}

	private String[] resources(int count) {
		String[] resources = new String[count];
		for (int index = 0; index < count; index++)
			resources[index] = "overhead-resource-" + index;
		return resources;
	}

	private static final class Sample {
		private final int operations;
		private final long durationNanos;
		private final long events;
		private final long dropped;

		private Sample(int operations, long durationNanos, long events,
				long dropped) {
			this.operations = operations;
			this.durationNanos = durationNanos;
			this.events = events;
			this.dropped = dropped;
		}
	}
}
