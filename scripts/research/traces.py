"""TLC state-graph parsing and canonical L1 trace extraction."""

from __future__ import annotations

import re
from collections import defaultdict
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
from .tla import (
    TOOLCHAIN_MANIFEST,
    configured_jar_path,
    load_toolchain_manifest,
    parse_tlc_memory,
    parse_tlc_metrics,
    verify_tla_jar,
)


DEFAULT_TRACE_RESULT = Path(
    "research/execution/week-03/results/step-04-canonical-traces.json"
)
NODE_PATTERN = re.compile(
    r'^(-?\d+) \[label="(.*)"(?:,style = filled)?\];?$'
)
EDGE_PATTERN = re.compile(
    r'^(-?\d+) -> (-?\d+) \[label="([^"]+)"'
)
EVENT_PATTERN = re.compile(
    r'lastEvent = \[\s*tx \|-> ([^,]+),\s*'
    r'resource \|-> ([^,]+),\s*mode \|-> "([^"]+)",\s*'
    r'action \|-> "([^"]+)"\s*\]'
)
SEED_PATTERN = re.compile(r"with fp \d+ and seed (-?\d+)")
PAIR_PATTERN = re.compile(r'(\w+) :> ("[^"]+"|\w+)')
NESTED_PATTERN = re.compile(r'(\w+) :> \(([^()]*)\)')
SET_PATTERN = re.compile(r'(\w+) :> \{([^}]*)\}')


def _event(action: str, tx: str, resource: str, mode: str) -> dict[str, str]:
    return {"action": action, "tx": tx, "resource": resource, "mode": mode}


SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "id": "shared-shared-compatible",
        "family": "S/S",
        "events": (
            _event("REQUEST_S", "t1", "r1", "S"),
            _event("GRANT", "t1", "r1", "S"),
            _event("REQUEST_S", "t2", "r1", "S"),
            _event("GRANT", "t2", "r1", "S"),
        ),
    },
    {
        "id": "shared-exclusive-conflict",
        "family": "S/X",
        "events": (
            _event("REQUEST_S", "t1", "r1", "S"),
            _event("GRANT", "t1", "r1", "S"),
            _event("REQUEST_X", "t2", "r1", "X"),
            _event("WAIT", "t2", "r1", "X"),
        ),
    },
    {
        "id": "exclusive-shared-conflict",
        "family": "X/S",
        "events": (
            _event("REQUEST_X", "t1", "r1", "X"),
            _event("GRANT", "t1", "r1", "X"),
            _event("REQUEST_S", "t2", "r1", "S"),
            _event("WAIT", "t2", "r1", "S"),
        ),
    },
    {
        "id": "exclusive-exclusive-conflict",
        "family": "X/X",
        "events": (
            _event("REQUEST_X", "t1", "r1", "X"),
            _event("GRANT", "t1", "r1", "X"),
            _event("REQUEST_X", "t2", "r1", "X"),
            _event("WAIT", "t2", "r1", "X"),
        ),
    },
    {
        "id": "single-upgrader",
        "family": "single upgrader",
        "events": (
            _event("REQUEST_S", "t1", "r1", "S"),
            _event("GRANT", "t1", "r1", "S"),
            _event("UPGRADE_REQUEST", "t1", "r1", "X"),
            _event("GRANT", "t1", "r1", "X"),
        ),
    },
    {
        "id": "double-upgrader",
        "family": "double upgrader",
        "events": (
            _event("REQUEST_S", "t1", "r1", "S"),
            _event("GRANT", "t1", "r1", "S"),
            _event("REQUEST_S", "t2", "r1", "S"),
            _event("GRANT", "t2", "r1", "S"),
            _event("UPGRADE_REQUEST", "t1", "r1", "X"),
            _event("WAIT", "t1", "r1", "X"),
            _event("UPGRADE_REQUEST", "t2", "r1", "X"),
            _event("WAIT", "t2", "r1", "X"),
        ),
    },
    {
        "id": "writer-commit-reader-grant",
        "family": "writer commit then reader grant",
        "events": (
            _event("REQUEST_X", "t1", "r1", "X"),
            _event("GRANT", "t1", "r1", "X"),
            _event("REQUEST_S", "t2", "r1", "S"),
            _event("WAIT", "t2", "r1", "S"),
            _event("COMMIT", "t1", "NO_RESOURCE", "NONE"),
            _event("RELEASE_ALL", "t1", "NO_RESOURCE", "NONE"),
            _event("WAKE", "t2", "r1", "S"),
            _event("GRANT", "t2", "r1", "S"),
        ),
    },
    {
        "id": "writer-rollback-reader-grant",
        "family": "writer rollback then reader grant",
        "events": (
            _event("REQUEST_X", "t1", "r1", "X"),
            _event("GRANT", "t1", "r1", "X"),
            _event("REQUEST_S", "t2", "r1", "S"),
            _event("WAIT", "t2", "r1", "S"),
            _event("ROLLBACK", "t1", "NO_RESOURCE", "NONE"),
            _event("RELEASE_ALL", "t1", "NO_RESOURCE", "NONE"),
            _event("WAKE", "t2", "r1", "S"),
            _event("GRANT", "t2", "r1", "S"),
        ),
    },
)


