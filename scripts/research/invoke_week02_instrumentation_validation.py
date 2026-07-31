"""Validate all five LockTable trace event types."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week2 import invoke_instrumentation_validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: invoke_instrumentation_validation(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
