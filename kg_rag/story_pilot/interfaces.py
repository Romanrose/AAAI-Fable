from __future__ import annotations

import json
from typing import Any

from kg_rag.m2na_v2.schemas import stable_hash
from kg_rag.multi_agent.llm import ChatLLM, ensure_object, extract_json


GENERATOR_VERSION = "frozen-mapping-generator/v1"
ALIGNER_VERSION = "evidence-aligner/v1"
JUDGE_VERSION = "mapping-aware-judge/v2"
REVISER_VERSION = "frozen-mapping-reviser/v2"


def generate_story(
    *,
    llm: ChatLLM,
    mapping_plan: dict[str, Any],
    forbidden_terms: list[str],
) -> tuple[str, dict[str, Any]]:
    prompt = {
        "task": "TASK:STORY_PILOT_GENERATOR",
        "requirements": [
            "Write only one Simplified Chinese fable body, without title, explanation, markdown, or JSON.",
            "Use 450-750 Chinese characters.",
            "Realize the frozen mapping plan without changing source domain, node mappings, edge mappings, or edge directions.",
            "Make the conflict, event chain, turning point, and resolution concrete and causally connected.",
            "Do not mention target concepts, aliases, textbook terms, formulas, or the mapping process.",
            "Avoid generic moralizing and repeated sentence templates.",
        ],
        "forbidden_terms": forbidden_terms,
        "frozen_mapping_plan": mapping_plan,
    }
    system = "You write natural Chinese fables from a frozen structural analogy plan. Do not remap the structure."
    story = llm.complete(
        system_prompt=system,
        user_prompt=json.dumps(prompt, ensure_ascii=False, indent=2),
        max_tokens=1800,
        temperature=0.7,
    ).strip()
    return _strip_fences(story), _trace(GENERATOR_VERSION, system, prompt)


