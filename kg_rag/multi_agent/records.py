from __future__ import annotations

from typing import Any

from kg_rag.multi_agent.text import unique_strings


def build_m2na_record(
    *,
    card: dict[str, Any],
    mechanism_graph: dict[str, Any],
    narrative: str,
    alignment: dict[str, Any],
    method: str = "con2fable-multi-agent",
) -> dict[str, Any]:
    return {
        "id": card["concept_id"],
        "method": method,
        "concept": {
            "name": card.get("canonical_name") or card["concept_id"],
            "aliases": unique_strings(card.get("aliases", [])),
            "forbidden_terms": unique_strings(
                [
                    card.get("canonical_name"),
                    *card.get("aliases", []),
                    *card.get("forbidden_terms_zh", []),
                ]
            ),
        },
        "mechanism_graph": {
            "nodes": mechanism_graph.get("nodes", []),
            "edges": mechanism_graph.get("edges", []),
        },
        "output": {
            "narrative": narrative,
            "node_alignments": alignment.get("node_alignments", []),
            "edge_alignments": alignment.get("edge_alignments", []),
        },
    }