def _decode_dot_label(label: str) -> str:
    return label.replace(r"\n", "\n").replace(r'\"', '"').replace(r"\\", "\\")


def _value(text: str) -> str:
    return text.strip().strip('"')


def parse_event(label: str) -> dict[str, str]:
    match = EVENT_PATTERN.search(label)
    if not match:
        raise ResearchError("TLC node does not contain a parseable lastEvent record.")
    tx, resource, mode, action = (_value(value) for value in match.groups())
    return _event(action, tx, resource, mode)


def parse_dot_graph(path: Path) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, set[tuple[str, str]]] = defaultdict(set)
    initial: str | None = None
    with path.open(encoding="utf-8") as stream:
        for raw_line in stream:
            line = raw_line.rstrip("\n")
            node_match = NODE_PATTERN.match(line)
            if node_match:
                node_id, encoded_label = node_match.groups()
                label = _decode_dot_label(encoded_label)
                nodes[node_id] = {"event": parse_event(label), "label": label}
                if "style = filled" in line:
                    if initial is not None:
                        raise ResearchError("TLC graph contains multiple initial states.")
                    initial = node_id
                continue
            edge_match = EDGE_PATTERN.match(line)
            if edge_match:
                source, target, action = edge_match.groups()
                edges[source].add((target, action))
    if initial is None or not nodes:
        raise ResearchError("TLC graph has no initial state or nodes.")
    dangling = sorted(
        {target for values in edges.values() for target, _ in values} - set(nodes)
    )
    if dangling:
        raise ResearchError(f"TLC graph has dangling targets: {dangling[:3]}")
    return {
        "initial": initial,
        "nodes": nodes,
        "edges": {
            source: sorted(values, key=lambda value: (int(value[0]), value[1]))
            for source, values in edges.items()
        },
        "nodeCount": len(nodes),
        "edgeCount": sum(len(values) for values in edges.values()),
    }


def _parse_map(expression: str) -> dict[str, str]:
    return {key: _value(value) for key, value in PAIR_PATTERN.findall(expression)}


def _parse_nested_map(expression: str) -> dict[str, dict[str, str]]:
    return {
        key: _parse_map(value)
        for key, value in NESTED_PATTERN.findall(expression)
    }


def _parse_set_map(expression: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for key, body in SET_PATTERN.findall(expression):
        values[key] = sorted(item.strip() for item in body.split(",") if item.strip())
    return values


def parse_state(label: str) -> dict[str, Any]:
    assignments: dict[str, str] = {}
    for part in re.split(r"\n/\\ ", label):
        normalized = part.removeprefix("/\\ ")
        if " = " in normalized:
            name, expression = normalized.split(" = ", 1)
            assignments[name] = expression
    required = {
        "owners",
        "xGranted",
        "pendingResource",
        "requestCount",
        "pendingMode",
        "lastEvent",
        "held",
        "txState",
    }
    missing = sorted(required - set(assignments))
    if missing:
        raise ResearchError(f"TLC state is missing assignments: {missing}")
    return {
        "txState": _parse_map(assignments["txState"]),
        "held": _parse_nested_map(assignments["held"]),
        "owners": _parse_nested_map(assignments["owners"]),
        "pendingResource": _parse_map(assignments["pendingResource"]),
        "pendingMode": _parse_map(assignments["pendingMode"]),
        "requestCount": int(assignments["requestCount"]),
        "xGranted": _parse_set_map(assignments["xGranted"]),
        "lastEvent": parse_event(label),
    }


def extract_trace(
    graph: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    frontier: dict[str, list[dict[str, Any]]] = {graph["initial"]: []}
    for expected in scenario["events"]:
        next_frontier: dict[str, list[dict[str, Any]]] = {}
        for source, path in sorted(frontier.items(), key=lambda item: int(item[0])):
            for target, tla_action in graph["edges"].get(source, []):
                actual = graph["nodes"][target]["event"]
                if actual != expected:
                    continue
                candidate = path + [
                    {
                        "ordinal": len(path) + 1,
                        "sourceStateId": source,
                        "targetStateId": target,
                        "tlaAction": tla_action,
                        "event": actual,
                    }
                ]
                previous = next_frontier.get(target)
                if previous is None or _path_key(candidate) < _path_key(previous):
                    next_frontier[target] = candidate
        if not next_frontier:
            raise ResearchError(
                f"Scenario '{scenario['id']}' is unreachable at event {expected}."
            )
        frontier = next_frontier
    final_id, path = min(
        frontier.items(), key=lambda item: (int(item[0]), _path_key(item[1]))
    )
    return {
        "id": scenario["id"],
        "family": scenario["family"],
        "selection": "exact event pattern; smallest numeric state-id tie break",
        "actionCount": len(path),
        "actionSequence": path,
        "finalStateId": final_id,
        "finalState": parse_state(graph["nodes"][final_id]["label"]),
    }


def _path_key(path: Sequence[Mapping[str, Any]]) -> tuple[int, ...]:
    return tuple(int(step["targetStateId"]) for step in path)


def _run_tlc_graph(
    root: Path,
    jar_path: Path,
    java: Mapping[str, Any],
    configuration: Mapping[str, Any],
) -> tuple[Path, str, float]:
    module_path = root / configuration["module"]
    config_path = root / configuration["config"]
    graph_path = root / configuration["rawDotPath"]
    graph_path.parent.mkdir(parents=True, exist_ok=True)
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
            "-seed",
            str(configuration["seed"]),
            "-metadir",
            str(metadir),
            "-dump",
            "dot,actionlabels",
            str(graph_path),
            "-config",
            config_path.name,
            module_path.name,
        ],
        cwd=module_path.parent,
        environment=java_environment(java),
        timeout_seconds=900,
    )
    output = result.stdout + result.stderr
    if result.timed_out or result.exit_code != 0 or not graph_path.is_file():
        raise ResearchError(f"TLC trace graph export failed: {output[-4000:]}")
    return graph_path, output, result.duration_seconds


