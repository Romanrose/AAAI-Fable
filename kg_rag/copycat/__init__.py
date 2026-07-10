"""Copycat-inspired structure mapping primitives for the multi-agent pipeline."""

from kg_rag.copycat.assembler import assemble_plan_from_structures, assemble_plan_from_workspace
from kg_rag.copycat.coderack import CoderackItem, seed_coderack
from kg_rag.copycat.slipnet import SlipnetActivation, build_slipnet_state
from kg_rag.copycat.temperature import temperature_band, workspace_temperature
from kg_rag.copycat.workspace import (
    CopycatCandidateState,
    CopycatWorkspace,
    WorkspaceStructure,
    build_candidate_state,
    build_workspace,
)
from kg_rag.copycat.controller import build_copycat_plan
from kg_rag.copycat.decision import choose_copycat_candidate

__all__ = [
    "CoderackItem",
    "CopycatCandidateState",
    "CopycatWorkspace",
    "SlipnetActivation",
    "WorkspaceStructure",
    "assemble_plan_from_workspace",
    "assemble_plan_from_structures",
    "build_copycat_plan",
    "build_candidate_state",
    "build_slipnet_state",
    "build_workspace",
    "choose_copycat_candidate",
    "seed_coderack",
    "temperature_band",
    "workspace_temperature",
]
