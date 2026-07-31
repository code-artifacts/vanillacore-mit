"""Portable process, Java, Git, and evidence helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


RESEARCH_JDK_VENDOR = "Eclipse Adoptium"
RESEARCH_JDK_RUNTIME = "17.0.20+8"


class ResearchError(RuntimeError):
    """Raised when a reproducibility invariant is not satisfied."""


@dataclass(frozen=True)
class CommandResult:
    """Result of a process that may have timed out."""

    command: list[str]
    started_at: str
    duration_seconds: float
    timed_out: bool
    exit_code: int
    process_id: int
    stdout: str = ""
    stderr: str = ""


def iso_now() -> str:
    return datetime.now().astimezone().isoformat()


def repository_root(start: Path | None = None) -> Path:
    location = (start or Path(__file__)).resolve()
    if location.is_file():
        location = location.parent
    result = subprocess.run(
        ["git", "-C", str(location), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def git(root: Path, *arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (result.stdout + result.stderr).strip()
    if check and result.returncode != 0:
        raise ResearchError(f"git {' '.join(arguments)} failed: {output}")
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ResearchError("Refusing to write a CSV without rows.")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def executable(home: Path, name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    path = home / "bin" / f"{name}{suffix}"
    if not path.is_file():
        raise ResearchError(f"{name} executable not found under '{home}'.")
    return path


def java_info(java_home: Path) -> dict[str, Any]:
    home = java_home.expanduser().resolve()
    result = subprocess.run(
        [str(executable(home, "java")), "-XshowSettings:properties", "-version"],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    settings = result.stdout + result.stderr

    def property_value(name: str) -> str:
        match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", settings)
        if not match:
            raise ResearchError(f"Unable to read {name} from '{home}'.")
        return match.group(1)

    major = property_value("java.specification.version").split(".")[-1]
    return {
        "Home": str(home),
        "Major": int(major),
        "Vendor": property_value("java.vendor"),
        "Version": property_value("java.version"),
        "RuntimeVersion": property_value("java.runtime.version"),
    }


def _registry_java_homes(major: int) -> list[Path]:
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []
    homes: list[Path] = []
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                rf"SOFTWARE\JavaSoft\JDK\{major}",
                0,
                winreg.KEY_READ | view,
            ) as key:
                homes.append(Path(winreg.QueryValueEx(key, "JavaHome")[0]))
        except OSError:
            continue
    return homes


def _default_java_homes() -> Iterable[Path]:
    if os.name == "nt":
        roots = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Eclipse Adoptium",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Java",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft",
        ]
        for root in roots:
            if root.is_dir():
                yield from root.glob("jdk-*")
    elif sys.platform == "darwin":
        root = Path("/Library/Java/JavaVirtualMachines")
        if root.is_dir():
            yield from root.glob("*/Contents/Home")
    else:
        for root in (Path("/usr/lib/jvm"), Path("/opt/java"), Path.home() / ".jdks"):
            if root.is_dir():
                yield from root.glob("*")


def resolve_java_home(major: int) -> dict[str, Any]:
    candidates: list[Path] = []
    for name in (f"VANILLADB_JDK{major}_HOME", f"JAVA{major}_HOME", "JAVA_HOME"):
        if os.environ.get(name):
            candidates.append(Path(os.environ[name]))
    candidates.extend(_registry_java_homes(major))
    candidates.extend(_default_java_homes())
    current_java = shutil.which("java")
    if current_java:
        candidates.append(Path(current_java).resolve().parent.parent)

    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(str(candidate.expanduser().resolve()))
        if key in seen or not candidate.is_dir():
            continue
        seen.add(key)
        try:
            info = java_info(candidate)
        except (OSError, ResearchError):
            continue
        if info["Major"] == major:
            return info
    raise ResearchError(
        f"No JDK {major} installation found. Set VANILLADB_JDK{major}_HOME."
    )


def require_research_jdk17() -> dict[str, Any]:
    info = resolve_java_home(17)
    if info["Vendor"] != RESEARCH_JDK_VENDOR:
        raise ResearchError(
            f"Expected {RESEARCH_JDK_VENDOR}, found '{info['Vendor']}'."
        )
    if info["RuntimeVersion"] != RESEARCH_JDK_RUNTIME:
        raise ResearchError(
            f"Expected Temurin runtime {RESEARCH_JDK_RUNTIME}, "
            f"found '{info['RuntimeVersion']}'."
        )
    return info


def java_environment(info: Mapping[str, Any]) -> dict[str, str]:
    environment = os.environ.copy()
    environment["JAVA_HOME"] = str(info["Home"])
    environment["PATH"] = str(Path(str(info["Home"])) / "bin") + os.pathsep + environment.get(
        "PATH", ""
    )
    return environment


def maven_executable() -> str:
    command = shutil.which("mvn") or shutil.which("mvn.cmd") or shutil.which("mvn.bat")
    if not command:
        raise ResearchError("Maven executable not found on PATH.")
    return command


def _kill_process_tree(process: subprocess.Popen[Any]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_process(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: int | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> CommandResult:
    if stdout_path:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
    if stderr_path:
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = iso_now()
    started = time.monotonic()
    stdout_stream: Any = stdout_path.open("w", encoding="utf-8", errors="replace") if stdout_path else subprocess.PIPE
    stderr_stream: Any = stderr_path.open("w", encoding="utf-8", errors="replace") if stderr_path else subprocess.PIPE
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(environment) if environment else None,
            stdout=stdout_stream,
            stderr=stderr_stream,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_tree(process)
            stdout, stderr = process.communicate()
        return CommandResult(
            command=list(command),
            started_at=started_at,
            duration_seconds=round(time.monotonic() - started, 3),
            timed_out=timed_out,
            exit_code=-1 if timed_out else process.returncode,
            process_id=process.pid,
            stdout=stdout or "",
            stderr=stderr or "",
        )
    finally:
        if stdout_path:
            stdout_stream.close()
        if stderr_path:
            stderr_stream.close()


def run_maven(
    root: Path,
    arguments: Sequence[str],
    *,
    jdk: Mapping[str, Any] | None = None,
    profile: bool = True,
    timeout_seconds: int | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    check: bool = True,
) -> CommandResult:
    selected_jdk = dict(jdk or require_research_jdk17())
    command = [maven_executable()]
    if profile:
        command.append("-Pmit-research")
    command.extend(arguments)
    result = run_process(
        command,
        cwd=root,
        environment=java_environment(selected_jdk),
        timeout_seconds=timeout_seconds,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    if check and (result.timed_out or result.exit_code != 0):
        detail = (result.stderr or result.stdout).strip()
        raise ResearchError(
            f"Maven failed with exit code {result.exit_code}: {detail[-2000:]}"
        )
    return result


def maven_version(root: Path, jdk: Mapping[str, Any]) -> str:
    result = run_maven(root, ["--version"], jdk=jdk, profile=False)
    return (result.stdout or result.stderr).splitlines()[0]


def empty_test_totals() -> dict[str, int]:
    return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}


def parse_surefire_reports(
    report_directory: Path,
    report_names: Sequence[str] | None = None,
) -> dict[str, int]:
    totals = empty_test_totals()
    paths = (
        [report_directory / name for name in report_names]
        if report_names is not None
        else sorted(report_directory.glob("TEST-*.xml"))
    )
    for path in paths:
        if not path.is_file():
            continue
        root = ET.parse(path).getroot()
        for key in totals:
            totals[key] += int(root.attrib.get(key, 0))
    return totals


def require_reports(
    report_directory: Path, report_names: Sequence[str]
) -> dict[str, int]:
    missing = [name for name in report_names if not (report_directory / name).is_file()]
    if missing:
        raise ResearchError(f"Missing Surefire reports: {', '.join(missing)}")
    return parse_surefire_reports(report_directory, report_names)


def remove_within(path: Path, root: Path) -> None:
    target = path.resolve()
    boundary = root.resolve()
    try:
        common = Path(os.path.commonpath([target, boundary]))
    except ValueError as error:
        raise ResearchError(f"Refusing to remove outside '{boundary}': {target}") from error
    if common != boundary or target == boundary:
        raise ResearchError(f"Refusing to remove outside '{boundary}': {target}")
    if target.exists():
        shutil.rmtree(target)


def event_counts(paths: Iterable[Path]) -> tuple[dict[str, int], int]:
    counts: dict[str, int] = {}
    total = 0
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                event = json.loads(line)
                event_type = str(event["event_type"])
                counts[event_type] = counts.get(event_type, 0) + 1
                total += 1
    return counts, total


def median(values: Sequence[float]) -> float:
    if not values:
        raise ResearchError("Median requires at least one value.")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def host_info() -> dict[str, str]:
    return {"os": platform.platform(), "architecture": platform.machine()}


def ensure_positive(**values: int) -> None:
    invalid = [name for name, value in values.items() if value <= 0]
    if invalid:
        raise ResearchError(f"Values must be positive: {', '.join(invalid)}")


def create_worktree(root: Path, destination: Path, commit: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    git(root, "worktree", "add", "--detach", str(destination), commit)


def remove_worktree(root: Path, destination: Path) -> None:
    if destination.exists():
        git(root, "worktree", "remove", "--force", str(destination), check=False)
    git(root, "worktree", "prune", check=False)


def first_line(value: str) -> str:
    lines = value.strip().splitlines()
    return lines[0] if lines else ""
