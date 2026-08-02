from __future__ import annotations


def classify_g3(
    *,
    week3_prerequisite_passed: bool,
    high_success_rate: float,
    low_success_rate: float,
    overhead_percent: float,
    silent_loss_or_residue: bool,
    partial_order_passed: bool,
    native_passed: bool,
) -> str:
    if (
        not week3_prerequisite_passed
        or high_success_rate < 1.0
        or low_success_rate < 0.9
        or overhead_percent > 25.0
        or silent_loss_or_residue
        or not partial_order_passed
        or not native_passed
    ):
        return "G3_FAIL"
    return "G3_PASS"
