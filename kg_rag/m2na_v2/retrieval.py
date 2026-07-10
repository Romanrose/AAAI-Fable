from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from kg_rag.m2na_v2.schemas import MULTISTEP_CONCEPT_TYPES


CORE_RELATIONS = {
    "prerequisites_for",
    "is_a",
    "verifies",
    "leads_to",
    "relates_to",
}
SECOND_HOP_RELATIONS = {
    "prerequisites_for",
    "is_a",
    "verifies",
    "leads_to",
}
CURRICULUM_BRIDGE_RELATIONS = {"appears_in"}
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


def retrieve_adaptive_two_hop(
    *,
    normalized_graph: dict[str, Any],
    seed: dict[str, Any],
    max_edges: int = 20,
    max_paths: int = 8,
) -> dict[str, Any]:
    """Build a target-centered retrieval package with bounded adaptive expansion."""
    if max_edges < 1:
        raise ValueError("max_edges must be at least 1")
    if max_paths < 1:
        raise ValueError("max_paths must be at least 1")

    nodes = _node_map(normalized_graph)
    target = _resolve_target(nodes=nodes, seed=seed)
    edges = [edge for edge in normalized_graph.get("edges", []) if isinstance(edge, dict)]
    adjacency = _adjacency(edges)
    target_id = str(target["id"])

    direct = _rank_direct_edges(
        target_id=target_id,
        target=target,
        nodes=nodes,
        edges=edges,
        adjacency=adjacency,
    )
    direct = direct[:max_edges]
    sufficient, reasons = _has_sufficient_direct_structure(seed=seed, direct_edges=direct)
    selected_paths: list[dict[str, Any]] = []
    retrieval_decision: dict[str, Any] = {
        "strategy": "adaptive_two_hop",
        "direct_edge_count": len(direct),
        "direct_structure_sufficient": sufficient,
        "direct_structure_reasons": reasons,
        "expanded_to_two_hop": False,
        "expansion_reason": None,
        "expansion_mode": None,
    }

    combined = {edge["source_edge_id"]: edge for edge in direct}
    if not sufficient:
        semantic_paths = _semantic_two_hop_paths(
            target_id=target_id,
            target=target,
            nodes=nodes,
            edges=edges,
            adjacency=adjacency,
            direct_edges=direct,
        )
        if semantic_paths:
            selected_paths = semantic_paths[:max_paths]
            retrieval_decision.update(
                {
                    "expanded_to_two_hop": True,
                    "expansion_reason": "direct_structure_insufficient",
                    "expansion_mode": "semantic_relation_paths",
                }
            )
        elif not direct:
            selected_paths = _curriculum_bridge_paths(
                target_id=target_id,
                target=target,
                seed=seed,
                nodes=nodes,
                edges=edges,
                adjacency=adjacency,
                max_paths=max_paths,
            )
            if selected_paths:
                retrieval_decision.update(
                    {
                        "expanded_to_two_hop": True,
                        "expansion_reason": "no_core_direct_edges",
                        "expansion_mode": "curriculum_lexical_bridge",
                    }
                )

        for path in selected_paths:
            for edge in path["edges"]:
                combined.setdefault(edge["source_edge_id"], edge)

    ranked_edges = sorted(
        combined.values(),
        key=lambda edge: (
            -float(edge.get("score", 0.0)),
            int(edge.get("hop", 99)),
            RELATION_PRIORITY.get(str(edge.get("relation")), 99),
            str(edge.get("source_edge_id")),
        ),
    )[:max_edges]
    retained_ids = {edge["source_edge_id"] for edge in ranked_edges}
    selected_paths = [
        path
        for path in selected_paths
        if all(edge["source_edge_id"] in retained_ids for edge in path["edges"])
    ]
    retrieved_nodes = _retrieved_nodes(target_id=target_id, raw_edges=ranked_edges, nodes=nodes)
    topic_summary = _topic_summary(
        target=target,
        raw_edges=ranked_edges,
        selected_paths=selected_paths,
    )
    stats = {
        "retrieval_mode": "adaptive_two_hop",
        "retrieval_edge_count": len(ranked_edges),
        "candidate_edge_count": len(direct),
        "retrieval_path_count": len(selected_paths),
        "max_edges": max_edges,
        "max_paths": max_paths,
        "direct_edge_count": len(direct),
        "expanded_to_two_hop": retrieval_decision["expanded_to_two_hop"],
    }
    return {
        "target": _node_payload(target),
        "retrieved_nodes": retrieved_nodes,
        "raw_edges": ranked_edges,
        "selected_paths": selected_paths,
        "topic_summary": topic_summary,
        "retrieval_decision": retrieval_decision,
        "retrieval_stats": stats,
    }


