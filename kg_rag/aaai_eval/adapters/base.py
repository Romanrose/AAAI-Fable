from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kg_rag.aaai_eval.schemas import EvaluationProtocol, MethodSpec


@dataclass(frozen=True)
class MethodRunContext:
    protocol: EvaluationProtocol
    method: MethodSpec
    dataset_row: dict[str, Any]
    method_output_dir: Path


class MethodAdapter(ABC):
    """Converts one method's output into standard evaluation records."""

    adapter_id: str

    def __init__(self, *, method: MethodSpec, base_dir: Path) -> None:
        self.method = method
        self.base_dir = base_dir

    @abstractmethod
    def run(self, context: MethodRunContext) -> list[dict[str, Any]]:
        raise NotImplementedError
