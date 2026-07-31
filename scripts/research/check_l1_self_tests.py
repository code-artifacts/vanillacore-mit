"""Run legal, negative, and Week 2 regression self-tests for L1."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .model_selftest import check_l1_self_tests


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: check_l1_self_tests(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
