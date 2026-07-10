from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.io import write_json
from kg_rag.copycat.coderack import seed_coderack
from kg_rag.copycat.workspace import CopycatCandidateState, CopycatWorkspace


def write_candidate_artifacts(candidate_dir: Path, state: CopycatCandidateState) -> None:
    payload = state.to_dict()
    payload["coderack"] = seed_coderack(payload)
    write_json(candidate_dir / "copycat_state.json", payload)


def write_workspace_artifacts(concept_dir: Path, workspace: CopycatWorkspace) -> None:
    payload = workspace.to_dict()
    write_json(concept_dir / "copycat_workspace.json", payload)
    write_json(
        concept_dir / "slipnet_activations.json",
        {
            "concept_id": workspace.concept_id,
            "candidates": [
                {
                    "candidate_id": candidate.candidate_id,
                    "slipnet_state": candidate.slipnet_state,
                }
                for candidate in workspace.candidates
            ],
        },
    )
    write_json(
        concept_dir / "coderack.final.json",
        {
            "concept_id": workspace.concept_id,
            "items": [
                item
                for candidate in workspace.candidates
                for item in seed_coderack(candidate.to_dict())
            ],
        },
    )
    write_jsonl(
        concept_dir / "temperature_trace.jsonl",
        [
            {
                "candidate_id": candidate.candidate_id,
                "temperature": candidate.temperature,
                "temperature_band": candidate.temperature_band,
                "copycat_score": candidate.copycat_score,
            }
            for candidate in workspace.candidates
        ],
    )
