from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CoderackItem:
    item_id: str
    codelet_type: str
    urgency: float
    temperature_sensitivity: float
    target_structure_id: str | None = None
    target_candidate_id: str | None = None
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "codelet_type": self.codelet_type,
            "urgency": round(max(0.0, min(1.0, self.urgency)), 4),
            "temperature_sensitivity": round(max(0.0, min(1.0, self.temperature_sensitivity)), 4),
            "target_structure_id": self.target_structure_id,
            "target_candidate_id": self.target_candidate_id,
            "reason": self.reason,
            "evidence": self.evidence,
        }


def adjusted_urgency(item: dict[str, Any], temperature: float) -> float:
    urgency = float(item.get("urgency") or 0.0)
    sensitivity = float(item.get("temperature_sensitivity") or 0.0)
    temperature_norm = max(0.0, min(1.0, temperature / 100.0))
    return round(urgency * (1.0 + sensitivity * temperature_norm), 6)


def rank_coderack_items(items: list[dict[str, Any]], temperature: float) -> list[dict[str, Any]]:
    ranked = []
    for item in items:
        payload = dict(item)
        payload["adjusted_urgency"] = adjusted_urgency(item, temperature)
        ranked.append(payload)
    return sorted(
        ranked,
        key=lambda item: (
            -float(item.get("adjusted_urgency") or 0.0),
            -float(item.get("urgency") or 0.0),
            str(item.get("codelet_type") or ""),
            str(item.get("item_id") or ""),
        ),
    )


def select_coderack_item(items: list[dict[str, Any]], temperature: float) -> dict[str, Any]:
    if not items:
        raise ValueError("select_coderack_item requires at least one item")
    return rank_coderack_items(items, temperature)[0]


def seed_structure_coderack(candidate_id: str) -> list[dict[str, Any]]:
    return [
        CoderackItem(
            item_id=f"{candidate_id}:build:001",
            codelet_type="BootstrapTargetConceptCodelet",
            urgency=0.9,
            temperature_sensitivity=0.65,
            target_candidate_id=candidate_id,
            reason="bootstrap target concept as the workspace subject",
        ).to_dict()
    ]


def followup_structure_items(
    *,
    candidate_id: str,
    completed_codelet: str,
    step: int,
) -> list[dict[str, Any]]:
    if completed_codelet == "BootstrapTargetConceptCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="ProposeSourceDomainCodelet",
                urgency=0.78,
                temperature_sensitivity=0.6,
                target_candidate_id=candidate_id,
                reason="target concept exists; choose a source domain",
            ).to_dict()
        ]
    if completed_codelet == "ProposeSourceDomainCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="BuildConceptRelationStructuresCodelet",
                urgency=0.86,
                temperature_sensitivity=0.5,
                target_candidate_id=candidate_id,
                reason="source domain exists; preserve typed GraphRAG concept relations",
            ).to_dict()
        ]
    if completed_codelet == "BuildConceptRelationStructuresCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="ExtractConceptRolesCodelet",
                urgency=0.84,
                temperature_sensitivity=0.5,
                target_candidate_id=candidate_id,
                reason="concept relations exist; extract target concept roles",
            ).to_dict()
        ]
    if completed_codelet == "ExtractConceptRolesCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="MapConceptRolesToSourceDomainCodelet",
                urgency=0.84,
                temperature_sensitivity=0.48,
                target_candidate_id=candidate_id,
                reason="concept roles exist; map them into the selected source domain",
            ).to_dict()
        ]
    if completed_codelet == "MapConceptRolesToSourceDomainCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="MapTypedRelationCodelet",
                urgency=0.86,
                temperature_sensitivity=0.55,
                target_candidate_id=candidate_id,
                reason="role correspondences exist; map typed concept relations to story relations",
            ).to_dict()
        ]
    if completed_codelet == "MapTypedRelationCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="ProposeNodeCorrespondenceCodelet",
                urgency=0.72,
                temperature_sensitivity=0.45,
                target_candidate_id=candidate_id,
                reason="typed relation mapping exists; add legacy mechanism-node correspondences",
            ).to_dict()
        ]
    if completed_codelet == "ProposeNodeCorrespondenceCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="ProposeEdgeCorrespondenceCodelet",
                urgency=0.86,
                temperature_sensitivity=0.55,
                target_candidate_id=candidate_id,
                reason="node correspondences exist; map mechanism edges to event relations",
            ).to_dict()
        ]
    if completed_codelet == "ProposeEdgeCorrespondenceCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 1:03d}",
                codelet_type="StrengthenEdgeCausalityCodelet",
                urgency=0.88,
                temperature_sensitivity=0.6,
                target_candidate_id=candidate_id,
                reason="edge correspondences exist; strengthen causal evidence before story assembly",
            ).to_dict(),
            CoderackItem(
                item_id=f"{candidate_id}:build:{step + 2:03d}",
                codelet_type="BuildEventChainFragmentCodelet",
                urgency=0.64,
                temperature_sensitivity=0.35,
                target_candidate_id=candidate_id,
                reason="edge correspondences exist; build narrative event-chain fragments",
            ).to_dict()
        ]
    if completed_codelet == "StrengthenEdgeCausalityCodelet":
        return [
            CoderackItem(
                item_id=f"{candidate_id}:repair_direction:{step + 1:03d}",
                codelet_type="RepairDirectionCodelet",
                urgency=0.7,
                temperature_sensitivity=0.45,
                target_candidate_id=candidate_id,
                reason="causal evidence exists; add a direction-preservation guard",
            ).to_dict()
        ]
    return []


