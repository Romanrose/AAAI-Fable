from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.llm_config import LLMConfig
from kg_rag.multi_agent.agents import AlignerAgent, ArbiterAgent, GeneratorAgent, PlannerAgent, ReviserAgent
from kg_rag.copycat.controller import (
    build_copycat_plan,
    record_copycat_candidate,
    record_copycat_workspace,
    repair_copycat_story,
    run_copycat_diagnostics,
)
from kg_rag.copycat.decision import choose_copycat_candidate
from kg_rag.multi_agent.decision import DecisionEngine, revision_reason
from kg_rag.multi_agent.graph import build_concept_relation_graph, build_mechanism_graph, retrieve_context
from kg_rag.multi_agent.llm import ChatLLM, DeepSeekLLM
from kg_rag.multi_agent.metrics import evaluate_record
from kg_rag.multi_agent.quality import build_rule_six_dim_eval
from kg_rag.multi_agent.records import build_m2na_record
from kg_rag.multi_agent.report import export_run_reports
from kg_rag.multi_agent.six_dim_judge import SixDimJudgeAgent
from kg_rag.multi_agent.text import clean_value


PIPELINE_VERSION = "multi-agent-v2"


@dataclass(frozen=True)
class MultiAgentOptions:
    language: str = "zh-CN"
    strategy: str = "standard"
    subjects: str | None = None
    priority: str | None = None
    limit_per_subject: int | None = None
    limit: int | None = None
    offset: int = 0
    max_edges: int = 16
    num_plans: int = 3
    revision_rounds: int = 1
    six_dim_mode: str = "rules"
    resume: bool = True
    sleep_seconds: float = 0.0
    copycat_steps: int = 30
    copycat_initial_candidates: int = 3
    copycat_temperature_threshold: float = 35.0


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _llm_identity(llm: ChatLLM) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "class": f"{type(llm).__module__}.{type(llm).__qualname__}",
    }
    config = getattr(llm, "config", None)
    for key in ("provider", "base_url", "model", "temperature", "max_tokens"):
        if config is not None and hasattr(config, key):
            identity[key] = getattr(config, key)
    for key in ("max_attempts", "retry_base_seconds"):
        if hasattr(llm, key):
            identity[key] = getattr(llm, key)
    return identity


def _generation_signature(
    *,
    card: dict[str, Any],
    graph_signature: str,
    options: MultiAgentOptions,
    llm: ChatLLM,
    judge_llm: ChatLLM,
) -> str:
    option_values = asdict(options)
    for key in ("subjects", "priority", "limit_per_subject", "limit", "offset", "resume", "sleep_seconds"):
        option_values.pop(key, None)
    return _stable_hash(
        {
            "pipeline_version": PIPELINE_VERSION,
            "card": card,
            "graph_signature": graph_signature,
            "options": option_values,
            "llm": _llm_identity(llm),
            "judge_llm": _llm_identity(judge_llm),
        }
    )


def run_one(
    *,
    concept_card_path: Path,
    normalized_graph_path: Path,
    output_dir: Path,
    options: MultiAgentOptions,
    llm: ChatLLM | None = None,
    config: LLMConfig | None = None,
    judge_llm: ChatLLM | None = None,
    judge_config: LLMConfig | None = None,
) -> dict[str, Any]:
    card = clean_value(read_json(concept_card_path))
    graph = clean_value(read_json(normalized_graph_path))
    llm = llm or DeepSeekLLM(config or LLMConfig.from_env())
    judge_llm = judge_llm or (DeepSeekLLM(judge_config) if judge_config else llm)
    return run_one_card(
        card=card,
        normalized_graph=graph,
        output_dir=output_dir,
        options=options,
        llm=llm,
        judge_llm=judge_llm,
        graph_signature=_sha256_path(normalized_graph_path),
    )


