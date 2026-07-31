"""Export eight canonical L1 traces from a TLC state graph."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .traces import export_l1_traces


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: export_l1_traces(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
