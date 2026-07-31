from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.research.common.tooling import (
    ResearchError,
    event_counts,
    median,
    parse_surefire_reports,
    remove_within,
    run_process,
)


class ToolingTest(unittest.TestCase):
    def test_median_handles_odd_and_even_samples(self) -> None:
        self.assertEqual(3, median([5, 1, 3]))
        self.assertEqual(2.5, median([4, 1, 3, 2]))

    def test_surefire_totals_are_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "TEST-a.xml").write_text(
                '<testsuite tests="2" failures="1" errors="0" skipped="0"/>',
                encoding="utf-8",
            )
            (directory / "TEST-b.xml").write_text(
                '<testsuite tests="3" failures="0" errors="1" skipped="1"/>',
                encoding="utf-8",
            )
            self.assertEqual(
                {"tests": 5, "failures": 1, "errors": 1, "skipped": 1},
                parse_surefire_reports(directory),
            )

    def test_event_counts_read_jsonl_portably(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = Path(temporary) / "trace.jsonl"
            trace.write_text(
                "\n".join(
                    json.dumps({"event_type": value})
                    for value in ("GRANT", "WAIT_BEGIN", "GRANT")
                ),
                encoding="utf-8",
            )
            counts, total = event_counts([trace])
            self.assertEqual(3, total)
            self.assertEqual({"GRANT": 2, "WAIT_BEGIN": 1}, counts)

    def test_remove_within_enforces_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            boundary = base / "raw"
            child = boundary / "run"
            child.mkdir(parents=True)
            remove_within(child, boundary)
            self.assertFalse(child.exists())
            with self.assertRaises(ResearchError):
                remove_within(boundary, boundary)
            with self.assertRaises(ResearchError):
                remove_within(base / "outside", boundary)

    def test_run_process_uses_current_platform(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run_process(
                [sys.executable, "-c", "print('portable')"],
                cwd=Path(temporary),
            )
            self.assertEqual(0, result.exit_code)
            self.assertEqual("portable", result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
