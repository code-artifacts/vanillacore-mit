from __future__ import annotations

import unittest

from scripts.research.week4_gate import classify_g3


class Week4GateTest(unittest.TestCase):
    def test_all_gates_are_required(self) -> None:
        self.assertEqual(
            "G3_PASS",
            classify_g3(
                week3_prerequisite_passed=True,
                high_success_rate=1.0,
                low_success_rate=0.9,
                overhead_percent=25.0,
                silent_loss_or_residue=False,
                partial_order_passed=True,
                native_passed=True,
            ),
        )

    def test_inherited_overhead_block_fails_closed(self) -> None:
        self.assertEqual(
            "G3_FAIL",
            classify_g3(
                week3_prerequisite_passed=False,
                high_success_rate=1.0,
                low_success_rate=1.0,
                overhead_percent=10.0,
                silent_loss_or_residue=False,
                partial_order_passed=True,
                native_passed=True,
            ),
        )

    def test_low_replay_and_residue_fail(self) -> None:
        common = dict(
            week3_prerequisite_passed=True,
            high_success_rate=1.0,
            overhead_percent=10.0,
            partial_order_passed=True,
            native_passed=True,
        )
        self.assertEqual(
            "G3_FAIL",
            classify_g3(low_success_rate=0.89, silent_loss_or_residue=False, **common),
        )
        self.assertEqual(
            "G3_FAIL",
            classify_g3(low_success_rate=1.0, silent_loss_or_residue=True, **common),
        )


if __name__ == "__main__":
    unittest.main()
