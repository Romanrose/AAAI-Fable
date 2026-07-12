from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.io import write_json
from kg_rag.m2na_v2.mapping_reviews import latest_mapping_reviews
from kg_rag.m2na_v2.reviews import latest_reviews


PIPELINE_REPORT_VERSION = "aaai-pipeline-report/v1"


def build_pipeline_reports(
    *, preparation_root: Path, story_protocol_path: Path, output_root: Path | None = None
) -> dict[str, Any]:
    """Build the four ordered report sections from existing experiment artifacts."""
    from kg_rag.aaai_eval.reports import build_reports

    story_report = build_reports(protocol_path=story_protocol_path)
    mechanism = build_mechanism_report(preparation_root=preparation_root)
    mapping = build_mapping_report(preparation_root=preparation_root)
    ablation = build_ablation_design()
    report_root = output_root.resolve() if output_root else Path(story_report["main_csv"]).parent
    report_root.mkdir(parents=True, exist_ok=True)
    result = {
        "report_version": PIPELINE_REPORT_VERSION,
        "sections": [
            "mechanism_graph_quality",
            "structure_mapping_quality",
            "story_generation_quality",
            "ablation",
        ],
        "mechanism_graph_quality": mechanism,
        "structure_mapping_quality": mapping,
        "story_generation_quality": story_report,
        "ablation": ablation,
        "report_root": str(report_root.resolve()),
    }
    write_json(report_root / "pipeline_report.json", result)
    _write_json_rows(report_root / "table_1_mechanism_graph_quality.csv", mechanism["main_results"])
    _write_json_rows(report_root / "table_2_structure_mapping_quality.csv", mapping["main_results"])
    _write_json_rows(report_root / "table_3_story_generation_quality.csv", story_report["main_results"])
    _write_json_rows(report_root / "table_4_ablation_design.csv", ablation["variants"])
    (report_root / "pipeline_report.md").write_text(
        _pipeline_markdown(result), encoding="utf-8"
    )
    return {
        "report_version": PIPELINE_REPORT_VERSION,
        "report_root": str(report_root.resolve()),
        "mechanism_record_count": mechanism["record_count"],
        "mapping_record_count": mapping["record_count"],
        "story_record_count": story_report["record_count"],
        "ablation_status": ablation["status"],
        "tables": {
            "table_1": str((report_root / "table_1_mechanism_graph_quality.csv").resolve()),
            "table_2": str((report_root / "table_2_structure_mapping_quality.csv").resolve()),
            "table_3": str((report_root / "table_3_story_generation_quality.csv").resolve()),
            "table_4": str((report_root / "table_4_ablation_design.csv").resolve()),
            "manifest": str((report_root / "pipeline_report.json").resolve()),
        },
    }


def build_mechanism_report(*, preparation_root: Path) -> dict[str, Any]:
    seeds = read_jsonl(preparation_root / "seeds.jsonl")
    retrieval = _by_id(preparation_root / "retrieval_index.jsonl")
    validation = _by_id(preparation_root / "mechanism_validation.jsonl")
    reviews = latest_reviews(preparation_root / "mechanism_reviews.jsonl")
    mechanisms = _by_id(preparation_root / "mechanisms.raw.jsonl")
    rows = [
        _mechanism_row(seed, retrieval, validation, reviews, mechanisms)
        for seed in seeds
    ]
    return _section("mechanism_graph_quality", rows, "subject", "subject")


