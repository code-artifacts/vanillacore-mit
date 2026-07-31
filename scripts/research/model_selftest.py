"""L1 legal replay, negative TLC, and Week 2 fixture self-tests."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

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
from .tla import configured_jar_path, load_toolchain_manifest, verify_tla_jar


DEFAULT_SELF_TEST_RESULT = Path(
    "research/execution/week-03/results/step-05-model-self-tests.json"
)
CANONICAL_RESULT = Path(
    "research/execution/week-03/results/step-04-canonical-traces.json"
)
WEEK2_FIXTURES = Path("tla/l1/fixtures/week2-v0.1.json")
TERMINAL_STATES = {"COMMITTED", "ABORTED"}
INVARIANT_FAILURE = re.compile(r"Invariant ([A-Za-z0-9_]+) is violated")


def initial_state(
    transactions: Sequence[str], resources: Sequence[str]
) -> dict[str, Any]:
    return {
        "txState": {tx: "ACTIVE" for tx in transactions},
        "held": {
            tx: {resource: "NONE" for resource in resources}
            for tx in transactions
        },
        "owners": {
            resource: {tx: "NONE" for tx in transactions}
            for resource in resources
        },
        "pendingResource": {tx: "NO_RESOURCE" for tx in transactions},
        "pendingMode": {tx: "NONE" for tx in transactions},
        "requestCount": 0,
        "xGranted": {tx: [] for tx in transactions},
        "lastEvent": {
            "action": "INIT",
            "tx": "NO_TX",
            "resource": "NO_RESOURCE",
            "mode": "NONE",
        },
    }


def _compatible(state: Mapping[str, Any], tx: str, resource: str, mode: str) -> bool:
    other_modes = [
        owner_mode
        for owner, owner_mode in state["owners"][resource].items()
        if owner != tx
    ]
    if mode == "S":
        return all(owner_mode in {"NONE", "S"} for owner_mode in other_modes)
    return all(owner_mode == "NONE" for owner_mode in other_modes)


def invariant_violations(state: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    transactions = tuple(state["txState"])
    resources = tuple(state["owners"])
    if any(
        state["owners"][resource][tx] != state["held"][tx][resource]
        for tx in transactions
        for resource in resources
    ):
        violations.append("OwnerHeldConsistency")
    if any(
        first != second
        and state["owners"][resource][first] != "NONE"
        and state["owners"][resource][second] != "NONE"
        and not (
            state["owners"][resource][first] == "S"
            and state["owners"][resource][second] == "S"
        )
        for resource in resources
        for first in transactions
        for second in transactions
    ):
        violations.append("MutualExclusion")
    pending_invalid = False
    for tx in transactions:
        resource = state["pendingResource"][tx]
        mode = state["pendingMode"][tx]
        if (resource == "NO_RESOURCE") != (mode == "NONE"):
            pending_invalid = True
        if state["txState"][tx] == "WAITING" and resource == "NO_RESOURCE":
            pending_invalid = True
        if state["txState"][tx] not in {"ACTIVE", "WAITING"} and resource != "NO_RESOURCE":
            pending_invalid = True
        if mode == "S" and state["held"][tx][resource] != "NONE":
            pending_invalid = True
        if mode == "X" and state["held"][tx][resource] not in {"NONE", "S"}:
            pending_invalid = True
    if pending_invalid:
        violations.append("PendingWellFormed")
    if any(
        state["txState"][tx] == "WAITING"
        and not (
            state["held"][tx][state["pendingResource"][tx]] == "NONE"
            or (
                state["held"][tx][state["pendingResource"][tx]] == "S"
                and state["pendingMode"][tx] == "X"
            )
        )
        for tx in transactions
    ):
        violations.append("WaiterNotOwnerOrUpgrade")
    if any(
        state["txState"][tx] in TERMINAL_STATES
        and (
            state["pendingResource"][tx] != "NO_RESOURCE"
            or any(state["held"][tx][resource] != "NONE" for resource in resources)
        )
        for tx in transactions
    ):
        violations.append("TerminalClean")
    if any(
        state["txState"][tx] not in TERMINAL_STATES
        and state["held"][tx][resource] != "X"
        for tx in transactions
        for resource in state["xGranted"][tx]
    ):
        violations.append("StrictXRetention")
    return violations


def _require(condition: bool, event: Mapping[str, str], message: str) -> None:
    if not condition:
        raise ResearchError(f"Illegal {event['action']} event: {message}: {event}")


def apply_event(state: dict[str, Any], event: Mapping[str, str]) -> None:
    action = event["action"]
    tx = event["tx"]
    resource = event["resource"]
    mode = event["mode"]
    if action in {"REQUEST_S", "REQUEST_X", "UPGRADE_REQUEST"}:
        _require(state["txState"][tx] == "ACTIVE", event, "transaction is not active")
        _require(
            state["pendingResource"][tx] == "NO_RESOURCE",
            event,
            "transaction already has a pending request",
        )
        if action == "UPGRADE_REQUEST":
            _require(state["held"][tx][resource] == "S", event, "upgrade lacks S")
            requested_mode = "X"
        else:
            _require(state["held"][tx][resource] == "NONE", event, "lock already held")
            requested_mode = "S" if action == "REQUEST_S" else "X"
        _require(mode == requested_mode, event, "mode does not match request")
        state["pendingResource"][tx] = resource
        state["pendingMode"][tx] = requested_mode
        state["requestCount"] += 1
    elif action == "GRANT":
        _require(state["txState"][tx] == "ACTIVE", event, "transaction is not active")
        _require(state["pendingResource"][tx] == resource, event, "resource is not pending")
        _require(state["pendingMode"][tx] == mode, event, "mode is not pending")
        _require(_compatible(state, tx, resource, mode), event, "owners are incompatible")
        state["held"][tx][resource] = mode
        state["owners"][resource][tx] = mode
        state["pendingResource"][tx] = "NO_RESOURCE"
        state["pendingMode"][tx] = "NONE"
        if mode == "X" and resource not in state["xGranted"][tx]:
            state["xGranted"][tx].append(resource)
            state["xGranted"][tx].sort()
    elif action == "WAIT":
        _require(state["txState"][tx] == "ACTIVE", event, "transaction is not active")
        _require(state["pendingResource"][tx] == resource, event, "resource is not pending")
        _require(state["pendingMode"][tx] == mode, event, "mode is not pending")
        _require(not _compatible(state, tx, resource, mode), event, "request is compatible")
        state["txState"][tx] = "WAITING"
    elif action == "WAKE":
        _require(state["txState"][tx] == "WAITING", event, "transaction is not waiting")
        _require(state["pendingResource"][tx] == resource, event, "resource is not pending")
        _require(state["pendingMode"][tx] == mode, event, "mode is not pending")
        _require(_compatible(state, tx, resource, mode), event, "request remains incompatible")
        state["txState"][tx] = "ACTIVE"
    elif action == "COMMIT":
        _require(state["txState"][tx] == "ACTIVE", event, "transaction is not active")
        _require(
            state["pendingResource"][tx] == "NO_RESOURCE",
            event,
            "transaction has a pending request",
        )
        state["txState"][tx] = "COMMITTING"
    elif action == "ROLLBACK":
        _require(
            state["txState"][tx] in {"ACTIVE", "WAITING"},
            event,
            "transaction cannot roll back",
        )
        state["txState"][tx] = "ROLLING_BACK"
        state["pendingResource"][tx] = "NO_RESOURCE"
        state["pendingMode"][tx] = "NONE"
    elif action == "RELEASE_ALL":
        prior = state["txState"][tx]
        _require(prior in {"COMMITTING", "ROLLING_BACK"}, event, "transaction is not ending")
        state["txState"][tx] = "COMMITTED" if prior == "COMMITTING" else "ABORTED"
        for held_resource in state["owners"]:
            state["held"][tx][held_resource] = "NONE"
            state["owners"][held_resource][tx] = "NONE"
    elif action == "DONE":
        _require(
            all(value in TERMINAL_STATES for value in state["txState"].values()),
            event,
            "transactions are not terminal",
        )
    else:
        raise ResearchError(f"Unsupported L1 action: {action}")
    state["lastEvent"] = dict(event)
    violations = invariant_violations(state)
    if violations:
        raise ResearchError(f"L1 invariant violation after {event}: {violations}")


def replay(
    events: Sequence[Mapping[str, str]],
    transactions: Sequence[str],
    resources: Sequence[str],
) -> dict[str, Any]:
    state = initial_state(transactions, resources)
    for event in events:
        apply_event(state, event)
    return state


def _require_hash(root: Path, description: str, record: Mapping[str, str]) -> None:
    path = root / record["path"]
    actual = sha256_file(path)
    if actual != record["sha256"]:
        raise ResearchError(
            f"{description} hash changed; replay and review fixtures: {actual}"
        )


def validate_canonical_corpus(root: Path) -> dict[str, Any]:
    corpus = read_json(root / CANONICAL_RESULT)
    provenance = corpus["provenance"]
    for description, path_key, hash_key in (
        ("L1 model", "module", "moduleSha256"),
        ("L1 trace config", "config", "configSha256"),
        ("L1 mapping", "mapping", "mappingSha256"),
    ):
        actual = sha256_file(root / provenance[path_key])
        if actual != provenance[hash_key]:
            raise ResearchError(f"{description} changed; regenerate canonical traces.")
    configuration = corpus["configuration"]
    traces = []
    for trace in corpus["traces"]:
        events = [step["event"] for step in trace["actionSequence"]]
        final_state = replay(
            events, configuration["transactions"], configuration["resources"]
        )
        if final_state != trace["finalState"]:
            raise ResearchError(f"Canonical trace final state differs: {trace['id']}")
        traces.append({"id": trace["id"], "actions": len(events), "status": "PASS"})
    return {
        "corpus": str(CANONICAL_RESULT).replace("\\", "/"),
        "corpusSha256": sha256_file(root / CANONICAL_RESULT),
        "traceCount": len(traces),
        "traces": traces,
    }


def validate_week2_fixtures(root: Path) -> dict[str, Any]:
    catalog = read_json(root / WEEK2_FIXTURES)
    _require_hash(root, "L1 model", catalog["model"])
    _require_hash(root, "L1 mapping", catalog["mapping"])
    _require_hash(root, "Week 2 summary", catalog["sources"]["summary"])
    _require_hash(root, "Week 2 scenario source", catalog["sources"]["scenarioSource"])
    constants = catalog["constants"]
    results = []
    for fixture in catalog["fixtures"]:
        state = replay(
            fixture["actions"],
            constants["transactions"],
            constants["resources"],
        )
        expected = fixture["expectedFinal"]
        terminal_clean = not any(
            state["held"][tx][resource] != "NONE"
            for tx in constants["transactions"]
            for resource in constants["resources"]
        )
        actual = {
            "txState": state["txState"],
            "requestCount": state["requestCount"],
            "terminalClean": terminal_clean,
        }
        if actual != expected:
            raise ResearchError(f"Week 2 fixture final state differs: {fixture['id']}")
        if fixture["expectedVerdict"] == "INCONCLUSIVE" and not fixture.get(
            "inconclusiveReason"
        ):
            raise ResearchError(f"Inconclusive fixture lacks reason: {fixture['id']}")
        results.append(
            {
                "id": fixture["id"],
                "sourceScenario": fixture["sourceScenario"],
                "actions": len(fixture["actions"]),
                "expectedVerdict": fixture["expectedVerdict"],
                "status": "PASS",
            }
        )
    return {
        "catalog": str(WEEK2_FIXTURES).replace("\\", "/"),
        "catalogSha256": sha256_file(root / WEEK2_FIXTURES),
        "fixtureCount": len(results),
        "confirmed": sum(item["expectedVerdict"] == "CONFIRMED" for item in results),
        "inconclusive": sum(
            item["expectedVerdict"] == "INCONCLUSIVE" for item in results
        ),
        "fixtures": results,
    }


def _run_negative_test(
    root: Path,
    jar_path: Path,
    java: Mapping[str, Any],
    configuration: Mapping[str, Any],
) -> dict[str, Any]:
    module_path = root / configuration["module"]
    config_path = root / configuration["config"]
    metadir = root / ".tools" / "tla" / "states" / "self-tests" / configuration["id"]
    result = run_process(
        [
            str(executable(Path(java["Home"]), "java")),
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
    match = INVARIANT_FAILURE.search(output)
    observed = match.group(1) if match else None
    if result.timed_out or result.exit_code != configuration["expectedExitCode"]:
        raise ResearchError(
            f"Negative self-test {configuration['id']} exit mismatch: "
            f"{result.exit_code}: {output[-2000:]}"
        )
    if observed != configuration["expectedInvariant"]:
        raise ResearchError(
            f"Negative self-test {configuration['id']} caught {observed}, "
            f"expected {configuration['expectedInvariant']}."
        )
    return {
        "id": configuration["id"],
        "fault": configuration["fault"],
        "expectedInvariant": configuration["expectedInvariant"],
        "observedInvariant": observed,
        "exitCode": result.exit_code,
        "durationSeconds": result.duration_seconds,
        "module": configuration["module"],
        "moduleSha256": sha256_file(module_path),
        "config": configuration["config"],
        "configSha256": sha256_file(config_path),
        "outputSha256": hashlib.sha256(output.encode("utf-8")).hexdigest().upper(),
        "status": "PASS",
    }


def check_l1_self_tests(output: Path | None = None) -> str:
    root = repository_root()
    manifest = load_toolchain_manifest(root)
    java = require_research_jdk17()
    jar_path = configured_jar_path(root, manifest)
    verify_tla_jar(jar_path, manifest)
    canonical = validate_canonical_corpus(root)
    fixtures = validate_week2_fixtures(root)
    negative = [
        _run_negative_test(root, jar_path, java, configuration)
        for configuration in manifest.get("selfTestModels", [])
    ]
    if len(negative) != 3:
        raise ResearchError("Exactly three negative L1 self-tests are required.")
    destination = (root / (output or DEFAULT_SELF_TEST_RESULT)).resolve()
    evidence = {
        "schemaVersion": 1,
        "step": "week-03-step-05-model-self-tests",
        "generatedAt": iso_now(),
        "gitCommit": git(root, "rev-parse", "HEAD"),
        "status": "PASS",
        "toolchain": {
            "releaseTag": manifest["releaseTag"],
            "tlcVersion": manifest["tlcVersion"],
            "toolSha256": manifest["asset"]["sha256"],
            "java": java,
        },
        "legalCanonicalReplay": canonical,
        "negativeInvariantTests": negative,
        "week2RegressionFixtures": fixtures,
        "claimBoundary": (
            "PASS means the current bounded canonical corpus replays, TLC catches "
            "the three injected initial-state faults, and all normalized Week 2 "
            "fixtures remain legal. It does not upgrade provisional mappings or "
            "turn the reverse-two-resource fixture into a strong verdict."
        ),
    }
    write_json(destination, evidence)
    return str(destination.relative_to(root))


def mutated_state(base: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(base)
