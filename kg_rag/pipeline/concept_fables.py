from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import append_jsonl, read_jsonl, write_jsonl
from kg_rag.concepts.prompts import (
    STORY_SYSTEM_PROMPT,
    build_chinese_story_prompt,
    build_chinese_structure_plan,
    build_local_chinese_story,
)
from kg_rag.concepts.quality import chinese_char_ratio, safe_dir_name
from kg_rag.evaluation.pipeline import evaluate_story_dir
from kg_rag.evaluation.report import export_reports
from kg_rag.io import write_json
from kg_rag.llm_client import LLMRequestError, chat_completion
from kg_rag.llm_config import LLMConfig


@dataclass(frozen=True)
class ConceptFableOptions:
    mode: str
    language: str
    subject: str | None
    priority: str | None
    limit: int | None
    offset: int
    batch_size: int
    retry: int
    sleep_seconds: float
    resume: bool
    evaluate_mode: str


def _filter_cards(cards: list[dict[str, Any]], options: ConceptFableOptions) -> list[dict[str, Any]]:
    filtered = cards
    if options.subject:
        filtered = [card for card in filtered if card.get("subject") == options.subject]
    if options.priority:
        priorities = {item.strip() for item in options.priority.split(",") if item.strip()}
        filtered = [card for card in filtered if card.get("data_quality", {}).get("generation_priority") in priorities]
    filtered = filtered[options.offset :]
    if options.limit is not None:
        filtered = filtered[: options.limit]
    return filtered


def _subgraph_pack_from_card(card: dict[str, Any]) -> dict[str, Any]:
    context = card.get("graph_context", {})
    return {
        "query": card["concept_id"],
        "found": True,
        "seed": {
            "id": card["concept_id"],
            "label": "Concept",
            "name": card.get("canonical_name"),
            "definition": card.get("definition"),
            "aliases": card.get("aliases", []),
            "examples": card.get("examples", []),
            "retrieval_text": "\n".join(
                item for item in [card.get("canonical_name"), card.get("definition")] if item
            ),
        },
        "sections": {
            "prerequisites": context.get("prerequisites", []),
            "related_concepts": context.get("related_concepts", []),
            "outcomes": context.get("outcomes", []),
            "experiments": context.get("experiments", []),
            "exercises": context.get("exercises", []),
            "hierarchy": context.get("hierarchy", []),
        },
        "context_blocks": [],
        "meta": {
            "source": "concept_card",
            "story_language": card.get("story_language", "zh-CN"),
        },
    }


def _write_status(concept_dir: Path, payload: dict[str, Any]) -> None:
    write_json(concept_dir / "status.json", payload)


def _call_story_llm(*, config: LLMConfig, prompt: str, retry: int) -> str:
    last_error: Exception | None = None
    for attempt in range(retry + 1):
        try:
            return chat_completion(
                config=config,
                system_prompt=STORY_SYSTEM_PROMPT,
                user_prompt=prompt,
            )
        except LLMRequestError as exc:
            last_error = exc
            if attempt >= retry:
                raise
            time.sleep(min(2**attempt, 10))
    raise last_error or RuntimeError("Unknown LLM request failure.")