def build_mapping_report(*, preparation_root: Path) -> dict[str, Any]:
    root = preparation_root / "mapping_plans"
    index_path = root / "mapping_plan_index.jsonl"
    if not index_path.exists():
        return _section("structure_mapping_quality", [], "method_id", "subject")
    seeds = {str(row["concept_id"]): row for row in read_jsonl(preparation_root / "seeds.jsonl")}
    mechanisms = {
        str(row["concept_id"]): row
        for row in read_jsonl(preparation_root / "mechanisms.approved.jsonl")
    }
    reviews = latest_mapping_reviews(root / "mapping_reviews.jsonl")
    rows: list[dict[str, Any]] = []
    for item in read_jsonl(index_path):
        plan_path = Path(str(item.get("path") or ""))
        if not plan_path.exists():
            continue
        plan = _read_json(plan_path)
        concept_id = str(item.get("concept_id") or plan.get("concept_id") or "")
        seed = seeds.get(concept_id, {})
        mechanism = mechanisms.get(concept_id, {}).get("mechanism_graph", {})
        nodes = {str(node.get("id")) for node in mechanism.get("nodes", []) if isinstance(node, dict)}
        edges = {str(edge.get("id")) for edge in mechanism.get("edges", []) if isinstance(edge, dict)}
        mapped_nodes = {
            str(row.get("mechanism_node_id"))
            for row in plan.get("node_mappings", [])
            if isinstance(row, dict)
        }
        mapped_edges = {
            str(row.get("mechanism_edge_id"))
            for row in plan.get("edge_mappings", [])
            if isinstance(row, dict)
        }
        edge_rows = [row for row in plan.get("edge_mappings", []) if isinstance(row, dict)]
        review = reviews.get((concept_id, str(item.get("candidate_id")), str(item.get("strategy"))), {})
        rows.append(
            {
                "concept_id": concept_id,
                "subject": seed.get("subject", "unknown"),
                "method_id": str(item.get("strategy") or plan.get("strategy") or "unknown"),
                "candidate_id": str(item.get("candidate_id") or plan.get("candidate_id") or ""),
                "node_mapping_coverage": _ratio(len(mapped_nodes & nodes), len(nodes)),
                "edge_mapping_coverage": _ratio(len(mapped_edges & edges), len(edges)),
                "direction_preservation": _ratio(
                    sum(row.get("direction_preserved") is True for row in edge_rows),
                    len(edge_rows),
                ),
                "plan_valid": bool(nodes <= mapped_nodes and edges <= mapped_edges and all(
                    row.get("direction_preserved") is True for row in edge_rows
                )),
                "review_decision": review.get("decision", "pending"),
                "mapping_context_sha256": item.get("mapping_context_sha256", ""),
                "mapping_plan_sha256": item.get("mapping_plan_sha256", ""),
            }
        )
    _add_mapping_context_matches(rows)
    return _section("structure_mapping_quality", rows, "method_id", "subject")


def build_ablation_design() -> dict[str, Any]:
    variants = [
        {
            "variant_id": "full_m2na",
            "display_name": "Full M2NA",
            "graphrag": True,
            "mechanism_graph": True,
            "structure_mapping": True,
            "multi_agent": True,
            "status": "planned",
        },
        {
            "variant_id": "no_graphrag",
            "display_name": "No GraphRAG",
            "graphrag": False,
            "mechanism_graph": True,
            "structure_mapping": True,
            "multi_agent": True,
            "status": "planned",
        },
        {
            "variant_id": "no_mechanism_graph",
            "display_name": "No Explicit Mechanism Graph",
            "graphrag": True,
            "mechanism_graph": False,
            "structure_mapping": True,
            "multi_agent": True,
            "status": "planned",
        },
        {
            "variant_id": "direct_llm",
            "display_name": "Direct LLM Baseline",
            "graphrag": False,
            "mechanism_graph": False,
            "structure_mapping": False,
            "multi_agent": False,
            "status": "planned",
        },
    ]
    return {
        "section": "ablation",
        "status": "design_only",
        "control_requirements": {
            "same_dataset": True,
            "same_generator": True,
            "same_candidate_budget": True,
            "same_revision_budget": True,
            "one_factor_removed_at_a_time": True,
        },
        "variants": variants,
        "note": "No ablation result is reported until a frozen protocol has been run.",
    }


