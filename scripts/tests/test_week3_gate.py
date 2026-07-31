from __future__ import annotations

import unittest

from scripts.research.week3_gate import classify_week3_gate


class Week3GateDecisionTest(unittest.TestCase):
    def test_ready_requires_every_gate(self) -> None:
        self.assertEqual("READY_FOR_G3", classify_week3_gate(True, True, True, True))

    def test_low_overhead_failure_blocks_g3(self) -> None:
        self.assertEqual(
            "BLOCKED_FOR_G3", classify_week3_gate(True, True, True, False)
        )

    def test_foundational_failure_takes_precedence(self) -> None:
        self.assertEqual(
            "BLOCKED_FOUNDATIONAL_GATE",
            classify_week3_gate(True, False, True, True),
        )


if __name__ == "__main__":
    unittest.main()
