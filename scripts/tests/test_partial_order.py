from __future__ import annotations

import copy
import unittest

from scripts.research.common.tooling import repository_root
from scripts.research.partial_order import independent_fixture, respects_edges, validate_dag
from scripts.research.week4_schedule import DEFAULT_CORPUS, read_json


class PartialOrderTest(unittest.TestCase):
    def test_all_frozen_schedules_are_dags(self) -> None:
        root = repository_root()
        schedules = sorted((root / DEFAULT_CORPUS).glob("*.json"))
        self.assertEqual(8, len(schedules))
        for path in schedules:
            with self.subTest(schedule=path.stem):
                self.assertTrue(validate_dag(read_json(path)))

    def test_fixture_retains_two_legal_linearizations(self) -> None:
        fixture = independent_fixture()
        self.assertEqual(2, len(fixture["legalLinearizations"]))
        self.assertTrue(
            all(
                respects_edges(linearization, fixture["edges"])
                for linearization in fixture["legalLinearizations"]
            )
        )

    def test_cycle_is_rejected(self) -> None:
        root = repository_root()
        schedule = copy.deepcopy(read_json(next((root / DEFAULT_CORPUS).glob("*.json"))))
        first, second = schedule["observations"][:2]
        schedule["happensBefore"].extend(
            [
                {"before": first["id"], "after": second["id"], "kind": "TEST"},
                {"before": second["id"], "after": first["id"], "kind": "TEST"},
            ]
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_dag(schedule)


if __name__ == "__main__":
    unittest.main()
