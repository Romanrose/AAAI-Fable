from __future__ import annotations

import re
from typing import Any


MECHANISM_KINDS = {"condition", "process", "effect"}


def _unique_strings(values: list[Any]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.strip()
        if text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def _classify_kind(text: str, relation: str = "") -> str:
    if relation == "prerequisites_for":
        return "condition"
    if relation == "leads_to":
        return "effect"
    if re.search(r"条件|原料|前提|先修|必需|输入", text):
        return "condition"
    if re.search(r"产物|应用|影响|结果|释放|输出", text):
        return "effect"
    return "process"


def _edge_step_text(edge: dict[str, Any]) -> str:
    return f"{edge.get('source_name')} --{edge.get('relation')}--> {edge.get('target_name')}"


def build_mechanism_plan(card: dict[str, Any], retrieval_package: dict[str, Any]) -> dict[str, Any]:
    raw_edges = retrieval_package.get("raw_edges", [])
    target = retrieval_package.get("target", {})
    steps: list[dict[str, Any]] = []
    used_edge_ids: list[str] = []

    for edge in raw_edges:
        if not isinstance(edge, dict):
            continue
        edge_id = edge.get("source_edge_id")
        text = _edge_step_text(edge)
        if not isinstance(edge_id, str) or not edge_id:
            continue
        if any(step.get("text") == text for step in steps):
            continue
        steps.append(
            {
                "step_id": f"s{len(steps) + 1}",
                "text": text,
                "kind": _classify_kind(text, str(edge.get("relation", ""))),
                "supporting_edge_ids": [edge_id],
            }
        )
        used_edge_ids.append(edge_id)
        if len(steps) >= 6:
            break

    fallback_items = [
        *card.get("core_mechanism_zh", []),
        *card.get("must_preserve_zh", []),
        card.get("definition"),
    ]
    for item in fallback_items:
        if len(steps) >= 4:
            break
        if not isinstance(item, str) or not item.strip():
            continue
        text = item.strip()
        if any(step.get("text") == text for step in steps):
            continue
        steps.append(
            {
                "step_id": f"s{len(steps) + 1}",
                "text": text,
                "kind": _classify_kind(text),
                "supporting_edge_ids": [],
            }
        )

    if not steps:
        name = card.get("canonical_name") or target.get("name") or card.get("concept_id")
        steps.append(
            {
                "step_id": "s1",
                "text": f"围绕{name}识别条件、过程和结果。",
                "kind": "process",
                "supporting_edge_ids": [],
            }
        )

    dependencies = [
        {
            "source_step_id": steps[index]["step_id"],
            "target_step_id": steps[index + 1]["step_id"],
            "relation": "leads_to",
        }
        for index in range(max(0, len(steps) - 1))
    ]
    forbidden_terms = _unique_strings(
        [
            card.get("canonical_name"),
            card.get("concept_id"),
            *card.get("aliases", []),
            *card.get("forbidden_terms_zh", []),
        ]
    )
    supporting_edge_ids = _unique_strings(used_edge_ids)
    return {
        "core_question": f"{card.get('canonical_name') or card.get('concept_id')}的关键条件、过程和结果是什么？",
        "steps": steps,
        "dependencies": dependencies,
        "supporting_edge_ids": supporting_edge_ids,
        "supporting_path_ids": [],
        "forbidden_terms": forbidden_terms,
        "coverage_targets": {
            "required_step_count": len(steps),
            "required_dependency_count": len(dependencies),
            "must_cover_edge_ids": supporting_edge_ids,
            "must_cover_path_ids": [],
        },
    }


def validate_mechanism_plan(plan: dict[str, Any], retrieval_package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    raw_edge_ids = {
        edge.get("source_edge_id")
        for edge in retrieval_package.get("raw_edges", [])
        if isinstance(edge, dict)
    }
    steps = plan.get("steps", [])
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
            errors.append(f"mechanism_plan.steps[{index}].step_id is required")
        elif step_id in step_ids:
            errors.append(f"duplicate mechanism step_id: {step_id}")
        else:
            step_ids.add(step_id)
        if step.get("kind") not in MECHANISM_KINDS:
            errors.append(f"mechanism_plan.steps[{index}].kind is invalid")
        for edge_id in step.get("supporting_edge_ids", []):
            if edge_id not in raw_edge_ids:
                errors.append(f"mechanism_plan.steps[{index}] references unavailable edge: {edge_id}")

    for edge_id in plan.get("supporting_edge_ids", []):
        if edge_id not in raw_edge_ids:
            errors.append(f"mechanism_plan.supporting_edge_ids references unavailable edge: {edge_id}")
    return errors

