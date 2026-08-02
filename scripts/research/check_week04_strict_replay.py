from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common.cli import execute
from .common.tooling import (
    git,
    iso_now,
    parse_surefire_reports,
    repository_root,
    require_research_jdk17,
    run_maven,
)
from .week4_schedule import write_json


DEFAULT_RESULT = Path("research/execution/week-04/results/step-03-strict-replay.json")
REPORT = "TEST-org.vanilladb.core.storage.tx.concurrency.schedule.StrictScheduleControllerTest.xml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Week 4 strict replay.")
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    return parser


def run(args: argparse.Namespace) -> str:
    root = repository_root()
    jdk = require_research_jdk17()
    command = ["--batch-mode", "-Dtest=StrictScheduleControllerTest", "test"]
    execution = run_maven(root, command, jdk=jdk, timeout_seconds=180)
    totals = parse_surefire_reports(root / "target/surefire-reports", [REPORT])
    status = "PASS" if totals == {"tests": 4, "failures": 0, "errors": 0, "skipped": 0} else "FAIL"
    result = {
        "schemaVersion": 1,
        "step": "week-04-step-03-strict-replay",
        "recordedAt": iso_now(),
        "gitCommit": git(root, "rev-parse", "HEAD"),
        "status": status,
        "jdk": {"vendor": jdk["Vendor"], "runtimeVersion": jdk["RuntimeVersion"]},
        "durationSeconds": execution.duration_seconds,
        "tests": totals,
        "divergenceKinds": [
            "MISSING_EVENT",
            "EXTRA_EVENT",
            "WRONG_TRANSACTION",
            "WRONG_RESOURCE",
            "TIMEOUT",
            "HARNESS_EXCEPTION",
        ],
        "prefixPolicy": "SHORTEST_EXPECTED_AND_ACTUAL_PREFIX_AT_FIRST_DIVERGENCE",
    }
    destination = root / args.result
    write_json(destination, result)
    if status != "PASS":
        raise ValueError(f"strict replay validation failed: {totals}")
    return json.dumps({"result": args.result.as_posix(), "tests": totals})


def main() -> int:
    return execute(lambda: run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
