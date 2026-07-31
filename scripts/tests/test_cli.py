from __future__ import annotations

import importlib
import subprocess
import sys
import unittest
from pathlib import Path


CLI_MODULES = (
    "check_document_links",
    "bootstrap_tla_tools",
    "check_l1_model",
    "check_l1_mapping",
    "export_l1_traces",
    "check_l1_self_tests",
    "invoke_week03_g1_stress",
    "test_jdk_compatibility",
    "new_baseline_manifest",
    "invoke_dual_baseline_build",
    "invoke_repetition_campaign",
    "invoke_pr95_witness_matrix",
    "invoke_week02_event_sink_validation",
    "invoke_week02_instrumentation_validation",
    "invoke_week02_direct_harness_validation",
    "invoke_week02_scenario_replay",
    "measure_week02_trace_quality",
    "new_week02_gate_decision",
)


class CliTest(unittest.TestCase):
    def test_all_cli_modules_import(self) -> None:
        for name in CLI_MODULES:
            with self.subTest(module=name):
                module = importlib.import_module(f"scripts.research.{name}")
                self.assertTrue(callable(module.build_parser))

    def test_all_cli_help_commands_succeed(self) -> None:
        root = Path(__file__).resolve().parents[2]
        for name in CLI_MODULES:
            with self.subTest(module=name):
                result = subprocess.run(
                    [sys.executable, "-m", f"scripts.research.{name}", "--help"],
                    cwd=root,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_no_legacy_powershell_scripts_remain(self) -> None:
        root = Path(__file__).resolve().parents[2]
        self.assertEqual([], list((root / "scripts").rglob("*.ps1")))

    def test_documentation_uses_python_commands(self) -> None:
        root = Path(__file__).resolve().parents[2]
        markdown = list((root / "research").rglob("*.md"))
        markdown.append(root / "scripts/README.md")
        for path in markdown:
            with self.subTest(path=path.relative_to(root)):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(".ps1", text)
                self.assertNotIn("```powershell", text)


if __name__ == "__main__":
    unittest.main()
