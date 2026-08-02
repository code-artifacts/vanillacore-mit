from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common.cli import execute
from .common.tooling import parse_surefire_reports, repository_root, require_research_jdk17, run_maven
from .week4_schedule import write_json


DEFAULT_RESULT = Path("research/execution/week-04/results/step-05-native-harness.json")
REPORT = "TEST-org.vanilladb.core.storage.tx.concurrency.NativeTransactionHarnessTest.xml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the Week 4 Native harness.")
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    return parser


def run(args: argparse.Namespace) -> str:
    root = repository_root()
    execution = run_maven(
        root,
        ["--batch-mode", "-Dtest=NativeTransactionHarnessTest", "test"],
        jdk=require_research_jdk17(),
        timeout_seconds=240,
    )
    totals = parse_surefire_reports(root / "target/surefire-reports", [REPORT])
    status = "PASS" if totals == {"tests": 4, "failures": 0, "errors": 0, "skipped": 0} else "FAIL"
    result = {
        "schemaVersion": 1,
        "step": "week-04-step-05-native-harness",
        "status": status,
        "tests": totals,
        "durationSeconds": execution.duration_seconds,
        "coverage": [
            "FILE_BLOCK_RECORD",
            "S_S",
            "S_X",
            "X_X",
            "COMMIT_RELEASE_GRANT",
            "ROLLBACK_UNDO_THEN_GRANT",
            "END_STATEMENT",
            "TERMINAL_CLEANUP",
            "WORKER_EXCEPTION_RETURN",
        ],
    }
    write_json(root / args.result, result)
    if status != "PASS":
        raise ValueError(f"native harness validation failed: {totals}")
    return json.dumps({"result": args.result.as_posix(), "tests": totals})


def main() -> int:
    return execute(lambda: run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