def run_batch(
    *,
    concept_cards_path: Path,
    normalized_graph_path: Path,
    output_dir: Path,
    options: MultiAgentOptions,
    llm: ChatLLM | None = None,
    config: LLMConfig | None = None,
    judge_llm: ChatLLM | None = None,
    judge_config: LLMConfig | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    graph = clean_value(read_json(normalized_graph_path))
    cards = [clean_value(card) for card in read_jsonl(concept_cards_path)]
    selected_cards = select_cards(cards, options)
    llm = llm or DeepSeekLLM(config or LLMConfig.from_env())
    judge_llm = judge_llm or (DeepSeekLLM(judge_config) if judge_config else llm)
    graph_signature = _sha256_path(normalized_graph_path)
    cards_signature = _sha256_path(concept_cards_path)

    manifest = {
        "pipeline": "kg_rag.multi_agent",
        "pipeline_version": PIPELINE_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "language": options.language,
        "strategy": options.strategy,
        "concept_cards_path": str(concept_cards_path),
        "concept_cards_sha256": cards_signature,
        "normalized_graph_path": str(normalized_graph_path),
        "normalized_graph_sha256": graph_signature,
        "llm": _llm_identity(llm),
        "judge_llm": _llm_identity(judge_llm),
        "subjects": options.subjects,
        "priority": options.priority,
        "limit_per_subject": options.limit_per_subject,
        "limit": options.limit,
        "num_plans": options.num_plans,
        "revision_rounds": options.revision_rounds,
        "six_dim_mode": options.six_dim_mode,
        "max_edges": options.max_edges,
        "copycat_steps": options.copycat_steps,
        "copycat_initial_candidates": options.copycat_initial_candidates,
        "copycat_temperature_threshold": options.copycat_temperature_threshold,
        "selected_count": len(selected_cards),
    }
    write_json(output_dir / "manifest.json", manifest)

    records: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    six_dim_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []

    for card in selected_cards:
        try:
            result = run_one_card(
                card=card,
                normalized_graph=graph,
                output_dir=output_dir,
                options=options,
                llm=llm,
                judge_llm=judge_llm,
                graph_signature=graph_signature,
            )
            if result.get("skipped"):
                result = load_existing_result(output_dir, card)
            records.append(result["record"])
            metric_rows.append(result["automatic_metrics"])
            six_dim_rows.append(result["six_dim_eval"])
            summary_rows.append(result["summary_row"])
        except Exception as exc:
            failed_rows.append(
                {
                    "concept_id": card.get("concept_id"),
                    "subject": card.get("subject"),
                    "error": str(exc),
                }
            )
        if options.sleep_seconds:
            time.sleep(options.sleep_seconds)

    paths = export_run_reports(
        output_dir=output_dir,
        records=records,
        metric_rows=metric_rows,
        six_dim_rows=six_dim_rows,
        summary_rows=summary_rows,
        failed_rows=failed_rows,
    )
    run_result = {
        **paths,
        "concept_count": len(selected_cards),
        "success_count": len(records),
        "fallback_concept_count": sum(
            1 for row in summary_rows if int(row.get("fallback_count") or 0) > 0
        ),
        "failed_count": len(failed_rows),
        "failed_rows": failed_rows,
    }
    write_json(output_dir / "run_result.json", run_result)
    return run_result


def evaluate_existing_run(
    *,
    run_dir: Path,
    six_dim_mode: str,
    llm: ChatLLM | None = None,
    config: LLMConfig | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    concepts_dir = run_dir / "concepts"
    if not concepts_dir.exists():
        raise ValueError(f"Run directory does not contain concepts/: {run_dir}")
    if six_dim_mode not in {"rules", "llm"}:
        raise ValueError("six_dim_mode must be either 'rules' or 'llm'")

    judge = None
    if six_dim_mode == "llm":
        llm = llm or DeepSeekLLM(config or LLMConfig.from_env())
        judge = SixDimJudgeAgent(llm)
    evaluation_manifest = {
        "pipeline_version": PIPELINE_VERSION,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "six_dim_mode": six_dim_mode,
        "resume": resume,
        "llm": _llm_identity(llm) if llm is not None else None,
    }
    write_json(run_dir / f"evaluation_manifest.{six_dim_mode}.json", evaluation_manifest)
    records: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    six_dim_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []

    for concept_dir in sorted(path for path in concepts_dir.iterdir() if path.is_dir()):
        try:
            card = read_json(concept_dir / "concept_card.json")
            retrieval_package = read_json(concept_dir / "retrieval_package.json")
            mechanism_graph = read_json(concept_dir / "mechanism_graph.json")
            story = (concept_dir / "final_story.txt").read_text(encoding="utf-8")
            alignment = read_json(concept_dir / "final_alignment.json")
            record = read_json(concept_dir / "m2na_record.json")
            metrics = read_json(concept_dir / "automatic_metrics.json")
            status_path = concept_dir / "status.json"
            status = read_json(status_path) if status_path.exists() else {}
            selected_candidate_id = status.get("selected_candidate_id")
            decision = {}
            if not selected_candidate_id and (concept_dir / "decision.json").exists():
                decision = read_json(concept_dir / "decision.json")
                selected_candidate_id = decision.get("winner_candidate_id")
            elif (concept_dir / "decision.json").exists():
                decision = read_json(concept_dir / "decision.json")
            plan_path = concept_dir / "candidates" / str(selected_candidate_id) / "narrative_plan.json"
            narrative_plan = read_json(plan_path) if plan_path.exists() else {}

            six_dim_path = concept_dir / "six_dim_eval.json"
            if resume and six_dim_path.exists():
                existing = read_json(six_dim_path)
                if existing.get("mode") == six_dim_mode:
                    six_dim = existing
                else:
                    six_dim = _evaluate_six_dim(
                        mode=six_dim_mode,
                        judge=judge,
                        card=card,
                        retrieval_package=retrieval_package,
                        mechanism_graph=mechanism_graph,
                        narrative_plan=narrative_plan,
                        story=story,
                        alignment=alignment,
                        metrics=metrics,
                    )
            else:
                six_dim = _evaluate_six_dim(
                    mode=six_dim_mode,
                    judge=judge,
                    card=card,
                    retrieval_package=retrieval_package,
                    mechanism_graph=mechanism_graph,
                    narrative_plan=narrative_plan,
                    story=story,
                    alignment=alignment,
                    metrics=metrics,
                )

            write_json(six_dim_path, six_dim)
            status.update(
                {
                    "concept_id": card.get("concept_id"),
                    "subject": card.get("subject"),
                    "story_language": card.get("story_language", "zh-CN"),
                    "strategy": status.get("strategy", "standard"),
                    "generation_status": status.get("generation_status", "success"),
                    "evaluation_status": six_dim["final_status"],
                    "weighted_overall": six_dim["weighted_overall"],
                    "six_dim_mode": six_dim["mode"],
                    "selected_candidate_id": selected_candidate_id,
                    "selection_mode": decision.get("selection_mode", status.get("selection_mode")),
                    "selected_score": decision.get("selected_score", status.get("selected_score")),
                    "selected_temperature": decision.get("selected_temperature", status.get("selected_temperature")),
                }
            )
            write_json(status_path, status)

            records.append(record)
            metric_rows.append(metrics)
            six_dim_rows.append(six_dim)
            summary_rows.append(
                build_summary_row(card=card, status=status, metrics=metrics, six_dim=six_dim)
            )
        except Exception as exc:
            failed_rows.append(
                {
                    "concept_id": concept_dir.name,
                    "subject": None,
                    "error": str(exc),
                }
            )

    paths = export_run_reports(
        output_dir=run_dir,
        records=records,
        metric_rows=metric_rows,
        six_dim_rows=six_dim_rows,
        summary_rows=summary_rows,
        failed_rows=failed_rows,
    )
    result = {
        **paths,
        "evaluated_count": len(six_dim_rows),
        "failed_count": len(failed_rows),
        "failed_rows": failed_rows,
        "six_dim_mode": six_dim_mode,
    }
    write_json(run_dir / "six_dim_eval_result.json", result)
    return result


def _evaluate_six_dim(
    *,
    mode: str,
    judge: SixDimJudgeAgent | None,
    card: dict[str, Any],
    retrieval_package: dict[str, Any],
    mechanism_graph: dict[str, Any],
    narrative_plan: dict[str, Any],
    story: str,
    alignment: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    if mode == "rules":
        return build_rule_six_dim_eval(
            concept_id=str(card.get("concept_id") or metrics.get("id") or ""),
            target_concept=card.get("canonical_name") or card.get("concept_id") or "",
            metrics=metrics,
        )
    if judge is None:
        raise ValueError("LLM six-dimensional evaluation requires a judge agent")
    return judge.evaluate(
        card=card,
        retrieval_package=retrieval_package,
        mechanism_graph=mechanism_graph,
        narrative_plan=narrative_plan,
        story=story,
        alignment=alignment,
        automatic_metrics=metrics,
    )


def run_one_card(
    *,
    card: dict[str, Any],
    normalized_graph: dict[str, Any],
    output_dir: Path,
    options: MultiAgentOptions,
    llm: ChatLLM,
    judge_llm: ChatLLM | None = None,
    graph_signature: str | None = None,
) -> dict[str, Any]:
    if options.language != "zh-CN":
        raise ValueError("kg_rag.multi_agent currently supports only language='zh-CN'")
    if options.strategy not in {"standard", "copycat"}:
        raise ValueError("strategy must be either 'standard' or 'copycat'")
    if options.num_plans < 1 or options.copycat_initial_candidates < 1:
        raise ValueError("candidate counts must be at least 1")
    if options.revision_rounds < 0:
        raise ValueError("revision_rounds must not be negative")
    if options.copycat_steps < 1:
        raise ValueError("copycat_steps must be at least 1")

    concept_id = str(card["concept_id"])
    judge_llm = judge_llm or llm
    graph_signature = graph_signature or _stable_hash(normalized_graph)
    input_signature = _generation_signature(
        card=card,
        graph_signature=graph_signature,
        options=options,
        llm=llm,
        judge_llm=judge_llm,
    )
    concept_dir = output_dir / "concepts" / concept_id
    status_path = concept_dir / "status.json"
    if options.resume and status_path.exists():
        status = read_json(status_path)
        if (
            str(status.get("generation_status") or "").startswith("success")
            and status.get("six_dim_mode", "rules") == options.six_dim_mode
            and status.get("strategy", "standard") == options.strategy
            and status.get("input_signature") == input_signature
        ):
            return {"skipped": True, "concept_id": concept_id}

    concept_dir.mkdir(parents=True, exist_ok=True)
    write_json(concept_dir / "concept_card.json", card)

    retrieval_package = retrieve_context(
        card=card,
        normalized_graph=normalized_graph,
        max_edges=options.max_edges,
    )
    mechanism_graph = build_mechanism_graph(card=card, retrieval_package=retrieval_package)
    concept_relation_graph = build_concept_relation_graph(
        card=card,
        retrieval_package=retrieval_package,
    )
    write_json(concept_dir / "retrieval_package.json", retrieval_package)
    write_json(concept_dir / "mechanism_graph.json", mechanism_graph)
    write_json(concept_dir / "concept_relation_graph.json", concept_relation_graph)

    planner = PlannerAgent(llm)
    generator = GeneratorAgent(llm)
    aligner = AlignerAgent(llm)
    reviser = ReviserAgent(llm)
    judge = SixDimJudgeAgent(judge_llm)
    arbiter = ArbiterAgent(llm)
    decision_engine = DecisionEngine(arbiter)

    candidates: list[dict[str, Any]] = []
    plan_count = options.copycat_initial_candidates if options.strategy == "copycat" else options.num_plans
    for index in range(1, plan_count + 1):
        candidate_id = f"candidate_{index:03d}"
        candidate_dir = concept_dir / "candidates" / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        copycat_payload: dict[str, Any] | None = None
        if options.strategy == "copycat":
            copycat_payload = build_copycat_plan(
                card=card,
                mechanism_graph=mechanism_graph,
                concept_relation_graph=concept_relation_graph,
                candidate_id=candidate_id,
                candidate_index=index,
                max_steps=options.copycat_steps,
            )
            plan = copycat_payload["plan"]
            planner_call = {"status": "not_applicable", "strategy": "copycat"}
        else:
            plan = planner.plan(
                card=card,
                retrieval_package=retrieval_package,
                mechanism_graph=mechanism_graph,
                candidate_index=index,
            )
            planner_call = dict(planner.last_call)
        story = generator.generate(card=card, mechanism_graph=mechanism_graph, plan=plan)
        generator_call = dict(generator.last_call)
        copycat_repair_trace: list[dict[str, Any]] = []
        if options.strategy == "copycat":
            story, copycat_repair_trace = repair_copycat_story(
                card=card,
                candidate_id=candidate_id,
                story=story,
            )
        alignment = aligner.align(mechanism_graph=mechanism_graph, plan=plan, story=story)
        aligner_call = dict(aligner.last_call)
        record = build_m2na_record(
            card=card,
            mechanism_graph=mechanism_graph,
            narrative=story,
            alignment=alignment,
            method=f"con2fable-{options.strategy}",
        )
        metrics = evaluate_record(record)
        six_dim = build_rule_six_dim_eval(
            concept_id=concept_id,
            target_concept=card.get("canonical_name") or concept_id,
            metrics=metrics,
        )
        candidate = {
            "candidate_id": candidate_id,
            "plan": plan,
            "story": story,
            "alignment": alignment,
            "record": record,
            "automatic_metrics": metrics,
            "six_dim_eval": six_dim,
            "agent_calls": {
                "planner": planner_call,
                "generator": generator_call,
                "aligner": aligner_call,
            },
        }
        if copycat_payload is not None:
            candidate["copycat_structures"] = copycat_payload["structures"]
            candidate["copycat_codelet_trace"] = copycat_payload["codelet_trace"]
            candidate["copycat_repair_trace"] = copycat_repair_trace
            candidate["copycat_check_trace"] = run_copycat_diagnostics(
                card=card,
                candidate_id=candidate_id,
                story=story,
                alignment=alignment,
                metrics=metrics,
            )
        candidates.append(candidate)
        _write_candidate(candidate_dir, candidate)
        record_copycat_candidate(
            candidate_dir=candidate_dir,
            candidate=candidate,
            mechanism_graph=mechanism_graph,
        )

    decision = (
        choose_copycat_candidate(
            candidates=candidates,
            mechanism_graph=mechanism_graph,
            temperature_threshold=options.copycat_temperature_threshold,
        )
        if options.strategy == "copycat"
        else decision_engine.choose(candidates)
    )
    selected = decision["selected_candidate"]
    final_plan = selected["plan"]
    final_story = selected["story"]
    final_alignment = selected["alignment"]
    final_record = selected["record"]
    final_metrics = selected["automatic_metrics"]
    final_six_dim = _evaluate_six_dim(
        mode=options.six_dim_mode,
        judge=judge,
        card=card,
        retrieval_package=retrieval_package,
        mechanism_graph=mechanism_graph,
        narrative_plan=final_plan,
        story=final_story,
        alignment=final_alignment,
        metrics=final_metrics,
    )
    revision_applied = False
    revision_history: list[dict[str, Any]] = []
    revisions_dir = concept_dir / "revisions"

    for round_index in range(1, options.revision_rounds + 1):
        reason = _revision_reason_for_result(
            metrics=final_metrics,
            six_dim=final_six_dim,
            initial_reason=decision.get("revision_reason") if round_index == 1 else None,
        )
        if not reason:
            break
        revised_story = reviser.revise(
            card=card,
            mechanism_graph=mechanism_graph,
            plan=final_plan,
            story=final_story,
            failure_reason=reason,
        )
        revised_alignment = aligner.align(
            mechanism_graph=mechanism_graph,
            plan=final_plan,
            story=revised_story,
        )
        revised_record = build_m2na_record(
            card=card,
            mechanism_graph=mechanism_graph,
            narrative=revised_story,
            alignment=revised_alignment,
            method=f"con2fable-{options.strategy}",
        )
        revised_metrics = evaluate_record(revised_record)
        revised_six_dim = _evaluate_six_dim(
            mode=options.six_dim_mode,
            judge=judge,
            card=card,
            retrieval_package=retrieval_package,
            mechanism_graph=mechanism_graph,
            narrative_plan=final_plan,
            story=revised_story,
            alignment=revised_alignment,
            metrics=revised_metrics,
        )
        improved = _is_better_result(
            new_metrics=revised_metrics,
            old_metrics=final_metrics,
            new_six_dim=revised_six_dim,
            old_six_dim=final_six_dim,
        )
        round_dir = revisions_dir / f"round_{round_index:03d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / "story.txt").write_text(revised_story, encoding="utf-8")
        write_json(round_dir / "alignment.json", revised_alignment)
        write_json(round_dir / "automatic_metrics.json", revised_metrics)
        write_json(round_dir / "six_dim_eval.json", revised_six_dim)
        round_result = {
            "round": round_index,
            "reason": reason,
            "improved": improved,
            "reviser_call": dict(reviser.last_call),
            "aligner_call": dict(aligner.last_call),
            "evaluation_status": revised_six_dim.get("final_status"),
            "weighted_overall": revised_six_dim.get("weighted_overall"),
        }
        revision_history.append(round_result)
        write_json(round_dir / "result.json", round_result)
        if improved:
            final_story = revised_story
            final_alignment = revised_alignment
            final_record = revised_record
            final_metrics = revised_metrics
            final_six_dim = revised_six_dim
            revision_applied = True
        if final_six_dim.get("final_status") == "accept":
            break

    write_json(
        concept_dir / "revision.json",
        {
            "requested_rounds": options.revision_rounds,
            "attempted_rounds": len(revision_history),
            "revision_applied": revision_applied,
            "history": revision_history,
        },
    )

    decision_payload = {
        key: value
        for key, value in decision.items()
        if key != "selected_candidate"
    }
    decision_payload["revision_applied"] = revision_applied
    decision_payload["revision_attempted_rounds"] = len(revision_history)
    write_json(concept_dir / "decision.json", decision_payload)
    record_copycat_workspace(
        concept_dir=concept_dir,
        concept_id=concept_id,
        mechanism_graph=mechanism_graph,
        candidates=candidates,
        best_candidate_id=decision_payload["winner_candidate_id"],
    )
    (concept_dir / "final_story.txt").write_text(final_story, encoding="utf-8")
    write_json(concept_dir / "final_alignment.json", final_alignment)
    write_json(concept_dir / "m2na_record.json", final_record)
    write_json(concept_dir / "automatic_metrics.json", final_metrics)
    write_json(concept_dir / "six_dim_eval.json", final_six_dim)
    agent_calls = {
        "candidates": {
            str(candidate["candidate_id"]): candidate.get("agent_calls", {})
            for candidate in candidates
        },
        "selected_candidate_id": selected.get("candidate_id"),
        "selected_candidate": selected.get("agent_calls", {}),
        "arbiter": dict(arbiter.last_call),
        "revisions": [
            {
                "round": item["round"],
                "reviser": item["reviser_call"],
                "aligner": item["aligner_call"],
            }
            for item in revision_history
        ],
    }
    fallback_count = _count_fallbacks(
        {
            "candidates": agent_calls["candidates"],
            "arbiter": agent_calls["arbiter"],
            "revisions": agent_calls["revisions"],
        }
    )
    write_json(concept_dir / "agent_calls.json", agent_calls)
    status = {
        "concept_id": concept_id,
        "subject": card.get("subject"),
        "story_language": options.language,
        "strategy": options.strategy,
        "generation_status": "success_with_fallback" if fallback_count else "success",
        "evaluation_status": final_six_dim["final_status"],
        "weighted_overall": final_six_dim["weighted_overall"],
        "six_dim_mode": final_six_dim["mode"],
        "selected_candidate_id": decision_payload["winner_candidate_id"],
        "selection_mode": decision_payload.get("selection_mode", "standard_decision"),
        "selected_score": decision_payload.get("selected_score"),
        "selected_temperature": decision_payload.get("selected_temperature"),
        "revision_applied": revision_applied,
        "revision_attempted_rounds": len(revision_history),
        "fallback_count": fallback_count,
        "input_signature": input_signature,
        "pipeline_version": PIPELINE_VERSION,
    }
    write_json(status_path, status)
    summary_row = build_summary_row(
        card=card,
        status=status,
        metrics=final_metrics,
        six_dim=final_six_dim,
    )
    return {
        "record": final_record,
        "automatic_metrics": final_metrics,
        "six_dim_eval": final_six_dim,
        "summary_row": summary_row,
        "status": status,
        "concept_dir": str(concept_dir),
    }


def _write_candidate(candidate_dir: Path, candidate: dict[str, Any]) -> None:
    write_json(candidate_dir / "narrative_plan.json", candidate["plan"])
    (candidate_dir / "draft_story.txt").write_text(candidate["story"], encoding="utf-8")
    write_json(candidate_dir / "alignment.json", candidate["alignment"])
    write_json(candidate_dir / "m2na_record.json", candidate["record"])
    write_json(candidate_dir / "automatic_metrics.json", candidate["automatic_metrics"])
    write_json(candidate_dir / "six_dim_eval.json", candidate["six_dim_eval"])
    write_json(candidate_dir / "agent_calls.json", candidate.get("agent_calls", {}))
    if candidate.get("copycat_structures"):
        write_json(candidate_dir / "copycat_structures.json", candidate["copycat_structures"])
    if candidate.get("copycat_codelet_trace"):
        write_json(candidate_dir / "copycat_codelet_trace.json", candidate["copycat_codelet_trace"])
    if candidate.get("copycat_repair_trace"):
        write_json(candidate_dir / "copycat_repair_trace.json", candidate["copycat_repair_trace"])
    if candidate.get("copycat_check_trace"):
        write_json(candidate_dir / "copycat_check_trace.json", candidate["copycat_check_trace"])


def _metric_score(metrics: dict[str, Any]) -> float:
    return (
        float(metrics.get("weighted_node_coverage") or 0.0)
        + float(metrics.get("weighted_edge_coverage") or 0.0)
        + float(metrics.get("alignment_precision") or 0.0)
        - float(metrics.get("exact_concept_leakage") or 0.0)
        - float(metrics.get("soft_term_leakage") or 0.0)
    )


def _is_better_result(
    *,
    new_metrics: dict[str, Any],
    old_metrics: dict[str, Any],
    new_six_dim: dict[str, Any],
    old_six_dim: dict[str, Any],
) -> bool:
    status_rank = {"reject": 0, "revise": 1, "accept": 2}
    new_rank = status_rank.get(str(new_six_dim.get("final_status")), -1)
    old_rank = status_rank.get(str(old_six_dim.get("final_status")), -1)
    new_key = (
        new_rank,
        float(new_six_dim.get("weighted_overall") or 0.0),
        _metric_score(new_metrics),
    )
    old_key = (
        old_rank,
        float(old_six_dim.get("weighted_overall") or 0.0),
        _metric_score(old_metrics),
    )
    return new_key > old_key


def _revision_reason_for_result(
    *,
    metrics: dict[str, Any],
    six_dim: dict[str, Any],
    initial_reason: str | None = None,
) -> str | None:
    if initial_reason:
        return initial_reason
    if six_dim.get("final_status") == "accept":
        return None
    automatic_reason = revision_reason(metrics)
    if automatic_reason:
        return automatic_reason
    suggestions = six_dim.get("revision_suggestions", [])
    if isinstance(suggestions, list):
        text = "；".join(str(item).strip() for item in suggestions if str(item).strip())
        if text:
            return text
    return f"六维评测状态为 {six_dim.get('final_status', 'unknown')}，需要提升忠实度、映射和教学价值。"


def _count_fallbacks(value: Any) -> int:
    if isinstance(value, dict):
        count = 1 if value.get("status") == "fallback" else 0
        return count + sum(_count_fallbacks(item) for item in value.values())
    if isinstance(value, list):
        return sum(_count_fallbacks(item) for item in value)
    return 0


def select_cards(cards: list[dict[str, Any]], options: MultiAgentOptions) -> list[dict[str, Any]]:
    subject_set = _split_filter(options.subjects)
    priority_set = _split_filter(options.priority)
    filtered = []
    for card in cards:
        if subject_set and card.get("subject") not in subject_set:
            continue
        priority = card.get("data_quality", {}).get("generation_priority")
        if priority_set and priority not in priority_set:
            continue
        filtered.append(card)

    if options.offset:
        filtered = filtered[options.offset :]
    if options.limit_per_subject is not None:
        counts: dict[str, int] = {}
        selected = []
        for card in filtered:
            subject = str(card.get("subject") or "")
            if counts.get(subject, 0) >= options.limit_per_subject:
                continue
            selected.append(card)
            counts[subject] = counts.get(subject, 0) + 1
        filtered = selected
    if options.limit is not None:
        filtered = filtered[: options.limit]
    return filtered


def _split_filter(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def load_existing_result(output_dir: Path, card: dict[str, Any]) -> dict[str, Any]:
    concept_dir = output_dir / "concepts" / str(card["concept_id"])
    record = read_json(concept_dir / "m2na_record.json")
    metrics = read_json(concept_dir / "automatic_metrics.json")
    six_dim = read_json(concept_dir / "six_dim_eval.json")
    status = read_json(concept_dir / "status.json")
    return {
        "record": record,
        "automatic_metrics": metrics,
        "six_dim_eval": six_dim,
        "summary_row": build_summary_row(card=card, status=status, metrics=metrics, six_dim=six_dim),
        "status": status,
        "concept_dir": str(concept_dir),
    }


def build_summary_row(
    *,
    card: dict[str, Any],
    status: dict[str, Any],
    metrics: dict[str, Any],
    six_dim: dict[str, Any],
) -> dict[str, Any]:
    return {
        "concept_id": card.get("concept_id"),
        "subject": card.get("subject"),
        "strategy": status.get("strategy"),
        "generation_status": status.get("generation_status"),
        "fallback_count": status.get("fallback_count", 0),
        "revision_attempted_rounds": status.get("revision_attempted_rounds", 0),
        "evaluation_status": status.get("evaluation_status"),
        "selected_candidate_id": status.get("selected_candidate_id"),
        "selection_mode": status.get("selection_mode"),
        "selected_score": status.get("selected_score"),
        "selected_temperature": status.get("selected_temperature"),
        "weighted_overall": six_dim.get("weighted_overall"),
        "six_dim_mode": six_dim.get("mode"),
        **{
            key: metrics.get(key)
            for key in (
                "format_validity",
                "exact_concept_leakage",
                "soft_term_leakage",
                "weighted_node_coverage",
                "weighted_edge_coverage",
                "alignment_precision",
                "alignment_hallucination_rate",
                "relation_direction_accuracy",
                "concept_relation_coverage",
                "typed_relation_preservation",
                "template_hit_rate",
                "narrative_char_count",
            )
        },
    }
