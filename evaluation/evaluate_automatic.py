#!/usr/bin/env python3
"""Deterministic automatic metrics for M2NA JSONL outputs."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_TEMPLATE_TERMS = [
    "智者",
    "村庄",
    "河流",
    "镜子",
    "钟表",
    "旅行者",
    "老人点醒",
]


def normalize(text: str) -> str:
    return "".join(str(text).casefold().split())


def contains_term(text: str, term: str) -> bool:
    normalized_term = normalize(term)
    return bool(normalized_term) and normalized_term in normalize(text)


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


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


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
            if not isinstance(value, list) or not all(
                _is_nonempty_string(item) for item in value
            ):
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

        node_alignments = output.get("node_alignments", [])
        if isinstance(node_alignments, list):
            for index, alignment in enumerate(node_alignments):
                if not isinstance(alignment, dict):
                    errors.append(f"node_alignment[{index}] must be an object")
                    continue
                for key in ("concept_node_id", "narrative_element", "evidence"):
                    if not _is_nonempty_string(alignment.get(key)):
                        errors.append(
                            f"node_alignment[{index}].{key} "
                            "must be a non-empty string"
                        )
                if "narrative_anchor" in alignment and not _is_nonempty_string(
                    alignment.get("narrative_anchor")
                ):
                    errors.append(
                        f"node_alignment[{index}].narrative_anchor "
                        "must be a non-empty string"
                    )

        edge_alignments = output.get("edge_alignments", [])
        if isinstance(edge_alignments, list):
            for index, alignment in enumerate(edge_alignments):
                if not isinstance(alignment, dict):
                    errors.append(f"edge_alignment[{index}] must be an object")
                    continue
                for key in (
                    "concept_edge_id",
                    "narrative_relation",
                    "evidence",
                    "narrative_source_concept_node_id",
                    "narrative_target_concept_node_id",
                ):
                    if not _is_nonempty_string(alignment.get(key)):
                        errors.append(
                            f"edge_alignment[{index}].{key} "
                            "must be a non-empty string"
                        )
                if "narrative_anchor" in alignment and not _is_nonempty_string(
                    alignment.get("narrative_anchor")
                ):
                    errors.append(
                        f"edge_alignment[{index}].narrative_anchor "
                        "must be a non-empty string"
                    )
                if (
                    "direction_preserved" in alignment
                    and not isinstance(alignment["direction_preserved"], bool)
                ):
                    errors.append(
                        f"edge_alignment[{index}].direction_preserved "
                        "must be a boolean"
                    )

    return errors


def _weighted_coverage(
    items: list[dict[str, Any]], covered_ids: set[str]
) -> float:
    if not items:
        return 1.0
    total = sum(float(item.get("weight", 1.0)) for item in items)
    covered = sum(
        float(item.get("weight", 1.0))
        for item in items
        if item.get("id") in covered_ids
    )
    return covered / total if total else 0.0


def evaluate_record(
    record: dict[str, Any], template_terms: Iterable[str] = DEFAULT_TEMPLATE_TERMS
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
                alignment.get("narrative_source_concept_node_id")
                == mechanism_edge["source"]
                and alignment.get("narrative_target_concept_node_id")
                == mechanism_edge["target"]
            )
        else:
            invalid_alignments += 1

    alignment_count = valid_alignments + invalid_alignments
    template_terms = list(template_terms)
    template_hits = sorted(
        {term for term in template_terms if contains_term(narrative, term)}
    )

    result.update(
        {
            "exact_concept_leakage": float(bool(exact_hits)),
            "soft_term_leakage": float(bool(soft_hits)),
            "exact_leakage_hits": exact_hits,
            "soft_leakage_hits": soft_hits,
            "node_coverage": len(valid_node_ids) / len(node_ids),
            "weighted_node_coverage": _weighted_coverage(
                graph["nodes"], valid_node_ids
            ),
            "edge_coverage": (
                len(valid_edge_ids) / len(edge_ids) if edge_ids else 1.0
            ),
            "weighted_edge_coverage": _weighted_coverage(
                graph["edges"], valid_edge_ids
            ),
            "alignment_precision": (
                valid_alignments / alignment_count if alignment_count else 0.0
            ),
            "alignment_hallucination_rate": (
                invalid_alignments / alignment_count if alignment_count else 0.0
            ),
            "relation_direction_accuracy": (
                sum(direction_values) / len(direction_values)
                if direction_values
                else None
            ),
            "template_hit_rate": (
                len(template_hits) / len(template_terms) if template_terms else 0.0
            ),
            "template_hits": template_hits,
            "narrative_char_count": len(narrative.strip()),
            "valid_node_alignment_count": len(valid_node_ids),
            "valid_edge_alignment_count": len(valid_edge_ids),
        }
    )
    return result


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            records.append(value)
    if not records:
        raise ValueError(f"{path}: no records found")
    return records


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
        "template_hit_rate",
        "narrative_char_count",
    ]
    summary: dict[str, Any] = {"sample_count": len(results)}
    for metric in metric_names:
        values = [
            float(result[metric])
            for result in results
            if result.get(metric) is not None
        ]
        summary[metric] = statistics.fmean(values) if values else None
    return summary


def group_by_method(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[str(result.get("method", "unknown"))].append(result)
    return {method: aggregate(items) for method, items in sorted(grouped.items())}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="M2NA JSONL predictions")
    parser.add_argument("--output", type=Path, help="write full JSON report")
    parser.add_argument(
        "--template-term",
        action="append",
        dest="template_terms",
        help="override default template terms; repeat for multiple terms",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        records = load_jsonl(args.input)
        template_terms = args.template_terms or DEFAULT_TEMPLATE_TERMS
        results = [evaluate_record(record, template_terms) for record in records]
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = {
        "input": str(args.input),
        "summary": aggregate(results),
        "by_method": group_by_method(results),
        "samples": results,
    }
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
