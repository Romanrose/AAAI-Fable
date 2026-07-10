from __future__ import annotations

from typing import Any


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _boolish(value: Any) -> bool:
    return bool(_float(value)) if isinstance(value, (int, float, str)) else bool(value)


def _normalized_overall(six_dim_eval: dict[str, Any]) -> float:
    overall = _float(six_dim_eval.get("weighted_overall"), 0.0)
    if overall > 1.0:
        return min(1.0, overall / 5.0)
    return max(0.0, min(1.0, overall))


def _direction_accuracy(metrics: dict[str, Any]) -> float:
    direction = metrics.get("relation_direction_accuracy")
    if direction is None:
        return 1.0
    return max(0.0, min(1.0, _float(direction, 1.0)))


def workspace_temperature(
    metrics: dict[str, Any],
    six_dim_eval: dict[str, Any] | None = None,
    *,
    average_structure_strength: float | None = None,
) -> float:
    """Return a Copycat-style workspace instability score in [0, 100]."""
    six_dim_eval = six_dim_eval or {}
    hard_flags = six_dim_eval.get("hard_flags", {}) if isinstance(six_dim_eval.get("hard_flags"), dict) else {}
    temperature = 100.0
    temperature -= 20.0 * max(0.0, min(1.0, _float(metrics.get("weighted_node_coverage"))))
    temperature -= 18.0 * max(0.0, min(1.0, _float(metrics.get("weighted_edge_coverage"))))
    temperature -= 16.0 * max(0.0, min(1.0, _float(metrics.get("alignment_precision"))))
    temperature -= 12.0 * _direction_accuracy(metrics)
    temperature -= 10.0 * _normalized_overall(six_dim_eval)

    if average_structure_strength is not None:
        temperature -= 5.0 * max(0.0, min(1.0, average_structure_strength))

    if _boolish(metrics.get("exact_concept_leakage")):
        temperature += 35.0
    if _boolish(metrics.get("soft_term_leakage")):
        temperature += 18.0
    temperature += 15.0 * max(0.0, min(1.0, _float(metrics.get("template_hit_rate"))))
    if hard_flags.get("unmapped_core_mechanism"):
        temperature += 20.0
    if hard_flags.get("concept_contradiction"):
        temperature += 20.0

    return round(max(0.0, min(100.0, temperature)), 2)


def temperature_band(temperature: float) -> str:
    if temperature <= 25.0:
        return "stable"
    if temperature <= 55.0:
        return "repairable"
    if temperature <= 80.0:
        return "unstable"
    return "chaotic"
