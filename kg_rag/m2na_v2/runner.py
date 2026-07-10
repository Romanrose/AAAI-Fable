from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.copycat.controller import build_copycat_plan, repair_copycat_story
from kg_rag.copycat.decision import choose_copycat_candidate
from kg_rag.io import read_json, write_json
from kg_rag.m2na_v2.schemas import stable_hash
from kg_rag.multi_agent.agents import AlignerAgent, ArbiterAgent, GeneratorAgent, PlannerAgent, ReviserAgent
from kg_rag.multi_agent.decision import DecisionEngine, revision_reason
from kg_rag.multi_agent.graph import build_concept_relation_graph
from kg_rag.multi_agent.llm import ChatLLM
from kg_rag.multi_agent.metrics import evaluate_record
from kg_rag.multi_agent.quality import build_rule_six_dim_eval
from kg_rag.multi_agent.records import build_m2na_record
from kg_rag.multi_agent.report import export_run_reports
from kg_rag.multi_agent.six_dim_judge import SixDimJudgeAgent


RUNNER_VERSION = "m2na-v2-runner/v1"


@dataclass(frozen=True)
class ExperimentOptions:
    strategies: tuple[str, ...] = ("standard", "copycat")
    candidate_count: int = 3
    revision_rounds: int = 2
    six_dim_mode: str = "llm"
    copycat_steps: int = 30
    copycat_temperature_threshold: float = 35.0


def run_experiment(
    *,
    seeds_path: Path,
    preparation_root: Path,
    output_dir: Path,
    llm: ChatLLM,
    judge_llm: ChatLLM,
    options: ExperimentOptions | None = None,
) -> dict[str, Any]:
    options = options or ExperimentOptions()
    _validate_options(options)
    seeds = {str(item["concept_id"]): item for item in read_jsonl(seeds_path)}
    approved_path = preparation_root / "mechanisms.approved.jsonl"
    if not approved_path.exists():
        raise ValueError("Approved mechanism dataset is missing; import human reviews first")
    mechanisms = read_jsonl(approved_path)
    if not mechanisms:
        raise ValueError("Approved mechanism dataset is empty")
    approved_manifest = read_json(preparation_root / "approved_manifest.json")
    output_dir.mkdir(parents=True, exist_ok=True)
    common_manifest = {
        "runner_version": RUNNER_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed_dataset_sha256": stable_hash(list(seeds.values())),
        "approved_mechanisms_sha256": stable_hash(mechanisms),
        "review_version": approved_manifest.get("review_version"),
        "generator": _llm_identity(llm),
        "judge": _llm_identity(judge_llm),
        "candidate_count": options.candidate_count,
        "revision_rounds": options.revision_rounds,
        "six_dim_mode": options.six_dim_mode,
        "copycat_steps": options.copycat_steps,
        "copycat_temperature_threshold": options.copycat_temperature_threshold,
        "strategies": list(options.strategies),
        "concept_count": len(mechanisms),
    }
    write_json(output_dir / "manifest.json", common_manifest)

    results: dict[str, Any] = {}
    shared_context_hashes: dict[str, str] = {}
    for strategy in options.strategies:
        strategy_dir = output_dir / strategy
        strategy_result = _run_strategy(
            strategy=strategy,
            seeds=seeds,
            mechanisms=mechanisms,
            preparation_root=preparation_root,
            output_dir=strategy_dir,
            llm=llm,
            judge_llm=judge_llm,
            options=options,
            shared_context_hashes=shared_context_hashes,
        )
        results[strategy] = strategy_result
    write_json(output_dir / "run_result.json", results)
    return results


