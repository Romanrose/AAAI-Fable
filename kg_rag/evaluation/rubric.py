from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DIMENSIONS = (
    "faithfulness",
    "implicitness",
    "mapping_clarity",
    "readability",
    "pedagogical_value",
    "novelty",
)

DIMENSION_NAMES_ZH = {
    "faithfulness": "\u5fe0\u5b9e\u5ea6",
    "implicitness": "\u9690\u542b\u6027",
    "mapping_clarity": "\u6620\u5c04\u6e05\u6670\u5ea6",
    "readability": "\u53ef\u8bfb\u6027",
    "pedagogical_value": "\u6559\u5b66\u4ef7\u503c",
    "novelty": "\u65b0\u9896\u6027",
}

WEIGHTS = {
    "faithfulness": 0.25,
    "mapping_clarity": 0.20,
    "pedagogical_value": 0.20,
    "implicitness": 0.15,
    "readability": 0.10,
    "novelty": 0.10,
}

HARD_FLAG_KEYS = (
    "hard_leakage",
    "soft_leakage",
    "title_leakage",
    "concept_contradiction",
    "unmapped_core_mechanism",
    "template_like",
)


@dataclass(frozen=True)
class EvaluationInput:
    concept_id: str
    target_concept: str
    concept_definition: str
    subgraph_pack: dict[str, Any]
    structure_plan: dict[str, Any]
    draft_story: str
    alignment_table: list[dict[str, Any]]
    forbidden_terms: list[str]


def clamp_score(value: Any, default: int = 3) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(5, score))


def normalize_scores(scores: dict[str, Any] | None) -> dict[str, int]:
    raw_scores = scores or {}
    return {dimension: clamp_score(raw_scores.get(dimension)) for dimension in DIMENSIONS}


def normalize_hard_flags(flags: dict[str, Any] | None) -> dict[str, bool]:
    raw_flags = flags or {}
    return {key: bool(raw_flags.get(key, False)) for key in HARD_FLAG_KEYS}


def weighted_overall(scores: dict[str, int]) -> float:
    value = sum(scores[dimension] * WEIGHTS[dimension] for dimension in DIMENSIONS)
    return round(value, 2)


def decide_status(scores: dict[str, int], hard_flags: dict[str, bool], *, strict_implicit: bool = True) -> str:
    if scores["faithfulness"] <= 2 or scores["mapping_clarity"] <= 2:
        return "reject"
    if hard_flags.get("concept_contradiction") or hard_flags.get("unmapped_core_mechanism"):
        return "reject"
    if strict_implicit and hard_flags.get("hard_leakage"):
        return "reject"

    core_ok = (
        scores["faithfulness"] >= 4
        and scores["mapping_clarity"] >= 4
        and scores["pedagogical_value"] >= 4
        and scores["implicitness"] >= 4
    )
    surface_ok = scores["readability"] >= 3 and scores["novelty"] >= 3
    blocking_flags = any(
        hard_flags[key] for key in ("hard_leakage", "concept_contradiction", "unmapped_core_mechanism")
    )
    if core_ok and surface_ok and not blocking_flags:
        return "accept"
    return "revise"


def build_result(
    *,
    evaluation_input: EvaluationInput,
    scores: dict[str, Any],
    hard_flags: dict[str, Any],
    rationales: dict[str, str] | None = None,
    revision_suggestions: list[str] | None = None,
    rule_findings: dict[str, Any] | None = None,
    judge_response: dict[str, Any] | None = None,
    mode: str = "rules",
) -> dict[str, Any]:
    normalized_scores = normalize_scores(scores)
    normalized_flags = normalize_hard_flags(hard_flags)
    return {
        "concept_id": evaluation_input.concept_id,
        "target_concept": evaluation_input.target_concept,
        "scores": normalized_scores,
        "weighted_overall": weighted_overall(normalized_scores),
        "hard_flags": normalized_flags,
        "rationales": rationales or {},
        "revision_suggestions": revision_suggestions or [],
        "rule_findings": rule_findings or {},
        "judge_response": judge_response,
        "final_status": decide_status(normalized_scores, normalized_flags),
        "mode": mode,
    }
