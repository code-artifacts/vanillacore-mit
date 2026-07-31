from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.research.check_document_links import audit_documents


class DocumentLinksTest(unittest.TestCase):
    def test_accepts_local_file_heading_line_and_external_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "Example.java"
            source.parent.mkdir(parents=True)
            source.write_text("class Example {\n}\n", encoding="utf-8")
            target = root / "target.md"
            target.write_text("# Target Section\n", encoding="utf-8")
            document = root / "README.md"
            document.write_text(
                "\n".join(
                    (
                        "[`Example`](src/Example.java#L1)",
                        "[target](target.md#target-section)",
                        "[official](https://example.com/docs)",
                    )
                ),
                encoding="utf-8",
            )
            self.assertEqual([], audit_documents(root, [document, target]))

    def test_reports_missing_target_anchor_and_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.java"
            source.write_text("line\n", encoding="utf-8")
            target = root / "target.md"
            target.write_text("# Present\n", encoding="utf-8")
            document = root / "README.md"
            document.write_text(
                "\n".join(
                    (
                        "[missing](missing.md)",
                        "[anchor](target.md#absent)",
                        "[line](source.java#L2)",
                    )
                ),
                encoding="utf-8",
            )
            messages = [
                issue.message for issue in audit_documents(root, [document, target])
            ]
            self.assertTrue(any("does not exist" in message for message in messages))
            self.assertTrue(any("anchor does not exist" in message for message in messages))
            self.assertTrue(any("out of range" in message for message in messages))

    def test_reports_unlinked_inline_code_and_repository_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = root / "README.md"
            document.write_text(
                "See `Example` and scripts/research/example.py.\n", encoding="utf-8"
            )
            messages = [issue.message for issue in audit_documents(root, [document])]
            self.assertTrue(
                any("inline code reference is not linked" in message for message in messages)
            )
            self.assertTrue(
                any("repository path is not linked" in message for message in messages)
            )

    def test_ignores_fenced_code_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = root / "README.md"
            document.write_text(
                "```console\npython -m scripts.research.example\n```\n",
                encoding="utf-8",
            )
            self.assertEqual([], audit_documents(root, [document]))

    def test_rejects_ignored_local_targets_in_git_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("raw/\n", encoding="utf-8")
            raw = root / "raw"
            raw.mkdir()
            document = root / "README.md"
            document.write_text("[raw](raw/)\n", encoding="utf-8")
            messages = [issue.message for issue in audit_documents(root, [document])]
            self.assertTrue(any("not managed by Git" in message for message in messages))

    def test_reports_plain_java_class_and_section_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "Example.java"
            source.parent.mkdir(parents=True)
            source.write_text("class Example {}\n", encoding="utf-8")
            document = root / "README.md"
            document.write_text(
                "# Guide\nSee Example and Step 2.\n",
                encoding="utf-8",
            )
            messages = [issue.message for issue in audit_documents(root, [document])]
            self.assertTrue(
                any("Java class reference is not linked" in message for message in messages)
            )
            self.assertTrue(
                any("document section reference is not linked" in message for message in messages)
            )

    def test_rejects_absolute_backslash_and_file_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = root / "README.md"
            document.write_text(
                "\n".join(
                    (
                        "[absolute](C:/repo/file.md)",
                        "[backslash](src\\Example.java)",
                        "[uri](file:///repo/file.md)",
                    )
                ),
                encoding="utf-8",
            )
            messages = [issue.message for issue in audit_documents(root, [document])]
            self.assertTrue(any("absolute path" in message for message in messages))
            self.assertTrue(any("POSIX separators" in message for message in messages))
            self.assertTrue(any("file URI" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
