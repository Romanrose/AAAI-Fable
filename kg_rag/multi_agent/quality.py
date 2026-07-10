from __future__ import annotations

from typing import Any

from kg_rag.evaluation.rubric import decide_status, weighted_overall


def _score_by_threshold(value: float, *, high: float, mid: float) -> int:
    if value >= high:
        return 5
    if value >= mid:
        return 4
    if value >= 0.4:
        return 3
    if value >= 0.2:
        return 2
    return 1


def build_rule_six_dim_eval(
    *,
    concept_id: str,
    target_concept: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    node_cov = float(metrics.get("weighted_node_coverage") or 0.0)
    edge_cov = float(metrics.get("weighted_edge_coverage") or 0.0)
    precision = float(metrics.get("alignment_precision") or 0.0)
    direction = metrics.get("relation_direction_accuracy")
    direction_value = 1.0 if direction is None else float(direction)
    template_rate = float(metrics.get("template_hit_rate") or 0.0)
    char_count = int(metrics.get("narrative_char_count") or 0)
    hard_leakage = bool(metrics.get("exact_concept_leakage"))
    soft_leakage = bool(metrics.get("soft_term_leakage"))

    faithfulness_base = (node_cov + edge_cov + direction_value) / 3
    mapping_base = (node_cov + edge_cov + precision) / 3
    readability = 5 if 220 <= char_count <= 1200 else 4 if 120 <= char_count < 1600 else 3
    novelty = 5 if template_rate == 0 else 3 if template_rate <= 0.2 else 2
    scores = {
        "faithfulness": min(5, _score_by_threshold(faithfulness_base, high=0.9, mid=0.7)),
        "implicitness": 1 if hard_leakage else 2 if soft_leakage else 5,
        "mapping_clarity": _score_by_threshold(mapping_base, high=0.9, mid=0.7),
        "readability": readability,
        "pedagogical_value": _score_by_threshold((node_cov + edge_cov) / 2, high=0.85, mid=0.65),
        "novelty": novelty,
    }
    hard_flags = {
        "hard_leakage": hard_leakage,
        "soft_leakage": soft_leakage,
        "title_leakage": False,
        "concept_contradiction": False,
        "unmapped_core_mechanism": node_cov < 0.35,
        "template_like": template_rate > 0.2,
    }
    return {
        "concept_id": concept_id,
        "target_concept": target_concept,
        "scores": scores,
        "weighted_overall": weighted_overall(scores),
        "hard_flags": hard_flags,
        "rationales": {
            "faithfulness": "根据机制节点、机制边覆盖率和方向正确率自动估计。",
            "implicitness": "根据目标概念名、别名和禁用词是否出现在正文中自动检查。",
            "mapping_clarity": "根据故事证据能否对齐回机制图自动估计。",
            "readability": "根据正文长度和完整性做轻量规则估计。",
            "pedagogical_value": "根据核心节点和关系是否被覆盖自动估计。",
            "novelty": "根据常见模板词命中率自动估计。",
        },
        "revision_suggestions": _suggest_revisions(scores, hard_flags),
        "final_status": decide_status(scores, hard_flags),
        "mode": "rules",
    }


def _suggest_revisions(scores: dict[str, int], flags: dict[str, bool]) -> list[str]:
    suggestions: list[str] = []
    if flags.get("hard_leakage") or flags.get("soft_leakage"):
        suggestions.append("重写正文，移除目标概念名、别名和强术语。")
    if scores["mapping_clarity"] < 4:
        suggestions.append("补充故事事件和机制节点/边之间的明确对应证据。")
    if scores["faithfulness"] < 4:
        suggestions.append("回到机制图检查关键条件、过程和结果是否缺失或反向。")
    if scores["novelty"] < 3:
        suggestions.append("更换故事域，避免智者、村庄、森林等常见模板。")
    return suggestions
