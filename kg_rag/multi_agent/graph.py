from __future__ import annotations

from typing import Any

from kg_rag.retrievers.dual_level import retrieve_dual_level

from kg_rag.multi_agent.text import clean_value, unique_strings

RELATION_SEMANTIC_ROLES = {
    "prerequisites_for": "prerequisite",
    "is_a": "category_membership",
    "verifies": "evidence_verification",
    "leads_to": "causal_or_supportive_outcome",
    "relates_to": "association",
}


def retrieve_context(
    *,
    card: dict[str, Any],
    normalized_graph: dict[str, Any],
    max_edges: int = 16,
) -> dict[str, Any]:
    return clean_value(
        retrieve_dual_level(
            normalized_graph=normalized_graph,
            card=card,
            max_edges=max_edges,
        )
    )


def _node_source(index: int, core_count: int, preserve_count: int) -> str:
    if index < core_count:
        return "core_mechanism_zh"
    if index < core_count + preserve_count:
        return "must_preserve_zh"
    return "definition"


def build_mechanism_graph(
    *,
    card: dict[str, Any],
    retrieval_package: dict[str, Any],
    max_nodes: int = 6,
) -> dict[str, Any]:
    core_items = [item for item in card.get("core_mechanism_zh", []) if isinstance(item, str)]
    preserve_items = [item for item in card.get("must_preserve_zh", []) if isinstance(item, str)]
    fallback_items = [card.get("definition")]
    raw_edges = retrieval_package.get("raw_edges", [])
    retrieval_items = _mechanism_items_from_retrieval_edges(
        raw_edges=raw_edges,
        target_name=str(card.get("canonical_name") or ""),
    )
    items = unique_strings([*core_items, *preserve_items, *fallback_items])[:max_nodes]
    if len(items) < 2:
        items = unique_strings([*items, *retrieval_items])[:max_nodes]

    if not items:
        name = card.get("canonical_name") or card.get("concept_id") or "目标概念"
        items = [f"识别{name}的关键条件、过程和结果"]

    nodes = []
    core_count = len(unique_strings(core_items))
    preserve_count = len(unique_strings(preserve_items))
    for index, text in enumerate(items):
        nodes.append(
            {
                "id": f"n{index + 1}",
                "text": text,
                "weight": 1.0 if index < core_count else 0.85,
                "source": _node_source(index, core_count, preserve_count),
            }
        )

    edges = []
    for index in range(max(0, len(nodes) - 1)):
        edges.append(
            {
                "id": f"e{index + 1}",
                "source": nodes[index]["id"],
                "target": nodes[index + 1]["id"],
                "relation": "leads_to",
                "weight": 1.0,
                "relation_semantic_role": "mechanism_sequence",
                "source_kind": "concept_card_mechanism",
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "source": "concept_card+dual_level_graphrag",
        "edge_semantics": "ordered concept-card mechanism steps; external KG relations are stored separately",
        "retrieval_edge_ids": [
            edge.get("source_edge_id")
            for edge in raw_edges
            if isinstance(edge, dict) and edge.get("source_edge_id")
        ],
    }


def build_concept_relation_graph(
    *,
    card: dict[str, Any],
    retrieval_package: dict[str, Any],
) -> dict[str, Any]:
    target = retrieval_package.get("target", {})
    target_id = str(target.get("source_node_id") or card.get("concept_id") or "")
    target_name = str(target.get("name") or card.get("canonical_name") or target_id)
    relations: list[dict[str, Any]] = []
    neighbors: dict[str, dict[str, Any]] = {}
    for edge in retrieval_package.get("raw_edges", []):
        if not isinstance(edge, dict):
            continue
        relation = str(edge.get("relation") or "")
        source_id = str(edge.get("source") or "")
        target_edge_id = str(edge.get("target") or "")
        source_name = str(edge.get("source_name") or source_id)
        target_edge_name = str(edge.get("target_name") or target_edge_id)
        if source_id == target_id:
            direction = "outgoing"
            neighbor_id = target_edge_id
            neighbor_name = target_edge_name
        elif target_edge_id == target_id:
            direction = "incoming"
            neighbor_id = source_id
            neighbor_name = source_name
        else:
            direction = "undirected"
            neighbor_id = target_edge_id or source_id
            neighbor_name = target_edge_name or source_name
        if neighbor_id:
            neighbors[neighbor_id] = {
                "id": neighbor_id,
                "name": neighbor_name,
            }
        relations.append(
            {
                "edge_id": edge.get("source_edge_id"),
                "source_id": source_id,
                "source_name": source_name,
                "target_id": target_edge_id,
                "target_name": target_edge_name,
                "relation": relation,
                "relation_semantic_role": RELATION_SEMANTIC_ROLES.get(
                    relation, "association"
                ),
                "direction": direction,
                "neighbor_id": neighbor_id,
                "neighbor_name": neighbor_name,
                "score": edge.get("score"),
                "evidence": edge.get("evidence", ""),
            }
        )
    return {
        "target_concept": {
            "id": target_id,
            "name": target_name,
            "label": target.get("label") or "Concept",
            "definition": target.get("properties", {}).get("definition")
            if isinstance(target.get("properties"), dict)
            else card.get("definition", ""),
        },
        "neighbors": list(neighbors.values()),
        "relations": relations,
        "raw_edge_count": len(relations),
        "source": "dual_level_graphrag",
    }


def _mechanism_items_from_retrieval_edges(
    *,
    raw_edges: list[Any],
    target_name: str,
) -> list[str]:
    items: list[str] = []
    for edge in raw_edges:
        if not isinstance(edge, dict):
            continue
        source_name = str(edge.get("source_name") or "").strip()
        target = str(edge.get("target_name") or "").strip()
        relation = str(edge.get("relation") or "").strip()
        if not source_name or not target:
            continue
        if relation == "prerequisites_for":
            other = source_name if target == target_name else target
            items.append(f"需要先满足或理解：{other}")
        elif relation == "leads_to":
            other = target if source_name == target_name else source_name
            items.append(f"会进一步导致或支持：{other}")
        elif relation == "is_a":
            other = target if source_name == target_name else source_name
            items.append(f"属于或连接到上位结构：{other}")
        elif relation == "verifies":
            other = target if source_name == target_name else source_name
            items.append(f"可以通过相关证据或实验验证：{other}")
        else:
            items.append(f"与相关概念保持关系：{source_name} 与 {target}")
    return items
