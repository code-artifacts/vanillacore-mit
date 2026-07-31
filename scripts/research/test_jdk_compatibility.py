"""Record the JDK 17/JDK 25 dependency compatibility probe."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week1 import test_jdk_compatibility


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(lambda: test_jdk_compatibility(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
