from __future__ import annotations

from typing import Any


def evaluate_alignment(
    *,
    mechanism_graph: dict[str, Any],
    alignment: dict[str, Any],
    story: str,
    forbidden_terms: list[str],
) -> dict[str, Any]:
    node_ids = {str(item.get("id")) for item in mechanism_graph.get("nodes", []) if isinstance(item, dict)}
    edge_ids = {str(item.get("id")) for item in mechanism_graph.get("edges", []) if isinstance(item, dict)}
    node_rows = [item for item in alignment.get("node_alignments", []) if isinstance(item, dict)]
    edge_rows = [item for item in alignment.get("edge_alignments", []) if isinstance(item, dict)]
    aligned_nodes = {
        str(item.get("mechanism_node_id"))
        for item in node_rows
        if _valid_evidence(item.get("story_evidence"), story)
    }
    aligned_edges = {
        str(item.get("mechanism_edge_id"))
        for item in edge_rows
        if _valid_evidence(item.get("story_evidence"), story)
    }
    directed_edges = {
        str(item.get("mechanism_edge_id"))
        for item in edge_rows
        if _valid_evidence(item.get("story_evidence"), story) and item.get("direction_preserved") is True
    }
    leaked = [term for term in forbidden_terms if term and term in story]
    story_chars = len(story)
    return {
        "node_coverage": _coverage(node_ids, aligned_nodes),
        "edge_coverage": _coverage(edge_ids, aligned_edges),
        "direction_accuracy": _coverage(aligned_edges, directed_edges),
        "exact_evidence_precision": _evidence_precision([*node_rows, *edge_rows], story),
        "forbidden_terms_found": leaked,
        "hard_leakage": bool(leaked),
        "story_chars": story_chars,
        "length_valid": 450 <= story_chars <= 750,
    }


def _valid_evidence(value: Any, story: str) -> bool:
    text = str(value or "").strip()
    return len(text) >= 2 and text in story


def _coverage(expected: set[str], actual: set[str]) -> float:
    if not expected:
        return 1.0
    return round(len(expected & actual) / len(expected), 4)


def _evidence_precision(rows: list[dict[str, Any]], story: str) -> float:
    evidence = [str(item.get("story_evidence") or "").strip() for item in rows if str(item.get("story_evidence") or "").strip()]
    if not evidence:
        return 0.0
    return round(sum(item in story for item in evidence) / len(evidence), 4)
