from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "vc-schedule-0.1"
MODEL_VERSION = "VC_L1_SX@week-03-step-04"
MAPPING_VERSION = "mapping-v0.1"
DEFAULT_CANONICAL = Path(
    "research/execution/week-03/results/step-04-canonical-traces.json"
)
DEFAULT_CORPUS = Path("research/execution/week-04/schedules")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _source_site(action: str, mode: str) -> tuple[str, str]:
    normalized = mode.lower()
    if action in {"REQUEST_S", "REQUEST_X", "UPGRADE_REQUEST"}:
        return "LOCK_CALL", f"locktable.{normalized}.call"
    if action == "GRANT":
        return "GRANT", f"locktable.{normalized}.grant"
    if action == "WAIT":
        return "WAIT_BEGIN", f"locktable.{normalized}.wait"
    if action == "RELEASE_ALL":
        return "TX_END", "locktable.releaseAll.txEnd"
    if action in {"COMMIT", "ROLLBACK"}:
        return "HARNESS_OPERATION", f"harness.transaction.{action.lower()}"
    if action == "WAKE":
        return "HARNESS_OBSERVATION", "harness.waiter.wake"
    raise ValueError(f"unsupported model action: {action}")


def _operation_kind(action: str) -> str | None:
    if action in {"REQUEST_S", "REQUEST_X", "UPGRADE_REQUEST"}:
        return "LOCK"
    if action in {"COMMIT", "ROLLBACK"}:
        return action
    return None


def _edge_kind(previous: Mapping[str, Any], current: Mapping[str, Any]) -> str:
    if previous["tx"] == current["tx"]:
        return "THREAD_ORDER"
    if current["modelAction"] in {"WAIT", "GRANT"}:
        return "OWNER_GRANT_CAUSALITY"
    if previous["modelAction"] in {"RELEASE_ALL", "WAKE"}:
        return "RELEASE_WAKE_CAUSALITY"
    return "SCHEDULER_EDGE"


