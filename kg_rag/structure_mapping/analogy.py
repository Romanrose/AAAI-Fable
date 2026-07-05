from __future__ import annotations

from typing import Any


SOURCE_DOMAINS_ZH = {
    "biology": "屋顶育苗棚",
    "chemistry": "材料试炼间",
    "physics": "轨道调度台",
    "math": "折纸修复台",
}

TEMPLATE_BLACKLIST_ZH = ("智者", "老人", "村庄", "森林", "镜子", "钟表", "河流")


def _mask_terms(text: str, terms: list[str]) -> str:
    masked = text
    for term in sorted((term for term in terms if term), key=len, reverse=True):
        masked = masked.replace(term, "这条隐藏规则")
    return masked


def _event_for_step(step: dict[str, Any], forbidden_terms: list[str]) -> str:
    text = _mask_terms(str(step.get("text", "")).strip(), forbidden_terms)
    kind = step.get("kind")
    if kind == "condition":
        return f"先确认一个起点条件是否具备：{text}"
    if kind == "effect":
        return f"再观察这个变化会留下什么结果：{text}"
    return f"让中间的行动承接前后变化：{text}"


def build_analogy_plan(
    card: dict[str, Any],
    mechanism_plan: dict[str, Any],
    *,
    template_blacklist: str = "default",
) -> dict[str, Any]:
    subject = str(card.get("subject") or "")
    source_domain = SOURCE_DOMAINS_ZH.get(subject, "临时修补台")
    forbidden_terms = [str(term) for term in mechanism_plan.get("forbidden_terms", []) if term]
    steps = [step for step in mechanism_plan.get("steps", []) if isinstance(step, dict)]
    event_chain = [_event_for_step(step, forbidden_terms) for step in steps]

    if not event_chain:
        event_chain = [
            "先确认隐藏条件是否成立。",
            "再让行动按顺序发生。",
            "最后检查结果是否稳定出现。",
        ]

    blacklist_terms = list(TEMPLATE_BLACKLIST_ZH) if template_blacklist == "default" else []
    return {
        "found": True,
        "query": card["concept_id"],
        "concept_id": card["concept_id"],
        "story_language": "zh-CN",
        "source_domain": source_domain,
        "characters": [
            "负责记录变化的学徒",
            "坚持按步骤验收的师傅",
            "一套会暴露错误顺序的器具",
        ],
        "entities": [
            "负责记录变化的学徒",
            "一张分段验收单",
            "一套会暴露错误顺序的器具",
        ],
        "conflict": "表面结果看似已经出现，但前置条件、核心过程和后续影响没有被逐项核对。",
        "event_chain": event_chain,
        "turning_point": "一次分段验收让主角发现，只有条件、过程和结果连起来，变化才算真正成立。",
        "resolution_state": "主角学会先看条件，再看过程，最后用结果反查整条关系是否可靠。",
        "alignment_targets": [
            {
                "mechanism_step_id": step.get("step_id"),
                "mechanism_kind": step.get("kind"),
                "story_event": event,
            }
            for step, event in zip(steps, event_chain, strict=False)
        ],
        "alignment_plan": [
            {
                "concept_role": "目标概念",
                "concept_items": [card.get("canonical_name")],
                "story_role": "故事中不直接说出的隐藏规则",
            },
            {
                "concept_role": "核心机制",
                "concept_items": [step.get("text") for step in steps[:6]],
                "story_role": "分段验收中的条件、行动和结果链",
            },
            {
                "concept_role": "学科约束",
                "concept_items": card.get("subject_constraints_zh", [])[:5],
                "story_role": "防止故事类比误导概念理解的写作约束",
            },
        ],
        "template_blacklist": blacklist_terms,
    }

