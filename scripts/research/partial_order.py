from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


def validate_dag(schedule: Mapping[str, Any]) -> list[str]:
    nodes = {
        item["id"] for item in schedule["operations"]
    } | {item["id"] for item in schedule["observations"]}
    predecessors: dict[str, set[str]] = {node: set() for node in nodes}
    successors: dict[str, set[str]] = defaultdict(set)
    for edge in schedule["happensBefore"]:
        before = edge["before"]
        after = edge["after"]
        if before not in nodes or after not in nodes:
            raise ValueError(f"edge references unknown node: {before} -> {after}")
        predecessors[after].add(before)
        successors[before].add(after)
    ready = sorted(node for node, values in predecessors.items() if not values)
    linearization: list[str] = []
    while ready:
        current = ready.pop(0)
        linearization.append(current)
        for successor in sorted(successors[current]):
            predecessors[successor].remove(current)
            if not predecessors[successor]:
                ready.append(successor)
                ready.sort()
    if len(linearization) != len(nodes):
        raise ValueError("schedule happens-before relation contains a cycle")
    return linearization


def respects_edges(linearization: Sequence[str], edges: Sequence[Mapping[str, str]]) -> bool:
    positions = {node: index for index, node in enumerate(linearization)}
    return all(positions[edge["before"]] < positions[edge["after"]] for edge in edges)


def independent_fixture() -> dict[str, Any]:
    return {
        "nodes": ["a", "b", "c"],
        "edges": [
            {"before": "a", "after": "c", "kind": "HARNESS_BARRIER"},
            {"before": "b", "after": "c", "kind": "HARNESS_BARRIER"},
        ],
        "legalLinearizations": [["a", "b", "c"], ["b", "a", "c"]],
    }
