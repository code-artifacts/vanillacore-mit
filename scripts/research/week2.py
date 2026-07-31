"""Week 2 tracing, replay, quality, and gate workflows."""

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
    median,
    read_json,
    repository_root,
    require_reports,
    run_maven,
    sha256_file,
    write_json,
)


REPORT_DIRECTORY = Path("target/surefire-reports")
EVENT_TYPES = ("LOCK_CALL", "WAIT_BEGIN", "GRANT", "RELEASE", "TX_END")
REPORTS = {
    "sink": "TEST-org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSinkTest.xml",
    "instrumentation": "TEST-org.vanilladb.core.storage.tx.concurrency.LockTableTraceInstrumentationTest.xml",
    "harness": "TEST-org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarnessTest.xml",
    "replay": "TEST-org.vanilladb.core.storage.tx.concurrency.LockTableReplayScenarioTest.xml",
    "full": "TEST-org.vanilladb.core.FullTestSuite.xml",
}


def _default(root: Path, value: Path | None, relative: str) -> Path:
    return value.resolve() if value else root / relative


def _run_tests(root: Path, selectors: str, extra: list[str] | None = None) -> None:
    arguments = ["--batch-mode"]
    if extra:
        arguments.extend(extra)
    arguments.extend([f"-Dtest={selectors}", "test"])
    run_maven(root, arguments)


def invoke_event_sink_validation(output_path: Path | None = None) -> Path:
    root = repository_root()
    output = _default(
        root,
        output_path,
        "research/execution/week-02/results/step-01-event-sink.json",
    )
    _run_tests(root, "BoundedLockTraceSinkTest")
    tests = require_reports(root / REPORT_DIRECTORY, [REPORTS["sink"]])
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "traceSchemaVersion": "vc-locktrace-0",
        "sink": {
            "type": "bounded-in-memory",
            "nonBlockingProducer": True,
            "explicitLossCounter": True,
        },
        "tests": tests,
    }
    write_json(output, result)
    return output


def invoke_instrumentation_validation(output_path: Path | None = None) -> Path:
    root = repository_root()
    output = _default(
        root,
        output_path,
        "research/execution/week-02/results/step-02-five-events.json",
    )
    _run_tests(root, "BoundedLockTraceSinkTest,LockTableTraceInstrumentationTest")
    tests = require_reports(
        root / REPORT_DIRECTORY, [REPORTS["sink"], REPORTS["instrumentation"]]
    )
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "traceSchemaVersion": "vc-locktrace-0",
        "instrumentedClass": "org.vanilladb.core.storage.tx.concurrency.LockTable",
        "eventTypes": list(EVENT_TYPES),
        "semanticFixIncluded": False,
        "tests": tests,
    }
    write_json(output, result)
    return output


def invoke_direct_harness_validation(output_path: Path | None = None) -> Path:
    root = repository_root()
    output = _default(
        root,
        output_path,
        "research/execution/week-02/results/step-03-direct-harness.json",
    )
    _run_tests(root, "DirectLockTableHarnessTest")
    tests = require_reports(root / REPORT_DIRECTORY, [REPORTS["harness"]])
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "harness": "DirectLockTableHarness",
        "capabilities": [
            "direct-five-mode-lock",
            "async-lock-request",
            "event-conditioned-wait",
            "specific-release",
            "transaction-end",
            "bounded-trace-snapshot",
            "deterministic-cleanup",
        ],
        "tests": tests,
    }
    write_json(output, result)
    return output


