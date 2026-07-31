from __future__ import annotations

import unittest

from scripts.research.common.tooling import ResearchError
from scripts.research.stress import classify_stress_cell, validate_stress_cells


def row(variant: str, workers: int = 2, workload: str = "compatible") -> dict[str, object]:
    return {
        "variant": variant,
        "workers": workers,
        "workload": workload,
        "iterations": 62500,
        "lockOperations": 125000,
        "acquireCalls": 62500,
        "firstGrants": 62500,
        "reentrantReturns": 0,
        "aborts": 0,
        "reentrantWaitLeakObservations": 0,
        "unexpectedErrors": 0,
        "timedOutWorkers": 0,
        "durationNanos": 1,
        "lockerMapEntries": 0,
        "ownerReferences": 0,
        "requestReferences": 0,
        "lockByMapEntries": 0,
        "waitMapEntries": 0,
        "abortRegistryEntries": 0,
    }


class StressClassificationTest(unittest.TestCase):
    def test_pristine_patch_targets_are_known(self) -> None:
        value = row("VC-HEAD-20230430")
        value["lockerMapEntries"] = -3
        value["reentrantWaitLeakObservations"] = 100
        result = classify_stress_cell(value)
        self.assertEqual("KNOWN_PR95_SYMPTOM", result["classification"])
        self.assertEqual(2, len(result["knownSymptoms"]))

    def test_reference_patch_target_symptom_is_unexplained(self) -> None:
        value = row("VC-REF-95")
        value["reentrantWaitLeakObservations"] = 1
        result = classify_stress_cell(value)
        self.assertEqual("UNEXPLAINED", result["classification"])

    def test_terminal_owner_residue_is_always_unexplained(self) -> None:
        value = row("VC-INST-PRISTINE")
        value["ownerReferences"] = 1
        result = classify_stress_cell(value)
        self.assertEqual("UNEXPLAINED", result["classification"])

    def test_matrix_requires_every_worker_workload_pair(self) -> None:
        workers = (2, 4, 8, 16)
        rows = [row("VC-REF-95", worker, workload) for worker in workers for workload in ("compatible", "conflict")]
        result = validate_stress_cells("VC-REF-95", rows, workers)
        self.assertEqual(1_000_000, result["totalLockOperations"])
        with self.assertRaises(ResearchError):
            validate_stress_cells("VC-REF-95", rows[:-1], workers)


if __name__ == "__main__":
    unittest.main()
