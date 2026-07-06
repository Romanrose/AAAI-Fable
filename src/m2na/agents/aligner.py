"""Aligner agent：叙事 N + G_c -> 结构映射 A。

把生成叙事中的实体/事件显式回指到机制图节点，产出可验证的对齐。
"""

from __future__ import annotations

import json

from ..types import AlignmentPair, M2NAInput
from .llm import STAGE_ALIGN, LLMClient, tag

# 独立、客观的评判 system。关键：允许判"未实现"、禁止硬凑、不假设叙事来源。
# 注意：aligner 是评判者，架构上可注入与 generator 不同的 client（异源模型更客观）。
SYSTEM_PROMPT = (
    "你是独立、严格的对齐评判员，不参与叙事创作。"
    "给你一段叙事和一组机制节点，你唯一的职责是客观判断：这段叙事是否真的实现了每个节点。"
    "规则："
    "（1）只有当叙事中确有具体内容对应某节点时，才给出对应的叙事片段；"
    "（2）若叙事并未真正体现某节点，必须诚实地把 narrative_element 留空字符串，"
    "绝不能为了凑满而牵强附会；"
    "（3）你不知道、也不应假设这段叙事是如何产生的、是否本应覆盖这些节点。"
    "对每个节点都要给出一项判断。只输出严格 JSON，不要解释。"
)


def _build_prompt(inp: M2NAInput, narrative: str) -> str:
    g = inp.mechanism
    nodes = "\n".join(f"- {n.id}: {n.label}" for n in g.nodes)
    return (
        f"{tag(STAGE_ALIGN, g.concept)}\n"
        f"机制节点:\n{nodes}\n\n"
        f"叙事:\n{narrative}\n\n"
        "对每个节点判断叙事是否真的实现了它：实现则给出具体叙事片段，"
        "未实现则 narrative_element 留空字符串（不要牵强）。\n"
        "返回 JSON: {\"alignment\": "
        "[{\"concept_element\": node_id, \"narrative_element\": str}]}"
    )


def _parse(raw: str) -> tuple[AlignmentPair, ...]:
    data = json.loads(raw)
    return tuple(
        AlignmentPair(
            concept_element=a["concept_element"],
            narrative_element=a["narrative_element"],
        )
        for a in data["alignment"]
    )


class Aligner:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def align(self, inp: M2NAInput, narrative: str) -> tuple[AlignmentPair, ...]:
        raw = self._llm.complete(_build_prompt(inp, narrative), system=SYSTEM_PROMPT)
        return _parse(raw)