def _mechanism_row(
    seed: dict[str, Any],
    retrieval: dict[str, Any],
    validation: dict[str, Any],
    reviews: dict[str, dict[str, Any]],
    mechanisms: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    concept_id = str(seed["concept_id"])
    retrieval_row = retrieval.get(concept_id, {})
    validation_row = validation.get(concept_id, {})
    review = reviews.get(concept_id, {})
    mechanism = mechanisms.get(concept_id, {})
    graph = mechanism.get("mechanism_graph", {}) if isinstance(mechanism, dict) else {}
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    constraints = mechanism.get("generation_constraints", {}) if isinstance(mechanism, dict) else {}
    return {
        "concept_id": concept_id,
        "subject": seed.get("subject", "unknown"),
        "retrieval_success": bool(retrieval_row),
        "expanded_to_two_hop": bool(retrieval_row.get("expanded_to_two_hop")),
        "path_count": int(retrieval_row.get("path_count") or 0),
        "retrieval_edge_count": int(retrieval_row.get("edge_count") or 0),
        "validation_status": validation_row.get("status", "missing"),
        "validation_error_count": len(validation_row.get("errors", [])),
        "mechanism_node_count": len(nodes),
        "mechanism_edge_count": len(edges),
        "evidence_complete": bool(nodes or edges) and all(
            isinstance(item.get("evidence_refs"), list) and bool(item["evidence_refs"])
            for item in [*nodes, *edges]
        ),
        "must_preserve_node_count": len(constraints.get("must_preserve_node_ids", [])),
        "must_preserve_edge_count": len(constraints.get("must_preserve_edge_ids", [])),
        "review_decision": review.get("decision", "pending"),
        "reviewer": review.get("reviewer", ""),
    }


def _section(name: str, rows: list[dict[str, Any]], group_key: str, subject_key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(group_key, "unknown"))].append(row)
    main = [_aggregate_group("overall", rows)] if rows else []
    main.extend(_aggregate_group(key, subset) for key, subset in sorted(groups.items()))
    return {"section": name, "record_count": len(rows), "main_results": main, "rows": rows}


def _aggregate_group(group: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"group": group, "records": len(rows)}
    numeric_keys = sorted({key for row in rows for key, value in row.items() if isinstance(value, (int, float)) and not isinstance(value, bool)})
    for key in numeric_keys:
        result[key] = round(sum(float(row.get(key) or 0) for row in rows) / len(rows), 4)
    if any("validation_status" in row for row in rows):
        result["valid_rate"] = _ratio(
            sum(row.get("validation_status") == "valid" for row in rows), len(rows)
        )
    result["approved_rate"] = _ratio(
        sum(row.get("review_decision") == "approve" for row in rows), len(rows)
    )
    for source_key, output_key in (
        ("retrieval_success", "retrieval_success_rate"),
        ("expanded_to_two_hop", "two_hop_trigger_rate"),
        ("evidence_complete", "evidence_complete_rate"),
        ("mapping_context_match", "mapping_context_match_rate"),
    ):
        if any(source_key in row for row in rows):
            result[output_key] = _ratio(
                sum(row.get(source_key) is True for row in rows), len(rows)
            )
    if any("plan_valid" in row for row in rows):
        result["plan_valid_rate"] = _ratio(
            sum(row.get("plan_valid") is True for row in rows), len(rows)
        )
    return result


def _by_id(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row.get("concept_id")): row for row in read_jsonl(path)} if path.exists() else {}


def _read_json(path: Path) -> dict[str, Any]:
    import json

    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def _write_json_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _add_mapping_context_matches(rows: list[dict[str, Any]]) -> None:
    by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        value = str(row.get("mapping_context_sha256") or "")
        if value:
            by_pair[(str(row["concept_id"]), str(row["candidate_id"]))].add(value)
    for row in rows:
        hashes = by_pair[(str(row["concept_id"]), str(row["candidate_id"]))]
        row["mapping_context_match"] = len(hashes) == 1


def _pipeline_markdown(result: dict[str, Any]) -> str:
    lines = ["# M2NA Pipeline Evaluation", "", "Ordered sections:", "", "1. Mechanism graph quality", "2. Structure mapping quality", "3. Story generation quality", "4. Ablation", ""]
    ablation = result["ablation"]
    lines.extend([f"Ablation status: `{ablation['status']}`", ""])
    for section_name in ("mechanism_graph_quality", "structure_mapping_quality"):
        section = result[section_name]
        lines.extend([f"## {section_name}", "", f"Records: {section['record_count']}", ""])
    story = result["story_generation_quality"]
    lines.extend(["## story_generation_quality", "", f"Records: {story['record_count']}", ""])
    return "\n".join(lines)
