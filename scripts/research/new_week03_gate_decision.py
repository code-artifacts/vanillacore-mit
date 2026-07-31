"""Create the Week 3 gate decision from retained evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week3_gate import new_week3_gate_decision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: new_week3_gate_decision(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
