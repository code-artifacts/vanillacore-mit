"""Assemble the Week 3 L1, G1, G2, and low-overhead gate decision."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common.tooling import (
    ResearchError,
    git,
    iso_now,
    read_json,
    repository_root,
    sha256_file,
    write_json,
)


def classify_week3_gate(
    l1_passed: bool,
    g1_passed: bool,
    g2_passed: bool,
    low_within_hard_ceiling: bool,
) -> str:
    if not l1_passed or not g1_passed or not g2_passed:
        return "BLOCKED_FOUNDATIONAL_GATE"
    if not low_within_hard_ceiling:
        return "BLOCKED_FOR_G3"
    return "READY_FOR_G3"


def _evidence(root: Path, name: str) -> tuple[Path, dict[str, Any]]:
    path = root / "research/execution/week-03/results" / name
    if not path.is_file():
        raise ResearchError(f"Missing Week 3 evidence: {path}")
    return path, read_json(path)


def new_week3_gate_decision(output_path: Path | None = None) -> Path:
    root = repository_root()
    output = output_path.resolve() if output_path else root / (
        "research/execution/week-03/results/step-07-week-03-gate.json"
    )
    step_files = [
        "step-01-tla-toolchain.json",
        "step-02-l1-model.json",
        "step-03-mapping-ledger.json",
        "step-04-canonical-traces.json",
        "step-05-model-self-tests.json",
    ]
    foundational = [_evidence(root, name) for name in step_files]
    g1_path, g1 = _evidence(root, "step-06-g1-stress.json")
    iteration_pairs = [
        _evidence(root, f"step-07-low-sink-iteration-{iteration:02d}.json")
        for iteration in (1, 2)
    ]

    l1_passed = (
        all(value["status"] == "PASS" for _, value in foundational)
        and foundational[3][1]["traceCount"] == 8
    )
    g1_passed = g1["status"] == "PASS" and g1["gate"]["g1Passed"]
    iteration_summaries = []
    for path, value in iteration_pairs:
        completeness = value["completeness"]
        overhead = value["overhead"]
        iteration_summaries.append(
            {
                "iteration": value["iteration"],
                "implementation": value["implementation"],
                "resultSha256": sha256_file(path),
                "microPrecision": completeness["microPrecision"],
                "microRecall": completeness["microRecall"],
                "traceLoss": completeness["traceLoss"],
                "lowOverheadPercent": overhead["lowOverheadPercent"],
                "withinHardCeiling": overhead["withinHardCeiling"],
                "decision": value["decision"],
            }
        )
    g2_passed = all(
        value["microPrecision"] >= 0.95
        and value["microRecall"] >= 0.95
        and value["traceLoss"] == 0
        for value in iteration_summaries
    )
    final_within_ceiling = iteration_summaries[-1]["withinHardCeiling"]
    decision = classify_week3_gate(
        l1_passed, g1_passed, g2_passed, final_within_ceiling
    )
    result = {
        "schemaVersion": 1,
        "step": "week-03-step-07-gate",
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "worktreeDirty": bool(git(root, "status", "--short")),
        "decision": decision,
        "gates": [
            {
                "id": "L1",
                "status": "PASS" if l1_passed else "FAIL",
                "evidence": [
                    {"path": str(path.relative_to(root)).replace("\\", "/"),
                     "sha256": sha256_file(path)}
                    for path, _ in foundational
                ],
            },
            {
                "id": "G1",
                "status": "PASS" if g1_passed else "FAIL",
                "resultSha256": sha256_file(g1_path),
            },
            {
                "id": "G2",
                "status": "PASS" if g2_passed else "FAIL",
                "iterations": iteration_summaries,
            },
            {
                "id": "G3_PREREQUISITE",
                "status": "PASS" if final_within_ceiling else "BLOCK",
                "hardCeilingPercent": 25,
                "finalLowOverheadPercent": iteration_summaries[-1][
                    "lowOverheadPercent"
                ],
            },
        ],
        "allowedNext": [
            "offline L1 model refinement",
            "trace validation without scheduler performance claims",
            "low-sink profiling and a newly approved optimization plan",
        ],
        "blockedUntilResolved": [
            "G3 replay conclusion",
            "scheduler performance claim",
            "scheduler replayability claim",
        ] if not final_within_ceiling else [],
        "policy": (
            "Two optimization iterations are exhausted. A result above the 25 percent "
            "hard ceiling blocks G3 while allowing offline model and trace-validation work."
        ),
    }
    write_json(output, result)
    return output
