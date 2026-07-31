"""Build the pristine and PR #95 baselines in isolated worktrees."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week1 import invoke_dual_baseline_build


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(
        lambda: invoke_dual_baseline_build(
            arguments.timeout_seconds, arguments.output
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
