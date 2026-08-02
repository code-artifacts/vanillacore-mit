from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common.cli import execute
from .common.tooling import repository_root
from .gate_audit import DEFAULT_AUDIT, read_audit, validate_gate_audit
from .week4_schedule import sha256_file, write_json


DEFAULT_RESULT = Path("research/execution/week-04/results/step-02-gate-audit.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the Week 4 gate-safe audit.")
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    return parser


def run(args: argparse.Namespace) -> str:
    root = repository_root()
    audit_path = root / args.audit
    counts = validate_gate_audit(root, read_audit(audit_path))
    destination = root / args.result
    result = {
        "schemaVersion": 1,
        "step": "week-04-step-02-gate-audit",
        "status": "PASS",
        "audit": args.audit.as_posix(),
        "auditSha256": sha256_file(audit_path),
        **counts,
        "decision": "REJECT_UNAUDITED_OR_MONITOR_HELD_BLOCKING_GATES",
    }
    write_json(destination, result)
    return json.dumps({"result": args.result.as_posix(), **counts})


def main() -> int:
    return execute(lambda: run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
