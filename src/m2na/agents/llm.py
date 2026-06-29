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
    """所有 agent 依赖的最小 LLM 契约。

    system: 角色化系统提示，与 user prompt 分离。每个 agent 传入自己独立的 system，
    使各 agent 作为互不知情的独立个体看待输入（隔离，降低"顺着上一步发挥"的偏置）。
    """

    def complete(self, prompt: str, system: str | None = None) -> str: ...


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
            "source_domain": "a village bakery and its first oven",
            "setting": "a hillside village bakery that must feed the market every morning",
            "conflict": "the baker keeps relying on an awkward old oven because the whole bakery has grown around it",
            "characters": [
                {"name": "the baker", "role": "owner who made the first purchase", "mapped_element": "initial_choice"},
                {"name": "the old oven", "role": "the early tool that shapes later routines", "mapped_element": "reinforcing_feedback"},
                {"name": "the apprentices", "role": "workers trained around the oven's habits", "mapped_element": "switching_cost"},
                {"name": "the new brass oven", "role": "better alternative that remains unused", "mapped_element": "suboptimal_persistence"},
            ],
            "mappings": [
                {"concept_element": "initial_choice", "narrative_carrier": "buying the only affordable oven on the first market day"},
                {"concept_element": "reinforcing_feedback", "narrative_carrier": "recipes, shelves, and apprentices adapting to that oven's quirks"},
                {"concept_element": "switching_cost", "narrative_carrier": "having to rebuild shelves, rewrite recipes, and retrain apprentices"},
                {"concept_element": "lock_in", "narrative_carrier": "the bakery can no longer work except around the old oven"},
                {"concept_element": "suboptimal_persistence", "narrative_carrier": "the newer brass oven stays outside while the smoky old oven remains"},
            ],
            "plot_beats": [
                {"beat_id": "b1", "event": "On opening day the baker buys the only oven he can afford.", "mapped_elements": ["initial_choice"]},
                {"beat_id": "b2", "event": "Recipes, shelves, and apprentice habits slowly form around its uneven heat.", "mapped_elements": ["reinforcing_feedback"]},
                {"beat_id": "b3", "event": "A better oven appears, but changing would require rebuilding the bakery's routines.", "mapped_elements": ["switching_cost"]},
                {"beat_id": "b4", "event": "The baker keeps the smoky oven because everything now depends on it.", "mapped_elements": ["lock_in", "suboptimal_persistence"]},
            ],
            "turning_point": "a merchant offers a cleaner brass oven at a fair price",
            "ending": "the brass oven leaves on the cart while the old oven smokes through another dawn",
            "implied_moral": "an early convenience can become a later cage",
        },
        STAGE_GENERATE: {
            "narrative": (
                "On the bakery's first market day, the baker bought the only oven he could afford, "
                "a squat iron one that burned hotter on the left than the right. Soon every loaf, shelf, "
                "and apprentice's hand learned its crooked temper. Years later a merchant brought a bright "
                "brass oven that used less wood and baked more evenly. The baker measured the doorway, the "
                "shelves, the recipes, and the apprentices' habits, then shut his purse. At dawn, the cart "
                "rolled away with the brass oven, while the old iron mouth coughed smoke and the village still queued for bread."
            )
        },
        STAGE_ALIGN: {
            "alignment": [
                {"concept_element": "initial_choice", "narrative_element": "buying the only oven he could afford on the first market day"},
                {"concept_element": "reinforcing_feedback", "narrative_element": "every loaf, shelf, and apprentice's hand learned its crooked temper"},
                {"concept_element": "switching_cost", "narrative_element": "measuring the doorway, shelves, recipes, and apprentices' habits before refusing the new oven"},
                {"concept_element": "lock_in", "narrative_element": "the bakery keeps working around the old iron oven"},
                {"concept_element": "suboptimal_persistence", "narrative_element": "the brass oven rolls away while the smoky old oven remains"},
            ]
        },
    },
    "overfitting": {
        STAGE_PLAN: {
            "source_domain": "a young tailor bird sewing cloaks for one grove",
            "setting": "a grove where each branch twists in the same familiar way",
            "conflict": "the tailor bird learns the old branches so exactly that it cannot dress any new tree",
            "characters": [
                {"name": "the tailor bird", "role": "maker that adapts too closely to familiar branches", "mapped_element": "fit_training_pattern"},
                {"name": "the old grove", "role": "familiar cases where the cloaks fit perfectly", "mapped_element": "high_seen_performance"},
                {"name": "the wind-bent orchard", "role": "new cases with different shapes", "mapped_element": "poor_generalization"},
            ],
            "mappings": [
                {"concept_element": "fit_training_pattern", "narrative_carrier": "sewing cloaks by memorizing every bend of the old grove"},
                {"concept_element": "high_seen_performance", "narrative_carrier": "each cloak fitting the old branches flawlessly"},
                {"concept_element": "poor_generalization", "narrative_carrier": "the same stitches failing on a differently shaped orchard"},
            ],
            "plot_beats": [
                {"beat_id": "b1", "event": "The tailor bird copies every bend and knot in the old grove.", "mapped_elements": ["fit_training_pattern"]},
                {"beat_id": "b2", "event": "Its cloaks fit those branches so well that the grove praises it.", "mapped_elements": ["high_seen_performance"]},
                {"beat_id": "b3", "event": "When asked to clothe a wind-bent orchard, every memorized stitch pulls the wrong way.", "mapped_elements": ["poor_generalization"]},
            ],
            "turning_point": "the bird is invited beyond the grove for the first time",
            "ending": "it carries a bag of perfect old patterns that fit nothing in the new orchard",
            "implied_moral": "learning the shell of old cases is not the same as learning what holds across cases",
        },
        STAGE_GENERATE: {
            "narrative": (
                "A young tailor bird made cloaks for the same grove every spring. It memorized each "
                "bend, knot, and fork, and its little garments hugged the old branches without a wrinkle. "
                "The grove rustled with praise. Then a storm-bent orchard asked for cloaks before winter. "
                "The bird opened its bag of perfect patterns, but every stitch tugged crookedly and every "
                "hem caught on an unfamiliar fork. By sunset it still held the finest patterns in the valley, "
                "and not one branch in the orchard was warm."
            )
        },
        STAGE_ALIGN: {
            "alignment": [
                {"concept_element": "fit_training_pattern", "narrative_element": "memorizing each bend, knot, and fork of the same grove"},
                {"concept_element": "high_seen_performance", "narrative_element": "cloaks hugging the old branches without a wrinkle"},
                {"concept_element": "poor_generalization", "narrative_element": "patterns failing on the storm-bent orchard's unfamiliar forks"},
            ]
        },
    },
}


class MockLLMClient:
    """根据 prompt 标签返回预设响应的离线 LLM。"""

    def __init__(self, knowledge: Dict[str, Dict] | None = None) -> None:
        self._knowledge = knowledge if knowledge is not None else _MOCK_KNOWLEDGE

    def complete(self, prompt: str, system: str | None = None) -> str:
        # Mock 按 prompt 标签分发，system 不影响离线预设；保留参数以满足协议。
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
