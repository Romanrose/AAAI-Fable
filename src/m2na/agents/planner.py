"""Planner agent：G_c -> 寓言规划。

为机制图挑选一个具体、可寓言化的源域，并产出角色、冲突、情节节拍、结局等
结构化蓝图。Generator 只负责把这个蓝图写成正文，不再临场发明故事骨架。
"""

from __future__ import annotations

import json

from ..types import (
    FableCharacter,
    M2NAInput,
    NarrativePlan,
    PlannedMapping,
    PlotBeat,
)
from .llm import STAGE_PLAN, LLMClient, tag

SYSTEM_PROMPT = (
    "你是寓言结构设计师。职责：把抽象机制图改写成一则短寓言的蓝图，而不是写正文。"
    "你必须为每个机制节点安排清晰的角色、器物、事件或后果，并把机制边转成情节推进。"
    "优先使用动物、器物、工匠、村庄、作坊、自然物等寓言载体；避免现代课堂、考试、论文、"
    "实验室、直接科普解释和抽象说理。"
    "蓝图必须包含情境、中心冲突、按因果推进的 plot beats、转折、后果和含蓄寓意。"
    "只依据本次提供的机制图工作，不假设它来自何处，也不参考任何此前对话。"
    "只输出严格 JSON，不要解释。"
)


def _build_prompt(inp: M2NAInput) -> str:
    g = inp.mechanism
    nodes = "\n".join(f"- {n.id}: {n.label}" for n in g.nodes)
    edges = "\n".join(f"- {e.source} --{e.relation}--> {e.target}" for e in g.edges)
    forbidden = ", ".join(inp.forbidden_terms)
    return (
        f"{tag(STAGE_PLAN, g.concept)}\n"
        "你拿到的是核心机制图：只表示概念内部如何运作，不是关键词附近的完整知识子图。\n"
        "请把它规划成寓言蓝图，让后续写作者能写出有角色、有冲突、有后果的短寓言。\n\n"
        f"机制节点:\n{nodes}\n\n"
        f"机制边:\n{edges}\n\n"
        f"禁用词（最终正文中不得出现）: {forbidden}\n\n"
        "返回 JSON，字段必须为：\n"
        "{\n"
        "  \"source_domain\": str,\n"
        "  \"setting\": str,\n"
        "  \"conflict\": str,\n"
        "  \"characters\": "
        "[{\"name\": str, \"role\": str, \"mapped_element\": node_id}],\n"
        "  \"mappings\": "
        "[{\"concept_element\": node_id, \"narrative_carrier\": str}],\n"
        "  \"plot_beats\": "
        "[{\"beat_id\": str, \"event\": str, \"mapped_elements\": [node_id]}],\n"
        "  \"turning_point\": str,\n"
        "  \"ending\": str,\n"
        "  \"implied_moral\": str\n"
        "}\n"
        "要求：plot_beats 要按机制边的因果顺序推进；每个机制节点至少出现在 mappings 中一次。"
    )


def _as_tuple(value: object) -> tuple:
    return tuple(value) if isinstance(value, list) else ()


def _parse(raw: str) -> NarrativePlan:
    data = json.loads(raw)
    mappings = tuple(
        PlannedMapping(
            concept_element=m["concept_element"],
            narrative_carrier=m["narrative_carrier"],
        )
        for m in data["mappings"]
    )
    characters = tuple(
        FableCharacter(
            name=c.get("name", ""),
            role=c.get("role", ""),
            mapped_element=c.get("mapped_element", ""),
        )
        for c in _as_tuple(data.get("characters"))
    )
    plot_beats = tuple(
        PlotBeat(
            beat_id=b.get("beat_id", ""),
            event=b.get("event", ""),
            mapped_elements=tuple(str(x) for x in b.get("mapped_elements", [])),
        )
        for b in _as_tuple(data.get("plot_beats"))
    )
    return NarrativePlan(
        source_domain=data["source_domain"],
        mappings=mappings,
        characters=characters,
        setting=data.get("setting", ""),
        conflict=data.get("conflict", ""),
        plot_beats=plot_beats,
        turning_point=data.get("turning_point", ""),
        ending=data.get("ending", ""),
        implied_moral=data.get("implied_moral", ""),
    )


class Planner:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def plan(self, inp: M2NAInput) -> NarrativePlan:
        raw = self._llm.complete(_build_prompt(inp), system=SYSTEM_PROMPT)
        return _parse(raw)