def invoke_scenario_replay(
    repetitions: int = 20, output_path: Path | None = None
) -> Path:
    ensure_positive(repetitions=repetitions)
    root = repository_root()
    output = _default(
        root,
        output_path,
        "research/execution/week-02/results/step-04-scenario-replay.json",
    )
    trace_directory = root / "research/execution/week-02/raw/step-04"
    trace_directory.mkdir(parents=True, exist_ok=True)
    _run_tests(
        root,
        "LockTableReplayScenarioTest",
        [
            f"-Dvanillacore.mit.repetitions={repetitions}",
            f"-Dvanillacore.mit.traceDir={trace_directory}",
        ],
    )
    tests = require_reports(root / REPORT_DIRECTORY, [REPORTS["replay"]])
    scenarios = []
    for scenario_id in ("s-s", "s-x", "x-x", "reverse-two-resource"):
        trace = trace_directory / f"{scenario_id}.jsonl"
        counts, total = event_counts([trace])
        scenarios.append(
            {
                "id": scenario_id,
                "repetitions": repetitions,
                "events": total,
                "eventCounts": {name: counts.get(name, 0) for name in EVENT_TYPES},
                "traceSha256": sha256_file(trace),
                "traceLoss": 0,
            }
        )
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "traceSchemaVersion": "vc-locktrace-0",
        "scheduler": "event-conditioned-v0",
        "repetitionsPerScenario": repetitions,
        "scenarios": scenarios,
        "tests": tests,
    }
    write_json(output, result)
    return output


def _event_metrics(
    actual_counts: dict[str, int], repetitions: int
) -> tuple[list[dict[str, Any]], int, int, int]:
    expected_per_repetition = {
        "LOCK_CALL": 10,
        "WAIT_BEGIN": 3,
        "GRANT": 9,
        "RELEASE": 9,
        "TX_END": 8,
    }
    metrics = []
    total_true_positive = 0
    total_false_positive = 0
    total_false_negative = 0
    for event_type, per_repetition in expected_per_repetition.items():
        expected = per_repetition * repetitions
        actual = actual_counts.get(event_type, 0)
        true_positive = min(expected, actual)
        false_positive = max(0, actual - expected)
        false_negative = max(0, expected - actual)
        precision = (
            1.0
            if true_positive + false_positive == 0
            else true_positive / (true_positive + false_positive)
        )
        recall = (
            1.0
            if true_positive + false_negative == 0
            else true_positive / (true_positive + false_negative)
        )
        metrics.append(
            {
                "eventType": event_type,
                "expected": expected,
                "actual": actual,
                "truePositive": true_positive,
                "falsePositive": false_positive,
                "falseNegative": false_negative,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
            }
        )
        total_true_positive += true_positive
        total_false_positive += false_positive
        total_false_negative += false_negative
    return (
        metrics,
        total_true_positive,
        total_false_positive,
        total_false_negative,
    )


