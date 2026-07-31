"""Replay the deterministic Week 2 lock scenarios."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week2 import invoke_scenario_replay


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: invoke_scenario_replay(arguments.repetitions, arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
