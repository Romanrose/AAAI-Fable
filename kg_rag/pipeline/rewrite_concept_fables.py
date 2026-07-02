from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from kg_rag.concepts.prompts import STORY_SYSTEM_PROMPT, build_chinese_story_prompt, build_local_chinese_story
from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.evaluation.pipeline import evaluate_story_dir
from kg_rag.evaluation.report import export_reports
from kg_rag.io import read_json, write_json
from kg_rag.llm_client import chat_completion
from kg_rag.llm_config import LLMConfig


def _parse_status_filter(status: str) -> set[str]:
    return {item.strip() for item in status.split(",") if item.strip()}


def _backup_if_exists(path: Path, suffix: str) -> None:
    if path.exists():
        target = path.with_name(f"{path.stem}.{suffix}{path.suffix}")
        shutil.copy2(path, target)


def _rewrite_prompt(card: dict[str, Any], plan: dict[str, Any], previous_eval: dict[str, Any]) -> str:
    base_prompt = build_chinese_story_prompt(card, plan)
    return "\n\n".join(
        [
            base_prompt,
            "Rewrite constraints:",
            "- Keep the output in Simplified Chinese.",
            "- Fix the issues from six_dim_eval.",
            "- Do not reveal forbidden terms in the story body.",
            "- Preserve the concept mapping.",
            f"Previous evaluation JSON:\n{previous_eval}",
        ]
    )


def rewrite_concept_fables(
    *,
    run_dir: Path,
    status: str = "revise,reject",
    language: str = "zh-CN",
    mode: str = "local",
    retry: int = 1,
    config: LLMConfig | None = None,
) -> dict[str, Any]:
    if language != "zh-CN":
        raise ValueError("The first-stage rewrite runner currently supports only zh-CN.")
    if mode == "llm" and config is None:
        raise ValueError("LLM rewrite mode requires an LLMConfig.")

    statuses = _parse_status_filter(status)
    concepts_dir = run_dir / "concepts"
    rewritten = 0
    skipped = 0
    failed = 0
    rewrite_summary = run_dir / "rewrite_summary.jsonl"
    if rewrite_summary.exists():
        rewrite_summary.unlink()

    if not concepts_dir.exists():
        raise FileNotFoundError(f"Missing concepts directory: {concepts_dir}")

    for concept_dir in sorted(path for path in concepts_dir.iterdir() if path.is_dir()):
        status_path = concept_dir / "status.json"
        if not status_path.exists():
            skipped += 1
            continue
        current_status = read_json(status_path)
        if str(current_status.get("evaluation_status")) not in statuses:
            skipped += 1
            continue

        try:
            card = read_json(concept_dir / "concept_card.json")
            plan = read_json(concept_dir / "structure_plan.json")
            previous_eval = read_json(concept_dir / "six_dim_eval.json")
            _backup_if_exists(concept_dir / "draft_story.txt", "v1")
            _backup_if_exists(concept_dir / "six_dim_eval.json", "v1")

            if mode == "llm":
                assert config is not None
                prompt = _rewrite_prompt(card, plan, previous_eval)
                draft = chat_completion(
                    config=config,
                    system_prompt=STORY_SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                (concept_dir / "rewrite_prompt.txt").write_text(prompt, encoding="utf-8")
            elif mode == "local":
                draft = build_local_chinese_story(card, plan)
            else:
                raise ValueError(f"Unsupported rewrite mode: {mode}")

            (concept_dir / "draft_story.txt").write_text(draft, encoding="utf-8")
            evaluation = evaluate_story_dir(concept_dir, mode="llm" if mode == "llm" else "rules", config=config)
            updated_status = dict(current_status)
            updated_status.update(
                {
                    "generation_status": "rewritten",
                    "evaluation_status": evaluation.get("final_status"),
                    "weighted_overall": evaluation.get("weighted_overall"),
                    "rewrite_retry_count": retry,
                }
            )
            write_json(status_path, updated_status)
            with rewrite_summary.open("a", encoding="utf-8") as fh:
                import json

                fh.write(json.dumps(updated_status, ensure_ascii=False) + "\n")
            rewritten += 1
        except Exception as exc:
            failed += 1
            error_payload = {
                "concept_dir": str(concept_dir),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
            write_json(concept_dir / "rewrite_error.json", error_payload)

    eval_summary_path = run_dir / "eval_summary.jsonl"
    all_evals = []
    for concept_dir in sorted(path for path in concepts_dir.iterdir() if path.is_dir()):
        eval_path = concept_dir / "six_dim_eval.json"
        if eval_path.exists():
            all_evals.append(read_json(eval_path))
    if all_evals:
        write_jsonl(eval_summary_path, all_evals)
    reports: dict[str, Any] = {}
    if eval_summary_path.exists():
        reports = export_reports(eval_summary_path)
    result = {
        "run_dir": str(run_dir),
        "status_filter": sorted(statuses),
        "rewritten_count": rewritten,
        "skipped_count": skipped,
        "failed_count": failed,
        "rewrite_summary_path": str(rewrite_summary),
        **reports,
    }
    write_json(run_dir / "rewrite_result.json", result)
    return result
