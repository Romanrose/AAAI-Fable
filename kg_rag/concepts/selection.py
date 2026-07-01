from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.concepts.quality import clean_text, context_quality, generation_priority, subject_from_id, text_quality
from kg_rag.io import read_json, write_json


def _parse_subjects(subjects: str | list[str] | None) -> set[str]:
    if subjects is None:
        return {"biology", "chemistry", "math", "physics"}
    if isinstance(subjects, str):
        return {item.strip() for item in subjects.split(",") if item.strip()}
    return {item.strip() for item in subjects if item.strip()}


def _degree_index(edges: list[dict[str, Any]]) -> tuple[Counter[str], dict[str, set[str]]]:
    degree: Counter[str] = Counter()
    edge_types: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        edge_type = edge["type"]
        degree[source] += 1
        degree[target] += 1
        edge_types[source].add(edge_type)
        edge_types[target].add(edge_type)
    return degree, edge_types


def select_concept_nodes(
    *,
    normalized_graph_path: Path,
    output_path: Path,
    subjects: str | list[str] | None = None,
    limit_per_subject: int | None = None,
) -> dict[str, Any]:
    graph = read_json(normalized_graph_path)
    selected_subjects = _parse_subjects(subjects)
    degree, edge_types = _degree_index(graph["edges"])
    per_subject_count: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for node in graph["nodes"]:
        if node.get("label") != "Concept":
            continue
        subject = subject_from_id(str(node["id"]))
        if subject not in selected_subjects:
            continue
        if limit_per_subject is not None and per_subject_count[subject] >= limit_per_subject:
            continue

        props = node.get("properties", {})
        name = clean_text(node.get("name"))
        definition = clean_text(props.get("definition"))
        quality = text_quality(name=name, definition=definition)
        deg = int(degree[node["id"]])
        priority = generation_priority(quality=quality, has_definition=bool(definition), degree=deg)
        rows.append(
            {
                "concept_id": node["id"],
                "subject": subject,
                "name": name,
                "definition": definition,
                "degree": deg,
                "edge_types": sorted(edge_types[node["id"]]),
                "has_definition": bool(definition),
                "text_quality": quality,
                "context_quality": context_quality(deg),
                "generation_priority": priority,
                "recommended_action": "repair" if priority == "repair" else "generate",
                "story_language": "zh-CN",
            }
        )
        per_subject_count[subject] += 1

    write_jsonl(output_path, rows)
    summary = {
        "output_path": str(output_path),
        "concept_count": len(rows),
        "subjects": dict(sorted(Counter(row["subject"] for row in rows).items())),
        "priorities": dict(sorted(Counter(row["generation_priority"] for row in rows).items())),
    }
    write_json(output_path.with_suffix(".summary.json"), summary)
    return summary

