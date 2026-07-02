from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.generation.prompts import build_review_prompt, build_story_prompt
from kg_rag.generation.review_parse import parse_review_json
from kg_rag.generation.review import build_review_checklist
from kg_rag.io import write_json
from kg_rag.llm_client import LLMRequestError, chat_completion
from kg_rag.llm_config import LLMConfig
from kg_rag.prompts.assembler import build_mapping_prompt
from kg_rag.retrievers.context_pack import build_subgraph_pack
from kg_rag.retrievers.subgraph import preview_normalized_seed
from kg_rag.structure_mapping.planner import build_structure_plan


def run_llm_demo_pipeline(
    *,
    concept_name: str,
    normalized_graph_path: Path,
    output_dir: Path,
    config: LLMConfig,
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

    pack_path = output_dir / "subgraph_pack.json"
    plan_path = output_dir / "structure_plan.json"
    mapping_prompt_path = output_dir / "mapping_prompt.txt"
    story_prompt_path = output_dir / "story_prompt.txt"
    draft_path = output_dir / "draft_story.txt"
    review_prompt_path = output_dir / "review_prompt.txt"
    review_response_path = output_dir / "review_response.txt"
    review_json_path = output_dir / "review_response.json"
    checklist_path = output_dir / "review_checklist.json"
    error_path = output_dir / "error.json"

    write_json(pack_path, pack)
    write_json(plan_path, plan)
    mapping_prompt_path.write_text(mapping_prompt, encoding="utf-8")
    story_prompt_path.write_text(story_prompt, encoding="utf-8")

    try:
        draft = chat_completion(
            config=config,
            system_prompt="You are a precise educational fable writer.",
            user_prompt=story_prompt,
        )
        draft_path.write_text(draft, encoding="utf-8")

        review_prompt = build_review_prompt(plan, draft)
        review_prompt_path.write_text(review_prompt, encoding="utf-8")

        review = chat_completion(
            config=config,
            system_prompt="You are a strict reviewer of concept-grounded stories.",
            user_prompt=review_prompt,
        )
        review_response_path.write_text(review, encoding="utf-8")
        review_json = parse_review_json(review)
        write_json(review_json_path, review_json)

        checklist = build_review_checklist(plan, draft)
        write_json(checklist_path, checklist)
    except LLMRequestError as exc:
        error_payload = {
            "stage": "llm_request",
            "message": str(exc),
            "base_url": config.base_url,
            "model": config.model,
        }
        write_json(error_path, error_payload)
        checklist = {
            "pass_fail": False,
            "reason": "llm_request_failed",
            "error_path": str(error_path),
        }
        write_json(checklist_path, checklist)
        return {
            "draft_path": str(draft_path),
            "review_response_path": str(review_response_path),
            "review_json_path": str(review_json_path),
            "checklist_path": str(checklist_path),
            "error_path": str(error_path),
            "checklist": checklist,
        }

    return {
        "draft_path": str(draft_path),
        "review_response_path": str(review_response_path),
        "review_json_path": str(review_json_path),
        "checklist_path": str(checklist_path),
        "checklist": checklist,
    }
