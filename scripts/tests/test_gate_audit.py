from __future__ import annotations

import copy
import unittest

from scripts.research.common.tooling import repository_root
from scripts.research.gate_audit import DEFAULT_AUDIT, read_audit, validate_gate_audit


class GateAuditTest(unittest.TestCase):
    def test_complete_audit_allows_only_monitor_free_blocking(self) -> None:
        root = repository_root()
        counts = validate_gate_audit(root, read_audit(root / DEFAULT_AUDIT))
        self.assertEqual(30, counts["points"])
        self.assertEqual(10, counts["blockingAllowed"])
        self.assertEqual(20, counts["observeOnly"])

    def test_rejects_blocking_gate_while_monitor_is_held(self) -> None:
        root = repository_root()
        audit = copy.deepcopy(read_audit(root / DEFAULT_AUDIT))
        wait = next(
            point for point in audit["points"] if point["sourceSite"] == "locktable.s.wait"
        )
        wait["controllerWait"] = "BLOCKING_ALLOWED"
        with self.assertRaisesRegex(ValueError, "holds anchor monitor"):
            validate_gate_audit(root, audit)

    def test_rejects_missing_required_site(self) -> None:
        root = repository_root()
        audit = copy.deepcopy(read_audit(root / DEFAULT_AUDIT))
        audit["points"] = [
            point
            for point in audit["points"]
            if point["sourceSite"] != "locktable.x.call"
        ]
        with self.assertRaisesRegex(ValueError, "missing required sites"):
            validate_gate_audit(root, audit)


if __name__ == "__main__":
    unittest.main()
