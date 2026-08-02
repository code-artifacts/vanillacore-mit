from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week4_campaign import run_week4_campaign


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Week 4 fresh-JVM G3 campaign.")
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return execute(lambda: run_week4_campaign(args.repetitions, args.output))


if __name__ == "__main__":
    raise SystemExit(main())