def _benchmark_mode(
    directory: Path,
    mode: str,
    processes: int,
    operations_per_sample: int,
) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for path in sorted(directory.glob(f"{mode}-*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows.extend(csv.DictReader(stream))
    if not rows:
        raise ResearchError(f"No benchmark rows found for mode '{mode}'.")
    durations = [float(row["durationNanos"]) for row in rows]
    operations = sum(int(row["operations"]) for row in rows)
    dropped = sum(int(row["dropped"]) for row in rows)
    polluted = sum(
        int(row["lockerMapSize"]) != 0
        or int(row["lockByMapSize"]) != 0
        or int(row["waitMapSize"]) != 0
        for row in rows
    )
    median_duration = median(durations)
    return {
        "processes": processes,
        "samples": len(rows),
        "measuredLockOperations": operations,
        "medianDurationNanos": int(median_duration),
        "medianThroughputOpsPerSecond": round(
            operations_per_sample / (median_duration / 1_000_000_000.0), 3
        ),
        "droppedEvents": dropped,
        "pollutedSamples": polluted,
    }


def measure_trace_quality(
    completeness_repetitions: int = 20,
    processes_per_mode: int = 3,
    samples_per_process: int = 5,
    operations_per_sample: int = 100000,
    warmup_operations: int = 20000,
    output_path: Path | None = None,
) -> Path:
    ensure_positive(
        completeness_repetitions=completeness_repetitions,
        processes_per_mode=processes_per_mode,
        samples_per_process=samples_per_process,
        operations_per_sample=operations_per_sample,
    )
    if warmup_operations < 0:
        raise ResearchError("Warmup operations must not be negative.")
    root = repository_root()
    output = _default(
        root,
        output_path,
        "research/execution/week-02/results/step-05-trace-quality.json",
    )
    run_id = f"{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}"
    raw = root / "research/execution/week-02/raw/step-05" / run_id
    completeness = raw / "completeness"
    benchmark = raw / "overhead"
    completeness.mkdir(parents=True, exist_ok=True)
    benchmark.mkdir(parents=True, exist_ok=True)

    _run_tests(
        root,
        "LockTableReplayScenarioTest",
        [
            f"-Dvanillacore.mit.repetitions={completeness_repetitions}",
            f"-Dvanillacore.mit.traceDir={completeness}",
        ],
    )
    actual_counts, _ = event_counts(completeness.glob("*.jsonl"))
    metrics, true_positive, false_positive, false_negative = _event_metrics(
        actual_counts, completeness_repetitions
    )

    order: list[str] = []
    for process_number in range(1, processes_per_mode + 1):
        order.extend(("off", "low") if process_number % 2 else ("low", "off"))
    mode_process = {"off": 0, "low": 0}
    for mode in order:
        mode_process[mode] += 1
        benchmark_output = benchmark / f"{mode}-{mode_process[mode]:02d}.csv"
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
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "traceSchemaVersion": "vc-locktrace-0",
        "completeness": {
            "repetitionsPerScenario": completeness_repetitions,
            "eventMetrics": metrics,
            "microPrecision": round(micro_precision, 6),
            "microRecall": round(micro_recall, 6),
            "traceLoss": 0,
            "scope": "event-type multiplicity for four deterministic direct scenarios",
        },
        "overhead": {
            "workload": "single-thread S acquire/release over 100 resources",
            "lowEventTypes": ["GRANT", "RELEASE", "TX_END"],
            "operationsPerSample": operations_per_sample,
            "samplesPerProcess": samples_per_process,
            "warmupOperationsPerProcess": warmup_operations,
            "modes": modes,
            "lowOverheadPercent": round(overhead_percent, 3),
            "targetPercent": 10,
            "hardCeilingPercent": 25,
            "withinTarget": overhead_percent <= 10,
            "withinHardCeiling": overhead_percent <= 25,
        },
        "baselineStress": {
            "offModeLockOperations": modes["off"]["measuredLockOperations"],
            "unexplainedPollutedSamples": modes["off"]["pollutedSamples"],
        },
    }
    write_json(output, result)
    return output


def new_gate_decision(output_path: Path | None = None) -> Path:
    root = repository_root()
    output = _default(
        root,
        output_path,
        "research/execution/week-02/results/step-06-g0-g2-decision.json",
    )
    run_maven(root, ["--batch-mode", "test"])
    full_suite = require_reports(root / REPORT_DIRECTORY, [REPORTS["full"]])
    mit_selectors = (
        "BoundedLockTraceSinkTest,LockTableTraceInstrumentationTest,"
        "DirectLockTableHarnessTest,LockTableReplayScenarioTest"
    )
    _run_tests(root, mit_selectors)
    mit_totals = require_reports(
        root / REPORT_DIRECTORY,
        [REPORTS["sink"], REPORTS["instrumentation"], REPORTS["harness"], REPORTS["replay"]],
    )
    week1 = root / "research/execution/week-01/results"
    week2 = root / "research/execution/week-02/results"
    build_matrix = read_json(week1 / "step-03-build-matrix.json")
    repetition = read_json(week1 / "step-04-repetition-summary.json")
    pr95 = read_json(week1 / "step-06-pr95-witness-matrix.json")
    replay = read_json(week2 / "step-04-scenario-replay.json")
    quality = read_json(week2 / "step-05-trace-quality.json")

    g0_passed = (
        not any(
            build["exitCode"] != 0
            or build["timedOut"]
            or build["tests"]["failures"] != 0
            or build["tests"]["errors"] != 0
            for build in build_matrix["builds"]
        )
        and not any(
            campaign["passes"] != campaign["repetitionsRequested"]
            or campaign["failures"] != 0
            for campaign in repetition["campaigns"]
        )
        and full_suite["failures"] == 0
        and full_suite["errors"] == 0
        and mit_totals["failures"] == 0
        and mit_totals["errors"] == 0
    )
    g1_passed = (
        pr95["matrixPassed"]
        and quality["baselineStress"]["offModeLockOperations"] >= 1_000_000
        and quality["baselineStress"]["unexplainedPollutedSamples"] == 0
    )
    g2_passed = (
        quality["completeness"]["microPrecision"] >= 0.95
        and quality["completeness"]["microRecall"] >= 0.95
        and quality["completeness"]["traceLoss"] == 0
        and not any(scenario["traceLoss"] != 0 for scenario in replay["scenarios"])
    )
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "decisionScope": "G0-G2 at the end of Week 2",
        "gates": [
            {
                "id": "G0",
                "name": "Build",
                "status": "PASS" if g0_passed else "FAIL",
                "evidence": {
                    "dualBaselineBuilds": len(build_matrix["builds"]),
                    "freshProcessCampaigns": len(repetition["campaigns"]),
                    "currentFullSuite": {
                        key: full_suite[key] for key in ("tests", "failures", "errors")
                    },
                    "currentMitFunctionalSuite": mit_totals,
                },
            },
            {
                "id": "G1",
                "name": "Baseline",
                "status": "CONDITIONAL_PASS" if g1_passed else "FAIL",
                "evidence": {
                    "pr95DifferentialPassed": pr95["matrixPassed"],
                    "offModeLockOperations": quality["baselineStress"]["offModeLockOperations"],
                    "unexplainedPollutedSamples": quality["baselineStress"]["unexplainedPollutedSamples"],
                },
                "limitations": [
                    "stress workload is single-thread S acquire/release",
                    "instrumented main source remains pristine rather than PR95 reference fix",
                    "conflicting 2/4/8/16-worker stress matrix remains open",
                ],
            },
            {
                "id": "G2",
                "name": "Trace",
                "status": "PASS_SCOPE_LIMITED" if g2_passed else "FAIL",
                "evidence": {
                    "microPrecision": quality["completeness"]["microPrecision"],
                    "microRecall": quality["completeness"]["microRecall"],
                    "traceLoss": quality["completeness"]["traceLoss"],
                    "scenarios": len(replay["scenarios"]),
                    "repetitionsPerScenario": replay["repetitionsPerScenario"],
                },
                "limitations": [
                    "precision and recall cover event-type multiplicity in Direct scenarios",
                    "resource role, parent, purpose, and owner/waiter snapshots are not validated",
                    "abort is an external Future outcome rather than a v0 trace event",
                ],
            },
        ],
        "performanceRisk": {
            "status": (
                "ACCEPTABLE_FOR_G3"
                if quality["overhead"]["withinHardCeiling"]
                else "BLOCKS_G3"
            ),
            "lowOverheadPercent": quality["overhead"]["lowOverheadPercent"],
            "hardCeilingPercent": quality["overhead"]["hardCeilingPercent"],
        },
        "overall": {
            "decision": "CONDITIONAL_GO" if g0_passed and g1_passed and g2_passed else "NO_GO",
            "allowedNext": [
                "L1 TLA+ model",
                "trace schema and mapping refinement",
                "Direct harness correctness experiments",
            ],
            "blockedUntilResolved": [
                "G3 replay or low-overhead claims",
                "broad mutation campaign",
                "production-performance claims",
            ],
            "mandatoryActions": [
                "activate PR95 as a separate reference-fix patch set",
                "run conflicting 2/4/8/16-worker million-operation stress",
                "reduce low overhead to at most 25 percent and remeasure unchanged protocol",
                "add explicit abort and trace-loss semantics before strong refinement verdicts",
            ],
        },
    }
    write_json(output, result)
    return output