def export_l1_traces(output: Path | None = None) -> str:
    root = repository_root()
    manifest = load_toolchain_manifest(root)
    configuration = manifest.get("traceModel")
    if not configuration:
        raise ResearchError("TLA+ toolchain manifest has no traceModel.")
    java = require_research_jdk17()
    jar_path = configured_jar_path(root, manifest)
    verify_tla_jar(jar_path, manifest)
    graph_path, tlc_output, duration = _run_tlc_graph(
        root, jar_path, java, configuration
    )
    graph = parse_dot_graph(graph_path)
    traces = [extract_trace(graph, scenario) for scenario in SCENARIOS]
    actual_seed = SEED_PATTERN.search(tlc_output)
    if not actual_seed or int(actual_seed.group(1)) != configuration["seed"]:
        raise ResearchError("TLC did not report the configured deterministic seed.")
    module_path = root / configuration["module"]
    config_path = root / configuration["config"]
    mapping_path = root / "tla/l1/mapping-v0.1.json"
    mapping = read_json(mapping_path)
    destination = (root / (output or DEFAULT_TRACE_RESULT)).resolve()
    evidence = {
        "schemaVersion": 1,
        "step": "week-03-step-04-canonical-traces",
        "generatedAt": iso_now(),
        "gitCommit": git(root, "rev-parse", "HEAD"),
        "status": "PASS",
        "provenance": {
            "releaseTag": manifest["releaseTag"],
            "tlcVersion": manifest["tlcVersion"],
            "toolSha256": manifest["asset"]["sha256"],
            "manifest": str(TOOLCHAIN_MANIFEST).replace("\\", "/"),
            "manifestSha256": sha256_file(root / TOOLCHAIN_MANIFEST),
            "module": configuration["module"],
            "moduleSha256": sha256_file(module_path),
            "config": configuration["config"],
            "configSha256": sha256_file(config_path),
            "mapping": str(mapping_path.relative_to(root)).replace("\\", "/"),
            "mappingSha256": sha256_file(mapping_path),
            "mappingStatus": mapping["status"],
            "rawGraph": {
                "path": configuration["rawDotPath"],
                "tracked": False,
                "sizeBytes": graph_path.stat().st_size,
                "sha256": sha256_file(graph_path),
            },
        },
        "configuration": {
            "transactions": configuration["transactions"],
            "resources": configuration["resources"],
            "maxRequests": configuration["requestBound"],
            "symmetryReduction": False,
            "fingerprintIndex": 0,
            "seed": configuration["seed"],
            "workers": 1,
        },
        "tlc": {
            "durationSeconds": duration,
            **parse_tlc_metrics(tlc_output),
            **parse_tlc_memory(tlc_output),
            "graphNodes": graph["nodeCount"],
            "graphEdges": graph["edgeCount"],
        },
        "traceCount": len(traces),
        "traces": traces,
        "claimBoundary": (
            "These are deterministic shortest exact-pattern witnesses from the "
            "complete bounded 2x2 TLC graph. They are not unbounded proofs, and "
            "the provisional mapping does not make them implementation traces."
        ),
    }
    write_json(destination, evidence)
    return str(destination.relative_to(root))
