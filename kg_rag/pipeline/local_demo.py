from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.generation.prompts import build_review_prompt, build_story_prompt
from kg_rag.generation.review import build_review_checklist
from kg_rag.generation.writer import build_heuristic_draft
from kg_rag.io import write_json
from kg_rag.prompts.assembler import build_mapping_prompt
from kg_rag.retrievers.context_pack import build_subgraph_pack
from kg_rag.retrievers.subgraph import preview_normalized_seed
from kg_rag.structure_mapping.planner import build_structure_plan


def run_local_demo_pipeline(
    *,
    concept_name: str,
    normalized_graph_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    subgraph = preview_normalized_seed(
        normalized_graph_path=normalized_graph_path,
        concept_name=concept_name,
    )
    pack = build_subgraph_pack(subgraph)
    plan = build_structure_plan(pack)
    mapping_prompt = build_mapping_prompt(pack)
    story_prompt = build_story_prompt(plan)
    draft = build_heuristic_draft(plan)
    review_prompt = build_review_prompt(plan, draft)
    checklist = build_review_checklist(plan, draft)

    pack_path = output_dir / "subgraph_pack.json"
    plan_path = output_dir / "structure_plan.json"
    mapping_prompt_path = output_dir / "mapping_prompt.txt"
    story_prompt_path = output_dir / "story_prompt.txt"
    draft_path = output_dir / "draft_story.txt"
    review_prompt_path = output_dir / "review_prompt.txt"
    checklist_path = output_dir / "review_checklist.json"

    write_json(pack_path, pack)
    write_json(plan_path, plan)
    mapping_prompt_path.write_text(mapping_prompt, encoding="utf-8")
    story_prompt_path.write_text(story_prompt, encoding="utf-8")
    draft_path.write_text(draft, encoding="utf-8")
    review_prompt_path.write_text(review_prompt, encoding="utf-8")
    write_json(checklist_path, checklist)

    return {
        "pack_path": str(pack_path),
        "plan_path": str(plan_path),
        "mapping_prompt_path": str(mapping_prompt_path),
        "story_prompt_path": str(story_prompt_path),
        "draft_path": str(draft_path),
        "review_prompt_path": str(review_prompt_path),
        "checklist_path": str(checklist_path),
        "checklist": checklist,
    }
