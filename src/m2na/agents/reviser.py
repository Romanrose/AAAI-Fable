"""Reviser agent：流水线内的质检环。

两项确定性自检(不依赖 LLM，结果可复现)：
- 词汇泄露 (Lexical Concealment)：叙事正文是否命中 T_c 中的禁用词。
- 机制覆盖 (Mechanism Preservation)：对齐 A 是否覆盖了 G_c 的全部机制节点。

注：这里只产出报告，不重写文本。是否依据报告重试由 Pipeline 决定。
"""

from __future__ import annotations

from typing import Tuple

from ..types import AlignmentPair, M2NAInput, RevisionReport


def _find_hard_leaks(narrative: str, forbidden_terms: Tuple[str, ...]) -> Tuple[str, ...]:
    lowered = narrative.lower()
    return tuple(term for term in forbidden_terms if term.lower() in lowered)


def _find_uncovered(
    inp: M2NAInput, alignment: Tuple[AlignmentPair, ...]
) -> Tuple[str, ...]:
    # 只有"有非空叙事片段"的节点才算被覆盖：aligner 判为未实现(片段留空)的不算，
    # 这样客观评判员的"未实现"判断会如实反映成未覆盖，而不是被硬凑掩盖。
    covered = {
        pair.concept_element
        for pair in alignment
        if pair.narrative_element.strip()
    }
    return tuple(nid for nid in inp.mechanism.node_ids() if nid not in covered)


class Reviser:
    def review(
        self,
        inp: M2NAInput,
        narrative: str,
        alignment: Tuple[AlignmentPair, ...],
    ) -> RevisionReport:
        hard_leaks = _find_hard_leaks(narrative, inp.forbidden_terms)
        uncovered = _find_uncovered(inp, alignment)
        passed = not hard_leaks and not uncovered
        return RevisionReport(
            hard_leaks=hard_leaks,
            uncovered_elements=uncovered,
            passed=passed,
        )
