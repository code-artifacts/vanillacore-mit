"""Week 3 differential LockTable stress and PR #95 witness automation."""

from __future__ import annotations

import csv
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .common.tooling import (
    ResearchError,
    create_worktree,
    ensure_positive,
    git,
    iso_now,
    parse_surefire_reports,
    read_json,
    remove_worktree,
    repository_root,
    require_research_jdk17,
    run_maven,
    sha256_file,
    write_json,
)


DEFAULT_STRESS_RESULT = Path(
    "research/execution/week-03/results/step-06-g1-stress.json"
)
ATTEMPT_1_RESULT = Path(
    "research/execution/week-03/results/step-06-g1-stress-attempt-01.json"
)
LOCK_TABLE = Path(
    "src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java"
)
STRESS_SOURCES = (
    Path(
        "src/test/java/org/vanilladb/core/storage/tx/concurrency/"
        "LockTableStressMatrixTest.java"
    ),
    Path(
        "src/test/java/org/vanilladb/core/storage/tx/concurrency/"
        "LockTableTestProbe.java"
    ),
    Path(
        "src/test/java/org/vanilladb/core/storage/tx/concurrency/"
        "LockTablePr95WitnessTest.java"
    ),
)
AUTOMATION_SOURCES = (
    Path("scripts/research/stress.py"),
    Path("scripts/research/invoke_week03_g1_stress.py"),
)
INTEGER_FIELDS = (
    "workers",
    "iterations",
    "lockOperations",
    "acquireCalls",
    "firstGrants",
    "reentrantReturns",
    "aborts",
    "reentrantWaitLeakObservations",
    "unexpectedErrors",
    "timedOutWorkers",
    "durationNanos",
    "lockerMapEntries",
    "ownerReferences",
    "requestReferences",
    "lockByMapEntries",
    "waitMapEntries",
    "abortRegistryEntries",
)
FINAL_RESIDUE_FIELDS = (
    "ownerReferences",
    "requestReferences",
    "lockByMapEntries",
    "waitMapEntries",
    "abortRegistryEntries",
)
KNOWN_PR95_VARIANTS = {"VC-HEAD-20230430", "VC-INST-PRISTINE"}


def read_stress_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for field in INTEGER_FIELDS:
            row[field] = int(row[field])
    return rows


def classify_stress_cell(row: Mapping[str, Any]) -> dict[str, Any]:
    variant = str(row["variant"])
    known: list[str] = []
    unexplained: list[str] = []
    if row["unexpectedErrors"] or row["timedOutWorkers"]:
        unexplained.append("worker-failure-or-timeout")
    if row["lockerMapEntries"] != 0:
        target = known if variant in KNOWN_PR95_VARIANTS else unexplained
        target.append("lockerMap-concurrent-corruption")
    if row["reentrantWaitLeakObservations"] > 0:
        target = known if variant in KNOWN_PR95_VARIANTS else unexplained
        target.append("reentrant-txWaitMap-registration")
    for field in FINAL_RESIDUE_FIELDS:
        if row[field] != 0:
            unexplained.append(field)
    if unexplained:
        classification = "UNEXPLAINED"
    elif known:
        classification = "KNOWN_PR95_SYMPTOM"
    else:
        classification = "CLEAN"
    return {
        **dict(row),
        "classification": classification,
        "knownSymptoms": sorted(set(known)),
        "unexplainedSymptoms": sorted(set(unexplained)),
    }


def validate_stress_cells(
    variant: str, rows: Sequence[Mapping[str, Any]], workers: Sequence[int]
) -> dict[str, Any]:
    expected = {(worker, workload) for worker in workers for workload in ("compatible", "conflict")}
    actual = {(int(row["workers"]), str(row["workload"])) for row in rows}
    if actual != expected or len(rows) != len(expected):
        raise ResearchError(
            f"Stress matrix mismatch for {variant}: expected {sorted(expected)}, "
            f"found {sorted(actual)}."
        )
    classified = [classify_stress_cell(row) for row in rows]
    total_operations = sum(row["lockOperations"] for row in classified)
    if total_operations < 1_000_000:
        raise ResearchError(
            f"Stress operations below one million for {variant}: {total_operations}"
        )
    unexplained = sum(row["classification"] == "UNEXPLAINED" for row in classified)
    return {
        "variant": variant,
        "totalLockOperations": total_operations,
        "totalAcquireCalls": sum(row["acquireCalls"] for row in classified),
        "totalAborts": sum(row["aborts"] for row in classified),
        "totalReentrantWaitLeakObservations": sum(
            row["reentrantWaitLeakObservations"] for row in classified
        ),
        "knownSymptomCells": sum(
            row["classification"] == "KNOWN_PR95_SYMPTOM"
            for row in classified
        ),
        "cleanCells": sum(row["classification"] == "CLEAN" for row in classified),
        "unexplainedCells": unexplained,
        "cells": classified,
    }


