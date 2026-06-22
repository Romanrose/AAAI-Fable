"""Aligner agent：叙事 N + G_c -> 结构映射 A。

把生成叙事中的实体/事件显式回指到机制图节点，产出可验证的对齐。
"""

from __future__ import annotations

import json

from ..types import AlignmentPair, M2NAInput
from .llm import STAGE_ALIGN, LLMClient, tag


def _build_prompt(inp: M2NAInput, narrative: str) -> str:
    g = inp.mechanism
    nodes = "\n".join(f"- {n.id}: {n.label}" for n in g.nodes)
    return (
        f"{tag(STAGE_ALIGN, g.concept)}\n"
        "Align the narrative back to the mechanism. For each mechanism node, point to "
        "the concrete narrative element that realizes it.\n\n"
        f"Mechanism nodes:\n{nodes}\n\n"
        f"Narrative:\n{narrative}\n\n"
        "Return JSON: {\"alignment\": "
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
        raw = self._llm.complete(_build_prompt(inp, narrative))
        return _parse(raw)
