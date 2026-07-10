from __future__ import annotations

import re
from typing import Any


def validate_candidate(candidate: dict[str, Any], context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = context["mechanism_graph"]
    node_ids = {str(item.get("id")) for item in graph.get("nodes", []) if isinstance(item, dict)}
    edge_ids = {str(item.get("id")) for item in graph.get("edges", []) if isinstance(item, dict)}
    constraints = context["generation_constraints"]
    required_nodes = node_ids
    required_edges = edge_ids
    node_mappings = candidate.get("node_mappings")
    edge_mappings = candidate.get("edge_mappings")
    if not isinstance(node_mappings, list) or not node_mappings:
        errors.append("node_mappings must be a non-empty array")
        node_mappings = []
    if not isinstance(edge_mappings, list):
        errors.append("edge_mappings must be an array")
        edge_mappings = []
    mapped_nodes = {str(item.get("mechanism_node_id")) for item in node_mappings if isinstance(item, dict)}
    mapped_edges = {str(item.get("mechanism_edge_id")) for item in edge_mappings if isinstance(item, dict)}
    if any(item not in node_ids for item in mapped_nodes):
        errors.append("unknown mechanism node mapping")
    if any(item not in edge_ids for item in mapped_edges):
        errors.append("unknown mechanism edge mapping")
    if not required_nodes.issubset(mapped_nodes):
        errors.append("must-preserve node coverage is incomplete")
    if not required_edges.issubset(mapped_edges):
        errors.append("must-preserve edge coverage is incomplete")
    if any(item.get("direction_preserved") is not True for item in edge_mappings if isinstance(item, dict)):
        errors.append("edge direction must be preserved")
    if not str(candidate.get("source_domain") or "").strip():
        errors.append("source_domain is required")
    return errors


def inspect_template_risk(candidate: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    carriers = [
        _normalize(item.get("story_carrier"))
        for item in candidate.get("node_mappings", [])
        if isinstance(item, dict) and item.get("story_carrier")
    ]
    relations = [
        _normalize(item.get("story_relation"))
        for item in candidate.get("edge_mappings", [])
        if isinstance(item, dict) and item.get("story_relation")
    ]
    events = [_normalize(item) for item in candidate.get("event_chain", []) if str(item).strip()]
    if _duplicate_ratio(carriers) > 0.2:
        issues.append("repeated_story_carriers")
    if _duplicate_ratio(relations) > 0.2:
        issues.append("repeated_edge_realizations")
    if _duplicate_ratio(events) > 0.2:
        issues.append("repeated_events")
    if any(re.search(r"第\s*\d+\s*(道|个)?.{0,4}(环节|步骤)", text) for text in carriers):
        issues.append("ordinal_placeholder_carriers")
    if len(set(events)) < 2:
        issues.append("insufficient_event_variation")
    return issues


def score_candidate(candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    graph = context["mechanism_graph"]
    constraints = context["generation_constraints"]
    required_nodes = {
        str(item.get("id"))
        for item in graph.get("nodes", [])
        if isinstance(item, dict) and item.get("id")
    }
    required_edges = {
        str(item.get("id"))
        for item in graph.get("edges", [])
        if isinstance(item, dict) and item.get("id")
    }
    mapped_nodes = {
        str(item.get("mechanism_node_id"))
        for item in candidate.get("node_mappings", [])
        if isinstance(item, dict)
    }
    mapped_edges = {
        str(item.get("mechanism_edge_id"))
        for item in candidate.get("edge_mappings", [])
        if isinstance(item, dict)
    }
    node_coverage = _coverage(required_nodes, mapped_nodes)
    edge_coverage = _coverage(required_edges, mapped_edges)
    carriers = [
        _normalize(item.get("story_carrier"))
        for item in candidate.get("node_mappings", [])
        if isinstance(item, dict) and item.get("story_carrier")
    ]
    relations = [
        _normalize(item.get("story_relation"))
        for item in candidate.get("edge_mappings", [])
        if isinstance(item, dict) and item.get("story_relation")
    ]
    carrier_diversity = 1.0 - _duplicate_ratio(carriers)
    relation_diversity = 1.0 - _duplicate_ratio(relations)
    text = " ".join([str(candidate.get("source_domain") or ""), *carriers, *relations])
    forbidden = [str(item) for item in constraints.get("forbidden_terms", []) if str(item).strip()]
    leakage_free = 0.0 if any(term in text for term in forbidden) else 1.0
    narrative_complete = sum(
        bool(candidate.get(key))
        for key in ("conflict", "event_chain", "turning_point", "resolution_state")
    ) / 4.0
    issues = inspect_template_risk(candidate)
    template_quality = max(0.0, 1.0 - 0.18 * len(issues))
    score = (
        0.28 * node_coverage
        + 0.28 * edge_coverage
        + 0.14 * carrier_diversity
        + 0.10 * relation_diversity
        + 0.08 * leakage_free
        + 0.06 * narrative_complete
        + 0.06 * template_quality
    )
    score = max(0.0, score - 0.06 * len(issues))
    validation_errors = validate_candidate(candidate, context)
    if validation_errors:
        score *= 0.2
    return {
        "score": round(score, 4),
        "temperature": round(100.0 * (1.0 - score), 2),
        "node_coverage": round(node_coverage, 4),
        "edge_coverage": round(edge_coverage, 4),
        "carrier_diversity": round(carrier_diversity, 4),
        "relation_diversity": round(relation_diversity, 4),
        "leakage_free": leakage_free,
        "narrative_complete": round(narrative_complete, 4),
        "template_issues": issues,
        "validation_errors": validation_errors,
        "mechanism_node_count": len(graph.get("nodes", [])),
    }


def _coverage(required: set[str], mapped: set[str]) -> float:
    return 1.0 if not required else len(required & mapped) / len(required)


def _duplicate_ratio(items: list[str]) -> float:
    if len(items) <= 1:
        return 0.0
    return 1.0 - len(set(items)) / len(items)


def _normalize(value: Any) -> str:
    return "".join(str(value or "").split()).casefold()
