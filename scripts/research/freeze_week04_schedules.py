from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common.cli import execute
from .common.tooling import repository_root
from .week4_schedule import DEFAULT_CORPUS, freeze_corpus, sha256_file, write_json


DEFAULT_RESULT = Path("research/execution/week-04/results/step-01-schedule-dsl.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze Week 4 schedule DSL v0.1 corpus.")
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    return parser


def run(args: argparse.Namespace) -> str:
    root = repository_root()
    paths = freeze_corpus(root, args.output_directory)
    result = {
        "schemaVersion": 1,
        "step": "week-04-step-01-schedule-dsl",
        "status": "PASS",
        "scheduleSchema": "vc-schedule-0.1",
        "scheduleCount": len(paths),
        "schedules": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
            }
            for path in paths
        ],
        "orderingPolicy": {
            "wallClock": "DIAGNOSTIC_ONLY",
            "nanoTime": "DIAGNOSTIC_ONLY",
            "crossThread": "EXPLICIT_EDGES_ONLY",
        },
    }
    destination = root / args.result
    write_json(destination, result)
    return json.dumps(
        {"result": destination.relative_to(root).as_posix(), "scheduleCount": len(paths)}
    )


def main() -> int:
    return execute(lambda: run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
