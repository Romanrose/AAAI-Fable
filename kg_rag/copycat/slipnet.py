from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SlipnetActivation:
    node_id: str
    node_type: str
    activation: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "activation": round(max(0.0, min(1.0, self.activation)), 4),
            "evidence": self.evidence,
        }


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _add_activation(
    activations: list[SlipnetActivation],
    *,
    node_id: str,
    node_type: str,
    activation: float,
    evidence: dict[str, Any],
) -> None:
    activations.append(
        SlipnetActivation(
            node_id=node_id,
            node_type=node_type,
            activation=max(0.0, min(1.0, activation)),
            evidence=evidence,
        )
    )


def build_slipnet_state(metrics: dict[str, Any], six_dim_eval: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a small activation network from current mapping/evaluation signals."""
    six_dim_eval = six_dim_eval or {}
    scores = six_dim_eval.get("scores", {}) if isinstance(six_dim_eval.get("scores"), dict) else {}
    hard_flags = six_dim_eval.get("hard_flags", {}) if isinstance(six_dim_eval.get("hard_flags"), dict) else {}
    activations: list[SlipnetActivation] = []

    if _float(metrics.get("exact_concept_leakage")) or _float(metrics.get("soft_term_leakage")):
        _add_activation(
            activations,
            node_id="failure.leakage",
            node_type="FailurePattern",
            activation=1.0 if _float(metrics.get("exact_concept_leakage")) else 0.7,
            evidence={
                "exact_concept_leakage": metrics.get("exact_concept_leakage"),
                "soft_term_leakage": metrics.get("soft_term_leakage"),
            },
        )

    node_cov = _float(metrics.get("weighted_node_coverage"))
    if node_cov < 0.7:
        _add_activation(
            activations,
            node_id="failure.low_node_coverage",
            node_type="FailurePattern",
            activation=1.0 - node_cov,
            evidence={"weighted_node_coverage": node_cov},
        )

    edge_cov = _float(metrics.get("weighted_edge_coverage"))
    if edge_cov < 0.7:
        _add_activation(
            activations,
            node_id="failure.low_edge_coverage",
            node_type="FailurePattern",
            activation=1.0 - edge_cov,
            evidence={"weighted_edge_coverage": edge_cov},
        )
        _add_activation(
            activations,
            node_id="relation.causal_chain",
            node_type="RelationConcept",
            activation=min(1.0, 1.0 - edge_cov + 0.2),
            evidence={"weighted_edge_coverage": edge_cov},
        )

    direction = metrics.get("relation_direction_accuracy")
    if direction is not None and _float(direction, 1.0) < 0.75:
        _add_activation(
            activations,
            node_id="failure.direction_error",
            node_type="FailurePattern",
            activation=1.0 - _float(direction),
            evidence={"relation_direction_accuracy": direction},
        )

    precision = _float(metrics.get("alignment_precision"))
    if precision < 0.75:
        _add_activation(
            activations,
            node_id="failure.weak_alignment",
            node_type="FailurePattern",
            activation=1.0 - precision,
            evidence={"alignment_precision": precision},
        )

    template_rate = _float(metrics.get("template_hit_rate"))
    if template_rate > 0.0 or hard_flags.get("template_like"):
        _add_activation(
            activations,
            node_id="failure.template_like",
            node_type="FailurePattern",
            activation=max(0.3, min(1.0, template_rate if template_rate else 0.8)),
            evidence={"template_hit_rate": template_rate, "template_like": hard_flags.get("template_like")},
        )

    for dimension in ("faithfulness", "mapping_clarity", "implicitness", "pedagogical_value", "novelty"):
        score = _float(scores.get(dimension), 5.0)
        if score < 4.0:
            _add_activation(
                activations,
                node_id=f"rubric.{dimension}",
                node_type="RubricDimension",
                activation=(4.0 - score) / 3.0,
                evidence={dimension: score},
            )

    dominant = [
        item.node_id
        for item in sorted(activations, key=lambda activation: (-activation.activation, activation.node_id))[:5]
    ]
    return {
        "activations": [activation.to_dict() for activation in activations],
        "dominant_pressures": dominant,
    }
