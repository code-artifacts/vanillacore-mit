from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_AUDIT = Path("research/execution/week-04/gate-audit-v0.1.json")


def read_audit(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_gate_audit(root: Path, audit: Mapping[str, Any]) -> dict[str, int]:
    if audit.get("schemaVersion") != "vc-gate-audit-0.1":
        raise ValueError("unsupported gate audit schema")
    policy = audit.get("policy", {})
    if policy.get("unknown") != "REJECT":
        raise ValueError("unaudited gates must be rejected")

    points = audit.get("points", [])
    by_site = {point["sourceSite"]: point for point in points}
    if len(by_site) != len(points):
        raise ValueError("gate audit source sites must be unique")
    required = {"locktable.releaseAll.txEnd", "harness.barrier"}
    for mode in ("is", "ix", "s", "six", "x"):
        required.update(
            {
                f"locktable.{mode}.call",
                f"locktable.{mode}.wait",
                f"locktable.{mode}.grant",
                f"locktable.release.{mode}",
                f"locktable.releaseAll.{mode}",
            }
        )
    required.update(
        {
            "harness.transaction.commit",
            "harness.transaction.rollback",
            "harness.transaction.endStatement",
        }
    )
    missing = sorted(required - set(by_site))
    if missing:
        raise ValueError(f"gate audit is missing required sites: {missing}")

    blocking = 0
    observe_only = 0
    for point in points:
        source = root / point["source"]
        if not source.is_file():
            raise ValueError(f"gate audit source does not exist: {point['source']}")
        lines = source.read_text(encoding="utf-8").splitlines()
        if point["line"] < 1 or point["line"] > len(lines):
            raise ValueError(f"gate audit line is stale: {point['sourceSite']}")
        if point["controllerWait"] == "BLOCKING_ALLOWED":
            blocking += 1
            if point["holdsAnchorMonitor"]:
                raise ValueError(f"blocking gate holds anchor monitor: {point['sourceSite']}")
        elif point["controllerWait"] == "OBSERVE_ONLY":
            observe_only += 1
        else:
            raise ValueError(f"unknown controller wait verdict: {point['sourceSite']}")
    return {"points": len(points), "blockingAllowed": blocking, "observeOnly": observe_only}
