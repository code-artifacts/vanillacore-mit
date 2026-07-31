from __future__ import annotations

import unittest

from scripts.research.common.tooling import ResearchError
from scripts.research.low_sink import classify_low_sink_iteration


class LowSinkDecisionTest(unittest.TestCase):
    def test_target_and_hard_ceiling_pass(self) -> None:
        self.assertEqual("TARGET_PASS", classify_low_sink_iteration(1, 10.0))
        self.assertEqual("HARD_CEILING_PASS", classify_low_sink_iteration(1, 25.0))

    def test_first_failure_requires_second_iteration(self) -> None:
        self.assertEqual("OPTIMIZE_AGAIN", classify_low_sink_iteration(1, 25.001))

    def test_second_failure_blocks_g3(self) -> None:
        self.assertEqual("BLOCK_G3", classify_low_sink_iteration(2, 25.001))

    def test_rejects_out_of_range_iteration(self) -> None:
        with self.assertRaises(ResearchError):
            classify_low_sink_iteration(3, 0.0)


if __name__ == "__main__":
    unittest.main()
