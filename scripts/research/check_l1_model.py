"""Model-check the bounded VanillaCore L1 S/X specification."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .tla import check_l1_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: check_l1_model(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
