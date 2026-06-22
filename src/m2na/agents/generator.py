"""Generator agent：叙事规划 -> 隐性叙事类比 N。

依据规划把机制实例化为一段具体、最小、连贯的短叙事，
正文不得出现概念名或 T_c 中的高泄露术语。
"""

from __future__ import annotations

import json

from ..types import M2NAInput, NarrativePlan
from .llm import STAGE_GENERATE, LLMClient, tag


def _build_prompt(inp: M2NAInput, plan: NarrativePlan) -> str:
    g = inp.mechanism
    carriers = "\n".join(
        f"- {m.concept_element} -> {m.narrative_carrier}" for m in plan.mappings
    )
    forbidden = ", ".join(inp.forbidden_terms)
    return (
        f"{tag(STAGE_GENERATE, g.concept)}\n"
        "Write a short implicit narrative analogy (one paragraph) that instantiates "
        "the planned mapping in a concrete situation.\n"
        "Constraints: keep it minimal and coherent; let events carry the meaning "
        "without explaining it; do NOT use any forbidden term.\n\n"
        f"Source domain: {plan.source_domain}\n"
        f"Element carriers:\n{carriers}\n\n"
        f"Forbidden terms: {forbidden}\n\n"
        "Return JSON: {\"narrative\": str}"
    )


def _parse(raw: str) -> str:
    return json.loads(raw)["narrative"]


class Generator:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def generate(self, inp: M2NAInput, plan: NarrativePlan) -> str:
        raw = self._llm.complete(_build_prompt(inp, plan))
        return _parse(raw)
