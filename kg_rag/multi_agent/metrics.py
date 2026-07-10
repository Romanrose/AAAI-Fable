from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Iterable

from kg_rag.multi_agent.text import contains_term


DEFAULT_TEMPLATE_TERMS = [
    "智者",
    "老人",
    "森林",
    "小动物",
    "村庄",
    "镜子",
    "钟表",
    "河流",
    "从此以后",
    "大家明白了",
]

TYPED_RELATIONS = {
    "prerequisites_for",
    "is_a",
    "verifies",
    "leads_to",
    "relates_to",
}

RELATION_KEYWORDS = {
    "prerequisites_for": ("先", "前置", "条件", "缺少", "不能", "确认"),
    "is_a": ("属于", "归入", "更大", "类别", "规则", "共同"),
    "verifies": ("检验", "验证", "证据", "比较", "核验", "复查", "记录"),
    "leads_to": ("导致", "推动", "产生", "结果", "因此", "承接", "再"),
    "relates_to": ("相关", "比较", "参照", "一起", "共同", "关联"),
}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def evidence_exists(narrative: str, evidence: Any) -> bool:
    return isinstance(evidence, str) and bool(evidence.strip()) and contains_term(
        narrative, evidence
    )


def alignment_anchor(alignment: Any) -> Any:
    if not isinstance(alignment, dict):
        return None
    anchor = alignment.get("narrative_anchor")
    if _is_nonempty_string(anchor):
        return anchor
    return alignment.get("evidence")


def validate_record(record: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be an object"]

    for key in ("id", "method"):
        if not _is_nonempty_string(record.get(key)):
            errors.append(f"{key} must be a non-empty string")

    concept = record.get("concept")
    if not isinstance(concept, dict):
        errors.append("concept must be an object")
    else:
        if not _is_nonempty_string(concept.get("name")):
            errors.append("concept.name must be a non-empty string")
        for key in ("aliases", "forbidden_terms"):
            value = concept.get(key, [])
            if not isinstance(value, list) or not all(_is_nonempty_string(item) for item in value):
                errors.append(f"concept.{key} must be an array of non-empty strings")

    graph = record.get("mechanism_graph")
    node_ids: set[str] = set()
    edge_ids: set[str] = set()
    if not isinstance(graph, dict):
        errors.append("mechanism_graph must be an object")
    else:
        nodes = graph.get("nodes")
        edges = graph.get("edges")
        if not isinstance(nodes, list) or not nodes:
            errors.append("mechanism_graph.nodes must be a non-empty array")
            nodes = []
        if not isinstance(edges, list):
            errors.append("mechanism_graph.edges must be an array")
            edges = []

        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"node[{index}] must be an object")
                continue
            node_id = node.get("id")
            if not _is_nonempty_string(node_id):
                errors.append(f"node[{index}].id must be a non-empty string")
            elif node_id in node_ids:
                errors.append(f"duplicate node id: {node_id}")
            else:
                node_ids.add(node_id)
            if not _is_nonempty_string(node.get("text")):
                errors.append(f"node[{index}].text must be a non-empty string")

        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(f"edge[{index}] must be an object")
                continue
            edge_id = edge.get("id")
            if not _is_nonempty_string(edge_id):
                errors.append(f"edge[{index}].id must be a non-empty string")
            elif edge_id in edge_ids:
                errors.append(f"duplicate edge id: {edge_id}")
            else:
                edge_ids.add(edge_id)
            for key in ("source", "target", "relation"):
                if not _is_nonempty_string(edge.get(key)):
                    errors.append(f"edge[{index}].{key} must be a non-empty string")
            if _is_nonempty_string(edge.get("source")) and edge["source"] not in node_ids:
                errors.append(f"edge[{index}].source references unknown node")
            if _is_nonempty_string(edge.get("target")) and edge["target"] not in node_ids:
                errors.append(f"edge[{index}].target references unknown node")

    output = record.get("output")
    if not isinstance(output, dict):
        errors.append("output must be an object")
    else:
        if not _is_nonempty_string(output.get("narrative")):
            errors.append("output.narrative must be a non-empty string")
        for key in ("node_alignments", "edge_alignments"):
            if not isinstance(output.get(key), list):
                errors.append(f"output.{key} must be an array")

    return errors


def _weighted_coverage(items: list[dict[str, Any]], covered_ids: set[str]) -> float:
    if not items:
        return 1.0
    total = sum(float(item.get("weight", 1.0)) for item in items)
    covered = sum(float(item.get("weight", 1.0)) for item in items if item.get("id") in covered_ids)
    return covered / total if total else 0.0


def _typed_relation_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        edge
        for edge in edges
        if isinstance(edge, dict)
        and str(edge.get("kg_relation") or "") in TYPED_RELATIONS
    ]


def _relation_preserved(edge: dict[str, Any], alignment: dict[str, Any]) -> bool:
    relation = str(edge.get("kg_relation") or edge.get("relation") or "")
    if relation not in TYPED_RELATIONS:
        return False
    text = " ".join(
        str(alignment.get(key) or "")
        for key in ("evidence", "narrative_anchor")
    )
    if not text:
        return False
    return any(keyword in text for keyword in RELATION_KEYWORDS.get(relation, ()))