def _copy_sources(root: Path, worktree: Path) -> None:
    for relative in STRESS_SOURCES:
        destination = worktree / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)


def _run_stress_variant(
    variant: str,
    worktree: Path,
    raw: Path,
    jdk: Mapping[str, Any],
    workers: Sequence[int],
    iterations: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    csv_path = raw / f"{variant}.csv"
    stdout = raw / f"{variant}.stress.stdout.log"
    stderr = raw / f"{variant}.stress.stderr.log"
    process = run_maven(
        worktree,
        [
            "--batch-mode",
            "-Dtest=LockTableStressMatrixTest",
            f"-Dvanillacore.mit.stressVariant={variant}",
            f"-Dvanillacore.mit.stressIterations={iterations}",
            f"-Dvanillacore.mit.stressWorkers={','.join(str(value) for value in workers)}",
            f"-Dvanillacore.mit.stressOutput={csv_path}",
            "-Dsurefire.rerunFailingTestsCount=0",
            "test",
        ],
        jdk=jdk,
        timeout_seconds=timeout_seconds,
        stdout_path=stdout,
        stderr_path=stderr,
        check=False,
    )
    report = parse_surefire_reports(
        worktree / "target/surefire-reports",
        [
            "TEST-org.vanilladb.core.storage.tx.concurrency."
            "LockTableStressMatrixTest.xml"
        ],
    )
    if process.timed_out or process.exit_code != 0 or report != {
        "tests": 1,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }:
        raise ResearchError(
            f"Stress process failed for {variant}; worktree retained at {worktree}."
        )
    if not csv_path.is_file():
        raise ResearchError(f"Stress CSV missing for {variant}: {csv_path}")
    matrix = validate_stress_cells(variant, read_stress_csv(csv_path), workers)
    return {
        **matrix,
        "startedAt": process.started_at,
        "durationSeconds": process.duration_seconds,
        "exitCode": process.exit_code,
        "tests": report,
        "lockTableSha256": sha256_file(worktree / LOCK_TABLE),
        "csvSha256": sha256_file(csv_path),
        "stdoutSha256": sha256_file(stdout),
        "stderrSha256": sha256_file(stderr),
    }


def _run_witness_variant(
    variant: str,
    worktree: Path,
    raw: Path,
    jdk: Mapping[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    stdout = raw / f"{variant}.witness.stdout.log"
    stderr = raw / f"{variant}.witness.stderr.log"
    process = run_maven(
        worktree,
        [
            "--batch-mode",
            "-Dtest=LockTablePr95WitnessTest",
            "-Dvanillacore.mit.pr95Witnesses=true",
            "-Dsurefire.rerunFailingTestsCount=0",
            "test",
        ],
        jdk=jdk,
        timeout_seconds=timeout_seconds,
        stdout_path=stdout,
        stderr_path=stderr,
        check=False,
    )
    report = parse_surefire_reports(
        worktree / "target/surefire-reports",
        [
            "TEST-org.vanilladb.core.storage.tx.concurrency."
            "LockTablePr95WitnessTest.xml"
        ],
    )
    return {
        "variant": variant,
        "durationSeconds": process.duration_seconds,
        "timedOut": process.timed_out,
        "exitCode": process.exit_code,
        **report,
        "stdoutSha256": sha256_file(stdout),
        "stderrSha256": sha256_file(stderr),
    }


def invoke_g1_stress(
    output: Path | None = None,
    *,
    workers: Sequence[int] = (2, 4, 8, 16),
    iterations: int = 62500,
    timeout_seconds: int = 900,
) -> str:
    ensure_positive(iterations=iterations, timeout_seconds=timeout_seconds)
    if tuple(workers) != (2, 4, 8, 16):
        raise ResearchError("The G1 evidence run requires workers 2,4,8,16.")
    root = repository_root()
    identity_path = root / "research/execution/week-01/results/step-02-baselines.json"
    identity = read_json(identity_path)
    patch = root / identity["patch"]["path"]
    if sha256_file(patch) != identity["patch"]["sha256"]:
        raise ResearchError("PR #95 patch hash differs from the pinned baseline.")
    baseline_commit = identity["repository"]["commit"]
    baseline_main = git(root, "rev-parse", f"{baseline_commit}:src/main")
    upstream_main = git(root, "rev-parse", f"{identity['upstream']['commit']}:src/main")
    if baseline_main != upstream_main:
        raise ResearchError("Pinned baseline production source differs from upstream.")
    instrumented_commit = git(root, "rev-parse", "HEAD")
    jdk = require_research_jdk17()
    destination = (root / (output or DEFAULT_STRESS_RESULT)).resolve()
    raw = root / "research/execution/week-03/raw/step-06"
    raw.mkdir(parents=True, exist_ok=True)
    worktree_root = Path(tempfile.mkdtemp(prefix="vanillacore-mit-week03-g1-"))
    pristine = worktree_root / "pristine"
    fixed = worktree_root / "pr95"
    instrumented = worktree_root / "instrumented"
    passed = False
    try:
        create_worktree(root, pristine, baseline_commit)
        create_worktree(root, fixed, baseline_commit)
        create_worktree(root, instrumented, instrumented_commit)
        for worktree in (pristine, fixed, instrumented):
            _copy_sources(root, worktree)
        git(fixed, "apply", "--check", str(patch))
        git(fixed, "apply", str(patch))
        variants = [
            _run_stress_variant(
                "VC-HEAD-20230430",
                pristine,
                raw,
                jdk,
                workers,
                iterations,
                timeout_seconds,
            ),
            _run_stress_variant(
                "VC-REF-95", fixed, raw, jdk, workers, iterations, timeout_seconds
            ),
            _run_stress_variant(
                "VC-INST-PRISTINE",
                instrumented,
                raw,
                jdk,
                workers,
                iterations,
                timeout_seconds,
            ),
        ]
        witnesses = [
            _run_witness_variant(
                "VC-HEAD-20230430", pristine, raw, jdk, timeout_seconds
            ),
            _run_witness_variant("VC-REF-95", fixed, raw, jdk, timeout_seconds),
        ]
        pristine_result, reference_result, instrumented_result = variants
        witness_passed = (
            witnesses[0]["exitCode"] != 0
            and witnesses[0]["tests"] == 2
            and witnesses[0]["failures"] == 2
            and witnesses[0]["errors"] == 0
            and not witnesses[0]["timedOut"]
            and witnesses[1]["exitCode"] == 0
            and witnesses[1]["tests"] == 2
            and witnesses[1]["failures"] == 0
            and witnesses[1]["errors"] == 0
            and not witnesses[1]["timedOut"]
        )
        stress_passed = (
            all(variant["unexplainedCells"] == 0 for variant in variants)
            and reference_result["cleanCells"] == 8
            and reference_result["knownSymptomCells"] == 0
            and pristine_result["knownSymptomCells"] > 0
            and instrumented_result["knownSymptomCells"] > 0
            and pristine_result["totalReentrantWaitLeakObservations"] > 0
            and instrumented_result["totalReentrantWaitLeakObservations"] > 0
            and reference_result["totalReentrantWaitLeakObservations"] == 0
        )
        passed = witness_passed and stress_passed
        evidence = {
            "schemaVersion": 1,
            "step": "week-03-step-06-g1-stress",
            "recordedAt": iso_now(),
            "gitCommit": instrumented_commit,
            "status": "PASS" if passed else "FAIL",
            "identity": {
                "baselineManifest": str(identity_path.relative_to(root)).replace(
                    "\\", "/"
                ),
                "baselineManifestSha256": sha256_file(identity_path),
                "baselineCommit": baseline_commit,
                "upstreamCommit": identity["upstream"]["commit"],
                "instrumentedCommit": instrumented_commit,
                "patch": identity["patch"]["path"],
                "patchSha256": identity["patch"]["sha256"],
            },
            "configuration": {
                "workers": list(workers),
                "workloads": ["compatible", "conflict"],
                "iterationsPerCell": iterations,
                "minimumLockOperationsPerVariant": 1_000_000,
                "jdk": jdk,
            },
            "harness": [
                {
                    "path": str(path).replace("\\", "/"),
                    "sha256": sha256_file(root / path),
                }
                for path in (*STRESS_SOURCES, *AUTOMATION_SOURCES)
            ],
            "priorAttempts": [
                {
                    "path": str(ATTEMPT_1_RESULT).replace("\\", "/"),
                    "sha256": sha256_file(root / ATTEMPT_1_RESULT),
                    "status": read_json(root / ATTEMPT_1_RESULT)["status"],
                    "gateEligible": False,
                }
            ],
            "variants": variants,
            "pr95WitnessRerun": {
                "witnesses": [
                    "lockerRegistrySupportsUpdatesFromDistinctAnchors",
                    "reentrantGrantRemovesWaitRegistration",
                ],
                "matrix": witnesses,
                "passed": witness_passed,
            },
            "gate": {
                "stressPassed": stress_passed,
                "witnessPassed": witness_passed,
                "g1Passed": passed,
                "policy": (
                    "Known pristine/instrumented symptoms are classified against "
                    "the pinned PR #95 patch; any worker failure, terminal owner/"
                    "waiter/map residue, or reference-fix symptom is unexplained."
                ),
            },
            "claimBoundary": (
                "The matrix covers the fixed worker/workload budget and classifies "
                "observed residues. It does not prove the reference fix complete "
                "outside these stress cells or imply upstream acceptance of PR #95."
            ),
        }
        write_json(destination, evidence)
        if not passed:
            raise ResearchError(
                f"G1 stress gate failed; worktrees retained at {worktree_root}."
            )
        return str(destination.relative_to(root))
    finally:
        if passed:
            for worktree in (pristine, fixed, instrumented):
                remove_worktree(root, worktree)
            shutil.rmtree(worktree_root, ignore_errors=True)