def run_concept_fable_batch(
    *,
    concept_cards_path: Path,
    output_dir: Path,
    options: ConceptFableOptions,
    config: LLMConfig | None = None,
) -> dict[str, Any]:
    if options.language != "zh-CN":
        raise ValueError("The first-stage concept fable runner currently supports only zh-CN.")
    if options.mode == "llm" and config is None:
        raise ValueError("LLM generation mode requires an LLMConfig.")

    output_dir.mkdir(parents=True, exist_ok=True)
    cards = _filter_cards(read_jsonl(concept_cards_path), options)
    write_jsonl(output_dir / "concept_cards.jsonl", cards)
    manifest = {
        "concept_cards_path": str(concept_cards_path),
        "output_dir": str(output_dir),
        "mode": options.mode,
        "language": options.language,
        "subject": options.subject,
        "priority": options.priority,
        "limit": options.limit,
        "offset": options.offset,
        "batch_size": options.batch_size,
        "retry": options.retry,
        "resume": options.resume,
        "evaluate_mode": options.evaluate_mode,
        "concept_count": len(cards),
    }
    write_json(output_dir / "manifest.json", manifest)

    summary_path = output_dir / "summary.jsonl"
    failed_queue_path = output_dir / "failed_queue.jsonl"
    if not options.resume:
        for path in (summary_path, failed_queue_path, output_dir / "eval_summary.jsonl"):
            if path.exists():
                path.unlink()

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for index, card in enumerate(cards, start=1):
        concept_id = card["concept_id"]
        subject = card.get("subject", "unknown")
        concept_dir = output_dir / "concepts" / safe_dir_name(concept_id)
        draft_path = concept_dir / "draft_story.txt"
        eval_path = concept_dir / "six_dim_eval.json"

        if options.resume and draft_path.exists() and eval_path.exists():
            skipped_count += 1
            row = {
                "concept_id": concept_id,
                "subject": subject,
                "status": "skipped",
                "reason": "existing_outputs",
                "output_dir": str(concept_dir),
            }
            append_jsonl(summary_path, row)
            continue

        concept_dir.mkdir(parents=True, exist_ok=True)
        try:
            plan = build_chinese_structure_plan(card)
            subgraph_pack = _subgraph_pack_from_card(card)
            story_prompt = build_chinese_story_prompt(card, plan)
            write_json(concept_dir / "concept_card.json", card)
            write_json(concept_dir / "subgraph_pack.json", subgraph_pack)
            write_json(concept_dir / "structure_plan.json", plan)
            (concept_dir / "story_prompt.txt").write_text(story_prompt, encoding="utf-8")

            if options.mode == "llm":
                assert config is not None
                draft = _call_story_llm(config=config, prompt=story_prompt, retry=options.retry)
            elif options.mode == "local":
                draft = build_local_chinese_story(card, plan)
            else:
                raise ValueError(f"Unsupported generation mode: {options.mode}")
            draft_path.write_text(draft, encoding="utf-8")

            eval_config = config if options.evaluate_mode == "llm" else None
            evaluation = evaluate_story_dir(concept_dir, mode=options.evaluate_mode, config=eval_config)
            status = {
                "concept_id": concept_id,
                "subject": subject,
                "story_language": "zh-CN",
                "concept_type": card.get("concept_type"),
                "generation_priority": card.get("data_quality", {}).get("generation_priority"),
                "generation_status": "success",
                "evaluation_status": evaluation.get("final_status"),
                "weighted_overall": evaluation.get("weighted_overall"),
                "retry_count": options.retry,
                "chinese_char_ratio": round(chinese_char_ratio(draft), 4),
            }
            _write_status(concept_dir, status)
            append_jsonl(output_dir / "eval_summary.jsonl", evaluation)
            row = {
                "concept_id": concept_id,
                "subject": subject,
                "status": "success",
                "output_dir": str(concept_dir),
                "final_status": evaluation.get("final_status"),
                "weighted_overall": evaluation.get("weighted_overall"),
                "chinese_char_ratio": status["chinese_char_ratio"],
                "index": index,
            }
            append_jsonl(summary_path, row)
            success_count += 1
        except Exception as exc:
            failed_count += 1
            error_payload = {
                "concept_id": concept_id,
                "subject": subject,
                "status": "failed",
                "output_dir": str(concept_dir),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "card": card,
            }
            write_json(concept_dir / "error.json", error_payload)
            append_jsonl(summary_path, error_payload)
            append_jsonl(failed_queue_path, error_payload)

        if options.sleep_seconds > 0:
            time.sleep(options.sleep_seconds)

    result = {
        "output_dir": str(output_dir),
        "summary_path": str(summary_path),
        "eval_summary_path": str(output_dir / "eval_summary.jsonl"),
        "failed_queue_path": str(failed_queue_path),
        "concept_count": len(cards),
        "success_count": success_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "mode": options.mode,
        "language": options.language,
    }
    eval_summary_path = output_dir / "eval_summary.jsonl"
    if eval_summary_path.exists():
        result.update(export_reports(eval_summary_path))
    write_json(output_dir / "run_result.json", result)
    return result
