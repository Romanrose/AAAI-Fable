"""Deterministic Graph RAG retrieval over the rich K12-KGraph subject files."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUBJECT_FILES = {
    "biology": "biology.json",
    "chemistry": "chemistry.json",
    "math": "math.json",
    "physics": "physics.json",
}

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
    "prerequisites_for": 1.00,
    "is_a": 0.85,
    "verifies": 0.75,
    "leads_to": 0.70,
    "relates_to": 0.55,
}

RETRIEVAL_MODES = {"one_hop", "path_pruned", "dual_level", "path_dual"}

NON_MECHANISM_LABELS = {"Book", "Chapter", "Section", "Exercise"}

SUMMARY_BUCKETS = {
    "condition_summary": (
        "条件",
        "原料",
        "前提",
        "先修",
        "不可缺少",
        "必需",
        "工具",
        "色素",
        "捕获",
    ),
    "process_summary": (
        "过程",
        "作用",
        "转化",
        "合成",
        "制造",
        "分解",
        "验证",
        "实验",
        "定律",
    ),
    "effect_summary": (
        "产物",
        "应用",
        "影响",
        "结果",
        "释放",
        "支持",
        "平衡",
        "生产",
        "能量",
    ),
}


class RetrievalError(ValueError):
    """Raised when graph loading or concept resolution fails."""


@dataclass(frozen=True)
class GraphIndex:
    nodes_by_id: dict[str, dict[str, Any]]
    edge_items: list[tuple[int, dict[str, Any]]]
    in_edges_by_node: dict[str, list[tuple[int, dict[str, Any]]]]
    out_edges_by_node: dict[str, list[tuple[int, dict[str, Any]]]]
    incident_edges_by_node: dict[str, list[tuple[int, dict[str, Any]]]]


def normalize(text: str) -> str:
    return "".join(str(text).casefold().split())


def default_subject_path(subject: str) -> Path:
    filename = SUBJECT_FILES.get(subject)
    if not filename:
        supported = ", ".join(sorted(SUBJECT_FILES))
        raise RetrievalError(f"unsupported subject {subject!r}; choose one of: {supported}")
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "K12-KGraph"
        / "K12-KGraph"
        / "subject_specific_KG"
        / filename
    )


def load_subject_graph(subject: str, graph_path: Path | None = None) -> dict[str, Any]:
    path = graph_path or default_subject_path(subject)
    try:
        graph = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RetrievalError(f"subject graph not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RetrievalError(f"subject graph is not valid JSON: {path}: {exc}") from exc

    if not isinstance(graph, dict):
        raise RetrievalError(f"subject graph must be an object: {path}")
    if not isinstance(graph.get("nodes"), list) or not isinstance(
        graph.get("edges"), list
    ):
        raise RetrievalError(f"subject graph must contain node and edge arrays: {path}")
    return graph


def _concept_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        node
        for node in nodes
        if isinstance(node, dict)
        and node.get("label") == "Concept"
        and isinstance(node.get("name"), str)
    ]


def _raise_ambiguity(query: str, candidates: list[dict[str, Any]]) -> None:
    labels = ", ".join(
        f"{candidate.get('name')} ({candidate.get('id')})"
        for candidate in candidates[:8]
    )
    raise RetrievalError(f"concept {query!r} is ambiguous: {labels}")


def resolve_concept(nodes: list[dict[str, Any]], query: str) -> dict[str, Any]:
    normalized_query = normalize(query)
    if not normalized_query:
        raise RetrievalError("concept query must not be empty")

    concepts = _concept_nodes(nodes)
    exact = [
        node for node in concepts if normalize(node.get("name", "")) == normalized_query
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        _raise_ambiguity(query, exact)

    alias_matches = []
    for node in concepts:
        aliases = node.get("properties", {}).get("aliases", [])
        if isinstance(aliases, list) and any(
            normalize(alias) == normalized_query for alias in aliases
        ):
            alias_matches.append(node)
    if len(alias_matches) == 1:
        return alias_matches[0]
    if len(alias_matches) > 1:
        _raise_ambiguity(query, alias_matches)

    fuzzy = [
        node
        for node in concepts
        if normalized_query in normalize(node.get("name", ""))
        or normalize(node.get("name", "")) in normalized_query
    ]
    if len(fuzzy) == 1:
        return fuzzy[0]
    if len(fuzzy) > 1:
        _raise_ambiguity(query, fuzzy)
    raise RetrievalError(f"concept {query!r} was not found")


def _edge_has_endpoints(edge: Any) -> bool:
    return (
        isinstance(edge, dict)
        and isinstance(edge.get("source"), str)
        and bool(edge["source"])
        and isinstance(edge.get("target"), str)
        and bool(edge["target"])
    )


def _edge_evidence(edge: dict[str, Any]) -> str:
    properties = edge.get("properties")
    if not isinstance(properties, dict):
        return ""
    evidence = properties.get("evidence")
    return evidence.strip() if isinstance(evidence, str) else ""


def _edge_relations(edge: dict[str, Any]) -> str:
    properties = edge.get("properties")
    if not isinstance(properties, dict):
        return ""
    relations = properties.get("relations")
    return relations.strip() if isinstance(relations, str) else ""


def _edge_sort_key(item: tuple[int, dict[str, Any]]) -> tuple[Any, ...]:
    edge_index, edge = item
    relation = str(edge.get("type", ""))
    evidence = _edge_evidence(edge)
    return (
        RELATION_PRIORITY.get(relation, 99),
        0 if evidence else 1,
        str(edge.get("source_name", "")),
        str(edge.get("target_name", "")),
        edge_index,
    )


def _json_chars(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def build_graph_index(graph: dict[str, Any]) -> GraphIndex:
    nodes_by_id = {
        node["id"]: node
        for node in graph["nodes"]
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    edge_items: list[tuple[int, dict[str, Any]]] = []
    in_edges_by_node: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    out_edges_by_node: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    incident_edges_by_node: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)

    for edge_index, edge in enumerate(graph["edges"]):
        if not _edge_has_endpoints(edge):
            continue
        if edge["source"] not in nodes_by_id or edge["target"] not in nodes_by_id:
            continue
        item = (edge_index, edge)
        edge_items.append(item)
        out_edges_by_node[edge["source"]].append(item)
        in_edges_by_node[edge["target"]].append(item)
        incident_edges_by_node[edge["source"]].append(item)
        incident_edges_by_node[edge["target"]].append(item)

    return GraphIndex(
        nodes_by_id=nodes_by_id,
        edge_items=edge_items,
        in_edges_by_node=dict(in_edges_by_node),
        out_edges_by_node=dict(out_edges_by_node),
        incident_edges_by_node=dict(incident_edges_by_node),
    )


def _is_mechanism_node(node: dict[str, Any] | None) -> bool:
    return isinstance(node, dict) and node.get("label") not in NON_MECHANISM_LABELS


def _valid_mechanism_edge(edge: dict[str, Any], index: GraphIndex) -> bool:
    if edge.get("type") not in ALLOWED_RELATIONS:
        return False
    return _is_mechanism_node(index.nodes_by_id.get(edge["source"])) and _is_mechanism_node(
        index.nodes_by_id.get(edge["target"])
    )


def _property_text(properties: Any) -> str:
    if not isinstance(properties, dict):
        return ""
    parts: list[str] = []
    for key in ("definition", "formula", "importance"):
        value = properties.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("aliases", "examples"):
        values = properties.get(key)
        if isinstance(values, list):
            parts.extend(str(value) for value in values if value)
    return " ".join(parts)


def _node_text(node: dict[str, Any]) -> str:
    return " ".join(
        value
        for value in (
            str(node.get("name", "")),
            _property_text(node.get("properties", {})),
        )
        if value
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    return any(normalize(keyword) in normalized for keyword in keywords)


def _definition_overlap_bonus(
    target: dict[str, Any], edge: dict[str, Any], index: GraphIndex
) -> float:
    target_text = _node_text(target)
    if not target_text:
        return 0.0
    endpoint_text = " ".join(
        _node_text(index.nodes_by_id[node_id])
        for node_id in (edge["source"], edge["target"])
        if node_id in index.nodes_by_id
    )
    haystack = normalize(
        " ".join((endpoint_text, _edge_evidence(edge), _edge_relations(edge)))
    )
    target_name = normalize(str(target.get("name", "")))
    if target_name and target_name in haystack:
        return 0.20

    for value in (
        target.get("properties", {}).get("definition"),
        target.get("properties", {}).get("formula"),
    ):
        if not isinstance(value, str):
            continue
        normalized = normalize(value)
        fragments = {
            normalized[start : start + 4] for start in range(max(0, len(normalized) - 3))
        }
        if any(fragment and fragment in haystack for fragment in fragments):
            return 0.12
    return 0.0


def _edge_score(edge: dict[str, Any], target: dict[str, Any], index: GraphIndex) -> float:
    relation = str(edge.get("type", ""))
    score = RELATION_WEIGHTS.get(relation, 0.0)
    if _edge_evidence(edge):
        score += 0.25
    score += _definition_overlap_bonus(target, edge, index)
    if (
        index.nodes_by_id[edge["source"]].get("label") == "Concept"
        and index.nodes_by_id[edge["target"]].get("label") == "Concept"
    ):
        score += 0.15
    if relation == "relates_to" and not _edge_relations(edge) and not _edge_evidence(edge):
        score -= 0.20
    return round(score, 4)


def _serialized_node(node_id: str, index: GraphIndex) -> dict[str, Any]:
    node = index.nodes_by_id[node_id]
    return {
        "source_node_id": node_id,
        "label": node.get("label"),
        "name": node.get("name"),
        "properties": node.get("properties", {}),
    }


def _serialized_edge(
    subject: str,
    item: tuple[int, dict[str, Any]],
    index: GraphIndex,
    score: float | None = None,
) -> dict[str, Any]:
    edge_index, edge = item
    value: dict[str, Any] = {
        "source_edge_id": f"{subject}:edge:{edge_index}",
        "source": edge["source"],
        "source_name": index.nodes_by_id[edge["source"]].get("name", edge["source"]),
        "target": edge["target"],
        "target_name": index.nodes_by_id[edge["target"]].get("name", edge["target"]),
        "relation": edge["type"],
        "relation_description": _edge_relations(edge),
        "evidence": _edge_evidence(edge),
    }
    if score is not None:
        value["score"] = score
    return value


def _ranked_edges(
    subject: str,
    candidates: list[tuple[int, dict[str, Any]]],
    target: dict[str, Any],
    index: GraphIndex,
) -> list[dict[str, Any]]:
    scored = []
    for item in candidates:
        edge_index, edge = item
        score = _edge_score(edge, target, index)
        scored.append(
            (
                -score,
                RELATION_PRIORITY.get(str(edge.get("type", "")), 99),
                str(index.nodes_by_id[edge["source"]].get("name", "")),
                str(index.nodes_by_id[edge["target"]].get("name", "")),
                edge_index,
                item,
            )
        )
    return [
        _serialized_edge(subject, item, index, score=_edge_score(item[1], target, index))
        for *_sort_key, item in sorted(scored)
    ]


def _node_sort_key(target_id: str, index: GraphIndex, node_id: str) -> tuple[Any, ...]:
    return (
        0 if node_id == target_id else 1,
        str(index.nodes_by_id[node_id].get("name", "")),
        node_id,
    )


def _assemble_subgraph(
    *,
    subject: str,
    concept_query: str,
    target: dict[str, Any],
    index: GraphIndex,
    selected_edges: list[dict[str, Any]],
    candidate_edge_count: int,
    max_edges: int,
    retrieval_mode: str,
    hop_count: int,
    selected_paths: list[dict[str, Any]] | None = None,
    topic_summary: dict[str, Any] | None = None,
    extra_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_id = target["id"]
    node_ids = {target_id}
    for edge in selected_edges:
        node_ids.update((edge["source"], edge["target"]))
    for path in selected_paths or []:
        node_ids.update(path.get("node_ids", []))

    target_value = {
        "source_node_id": target_id,
        "label": target.get("label"),
        "name": target.get("name"),
        "properties": target.get("properties", {}),
    }
    node_values = [
        _serialized_node(node_id, index)
        for node_id in sorted(
            node_ids, key=lambda value: _node_sort_key(target_id, index, value)
        )
        if node_id in index.nodes_by_id
    ]
    selected_paths = selected_paths or []
    topic_summary = topic_summary or {}
    path_lengths = [
        int(path.get("length", 0))
        for path in selected_paths
        if isinstance(path, dict) and int(path.get("length", 0)) > 0
    ]
    raw_edge_chars = _json_chars(selected_edges)
    path_chars = _json_chars(selected_paths)
    summary_chars = _json_chars(topic_summary)
    retrieval_stats = {
        "retrieval_mode": retrieval_mode,
        "retrieval_edge_count": len(selected_edges),
        "candidate_edge_count": candidate_edge_count,
        "retrieval_path_count": len(selected_paths),
        "avg_path_length": round(statistics.fmean(path_lengths), 4)
        if path_lengths
        else 0.0,
        "max_path_length": max(path_lengths) if path_lengths else 0,
        "retrieval_context_chars": raw_edge_chars + path_chars + summary_chars,
        "raw_edge_chars": raw_edge_chars,
        "path_chars": path_chars,
        "summary_chars": summary_chars,
        "non_mechanism_node_ratio": _ratio(
            sum(1 for node in node_values if node.get("label") in NON_MECHANISM_LABELS),
            len(node_values),
        ),
    }
    retrieval_stats.update(extra_stats or {})
    retrieval_package = {
        "target": target_value,
        "raw_edges": selected_edges,
        "selected_paths": selected_paths,
        "topic_summary": topic_summary,
        "retrieval_stats": retrieval_stats,
    }

    return {
        "retrieval": {
            "subject": subject,
            "query": concept_query,
            "target_node_id": target_id,
            "retrieval_mode": retrieval_mode,
            "hop_count": hop_count,
            "allowed_relations": sorted(ALLOWED_RELATIONS),
            "max_edges": max_edges,
            "candidate_edge_count": candidate_edge_count,
            "selected_edge_count": len(selected_edges),
            "selected_path_count": len(selected_paths),
        },
        "target": target_value,
        "nodes": node_values,
        "edges": selected_edges,
        "selected_paths": selected_paths,
        "topic_summary": topic_summary,
        "retrieval_package": retrieval_package,
    }


def retrieve_one_hop(
    graph: dict[str, Any],
    concept_query: str,
    subject: str,
    max_edges: int = 12,
) -> dict[str, Any]:
    if max_edges < 1:
        raise RetrievalError("max_edges must be at least 1")

    target = resolve_concept(graph["nodes"], concept_query)
    target_id = target["id"]
    index = build_graph_index(graph)

    candidates = []
    for edge_index, edge in enumerate(graph["edges"]):
        if not _edge_has_endpoints(edge):
            continue
        if edge.get("type") not in ALLOWED_RELATIONS:
            continue
        if target_id not in (edge["source"], edge["target"]):
            continue
        if edge["source"] not in index.nodes_by_id or edge["target"] not in index.nodes_by_id:
            continue
        candidates.append((edge_index, edge))

    selected = sorted(candidates, key=_edge_sort_key)[:max_edges]
    serialized_edges = [_serialized_edge(subject, item, index) for item in selected]
    return _assemble_subgraph(
        subject=subject,
        concept_query=concept_query,
        target=target,
        index=index,
        selected_edges=serialized_edges,
        candidate_edge_count=len(candidates),
        max_edges=max_edges,
        retrieval_mode="one_hop",
        hop_count=1,
    )


def _ranked_ego_edges(
    subject: str,
    target: dict[str, Any],
    index: GraphIndex,
    max_edges: int,
) -> tuple[list[dict[str, Any]], int]:
    target_id = target["id"]
    candidates = [
        item
        for item in index.incident_edges_by_node.get(target_id, [])
        if _valid_mechanism_edge(item[1], index)
    ]
    return _ranked_edges(subject, candidates, target, index)[:max_edges], len(candidates)


def _mechanism_pattern_bonus(path: dict[str, Any]) -> float:
    node_text = " ".join(path["node_names"])
    categories = sum(
        1 for keywords in SUMMARY_BUCKETS.values() if _contains_any(node_text, keywords)
    )
    if categories >= 3:
        return 0.30
    if categories == 2:
        return 0.18
    if categories == 1:
        return 0.08
    return 0.0


def _path_text(path: dict[str, Any]) -> str:
    parts = [path["node_names"][0]]
    for step in path["steps"]:
        parts.append(f"--{step['relation']}-->")
        parts.append(step["traversal_target_name"])
    return " ".join(parts)


def _serialize_path(
    subject: str,
    path_index: int,
    node_ids: list[str],
    edge_items: list[tuple[int, dict[str, Any]]],
    target: dict[str, Any],
    index: GraphIndex,
) -> dict[str, Any]:
    steps = []
    edge_scores = []
    for offset, item in enumerate(edge_items):
        edge_index, edge = item
        traversal_source = node_ids[offset]
        traversal_target = node_ids[offset + 1]
        score = _edge_score(edge, target, index)
        edge_scores.append(score)
        steps.append(
            {
                "source_edge_id": f"{subject}:edge:{edge_index}",
                "source": edge["source"],
                "source_name": index.nodes_by_id[edge["source"]].get("name", edge["source"]),
                "target": edge["target"],
                "target_name": index.nodes_by_id[edge["target"]].get("name", edge["target"]),
                "traversal_source": traversal_source,
                "traversal_source_name": index.nodes_by_id[traversal_source].get(
                    "name", traversal_source
                ),
                "traversal_target": traversal_target,
                "traversal_target_name": index.nodes_by_id[traversal_target].get(
                    "name", traversal_target
                ),
                "relation": edge["type"],
                "relation_description": _edge_relations(edge),
                "evidence": _edge_evidence(edge),
                "score": score,
            }
        )
    path = {
        "path_id": f"p{path_index}",
        "length": len(edge_items),
        "node_ids": node_ids,
        "node_names": [
            index.nodes_by_id[node_id].get("name", node_id) for node_id in node_ids
        ],
        "edge_ids": [step["source_edge_id"] for step in steps],
        "relations": [step["relation"] for step in steps],
        "steps": steps,
        "base_score": round(
            statistics.fmean(edge_scores) * (0.75 ** (len(edge_items) - 1)), 4
        ),
    }
    path["base_score"] = round(path["base_score"] + _mechanism_pattern_bonus(path), 4)
    path["path_text"] = _path_text(path)
    return path


def _generate_candidate_paths(
    subject: str,
    target: dict[str, Any],
    index: GraphIndex,
    max_hops: int,
) -> list[dict[str, Any]]:
    if max_hops < 1:
        raise RetrievalError("max_hops must be at least 1")
    target_id = target["id"]
    queue: list[tuple[list[str], list[tuple[int, dict[str, Any]]]]] = [([target_id], [])]
    paths: list[dict[str, Any]] = []
    path_counter = 1

    while queue:
        node_ids, edge_items = queue.pop(0)
        current_id = node_ids[-1]
        if edge_items:
            paths.append(
                _serialize_path(
                    subject,
                    path_counter,
                    node_ids,
                    edge_items,
                    target,
                    index,
                )
            )
            path_counter += 1
        if len(edge_items) >= max_hops:
            continue

        for item in sorted(index.incident_edges_by_node.get(current_id, []), key=_edge_sort_key):
            edge = item[1]
            if not _valid_mechanism_edge(edge, index):
                continue
            other_id = edge["target"] if edge["source"] == current_id else edge["source"]
            if other_id in node_ids:
                continue
            if not _is_mechanism_node(index.nodes_by_id.get(other_id)):
                continue
            queue.append(([*node_ids, other_id], [*edge_items, item]))
    return paths


def _select_diverse_paths(paths: list[dict[str, Any]], max_paths: int) -> list[dict[str, Any]]:
    remaining = sorted(
        paths,
        key=lambda path: (
            -float(path["base_score"]),
            path["length"],
            path["path_text"],
            path["path_id"],
        ),
    )
    selected: list[dict[str, Any]] = []
    used_edges: set[str] = set()
    used_nodes: set[str] = set()

    while remaining and len(selected) < max_paths:
        best_index = 0
        best_score = float("-inf")
        for index, path in enumerate(remaining):
            edge_overlap = len(set(path["edge_ids"]) & used_edges)
            node_overlap = len(set(path["node_ids"]) & used_nodes)
            adjusted = float(path["base_score"]) - 0.25 * edge_overlap - 0.04 * node_overlap
            if adjusted > best_score:
                best_score = adjusted
                best_index = index
        path = dict(remaining.pop(best_index))
        path["score"] = round(best_score, 4)
        selected.append(path)
        used_edges.update(path["edge_ids"])
        used_nodes.update(path["node_ids"])

    return selected


def _raw_edge_by_index(index: GraphIndex, edge_index: int) -> dict[str, Any]:
    for item_index, edge in index.edge_items:
        if item_index == edge_index:
            return edge
    raise RetrievalError(f"selected path references unknown edge index: {edge_index}")


def _edges_from_paths(
    subject: str,
    selected_paths: list[dict[str, Any]],
    target: dict[str, Any],
    index: GraphIndex,
    max_edges: int,
    fill_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_edge_id: dict[str, dict[str, Any]] = {}
    for path in selected_paths:
        for step in path["steps"]:
            edge_id = step["source_edge_id"]
            raw_index = int(edge_id.rsplit(":", 1)[1])
            edge = _raw_edge_by_index(index, raw_index)
            by_edge_id[edge_id] = _serialized_edge(
                subject,
                (raw_index, edge),
                index,
                score=_edge_score(edge, target, index),
            )
            if len(by_edge_id) >= max_edges:
                break
        if len(by_edge_id) >= max_edges:
            break
    for edge in fill_edges:
        by_edge_id.setdefault(edge["source_edge_id"], edge)
        if len(by_edge_id) >= max_edges:
            break
    return sorted(
        by_edge_id.values(),
        key=lambda edge: (
            -float(edge.get("score", 0.0)),
            RELATION_PRIORITY.get(edge["relation"], 99),
            edge["source_name"],
            edge["target_name"],
            edge["source_edge_id"],
        ),
    )


def _summary_entry(edge: dict[str, Any]) -> str:
    evidence = edge.get("evidence") or edge.get("relation_description") or ""
    if len(evidence) > 70:
        evidence = evidence[:67] + "..."
    return (
        f"{edge['source_name']} --{edge['relation']}--> {edge['target_name']}"
        + (f"；证据：{evidence}" if evidence else "")
    )


def _topic_summary(target: dict[str, Any], selected_edges: list[dict[str, Any]]) -> dict[str, Any]:
    properties = target.get("properties", {})
    summary: dict[str, Any] = {
        "definition_summary": {
            "name": target.get("name"),
            "definition": properties.get("definition", ""),
            "formula": properties.get("formula", ""),
            "importance": properties.get("importance", ""),
        },
        "condition_summary": [],
        "process_summary": [],
        "effect_summary": [],
    }
    seen_by_bucket = {key: set() for key in SUMMARY_BUCKETS}
    for edge in selected_edges:
        text = " ".join(
            str(value)
            for value in (
                edge.get("source_name"),
                edge.get("target_name"),
                edge.get("relation_description"),
                edge.get("evidence"),
            )
            if value
        )
        for bucket, keywords in SUMMARY_BUCKETS.items():
            if _contains_any(text, keywords):
                entry = _summary_entry(edge)
                if entry not in seen_by_bucket[bucket] and len(summary[bucket]) < 5:
                    summary[bucket].append(entry)
                    seen_by_bucket[bucket].add(entry)
    return summary


def _retrieve_path_pruned(
    graph: dict[str, Any],
    concept_query: str,
    subject: str,
    max_edges: int,
    max_hops: int,
    max_paths: int,
    include_topic_summary: bool,
    retrieval_mode: str,
) -> dict[str, Any]:
    target = resolve_concept(graph["nodes"], concept_query)
    index = build_graph_index(graph)
    ranked_ego, candidate_edge_count = _ranked_ego_edges(subject, target, index, max_edges)
    candidate_paths = _generate_candidate_paths(subject, target, index, max_hops)
    selected_paths = _select_diverse_paths(candidate_paths, max_paths)
    selected_edges = _edges_from_paths(
        subject, selected_paths, target, index, max_edges, ranked_ego
    )
    summary = _topic_summary(target, selected_edges) if include_topic_summary else {}
    return _assemble_subgraph(
        subject=subject,
        concept_query=concept_query,
        target=target,
        index=index,
        selected_edges=selected_edges,
        candidate_edge_count=candidate_edge_count,
        max_edges=max_edges,
        retrieval_mode=retrieval_mode,
        hop_count=max_hops,
        selected_paths=selected_paths,
        topic_summary=summary,
        extra_stats={
            "candidate_path_count": len(candidate_paths),
            "naive_2hop_context_chars": _json_chars(candidate_paths),
        },
    )


def _retrieve_dual_level(
    graph: dict[str, Any],
    concept_query: str,
    subject: str,
    max_edges: int,
) -> dict[str, Any]:
    target = resolve_concept(graph["nodes"], concept_query)
    index = build_graph_index(graph)
    selected_edges, candidate_edge_count = _ranked_ego_edges(
        subject, target, index, max_edges
    )
    return _assemble_subgraph(
        subject=subject,
        concept_query=concept_query,
        target=target,
        index=index,
        selected_edges=selected_edges,
        candidate_edge_count=candidate_edge_count,
        max_edges=max_edges,
        retrieval_mode="dual_level",
        hop_count=1,
        selected_paths=[],
        topic_summary=_topic_summary(target, selected_edges),
    )


def retrieve_subgraph(
    graph: dict[str, Any],
    concept_query: str,
    subject: str,
    retrieval_mode: str = "one_hop",
    max_edges: int = 12,
    max_hops: int = 2,
    max_paths: int = 5,
) -> dict[str, Any]:
    if retrieval_mode not in RETRIEVAL_MODES:
        supported = ", ".join(sorted(RETRIEVAL_MODES))
        raise RetrievalError(
            f"unsupported retrieval mode {retrieval_mode!r}; choose one of: {supported}"
        )
    if max_edges < 1:
        raise RetrievalError("max_edges must be at least 1")
    if max_hops < 1:
        raise RetrievalError("max_hops must be at least 1")
    if max_paths < 1:
        raise RetrievalError("max_paths must be at least 1")

    if retrieval_mode == "one_hop":
        return retrieve_one_hop(graph, concept_query, subject, max_edges=max_edges)
    if retrieval_mode == "dual_level":
        return _retrieve_dual_level(graph, concept_query, subject, max_edges=max_edges)
    if retrieval_mode == "path_pruned":
        return _retrieve_path_pruned(
            graph,
            concept_query,
            subject,
            max_edges=max_edges,
            max_hops=max_hops,
            max_paths=max_paths,
            include_topic_summary=False,
            retrieval_mode="path_pruned",
        )
    return _retrieve_path_pruned(
        graph,
        concept_query,
        subject,
        max_edges=max_edges,
        max_hops=max_hops,
        max_paths=max_paths,
        include_topic_summary=True,
        retrieval_mode="path_dual",
    )


def serialize_subgraph(subgraph: dict[str, Any]) -> str:
    target = subgraph["target"]
    properties = target.get("properties", {})
    lines = [
        f"目标概念：{target.get('name')} [{target.get('source_node_id')}]",
        f"检索模式：{subgraph.get('retrieval', {}).get('retrieval_mode', 'one_hop')}",
        f"定义：{properties.get('definition', '')}",
        f"公式：{properties.get('formula', '')}",
        "raw_edges（原始 KG 边证据）：",
    ]
    for edge in subgraph["edges"]:
        description = edge.get("relation_description") or ""
        evidence = edge.get("evidence") or ""
        score = f"; score={edge['score']}" if "score" in edge else ""
        lines.append(
            "- "
            f"[{edge['source_edge_id']}] "
            f"{edge['source_name']} --{edge['relation']}--> {edge['target_name']}; "
            f"关系说明：{description}; 教材证据：{evidence}{score}"
        )
    if subgraph.get("selected_paths"):
        lines.append("selected_paths（PathRAG 裁剪后的机制路径）：")
        for path in subgraph["selected_paths"]:
            lines.append(
                "- "
                f"[{path['path_id']}] score={path.get('score')}; "
                f"edges={','.join(path['edge_ids'])}; {path['path_text']}"
            )
    if subgraph.get("topic_summary"):
        lines.append("topic_summary（LightRAG 高层结构摘要，辅助背景，非原始事实来源）：")
        summary = subgraph["topic_summary"]
        definition = summary.get("definition_summary", {})
        lines.append(
            "- definition_summary: "
            f"{definition.get('definition', '')}; "
            f"公式：{definition.get('formula', '')}; "
            f"重要性：{definition.get('importance', '')}"
        )
        for key in ("condition_summary", "process_summary", "effect_summary"):
            values = summary.get(key, [])
            if values:
                lines.append(f"- {key}: " + " / ".join(values))
    return "\n".join(lines)
