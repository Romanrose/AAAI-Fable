from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from kg_rag.io import read_json, write_json
from kg_rag.models import GraphEdge, GraphNode
from kg_rag.text_cleaning import clean_value, count_text_issues


def _merge_property_lists(left: list[Any], right: list[Any]) -> list[Any]:
    merged: list[Any] = []
    for value in [*left, *right]:
        if value not in merged:
            merged.append(value)
    return merged


def _merge_properties(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if value in (None, "", [], {}):
            continue
        if key not in merged or merged[key] in (None, "", [], {}):
            merged[key] = value
            continue
        if isinstance(merged[key], list) and isinstance(value, list):
            merged[key] = _merge_property_lists(merged[key], value)
            continue
        if merged[key] != value:
            merged[f"subject_{key}"] = value
    return merged


def _build_retrieval_text(node: GraphNode) -> str:
    props = node.properties
    parts: list[str] = [node.name, node.label]
    for key in ("definition", "importance", "unit", "formula", "pages"):
        value = props.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    for key in ("aliases", "examples"):
        values = props.get(key, [])
        if isinstance(values, list):
            parts.extend(str(v).strip() for v in values if str(v).strip())
    return "\n".join(dict.fromkeys(parts))


def load_global_graph(nodes_path: Path, edges_path: Path) -> tuple[dict[str, GraphNode], list[GraphEdge]]:
    raw_nodes = read_json(nodes_path)
    raw_edges = read_json(edges_path)

    nodes = {
        item["id"]: GraphNode(
            id=item["id"],
            label=item["label"],
            name=item["name"],
            properties=item.get("properties", {}),
        )
        for item in raw_nodes
    }
    edges = [GraphEdge(source=item["source"], target=item["target"], type=item["type"]) for item in raw_edges]
    return nodes, edges


def enrich_with_subject_graphs(nodes: dict[str, GraphNode], subject_graph_dir: Path) -> dict[str, GraphNode]:
    for path in sorted(subject_graph_dir.glob("*.json")):
        payload = read_json(path)
        for item in payload.get("nodes", []):
            node_id = item["id"]
            if node_id not in nodes:
                nodes[node_id] = GraphNode(
                    id=node_id,
                    label=item["label"],
                    name=item["name"],
                    properties=item.get("properties", {}),
                )
                continue
            node = nodes[node_id]
            node.name = item.get("name", node.name)
            node.label = item.get("label", node.label)
            node.properties = _merge_properties(node.properties, item.get("properties", {}))
    return nodes


def build_normalized_payload(nodes: dict[str, GraphNode], edges: list[GraphEdge]) -> dict[str, Any]:
    label_counts = Counter(node.label for node in nodes.values())
    edge_counts = Counter(edge.type for edge in edges)
    issue_count_before = 0
    issue_count_after = 0

    normalized_nodes = []
    for node in sorted(nodes.values(), key=lambda item: item.id):
        issue_count_before += count_text_issues(
            {
                "name": node.name,
                "properties": node.properties,
            }
        )
        enriched = GraphNode(
            id=node.id,
            label=node.label,
            name=clean_value(node.name),
            properties=clean_value(dict(node.properties)),
        )
        enriched.properties["retrieval_text"] = _build_retrieval_text(enriched)
        issue_count_after += count_text_issues(
            {
                "name": enriched.name,
                "properties": enriched.properties,
            }
        )
        normalized_nodes.append(enriched.to_dict())

    normalized_edges = [edge.to_dict() for edge in sorted(edges, key=lambda item: (item.type, item.source, item.target))]

    return {
        "meta": {
            "node_count": len(normalized_nodes),
            "edge_count": len(normalized_edges),
            "node_labels": dict(sorted(label_counts.items())),
            "edge_types": dict(sorted(edge_counts.items())),
            "text_cleaning": {
                "mojibake_score_before": issue_count_before,
                "mojibake_score_after": issue_count_after,
            },
        },
        "nodes": normalized_nodes,
        "edges": normalized_edges,
    }


def normalize_k12_graph(
    *,
    nodes_path: Path,
    edges_path: Path,
    subject_graph_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    nodes, edges = load_global_graph(nodes_path, edges_path)
    enrich_with_subject_graphs(nodes, subject_graph_dir)
    payload = build_normalized_payload(nodes, edges)
    write_json(output_path, payload)
    return payload
