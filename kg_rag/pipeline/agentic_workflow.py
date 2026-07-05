from __future__ import annotations

from typing import Any

from kg_rag.retrievers.dual_level import retrieve_dual_level
from kg_rag.structure_mapping.analogy import build_analogy_plan
from kg_rag.structure_mapping.mechanism import build_mechanism_plan, validate_mechanism_plan


def _seed_from_card(card: dict[str, Any], retrieval_package: dict[str, Any]) -> dict[str, Any]:
    target = retrieval_package.get("target", {})
    props = target.get("properties", {}) if isinstance(target.get("properties"), dict) else {}
    return {
        "id": card["concept_id"],
        "label": "Concept",
        "name": card.get("canonical_name") or target.get("name"),
        "definition": card.get("definition") or props.get("definition"),
        "aliases": card.get("aliases", []),
        "examples": card.get("examples", []),
        "retrieval_text": "\n".join(
            item for item in [card.get("canonical_name"), card.get("definition")] if item
        ),
    }


def build_agentic_subgraph_pack(card: dict[str, Any], retrieval_package: dict[str, Any]) -> dict[str, Any]:
    context = card.get("graph_context", {})
    seed = _seed_from_card(card, retrieval_package)
    return {
        "query": card["concept_id"],
        "found": True,
        "seed": seed,
        "sections": {
            "prerequisites": context.get("prerequisites", []),
            "related_concepts": context.get("related_concepts", []),
            "outcomes": context.get("outcomes", []),
            "experiments": context.get("experiments", []),
            "exercises": context.get("exercises", []),
            "hierarchy": context.get("hierarchy", []),
        },
        "context_blocks": [
            {
                "title": "Dual-level GraphRAG raw edges",
                "text": "\n".join(
                    f"- [{edge.get('source_edge_id')}] {edge.get('source_name')} --{edge.get('relation')}--> {edge.get('target_name')}"
                    for edge in retrieval_package.get("raw_edges", [])
                ),
            },
            {
                "title": "Dual-level GraphRAG topic summary",
                "text": str(retrieval_package.get("topic_summary", {})),
            },
        ],
        "retrieval_package": retrieval_package,
        "meta": {
            "source": "agentic_dual_level",
            "story_language": card.get("story_language", "zh-CN"),
            **retrieval_package.get("retrieval_stats", {}),
        },
    }


def build_agentic_structure_plan(
    card: dict[str, Any],
    retrieval_package: dict[str, Any],
    mechanism_plan: dict[str, Any],
    analogy_plan: dict[str, Any],
) -> dict[str, Any]:
    seed = _seed_from_card(card, retrieval_package)
    return {
        "found": True,
        "query": card["concept_id"],
        "concept_id": card["concept_id"],
        "story_language": "zh-CN",
        "seed": seed,
        "retrieval_package": retrieval_package,
        "mechanism_plan": mechanism_plan,
        "analogy_plan": analogy_plan,
        "source_domain": analogy_plan.get("source_domain"),
        "entities": analogy_plan.get("entities", []),
        "characters": analogy_plan.get("characters", []),
        "event_chain": analogy_plan.get("event_chain", []),
        "conflict": analogy_plan.get("conflict"),
        "turning_point": analogy_plan.get("turning_point"),
        "resolution_state": analogy_plan.get("resolution_state"),
        "alignment_plan": analogy_plan.get("alignment_plan", []),
        "alignment_targets": analogy_plan.get("alignment_targets", []),
        "template_blacklist": analogy_plan.get("template_blacklist", []),
    }


def build_agentic_workflow_artifacts(
    *,
    card: dict[str, Any],
    normalized_graph: dict[str, Any],
    retrieval_mode: str = "dual_level",
    max_edges: int = 16,
    template_blacklist: str = "default",
) -> dict[str, Any]:
    if retrieval_mode != "dual_level":
        raise ValueError("The agentic workflow currently supports retrieval_mode='dual_level'.")

    retrieval_package = retrieve_dual_level(
        normalized_graph=normalized_graph,
        card=card,
        max_edges=max_edges,
    )
    mechanism_plan = build_mechanism_plan(card, retrieval_package)
    mechanism_errors = validate_mechanism_plan(mechanism_plan, retrieval_package)
    if mechanism_errors:
        raise ValueError("Invalid mechanism_plan: " + "; ".join(mechanism_errors))

    analogy_plan = build_analogy_plan(
        card,
        mechanism_plan,
        template_blacklist=template_blacklist,
    )
    structure_plan = build_agentic_structure_plan(
        card,
        retrieval_package,
        mechanism_plan,
        analogy_plan,
    )
    subgraph_pack = build_agentic_subgraph_pack(card, retrieval_package)
    return {
        "retrieval_package": retrieval_package,
        "mechanism_plan": mechanism_plan,
        "analogy_plan": analogy_plan,
        "structure_plan": structure_plan,
        "subgraph_pack": subgraph_pack,
    }

