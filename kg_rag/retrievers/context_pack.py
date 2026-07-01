from __future__ import annotations

from collections import defaultdict
from typing import Any


def _node_summary(node: dict[str, Any]) -> dict[str, Any]:
    props = node.get("properties", {})
    return {
        "id": node["id"],
        "label": node.get("label"),
        "name": node.get("name"),
        "definition": props.get("definition"),
        "importance": props.get("importance"),
        "aliases": props.get("aliases", []),
        "examples": props.get("examples", []),
        "retrieval_text": props.get("retrieval_text"),
    }


def _edge_index(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        grouped[edge["type"]].append(edge)
    return grouped


def _connected_node_ids(seed_id: str, edges: list[dict[str, Any]], edge_type: str) -> list[str]:
    results: list[str] = []
    for edge in edges:
        if edge["type"] != edge_type:
            continue
        if edge["source"] == seed_id:
            results.append(edge["target"])
        elif edge["target"] == seed_id:
            results.append(edge["source"])
    seen: set[str] = set()
    ordered: list[str] = []
    for node_id in results:
        if node_id in seen:
            continue
        seen.add(node_id)
        ordered.append(node_id)
    return ordered


def build_subgraph_pack(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("found") or not payload.get("seed"):
        return {
            "query": payload.get("query"),
            "found": False,
            "seed": None,
            "sections": {},
            "context_blocks": [],
        }

    seed = payload["seed"]
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])

    if not nodes:
        nodes = [seed]

    node_map = {node["id"]: node for node in nodes}
    node_map.setdefault(seed["id"], seed)

    prereq_ids = _connected_node_ids(seed["id"], edges, "prerequisites_for")
    related_ids = _connected_node_ids(seed["id"], edges, "relates_to")
    leads_to_ids = _connected_node_ids(seed["id"], edges, "leads_to")
    experiment_ids = _connected_node_ids(seed["id"], edges, "verifies")
    exercise_ids = _connected_node_ids(seed["id"], edges, "tests_concept") + _connected_node_ids(
        seed["id"], edges, "tests_skill"
    )
    hierarchy_ids = _connected_node_ids(seed["id"], edges, "is_a") + _connected_node_ids(
        seed["id"], edges, "appears_in"
    ) + _connected_node_ids(seed["id"], edges, "is_part_of")

    def pick(node_ids: list[str]) -> list[dict[str, Any]]:
        return [_node_summary(node_map[node_id]) for node_id in node_ids if node_id in node_map]

    sections = {
        "prerequisites": pick(prereq_ids),
        "related_concepts": pick(related_ids),
        "outcomes": pick(leads_to_ids),
        "experiments": pick(experiment_ids),
        "exercises": pick(exercise_ids),
        "hierarchy": pick(hierarchy_ids),
    }

    seed_summary = _node_summary(seed)
    context_blocks = [
        {
            "title": "Target Concept",
            "text": "\n".join(
                part
                for part in [
                    f"Name: {seed_summary['name']}",
                    f"Label: {seed_summary['label']}",
                    f"Definition: {seed_summary['definition']}" if seed_summary["definition"] else None,
                    f"Importance: {seed_summary['importance']}" if seed_summary["importance"] else None,
                    (
                        f"Aliases: {', '.join(seed_summary['aliases'])}"
                        if seed_summary["aliases"]
                        else None
                    ),
                ]
                if part
            ),
        }
    ]

    for title, key in [
        ("Prerequisites", "prerequisites"),
        ("Related Concepts", "related_concepts"),
        ("Downstream Outcomes", "outcomes"),
        ("Experiments", "experiments"),
        ("Exercises", "exercises"),
        ("Hierarchy", "hierarchy"),
    ]:
        items = sections[key]
        if not items:
            continue
        lines = []
        for item in items:
            line = item["name"]
            if item.get("definition"):
                line = f"{line}: {item['definition']}"
            lines.append(line)
        context_blocks.append(
            {
                "title": title,
                "text": "\n".join(lines),
            }
        )

    return {
        "query": payload["query"],
        "found": True,
        "seed": seed_summary,
        "sections": sections,
        "context_blocks": context_blocks,
        "meta": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }
