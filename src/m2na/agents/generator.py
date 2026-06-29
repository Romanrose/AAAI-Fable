"""Generator agent：寓言规划 -> 隐性寓言叙事 N。

依据 Planner 给出的寓言蓝图写正文。目标不是普通案例说明，而是一则短、具体、
有冲突和后果的隐性寓言；正文不得出现概念名或 T_c 中的高泄露术语。
"""

from __future__ import annotations

import json

from ..types import M2NAInput, NarrativePlan
from .llm import STAGE_GENERATE, LLMClient, tag

SYSTEM_PROMPT = (
    "你是寓言写作者。职责：把给定寓言蓝图写成一则短寓言，而不是解释性案例。"
    "故事必须有具体角色、处境、冲突、选择、转折和后果；用情节暗示机制，不直接解释概念。"
    "硬约束：严禁出现任何禁用词；不要出现'这说明/这象征/这个概念/对应/机制'等解释性话语；"
    "不要在正文后附映射表；不要写课堂、考试、模型训练或科普说明；控制在 150-250 个中文字左右。"
    "可以有一句含蓄收束，但不要点破目标概念。"
    "你只依据本次提供的规划工作，不参考任何此前对话。只输出严格 JSON，不要解释。"
)


def _build_prompt(inp: M2NAInput, plan: NarrativePlan) -> str:
    g = inp.mechanism
    carriers = "\n".join(
        f"- {m.concept_element} -> {m.narrative_carrier}" for m in plan.mappings
    )
    characters = "\n".join(
        f"- {c.name}: {c.role} (承载 {c.mapped_element})" for c in plan.characters
    ) or "- （无，请依据要素载体自行保持一致）"
    beats = "\n".join(
        f"- {b.beat_id}: {b.event} (承载 {', '.join(b.mapped_elements)})"
        for b in plan.plot_beats
    ) or "- （无，请按要素载体形成因果推进）"
    forbidden = ", ".join(inp.forbidden_terms)
    return (
        f"{tag(STAGE_GENERATE, g.concept)}\n"
        f"源域: {plan.source_domain}\n"
        f"情境: {plan.setting}\n"
        f"中心冲突: {plan.conflict}\n"
        f"角色/器物:\n{characters}\n\n"
        f"要素载体:\n{carriers}\n\n"
        f"情节节拍:\n{beats}\n\n"
        f"转折: {plan.turning_point}\n"
        f"结局: {plan.ending}\n"
        f"含蓄寓意（只供你把握，不要解释性点破）: {plan.implied_moral}\n\n"
        f"禁用词: {forbidden}\n\n"
        "请写一则完整短寓言。正文要自然覆盖所有情节节拍，但不要显式说明任何映射。\n"
        "返回 JSON: {\"narrative\": str}"
    )


def _parse(raw: str) -> str:
    return json.loads(raw)["narrative"]


class Generator:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def generate(self, inp: M2NAInput, plan: NarrativePlan) -> str:
        raw = self._llm.complete(_build_prompt(inp, plan), system=SYSTEM_PROMPT)
        return _parse(raw)
