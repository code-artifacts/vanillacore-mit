"""Week 1 environment and baseline research workflows."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .common.tooling import (
    ResearchError,
    create_worktree,
    ensure_positive,
    executable,
    first_line,
    git,
    host_info,
    iso_now,
    maven_version,
    parse_surefire_reports,
    read_json,
    remove_within,
    remove_worktree,
    repository_root,
    require_research_jdk17,
    resolve_java_home,
    run_maven,
    run_process,
    sha256_file,
    write_csv,
    write_json,
)


LOCK_TABLE = Path(
    "src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java"
)
WITNESS_FILES = (
    Path("src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTestProbe.java"),
    Path("src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTablePr95WitnessTest.java"),
)


def _default(root: Path, value: Path | None, relative: str) -> Path:
    return value.resolve() if value else root / relative


def _git_command(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_jdk_compatibility(output_path: Path | None = None) -> Path:
    root = repository_root()
    output = _default(
        root,
        output_path,
        "research/execution/week-01/results/step-01-environment.json",
    )
    jdk17 = resolve_java_home(17)
    jdk25 = resolve_java_home(25)
    jna_jar = (
        Path.home()
        / ".m2/repository/net/java/dev/jna/jna/4.0.0/jna-4.0.0.jar"
    )
    if not jna_jar.is_file():
        raise ResearchError(
            f"JNA 4.0.0 is not present at '{jna_jar}'. Resolve dependencies with JDK 17."
        )

    jdk17_probe = run_process(
        [str(executable(Path(jdk17["Home"]), "jar")), "tf", str(jna_jar)],
        cwd=root,
    )
    jdk25_probe = run_process(
        [str(executable(Path(jdk25["Home"]), "jar")), "tf", str(jna_jar)],
        cwd=root,
    )
    maven_probe = run_maven(
        root,
        ["--batch-mode", "-Denforcer.skip=true", "-DskipTests", "clean", "compile"],
        jdk=jdk25,
        check=False,
    )
    maven_text = maven_probe.stdout + maven_probe.stderr
    error_pattern = r"Invalid CEN header \(invalid zip64 extra data field size\)"
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "host": host_info(),
        "jdk17": jdk17,
        "jdk25": jdk25,
        "jna": {
            "coordinate": "net.java.dev.jna:jna:4.0.0",
            "path": str(jna_jar),
            "sha256": sha256_file(jna_jar),
        },
        "probes": {
            "jdk17JarReadable": jdk17_probe.exit_code == 0,
            "jdk25JarReadable": jdk25_probe.exit_code == 0,
            "jdk25JarError": first_line(jdk25_probe.stderr or jdk25_probe.stdout),
            "jdk25MavenExitCode": maven_probe.exit_code,
            "jdk25MavenMatchedZip64Error": bool(re.search(error_pattern, maven_text)),
        },
    }
    write_json(output, result)
    if not result["probes"]["jdk17JarReadable"]:
        raise ResearchError("JDK 17 unexpectedly rejected JNA 4.0.0.")
    if result["probes"]["jdk25JarReadable"] or not result["probes"][
        "jdk25MavenMatchedZip64Error"
    ]:
        raise ResearchError(
            "JDK 25 compatibility probe did not reproduce the expected Zip64 failure."
        )
    return output


def _baseline_repository_ref(root: Path, output: Path, upstream: str) -> str:
    current = git(root, "rev-parse", "HEAD")
    if git(root, "rev-parse", f"{current}:src") == git(
        root, "rev-parse", f"{upstream}:src"
    ):
        return current
    canonical = root / "research/execution/week-01/results/step-02-baselines.json"
    for manifest in dict.fromkeys((output, canonical)):
        if manifest.is_file():
            existing = read_json(manifest)
            candidate = existing.get("repository", {}).get("commit")
            if candidate and git(root, "rev-parse", f"{candidate}:src") == git(
                root, "rev-parse", f"{upstream}:src"
            ):
                return str(candidate)
    raise ResearchError(
        "Current source differs from upstream and no reusable baseline manifest exists."
    )


def new_baseline_manifest(
    upstream_commit: str = "03e1f2df49bb9664c8bdae11cf911f56b74bbc57",
    patch_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    root = repository_root()
    patch = _default(
        root, patch_path, "research/evidence/patches/pr-95-fix-locktable.patch"
    )
    output = _default(
        root,
        output_path,
        "research/execution/week-01/results/step-02-baselines.json",
    )
    upstream = git(root, "rev-parse", upstream_commit)
    repository_ref = _baseline_repository_ref(root, output, upstream)

    with tempfile.TemporaryDirectory(prefix="vanillacore-mit-baseline-") as temporary:
        worktree = Path(temporary) / "baseline"
        create_worktree(root, worktree, upstream)
        try:
            apply_check = _git_command(worktree, "apply", "--check", str(patch))
        finally:
            remove_worktree(root, worktree)

    patch_text = patch.read_text(encoding="utf-8")
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "variants": {"pristine": "VC-HEAD-20230430", "referenceFix": "VC-REF-95"},
        "repository": {
            "commit": repository_ref,
            "tree": git(root, "rev-parse", f"{repository_ref}^{{tree}}"),
            "sourceTree": git(root, "rev-parse", f"{repository_ref}:src"),
            "pomBlob": git(root, "rev-parse", f"{repository_ref}:pom.xml"),
            "branch": git(root, "branch", "--show-current"),
            "origin": git(root, "remote", "get-url", "origin"),
        },
        "upstream": {
            "commit": upstream,
            "tree": git(root, "rev-parse", f"{upstream}^{{tree}}"),
            "sourceTree": git(root, "rev-parse", f"{upstream}:src"),
            "pomBlob": git(root, "rev-parse", f"{upstream}:pom.xml"),
            "url": "https://github.com/vanilladb/vanillacore",
        },
        "patch": {
            "path": patch.relative_to(root).as_posix(),
            "sha256": sha256_file(patch),
            "gitBlob": git(root, "hash-object", "--no-filters", str(patch)),
            "mailCommitIds": re.findall(r"(?m)^From ([0-9a-f]{40}) ", patch_text),
            "upstreamPullRequest": "https://github.com/vanilladb/vanillacore/pull/95",
            "applyCheck": apply_check.returncode == 0,
        },
        "checks": {
            "repositorySourceMatchesUpstream": git(
                root, "rev-parse", f"{repository_ref}:src"
            )
            == git(root, "rev-parse", f"{upstream}:src"),
            "repositoryPomIntentionallyDiffers": git(
                root, "rev-parse", f"{repository_ref}:pom.xml"
            )
            != git(root, "rev-parse", f"{upstream}:pom.xml"),
        },
    }
    write_json(output, result)
    if not result["patch"]["applyCheck"]:
        raise ResearchError("PR #95 patch does not apply to the upstream baseline.")
    if not result["checks"]["repositorySourceMatchesUpstream"]:
        raise ResearchError("Pinned repository source differs from upstream.")
    return output


def _build_variant(
    variant: str,
    worktree: Path,
    raw_directory: Path,
    jdk: Mapping[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    result = run_maven(
        worktree,
        ["--batch-mode", "clean", "test"],
        jdk=jdk,
        profile=False,
        timeout_seconds=timeout_seconds,
        stdout_path=raw_directory / f"{variant}.stdout.log",
        stderr_path=raw_directory / f"{variant}.stderr.log",
        check=False,
    )
    return {
        "variant": variant,
        "command": "mvn --batch-mode clean test",
        "startedAt": result.started_at,
        "durationSeconds": result.duration_seconds,
        "timedOut": result.timed_out,
        "exitCode": result.exit_code,
        "tests": parse_surefire_reports(worktree / "target/surefire-reports"),
        "lockTableSha256": sha256_file(worktree / LOCK_TABLE),
    }


def invoke_dual_baseline_build(
    timeout_seconds: int = 600, output_path: Path | None = None
) -> Path:
    ensure_positive(timeout_seconds=timeout_seconds)
    root = repository_root()
    identity = read_json(
        root / "research/execution/week-01/results/step-02-baselines.json"
    )
    patch = root / identity["patch"]["path"]
    jdk = require_research_jdk17()
    if sha256_file(patch) != identity["patch"]["sha256"]:
        raise ResearchError("PR #95 patch hash differs from the baseline manifest.")
    output = _default(
        root,
        output_path,
        "research/execution/week-01/results/step-03-build-matrix.json",
    )
    raw = root / "research/execution/week-01/raw/step-03"
    raw.mkdir(parents=True, exist_ok=True)
    worktree_root = Path(tempfile.mkdtemp(prefix="vanillacore-mit-step03-"))
    pristine = worktree_root / "pristine"
    fixed = worktree_root / "pr95"
    completed = False
    try:
        create_worktree(root, pristine, identity["upstream"]["commit"])
        create_worktree(root, fixed, identity["upstream"]["commit"])
        check = _git_command(fixed, "apply", "--check", str(patch))
        if check.returncode != 0:
            raise ResearchError(f"PR #95 patch dry-run failed: {check.stderr}")
        git(fixed, "apply", str(patch))
        builds = [
            _build_variant("VC-HEAD-20230430", pristine, raw, jdk, timeout_seconds),
            _build_variant("VC-REF-95", fixed, raw, jdk, timeout_seconds),
        ]
        result = {
            "schemaVersion": 1,
            "recordedAt": iso_now(),
            "upstreamCommit": identity["upstream"]["commit"],
            "patchSha256": identity["patch"]["sha256"],
            "jdk": jdk,
            "mavenVersion": maven_version(root, jdk),
            "timeoutSeconds": timeout_seconds,
            "builds": builds,
        }
        write_json(output, result)
        failed = [
            build
            for build in builds
            if build["timedOut"]
            or build["exitCode"] != 0
            or build["tests"]["failures"] != 0
            or build["tests"]["errors"] != 0
        ]
        if failed:
            raise ResearchError(
                f"One or more baseline builds failed. Worktrees retained at {worktree_root}"
            )
        completed = True
        return output
    finally:
        if completed:
            remove_worktree(root, pristine)
            remove_worktree(root, fixed)
            shutil.rmtree(worktree_root, ignore_errors=True)


def _isolated_config(template: Path, run_directory: Path) -> Path:
    storage = run_directory / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    value = storage.as_posix()
    config = template.read_text(encoding="utf-8")
    config = re.sub(
        r"(?m)^org\.vanilladb\.core\.storage\.file\.FileMgr\.DB_FILES_DIR=.*$",
        f"org.vanilladb.core.storage.file.FileMgr.DB_FILES_DIR={value}",
        config,
    )
    config = re.sub(
        r"(?m)^org\.vanilladb\.core\.storage\.file\.FileMgr\.LOG_FILES_DIR=.*$",
        f"org.vanilladb.core.storage.file.FileMgr.LOG_FILES_DIR={value}",
        config,
    )
    path = run_directory / "vanilladb.properties"
    path.write_text(config, encoding="utf-8", newline="\n")
    return path


def invoke_repetition_campaign(
    repetitions: int = 20,
    timeout_seconds: int = 420,
    summary_path: Path | None = None,
    runs_path: Path | None = None,
) -> tuple[Path, Path]:
    ensure_positive(repetitions=repetitions, timeout_seconds=timeout_seconds)
    root = repository_root()
    jdk = require_research_jdk17()
    summary = _default(
        root,
        summary_path,
        "research/execution/week-01/results/step-04-repetition-summary.json",
    )
    runs_output = _default(
        root, runs_path, "research/execution/week-01/results/step-04-runs.csv"
    )
    raw_root = root / "research/execution/week-01/raw/step-04"
    raw_root.mkdir(parents=True, exist_ok=True)
    template = root / "src/test/resources/org/vanilladb/core/vanilladb.properties"
    reports = root / "target/surefire-reports"
    campaigns = (
        {"id": "default-suite", "selector": "FullTestSuite", "expectedTests": 110},
        {
            "id": "omitted-five",
            "selector": "ParserTest,SpResultSetTest,ConstantRangeTest,ConstantTest,BTreeIndexConcurrentTest",
            "expectedTests": 10,
        },
    )
    run_results: list[dict[str, Any]] = []
    for campaign in campaigns:
        for repetition in range(1, repetitions + 1):
            run_id = f"{campaign['id']}-{repetition:02d}"
            run_directory = raw_root / run_id
            if run_directory.exists():
                remove_within(run_directory, raw_root)
            run_directory.mkdir(parents=True)
            config = _isolated_config(template, run_directory)
            if reports.exists():
                remove_within(reports, root)
            stdout = run_directory / "stdout.log"
            stderr = run_directory / "stderr.log"
            process = run_maven(
                root,
                [
                    "--batch-mode",
                    f"-Dtest={campaign['selector']}",
                    "-DforkCount=1",
                    "-DreuseForks=false",
                    "-Dsurefire.rerunFailingTestsCount=0",
                    f"-Dorg.vanilladb.core.config.file={config}",
                    "test",
                ],
                jdk=jdk,
                timeout_seconds=timeout_seconds,
                stdout_path=stdout,
                stderr_path=stderr,
                check=False,
            )
            totals = parse_surefire_reports(reports)
            passed = (
                not process.timed_out
                and process.exit_code == 0
                and totals["tests"] == campaign["expectedTests"]
                and all(totals[key] == 0 for key in ("failures", "errors", "skipped"))
            )
            outcome = "pass" if passed else ("timeout" if process.timed_out else "fail")
            row = {
                "runId": run_id,
                "campaign": campaign["id"],
                "repetition": repetition,
                "selector": campaign["selector"],
                "startedAt": process.started_at,
                "durationSeconds": process.duration_seconds,
                "processId": process.process_id,
                "exitCode": process.exit_code,
                "outcome": outcome,
                **totals,
                "configSha256": sha256_file(config),
                "stdoutSha256": sha256_file(stdout),
                "stderrSha256": sha256_file(stderr),
            }
            run_results.append(row)
            print(
                f"[{run_id}] {outcome} ({totals['tests']} tests, "
                f"{process.duration_seconds:.1f}s)"
            )

    campaign_results = []
    for campaign in campaigns:
        selected = [row for row in run_results if row["campaign"] == campaign["id"]]
        durations = sorted(float(row["durationSeconds"]) for row in selected)
        campaign_results.append(
            {
                "id": campaign["id"],
                "selector": campaign["selector"],
                "repetitionsRequested": repetitions,
                "repetitionsCompleted": len(selected),
                "passes": sum(row["outcome"] == "pass" for row in selected),
                "failures": sum(row["outcome"] != "pass" for row in selected),
                "expectedTestsPerRun": campaign["expectedTests"],
                "durationSeconds": {
                    "min": durations[0],
                    "median": durations[len(durations) // 2],
                    "max": durations[-1],
                },
            }
        )
    result = {
        "schemaVersion": 1,
        "recordedAt": iso_now(),
        "repositoryCommit": git(root, "rev-parse", "HEAD"),
        "jdk": jdk,
        "mavenVersion": maven_version(root, jdk),
        "freshMavenProcesses": len(run_results),
        "forkCount": 1,
        "reuseForks": False,
        "rerunFailingTestsCount": 0,
        "timeoutSeconds": timeout_seconds,
        "isolatedStorageRootPerRun": True,
        "campaigns": campaign_results,
    }
    write_json(summary, result)
    write_csv(runs_output, run_results)
    failed = [row for row in run_results if row["outcome"] != "pass"]
    if len(run_results) != len(campaigns) * repetitions or failed:
        raise ResearchError(f"Repetition gate failed: {len(failed)} non-passing runs.")
    return summary, runs_output


def _copy_witness_sources(root: Path, destination: Path) -> None:
    for relative in WITNESS_FILES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)


def _run_witnesses(
    variant: str,
    worktree: Path,
    raw: Path,
    jdk: Mapping[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    stdout = raw / f"{variant}.stdout.log"
    stderr = raw / f"{variant}.stderr.log"
    process = run_maven(
        worktree,
        [
            "--batch-mode",
            "-Dtest=LockTablePr95WitnessTest",
            "-Dvanillacore.mit.pr95Witnesses=true",
            "-Dsurefire.rerunFailingTestsCount=0",
            "test",
        ],
        jdk=jdk,
        timeout_seconds=timeout_seconds,
        stdout_path=stdout,
        stderr_path=stderr,
        check=False,
    )
    report = parse_surefire_reports(
        worktree / "target/surefire-reports",
        [
            "TEST-org.vanilladb.core.storage.tx.concurrency.LockTablePr95WitnessTest.xml"
        ],
    )
    return {
        "variant": variant,
        "startedAt": process.started_at,
        "durationSeconds": process.duration_seconds,
        "timedOut": process.timed_out,
        "exitCode": process.exit_code,
        **report,
        "stdoutSha256": sha256_file(stdout),
        "stderrSha256": sha256_file(stderr),
        "lockTableSha256": sha256_file(worktree / LOCK_TABLE),
    }


def invoke_pr95_witness_matrix(
    timeout_seconds: int = 180, output_path: Path | None = None
) -> Path:
    ensure_positive(timeout_seconds=timeout_seconds)
    root = repository_root()
    identity = read_json(
        root / "research/execution/week-01/results/step-02-baselines.json"
    )
    patch = root / identity["patch"]["path"]
    if sha256_file(patch) != identity["patch"]["sha256"]:
        raise ResearchError("PR #95 patch hash differs from the baseline manifest.")
    jdk = require_research_jdk17()
    output = _default(
        root,
        output_path,
        "research/execution/week-01/results/step-06-pr95-witness-matrix.json",
    )
    raw = root / "research/execution/week-01/raw/step-06"
    raw.mkdir(parents=True, exist_ok=True)
    baseline_commit = identity["repository"]["commit"]
    main_tree = git(root, "rev-parse", f"{baseline_commit}:src/main")
    upstream_main_tree = git(
        root, "rev-parse", f"{identity['upstream']['commit']}:src/main"
    )
    if main_tree != upstream_main_tree:
        raise ResearchError("Baseline production source differs from pinned upstream.")

    worktree_root = Path(tempfile.mkdtemp(prefix="vanillacore-mit-step06-"))
    pristine = worktree_root / "pristine"
    fixed = worktree_root / "pr95"
    passed = False
    try:
        create_worktree(root, pristine, baseline_commit)
        create_worktree(root, fixed, baseline_commit)
        _copy_witness_sources(root, pristine)
        _copy_witness_sources(root, fixed)
        check = _git_command(fixed, "apply", "--check", str(patch))
        if check.returncode != 0:
            raise ResearchError(f"PR #95 patch dry-run failed: {check.stderr}")
        git(fixed, "apply", str(patch))
        matrix = [
            _run_witnesses("VC-HEAD-20230430", pristine, raw, jdk, timeout_seconds),
            _run_witnesses("VC-REF-95", fixed, raw, jdk, timeout_seconds),
        ]
        passed = (
            matrix[0]["exitCode"] != 0
            and matrix[0]["tests"] == 2
            and matrix[0]["failures"] == 2
            and matrix[0]["errors"] == 0
            and matrix[1]["exitCode"] == 0
            and matrix[1]["tests"] == 2
            and matrix[1]["failures"] == 0
            and matrix[1]["errors"] == 0
            and not matrix[0]["timedOut"]
            and not matrix[1]["timedOut"]
        )
        result = {
            "schemaVersion": 1,
            "recordedAt": iso_now(),
            "repositoryCommit": baseline_commit,
            "upstreamCommit": identity["upstream"]["commit"],
            "productionSourceMatchesUpstream": True,
            "patchSha256": identity["patch"]["sha256"],
            "jdk": jdk,
            "witnesses": [
                "lockerRegistrySupportsUpdatesFromDistinctAnchors",
                "reentrantGrantRemovesWaitRegistration",
            ],
            "expected": {"pristineFailures": 2, "referenceFixFailures": 0},
            "matrix": matrix,
            "matrixPassed": passed,
        }
        write_json(output, result)
        if not passed:
            raise ResearchError(
                f"PR #95 witness matrix failed. Worktrees retained at {worktree_root}"
            )
        return output
    finally:
        if passed:
            remove_worktree(root, pristine)
            remove_worktree(root, fixed)
            shutil.rmtree(worktree_root, ignore_errors=True)
