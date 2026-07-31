from __future__ import annotations

import unittest
from pathlib import Path

from scripts.research.model_selftest import (
    initial_state,
    invariant_violations,
    validate_canonical_corpus,
    validate_week2_fixtures,
)


class ModelSelfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.state = initial_state(("t1", "t2"), ("r1", "r2"))

    def test_compatibility_fault_is_rejected(self) -> None:
        self.state["held"]["t1"]["r1"] = "S"
        self.state["owners"]["r1"]["t1"] = "S"
        self.state["held"]["t2"]["r1"] = "X"
        self.state["owners"]["r1"]["t2"] = "X"
        self.state["xGranted"]["t2"] = ["r1"]
        self.assertEqual(["MutualExclusion"], invariant_violations(self.state))

    def test_strictness_fault_is_rejected(self) -> None:
        self.state["xGranted"]["t1"] = ["r1"]
        self.assertEqual(["StrictXRetention"], invariant_violations(self.state))

    def test_cleanup_fault_is_rejected(self) -> None:
        self.state["txState"]["t1"] = "COMMITTED"
        self.state["held"]["t1"]["r1"] = "S"
        self.state["owners"]["r1"]["t1"] = "S"
        self.assertEqual(["TerminalClean"], invariant_violations(self.state))

    def test_all_canonical_traces_replay(self) -> None:
        root = Path(__file__).resolve().parents[2]
        result = validate_canonical_corpus(root)
        self.assertEqual(8, result["traceCount"])

    def test_all_week2_fixtures_replay(self) -> None:
        root = Path(__file__).resolve().parents[2]
        result = validate_week2_fixtures(root)
        self.assertEqual(4, result["fixtureCount"])
        self.assertEqual(3, result["confirmed"])
        self.assertEqual(1, result["inconclusive"])


if __name__ == "__main__":
    unittest.main()
