from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.concepts.quality import clean_text, context_quality, generation_priority, text_quality
from kg_rag.io import read_json, write_json


SUBJECT_CONSTRAINTS_ZH = {
    "biology": [
        "\u907f\u514d\u76ee\u7684\u8bba\u89e3\u91ca\u3002",
        "\u907f\u514d\u628a\u4e2a\u4f53\u52aa\u529b\u5199\u6210\u8fdb\u5316\u539f\u56e0\u3002",
        "\u4fdd\u7559\u751f\u547d\u7cfb\u7edf\u7684\u6761\u4ef6\u3001\u8fc7\u7a0b\u548c\u7ed3\u679c\u3002",
    ],
    "chemistry": [
        "\u533a\u5206\u5316\u5b66\u53cd\u5e94\u548c\u7269\u7406\u6df7\u5408\u3002",
        "\u4fdd\u7559\u5b88\u6052\u5173\u7cfb\u548c\u53cd\u5e94\u524d\u540e\u53d8\u5316\u3002",
        "\u907f\u514d\u5316\u5b66\u5f0f\u6216\u5143\u7d20\u7b26\u53f7\u5728\u6545\u4e8b\u6b63\u6587\u4e2d\u6cc4\u9732\u3002",
    ],
    "physics": [
        "\u4fdd\u7559\u53d8\u91cf\u4e4b\u95f4\u7684\u5173\u7cfb\u3002",
        "\u907f\u514d\u628a\u81ea\u7136\u89c4\u5f8b\u5199\u6210\u89d2\u8272\u4e3b\u89c2\u610f\u5fd7\u3002",
        "\u4fdd\u7559\u65b9\u5411\u3001\u5927\u5c0f\u3001\u6761\u4ef6\u53d8\u5316\u3002",
    ],
    "math": [
        "\u4fdd\u7559\u5f62\u5f0f\u5b9a\u4e49\u6761\u4ef6\u548c\u89c4\u5219\u4e00\u81f4\u6027\u3002",
        "\u907f\u514d\u53ea\u6709\u6545\u4e8b\u6ca1\u6709\u6570\u5b66\u7ed3\u6784\u3002",
        "\u907f\u514d\u628a\u6570\u5b66\u6982\u5ff5\u9053\u5fb7\u5316\u3002",
    ],
}


def _node_summary(node: dict[str, Any]) -> dict[str, Any]:
    props = node.get("properties", {})
    return {
        "id": node["id"],
        "label": node.get("label"),
        "name": clean_text(node.get("name")),
        "definition": clean_text(props.get("definition")),
    }