def schedule_from_trace(
    trace: Mapping[str, Any], provenance: Mapping[str, Any], seed: int
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    operation_by_observation: dict[str, str] = {}
    previous_operation_by_tx: dict[str, str] = {}
    happens_before: list[dict[str, str]] = []

    for index, step in enumerate(trace["actionSequence"], start=1):
        event = step["event"]
        observation_id = f"obs-{index:02d}"
        event_type, source_site = _source_site(event["action"], event["mode"])
        observations.append(
            {
                "id": observation_id,
                "ordinal": index,
                "modelAction": event["action"],
                "tx": event["tx"],
                "resource": event["resource"],
                "mode": event["mode"],
                "eventType": event_type,
                "sourceSite": source_site,
                "gateRequested": event_type in {"LOCK_CALL", "HARNESS_OPERATION"},
            }
        )
        kind = _operation_kind(event["action"])
        if kind is not None:
            operation_id = f"op-{len(operations) + 1:02d}"
            operation = {
                "id": operation_id,
                "thread": event["tx"],
                "tx": event["tx"],
                "kind": kind,
                "resource": event["resource"],
                "mode": event["mode"],
                "triggerObservation": observation_id,
            }
            operations.append(operation)
            operation_by_observation[observation_id] = operation_id
            previous = previous_operation_by_tx.get(event["tx"])
            if previous is not None:
                happens_before.append(
                    {"before": previous, "after": operation_id, "kind": "THREAD_ORDER"}
                )
            previous_operation_by_tx[event["tx"]] = operation_id

    strict_order = [observation["id"] for observation in observations]
    for previous, current in zip(observations, observations[1:]):
        if (
            previous["tx"] == current["tx"]
            or current["modelAction"] in {"WAIT", "GRANT"}
            or previous["modelAction"] in {"RELEASE_ALL", "WAKE"}
        ):
            happens_before.append(
                {
                    "before": previous["id"],
                    "after": current["id"],
                    "kind": _edge_kind(previous, current),
                }
            )

    return {
        "schemaVersion": SCHEMA_VERSION,
        "scheduleId": trace["id"],
        "family": trace["family"],
        "source": {
            "canonicalTrace": (
                "research/execution/week-03/results/step-04-canonical-traces.json"
            ),
            "canonicalTraceId": trace["id"],
            "canonicalTraceSha256": provenance["canonicalTraceSha256"],
        },
        "versions": {
            "model": MODEL_VERSION,
            "modelSha256": provenance["modelSha256"],
            "mapping": MAPPING_VERSION,
            "mappingSha256": provenance["mappingSha256"],
        },
        "seed": seed,
        "timeoutMillis": 5000,
        "policy": {"kind": "STRICT_OR_PARTIAL_ORDER", "pctReserved": True},
        "operations": operations,
        "observations": observations,
        "strictOrder": strict_order,
        "happensBefore": happens_before,
        "expectedOutcome": {
            "kind": "MODEL_PREFIX_REPLAYED",
            "finalTransactionState": trace["finalState"]["txState"],
            "cleanupRequired": True,
        },
        "diagnostics": {
            "wallClock": "DIAGNOSTIC_ONLY",
            "nanoTime": "DIAGNOSTIC_ONLY",
            "crossThreadOrder": "EXPLICIT_EDGES_ONLY",
        },
    }


def validate_schedule(schedule: Mapping[str, Any]) -> None:
    required = {
        "schemaVersion",
        "scheduleId",
        "family",
        "source",
        "versions",
        "seed",
        "timeoutMillis",
        "policy",
        "operations",
        "observations",
        "strictOrder",
        "happensBefore",
        "expectedOutcome",
        "diagnostics",
    }
    missing = sorted(required - set(schedule))
    if missing:
        raise ValueError(f"schedule is missing fields: {missing}")
    if schedule["schemaVersion"] != SCHEMA_VERSION:
        raise ValueError("unsupported schedule schema version")
    if not isinstance(schedule["seed"], int) or schedule["seed"] < 0:
        raise ValueError("seed must be a non-negative integer")
    if not isinstance(schedule["timeoutMillis"], int) or schedule["timeoutMillis"] <= 0:
        raise ValueError("timeoutMillis must be positive")

    operations = {item["id"]: item for item in schedule["operations"]}
    observations = {item["id"]: item for item in schedule["observations"]}
    if len(operations) != len(schedule["operations"]):
        raise ValueError("operation ids must be unique")
    if len(observations) != len(schedule["observations"]):
        raise ValueError("observation ids must be unique")
    if set(schedule["strictOrder"]) != set(observations):
        raise ValueError("strictOrder must contain every observation exactly once")
    if len(schedule["strictOrder"]) != len(observations):
        raise ValueError("strictOrder contains duplicate observations")

    nodes = set(operations) | set(observations)
    for edge in schedule["happensBefore"]:
        if edge["before"] not in nodes or edge["after"] not in nodes:
            raise ValueError(f"happens-before edge references an unknown node: {edge}")
        if edge["before"] == edge["after"]:
            raise ValueError("happens-before self edge is not allowed")
    diagnostics = schedule["diagnostics"]
    if diagnostics.get("crossThreadOrder") != "EXPLICIT_EDGES_ONLY":
        raise ValueError("cross-thread order must use explicit edges only")
    if any(diagnostics.get(name) != "DIAGNOSTIC_ONLY" for name in ("wallClock", "nanoTime")):
        raise ValueError("wall and nano time must be diagnostic only")


def freeze_corpus(root: Path, output_directory: Path = DEFAULT_CORPUS) -> list[Path]:
    canonical_path = root / DEFAULT_CANONICAL
    canonical = read_json(canonical_path)
    provenance = {
        "canonicalTraceSha256": sha256_file(canonical_path),
        "modelSha256": canonical["provenance"]["moduleSha256"],
        "mappingSha256": canonical["provenance"]["mappingSha256"],
    }
    destination = root / output_directory
    paths: list[Path] = []
    seed = int(canonical["configuration"]["seed"])
    for offset, trace in enumerate(canonical["traces"]):
        schedule = schedule_from_trace(trace, provenance, seed + offset)
        validate_schedule(schedule)
        path = destination / f"{trace['id']}.json"
        write_json(path, schedule)
        paths.append(path)
    return paths
