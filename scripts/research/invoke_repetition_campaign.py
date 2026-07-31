"""Run fresh-process repetition campaigns with isolated storage."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week1 import invoke_repetition_campaign


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=420)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--runs", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(
        lambda: invoke_repetition_campaign(
            arguments.repetitions,
            arguments.timeout_seconds,
            arguments.summary,
            arguments.runs,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
