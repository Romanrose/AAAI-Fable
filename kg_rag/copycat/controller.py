from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.copycat.assembler import assemble_plan_from_structures
from kg_rag.copycat.artifacts import write_candidate_artifacts, write_workspace_artifacts
from kg_rag.copycat.codelets import build_copycat_structures, repair_leakage_story, run_diagnostic_codelets
from kg_rag.copycat.workspace import build_candidate_state, build_workspace


def build_copycat_plan(
    *,
    card: dict[str, Any],
    mechanism_graph: dict[str, Any],
    concept_relation_graph: dict[str, Any] | None = None,
    candidate_id: str,
    candidate_index: int,
    max_steps: int = 30,
) -> dict[str, Any]:
    structures, trace = build_copycat_structures(
        card=card,
        mechanism_graph=mechanism_graph,
        concept_relation_graph=concept_relation_graph or {},
        candidate_id=candidate_id,
        candidate_index=candidate_index,
        max_steps=max_steps,
    )
    plan = assemble_plan_from_structures(structures)
    return {
        "plan": plan,
        "structures": [structure.to_dict() for structure in structures],
        "codelet_trace": trace,
    }


def record_copycat_candidate(
    *,
    candidate_dir: Path,
    candidate: dict[str, Any],
    mechanism_graph: dict[str, Any],
) -> dict[str, Any]:
    state = build_candidate_state(candidate=candidate, mechanism_graph=mechanism_graph)
    write_candidate_artifacts(candidate_dir, state)
    return state.to_dict()


def repair_copycat_story(
    *,
    card: dict[str, Any],
    candidate_id: str,
    story: str,
) -> tuple[str, list[dict[str, Any]]]:
    return repair_leakage_story(card=card, candidate_id=candidate_id, story=story)


def run_copycat_diagnostics(
    *,
    card: dict[str, Any],
    candidate_id: str,
    story: str,
    alignment: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    return run_diagnostic_codelets(
        card=card,
        candidate_id=candidate_id,
        story=story,
        alignment=alignment,
        metrics=metrics,
    )


def record_copycat_workspace(
    *,
    concept_dir: Path,
    concept_id: str,
    mechanism_graph: dict[str, Any],
    candidates: list[dict[str, Any]],
    best_candidate_id: str | None,
) -> dict[str, Any]:
    workspace = build_workspace(
        concept_id=concept_id,
        mechanism_graph=mechanism_graph,
        candidates=candidates,
        best_candidate_id=best_candidate_id,
    )
    write_workspace_artifacts(concept_dir, workspace)
    trace_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        for phase, key in (
            ("structure_build", "copycat_codelet_trace"),
            ("repair", "copycat_repair_trace"),
            ("diagnostic", "copycat_check_trace"),
        ):
            for item in candidate.get(key, []):
                if not isinstance(item, dict):
                    continue
                trace_rows.append({"candidate_id": candidate_id, "phase": phase, **item})
    if trace_rows:
        write_jsonl(concept_dir / "codelet_trace.jsonl", trace_rows)
    return workspace.to_dict()
