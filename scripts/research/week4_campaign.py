from __future__ import annotations

import csv
import json
import os
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .common.tooling import (
    ResearchError,
    executable,
    git,
    iso_now,
    java_environment,
    read_json,
    repository_root,
    require_research_jdk17,
    run_maven,
    run_process,
    sha256_file,
)
from .week4_gate import classify_g3
from .week4_schedule import DEFAULT_CORPUS, write_json


DEFAULT_RESULT = Path("research/execution/week-04/results/step-07-g3-decision.json")
REPLAY_TEST = "org.vanilladb.core.storage.tx.concurrency.Week04ScheduleReplayTest"
BENCHMARK_TEST = "org.vanilladb.core.storage.tx.concurrency.LockTraceOverheadBenchmarkTest"
RESIDUE_FIELDS = (
    "lockerMapEntries",
    "ownerReferences",
    "requestReferences",
    "transactionLockSetEntries",
    "waitRegistrationEntries",
    "abortRegistryEntries",
    "liveWorkerThreads",
)


def _prepare_classpath(root: Path, jdk: Mapping[str, Any]) -> str:
    output = root / "target/week04-dependency-classpath.txt"
    run_maven(
        root,
        [
            "--batch-mode",
            "test-compile",
            "dependency:build-classpath",
            f"-Dmdep.outputFile={output}",
        ],
        jdk=jdk,
        timeout_seconds=300,
    )
    dependencies = output.read_text(encoding="utf-8").strip()
    return os.pathsep.join(
        (str(root / "target/test-classes"), str(root / "target/classes"), dependencies)
    )


def _java_command(
    root: Path,
    jdk: Mapping[str, Any],
    classpath: str,
    properties: Mapping[str, object],
    test_class: str,
) -> list[str]:
    command = [
        str(executable(Path(jdk["Home"]), "java")),
        f"-Dorg.vanilladb.core.config.file={root / 'target/test-classes/org/vanilladb/core/vanilladb.properties'}",
        f"-Djava.util.logging.config.file={root / 'target/test-classes/java/util/logging/logging.properties'}",
    ]
    command.extend(f"-D{name}={value}" for name, value in properties.items())
    command.extend(["-cp", classpath, "org.junit.runner.JUnitCore", test_class])
    return command


def _save_failure_logs(path: Path, stdout: str, stderr: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".stdout.log").write_text(stdout, encoding="utf-8")
    path.with_suffix(".stderr.log").write_text(stderr, encoding="utf-8")


