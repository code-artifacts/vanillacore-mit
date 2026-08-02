from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common.cli import execute
from .common.tooling import parse_surefire_reports, repository_root, require_research_jdk17, run_maven
from .projection import DEFAULT_PROJECTION, read_projection, validate_projection
from .week4_schedule import sha256_file, write_json


DEFAULT_RESULT = Path("research/execution/week-04/results/step-06-direct-native-projection.json")
REPORT = "TEST-org.vanilladb.core.storage.tx.concurrency.DirectNativeProjectionTest.xml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Direct/Native L1 projection.")
    parser.add_argument("--projection", type=Path, default=DEFAULT_PROJECTION)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    return parser


def run(args: argparse.Namespace) -> str:
    root = repository_root()
    projection_path = root / args.projection
    counts = validate_projection(root, read_projection(projection_path))
    execution = run_maven(
        root,
        ["--batch-mode", "-Dtest=DirectNativeProjectionTest", "test"],
        jdk=require_research_jdk17(),
        timeout_seconds=300,
    )
    totals = parse_surefire_reports(root / "target/surefire-reports", [REPORT])
    status = "PASS" if totals == {"tests": 4, "failures": 0, "errors": 0, "skipped": 0} else "FAIL"
    result = {
        "schemaVersion": 1,
        "step": "week-04-step-06-direct-native-projection",
        "status": status,
        "projection": args.projection.as_posix(),
        "projectionSha256": sha256_file(projection_path),
        **counts,
        "tests": totals,
        "durationSeconds": execution.duration_seconds,
        "comparedFamilies": ["S/S", "S/X", "X/X", "COMMIT_GRANT", "ROLLBACK_GRANT"],
        "comparison": "EQUAL_L1_ACTIONS_WITH_NATIVE_CONTEXT_RETAINED",
    }
    write_json(root / args.result, result)
    if status != "PASS":
        raise ValueError(f"Direct/Native projection validation failed: {totals}")
    return json.dumps({"result": args.result.as_posix(), "tests": totals})


def main() -> int:
    return execute(lambda: run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
