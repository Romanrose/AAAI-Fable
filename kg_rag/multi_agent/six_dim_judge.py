from __future__ import annotations

import json
from typing import Any

from kg_rag.evaluation.rubric import (
    DIMENSIONS,
    HARD_FLAG_KEYS,
    decide_status,
    normalize_hard_flags,
    normalize_scores,
    weighted_overall,
)
from kg_rag.multi_agent.llm import ChatLLM, ensure_object, extract_json
from kg_rag.multi_agent.quality import build_rule_six_dim_eval


DIMENSION_RUBRIC_ZH = {
    "faithfulness": "忠实度：寓言是否准确表达目标概念的核心机制、条件和结果。",
    "implicitness": "隐含性：正文是否没有直接暴露概念名、别名、专业术语或教材式定义。",
    "mapping_clarity": "映射清晰度：故事角色、物品、行动和因果链是否能对应机制图。",
    "readability": "可读性：故事是否自然、连贯、易读，适合中文学习者阅读。",
    "pedagogical_value": "教学价值：读完后是否有助于理解概念机制，而不是只得到表面类比。",
    "novelty": "新颖性：故事是否避免模板化、陈词滥调和固定寓言壳。",
}


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


class SixDimJudgeAgent:
    def __init__(self, llm: ChatLLM):
        self.llm = llm

    def evaluate(
        self,
        *,
        card: dict[str, Any],
        retrieval_package: dict[str, Any],
        mechanism_graph: dict[str, Any],
        narrative_plan: dict[str, Any],
        story: str,
        alignment: dict[str, Any],
        automatic_metrics: dict[str, Any],
    ) -> dict[str, Any]:
        concept_id = str(card.get("concept_id") or automatic_metrics.get("id") or "")
        target_concept = str(card.get("canonical_name") or concept_id)
        rule_eval = build_rule_six_dim_eval(
            concept_id=concept_id,
            target_concept=target_concept,
            metrics=automatic_metrics,
        )
        system_prompt = (
            "你是教育寓言质量评审 Agent。你必须严格按照六维量表评估中文寓言，"
            "只输出合法 JSON，不输出 Markdown 或解释性段落。"
        )
        user_prompt = f"""TASK:SIX_DIM_JUDGE_JSON
请对下面的“目标概念 -> 图检索机制 -> 寓言结构 -> 最终故事”产物做中文六维评估。

评估原则：
1. 评分使用 1-5 分 Likert，5 分最好，1 分最差。
2. 必须优先判断概念是否忠实、机制映射是否清楚、是否有教学价值。
3. 故事正文不能直接出现目标概念名、别名或禁用术语；如果出现，hard_leakage=true，implicitness=1。
4. 如果故事核心机制与目标概念相反，concept_contradiction=true，faithfulness<=2。
5. 如果核心机制无法映射到故事事件，unmapped_core_mechanism=true，mapping_clarity<=2。
6. rationales、evidence、revision_suggestions 必须使用自然中文。
7. evidence 可以概括故事证据，不需要长篇引用。

六维定义：
{_dumps(DIMENSION_RUBRIC_ZH)}

概念卡：
{_dumps(card)}

GraphRAG 检索摘要：
{_dumps(retrieval_package.get("topic_summary", {}))}

机制图：
{_dumps(mechanism_graph)}

寓言结构方案：
{_dumps(narrative_plan)}

最终故事正文：
{story}

故事-机制对齐：
{_dumps(alignment)}

确定性自动指标：
{_dumps(automatic_metrics)}

输出 JSON schema：
{{
  "scores": {{
    "faithfulness": 1,
    "implicitness": 1,
    "mapping_clarity": 1,
    "readability": 1,
    "pedagogical_value": 1,
    "novelty": 1
  }},
  "hard_flags": {{
    "hard_leakage": false,
    "soft_leakage": false,
    "title_leakage": false,
    "concept_contradiction": false,
    "unmapped_core_mechanism": false,
    "template_like": false
  }},
  "rationales": {{
    "faithfulness": "1-3句中文理由",
    "implicitness": "1-3句中文理由",
    "mapping_clarity": "1-3句中文理由",
    "readability": "1-3句中文理由",
    "pedagogical_value": "1-3句中文理由",
    "novelty": "1-3句中文理由"
  }},
  "evidence": {{
    "faithfulness": "中文证据",
    "implicitness": "中文证据",
    "mapping_clarity": "中文证据",
    "readability": "中文证据",
    "pedagogical_value": "中文证据",
    "novelty": "中文证据"
  }},
  "revision_suggestions": ["中文修改建议"]
}}
"""
        try:
            response = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1800,
                temperature=0.15,
            )
            judge_response = ensure_object(extract_json(response), context="six-dimensional judge response")
            return normalize_llm_judge_result(
                concept_id=concept_id,
                target_concept=target_concept,
                judge_response=judge_response,
                automatic_metrics=automatic_metrics,
                rule_eval=rule_eval,
            )
        except Exception as exc:
            fallback = dict(rule_eval)
            fallback["mode"] = "llm_failed_rules"
            fallback["judge_error"] = str(exc)
            fallback["judge_response"] = None
            return fallback


