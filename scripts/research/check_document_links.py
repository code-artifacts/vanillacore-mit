from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote


DOCUMENT_SUFFIXES = {".md", ".mdx", ".rst", ".adoc", ".txt"}
EXTERNAL_SCHEMES = {"http", "https", "mailto"}
INLINE_LINK = re.compile(
    r"!?\[(?P<label>[^\]]*)\]\("
    r"(?P<target><[^>]+>|(?:[^()\s]|\([^)]*\))+)"
    r"(?:\s+[\"'][^\"']*[\"'])?\)"
)
REFERENCE_LINK = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\[(?P<id>[^\]]*)\]")
REFERENCE_DEFINITION = re.compile(
    r"(?m)^[ \t]{0,3}\[(?P<id>[^\]]+)\]:[ \t]*(?P<target><[^>]+>|\S+)"
)
INLINE_CODE = re.compile(r"(?<!`)`(?P<value>[^`\n]+)`(?!`)")
EXPLICIT_ANCHOR = re.compile(
    r"<a\s+(?:[^>]*?\s)?(?:id|name)=[\"'](?P<id>[^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)
HEADING = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$")
LINE_FRAGMENT = re.compile(r"^L(?P<start>\d+)(?:-L(?P<end>\d+))?$")
ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")
BARE_REPOSITORY_PATH = re.compile(
    r"(?<![\w./-])"
    r"(?P<path>(?:src|research|scripts|tla|doc|ai|\.github)/"
    r"[A-Za-z0-9_./+-]+(?:#[A-Za-z0-9_.:-]+)?)"
)
SECTION_REFERENCE = re.compile(
    r"(?:第\s*\d+(?:\.\d+)*\s*节|Step\s*\d+|步骤\s*\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    path: Path
    line: int
    message: str

    def render(self, root: Path) -> str:
        try:
            relative = self.path.relative_to(root)
        except ValueError:
            relative = self.path
        return f"{relative.as_posix()}:{self.line}: {self.message}"


@dataclass(frozen=True)
class Link:
    target: str
    start: int
    end: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate locally navigable references in repository documents."
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="repository root; defaults to the current Git worktree",
    )
    return parser


def repository_root(value: Path | None = None) -> Path:
    if value is not None:
        return value.resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "not inside a Git worktree")
    return Path(result.stdout.strip()).resolve()


def git_documents(root: Path) -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "*.md",
            "*.mdx",
            "*.rst",
            "*.adoc",
            "*.txt",
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return sorted(
        root / Path(raw.decode("utf-8"))
        for raw in result.stdout.split(b"\0")
        if raw
    )


@lru_cache(maxsize=None)
def _git_managed_paths(root: Path) -> tuple[Path, ...] | None:
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return tuple(
        (root / Path(raw.decode("utf-8"))).resolve()
        for raw in result.stdout.split(b"\0")
        if raw
    )


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _mask_fenced_code(text: str) -> str:
    lines = text.splitlines(keepends=True)
    masked: list[str] = []
    fence_character = ""
    fence_length = 0
    for line in lines:
        match = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if not fence_character:
                fence_character = marker[0]
                fence_length = len(marker)
            elif marker[0] == fence_character and len(marker) >= fence_length:
                fence_character = ""
                fence_length = 0
            masked.append("".join("\n" if char == "\n" else " " for char in line))
        elif fence_character:
            masked.append("".join("\n" if char == "\n" else " " for char in line))
        else:
            masked.append(line)
    return "".join(masked)


def _reference_definitions(text: str) -> dict[str, str]:
    return {
        match.group("id").strip().casefold(): match.group("target").strip()
        for match in REFERENCE_DEFINITION.finditer(text)
    }


def _links(text: str) -> list[Link]:
    links = [
        Link(match.group("target").strip(), match.start(), match.end())
        for match in INLINE_LINK.finditer(text)
    ]
    definitions = _reference_definitions(text)
    for match in REFERENCE_LINK.finditer(text):
        identifier = (match.group("id") or match.group("label")).strip().casefold()
        target = definitions.get(identifier)
        if target is not None:
            links.append(Link(target, match.start(), match.end()))
    links.extend(
        Link(match.group("target").strip(), match.start(), match.end())
        for match in REFERENCE_DEFINITION.finditer(text)
    )
    return sorted(links, key=lambda link: link.start)


def _mask_ranges(text: str, ranges: list[tuple[int, int]]) -> str:
    characters = list(text)
    for start, end in ranges:
        for index in range(start, end):
            if characters[index] != "\n":
                characters[index] = " "
    return "".join(characters)


def _heading_anchors(text: str) -> set[str]:
    anchors = {match.group("id") for match in EXPLICIT_ANCHOR.finditer(text)}
    duplicates: dict[str, int] = {}
    for match in HEADING.finditer(_mask_fenced_code(text)):
        title = re.sub(r"<[^>]+>", "", match.group("title"))
        title = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", title)
        title = title.strip().lower()
        title = re.sub(r"[^\w\u4e00-\u9fff -]", "", title)
        base = re.sub(r"[ \t]+", "-", title)
        duplicate = duplicates.get(base, 0)
        duplicates[base] = duplicate + 1
        anchors.add(base if duplicate == 0 else f"{base}-{duplicate}")
    return anchors


