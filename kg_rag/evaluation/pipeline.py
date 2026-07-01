from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from kg_rag.evaluation.parser import build_evaluation_input_from_dir, parse_json_object
from kg_rag.evaluation.prompts import SYSTEM_PROMPT, build_six_dim_eval_prompt
from kg_rag.evaluation.report import append_jsonl, export_reports
from kg_rag.evaluation.rubric import build_result
from kg_rag.evaluation.rules import evaluate_rules
from kg_rag.io import write_json
from kg_rag.llm_client import chat_completion
from kg_rag.llm_config import LLMConfig


def evaluate_story_dir(
    story_dir: Path,
    *,
    mode: str = "rules",
    config: LLMConfig | None = None,
    peer_stories: list[str] | None = None,
) -> dict[str, Any]:
    evaluation_input = build_evaluation_input_from_dir(story_dir)
    rule_scores, rule_flags, rule_rationales, rule_suggestions, rule_findings = evaluate_rules(
        evaluation_input,
        peer_stories=peer_stories,
    )

    judge_payload = None
    scores = rule_scores
    flags = rule_flags
    rationales = rule_rationales
    suggestions = rule_suggestions
    prompt = build_six_dim_eval_prompt(evaluation_input, rule_findings)

    if mode == "llm":
        if config is None:
            raise ValueError("LLM evaluation mode requires an LLMConfig.")
        raw_response = chat_completion(
            config=config,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
        )
        (story_dir / "six_dim_eval_prompt.txt").write_text(prompt, encoding="utf-8")
        (story_dir / "six_dim_eval_response.txt").write_text(raw_response, encoding="utf-8")
        judge_payload = parse_json_object(raw_response)
        scores = judge_payload.get("scores", rule_scores)
        merged_flags = dict(rule_flags)
        merged_flags.update(judge_payload.get("hard_flags", {}))
        flags = merged_flags
        rationales = judge_payload.get("rationales", rule_rationales)
        suggestions = judge_payload.get("revision_suggestions", rule_suggestions)
    elif mode != "rules":
        raise ValueError(f"Unsupported evaluation mode: {mode}")

    result = build_result(
        evaluation_input=evaluation_input,
        scores=scores,
        hard_flags=flags,
        rationales=rationales,
        revision_suggestions=suggestions,
        rule_findings=rule_findings,
        judge_response=judge_payload,
        mode=mode,
    )
    write_json(story_dir / "six_dim_eval.json", result)
    if mode == "rules":
        (story_dir / "six_dim_eval_prompt.txt").write_text(prompt, encoding="utf-8")
    return result


def _concept_dirs(batch_dir: Path) -> list[Path]:
    concepts_dir = batch_dir / "concepts"
    if concepts_dir.exists():
        return sorted(path for path in concepts_dir.iterdir() if path.is_dir())
    return [batch_dir]


def _copy_failed_case(concept_dir: Path, failed_root: Path) -> None:
    target = failed_root / concept_dir.name
    target.mkdir(parents=True, exist_ok=True)
    for filename in ("draft_story.txt", "subgraph_pack.json", "structure_plan.json", "six_dim_eval.json"):
        source = concept_dir / filename
        if source.exists():
            shutil.copy2(source, target / filename)


def evaluate_batch_dir(
    batch_dir: Path,
    *,
    mode: str = "rules",
    config: LLMConfig | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    concept_dirs = _concept_dirs(batch_dir)
    summary_path = batch_dir / "eval_summary.jsonl"
    if summary_path.exists() and not resume:
        summary_path.unlink()

    story_texts = {
        concept_dir: (concept_dir / "draft_story.txt").read_text(encoding="utf-8")
        for concept_dir in concept_dirs
        if (concept_dir / "draft_story.txt").exists()
    }

    evaluated = 0
    skipped = 0
    failed = 0
    failed_root = batch_dir / "failed_cases"

    for concept_dir in concept_dirs:
        eval_path = concept_dir / "six_dim_eval.json"
        if resume and eval_path.exists():
            skipped += 1
            continue
        peers = [story for path, story in story_texts.items() if path != concept_dir]
        try:
            row = evaluate_story_dir(concept_dir, mode=mode, config=config, peer_stories=peers)
            append_jsonl(summary_path, row)
            evaluated += 1
            if row.get("final_status") != "accept":
                _copy_failed_case(concept_dir, failed_root)
        except Exception as exc:
            failed += 1
            error_payload = {
                "concept_dir": str(concept_dir),
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
            write_json(concept_dir / "six_dim_eval_error.json", error_payload)

    report_paths = export_reports(summary_path) if summary_path.exists() else {}
    result = {
        "batch_dir": str(batch_dir),
        "summary_path": str(summary_path),
        "evaluated_count": evaluated,
        "skipped_count": skipped,
        "failed_count": failed,
        "mode": mode,
        **report_paths,
    }
    write_json(batch_dir / "eval_run_result.json", result)
    return result