def _node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(node["id"]): node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }


def _resolve_target(*, nodes: dict[str, dict[str, Any]], seed: dict[str, Any]) -> dict[str, Any]:
    concept_id = str(seed.get("concept_id") or "")
    node = nodes.get(concept_id)
    if node is not None:
        return node
    name = _normalize(seed.get("canonical_name"))
    matches = [
        item
        for item in nodes.values()
        if item.get("label") == "Concept" and _normalize(item.get("name")) == name
    ]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"Could not resolve ConceptSeed in normalized graph: {concept_id!r}")


def _adjacency(edges: list[dict[str, Any]]) -> dict[str, list[tuple[int, dict[str, Any]]]]:
    result: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, edge in enumerate(edges):
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        result[source].append((index, edge))
        result[target].append((index, edge))
    return result


def _rank_direct_edges(
    *,
    target_id: str,
    target: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    adjacency: dict[str, list[tuple[int, dict[str, Any]]]],
) -> list[dict[str, Any]]:
    candidates = [
        _serialize_edge(
            edge_index=index,
            edge=edge,
            nodes=nodes,
            target=target,
            hop=1,
            retrieval_role="core_direct",
            evidence_eligible=True,
        )
        for index, edge in adjacency.get(target_id, [])
        if edge.get("type") in CORE_RELATIONS
        and edge.get("source") in nodes
        and edge.get("target") in nodes
    ]
    return sorted(
        candidates,
        key=lambda edge: (
            -float(edge["score"]),
            RELATION_PRIORITY.get(str(edge["relation"]), 99),
            str(edge["source_edge_id"]),
        ),
    )