def normalize_llm_judge_result(
    *,
    concept_id: str,
    target_concept: str,
    judge_response: dict[str, Any],
    automatic_metrics: dict[str, Any],
    rule_eval: dict[str, Any],
) -> dict[str, Any]:
    scores = normalize_scores(judge_response.get("scores"))
    hard_flags = normalize_hard_flags(judge_response.get("hard_flags"))
    rationales = _normalize_text_map(judge_response.get("rationales"))
    evidence = _normalize_text_map(judge_response.get("evidence"))
    raw_suggestions = judge_response.get("revision_suggestions", [])
    if not isinstance(raw_suggestions, list):
        raw_suggestions = []
    suggestions = [
        str(item).strip()
        for item in raw_suggestions
        if isinstance(item, str) and item.strip()
    ]

    apply_metric_overrides(scores, hard_flags, automatic_metrics)

    if not rationales:
        rationales = rule_eval.get("rationales", {})
    if not suggestions:
        suggestions = rule_eval.get("revision_suggestions", [])

    return {
        "concept_id": concept_id,
        "target_concept": target_concept,
        "scores": scores,
        "weighted_overall": weighted_overall(scores),
        "hard_flags": hard_flags,
        "rationales": rationales,
        "evidence": evidence,
        "revision_suggestions": suggestions,
        "final_status": decide_status(scores, hard_flags),
        "mode": "llm",
        "judge_response": judge_response,
        "rule_eval": rule_eval,
        "automatic_metric_overrides": {
            "exact_concept_leakage": automatic_metrics.get("exact_concept_leakage"),
            "soft_term_leakage": automatic_metrics.get("soft_term_leakage"),
            "weighted_node_coverage": automatic_metrics.get("weighted_node_coverage"),
            "weighted_edge_coverage": automatic_metrics.get("weighted_edge_coverage"),
            "alignment_precision": automatic_metrics.get("alignment_precision"),
            "relation_direction_accuracy": automatic_metrics.get("relation_direction_accuracy"),
            "template_hit_rate": automatic_metrics.get("template_hit_rate"),
        },
    }


def apply_metric_overrides(
    scores: dict[str, int],
    hard_flags: dict[str, bool],
    automatic_metrics: dict[str, Any],
) -> None:
    if bool(automatic_metrics.get("exact_concept_leakage")):
        hard_flags["hard_leakage"] = True
        scores["implicitness"] = 1
    if bool(automatic_metrics.get("soft_term_leakage")):
        hard_flags["soft_leakage"] = True
        scores["implicitness"] = min(scores["implicitness"], 2)

    node_cov = float(automatic_metrics.get("weighted_node_coverage") or 0.0)
    edge_cov = float(automatic_metrics.get("weighted_edge_coverage") or 0.0)
    alignment_precision = float(automatic_metrics.get("alignment_precision") or 0.0)
    direction = automatic_metrics.get("relation_direction_accuracy")

    if node_cov < 0.35:
        hard_flags["unmapped_core_mechanism"] = True
        scores["mapping_clarity"] = min(scores["mapping_clarity"], 2)
        scores["pedagogical_value"] = min(scores["pedagogical_value"], 2)
    elif node_cov < 0.65:
        scores["mapping_clarity"] = min(scores["mapping_clarity"], 3)

    if edge_cov < 0.35:
        hard_flags["unmapped_core_mechanism"] = True
        scores["mapping_clarity"] = min(scores["mapping_clarity"], 2)
    elif edge_cov < 0.65:
        scores["mapping_clarity"] = min(scores["mapping_clarity"], 3)

    if alignment_precision < 0.5:
        scores["mapping_clarity"] = min(scores["mapping_clarity"], 3)

    if direction is not None and float(direction) < 0.5:
        scores["faithfulness"] = min(scores["faithfulness"], 2)
        hard_flags["concept_contradiction"] = True

    if float(automatic_metrics.get("template_hit_rate") or 0.0) > 0.2:
        hard_flags["template_like"] = True
        scores["novelty"] = min(scores["novelty"], 2)


def _normalize_text_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    results: dict[str, str] = {}
    for dimension in DIMENSIONS:
        text = value.get(dimension)
        if isinstance(text, str) and text.strip():
            results[dimension] = text.strip()
    for key in HARD_FLAG_KEYS:
        text = value.get(key)
        if isinstance(text, str) and text.strip():
            results[key] = text.strip()
    return results