def evaluate_record(
    record: dict[str, Any],
    template_terms: Iterable[str] = DEFAULT_TEMPLATE_TERMS,
) -> dict[str, Any]:
    validation_errors = validate_record(record)
    result: dict[str, Any] = {
        "id": record.get("id"),
        "method": record.get("method"),
        "format_validity": 0.0 if validation_errors else 1.0,
        "validation_errors": validation_errors,
    }
    if validation_errors:
        return result

    concept = record["concept"]
    graph = record["mechanism_graph"]
    output = record["output"]
    narrative = output["narrative"]

    exact_terms = [concept["name"], *concept.get("aliases", [])]
    soft_terms = concept.get("forbidden_terms", [])
    exact_hits = sorted({term for term in exact_terms if contains_term(narrative, term)})
    soft_hits = sorted({term for term in soft_terms if contains_term(narrative, term)})

    node_ids = {item["id"] for item in graph["nodes"]}
    edge_ids = {item["id"] for item in graph["edges"]}
    edges_by_id = {item["id"]: item for item in graph["edges"]}
    valid_node_ids: set[str] = set()
    valid_edge_ids: set[str] = set()
    preserved_typed_edge_ids: set[str] = set()
    valid_alignments = 0
    invalid_alignments = 0
    direction_values: list[bool] = []

    for alignment in output["node_alignments"]:
        valid = (
            isinstance(alignment, dict)
            and alignment.get("concept_node_id") in node_ids
            and evidence_exists(narrative, alignment_anchor(alignment))
        )
        if valid:
            valid_alignments += 1
            valid_node_ids.add(alignment["concept_node_id"])
        else:
            invalid_alignments += 1

    for alignment in output["edge_alignments"]:
        valid = (
            isinstance(alignment, dict)
            and alignment.get("concept_edge_id") in edge_ids
            and evidence_exists(narrative, alignment_anchor(alignment))
        )
        if valid:
            valid_alignments += 1
            valid_edge_ids.add(alignment["concept_edge_id"])
            mechanism_edge = edges_by_id[alignment["concept_edge_id"]]
            direction_values.append(
                alignment.get("direction_preserved") is True
                and alignment.get("narrative_source_concept_node_id") == mechanism_edge["source"]
                and alignment.get("narrative_target_concept_node_id") == mechanism_edge["target"]
            )
            if _relation_preserved(mechanism_edge, alignment):
                preserved_typed_edge_ids.add(alignment["concept_edge_id"])
        else:
            invalid_alignments += 1

    alignment_count = valid_alignments + invalid_alignments
    template_terms = list(template_terms)
    template_hits = sorted({term for term in template_terms if contains_term(narrative, term)})
    typed_edges = _typed_relation_edges(graph["edges"])
    typed_edge_ids = {edge["id"] for edge in typed_edges}
    covered_typed_edge_ids = valid_edge_ids & typed_edge_ids

    result.update(
        {
            "exact_concept_leakage": float(bool(exact_hits)),
            "soft_term_leakage": float(bool(soft_hits)),
            "exact_leakage_hits": exact_hits,
            "soft_leakage_hits": soft_hits,
            "node_coverage": len(valid_node_ids) / len(node_ids),
            "weighted_node_coverage": _weighted_coverage(graph["nodes"], valid_node_ids),
            "edge_coverage": len(valid_edge_ids) / len(edge_ids) if edge_ids else 1.0,
            "weighted_edge_coverage": _weighted_coverage(graph["edges"], valid_edge_ids),
            "alignment_precision": valid_alignments / alignment_count if alignment_count else 0.0,
            "alignment_hallucination_rate": invalid_alignments / alignment_count if alignment_count else 0.0,
            "relation_direction_accuracy": (
                sum(direction_values) / len(direction_values) if direction_values else None
            ),
            "template_hit_rate": len(template_hits) / len(template_terms) if template_terms else 0.0,
            "template_hits": template_hits,
            "narrative_char_count": len(narrative.strip()),
            "valid_node_alignment_count": len(valid_node_ids),
            "valid_edge_alignment_count": len(valid_edge_ids),
            "concept_relation_coverage": (
                len(covered_typed_edge_ids) / len(typed_edges) if typed_edges else None
            ),
            "typed_relation_preservation": (
                len(preserved_typed_edge_ids) / len(typed_edges) if typed_edges else None
            ),
        }
    )
    return result


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = [
        "format_validity",
        "exact_concept_leakage",
        "soft_term_leakage",
        "node_coverage",
        "weighted_node_coverage",
        "edge_coverage",
        "weighted_edge_coverage",
        "alignment_precision",
        "alignment_hallucination_rate",
        "relation_direction_accuracy",
        "concept_relation_coverage",
        "typed_relation_preservation",
        "template_hit_rate",
        "narrative_char_count",
    ]
    summary: dict[str, Any] = {"sample_count": len(results)}
    for metric in metric_names:
        values = [float(result[metric]) for result in results if result.get(metric) is not None]
        summary[metric] = statistics.fmean(values) if values else None
    return summary


def group_by_method(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[str(result.get("method", "unknown"))].append(result)
    return {method: aggregate(items) for method, items in sorted(grouped.items())}