def _run_replays(
    root: Path,
    jdk: Mapping[str, Any],
    classpath: str,
    raw: Path,
    schedules: list[str],
    repetitions: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    outcomes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for mode in ("high", "low"):
        for schedule_index, schedule in enumerate(schedules):
            passed = 0
            for repetition in range(1, repetitions + 1):
                result_path = raw / "replay" / mode / schedule / f"{repetition:02d}.json"
                command = _java_command(
                    root,
                    jdk,
                    classpath,
                    {
                        "vanillacore.mit.schedule": schedule,
                        "vanillacore.mit.traceMode": mode,
                        "vanillacore.mit.seed": 20260802 + schedule_index * 100 + repetition,
                        "vanillacore.mit.result": result_path,
                    },
                    REPLAY_TEST,
                )
                execution = run_process(
                    command,
                    cwd=root,
                    environment=java_environment(jdk),
                    timeout_seconds=30,
                )
                evidence: dict[str, Any]
                if result_path.is_file():
                    evidence = read_json(result_path)
                else:
                    evidence = {
                        "schedule": schedule,
                        "mode": mode,
                        "status": "PROCESS_FAILURE",
                        "failureClass": "PROCESS_TIMEOUT"
                        if execution.timed_out
                        else "PROCESS_EXIT",
                        "failureMessage": f"exit={execution.exit_code}",
                        "droppedEvents": -1,
                        **{field: -1 for field in RESIDUE_FIELDS},
                    }
                clean = (
                    execution.exit_code == 0
                    and not execution.timed_out
                    and evidence.get("status") == "PASS"
                    and evidence.get("droppedEvents") == 0
                    and all(evidence.get(field) == 0 for field in RESIDUE_FIELDS)
                    and evidence.get("expectedEvents") == evidence.get("actualEvents")
                )
                outcome = {
                    "mode": mode,
                    "schedule": schedule,
                    "repetition": repetition,
                    "status": "PASS" if clean else "FAIL",
                    "failureClass": evidence.get("failureClass"),
                    "droppedEvents": evidence.get("droppedEvents"),
                    "residue": {field: evidence.get(field) for field in RESIDUE_FIELDS},
                    "raw": result_path.relative_to(root).as_posix(),
                }
                outcomes.append(outcome)
                if clean:
                    passed += 1
                else:
                    _save_failure_logs(result_path, execution.stdout, execution.stderr)
                    failures.append(
                        {
                            **outcome,
                            "failureMessage": evidence.get("failureMessage"),
                            "exitCode": execution.exit_code,
                            "timedOut": execution.timed_out,
                        }
                    )
            print(f"{mode} {schedule}: {passed}/{repetitions}", flush=True)
    return outcomes, failures


def _run_benchmark(
    root: Path,
    jdk: Mapping[str, Any],
    classpath: str,
    raw: Path,
) -> dict[str, Any]:
    samples: dict[str, list[dict[str, int]]] = {"off": [], "low": []}
    process_order: list[str] = []
    for process in range(1, 4):
        modes = ("off", "low") if process % 2 else ("low", "off")
        for mode in modes:
            process_id = f"{mode}-{process:02d}"
            process_order.append(process_id)
            output = raw / "overhead" / f"{process_id}.csv"
            command = _java_command(
                root,
                jdk,
                classpath,
                {
                    "vanillacore.mit.benchmarkMode": mode,
                    "vanillacore.mit.operations": 100000,
                    "vanillacore.mit.samples": 5,
                    "vanillacore.mit.warmupOperations": 20000,
                    "vanillacore.mit.benchmarkOutput": output,
                },
                BENCHMARK_TEST,
            )
            execution = run_process(
                command,
                cwd=root,
                environment=java_environment(jdk),
                timeout_seconds=90,
            )
            if execution.timed_out or execution.exit_code != 0 or not output.is_file():
                _save_failure_logs(output, execution.stdout, execution.stderr)
                raise ResearchError(f"Week 4 {mode} benchmark process failed: {process_id}")
            with output.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    samples[mode].append(
                        {
                            "process": process,
                            "sample": int(row["sample"]),
                            "durationNanos": int(row["durationNanos"]),
                            "events": int(row["events"]),
                            "dropped": int(row["dropped"]),
                            "lockerMapSize": int(row["lockerMapSize"]),
                            "lockByMapSize": int(row["lockByMapSize"]),
                            "waitMapSize": int(row["waitMapSize"]),
                        }
                    )
    medians = {
        mode: int(statistics.median(sample["durationNanos"] for sample in values))
        for mode, values in samples.items()
    }
    overhead = (medians["low"] / medians["off"] - 1.0) * 100.0
    return {
        "protocol": {
            "processesPerMode": 3,
            "samplesPerProcess": 5,
            "operationsPerSample": 100000,
            "warmupOperations": 20000,
            "processOrder": process_order,
        },
        "medianDurationNanos": medians,
        "lowOverheadPercent": round(overhead, 3),
        "hardCeilingPercent": 25,
        "withinHardCeiling": overhead <= 25,
        "samples": samples,
    }


def _mode_summary(
    outcomes: list[dict[str, Any]], schedules: list[str], repetitions: int, mode: str
) -> dict[str, Any]:
    selected = [outcome for outcome in outcomes if outcome["mode"] == mode]
    by_schedule = {}
    for schedule in schedules:
        values = [outcome for outcome in selected if outcome["schedule"] == schedule]
        success = sum(outcome["status"] == "PASS" for outcome in values)
        by_schedule[schedule] = {
            "success": success,
            "runs": repetitions,
            "successRate": round(success / repetitions, 6),
            "outcomes": dict(Counter(outcome["status"] for outcome in values)),
        }
    success = sum(outcome["status"] == "PASS" for outcome in selected)
    return {
        "success": success,
        "runs": len(selected),
        "successRate": round(success / len(selected), 6),
        "bySchedule": by_schedule,
    }


def run_week4_campaign(repetitions: int = 30, output: Path | None = None) -> Path:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    root = repository_root()
    destination = root / (output or DEFAULT_RESULT)
    jdk = require_research_jdk17()
    classpath = _prepare_classpath(root, jdk)
    schedules = sorted(path.stem for path in (root / DEFAULT_CORPUS).glob("*.json"))
    if len(schedules) != 8:
        raise ResearchError(f"expected eight frozen schedules, found {len(schedules)}")
    run_id = f"{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}"
    raw = root / "research/execution/week-04/raw/step-07" / run_id
    outcomes, failures = _run_replays(
        root, jdk, classpath, raw, schedules, repetitions
    )
    overhead = _run_benchmark(root, jdk, classpath, raw)
    high = _mode_summary(outcomes, schedules, repetitions, "high")
    low = _mode_summary(outcomes, schedules, repetitions, "low")
    silent_loss_or_residue = any(
        outcome["droppedEvents"] != 0
        or any(value != 0 for value in outcome["residue"].values())
        for outcome in outcomes
    )
    week3_path = root / "research/execution/week-03/results/step-07-week-03-gate.json"
    week3 = read_json(week3_path)
    partial_path = root / "research/execution/week-04/results/step-04-partial-order.json"
    native_path = root / "research/execution/week-04/results/step-05-native-harness.json"
    partial = read_json(partial_path)
    native = read_json(native_path)
    decision = classify_g3(
        week3_prerequisite_passed=week3["decision"] == "READY_FOR_G3",
        high_success_rate=high["successRate"],
        low_success_rate=low["successRate"],
        overhead_percent=overhead["lowOverheadPercent"],
        silent_loss_or_residue=silent_loss_or_residue,
        partial_order_passed=partial["status"] == "PASS",
        native_passed=native["status"] == "PASS",
    )
    result = {
        "schemaVersion": 1,
        "step": "week-04-step-07-g3",
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "worktreeDirty": bool(git(root, "status", "--short")),
        "status": "COMPLETE",
        "decision": decision,
        "protocol": {
            "freshJvmPerRun": True,
            "schedules": schedules,
            "repetitionsPerSchedulePerMode": repetitions,
            "totalReplayRuns": len(outcomes),
            "seedBase": 20260802,
            "rawDirectory": raw.relative_to(root).as_posix(),
        },
        "replay": {"high": high, "low": low},
        "overhead": overhead,
        "integrity": {
            "silentLossOrResidue": silent_loss_or_residue,
            "failureCount": len(failures),
            "failureDistribution": dict(
                Counter(failure.get("failureClass") or "UNCLASSIFIED" for failure in failures)
            ),
            "failures": failures,
            "allOutcomes": outcomes,
        },
        "dependencies": {
            "week3Prerequisite": {
                "path": week3_path.relative_to(root).as_posix(),
                "sha256": sha256_file(week3_path),
                "decision": week3["decision"],
            },
            "partialOrder": {
                "path": partial_path.relative_to(root).as_posix(),
                "sha256": sha256_file(partial_path),
                "status": partial["status"],
            },
            "nativeHarness": {
                "path": native_path.relative_to(root).as_posix(),
                "sha256": sha256_file(native_path),
                "status": native["status"],
            },
        },
        "gates": {
            "high30of30Each": all(
                value["success"] == repetitions for value in high["bySchedule"].values()
            ),
            "lowAtLeast90Percent": low["successRate"] >= 0.9,
            "lowBelow80Percent": low["successRate"] < 0.8,
            "overheadAtMost25Percent": overhead["withinHardCeiling"],
            "noSilentLossOrResidue": not silent_loss_or_residue,
            "week3PrerequisitePassed": week3["decision"] == "READY_FOR_G3",
        },
        "blockedWeek5MethodEvidence": decision != "G3_PASS",
        "claimBoundary": (
            "A completed campaign is not a G3 pass. Failure of the inherited Week 3 "
            "overhead prerequisite or any current gate blocks Week 5 method-effectiveness claims."
        ),
    }
    write_json(destination, result)
    return destination
