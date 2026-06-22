"""Planner agent：G_c -> 叙事规划。

为机制图挑选一个具体、日常、非模板化的源域，并建立
「概念要素 -> 叙事载体」的初步映射，供后续生成阶段落笔。
"""

from __future__ import annotations

import json

from ..types import M2NAInput, NarrativePlan, PlannedMapping
from .llm import STAGE_PLAN, LLMClient, tag


def _build_prompt(inp: M2NAInput) -> str:
    g = inp.mechanism
    nodes = "\n".join(f"- {n.id}: {n.label}" for n in g.nodes)
    edges = "\n".join(f"- {e.source} --{e.relation}--> {e.target}" for e in g.edges)
    forbidden = ", ".join(inp.forbidden_terms)
    return (
        f"{tag(STAGE_PLAN, g.concept)}\n"
        "You plan an implicit narrative analogy for an abstract mechanism.\n"
        "Pick one concrete, everyday source domain (avoid clichés like sages, "
        "rivers, mirrors) and map each mechanism element to a narrative carrier.\n\n"
        f"Mechanism nodes:\n{nodes}\n\n"
        f"Mechanism edges:\n{edges}\n\n"
        f"Forbidden terms (must not appear in the final narrative): {forbidden}\n\n"
        "Return JSON: {\"source_domain\": str, "
        "\"mappings\": [{\"concept_element\": node_id, \"narrative_carrier\": str}]}"
    )


def _parse(raw: str) -> NarrativePlan:
    data = json.loads(raw)
    mappings = tuple(
        PlannedMapping(
            concept_element=m["concept_element"],
            narrative_carrier=m["narrative_carrier"],
        )
        for m in data["mappings"]
    )
    return NarrativePlan(source_domain=data["source_domain"], mappings=mappings)


class Planner:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def plan(self, inp: M2NAInput) -> NarrativePlan:
        raw = self._llm.complete(_build_prompt(inp))
        return _parse(raw)