@lru_cache(maxsize=None)
def _java_class_names(root: Path) -> tuple[str, ...]:
    names: set[str] = set()
    for path in root.rglob("*.java"):
        if ".git" in path.parts or "target" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(
            rf"\b(?:class|interface|enum)\s+{re.escape(path.stem)}\b",
            text,
        ):
            names.add(path.stem)
    return tuple(sorted(names, key=lambda name: (-len(name), name)))


def _split_target(target: str) -> tuple[str, str]:
    normalized = target.strip("<>")
    if "#" not in normalized:
        return normalized, ""
    path, fragment = normalized.split("#", 1)
    return path, unquote(fragment)


def _validate_link(
    root: Path,
    document: Path,
    text: str,
    link: Link,
) -> Issue | None:
    target = link.target.strip("<>")
    line = _line_number(text, link.start)
    scheme_match = re.match(r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*):", target)
    if scheme_match and scheme_match.group("scheme").lower() in EXTERNAL_SCHEMES:
        return None
    if target.lower().startswith("file:"):
        return Issue(document, line, f"file URI is not a repository-relative link: {target}")
    if "\\" in target:
        return Issue(document, line, f"link must use POSIX separators: {target}")
    path_value, fragment = _split_target(target)
    if ABSOLUTE_WINDOWS_PATH.match(path_value) or Path(path_value).is_absolute():
        return Issue(document, line, f"absolute path is not allowed: {target}")

    destination = document if not path_value else (document.parent / unquote(path_value))
    destination = destination.resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        return Issue(document, line, f"link escapes the repository: {target}")
    if not destination.exists():
        return Issue(document, line, f"link target does not exist: {target}")
    managed_paths = _git_managed_paths(root)
    if managed_paths is not None:
        if destination.is_file():
            managed = destination in managed_paths
        else:
            managed = any(
                path == destination or destination in path.parents
                for path in managed_paths
            )
        if not managed:
            return Issue(document, line, f"link target is not managed by Git: {target}")
    if not fragment:
        return None

    line_match = LINE_FRAGMENT.fullmatch(fragment)
    if line_match:
        if not destination.is_file():
            return Issue(document, line, f"line fragment targets a directory: {target}")
        line_count = len(destination.read_text(encoding="utf-8").splitlines())
        start = int(line_match.group("start"))
        end = int(line_match.group("end") or start)
        if start < 1 or end < start or end > line_count:
            return Issue(document, line, f"line fragment is out of range: {target}")
        return None

    if destination.suffix.lower() not in DOCUMENT_SUFFIXES:
        return Issue(document, line, f"non-document fragment must use #L<n>: {target}")
    anchors = _heading_anchors(destination.read_text(encoding="utf-8"))
    if fragment not in anchors:
        return Issue(document, line, f"document anchor does not exist: {target}")
    return None


def audit_document(root: Path, document: Path) -> list[Issue]:
    text = document.read_text(encoding="utf-8")
    prose = _mask_fenced_code(text)
    links = _links(prose)
    issues = [
        issue
        for link in links
        if (issue := _validate_link(root, document, prose, link)) is not None
    ]

    link_ranges = [(link.start, link.end) for link in links]
    masked_links = _mask_ranges(prose, link_ranges)
    code_ranges: list[tuple[int, int]] = []
    for match in INLINE_CODE.finditer(masked_links):
        code_ranges.append((match.start(), match.end()))
        issues.append(
            Issue(
                document,
                _line_number(masked_links, match.start()),
                f"inline code reference is not linked: `{match.group('value')}`",
            )
        )

    searchable = _mask_ranges(masked_links, code_ranges)
    for match in BARE_REPOSITORY_PATH.finditer(searchable):
        issues.append(
            Issue(
                document,
                _line_number(searchable, match.start()),
                f"repository path is not linked: {match.group('path')}",
            )
        )
    for class_name in _java_class_names(root):
        if len(class_name) < 4:
            continue
        for match in re.finditer(
            rf"(?<![\w`]){re.escape(class_name)}(?![\w`])",
            searchable,
        ):
            issues.append(
                Issue(
                    document,
                    _line_number(searchable, match.start()),
                    f"Java class reference is not linked: {class_name}",
                )
            )

    heading_ranges = [(match.start(), match.end()) for match in HEADING.finditer(searchable)]
    section_searchable = _mask_ranges(searchable, heading_ranges)
    for match in SECTION_REFERENCE.finditer(section_searchable):
        issues.append(
            Issue(
                document,
                _line_number(section_searchable, match.start()),
                f"document section reference is not linked: {match.group(0)}",
            )
        )
    return issues


def audit_documents(root: Path, documents: list[Path]) -> list[Issue]:
    issues: list[Issue] = []
    for document in documents:
        issues.extend(audit_document(root, document))
    return sorted(issues, key=lambda issue: (str(issue.path), issue.line, issue.message))


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = repository_root(args.root)
        documents = git_documents(root)
        issues = audit_documents(root, documents)
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"document link audit failed: {error}", file=sys.stderr)
        return 2
    for issue in issues:
        print(issue.render(root))
    if issues:
        print(f"{len(issues)} documentation reference issue(s) found.", file=sys.stderr)
        return 1
    print(f"Validated {len(documents)} document(s); all references are navigable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
