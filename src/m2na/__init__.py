"""M2NA: Mechanism-to-Narrative Analogy Generation (初版第二部分：agent 架构)。"""

from .agents.llm import LLMClient, MockLLMClient
from .agents.pipeline import M2NAPipeline
from .types import M2NAInput, M2NAResult

__all__ = [
    "M2NAInput",
    "M2NAResult",
    "M2NAPipeline",
    "LLMClient",
    "MockLLMClient",
]
