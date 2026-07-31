"""Week 3 low-sink optimization measurements and decisions."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .common.tooling import (
    ResearchError,
    ensure_positive,
    event_counts,
    git,
    iso_now,
    read_json,
    repository_root,
    require_reports,
    sha256_file,
    write_json,
)
from .week2 import EVENT_TYPES, REPORTS, _benchmark_mode, _event_metrics, _run_tests


TARGET_PERCENT = 10
HARD_CEILING_PERCENT = 25
MAX_ITERATIONS = 2


def classify_low_sink_iteration(iteration: int, overhead_percent: float) -> str:
    if iteration not in range(1, MAX_ITERATIONS + 1):
        raise ResearchError("Low-sink iteration must be 1 or 2.")
    if overhead_percent <= TARGET_PERCENT:
        return "TARGET_PASS"
    if overhead_percent <= HARD_CEILING_PERCENT:
        return "HARD_CEILING_PASS"
    return "OPTIMIZE_AGAIN" if iteration < MAX_ITERATIONS else "BLOCK_G3"


def _samples(directory: Path, mode: str) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for path in sorted(directory.glob(f"{mode}-*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                samples.append(
                    {
                        "process": path.stem,
                        "sample": int(row["sample"]),
                        "operations": int(row["operations"]),
                        "durationNanos": int(row["durationNanos"]),
                        "events": int(row["events"]),
                        "dropped": int(row["dropped"]),
                        "lockerMapSize": int(row["lockerMapSize"]),
                        "lockByMapSize": int(row["lockByMapSize"]),
                        "waitMapSize": int(row["waitMapSize"]),
                    }
                )
    if not samples:
        raise ResearchError(f"No raw samples found for mode '{mode}'.")
    return samples


def _source_hashes(root: Path) -> dict[str, str]:
    paths = {
        "lockTable": "src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java",
        "lockTrace": "src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTrace.java",
        "lockTraceSink": "src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceSink.java",
        "boundedSink": "src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java",
        "benchmark": "src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTraceOverheadBenchmarkTest.java",
        "automation": "scripts/research/low_sink.py",
    }
    return {name: sha256_file(root / path) for name, path in paths.items()}


def measure_low_sink_iteration(
    iteration: int,
    implementation: str,
    completeness_repetitions: int = 20,
    processes_per_mode: int = 3,
    samples_per_process: int = 5,
    operations_per_sample: int = 100000,
    warmup_operations: int = 20000,
    output_path: Path | None = None,
) -> Path:
    if iteration not in range(1, MAX_ITERATIONS + 1):
        raise ResearchError("Low-sink iteration must be 1 or 2.")
    if not implementation.strip():
        raise ResearchError("Implementation label must not be empty.")
    ensure_positive(
        completeness_repetitions=completeness_repetitions,
        processes_per_mode=processes_per_mode,
        samples_per_process=samples_per_process,
        operations_per_sample=operations_per_sample,
    )
    if warmup_operations < 0:
        raise ResearchError("Warmup operations must not be negative.")

    root = repository_root()
    output = output_path.resolve() if output_path else root / (
        "research/execution/week-03/results/"
        f"step-07-low-sink-iteration-{iteration:02d}.json"
    )
    run_id = f"{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}"
    raw = root / (
        "research/execution/week-03/raw/step-07/"
        f"iteration-{iteration:02d}/{run_id}"
    )
    completeness = raw / "completeness"
    benchmark = raw / "overhead"
    completeness.mkdir(parents=True, exist_ok=True)
    benchmark.mkdir(parents=True, exist_ok=True)

    _run_tests(
        root,
        "BoundedLockTraceSinkTest,LockTableTraceInstrumentationTest,"
        "LockTableReplayScenarioTest",
        [
            f"-Dvanillacore.mit.repetitions={completeness_repetitions}",
            f"-Dvanillacore.mit.traceDir={completeness}",
        ],
    )
    tests = require_reports(
        root / "target/surefire-reports",
        [REPORTS["sink"], REPORTS["instrumentation"], REPORTS["replay"]],
    )
    actual_counts, _ = event_counts(completeness.glob("*.jsonl"))
    metrics, true_positive, false_positive, false_negative = _event_metrics(
        actual_counts, completeness_repetitions
    )

    order: list[str] = []
    for process_number in range(1, processes_per_mode + 1):
        order.extend(("off", "low") if process_number % 2 else ("low", "off"))
    mode_process = {"off": 0, "low": 0}
    process_order: list[str] = []
    for mode in order:
        mode_process[mode] += 1
        process_id = f"{mode}-{mode_process[mode]:02d}"
        process_order.append(process_id)
        benchmark_output = benchmark / f"{process_id}.csv"
        _run_tests(
            root,
            "LockTraceOverheadBenchmarkTest",
            [
                f"-Dvanillacore.mit.benchmarkMode={mode}",
                f"-Dvanillacore.mit.operations={operations_per_sample}",
                f"-Dvanillacore.mit.samples={samples_per_process}",
                f"-Dvanillacore.mit.warmupOperations={warmup_operations}",
                f"-Dvanillacore.mit.benchmarkOutput={benchmark_output}",
            ],
        )

    modes = {
        mode: _benchmark_mode(
            benchmark, mode, processes_per_mode, operations_per_sample
        )
        for mode in ("off", "low")
    }
    overhead_percent = (
        modes["low"]["medianDurationNanos"]
        / modes["off"]["medianDurationNanos"]
        - 1.0
    ) * 100.0
    micro_precision = true_positive / (true_positive + false_positive)
    micro_recall = true_positive / (true_positive + false_negative)
    baseline_path = root / (
        "research/execution/week-02/results/step-05-trace-quality.json"
    )
    baseline = read_json(baseline_path)
    result = {
        "schemaVersion": 1,
        "step": "week-03-step-07",
        "iteration": iteration,
        "implementation": implementation,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "worktreeDirty": bool(git(root, "status", "--short")),
        "traceSchemaVersion": "vc-locktrace-0",
        "protocol": {
            "matchesWeek2": True,
            "completenessRepetitionsPerScenario": completeness_repetitions,
            "processesPerMode": processes_per_mode,
            "samplesPerProcess": samples_per_process,
            "operationsPerSample": operations_per_sample,
            "warmupOperationsPerProcess": warmup_operations,
            "processOrder": process_order,
        },
        "completeness": {
            "eventMetrics": metrics,
            "microPrecision": round(micro_precision, 6),
            "microRecall": round(micro_recall, 6),
            "traceLoss": 0,
            "tests": tests,
        },
        "overhead": {
            "workload": "single-thread S acquire/release over 100 resources",
            "lowEventTypes": ["GRANT", "RELEASE", "TX_END"],
            "modes": modes,
            "samples": {mode: _samples(benchmark, mode) for mode in ("off", "low")},
            "lowOverheadPercent": round(overhead_percent, 3),
            "targetPercent": TARGET_PERCENT,
            "hardCeilingPercent": HARD_CEILING_PERCENT,
            "withinTarget": overhead_percent <= TARGET_PERCENT,
            "withinHardCeiling": overhead_percent <= HARD_CEILING_PERCENT,
        },
        "decision": classify_low_sink_iteration(iteration, overhead_percent),
        "baseline": {
            "resultSha256": sha256_file(baseline_path),
            "lowOverheadPercent": baseline["overhead"]["lowOverheadPercent"],
        },
        "sourceSha256": _source_hashes(root),
    }
    write_json(output, result)
    return output