def _has_sufficient_direct_structure(*, seed: dict[str, Any], direct_edges: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    if not direct_edges:
        return False, ["no_core_direct_edges"]
    if str(seed.get("concept_type")) not in MULTISTEP_CONCEPT_TYPES:
        return True, ["single_direct_relation_is_sufficient_for_non_multistep_concept"]

    neighbor_ids = {
        edge["target"] if edge["source"] == seed.get("concept_id") else edge["source"]
        for edge in direct_edges
    }
    structural_count = sum(1 for edge in direct_edges if edge["relation"] in SECOND_HOP_RELATIONS)
    if len(direct_edges) < 2:
        return False, ["multistep_concept_has_fewer_than_two_direct_edges"]
    if len(neighbor_ids) < 2:
        return False, ["multistep_concept_has_fewer_than_two_direct_neighbors"]
    if not structural_count:
        return False, ["multistep_concept_has_no_high_value_direct_relation"]
    return True, ["multistep_direct_structure_is_sufficient"]


def _semantic_two_hop_paths(
    *,
    target_id: str,
    target: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    adjacency: dict[str, list[tuple[int, dict[str, Any]]]],
    direct_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for first in direct_edges:
        if first["relation"] not in SECOND_HOP_RELATIONS:
            continue
        intermediary_id = first["target"] if first["source"] == target_id else first["source"]
        for edge_index, edge in adjacency.get(intermediary_id, []):
            if edge.get("type") not in SECOND_HOP_RELATIONS:
                continue
            source = edge.get("source")
            target_node = edge.get("target")
            if source not in nodes or target_node not in nodes:
                continue
            endpoint_id = target_node if source == intermediary_id else source
            if endpoint_id == target_id or edge_index == _edge_index_from_id(first["source_edge_id"]):
                continue
            second = _serialize_edge(
                edge_index=edge_index,
                edge=edge,
                nodes=nodes,
                target=target,
                hop=2,
                retrieval_role="semantic_second_hop",
                evidence_eligible=True,
            )
            score = round(float(first["score"]) + 0.65 * float(second["score"]), 4)
            paths.append(
                _path_payload(
                    path_kind="semantic_relation_path",
                    target_id=target_id,
                    intermediary_id=intermediary_id,
                    endpoint_id=endpoint_id,
                    nodes=nodes,
                    edges=[first, second],
                    score=score,
                )
            )
    return _dedupe_and_rank_paths(paths)


def _curriculum_bridge_paths(
    *,
    target_id: str,
    target: dict[str, Any],
    seed: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    adjacency: dict[str, list[tuple[int, dict[str, Any]]]],
    max_paths: int,
) -> list[dict[str, Any]]:
    """Use a transparent non-mechanistic section bridge only for isolated concepts."""
    definition = str(seed.get("definition") or "")
    if not definition.strip():
        return []
    paths: list[dict[str, Any]] = []
    for bridge_index, bridge_edge in adjacency.get(target_id, []):
        if bridge_edge.get("type") not in CURRICULUM_BRIDGE_RELATIONS:
            continue
        bridge_id = bridge_edge["target"] if bridge_edge["source"] == target_id else bridge_edge["source"]
        bridge_node = nodes.get(bridge_id, {})
        if bridge_node.get("label") not in {"Section", "Chapter", "Book"}:
            continue
        first = _serialize_edge(
            edge_index=bridge_index,
            edge=bridge_edge,
            nodes=nodes,
            target=target,
            hop=1,
            retrieval_role="curriculum_bridge",
            evidence_eligible=False,
        )
        for peer_index, peer_edge in adjacency.get(bridge_id, []):
            if peer_edge.get("type") not in CURRICULUM_BRIDGE_RELATIONS or peer_index == bridge_index:
                continue
            peer_id = peer_edge["target"] if peer_edge["source"] == bridge_id else peer_edge["source"]
            peer = nodes.get(peer_id, {})
            if peer.get("label") != "Concept" or peer_id == target_id:
                continue
            lexical_match = _definition_mention(definition=definition, node=peer)
            if lexical_match is None:
                continue
            lexical_score, lexical_anchor = lexical_match
            second = _serialize_edge(
                edge_index=peer_index,
                edge=peer_edge,
                nodes=nodes,
                target=target,
                hop=2,
                retrieval_role="curriculum_peer",
                evidence_eligible=False,
            )
            paths.append(
                _path_payload(
                    path_kind="curriculum_lexical_bridge",
                    target_id=target_id,
                    intermediary_id=bridge_id,
                    endpoint_id=peer_id,
                    nodes=nodes,
                    edges=[first, second],
                    score=round(0.2 + lexical_score, 4),
                    lexical_anchor=lexical_anchor,
                )
            )
    return _dedupe_and_rank_paths(paths)[:max_paths]


def _definition_mention(*, definition: str, node: dict[str, Any]) -> tuple[float, str] | None:
    props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
    terms = _candidate_anchors(node.get("name"))
    for alias in props.get("aliases", []):
        terms.extend(_candidate_anchors(alias))
    matched = [term for term in terms if len(term.strip()) >= 2 and term in definition]
    if not matched:
        return None
    anchor = max(matched, key=len)
    return min(len(anchor) / 12.0, 1.0), anchor


def _candidate_anchors(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    results = [text]
    primary = re.split(r"[（(\[【]", text, maxsplit=1)[0].strip()
    if primary and primary != text:
        results.append(primary)
    return list(dict.fromkeys(results))


def _dedupe_and_rank_paths(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_edge_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        key = tuple(edge["source_edge_id"] for edge in path["edges"])
        previous = by_edge_pair.get(key)
        if previous is None or float(path["score"]) > float(previous["score"]):
            by_edge_pair[key] = path
    return sorted(
        by_edge_pair.values(),
        key=lambda path: (
            -float(path["score"]),
            path["path_kind"],
            tuple(edge["source_edge_id"] for edge in path["edges"]),
        ),
    )


def _path_payload(
    *,
    path_kind: str,
    target_id: str,
    intermediary_id: str,
    endpoint_id: str,
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    score: float,
    lexical_anchor: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "path_kind": path_kind,
        "hop_count": 2,
        "node_ids": [target_id, intermediary_id, endpoint_id],
        "node_names": [
            str(nodes[node_id].get("name") or node_id)
            for node_id in (target_id, intermediary_id, endpoint_id)
        ],
        "edges": edges,
        "score": score,
    }
    if lexical_anchor:
        payload["lexical_anchor"] = lexical_anchor
    return payload


def _serialize_edge(
    *,
    edge_index: int,
    edge: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    target: dict[str, Any],
    hop: int,
    retrieval_role: str,
    evidence_eligible: bool,
) -> dict[str, Any]:
    source = nodes[str(edge["source"])]
    target_node = nodes[str(edge["target"])]
    relation = str(edge.get("type") or "")
    return {
        "source_edge_id": f"normalized:edge:{edge_index}",
        "source": str(edge["source"]),
        "source_name": str(source.get("name") or edge["source"]),
        "target": str(edge["target"]),
        "target_name": str(target_node.get("name") or edge["target"]),
        "relation": relation,
        "relation_description": relation,
        "score": _edge_score(edge=edge, target=target, nodes=nodes),
        "hop": hop,
        "retrieval_role": retrieval_role,
        "evidence_eligible": evidence_eligible,
    }


def _edge_score(*, edge: dict[str, Any], target: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> float:
    relation = str(edge.get("type") or "")
    score = RELATION_WEIGHTS.get(relation, 0.2)
    source = nodes[str(edge["source"])]
    target_node = nodes[str(edge["target"])]
    if source.get("label") == "Concept" and target_node.get("label") == "Concept":
        score += 0.15
    target_name = _normalize(target.get("name"))
    endpoint_text = _normalize(f"{_node_text(source)} {_node_text(target_node)}")
    if target_name and target_name in endpoint_text:
        score += 0.2
    return round(score, 4)


def _retrieved_nodes(
    *,
    target_id: str,
    raw_edges: list[dict[str, Any]],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    ids = {
        node_id
        for edge in raw_edges
        for node_id in (edge.get("source"), edge.get("target"))
        if isinstance(node_id, str) and node_id != target_id
    }
    return [_node_payload(nodes[node_id]) for node_id in sorted(ids) if node_id in nodes]


def _topic_summary(
    *,
    target: dict[str, Any],
    raw_edges: list[dict[str, Any]],
    selected_paths: list[dict[str, Any]],
) -> dict[str, Any]:
    props = target.get("properties", {}) if isinstance(target.get("properties"), dict) else {}
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
        "curriculum_context_summary": [],
    }
    for edge in raw_edges:
        relation = edge["relation"]
        if relation == "prerequisites_for":
            bucket = "condition_summary"
        elif relation == "leads_to":
            bucket = "effect_summary"
        elif edge.get("retrieval_role") == "curriculum_bridge" or edge.get("retrieval_role") == "curriculum_peer":
            bucket = "curriculum_context_summary"
        else:
            bucket = "process_summary"
        entry = f"[{edge['source_edge_id']}] {edge['source_name']} --{relation}--> {edge['target_name']}"
        if entry not in summary[bucket] and len(summary[bucket]) < 5:
            summary[bucket].append(entry)
    for path in selected_paths:
        if path["path_kind"] != "curriculum_lexical_bridge":
            continue
        entry = (
            f"{path['node_names'][0]} --课程章节--> {path['node_names'][2]}"
            f"（定义显式提及：{path.get('lexical_anchor', '')}）"
        )
        if entry not in summary["curriculum_context_summary"] and len(summary["curriculum_context_summary"]) < 5:
            summary["curriculum_context_summary"].append(entry)
    return summary


def _node_payload(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_node_id": str(node["id"]),
        "label": node.get("label"),
        "name": node.get("name"),
        "properties": node.get("properties", {}) if isinstance(node.get("properties"), dict) else {},
    }


def _edge_index_from_id(source_edge_id: str) -> int:
    return int(source_edge_id.rsplit(":", 1)[1])


def _node_text(node: dict[str, Any]) -> str:
    props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
    values = [node.get("name"), props.get("definition"), props.get("formula"), props.get("importance")]
    for key in ("aliases", "examples"):
        value = props.get(key, [])
        if isinstance(value, list):
            values.extend(value)
    return " ".join(str(value) for value in values if value)


def _normalize(value: Any) -> str:
    return "".join(str(value or "").casefold().split())
