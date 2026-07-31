from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.research.common.tooling import ResearchError
from scripts.research.tla import (
    configured_jar_path,
    load_toolchain_manifest,
    parse_tlc_metrics,
    verify_tla_jar,
)


class TlaToolingTest(unittest.TestCase):
    def test_manifest_pins_stable_release_and_bounds(self) -> None:
        root = Path(__file__).resolve().parents[2]
        manifest = load_toolchain_manifest(root)
        self.assertEqual("v1.7.4", manifest["releaseTag"])
        self.assertEqual(17, manifest["java"]["researchMajor"])
        self.assertEqual(["2x2", "3x3"], [m["id"] for m in manifest["smokeModels"]])
        self.assertTrue(str(configured_jar_path(root, manifest)).endswith("tla2tools.jar"))

    def test_parse_tlc_metrics(self) -> None:
        output = """
1,025 states generated, 512 distinct states found, 0 states left on queue.
The depth of the complete state graph search is 10.
"""
        self.assertEqual(
            {"generatedStates": 1025, "distinctStates": 512, "depth": 10},
            parse_tlc_metrics(output),
        )

    def test_verify_tla_jar_rejects_wrong_size(self) -> None:
        manifest = {
            "asset": {
                "sizeBytes": 2,
                "sha256": "0" * 64,
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tla2tools.jar"
            path.write_bytes(b"x")
            with self.assertRaises(ResearchError):
                verify_tla_jar(path, manifest)


if __name__ == "__main__":
    unittest.main()