PRESSURE_TO_CODELET = {
    "failure.leakage": ("RepairLeakageCodelet", "remove forbidden concept terms from the story"),
    "failure.low_node_coverage": ("ProposeNodeCorrespondenceCodelet", "add missing mechanism-node correspondences"),
    "failure.low_edge_coverage": ("ProposeEdgeCorrespondenceCodelet", "strengthen mechanism-edge causal mapping"),
    "failure.direction_error": ("RepairDirectionCodelet", "repair reversed story event order"),
    "failure.weak_alignment": ("RealignEvidenceCodelet", "ground alignment evidence in story text"),
    "failure.template_like": ("ProposeAlternativeSourceDomainCodelet", "replace template-like source domain"),
}


def seed_coderack(candidate_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Seed a deterministic coderack from dominant slipnet pressures."""
    candidate_id = str(candidate_state.get("candidate_id") or "")
    temperature = float(candidate_state.get("temperature") or 100.0)
    items: list[CoderackItem] = []
    pressures = candidate_state.get("slipnet_state", {}).get("activations", [])
    ranked_pressures = sorted(
        [pressure for pressure in pressures if isinstance(pressure, dict)],
        key=lambda pressure: (-float(pressure.get("activation") or 0.0), str(pressure.get("node_id") or "")),
    )
    for index, pressure in enumerate(ranked_pressures, start=1):
        node_id = str(pressure.get("node_id") or "")
        if node_id not in PRESSURE_TO_CODELET:
            continue
        codelet_type, reason = PRESSURE_TO_CODELET[node_id]
        activation = float(pressure.get("activation") or 0.0)
        sensitivity = 0.8 if temperature > 55.0 else 0.45 if temperature > 25.0 else 0.2
        items.append(
            CoderackItem(
                item_id=f"{candidate_id}:coderack:{index:03d}",
                codelet_type=codelet_type,
                urgency=max(0.05, min(1.0, activation)),
                temperature_sensitivity=sensitivity,
                target_candidate_id=candidate_id,
                reason=reason,
                evidence=pressure.get("evidence", {}) if isinstance(pressure.get("evidence"), dict) else {},
            )
        )

    if not items:
        items.append(
            CoderackItem(
                item_id=f"{candidate_id}:coderack:001",
                codelet_type="EvaluateStructureStrengthCodelet",
                urgency=0.25,
                temperature_sensitivity=0.2,
                target_candidate_id=candidate_id,
                reason="candidate has no dominant failure pressure",
            )
        )
    return [item.to_dict() for item in items]
