from __future__ import annotations

import shutil
from pathlib import Path
from statistics import median
from typing import Any

from kg_rag.evaluation.parser import build_evaluation_input_from_dir, parse_json_object
from kg_rag.evaluation.prompts import SYSTEM_PROMPT, build_six_dim_eval_prompt
from kg_rag.evaluation.report import append_jsonl, export_reports
from kg_rag.evaluation.rubric import DIMENSIONS, HARD_FLAG_KEYS, build_result, normalize_hard_flags, normalize_scores
from kg_rag.evaluation.rules import evaluate_rules
from kg_rag.io import write_json
from kg_rag.llm_client import chat_completion
from kg_rag.llm_config import LLMConfig


def _as_judge_configs(config: LLMConfig | list[LLMConfig] | tuple[LLMConfig, ...] | None) -> list[LLMConfig]:
    if config is None:
        return []
    if isinstance(config, LLMConfig):
        return [config]
    return list(config)


def _safe_filename(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in text).strip("_") or "judge"


def _aggregate_judge_payloads(
    *,
    judge_payloads: list[dict[str, Any]],
    rule_scores: dict[str, int],
    rule_flags: dict[str, bool],
    rule_rationales: dict[str, str],
    rule_suggestions: list[str],
) -> tuple[dict[str, int], dict[str, bool], dict[str, str], list[str], dict[str, Any]]:
    if not judge_payloads:
        return rule_scores, rule_flags, rule_rationales, rule_suggestions, {"judge_count": 0}

    normalized_scores = [normalize_scores(payload.get("scores")) for payload in judge_payloads]
    scores = {
        dimension: int(round(median(score_set[dimension] for score_set in normalized_scores)))
        for dimension in DIMENSIONS
    }

    normalized_flags = [normalize_hard_flags(payload.get("hard_flags")) for payload in judge_payloads]
    flags = dict(rule_flags)
    for key in HARD_FLAG_KEYS:
        positive_votes = sum(1 for flag_set in normalized_flags if flag_set[key])
        flags[key] = bool(rule_flags.get(key, False)) or positive_votes > len(normalized_flags) / 2

    rationales: dict[str, str] = {}
    for dimension in DIMENSIONS:
        snippets = []
        for index, payload in enumerate(judge_payloads, start=1):
            text = str(payload.get("rationales", {}).get(dimension, "")).strip()
            if text:
                snippets.append(f"J{index}: {text}")
        rationales[dimension] = " | ".join(snippets) if snippets else rule_rationales.get(dimension, "")

    suggestions: list[str] = []
    for payload in judge_payloads:
        for suggestion in payload.get("revision_suggestions", []) or []:
            if isinstance(suggestion, str) and suggestion.strip() and suggestion not in suggestions:
                suggestions.append(suggestion.strip())
    if not suggestions:
        suggestions = rule_suggestions

    aggregation = {
        "judge_count": len(judge_payloads),
        "score_aggregation": "median_by_dimension",
        "hard_flag_aggregation": "rule_or_majority_vote",
        "judge_scores": normalized_scores,
        "judge_flags": normalized_flags,
    }
    return scores, flags, rationales, suggestions, aggregation


def evaluate_story_dir(
    story_dir: Path,
    *,
    mode: str = "rules",
    config: LLMConfig | list[LLMConfig] | tuple[LLMConfig, ...] | None = None,
    peer_stories: list[str] | None = None,
) -> dict[str, Any]:
    evaluation_input = build_evaluation_input_from_dir(story_dir)
    rule_scores, rule_flags, rule_rationales, rule_suggestions, rule_findings = evaluate_rules(
        evaluation_input,
        peer_stories=peer_stories,
    )

    judge_payload = None
    judge_payloads: list[dict[str, Any]] = []
    judge_errors: list[dict[str, Any]] = []
    judge_configs = _as_judge_configs(config)
    scores = rule_scores
    flags = rule_flags
    rationales = rule_rationales
    suggestions = rule_suggestions
    prompt = build_six_dim_eval_prompt(evaluation_input, rule_findings)

    if mode == "llm":
        if not judge_configs:
            raise ValueError("LLM evaluation mode requires at least one judge LLMConfig.")
        (story_dir / "six_dim_eval_prompt.txt").write_text(prompt, encoding="utf-8")
        for index, judge_config in enumerate(judge_configs, start=1):
            judge_id = _safe_filename(judge_config.name or f"judge_{index}")
            try:
                raw_response = chat_completion(
                    config=judge_config,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                (story_dir / f"six_dim_eval_response_{index}_{judge_id}.txt").write_text(
                    raw_response,
                    encoding="utf-8",
                )
                payload = parse_json_object(raw_response)
                payload["_judge"] = {
                    "index": index,
                    "name": judge_config.name,
                    "provider": judge_config.provider,
                    "model": judge_config.model,
                }
                write_json(story_dir / f"six_dim_eval_judge_{index}_{judge_id}.json", payload)
                judge_payloads.append(payload)
            except Exception as exc:
                error_payload = {
                    "index": index,
                    "name": judge_config.name,
                    "provider": judge_config.provider,
                    "model": judge_config.model,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
                write_json(story_dir / f"six_dim_eval_judge_{index}_{judge_id}_error.json", error_payload)
                judge_errors.append(error_payload)
        if not judge_payloads:
            raise RuntimeError(f"All LLM judges failed for {story_dir}.")
        scores, flags, rationales, suggestions, aggregation = _aggregate_judge_payloads(
            judge_payloads=judge_payloads,
            rule_scores=rule_scores,
            rule_flags=rule_flags,
            rule_rationales=rule_rationales,
            rule_suggestions=rule_suggestions,
        )
        judge_payload = {
            "mode": "panel",
            "judges_requested": len(judge_configs),
            "judges_succeeded": len(judge_payloads),
            "judges_failed": len(judge_errors),
            "aggregation": aggregation,
            "errors": judge_errors,
            "responses": judge_payloads,
        }
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
    config: LLMConfig | list[LLMConfig] | tuple[LLMConfig, ...] | None = None,
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
