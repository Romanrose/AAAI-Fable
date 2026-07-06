from __future__ import annotations

import json
from collections import defaultdict
from typing import Any


ALLOWED_RELATIONS = {
    "prerequisites_for",
    "is_a",
    "verifies",
    "leads_to",
    "relates_to",
}

RELATION_PRIORITY = {
    "prerequisites_for": 0,
    "is_a": 1,
    "verifies": 2,
    "leads_to": 3,
    "relates_to": 4,
}

RELATION_WEIGHTS = {
    "prerequisites_for": 1.0,
    "is_a": 0.85,
    "verifies": 0.75,
    "leads_to": 0.7,
    "relates_to": 0.55,
}

SUMMARY_BUCKETS = {
    "condition_summary": (
        "条件",
        "原料",
        "前提",
        "先修",
        "必需",
        "不可缺少",
        "输入",
        "工具",
    ),
    "process_summary": (
        "过程",
        "作用",
        "转化",
        "合成",
        "分解",
        "验证",
        "实验",
        "定律",
        "关系",
    ),
    "effect_summary": (
        "产物",
        "应用",
        "影响",
        "结果",
        "释放",
        "支持",
        "平衡",
        "输出",
    ),
}


def _normalize(text: Any) -> str:
    return "".join(str(text or "").casefold().split())


def _json_chars(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _node_text(node: dict[str, Any]) -> str:
    props = node.get("properties", {})
    parts = [node.get("name"), props.get("definition"), props.get("formula"), props.get("importance")]
    for key in ("aliases", "examples"):
        values = props.get(key, [])
        if isinstance(values, list):
            parts.extend(values)
    return " ".join(str(part) for part in parts if part)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = _normalize(text)
    return any(_normalize(keyword) in normalized for keyword in keywords)


def _resolve_target(graph: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    node_map = {
        node["id"]: node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    concept_id = card.get("concept_id")
    if concept_id in node_map:
        return node_map[str(concept_id)]

    query = _normalize(card.get("canonical_name") or concept_id)
    matches = [
        node
        for node in node_map.values()
        if node.get("label") == "Concept" and _normalize(node.get("name")) == query
    ]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"Could not resolve concept card in normalized graph: {concept_id!r}")


def _edge_score(edge: dict[str, Any], target: dict[str, Any], node_map: dict[str, dict[str, Any]]) -> float:
    relation = str(edge.get("type", ""))
    score = RELATION_WEIGHTS.get(relation, 0.0)
    source = node_map.get(edge.get("source"), {})
    target_node = node_map.get(edge.get("target"), {})
    if source.get("label") == "Concept" and target_node.get("label") == "Concept":
        score += 0.15

    target_text = _normalize(_node_text(target))
    endpoint_text = _normalize(f"{_node_text(source)} {_node_text(target_node)}")
    target_name = _normalize(target.get("name"))
    if target_name and target_name in endpoint_text:
        score += 0.2
    elif target_text and any(target_text[start : start + 4] in endpoint_text for start in range(max(0, len(target_text) - 3))):
        score += 0.12
    return round(score, 4)


def _serialize_edge(
    *,
    edge_index: int,
    edge: dict[str, Any],
    node_map: dict[str, dict[str, Any]],
    target: dict[str, Any],
) -> dict[str, Any]:
    source = node_map[edge["source"]]
    target_node = node_map[edge["target"]]
    relation = str(edge.get("type", ""))
    return {
        "source_edge_id": f"normalized:edge:{edge_index}",
        "source": edge["source"],
        "source_name": source.get("name", edge["source"]),
        "target": edge["target"],
        "target_name": target_node.get("name", edge["target"]),
        "relation": relation,
        "relation_description": relation,
        "evidence": "",
        "score": _edge_score(edge, target, node_map),
    }


def _summary_bucket(edge: dict[str, Any]) -> str:
    relation = edge.get("relation")
    if relation == "prerequisites_for":
        return "condition_summary"
    if relation == "leads_to":
        return "effect_summary"
    text = " ".join(
        str(value)
        for value in (
            edge.get("source_name"),
            edge.get("target_name"),
            edge.get("relation_description"),
        )
        if value
    )
    for bucket, keywords in SUMMARY_BUCKETS.items():
        if _contains_any(text, keywords):
            return bucket
    return "process_summary"


def _summary_entry(edge: dict[str, Any]) -> str:
    return (
        f"[{edge['source_edge_id']}] "
        f"{edge['source_name']} --{edge['relation']}--> {edge['target_name']}"
    )


def _topic_summary(target: dict[str, Any], raw_edges: list[dict[str, Any]]) -> dict[str, Any]:
    props = target.get("properties", {})
    summary: dict[str, Any] = {
        "definition_summary": {
            "name": target.get("name"),
            "definition": props.get("definition", ""),
            "formula": props.get("formula", ""),
            "importance": props.get("importance", ""),
        },
        "condition_summary": [],
        "process_summary": [],
        "effect_summary": [],
    }
    seen: dict[str, set[str]] = defaultdict(set)
    for edge in raw_edges:
        bucket = _summary_bucket(edge)
        entry = _summary_entry(edge)
        if entry not in seen[bucket] and len(summary[bucket]) < 5:
            summary[bucket].append(entry)
            seen[bucket].add(entry)
    return summary


def retrieve_dual_level(
    *,
    normalized_graph: dict[str, Any],
    card: dict[str, Any],
    max_edges: int = 16,
) -> dict[str, Any]:
    if max_edges < 1:
        raise ValueError("max_edges must be at least 1")

    target = _resolve_target(normalized_graph, card)
    target_id = target["id"]
    node_map = {
        node["id"]: node
        for node in normalized_graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    candidates = []
    for edge_index, edge in enumerate(normalized_graph.get("edges", [])):
        if not isinstance(edge, dict):
            continue
        if edge.get("type") not in ALLOWED_RELATIONS:
            continue
        if target_id not in (edge.get("source"), edge.get("target")):
            continue
        if edge.get("source") not in node_map or edge.get("target") not in node_map:
            continue
        candidates.append((edge_index, edge))

    raw_edges = [
        _serialize_edge(edge_index=edge_index, edge=edge, node_map=node_map, target=target)
        for edge_index, edge in candidates
    ]
    raw_edges = sorted(
        raw_edges,
        key=lambda edge: (
            -float(edge.get("score", 0.0)),
            RELATION_PRIORITY.get(edge.get("relation"), 99),
            str(edge.get("source_name", "")),
            str(edge.get("target_name", "")),
            str(edge.get("source_edge_id", "")),
        ),
    )[:max_edges]
    topic_summary = _topic_summary(target, raw_edges)
    retrieval_stats = {
        "retrieval_mode": "dual_level",
        "retrieval_edge_count": len(raw_edges),
        "candidate_edge_count": len(candidates),
        "retrieval_path_count": 0,
        "raw_edge_chars": _json_chars(raw_edges),
        "summary_chars": _json_chars(topic_summary),
        "path_chars": 0,
    }
    retrieval_stats["retrieval_context_chars"] = (
        retrieval_stats["raw_edge_chars"] + retrieval_stats["summary_chars"]
    )

    target_value = {
        "source_node_id": target_id,
        "label": target.get("label"),
        "name": target.get("name"),
        "properties": target.get("properties", {}),
    }
    return {
        "target": target_value,
        "raw_edges": raw_edges,
        "selected_paths": [],
        "topic_summary": topic_summary,
        "retrieval_stats": retrieval_stats,
    }