def _graph_indexes(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    node_map = {node["id"]: node for node in graph["nodes"]}
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph["edges"]:
        adjacency[edge["source"]].append(edge)
        adjacency[edge["target"]].append(edge)
    return node_map, adjacency


def _neighbors(
    *,
    node_id: str,
    edge_types: set[str],
    node_map: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    labels: set[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for edge in adjacency.get(node_id, []):
        if edge["type"] not in edge_types:
            continue
        other_id = edge["target"] if edge["source"] == node_id else edge["source"]
        if other_id in seen or other_id not in node_map:
            continue
        other = node_map[other_id]
        if labels and other.get("label") not in labels:
            continue
        seen.add(other_id)
        results.append(_node_summary(other))
        if len(results) >= limit:
            break
    return results


def infer_concept_type(subject: str, name: str, definition: str) -> str:
    text = f"{name}\n{definition}"
    if subject == "math":
        for token in ("\u5b9a\u7406", "\u6027\u8d28", "\u516c\u5f0f", "\u6cd5\u5219"):
            if token in text:
                return "theorem"
        for token in ("\u8ba1\u7b97", "\u8fd0\u7b97", "\u65b9\u6cd5", "\u89e3\u6cd5"):
            if token in text:
                return "method"
        return "relation"
    if subject == "chemistry":
        for token in ("\u53cd\u5e94", "\u6c27\u5316", "\u8fd8\u539f", "\u4e2d\u548c"):
            if token in text:
                return "process"
        for token in ("\u7269\u8d28", "\u5143\u7d20", "\u5206\u5b50", "\u539f\u5b50", "\u79bb\u5b50"):
            if token in text:
                return "entity"
        return "mechanism"
    if subject == "physics":
        for token in ("\u5b9a\u5f8b", "\u539f\u7406", "\u5173\u7cfb"):
            if token in text:
                return "law"
        return "mechanism"
    if subject == "biology":
        for token in ("\u8fc7\u7a0b", "\u4f5c\u7528", "\u5faa\u73af", "\u8c03\u8282"):
            if token in text:
                return "process"
        return "definition"
    return "definition"


def build_concept_cards(
    *,
    selection_path: Path,
    normalized_graph_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    selection_rows = read_jsonl(selection_path)
    graph = read_json(normalized_graph_path)
    node_map, adjacency = _graph_indexes(graph)
    cards: list[dict[str, Any]] = []

    for row in selection_rows:
        concept_id = row["concept_id"]
        node = node_map[concept_id]
        props = node.get("properties", {})
        subject = row["subject"]
        name = clean_text(node.get("name"))
        definition = clean_text(props.get("definition"))
        aliases = [clean_text(item) for item in props.get("aliases", []) if clean_text(item)]
        examples = [clean_text(item) for item in props.get("examples", []) if clean_text(item)]
        quality = text_quality(name=name, definition=definition)
        degree = len(adjacency.get(concept_id, []))
        priority = generation_priority(quality=quality, has_definition=bool(definition), degree=degree)
        forbidden_terms = list(dict.fromkeys([name, *aliases]))
        graph_context = {
            "prerequisites": _neighbors(
                node_id=concept_id,
                edge_types={"prerequisites_for"},
                node_map=node_map,
                adjacency=adjacency,
                labels={"Concept"},
            ),
            "related_concepts": _neighbors(
                node_id=concept_id,
                edge_types={"relates_to", "is_a"},
                node_map=node_map,
                adjacency=adjacency,
                labels={"Concept"},
            ),
            "outcomes": _neighbors(
                node_id=concept_id,
                edge_types={"leads_to"},
                node_map=node_map,
                adjacency=adjacency,
                labels={"Concept"},
            ),
            "experiments": _neighbors(
                node_id=concept_id,
                edge_types={"verifies"},
                node_map=node_map,
                adjacency=adjacency,
                labels={"Experiment"},
            ),
            "exercises": _neighbors(
                node_id=concept_id,
                edge_types={"tests_concept", "tests_skill"},
                node_map=node_map,
                adjacency=adjacency,
                labels={"Exercise", "Skill"},
            ),
            "hierarchy": _neighbors(
                node_id=concept_id,
                edge_types={"appears_in", "is_part_of"},
                node_map=node_map,
                adjacency=adjacency,
                labels={"Section", "Chapter", "Book"},
            ),
        }
        needs_enrichment = priority in {"silver", "bronze", "repair"} or not definition
        cards.append(
            {
                "concept_id": concept_id,
                "subject": subject,
                "story_language": "zh-CN",
                "canonical_name": name,
                "definition": definition,
                "aliases": aliases,
                "examples": examples,
                "teaching_level": "middle_school",
                "concept_type": infer_concept_type(subject, name, definition),
                "graph_context": graph_context,
                "core_mechanism_zh": [],
                "must_preserve_zh": [],
                "common_misconceptions_zh": [],
                "forbidden_terms_zh": forbidden_terms,
                "subject_constraints_zh": SUBJECT_CONSTRAINTS_ZH.get(subject, []),
                "generation_notes_zh": [],
                "data_quality": {
                    "text_quality": quality,
                    "context_quality": context_quality(degree),
                    "needs_llm_enrichment": needs_enrichment,
                    "generation_priority": priority,
                },
            }
        )

    write_jsonl(output_path, cards)
    summary = {
        "output_path": str(output_path),
        "concept_card_count": len(cards),
    }
    write_json(output_path.with_suffix(".summary.json"), summary)
    return summary

