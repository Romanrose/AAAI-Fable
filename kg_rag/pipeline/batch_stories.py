from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kg_rag.generation.prompts import build_review_prompt, build_story_prompt
from kg_rag.generation.review import build_review_checklist
from kg_rag.generation.review_parse import parse_review_json
from kg_rag.generation.writer import build_heuristic_draft
from kg_rag.io import read_json, write_json
from kg_rag.llm_client import LLMRequestError, chat_completion
from kg_rag.llm_config import LLMConfig
from kg_rag.prompts.assembler import build_mapping_prompt
from kg_rag.retrievers.context_pack import build_subgraph_pack
from kg_rag.retrievers.subgraph import preview_normalized_seed
from kg_rag.structure_mapping.planner import build_structure_plan


@dataclass(frozen=True)
class BatchOptions:
    mode: str
    label: str
    subject: str | None
    limit: int | None
    offset: int
    sleep_seconds: float
    retry: int
    resume: bool


def _safe_dir_name(value: str) -> str:
    safe = []
    for char in value:
        if char.isalnum() or char in ("-", "_"):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("_") or "concept"


def _select_concepts(
    normalized_graph_path: Path,
    *,
    label: str,
    subject: str | None,
    limit: int | None,
    offset: int,
) -> list[dict[str, Any]]:
    payload = read_json(normalized_graph_path)
    concepts = [node for node in payload["nodes"] if node.get("label") == label]
    if subject:
        subject_prefix = f"{subject}_"
        concepts = [node for node in concepts if str(node.get("id", "")).startswith(subject_prefix)]
    concepts = concepts[offset:]
    if limit is not None:
        concepts = concepts[:limit]
    return concepts


def _write_summary_line(summary_path: Path, row: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _run_one_concept(
    *,
    concept: dict[str, Any],
    normalized_graph_path: Path,
    output_dir: Path,
    mode: str,
    config: LLMConfig | None,
    retry: int,
) -> dict[str, Any]:
    concept_id = concept["id"]
    concept_name = concept["name"]
    concept_dir = output_dir / "concepts" / _safe_dir_name(concept_id)
    concept_dir.mkdir(parents=True, exist_ok=True)

    pack_path = concept_dir / "subgraph_pack.json"
    plan_path = concept_dir / "structure_plan.json"
    story_prompt_path = concept_dir / "story_prompt.txt"
    draft_path = concept_dir / "draft_story.txt"
    review_prompt_path = concept_dir / "review_prompt.txt"
    review_response_path = concept_dir / "review_response.txt"
    review_json_path = concept_dir / "review_response.json"
    checklist_path = concept_dir / "review_checklist.json"
    error_path = concept_dir / "error.json"

    try:
        subgraph = preview_normalized_seed(normalized_graph_path=normalized_graph_path, concept_name=concept_id)
        pack = build_subgraph_pack(subgraph)
        plan = build_structure_plan(pack)
        mapping_prompt = build_mapping_prompt(pack)
        story_prompt = build_story_prompt(plan)

        write_json(pack_path, pack)
        write_json(plan_path, plan)
        (concept_dir / "mapping_prompt.txt").write_text(mapping_prompt, encoding="utf-8")
        story_prompt_path.write_text(story_prompt, encoding="utf-8")

        if mode == "local":
            draft = build_heuristic_draft(plan)
        else:
            if config is None:
                raise ValueError("LLM mode requires an LLMConfig.")
            last_error: Exception | None = None
            for attempt in range(retry + 1):
                try:
                    draft = chat_completion(
                        config=config,
                        system_prompt="You are a precise educational fable writer.",
                        user_prompt=story_prompt,
                    )
                    break
                except LLMRequestError as exc:
                    last_error = exc
                    if attempt >= retry:
                        raise
                    time.sleep(min(2 ** attempt, 10))
            else:
                raise last_error or RuntimeError("Unknown LLM request failure.")

        draft_path.write_text(draft, encoding="utf-8")
        review_prompt = build_review_prompt(plan, draft)
        review_prompt_path.write_text(review_prompt, encoding="utf-8")

        review_json = None
        if mode == "llm":
            assert config is not None
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

        return {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "status": "success",
            "mode": mode,
            "output_dir": str(concept_dir),
            "local_pass_fail": checklist.get("pass_fail"),
            "review_pass_fail": review_json.get("pass_fail") if review_json else None,
            "draft_length": checklist.get("draft_length"),
        }
    except Exception as exc:
        error_payload = {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        write_json(error_path, error_payload)
        return {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "status": "failed",
            "mode": mode,
            "output_dir": str(concept_dir),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }


def run_batch_stories(
    *,
    normalized_graph_path: Path,
    output_dir: Path,
    options: BatchOptions,
    config: LLMConfig | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    concepts = _select_concepts(
        normalized_graph_path,
        label=options.label,
        subject=options.subject,
        limit=options.limit,
        offset=options.offset,
    )
    manifest = {
        "mode": options.mode,
        "label": options.label,
        "subject": options.subject,
        "limit": options.limit,
        "offset": options.offset,
        "sleep_seconds": options.sleep_seconds,
        "retry": options.retry,
        "resume": options.resume,
        "concept_count": len(concepts),
        "normalized_graph_path": str(normalized_graph_path),
    }
    write_json(output_dir / "manifest.json", manifest)

    summary_path = output_dir / "summary.jsonl"
    if summary_path.exists() and not options.resume:
        summary_path.unlink()

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for concept in concepts:
        concept_dir = output_dir / "concepts" / _safe_dir_name(concept["id"])
        checklist_path = concept_dir / "review_checklist.json"
        if options.resume and checklist_path.exists():
            row = {
                "concept_id": concept["id"],
                "concept_name": concept["name"],
                "status": "skipped",
                "reason": "existing_outputs",
                "output_dir": str(concept_dir),
            }
            skipped_count += 1
            _write_summary_line(summary_path, row)
            continue

        row = _run_one_concept(
            concept=concept,
            normalized_graph_path=normalized_graph_path,
            output_dir=output_dir,
            mode=options.mode,
            config=config,
            retry=options.retry,
        )
        if row["status"] == "success":
            success_count += 1
        else:
            failed_count += 1
        _write_summary_line(summary_path, row)
        if options.sleep_seconds > 0:
            time.sleep(options.sleep_seconds)

    result = {
        "summary_path": str(summary_path),
        "manifest_path": str(output_dir / "manifest.json"),
        "concept_count": len(concepts),
        "success_count": success_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
    }
    write_json(output_dir / "run_result.json", result)
    return result
