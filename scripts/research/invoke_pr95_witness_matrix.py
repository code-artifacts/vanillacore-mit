"""Run differential PR #95 witnesses against both pinned baselines."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week1 import invoke_pr95_witness_matrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(
        lambda: invoke_pr95_witness_matrix(
            arguments.timeout_seconds, arguments.output
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