def align_story(
    *,
    llm: ChatLLM,
    mechanism_graph: dict[str, Any],
    mapping_plan: dict[str, Any],
    story: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = {
        "node_alignments": [
            {"mechanism_node_id": "n1", "story_evidence": "exact substring or empty", "confidence": 0.0}
        ],
        "edge_alignments": [
            {
                "mechanism_edge_id": "e1",
                "story_evidence": "exact substring or empty",
                "direction_preserved": True,
                "confidence": 0.0,
            }
        ],
        "missing_node_ids": [],
        "missing_edge_ids": [],
        "summary": "...",
    }
    prompt = {
        "task": "TASK:STORY_PILOT_ALIGNER",
        "requirements": [
            "Return strict JSON only.",
            "Return exactly one alignment row for every mechanism node and every mechanism edge.",
            "story_evidence must be an exact contiguous substring copied from the story, or an empty string when absent.",
            "Do not infer evidence that is not stated or enacted in the story.",
            "For edges, verify the relation and its direction, not merely whether both endpoints appear.",
        ],
        "mechanism_graph": mechanism_graph,
        "frozen_mapping_plan": mapping_plan,
        "story": story,
        "output_schema": schema,
    }
    system = "You are a conservative mechanism-to-story evidence aligner. Return strict JSON only."
    response = llm.complete(
        system_prompt=system,
        user_prompt=json.dumps(prompt, ensure_ascii=False, indent=2),
        max_tokens=2200,
        temperature=0.1,
    )
    alignment = ensure_object(extract_json(response), context="story pilot alignment")
    return alignment, _trace(ALIGNER_VERSION, system, prompt)


def judge_story(
    *,
    llm: ChatLLM,
    mechanism_graph: dict[str, Any],
    mapping_plan: dict[str, Any],
    story: str,
    alignment: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = {
        "scores": {
            "faithfulness": 1,
            "implicitness": 1,
            "mapping_clarity": 1,
            "readability": 1,
            "pedagogical_value": 1,
            "novelty": 1,
        },
        "hard_flags": {
            "concept_contradiction": False,
            "unmapped_core_mechanism": False,
            "template_like": False,
        },
        "mapping_diagnosis": {
            "strongest_node_id": "n1",
            "weakest_node_id": "n2",
            "weakest_edge_id": "e1",
            "distinguishing_reason": "...",
        },
        "revision_instructions": ["..."],
        "final_status": "accept|revise|reject",
    }
    prompt = {
        "task": "TASK:STORY_PILOT_JUDGE",
        "requirements": [
            "Return strict JSON only and score each dimension from 1 to 5.",
            "Use the supplied exact-evidence alignment and automatic metrics; do not reward fluent prose for missing mechanism structure.",
            "Distinguish relation preservation from endpoint mention.",
            "Explain what makes this mapping observably better or worse than another possible realization.",
            "Set revise or reject when any must-preserve relation is missing or reversed.",
            "The automatic structure gate is binding: node_coverage or edge_coverage below 0.8 cannot be accept; direction_accuracy below 1.0 cannot be accept.",
            "Hard leakage or story length outside 450-750 Chinese characters cannot be accept.",
        ],
        "mechanism_graph": mechanism_graph,
        "frozen_mapping_plan": mapping_plan,
        "story": story,
        "alignment": alignment,
        "automatic_metrics": metrics,
        "output_schema": schema,
    }
    system = "You are a strict, mapping-aware Chinese educational-fable judge. Return JSON only."
    response = llm.complete(
        system_prompt=system,
        user_prompt=json.dumps(prompt, ensure_ascii=False, indent=2),
        max_tokens=1800,
        temperature=0.1,
    )
    judgment = ensure_object(extract_json(response), context="story pilot judgment")
    return judgment, _trace(JUDGE_VERSION, system, prompt)


def revise_story(
    *,
    llm: ChatLLM,
    mapping_plan: dict[str, Any],
    story: str,
    alignment: dict[str, Any],
    judgment: dict[str, Any],
    metrics: dict[str, Any],
    forbidden_terms: list[str],
) -> tuple[str, dict[str, Any]]:
    prompt = {
        "task": "TASK:STORY_PILOT_REVISER",
        "requirements": [
            "Return only the revised Chinese story body.",
            "Keep the frozen source domain and every node/edge correspondence unchanged.",
            "Repair only evidence gaps, relation direction, repetition, leakage, and narrative clarity.",
            "Do not add scientific explanation or target terminology.",
        ],
        "forbidden_terms": forbidden_terms,
        "frozen_mapping_plan": mapping_plan,
        "current_story": story,
        "alignment": alignment,
        "judgment": judgment,
        "automatic_metrics": metrics,
        "explicit_repair_targets": {
            "missing_node_ids": alignment.get("missing_node_ids", []),
            "missing_edge_ids": alignment.get("missing_edge_ids", []),
            "hard_leakage": metrics.get("hard_leakage", False),
            "length_valid": metrics.get("length_valid", False),
        },
    }
    system = "You revise a Chinese fable while preserving its frozen analogy mapping."
    revised = llm.complete(
        system_prompt=system,
        user_prompt=json.dumps(prompt, ensure_ascii=False, indent=2),
        max_tokens=1800,
        temperature=0.45,
    ).strip()
    return _strip_fences(revised), _trace(REVISER_VERSION, system, prompt)


def apply_quality_gate(judgment: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(judgment.get("final_status") or "revise")
    reasons: list[str] = []
    if float(metrics.get("node_coverage") or 0.0) < 0.8:
        reasons.append("node_coverage_below_0.8")
    if float(metrics.get("edge_coverage") or 0.0) < 0.8:
        reasons.append("edge_coverage_below_0.8")
    if float(metrics.get("direction_accuracy") or 0.0) < 1.0:
        reasons.append("direction_not_preserved")
    if metrics.get("hard_leakage"):
        reasons.append("hard_leakage")
    if not metrics.get("length_valid", False):
        reasons.append("story_length_outside_450_750")
    effective_status = raw_status
    if reasons and raw_status == "accept":
        effective_status = "revise"
    if (
        float(metrics.get("node_coverage") or 0.0) < 0.4
        or float(metrics.get("edge_coverage") or 0.0) < 0.4
    ):
        effective_status = "reject"
    return {
        **judgment,
        "raw_final_status": raw_status,
        "final_status": effective_status,
        "quality_gate": {"passed": not reasons, "reasons": reasons},
    }


def _trace(version: str, system: str, prompt: dict[str, Any]) -> dict[str, Any]:
    return {"status": "success", "version": version, "prompt_sha256": stable_hash({"system": system, "prompt": prompt})}


def _strip_fences(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        value = value.strip("`").strip()
        if value.lower().startswith("text"):
            value = value[4:].strip()
    return value
