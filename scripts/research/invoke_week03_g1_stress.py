"""Run the Week 3 three-variant G1 LockTable stress matrix."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .stress import invoke_g1_stress


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--iterations", type=int, default=62500)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(
        lambda: invoke_g1_stress(
            arguments.output,
            iterations=arguments.iterations,
            timeout_seconds=arguments.timeout_seconds,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
