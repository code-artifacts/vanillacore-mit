"""Measure deterministic trace completeness and low-mode overhead."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common.cli import execute
from .week2 import measure_trace_quality


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completeness-repetitions", type=int, default=20)
    parser.add_argument("--processes-per-mode", type=int, default=3)
    parser.add_argument("--samples-per-process", type=int, default=5)
    parser.add_argument("--operations-per-sample", type=int, default=100000)
    parser.add_argument("--warmup-operations", type=int, default=20000)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    return execute(
        lambda: measure_trace_quality(
            arguments.completeness_repetitions,
            arguments.processes_per_mode,
            arguments.samples_per_process,
            arguments.operations_per_sample,
            arguments.warmup_operations,
            arguments.output,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
