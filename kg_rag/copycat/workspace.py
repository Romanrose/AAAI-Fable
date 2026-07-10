from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kg_rag.copycat.slipnet import build_slipnet_state
from kg_rag.copycat.temperature import temperature_band, workspace_temperature


@dataclass(frozen=True)
class WorkspaceStructure:
    structure_id: str
    structure_type: str
    content: dict[str, Any]
    strength: float
    salience: float
    support: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    created_by_codelet: str = "bootstrap_from_plan"
    candidate_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure_id": self.structure_id,
            "structure_type": self.structure_type,
            "content": self.content,
            "strength": round(max(0.0, min(1.0, self.strength)), 4),
            "salience": round(max(0.0, min(1.0, self.salience)), 4),
            "support": self.support,
            "conflicts": self.conflicts,
            "created_by_codelet": self.created_by_codelet,
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True)
class CopycatCandidateState:
    candidate_id: str
    structures: list[WorkspaceStructure]
    slipnet_state: dict[str, Any]
    temperature: float
    temperature_band: str
    copycat_score: float
    failure_summary: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "structures": [structure.to_dict() for structure in self.structures],
            "slipnet_state": self.slipnet_state,
            "temperature": self.temperature,
            "temperature_band": self.temperature_band,
            "copycat_score": self.copycat_score,
            "failure_summary": self.failure_summary,
        }


@dataclass(frozen=True)
class CopycatWorkspace:
    concept_id: str
    target_domain: dict[str, Any]
    candidates: list[CopycatCandidateState]
    best_candidate_id: str | None
    workspace_temperature: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "target_domain": self.target_domain,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "best_candidate_id": self.best_candidate_id,
            "workspace_temperature": self.workspace_temperature,
        }


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _strength_from_metric(metrics: dict[str, Any], key: str, default: float = 0.55) -> float:
    value = metrics.get(key)
    if value is None:
        return default
    return max(0.0, min(1.0, _float(value, default)))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def structures_from_plan(
    *,
    candidate_id: str,
    plan: dict[str, Any],
    mechanism_graph: dict[str, Any],
    alignment: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> list[WorkspaceStructure]:
    metrics = metrics or {}
    alignment = alignment or {}
    structures: list[WorkspaceStructure] = []
    source_domain = plan.get("source_domain")
    if source_domain:
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:source_domain:001",
                structure_type="SourceDomainStructure",
                content={"source_domain": source_domain},
                strength=0.72,
                salience=0.8,
                support=["narrative_plan.source_domain"],
                candidate_id=candidate_id,
            )
        )

    for index, item in enumerate(_list(plan.get("mapping_plan")), start=1):
        if not isinstance(item, dict):
            continue
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:node_correspondence:{index:03d}",
                structure_type="NodeCorrespondence",
                content={
                    "mechanism_node_id": item.get("mechanism_node_id"),
                    "mechanism_text": item.get("mechanism_text"),
                    "narrative_carrier": item.get("story_role") or item.get("narrative_carrier"),
                },
                strength=_strength_from_metric(metrics, "weighted_node_coverage", 0.6),
                salience=0.85,
                support=["narrative_plan.mapping_plan"],
                candidate_id=candidate_id,
            )
        )

    event_chain = [str(event) for event in _list(plan.get("event_chain"))]
    for index, edge in enumerate(_list(mechanism_graph.get("edges")), start=1):
        if not isinstance(edge, dict):
            continue
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:edge_correspondence:{index:03d}",
                structure_type="EdgeCorrespondence",
                content={
                    "mechanism_edge_id": edge.get("id"),
                    "source": edge.get("source"),
                    "target": edge.get("target"),
                    "relation": edge.get("relation"),
                    "event_evidence": event_chain[min(index, len(event_chain)) - 1] if event_chain else None,
                },
                strength=_strength_from_metric(metrics, "weighted_edge_coverage", 0.5),
                salience=0.9,
                support=["mechanism_graph.edges", "narrative_plan.event_chain"],
                candidate_id=candidate_id,
            )
        )

    for index, event in enumerate(event_chain, start=1):
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:event_fragment:{index:03d}",
                structure_type="EventChainFragment",
                content={"event": event, "position": index},
                strength=0.65,
                salience=0.7,
                support=["narrative_plan.event_chain"],
                candidate_id=candidate_id,
            )
        )

    for key, structure_type in (
        ("conflict", "ConflictStructure"),
        ("turning_point", "TurningPointStructure"),
        ("resolution_state", "ResolutionStructure"),
    ):
        if plan.get(key):
            structures.append(
                WorkspaceStructure(
                    structure_id=f"{candidate_id}:{key}:001",
                    structure_type=structure_type,
                    content={key: plan[key]},
                    strength=0.62,
                    salience=0.62,
                    support=[f"narrative_plan.{key}"],
                    candidate_id=candidate_id,
                )
            )

    evidence_index = 1
    for bucket in ("node_alignments", "edge_alignments"):
        for item in _list(alignment.get(bucket)):
            if not isinstance(item, dict) or not item.get("evidence"):
                continue
            structures.append(
                WorkspaceStructure(
                    structure_id=f"{candidate_id}:alignment_evidence:{evidence_index:03d}",
                    structure_type="AlignmentEvidence",
                    content={
                        "alignment_type": bucket,
                        "concept_id": item.get("concept_node_id") or item.get("concept_edge_id"),
                        "evidence": item.get("evidence"),
                    },
                    strength=_strength_from_metric(metrics, "alignment_precision", 0.55),
                    salience=0.76,
                    support=["alignment"],
                    candidate_id=candidate_id,
                )
            )
            evidence_index += 1

    return structures


