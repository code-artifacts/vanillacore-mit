"""Validation for the L1 model-to-implementation mapping ledger."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .common.tooling import (
    ResearchError,
    git,
    iso_now,
    read_json,
    repository_root,
    sha256_file,
    write_json,
)


MAPPING_PATH = Path("tla/l1/mapping-v0.1.json")
DEFAULT_RESULT = Path(
    "research/execution/week-03/results/step-03-mapping-ledger.json"
)
EXPECTED_ACTIONS = {
    "Init",
    "RequestS",
    "RequestX",
    "RequestUpgrade",
    "Grant",
    "Wait",
    "Wake",
    "Commit",
    "Rollback",
    "ReleaseAll",
    "DoneStutter",
}
EXPECTED_INVARIANTS = {
    "TypeOK",
    "OwnerHeldConsistency",
    "MutualExclusion",
    "PendingWellFormed",
    "WaiterNotOwnerOrUpgrade",
    "TerminalClean",
    "StrictXRetention",
}
OBSERVATIONS = {"OBSERVED", "DERIVED", "INFERRED", "UNOBSERVED"}


def _enum_values(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    body = re.search(r"enum\s+LockTraceEventType\s*\{(?P<body>.*?)\}", text, re.S)
    if not body:
        raise ResearchError("Unable to parse LockTraceEventType.")
    return set(
        re.findall(r"(?m)^\s*([A-Z][A-Z0-9_]*)\s*(?:,|$)", body.group("body"))
    )


def _validate_location(root: Path, location: Mapping[str, Any]) -> None:
    path = (root / location["path"]).resolve()
    if not path.is_file():
        raise ResearchError(f"Mapping location does not exist: {location['path']}")
    lines = path.read_text(encoding="utf-8").splitlines()
    line = location["line"]
    if not isinstance(line, int) or line < 1 or line > len(lines):
        raise ResearchError(f"Invalid mapping line {line} in {location['path']}")
    if location["symbol"] not in lines[line - 1]:
        raise ResearchError(
            f"Symbol {location['symbol']} is not at {location['path']}#L{line}"
        )


def validate_mapping(root: Path, mapping: Mapping[str, Any]) -> dict[str, Any]:
    model_path = root / mapping["model"]["path"]
    if sha256_file(model_path) != mapping["model"]["sha256"]:
        raise ResearchError("Mapping model SHA-256 does not match the L1 module.")
    event_types = _enum_values(root / mapping["traceSchema"]["eventEnumPath"])

    actions = mapping["actions"]
    action_names = [action["action"] for action in actions]
    if set(action_names) != EXPECTED_ACTIONS or len(action_names) != len(EXPECTED_ACTIONS):
        raise ResearchError("Mapping must cover each expected L1 action exactly once.")
    rule_ids = [action["ruleId"] for action in actions]
    if len(rule_ids) != len(set(rule_ids)):
        raise ResearchError("Action mapping rule IDs must be unique.")

    for action in actions:
        _validate_location(root, action["modelLocation"])
        for location in action["implementationLocations"]:
            _validate_location(root, location)
        unknown_events = set(action["requiredEvents"]) - event_types
        if unknown_events:
            raise ResearchError(f"Unknown trace events: {sorted(unknown_events)}")
        if action["observation"] not in OBSERVATIONS:
            raise ResearchError(f"Unknown observation class: {action['observation']}")
        if action["strongContradictionEligible"] and action["observation"] not in {
            "OBSERVED",
            "DERIVED",
        }:
            raise ResearchError(
                f"Strong action {action['action']} lacks observed or derived evidence."
            )
        if action["strongContradictionEligible"] and not action.get("strongConditions"):
            raise ResearchError(
                f"Strong action {action['action']} lacks explicit evidence conditions."
            )
        if action["stutter"] and action["strongContradictionEligible"]:
            raise ResearchError(f"Stutter action {action['action']} cannot be strong.")

    for resource in mapping["resourceMapping"].values():
        locations = resource.get("locations", [resource.get("location")])
        if not locations or any(location is None for location in locations):
            raise ResearchError("Every resource mapping requires source locations.")
        for location in locations:
            _validate_location(root, location)
    for location in mapping["ordering"]["locations"]:
        _validate_location(root, location)

    invariants = mapping["invariants"]
    invariant_names = [invariant["name"] for invariant in invariants]
    if set(invariant_names) != EXPECTED_INVARIANTS or len(invariant_names) != len(
        EXPECTED_INVARIANTS
    ):
        raise ResearchError("Refinement ledger must cover each L1 invariant exactly once.")
    invariant_ids = [invariant["ruleId"] for invariant in invariants]
    if len(invariant_ids) != len(set(invariant_ids)):
        raise ResearchError("Invariant rule IDs must be unique.")
    for invariant in invariants:
        _validate_location(root, invariant["modelLocation"])
        for location in invariant["sources"]:
            _validate_location(root, location)
        if invariant["confidence"] not in {"HIGH", "MEDIUM", "LOW"}:
            raise ResearchError(f"Invalid confidence: {invariant['confidence']}")
        if "reviewer" not in invariant:
            raise ResearchError(f"Invariant {invariant['name']} lacks a reviewer field.")

    observations = Counter(action["observation"] for action in actions)
    return {
        "mappingVersion": mapping["mappingVersion"],
        "mappingStatus": mapping["status"],
        "actionCount": len(actions),
        "invariantCount": len(invariants),
        "strongActionCount": sum(
            bool(action["strongContradictionEligible"]) for action in actions
        ),
        "observationCounts": dict(sorted(observations.items())),
        "eventTypes": sorted(event_types),
        "unresolvedCount": len(mapping["unresolved"]),
        "unassignedReviewers": sum(
            invariant["reviewer"] == "UNASSIGNED" for invariant in invariants
        ),
    }


def check_l1_mapping(output: Path | None = None) -> str:
    root = repository_root()
    mapping_path = root / MAPPING_PATH
    mapping = read_json(mapping_path)
    summary = validate_mapping(root, mapping)
    destination = (root / (output or DEFAULT_RESULT)).resolve()
    evidence = {
        "schemaVersion": 1,
        "step": "week-03-step-03-mapping-ledger",
        "generatedAt": iso_now(),
        "gitCommit": git(root, "rev-parse", "HEAD"),
        "status": "PASS",
        "mappingPath": str(MAPPING_PATH).replace("\\", "/"),
        "mappingSha256": sha256_file(mapping_path),
        **summary,
        "claimBoundary": (
            "PASS validates coverage and source-location integrity. The mapping "
            "remains PROVISIONAL until independent review and stronger snapshots."
        ),
    }
    write_json(destination, evidence)
    return str(destination.relative_to(root))
