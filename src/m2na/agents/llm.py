"""可插拔的 LLM 接口层。

设计目标：让第二部分(agent 架构)在不接真实 API 的情况下也能端到端跑通。
- LLMClient：统一协议，各 agent 只依赖它。
- MockLLMClient：离线实现，根据 prompt 中的 [[STAGE]] / [[CONCEPT]] 标签返回预设响应。
- 真实后端(OpenAI/DeepSeek 等)只需另写一个实现同样 complete() 的类即可替换。
"""

from __future__ import annotations

import json
import re
from typing import Dict, Protocol

# 各 agent 在 prompt 中嵌入的阶段标签，Mock 据此分发；对真实 LLM 也是有用的上下文。
STAGE_PLAN = "plan"
STAGE_GENERATE = "generate"
STAGE_ALIGN = "align"

_STAGE_RE = re.compile(r"\[\[STAGE:(?P<stage>[a-z]+)\]\]")
_CONCEPT_RE = re.compile(r"\[\[CONCEPT:(?P<concept>[^\]]+)\]\]")


class LLMClient(Protocol):
    """所有 agent 依赖的最小 LLM 契约。"""

    def complete(self, prompt: str) -> str: ...


def tag(stage: str, concept: str) -> str:
    """生成 prompt 中的标签头，供 agent 复用。"""

    return f"[[STAGE:{stage}]] [[CONCEPT:{concept}]]"


class LLMError(RuntimeError):
    """Mock 无法为给定输入给出响应时抛出，避免静默返回空结果。"""


# --------------------------------------------------------------------------- #
# 离线 Mock 实现
# --------------------------------------------------------------------------- #
# 预设故事库：concept -> 各阶段的结构化响应。
# 内容取自论文文档中的示例(path dependence 的炉子故事)，使端到端结果非平凡、可评估。
_MOCK_KNOWLEDGE: Dict[str, Dict] = {
    "path dependence": {
        STAGE_PLAN: {
            "source_domain": "a small neighborhood restaurant and its first stove",
            "mappings": [
                {"concept_element": "initial_choice", "narrative_carrier": "the rare stove the shop bought on opening day"},
                {"concept_element": "reinforcing_feedback", "narrative_carrier": "recipes and worker habits that grew around the stove"},
                {"concept_element": "switching_cost", "narrative_carrier": "retraining cooks and redesigning the menu"},
                {"concept_element": "lock_in", "narrative_carrier": "the shop could no longer imagine cooking any other way"},
                {"concept_element": "suboptimal_persistence", "narrative_carrier": "a newer cheaper stove existed but was never adopted"},
            ],
        },
        STAGE_GENERATE: {
            "narrative": (
                "On its opening day a small corner eatery bought one unusual cast-iron stove, "
                "simply because it was the only one the owner could afford that morning. "
                "Over the years every recipe was tuned to its quirks, and the cooks learned its "
                "hot corners by heart. New cooks were trained on it, and regulars came back for the "
                "dishes only that stove could make. When a lighter, cheaper stove appeared at the "
                "market, the owner did the math: every cook would need retraining and half the menu "
                "redrawn. So the old stove stayed, year after year, long after better ones existed."
            )
        },
        STAGE_ALIGN: {
            "alignment": [
                {"concept_element": "initial_choice", "narrative_element": "buying the only affordable stove on opening day"},
                {"concept_element": "reinforcing_feedback", "narrative_element": "recipes and cooks tuned to the stove over years"},
                {"concept_element": "switching_cost", "narrative_element": "retraining cooks and redrawing the menu"},
                {"concept_element": "lock_in", "narrative_element": "the old stove stayed year after year"},
                {"concept_element": "suboptimal_persistence", "narrative_element": "better stoves existed but were never adopted"},
            ]
        },
    },
    "overfitting": {
        STAGE_PLAN: {
            "source_domain": "a student who memorizes one teacher's past exams",
            "mappings": [
                {"concept_element": "fit_training_pattern", "narrative_carrier": "memorizing every old exam word for word"},
                {"concept_element": "high_seen_performance", "narrative_carrier": "scoring perfectly on the practice papers"},
                {"concept_element": "poor_generalization", "narrative_carrier": "freezing when the real test asks something new"},
            ],
        },
        STAGE_GENERATE: {
            "narrative": (
                "A diligent student got hold of every quiz a teacher had ever given and memorized "
                "each answer exactly, down to the order of the choices. On the practice papers he "
                "never missed a single question. But when the real exam arrived with freshly written "
                "problems, he sat frozen: he had learned the old papers, not the subject beneath them."
            )
        },
        STAGE_ALIGN: {
            "alignment": [
                {"concept_element": "fit_training_pattern", "narrative_element": "memorizing every old quiz exactly"},
                {"concept_element": "high_seen_performance", "narrative_element": "never missing a practice question"},
                {"concept_element": "poor_generalization", "narrative_element": "freezing on freshly written exam problems"},
            ]
        },
    },
}


class MockLLMClient:
    """根据 prompt 标签返回预设响应的离线 LLM。"""

    def __init__(self, knowledge: Dict[str, Dict] | None = None) -> None:
        self._knowledge = knowledge if knowledge is not None else _MOCK_KNOWLEDGE

    def complete(self, prompt: str) -> str:
        stage = self._extract(_STAGE_RE, prompt, "stage")
        concept = self._extract(_CONCEPT_RE, prompt, "concept")

        concept_entry = self._knowledge.get(concept)
        if concept_entry is None or stage not in concept_entry:
            raise LLMError(
                f"MockLLMClient 无预设响应: concept={concept!r} stage={stage!r}。"
                "请在 _MOCK_KNOWLEDGE 中补充，或改用真实 LLM 后端。"
            )
        return json.dumps(concept_entry[stage], ensure_ascii=False)

    @staticmethod
    def _extract(pattern: re.Pattern, prompt: str, field: str) -> str:
        match = pattern.search(prompt)
        if match is None:
            raise LLMError(f"prompt 缺少 [[{field.upper()}:...]] 标签，无法分发。")
        return match.group(field).strip()
