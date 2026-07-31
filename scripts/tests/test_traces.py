from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.research.traces import SCENARIOS, extract_trace, parse_dot_graph


INITIAL = r'''/\ owners = (r1 :> (t1 :> "NONE" @@ t2 :> "NONE"))\n/\ xGranted = (t1 :> {} @@ t2 :> {})\n/\ pendingResource = (t1 :> "NO_RESOURCE" @@ t2 :> "NO_RESOURCE")\n/\ requestCount = 0\n/\ pendingMode = (t1 :> "NONE" @@ t2 :> "NONE")\n/\ lastEvent = [tx |-> "NO_TX", resource |-> "NO_RESOURCE", mode |-> "NONE", action |-> "INIT"]\n/\ held = (t1 :> (r1 :> "NONE") @@ t2 :> (r1 :> "NONE"))\n/\ txState = (t1 :> "ACTIVE" @@ t2 :> "ACTIVE")'''
REQUEST = r'''/\ owners = (r1 :> (t1 :> "NONE" @@ t2 :> "NONE"))\n/\ xGranted = (t1 :> {} @@ t2 :> {})\n/\ pendingResource = (t1 :> r1 @@ t2 :> "NO_RESOURCE")\n/\ requestCount = 1\n/\ pendingMode = (t1 :> "S" @@ t2 :> "NONE")\n/\ lastEvent = [tx |-> t1, resource |-> r1, mode |-> "S", action |-> "REQUEST_S"]\n/\ held = (t1 :> (r1 :> "NONE") @@ t2 :> (r1 :> "NONE"))\n/\ txState = (t1 :> "ACTIVE" @@ t2 :> "ACTIVE")'''
GRANT = r'''/\ owners = (r1 :> (t1 :> "S" @@ t2 :> "NONE"))\n/\ xGranted = (t1 :> {} @@ t2 :> {})\n/\ pendingResource = (t1 :> "NO_RESOURCE" @@ t2 :> "NO_RESOURCE")\n/\ requestCount = 1\n/\ pendingMode = (t1 :> "NONE" @@ t2 :> "NONE")\n/\ lastEvent = [ tx |-> t1,\n  resource |-> r1,\n  mode |-> "S",\n  action |-> "GRANT" ]\n/\ held = (t1 :> (r1 :> "S") @@ t2 :> (r1 :> "NONE"))\n/\ txState = (t1 :> "ACTIVE" @@ t2 :> "ACTIVE")'''


class TraceExportTest(unittest.TestCase):
    def _graph(self) -> dict[str, object]:
        content = "\n".join(
            (
                "strict digraph DiskGraph {",
                f'1 [label="{INITIAL}",style = filled]',
                '1 -> 2 [label="RequestS",color="black"];',
                '1 -> 2 [label="RequestS",color="black"];',
                f'2 [label="{REQUEST}"];',
                '2 -> 3 [label="Grant",color="black"];',
                f'3 [label="{GRANT}"];',
                "}",
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "graph.dot"
            path.write_text(content, encoding="utf-8")
            return parse_dot_graph(path)

    def test_parser_deduplicates_edges_and_reads_multiline_event(self) -> None:
        graph = self._graph()
        self.assertEqual("1", graph["initial"])
        self.assertEqual(3, graph["nodeCount"])
        self.assertEqual(2, graph["edgeCount"])
        self.assertEqual("GRANT", graph["nodes"]["3"]["event"]["action"])

    def test_exact_trace_includes_structured_final_state(self) -> None:
        graph = self._graph()
        scenario = {
            "id": "fixture",
            "family": "fixture",
            "events": (
                {"action": "REQUEST_S", "tx": "t1", "resource": "r1", "mode": "S"},
                {"action": "GRANT", "tx": "t1", "resource": "r1", "mode": "S"},
            ),
        }
        trace = extract_trace(graph, scenario)
        self.assertEqual(2, trace["actionCount"])
        self.assertEqual("S", trace["finalState"]["held"]["t1"]["r1"])
        self.assertEqual(1, trace["finalState"]["requestCount"])

    def test_catalog_contains_all_eight_required_families(self) -> None:
        self.assertEqual(8, len(SCENARIOS))
        self.assertEqual(
            {
                "S/S",
                "S/X",
                "X/S",
                "X/X",
                "single upgrader",
                "double upgrader",
                "writer commit then reader grant",
                "writer rollback then reader grant",
            },
            {scenario["family"] for scenario in SCENARIOS},
        )


if __name__ == "__main__":
    unittest.main()
