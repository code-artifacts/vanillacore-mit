from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common.cli import execute
from .common.tooling import (
    parse_surefire_reports,
    repository_root,
    require_research_jdk17,
    run_maven,
)
from .partial_order import independent_fixture, respects_edges, validate_dag
from .week4_schedule import DEFAULT_CORPUS, read_json, write_json


DEFAULT_RESULT = Path("research/execution/week-04/results/step-04-partial-order.json")
REPORT = "TEST-org.vanilladb.core.storage.tx.concurrency.schedule.PartialOrderScheduleControllerTest.xml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Week 4 partial-order replay.")
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    return parser


def run(args: argparse.Namespace) -> str:
    root = repository_root()
    schedules = sorted((root / DEFAULT_CORPUS).glob("*.json"))
    dag_sizes = {path.stem: len(validate_dag(read_json(path))) for path in schedules}
    fixture = independent_fixture()
    if not all(
        respects_edges(linearization, fixture["edges"])
        for linearization in fixture["legalLinearizations"]
    ):
        raise ValueError("independent fixture contains an illegal linearization")
    execution = run_maven(
        root,
        ["--batch-mode", "-Dtest=PartialOrderScheduleControllerTest", "test"],
        jdk=require_research_jdk17(),
        timeout_seconds=180,
    )
    totals = parse_surefire_reports(root / "target/surefire-reports", [REPORT])
    status = "PASS" if totals == {"tests": 3, "failures": 0, "errors": 0, "skipped": 0} else "FAIL"
    result = {
        "schemaVersion": 1,
        "step": "week-04-step-04-partial-order",
        "status": status,
        "seed": 20260802,
        "validatedSchedules": dag_sizes,
        "fixture": fixture,
        "javaTests": totals,
        "durationSeconds": execution.duration_seconds,
        "claimBoundary": "Validates supplied DAGs and two legal linearizations; it is not DPOR search.",
    }
    write_json(root / args.result, result)
    if status != "PASS":
        raise ValueError(f"partial-order validation failed: {totals}")
    return json.dumps({"result": args.result.as_posix(), "schedules": len(schedules)})


def main() -> int:
    return execute(lambda: run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
