from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.research.common.tooling import repository_root
from scripts.research.week4_schedule import (
    DEFAULT_CANONICAL,
    freeze_corpus,
    read_json,
    validate_schedule,
)


class Week4ScheduleTest(unittest.TestCase):
    def test_freezes_all_eight_canonical_schedules(self) -> None:
        root = repository_root()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            paths = freeze_corpus(root, output)
            canonical = read_json(root / DEFAULT_CANONICAL)
            self.assertEqual(8, len(paths))
            self.assertEqual(
                {trace["id"] for trace in canonical["traces"]},
                {path.stem for path in paths},
            )
            for path in paths:
                validate_schedule(read_json(path))

    def test_rejects_time_as_cross_thread_order(self) -> None:
        root = repository_root()
        with tempfile.TemporaryDirectory() as temporary:
            schedule_path = freeze_corpus(root, Path(temporary))[0]
            schedule = read_json(schedule_path)
            schedule["diagnostics"]["crossThreadOrder"] = "NANO_TIME"
            with self.assertRaisesRegex(ValueError, "explicit edges"):
                validate_schedule(schedule)

    def test_request_observations_use_stable_source_sites(self) -> None:
        root = repository_root()
        with tempfile.TemporaryDirectory() as temporary:
            schedules = [read_json(path) for path in freeze_corpus(root, Path(temporary))]
            request_sites = {
                observation["sourceSite"]
                for schedule in schedules
                for observation in schedule["observations"]
                if observation["eventType"] == "LOCK_CALL"
            }
            self.assertEqual({"locktable.s.call", "locktable.x.call"}, request_sites)


if __name__ == "__main__":
    unittest.main()
