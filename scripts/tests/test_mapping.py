from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts.research.common.tooling import ResearchError, read_json
from scripts.research.mapping import MAPPING_PATH, validate_mapping


class MappingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]
        self.mapping = read_json(self.root / MAPPING_PATH)

    def test_mapping_covers_all_actions_and_invariants(self) -> None:
        summary = validate_mapping(self.root, self.mapping)
        self.assertEqual(11, summary["actionCount"])
        self.assertEqual(7, summary["invariantCount"])
        self.assertEqual(5, summary["strongActionCount"])
        self.assertEqual(7, summary["unassignedReviewers"])

    def test_mapping_rejects_unknown_event(self) -> None:
        mapping = copy.deepcopy(self.mapping)
        mapping["actions"][1]["requiredEvents"] = ["UNKNOWN_EVENT"]
        with self.assertRaises(ResearchError):
            validate_mapping(self.root, mapping)

    def test_mapping_rejects_stale_source_line(self) -> None:
        mapping = copy.deepcopy(self.mapping)
        mapping["actions"][1]["modelLocation"]["line"] = 1
        with self.assertRaises(ResearchError):
            validate_mapping(self.root, mapping)

    def test_mapping_rejects_strong_action_without_conditions(self) -> None:
        mapping = copy.deepcopy(self.mapping)
        del mapping["actions"][1]["strongConditions"]
        with self.assertRaises(ResearchError):
            validate_mapping(self.root, mapping)


if __name__ == "__main__":
    unittest.main()
