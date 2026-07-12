"""Extensible evaluation framework for the M2NA AAAI experiments."""

from kg_rag.aaai_eval.registry import AdapterRegistry, default_registry
from kg_rag.aaai_eval.schemas import EvaluationProtocol, MethodSpec

__all__ = ["AdapterRegistry", "EvaluationProtocol", "MethodSpec", "default_registry"]
