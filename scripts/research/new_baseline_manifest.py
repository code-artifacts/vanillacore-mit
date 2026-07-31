"""Create the pinned pristine/reference-fix baseline manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week1 import new_baseline_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upstream-commit",
        default="03e1f2df49bb9664c8bdae11cf911f56b74bbc57",
    )
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(
        lambda: new_baseline_manifest(
            arguments.upstream_commit, arguments.patch, arguments.output
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
