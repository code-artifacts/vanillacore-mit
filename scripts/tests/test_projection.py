from __future__ import annotations

import copy
import unittest

from scripts.research.common.tooling import repository_root
from scripts.research.projection import DEFAULT_PROJECTION, read_projection, validate_projection


class ProjectionTest(unittest.TestCase):
    def test_projection_covers_l1_and_context(self) -> None:
        root = repository_root()
        counts = validate_projection(root, read_projection(root / DEFAULT_PROJECTION))
        self.assertEqual(7, counts["rules"])
        self.assertEqual(5, counts["families"])
        self.assertEqual(4, counts["contextClasses"])

    def test_projection_rejects_missing_wake_rule(self) -> None:
        root = repository_root()
        projection = copy.deepcopy(read_projection(root / DEFAULT_PROJECTION))
        projection["rules"] = [
            rule for rule in projection["rules"] if rule["l1Action"] != "WAKE_THEN_GRANT"
        ]
        with self.assertRaisesRegex(ValueError, "missing L1 actions"):
            validate_projection(root, projection)


if __name__ == "__main__":
    unittest.main()
