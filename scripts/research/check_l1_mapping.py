"""Validate the L1 model-to-implementation mapping ledger."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .mapping import check_l1_mapping


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: check_l1_mapping(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