def _structure_from_payload(payload: dict[str, Any]) -> WorkspaceStructure:
    return WorkspaceStructure(
        structure_id=str(payload.get("structure_id") or ""),
        structure_type=str(payload.get("structure_type") or "UnknownStructure"),
        content=payload.get("content", {}) if isinstance(payload.get("content"), dict) else {},
        strength=_float(payload.get("strength"), 0.5),
        salience=_float(payload.get("salience"), 0.5),
        support=[str(item) for item in _list(payload.get("support"))],
        conflicts=[str(item) for item in _list(payload.get("conflicts"))],
        created_by_codelet=str(payload.get("created_by_codelet") or "unknown"),
        candidate_id=str(payload.get("candidate_id") or ""),
    )


def _average_strength(structures: list[WorkspaceStructure]) -> float:
    if not structures:
        return 0.0
    return sum(structure.strength for structure in structures) / len(structures)


def _copycat_score(temperature: float, metrics: dict[str, Any], structures: list[WorkspaceStructure]) -> float:
    score = (
        1.0
        - temperature / 100.0
        + 0.25 * _strength_from_metric(metrics, "weighted_node_coverage")
        + 0.25 * _strength_from_metric(metrics, "weighted_edge_coverage")
        + 0.20 * _strength_from_metric(metrics, "alignment_precision")
        + 0.12 * _strength_from_metric(metrics, "concept_relation_coverage")
        + 0.12 * _strength_from_metric(metrics, "typed_relation_preservation")
        + 0.10 * _average_strength(structures)
    )
    return round(max(0.0, score), 4)


def _failure_summary(slipnet_state: dict[str, Any]) -> list[str]:
    return [
        str(node_id)
        for node_id in slipnet_state.get("dominant_pressures", [])
        if str(node_id).startswith("failure.")
    ]


def build_candidate_state(
    *,
    candidate: dict[str, Any],
    mechanism_graph: dict[str, Any],
) -> CopycatCandidateState:
    metrics = candidate.get("automatic_metrics", {})
    six_dim_eval = candidate.get("six_dim_eval", {})
    raw_copycat_structures = candidate.get("copycat_structures")
    if isinstance(raw_copycat_structures, list) and raw_copycat_structures:
        structures = [
            _structure_from_payload(structure)
            for structure in raw_copycat_structures
            if isinstance(structure, dict)
        ]
        alignment_structures = [
            structure
            for structure in structures_from_plan(
                candidate_id=str(candidate["candidate_id"]),
                plan=candidate.get("plan", {}),
                mechanism_graph=mechanism_graph,
                alignment=candidate.get("alignment", {}),
                metrics=metrics,
            )
            if structure.structure_type == "AlignmentEvidence"
        ]
        structures.extend(alignment_structures)
    else:
        structures = structures_from_plan(
            candidate_id=str(candidate["candidate_id"]),
            plan=candidate.get("plan", {}),
            mechanism_graph=mechanism_graph,
            alignment=candidate.get("alignment", {}),
            metrics=metrics,
        )
    temperature = workspace_temperature(
        metrics,
        six_dim_eval,
        average_structure_strength=_average_strength(structures),
    )
    slipnet_state = build_slipnet_state(metrics, six_dim_eval)
    return CopycatCandidateState(
        candidate_id=str(candidate["candidate_id"]),
        structures=structures,
        slipnet_state=slipnet_state,
        temperature=temperature,
        temperature_band=temperature_band(temperature),
        copycat_score=_copycat_score(temperature, metrics, structures),
        failure_summary=_failure_summary(slipnet_state),
    )


def build_workspace(
    *,
    concept_id: str,
    mechanism_graph: dict[str, Any],
    candidates: list[dict[str, Any]],
    best_candidate_id: str | None = None,
) -> CopycatWorkspace:
    candidate_states = [
        build_candidate_state(candidate=candidate, mechanism_graph=mechanism_graph)
        for candidate in candidates
    ]
    if best_candidate_id is None and candidate_states:
        best_candidate_id = max(
            candidate_states,
            key=lambda candidate: (candidate.copycat_score, -candidate.temperature, candidate.candidate_id),
        ).candidate_id
    avg_temperature = (
        sum(candidate.temperature for candidate in candidate_states) / len(candidate_states)
        if candidate_states
        else 100.0
    )
    return CopycatWorkspace(
        concept_id=concept_id,
        target_domain={
            "mechanism_graph_source": mechanism_graph.get("source"),
            "node_count": len(_list(mechanism_graph.get("nodes"))),
            "edge_count": len(_list(mechanism_graph.get("edges"))),
        },
        candidates=candidate_states,
        best_candidate_id=best_candidate_id,
        workspace_temperature=round(avg_temperature, 2),
    )
