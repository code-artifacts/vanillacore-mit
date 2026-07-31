"""Install and verify the pinned TLA+ command-line tools."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .tla import bootstrap_tla_tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(
        lambda: bootstrap_tla_tools(
            arguments.output,
            offline=arguments.offline,
            refresh=arguments.refresh,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