def _run_strategy(
    *,
    strategy: str,
    seeds: dict[str, dict[str, Any]],
    mechanisms: list[dict[str, Any]],
    preparation_root: Path,
    output_dir: Path,
    llm: ChatLLM,
    judge_llm: ChatLLM,
    options: ExperimentOptions,
    shared_context_hashes: dict[str, str],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    six_dim_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    for mechanism_record in mechanisms:
        concept_id = str(mechanism_record["concept_id"])
        try:
            seed = seeds.get(concept_id)
            if seed is None:
                raise ValueError("missing seed")
            retrieval = read_json(preparation_root / "retrieval" / f"{concept_id}.json")
            context = build_mapping_context(seed=seed, retrieval=retrieval, mechanism_record=mechanism_record)
            context_hash = stable_hash(context)
            previous = shared_context_hashes.setdefault(concept_id, context_hash)
            if previous != context_hash:
                raise ValueError("MappingContext mismatch across strategies")
            context_rows.append({"concept_id": concept_id, "mapping_context_sha256": context_hash})
            concept_dir = output_dir / "concepts" / concept_id
            write_json(concept_dir / "mapping_context.json", context)
            result = _run_concept(
                strategy=strategy,
                context=context,
                concept_dir=concept_dir,
                llm=llm,
                judge_llm=judge_llm,
                options=options,
            )
        except Exception as exc:
            invalid_rows.append(
                {
                    "concept_id": concept_id,
                    "strategy": strategy,
                    "generation_status": "invalid_for_official_eval",
                    "reason": "pipeline_exception",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        if not result["official_valid"]:
            invalid_rows.append(result["invalid_row"])
            continue
        records.append(result["record"])
        metric_rows.append(result["metrics"])
        six_dim_rows.append(result["six_dim"])
        summary_rows.append(result["summary_row"])
    write_jsonl(output_dir / "mapping_context_hashes.jsonl", context_rows)
    write_jsonl(output_dir / "invalid_for_official_eval.jsonl", invalid_rows)
    paths = export_run_reports(
        output_dir=output_dir,
        records=records,
        metric_rows=metric_rows,
        six_dim_rows=six_dim_rows,
        summary_rows=summary_rows,
        failed_rows=invalid_rows,
    )
    result = {
        **paths,
        "strategy": strategy,
        "approved_input_count": len(mechanisms),
        "official_count": len(records),
        "invalid_count": len(invalid_rows),
        "candidate_count": options.candidate_count,
        "revision_rounds": options.revision_rounds,
    }
    write_json(output_dir / "strategy_result.json", result)
    return result


def build_mapping_context(
    *,
    seed: dict[str, Any],
    retrieval: dict[str, Any],
    mechanism_record: dict[str, Any],
) -> dict[str, Any]:
    mechanism_retrieval = {
        **retrieval,
        "raw_edges": [
            edge
            for edge in retrieval.get("raw_edges", [])
            if isinstance(edge, dict) and edge.get("evidence_eligible", True)
        ],
    }
    concept_relations = build_concept_relation_graph(card=seed, retrieval_package=mechanism_retrieval)
    return {
        "schema_version": "m2na-mapping-context/v1",
        "seed": seed,
        "mechanism_graph": mechanism_record["mechanism_graph"],
        "generation_constraints": mechanism_record["generation_constraints"],
        "concept_relation_graph": concept_relations,
        "retrieval_summary": retrieval.get("topic_summary", {}),
        "retrieval_edge_ids": [
            edge.get("source_edge_id")
            for edge in mechanism_retrieval["raw_edges"]
            if edge.get("source_edge_id")
        ],
        "provenance": {
            "seed_sha256": stable_hash(seed),
            "retrieval_sha256": stable_hash(retrieval),
            "mechanism_record_sha256": stable_hash(mechanism_record),
        },
    }


def _run_concept(
    *,
    strategy: str,
    context: dict[str, Any],
    concept_dir: Path,
    llm: ChatLLM,
    judge_llm: ChatLLM,
    options: ExperimentOptions,
) -> dict[str, Any]:
    seed = context["seed"]
    concept_id = str(seed["concept_id"])
    graph = context["mechanism_graph"]
    card = _runtime_card(context)
    retrieval = {
        "topic_summary": {
            **context["retrieval_summary"],
            "typed_concept_relations": context["concept_relation_graph"],
        },
        "raw_edges": [],
        "target": {
            "source_node_id": concept_id,
            "name": seed["canonical_name"],
            "properties": {"definition": seed.get("definition", "")},
        },
    }
    planner = PlannerAgent(llm)
    generator = GeneratorAgent(llm)
    aligner = AlignerAgent(llm)
    reviser = ReviserAgent(llm)
    arbiter = ArbiterAgent(llm)
    judge = SixDimJudgeAgent(judge_llm)
    candidates: list[dict[str, Any]] = []
    fallback_events: list[dict[str, Any]] = []
    for index in range(1, options.candidate_count + 1):
        candidate_id = f"candidate_{index:03d}"
        candidate_dir = concept_dir / "candidates" / candidate_id
        if strategy == "copycat":
            mapping = build_copycat_plan(
                card=card,
                mechanism_graph=graph,
                concept_relation_graph=context["concept_relation_graph"],
                candidate_id=candidate_id,
                candidate_index=index,
                max_steps=options.copycat_steps,
            )
            plan = mapping["plan"]
            planner_call = {"status": "not_applicable"}
        else:
            plan = planner.plan(
                card=card,
                retrieval_package=retrieval,
                mechanism_graph=graph,
                candidate_index=index,
            )
            mapping = None
            planner_call = dict(planner.last_call)
        story = generator.generate(card=card, mechanism_graph=graph, plan=plan)
        if strategy == "copycat":
            story, repair_trace = repair_copycat_story(card=card, candidate_id=candidate_id, story=story)
        else:
            repair_trace = []
        alignment = aligner.align(mechanism_graph=graph, plan=plan, story=story)
        calls = {
            "planner": planner_call,
            "generator": dict(generator.last_call),
            "aligner": dict(aligner.last_call),
        }
        fallback_events.extend(_fallback_rows(candidate_id, calls))
        record = build_m2na_record(
            card=card,
            mechanism_graph=graph,
            narrative=story,
            alignment=alignment,
            method=f"m2na-v2-{strategy}",
        )
        metrics = evaluate_record(record)
        candidate = {
            "candidate_id": candidate_id,
            "plan": plan,
            "story": story,
            "alignment": alignment,
            "record": record,
            "automatic_metrics": metrics,
            "six_dim_eval": build_rule_six_dim_eval(
                concept_id=concept_id,
                target_concept=seed["canonical_name"],
                metrics=metrics,
            ),
        }
        candidates.append(candidate)
        write_json(candidate_dir / "narrative_plan.json", plan)
        (candidate_dir / "draft_story.txt").write_text(story, encoding="utf-8")
        write_json(candidate_dir / "alignment.json", alignment)
        write_json(candidate_dir / "automatic_metrics.json", metrics)
        write_json(candidate_dir / "agent_calls.json", calls)
        if mapping is not None:
            write_json(candidate_dir / "copycat_structures.json", mapping["structures"])
            write_json(candidate_dir / "copycat_codelet_trace.json", mapping["codelet_trace"])
            write_json(candidate_dir / "copycat_repair_trace.json", repair_trace)

    if fallback_events:
        return _invalid_result(concept_id, strategy, "candidate_agent_fallback", fallback_events, concept_dir)
    decision = (
        choose_copycat_candidate(
            candidates=candidates,
            mechanism_graph=graph,
            temperature_threshold=options.copycat_temperature_threshold,
        )
        if strategy == "copycat"
        else DecisionEngine(arbiter).choose(candidates)
    )
    if arbiter.last_call.get("status") == "fallback":
        return _invalid_result(concept_id, strategy, "arbiter_fallback", [arbiter.last_call], concept_dir)
    selected = decision["selected_candidate"]
    story = selected["story"]
    alignment = selected["alignment"]
    record = selected["record"]
    metrics = selected["automatic_metrics"]
    six_dim = _evaluate(
        mode=options.six_dim_mode,
        judge=judge,
        card=card,
        retrieval=retrieval,
        graph=graph,
        plan=selected["plan"],
        story=story,
        alignment=alignment,
        metrics=metrics,
    )
    if six_dim.get("mode") == "llm_failed_rules":
        return _invalid_result(concept_id, strategy, "judge_fallback", [six_dim], concept_dir)

    revision_history: list[dict[str, Any]] = []
    for round_index in range(1, options.revision_rounds + 1):
        reason = decision.get("revision_reason") if round_index == 1 else None
        reason = reason or revision_reason(metrics)
        if six_dim.get("final_status") == "accept" and not reason:
            break
        reason = reason or "六维评测未达到 accept，需要修订忠实度、映射和教学价值。"
        revised_story = reviser.revise(
            card=card,
            mechanism_graph=graph,
            plan=selected["plan"],
            story=story,
            failure_reason=reason,
        )
        revised_alignment = aligner.align(mechanism_graph=graph, plan=selected["plan"], story=revised_story)
        if reviser.last_call.get("status") == "fallback" or aligner.last_call.get("status") == "fallback":
            return _invalid_result(
                concept_id,
                strategy,
                "revision_agent_fallback",
                [reviser.last_call, aligner.last_call],
                concept_dir,
            )
        revised_record = build_m2na_record(
            card=card,
            mechanism_graph=graph,
            narrative=revised_story,
            alignment=revised_alignment,
            method=f"m2na-v2-{strategy}",
        )
        revised_metrics = evaluate_record(revised_record)
        revised_six_dim = _evaluate(
            mode=options.six_dim_mode,
            judge=judge,
            card=card,
            retrieval=retrieval,
            graph=graph,
            plan=selected["plan"],
            story=revised_story,
            alignment=revised_alignment,
            metrics=revised_metrics,
        )
        if revised_six_dim.get("mode") == "llm_failed_rules":
            return _invalid_result(concept_id, strategy, "judge_fallback", [revised_six_dim], concept_dir)
        improved = _result_key(revised_six_dim, revised_metrics) > _result_key(six_dim, metrics)
        revision_history.append({"round": round_index, "reason": reason, "improved": improved})
        if improved:
            story, alignment, record, metrics, six_dim = (
                revised_story,
                revised_alignment,
                revised_record,
                revised_metrics,
                revised_six_dim,
            )
        if six_dim.get("final_status") == "accept":
            break

    (concept_dir / "final_story.txt").write_text(story, encoding="utf-8")
    write_json(concept_dir / "final_alignment.json", alignment)
    write_json(concept_dir / "automatic_metrics.json", metrics)
    write_json(concept_dir / "six_dim_eval.json", six_dim)
    write_json(concept_dir / "decision.json", {key: value for key, value in decision.items() if key != "selected_candidate"})
    write_json(concept_dir / "revision_history.json", revision_history)
    status = {
        "concept_id": concept_id,
        "subject": seed["subject"],
        "strategy": strategy,
        "generation_status": "success",
        "evaluation_status": six_dim["final_status"],
        "selected_candidate_id": decision["winner_candidate_id"],
        "weighted_overall": six_dim["weighted_overall"],
        "six_dim_mode": six_dim["mode"],
        "revision_attempted_rounds": len(revision_history),
        "fallback_count": 0,
    }
    write_json(concept_dir / "status.json", status)
    return {
        "official_valid": True,
        "record": record,
        "metrics": metrics,
        "six_dim": six_dim,
        "summary_row": {**status, **metrics},
    }


def _runtime_card(context: dict[str, Any]) -> dict[str, Any]:
    seed = context["seed"]
    graph = context["mechanism_graph"]
    required = set(context["generation_constraints"].get("must_preserve_node_ids", []))
    node_texts = [str(node.get("text") or "") for node in graph.get("nodes", [])]
    preserve_texts = [
        str(node.get("text") or "") for node in graph.get("nodes", []) if node.get("id") in required
    ]
    return {
        "concept_id": seed["concept_id"],
        "subject": seed["subject"],
        "canonical_name": seed["canonical_name"],
        "definition": seed.get("definition", ""),
        "aliases": seed.get("aliases", []),
        "concept_type": seed["concept_type"],
        "forbidden_terms_zh": context["generation_constraints"].get("forbidden_terms", []),
        "core_mechanism_zh": node_texts,
        "must_preserve_zh": preserve_texts,
    }


def _evaluate(
    *,
    mode: str,
    judge: SixDimJudgeAgent,
    card: dict[str, Any],
    retrieval: dict[str, Any],
    graph: dict[str, Any],
    plan: dict[str, Any],
    story: str,
    alignment: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    if mode == "rules":
        return build_rule_six_dim_eval(
            concept_id=card["concept_id"],
            target_concept=card["canonical_name"],
            metrics=metrics,
        )
    return judge.evaluate(
        card=card,
        retrieval_package=retrieval,
        mechanism_graph=graph,
        narrative_plan=plan,
        story=story,
        alignment=alignment,
        automatic_metrics=metrics,
    )


def _invalid_result(
    concept_id: str,
    strategy: str,
    reason: str,
    details: list[Any],
    concept_dir: Path,
) -> dict[str, Any]:
    row = {
        "concept_id": concept_id,
        "strategy": strategy,
        "generation_status": "invalid_for_official_eval",
        "reason": reason,
        "details": details,
    }
    write_json(concept_dir / "status.json", row)
    return {"official_valid": False, "invalid_row": row}


def _fallback_rows(candidate_id: str, calls: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"candidate_id": candidate_id, "agent": name, **payload}
        for name, payload in calls.items()
        if isinstance(payload, dict) and payload.get("status") == "fallback"
    ]


def _result_key(six_dim: dict[str, Any], metrics: dict[str, Any]) -> tuple[float, float, float]:
    rank = {"reject": 0.0, "revise": 1.0, "accept": 2.0}.get(str(six_dim.get("final_status")), -1.0)
    metric_score = sum(
        float(metrics.get(key) or 0.0)
        for key in ("weighted_node_coverage", "weighted_edge_coverage", "alignment_precision")
    )
    return rank, float(six_dim.get("weighted_overall") or 0.0), metric_score


def _llm_identity(llm: ChatLLM) -> dict[str, Any]:
    identity: dict[str, Any] = {"class": f"{type(llm).__module__}.{type(llm).__qualname__}"}
    config = getattr(llm, "config", None)
    for key in ("provider", "base_url", "model", "temperature", "max_tokens"):
        if config is not None and hasattr(config, key):
            identity[key] = getattr(config, key)
    return identity


def _validate_options(options: ExperimentOptions) -> None:
    if not options.strategies or any(item not in {"standard", "copycat"} for item in options.strategies):
        raise ValueError("strategies must contain standard and/or copycat")
    if options.candidate_count != 3:
        raise ValueError("V2 official experiment fixes candidate_count at 3")
    if options.revision_rounds != 2:
        raise ValueError("V2 official experiment fixes revision_rounds at 2")
    if options.six_dim_mode not in {"rules", "llm"}:
        raise ValueError("six_dim_mode must be rules or llm")
