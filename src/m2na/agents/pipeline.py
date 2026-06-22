"""M2NA 流水线编排：plan -> generate -> align -> review。

把四个 agent 串成一条最小端到端闭环：输入 (G_c, T_c) -> 输出 (N, A) + 自检报告。
LLM 通过构造函数注入，可在 Mock 与真实后端之间无缝替换。
"""

from __future__ import annotations

from ..types import M2NAInput, M2NAResult
from .aligner import Aligner
from .generator import Generator
from .llm import LLMClient
from .planner import Planner
from .reviser import Reviser


class M2NAPipeline:
    def __init__(self, llm: LLMClient) -> None:
        self._planner = Planner(llm)
        self._generator = Generator(llm)
        self._aligner = Aligner(llm)
        self._reviser = Reviser()

    def run(self, inp: M2NAInput) -> M2NAResult:
        plan = self._planner.plan(inp)
        narrative = self._generator.generate(inp, plan)
        alignment = self._aligner.align(inp, narrative)
        report = self._reviser.review(inp, narrative, alignment)
        return M2NAResult(
            concept=inp.mechanism.concept,
            plan=plan,
            narrative=narrative,
            alignment=alignment,
            report=report,
        )
