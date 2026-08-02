from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_PROJECTION = Path(
    "research/execution/week-04/direct-native-projection-v0.1.json"
)


def read_projection(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_projection(root: Path, projection: Mapping[str, Any]) -> dict[str, int]:
    if projection.get("schemaVersion") != "vc-direct-native-projection-0.1":
        raise ValueError("unsupported projection schema")
    required_actions = {
        "REQUEST_S",
        "REQUEST_X",
        "UPGRADE_REQUEST",
        "WAIT",
        "GRANT",
        "COMMIT_OR_ROLLBACK_THEN_RELEASE_ALL",
        "WAKE_THEN_GRANT",
    }
    rules = projection.get("rules", [])
    missing = required_actions - {rule["l1Action"] for rule in rules}
    if missing:
        raise ValueError(f"projection is missing L1 actions: {sorted(missing)}")
    for rule in rules:
        source = root / rule["source"]
        if not source.is_file():
            raise ValueError(f"projection source is missing: {rule['source']}")
        lines = source.read_text(encoding="utf-8").splitlines()
        if rule["line"] < 1 or rule["line"] > len(lines):
            raise ValueError(f"projection source line is stale: {rule['l1Action']}")
    lifecycle = projection.get("lifecycleContext", {})
    transaction = root / lifecycle.get("transactionSource", "")
    if not transaction.is_file():
        raise ValueError("projection lifecycle source is missing")
    return {
        "rules": len(rules),
        "families": len(projection.get("requiredFamilies", [])),
        "contextClasses": len(projection.get("ignoredFromL1ButRetainedAsContext", [])),
    }
