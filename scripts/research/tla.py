"""Pinned TLA+ toolchain installation and TLC execution helpers."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from .common.tooling import (
    ResearchError,
    executable,
    git,
    iso_now,
    java_environment,
    read_json,
    repository_root,
    require_research_jdk17,
    run_process,
    sha256_file,
    write_json,
)


TOOLCHAIN_MANIFEST = Path("tla/toolchain.json")
DEFAULT_RESULT = Path(
    "research/execution/week-03/results/step-01-tla-toolchain.json"
)
DEFAULT_L1_RESULT = Path(
    "research/execution/week-03/results/step-02-l1-model.json"
)
USER_AGENT = "vanillacore-mit-tla-bootstrap/1"


def load_toolchain_manifest(root: Path) -> dict[str, Any]:
    manifest = read_json(root / TOOLCHAIN_MANIFEST)
    required = {
        "schemaVersion",
        "releaseTag",
        "tlcVersion",
        "asset",
        "java",
        "installation",
        "smokeModels",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ResearchError(f"TLA+ toolchain manifest is missing: {missing}")
    asset = manifest["asset"]
    for name in ("name", "url", "sizeBytes", "sha256"):
        if name not in asset:
            raise ResearchError(f"TLA+ asset is missing '{name}'.")
    if not re.fullmatch(r"[0-9A-F]{64}", asset["sha256"]):
        raise ResearchError("TLA+ asset SHA-256 must be uppercase hexadecimal.")
    return manifest


def configured_jar_path(root: Path, manifest: Mapping[str, Any]) -> Path:
    relative = Path(manifest["installation"]["relativeJarPath"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ResearchError("TLA+ jar path must remain within the repository.")
    return (root / relative).resolve()


def verify_tla_jar(path: Path, manifest: Mapping[str, Any]) -> None:
    if not path.is_file():
        raise ResearchError(f"TLA+ tools jar not found at '{path}'.")
    asset = manifest["asset"]
    actual_size = path.stat().st_size
    if actual_size != asset["sizeBytes"]:
        raise ResearchError(
            f"TLA+ tools size mismatch: expected {asset['sizeBytes']}, "
            f"found {actual_size}."
        )
    actual_hash = sha256_file(path)
    if actual_hash != asset["sha256"]:
        raise ResearchError(
            f"TLA+ tools SHA-256 mismatch: expected {asset['sha256']}, "
            f"found {actual_hash}."
        )


def install_tla_tools(
    root: Path,
    manifest: Mapping[str, Any],
    *,
    offline: bool = False,
    refresh: bool = False,
) -> tuple[Path, str]:
    target = configured_jar_path(root, manifest)
    if target.is_file() and not refresh:
        verify_tla_jar(target, manifest)
        return target, "reused"
    if offline:
        raise ResearchError("Offline mode requires an existing verified TLA+ jar.")

    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        manifest["asset"]["url"], headers={"User-Agent": USER_AGENT}
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix="tla2tools-", suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            with urllib.request.urlopen(request, timeout=60) as response:
                shutil.copyfileobj(response, temporary)
        verify_tla_jar(temporary_path, manifest)
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
    return target, "downloaded"


def parse_tlc_metrics(output: str) -> dict[str, int]:
    states = re.search(
        r"(?m)^([\d,]+) states generated, ([\d,]+) distinct states found",
        output,
    )
    depth = re.search(
        r"The depth of the complete state graph search is ([\d,]+)", output
    )
    if not states or not depth:
        raise ResearchError("Unable to parse TLC state metrics.")
    return {
        "generatedStates": int(states.group(1).replace(",", "")),
        "distinctStates": int(states.group(2).replace(",", "")),
        "depth": int(depth.group(1).replace(",", "")),
    }


def parse_tlc_memory(output: str) -> dict[str, int]:
    match = re.search(r"with ([\d,]+)MB heap and ([\d,]+)MB offheap memory", output)
    if not match:
        raise ResearchError("Unable to parse TLC memory boundary.")
    return {
        "heapMegabytes": int(match.group(1).replace(",", "")),
        "offHeapMegabytes": int(match.group(2).replace(",", "")),
    }


def run_tlc_smoke_model(
    root: Path,
    jar_path: Path,
    java: Mapping[str, Any],
    model: Mapping[str, Any],
) -> dict[str, Any]:
    module_path = root / model["module"]
    config_path = root / model["config"]
    metadir = root / ".tools" / "tla" / "states" / model["id"]
    metadir.mkdir(parents=True, exist_ok=True)
    result = run_process(
        [
            str(executable(Path(java["Home"]), "java")),
            "-XX:+UseParallelGC",
            "-cp",
            str(jar_path),
            "tlc2.TLC",
            "-cleanup",
            "-workers",
            "1",
            "-fp",
            "0",
            "-metadir",
            str(metadir),
            "-config",
            config_path.name,
            module_path.name,
        ],
        cwd=module_path.parent,
        environment=java_environment(java),
        timeout_seconds=120,
    )
    output = result.stdout + result.stderr
    if result.timed_out or result.exit_code != 0:
        raise ResearchError(
            f"TLC smoke model {model['id']} failed: {output[-2000:]}"
        )
    metrics = parse_tlc_metrics(output)
    return {
        "id": model["id"],
        "module": model["module"],
        "config": model["config"],
        "transactions": model["transactions"],
        "resources": model["resources"],
        "exitCode": result.exit_code,
        "durationSeconds": result.duration_seconds,
        **metrics,
    }


def bootstrap_tla_tools(
    output: Path | None = None,
    *,
    offline: bool = False,
    refresh: bool = False,
) -> str:
    root = repository_root()
    manifest = load_toolchain_manifest(root)
    java = require_research_jdk17()
    jar_path, installation_status = install_tla_tools(
        root, manifest, offline=offline, refresh=refresh
    )
    help_result = run_process(
        [
            str(executable(Path(java["Home"]), "java")),
            "-cp",
            str(jar_path),
            "tlc2.TLC",
            "-help",
        ],
        cwd=root,
        environment=java_environment(java),
        timeout_seconds=30,
    )
    help_output = help_result.stdout + help_result.stderr
    if help_result.timed_out or manifest["tlcVersion"] not in help_output:
        raise ResearchError("Installed TLC version does not match the manifest.")

    smoke_results = [
        run_tlc_smoke_model(root, jar_path, java, model)
        for model in manifest["smokeModels"]
    ]
    destination = (root / (output or DEFAULT_RESULT)).resolve()
    evidence = {
        "schemaVersion": 1,
        "step": "week-03-step-01-tla-toolchain",
        "generatedAt": iso_now(),
        "gitCommit": git(root, "rev-parse", "HEAD"),
        "status": "PASS",
        "releaseTag": manifest["releaseTag"],
        "tlcVersion": manifest["tlcVersion"],
        "asset": {
            "name": manifest["asset"]["name"],
            "url": manifest["asset"]["url"],
            "sizeBytes": manifest["asset"]["sizeBytes"],
            "sha256": manifest["asset"]["sha256"],
            "installationStatus": installation_status,
        },
        "java": java,
        "smokeModels": smoke_results,
        "claimBoundary": (
            "The smoke models validate the pinned toolchain and bounded "
            "2x2/3x3 configurations; they do not validate the L1 lock model."
        ),
    }
    write_json(destination, evidence)
    return str(destination.relative_to(root))


def run_l1_configuration(
    root: Path,
    jar_path: Path,
    java: Mapping[str, Any],
    configuration: Mapping[str, Any],
) -> dict[str, Any]:
    module_path = root / configuration["module"]
    config_path = root / configuration["config"]
    metadir = root / ".tools" / "tla" / "states" / configuration["id"]
    metadir.mkdir(parents=True, exist_ok=True)
    result = run_process(
        [
            str(executable(Path(java["Home"]), "java")),
            "-Xmx2048m",
            "-XX:+UseParallelGC",
            "-cp",
            str(jar_path),
            "tlc2.TLC",
            "-cleanup",
            "-workers",
            "1",
            "-fp",
            "0",
            "-metadir",
            str(metadir),
            "-config",
            config_path.name,
            module_path.name,
        ],
        cwd=module_path.parent,
        environment=java_environment(java),
        timeout_seconds=900,
    )
    output = result.stdout + result.stderr
    if result.timed_out or result.exit_code != 0:
        raise ResearchError(
            f"L1 model {configuration['id']} failed: {output[-4000:]}"
        )
    return {
        "id": configuration["id"],
        "kind": configuration["kind"],
        "module": configuration["module"],
        "config": configuration["config"],
        "transactions": configuration["transactions"],
        "resources": configuration["resources"],
        "requestBound": configuration["requestBound"],
        "completeWithinBound": configuration["completeWithinBound"],
        "exitCode": result.exit_code,
        "durationSeconds": result.duration_seconds,
        "moduleSha256": sha256_file(module_path),
        "configSha256": sha256_file(config_path),
        **parse_tlc_metrics(output),
        **parse_tlc_memory(output),
    }


def check_l1_model(output: Path | None = None) -> str:
    root = repository_root()
    manifest = load_toolchain_manifest(root)
    java = require_research_jdk17()
    jar_path = configured_jar_path(root, manifest)
    verify_tla_jar(jar_path, manifest)
    configurations = [
        run_l1_configuration(root, jar_path, java, configuration)
        for configuration in manifest["l1Models"]
    ]
    destination = (root / (output or DEFAULT_L1_RESULT)).resolve()
    evidence = {
        "schemaVersion": 1,
        "step": "week-03-step-02-l1-model",
        "generatedAt": iso_now(),
        "gitCommit": git(root, "rev-parse", "HEAD"),
        "status": "PASS",
        "releaseTag": manifest["releaseTag"],
        "tlcVersion": manifest["tlcVersion"],
        "java": java,
        "invariants": [
            "TypeOK",
            "OwnerHeldConsistency",
            "MutualExclusion",
            "PendingWellFormed",
            "WaiterNotOwnerOrUpgrade",
            "TerminalClean",
            "StrictXRetention",
        ],
        "liveness": {
            "property": "EventualTermination",
            "assumptions": [
                "weak fairness of Resolve(tx)",
                "weak fairness of Finish(tx)",
                "weak fairness of ReleaseAll(tx)",
            ],
        },
        "configurations": configurations,
        "claimBoundary": (
            "The 2x2 configuration is exhaustive within the protocol's maximum "
            "eight requests. The 3x3 configuration checks key invariants only "
            "through six requests. Neither result is an unbounded proof."
        ),
    }
    write_json(destination, evidence)
    return str(destination.relative_to(root))
