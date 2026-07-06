"""Retrieval and mechanism-plan analysis helpers for batch experiments."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from typing import Any

from .retrieval import NON_MECHANISM_LABELS


MECHANISM_KINDS = {"condition", "process", "effect"}


def _json_chars(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def classify_step_kind(text: str) -> str:
    condition_terms = ("条件", "原料", "前提", "先修", "必需", "不可缺少", "输入")
    effect_terms = ("产物", "应用", "影响", "结果", "释放", "支持", "平衡", "输出")
    if any(term in text for term in condition_terms):
        return "condition"
    if any(term in text for term in effect_terms):
        return "effect"
    return "process"


def retrieval_stats(subgraph: dict[str, Any]) -> dict[str, Any]:
    package = subgraph.get("retrieval_package", {})
    raw_edges = package.get("raw_edges", subgraph.get("edges", []))
    selected_paths = package.get("selected_paths", subgraph.get("selected_paths", []))
    topic_summary = package.get("topic_summary", subgraph.get("topic_summary", {}))
    path_lengths = [
        int(path.get("length", 0))
        for path in selected_paths
        if isinstance(path, dict) and int(path.get("length", 0)) > 0
    ]
    nodes = subgraph.get("nodes", [])
    non_mechanism_nodes = [
        node
        for node in nodes
        if isinstance(node, dict) and node.get("label") in NON_MECHANISM_LABELS
    ]
    raw_edge_chars = _json_chars(raw_edges)
    path_chars = _json_chars(selected_paths)
    summary_chars = _json_chars(topic_summary)
    stats = {
        "retrieval_mode": subgraph.get("retrieval", {}).get(
            "retrieval_mode", "one_hop"
        ),
        "retrieval_edge_count": len(raw_edges),
        "candidate_edge_count": subgraph.get("retrieval", {}).get(
            "candidate_edge_count", 0
        ),
        "retrieval_path_count": len(selected_paths),
        "avg_path_length": round(statistics.fmean(path_lengths), 4)
        if path_lengths
        else 0.0,
        "max_path_length": max(path_lengths) if path_lengths else 0,
        "retrieval_context_chars": raw_edge_chars + path_chars + summary_chars,
        "raw_edge_chars": raw_edge_chars,
        "path_chars": path_chars,
        "summary_chars": summary_chars,
        "non_mechanism_node_ratio": _ratio(len(non_mechanism_nodes), len(nodes)),
    }
    stats.update(package.get("retrieval_stats", {}))
    return stats


def build_heuristic_mechanism_plan(subgraph: dict[str, Any]) -> dict[str, Any]:
    package = subgraph.get("retrieval_package", {})
    target = package.get("target", subgraph.get("target", {}))
    raw_edges = package.get("raw_edges", subgraph.get("edges", []))
    selected_paths = package.get("selected_paths", subgraph.get("selected_paths", []))

    steps: list[dict[str, Any]] = []
    supporting_edge_ids: list[str] = []
    supporting_path_ids: list[str] = []

    if selected_paths:
        for index, path in enumerate(selected_paths[:5], start=1):
            text = str(path.get("path_text") or " -> ".join(path.get("node_names", [])))
            steps.append(
                {
                    "step_id": f"s{index}",
                    "text": text,
                    "kind": classify_step_kind(text),
                }
            )
            supporting_path_ids.append(str(path.get("path_id")))
            supporting_edge_ids.extend(str(edge_id) for edge_id in path.get("edge_ids", []))
    else:
        for index, edge in enumerate(raw_edges[:5], start=1):
            text = (
                f"{edge.get('source_name')} --{edge.get('relation')}--> "
                f"{edge.get('target_name')}"
            )
            steps.append(
                {
                    "step_id": f"s{index}",
                    "text": text,
                    "kind": classify_step_kind(text),
                }
            )
            supporting_edge_ids.append(str(edge.get("source_edge_id")))

    dependencies = [
        {
            "source_step_id": steps[index]["step_id"],
            "target_step_id": steps[index + 1]["step_id"],
            "relation": "next",
        }
        for index in range(max(0, len(steps) - 1))
    ]
    supporting_edge_ids = sorted({edge_id for edge_id in supporting_edge_ids if edge_id})
    supporting_path_ids = sorted({path_id for path_id in supporting_path_ids if path_id})
    forbidden_terms = [str(target.get("name", ""))]
    aliases = target.get("properties", {}).get("aliases", [])
    if isinstance(aliases, list):
        forbidden_terms.extend(str(alias) for alias in aliases if alias)

    return {
        "core_question": f"{target.get('name', '')}的关键条件、过程和结果是什么？",
        "steps": steps,
        "dependencies": dependencies,
        "supporting_edge_ids": supporting_edge_ids,
        "supporting_path_ids": supporting_path_ids,
        "forbidden_terms": sorted({term for term in forbidden_terms if term}),
        "coverage_targets": {
            "required_step_count": len(steps),
            "required_dependency_count": len(dependencies),
            "must_cover_path_ids": supporting_path_ids,
        },
    }


def validate_mechanism_plan(plan: Any, subgraph: dict[str, Any]) -> list[str]:
    if not isinstance(plan, dict):
        return ["mechanism_plan must be an object"]
    errors: list[str] = []
    raw_edge_ids = {
        edge["source_edge_id"]
        for edge in subgraph.get("retrieval_package", {}).get(
            "raw_edges", subgraph.get("edges", [])
        )
        if isinstance(edge, dict) and isinstance(edge.get("source_edge_id"), str)
    }
    selected_path_ids = {
        path["path_id"]
        for path in subgraph.get("retrieval_package", {}).get(
            "selected_paths", subgraph.get("selected_paths", [])
        )
        if isinstance(path, dict) and isinstance(path.get("path_id"), str)
    }

    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("mechanism_plan.steps must be a non-empty array")
        steps = []
    step_ids: set[str] = set()
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"mechanism_plan.steps[{index}] must be an object")
            continue
        step_id = step.get("step_id")
        if not isinstance(step_id, str) or not step_id.strip():
            errors.append(f"mechanism_plan.steps[{index}].step_id must be non-empty")
        elif step_id in step_ids:
            errors.append(f"duplicate mechanism_plan step_id: {step_id}")
        else:
            step_ids.add(step_id)
        if step.get("kind") not in MECHANISM_KINDS:
            errors.append(
                f"mechanism_plan.steps[{index}].kind must be one of "
                + ", ".join(sorted(MECHANISM_KINDS))
            )
        if not isinstance(step.get("text"), str) or not step["text"].strip():
            errors.append(f"mechanism_plan.steps[{index}].text must be non-empty")

    dependencies = plan.get("dependencies", [])
    if not isinstance(dependencies, list):
        errors.append("mechanism_plan.dependencies must be an array")
        dependencies = []
    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            errors.append(f"mechanism_plan.dependencies[{index}] must be an object")
            continue
        if dependency.get("source_step_id") not in step_ids:
            errors.append(
                f"mechanism_plan.dependencies[{index}].source_step_id is unknown"
            )
        if dependency.get("target_step_id") not in step_ids:
            errors.append(
                f"mechanism_plan.dependencies[{index}].target_step_id is unknown"
            )
        if not isinstance(dependency.get("relation"), str) or not dependency[
            "relation"
        ].strip():
            errors.append(f"mechanism_plan.dependencies[{index}].relation is required")

    supporting_edge_ids = plan.get("supporting_edge_ids", [])
    if not isinstance(supporting_edge_ids, list):
        errors.append("mechanism_plan.supporting_edge_ids must be an array")
        supporting_edge_ids = []
    unknown_edges = set(supporting_edge_ids) - raw_edge_ids
    if unknown_edges:
        errors.append(
            "mechanism_plan.supporting_edge_ids reference unavailable edges: "
            + ", ".join(sorted(unknown_edges))
        )

    supporting_path_ids = plan.get("supporting_path_ids", [])
    if not isinstance(supporting_path_ids, list):
        errors.append("mechanism_plan.supporting_path_ids must be an array")
        supporting_path_ids = []
    unknown_paths = set(supporting_path_ids) - selected_path_ids
    if unknown_paths:
        errors.append(
            "mechanism_plan.supporting_path_ids reference unavailable paths: "
            + ", ".join(sorted(unknown_paths))
        )

    coverage_targets = plan.get("coverage_targets")
    if not isinstance(coverage_targets, dict):
        errors.append("mechanism_plan.coverage_targets must be an object")
    else:
        must_cover = coverage_targets.get("must_cover_path_ids", [])
        if not isinstance(must_cover, list):
            errors.append(
                "mechanism_plan.coverage_targets.must_cover_path_ids must be an array"
            )
            must_cover = []
        if set(must_cover) - set(supporting_path_ids):
            errors.append(
                "coverage_targets.must_cover_path_ids must be a subset of "
                "supporting_path_ids"
            )
    return errors


def compute_retrieval_analysis(
    subgraph: dict[str, Any], mechanism_bundle: dict[str, Any] | None = None
) -> dict[str, Any]:
    stats = retrieval_stats(subgraph)
    package = subgraph.get("retrieval_package", {})
    raw_edges = package.get("raw_edges", subgraph.get("edges", []))
    selected_paths = package.get("selected_paths", subgraph.get("selected_paths", []))
    raw_edge_ids = {
        edge["source_edge_id"]
        for edge in raw_edges
        if isinstance(edge, dict) and isinstance(edge.get("source_edge_id"), str)
    }
    selected_path_ids = {
        path["path_id"]
        for path in selected_paths
        if isinstance(path, dict) and isinstance(path.get("path_id"), str)
    }
    mechanism_bundle = mechanism_bundle or {}
    plan = mechanism_bundle.get("mechanism_plan") or build_heuristic_mechanism_plan(
        subgraph
    )
    grounding = mechanism_bundle.get("grounding", {})
    plan_edge_ids = {
        edge_id
        for edge_id in plan.get("supporting_edge_ids", [])
        if isinstance(edge_id, str)
    }
    grounding_edge_ids = {
        edge_id
        for edge_id in grounding.get("source_edge_ids", [])
        if isinstance(edge_id, str)
    }
    used_edge_ids = (plan_edge_ids | grounding_edge_ids) & raw_edge_ids
    plan_path_ids = {
        path_id
        for path_id in plan.get("supporting_path_ids", [])
        if isinstance(path_id, str)
    }
    used_path_ids = plan_path_ids & selected_path_ids
    step_count = len(plan.get("steps", [])) if isinstance(plan.get("steps"), list) else 0

    analysis = dict(stats)
    analysis.update(
        {
            "unused_raw_edge_ratio": _ratio(
                len(raw_edge_ids - used_edge_ids), len(raw_edge_ids)
            ),
            "unused_selected_path_ratio": _ratio(
                len(selected_path_ids - used_path_ids), len(selected_path_ids)
            ),
            "grounding_edge_usage_rate": _ratio(len(used_edge_ids), len(raw_edge_ids)),
            "mechanism_compression_ratio": _ratio(
                step_count, int(stats.get("retrieval_edge_count", 0))
            ),
            "mechanism_step_count": step_count,
        }
    )
    return analysis


def mean_numeric(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for record in records:
        for key, value in record.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                grouped[key].append(float(value))
    return {
        key: round(statistics.fmean(values), 6) if values else None
        for key, values in sorted(grouped.items())
    }
