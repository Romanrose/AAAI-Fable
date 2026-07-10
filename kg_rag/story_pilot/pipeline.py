from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.llm_guided_copycat.pipeline import run_one as run_guided_mapping
from kg_rag.m2na_v2.schemas import stable_hash
from kg_rag.multi_agent.llm import ChatLLM
from kg_rag.story_pilot.interfaces import align_story, apply_quality_gate, generate_story, judge_story, revise_story
from kg_rag.story_pilot.metrics import evaluate_alignment
from kg_rag.story_pilot.selection import PILOT12_IDS, subject_counts


PILOT_VERSION = "story-pilot-12x3x3/v1"
STRATEGIES = ("standard", "copycat", "llm_guided_copycat")


def prepare_guided_mappings(
    *,
    preparation_root: Path,
    output_root: Path,
    llm: ChatLLM,
    model_identity: dict[str, Any],
    workers: int = 3,
) -> dict[str, Any]:
    guided_root = output_root / "guided_mappings"
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def run(concept_id: str) -> dict[str, Any]:
        concept_dir = guided_root / concept_id
        result_path = concept_dir / "run_result.json"
        candidates_path = concept_dir / "candidate_evaluations.json"
        if result_path.exists() and candidates_path.exists():
            return read_json(result_path)
        return run_guided_mapping(
            concept_id=concept_id,
            preparation_root=preparation_root,
            output_dir=concept_dir,
            llm=llm,
            model_identity=model_identity,
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run, concept_id): concept_id for concept_id in PILOT12_IDS}
        for future in as_completed(futures):
            concept_id = futures[future]
            try:
                result = future.result()
                rows.append(
                    {
                        "concept_id": concept_id,
                        "candidate_count": result["candidate_count"],
                        "selected_candidate_id": result["selected_candidate_id"],
                        "path": str(guided_root / concept_id),
                    }
                )
            except Exception as exc:
                failures.append({"concept_id": concept_id, "error_type": type(exc).__name__, "error": str(exc)})
    rows.sort(key=lambda row: PILOT12_IDS.index(row["concept_id"]))
    write_jsonl(output_root / "guided_mapping_index.jsonl", rows)
    write_jsonl(output_root / "guided_mapping_failures.jsonl", failures)
    result = {
        "concept_count": len(rows),
        "failure_count": len(failures),
        "expected_concept_count": len(PILOT12_IDS),
        "model": model_identity,
    }
    write_json(output_root / "guided_mapping_manifest.json", result)
    return result


def run_initial_stories(
    *,
    preparation_root: Path,
    mapping_root: Path,
    pilot_root: Path,
    llm: ChatLLM,
    judge_llm: ChatLLM,
    model_identity: dict[str, Any],
    judge_identity: dict[str, Any],
    workers: int = 4,
) -> dict[str, Any]:
    inputs = _build_inputs(
        preparation_root=preparation_root,
        mapping_root=mapping_root,
        pilot_root=pilot_root,
    )
    pilot_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(pilot_root / "story_input_index.jsonl", inputs)
    completed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def run(item: dict[str, Any]) -> dict[str, Any]:
        output_dir = Path(item["output_dir"])
        status_path = output_dir / "status.json"
        if status_path.exists():
            status = read_json(status_path)
            if status.get("status") == "complete":
                return status
        mapping_plan = read_json(Path(item["mapping_plan_path"]))
        mechanism_record = read_json(Path(item["mechanism_record_path"]))
        seed = read_json(Path(item["seed_path"]))
        story_plan = _story_side_mapping(mapping_plan)
        forbidden_terms = list(seed.get("forbidden_terms", []))
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "frozen_mapping_plan.json", story_plan)
        story, generator_trace = generate_story(
            llm=llm,
            mapping_plan=story_plan,
            forbidden_terms=forbidden_terms,
        )
        (output_dir / "initial_story.txt").write_text(story, encoding="utf-8")
        alignment, aligner_trace = align_story(
            llm=llm,
            mechanism_graph=mechanism_record["mechanism_graph"],
            mapping_plan=story_plan,
            story=story,
        )
        metrics = evaluate_alignment(
            mechanism_graph=mechanism_record["mechanism_graph"],
            alignment=alignment,
            story=story,
            forbidden_terms=forbidden_terms,
        )
        judgment, judge_trace = judge_story(
            llm=judge_llm,
            mechanism_graph=mechanism_record["mechanism_graph"],
            mapping_plan=story_plan,
            story=story,
            alignment=alignment,
            metrics=metrics,
        )
        judgment = apply_quality_gate(judgment, metrics)
        write_json(output_dir / "alignment.json", alignment)
        write_json(output_dir / "automatic_metrics.json", metrics)
        write_json(output_dir / "judgment.json", judgment)
        write_json(
            output_dir / "agent_calls.json",
            {"generator": generator_trace, "aligner": aligner_trace, "judge": judge_trace},
        )
        status = {
            "status": "complete",
            "concept_id": item["concept_id"],
            "strategy": item["strategy"],
            "candidate_id": item["candidate_id"],
            "node_coverage": metrics["node_coverage"],
            "edge_coverage": metrics["edge_coverage"],
            "direction_accuracy": metrics["direction_accuracy"],
            "hard_leakage": metrics["hard_leakage"],
            "judge_status": judgment.get("final_status"),
            "output_dir": str(output_dir),
        }
        write_json(status_path, status)
        return status

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run, item): item for item in inputs}
        for future in as_completed(futures):
            item = futures[future]
            try:
                completed.append(future.result())
            except Exception as exc:
                failures.append(
                    {
                        "concept_id": item["concept_id"],
                        "strategy": item["strategy"],
                        "candidate_id": item["candidate_id"],
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
    completed.sort(key=lambda row: (PILOT12_IDS.index(row["concept_id"]), STRATEGIES.index(row["strategy"]), row["candidate_id"]))
    write_jsonl(pilot_root / "story_status.jsonl", completed)
    write_jsonl(pilot_root / "story_failures.jsonl", failures)
    analysis = analyze_results(pilot_root=pilot_root)
    manifest = {
        "pipeline_version": PILOT_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "concept_ids": PILOT12_IDS,
        "subject_counts": subject_counts(),
        "strategies": list(STRATEGIES),
        "candidate_count_per_strategy": 3,
        "expected_story_count": 108,
        "completed_story_count": len(completed),
        "failure_count": len(failures),
        "generator": model_identity,
        "judge": judge_identity,
        "input_index_sha256": stable_hash(inputs),
        "analysis": analysis,
    }
    write_json(pilot_root / "manifest.json", manifest)
    return manifest


def rejudge_stories(
    *,
    preparation_root: Path,
    pilot_root: Path,
    judge_llm: ChatLLM,
    judge_identity: dict[str, Any],
    workers: int = 4,
) -> dict[str, Any]:
    inputs = read_jsonl(pilot_root / "story_input_index.jsonl")
    completed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def run(item: dict[str, Any]) -> dict[str, Any]:
        output_dir = Path(item["output_dir"])
        v2_path = output_dir / "judgment_v2.json"
        mapping_plan = read_json(output_dir / "frozen_mapping_plan.json")
        mechanism = read_json(Path(item["mechanism_record_path"]))
        story = (output_dir / "initial_story.txt").read_text(encoding="utf-8")
        alignment = read_json(output_dir / "alignment.json")
        metrics = evaluate_alignment(
            mechanism_graph=mechanism["mechanism_graph"],
            alignment=alignment,
            story=story,
            forbidden_terms=read_json(Path(item["seed_path"])).get("forbidden_terms", []),
        )
        if v2_path.exists():
            judgment = read_json(v2_path)
        else:
            judgment, trace = judge_story(
                llm=judge_llm,
                mechanism_graph=mechanism["mechanism_graph"],
                mapping_plan=mapping_plan,
                story=story,
                alignment=alignment,
                metrics=metrics,
            )
            judgment = apply_quality_gate(judgment, metrics)
            if not (output_dir / "judgment_v1.json").exists() and (output_dir / "judgment.json").exists():
                write_json(output_dir / "judgment_v1.json", read_json(output_dir / "judgment.json"))
            write_json(v2_path, judgment)
            write_json(output_dir / "judge_v2_call.json", trace)
        write_json(output_dir / "judgment.json", judgment)
        write_json(output_dir / "automatic_metrics.json", metrics)
        status = read_json(output_dir / "status.json")
        status.update(
            {
                "node_coverage": metrics["node_coverage"],
                "edge_coverage": metrics["edge_coverage"],
                "direction_accuracy": metrics["direction_accuracy"],
                "hard_leakage": metrics["hard_leakage"],
                "length_valid": metrics["length_valid"],
                "judge_status": judgment["final_status"],
                "judge_raw_status": judgment.get("raw_final_status"),
                "quality_gate_reasons": judgment.get("quality_gate", {}).get("reasons", []),
            }
        )
        write_json(output_dir / "status.json", status)
        return status

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run, item): item for item in inputs}
        for future in as_completed(futures):
            item = futures[future]
            try:
                completed.append(future.result())
            except Exception as exc:
                failures.append(
                    {
                        "concept_id": item["concept_id"],
                        "strategy": item["strategy"],
                        "candidate_id": item["candidate_id"],
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
    completed.sort(key=lambda row: (PILOT12_IDS.index(row["concept_id"]), STRATEGIES.index(row["strategy"]), row["candidate_id"]))
    write_jsonl(pilot_root / "story_status.jsonl", completed)
    write_jsonl(pilot_root / "rejudge_failures.jsonl", failures)
    result = {
        "story_count": len(completed),
        "failure_count": len(failures),
        "judge": judge_identity,
        "analysis": analyze_results(pilot_root=pilot_root),
    }
    write_json(pilot_root / "rejudge_manifest.json", result)
    return result


def run_revisions(
    *,
    pilot_root: Path,
    llm: ChatLLM,
    judge_llm: ChatLLM,
    model_identity: dict[str, Any],
    judge_identity: dict[str, Any],
    workers: int = 4,
) -> dict[str, Any]:
    inputs = read_jsonl(pilot_root / "story_input_index.jsonl")
    completed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def run(item: dict[str, Any]) -> dict[str, Any]:
        output_dir = Path(item["output_dir"])
        final_status_path = output_dir / "final_status.json"
        if final_status_path.exists():
            return read_json(final_status_path)
        mapping_plan = read_json(output_dir / "frozen_mapping_plan.json")
        mechanism = read_json(Path(item["mechanism_record_path"]))
        seed = read_json(Path(item["seed_path"]))
        initial_story = (output_dir / "initial_story.txt").read_text(encoding="utf-8")
        initial_alignment = read_json(output_dir / "alignment.json")
        initial_metrics = read_json(output_dir / "automatic_metrics.json")
        initial_judgment = read_json(output_dir / "judgment.json")
        chosen = {
            "story": initial_story,
            "alignment": initial_alignment,
            "metrics": initial_metrics,
            "judgment": initial_judgment,
            "source": "initial",
        }
        revision_attempted = initial_judgment.get("final_status") != "accept"
        improved = False
        if revision_attempted:
            revision_dir = output_dir / "revisions" / "round_001"
            revised_story, reviser_trace = revise_story(
                llm=llm,
                mapping_plan=mapping_plan,
                story=initial_story,
                alignment=initial_alignment,
                judgment=initial_judgment,
                metrics=initial_metrics,
                forbidden_terms=seed.get("forbidden_terms", []),
            )
            revised_alignment, aligner_trace = align_story(
                llm=llm,
                mechanism_graph=mechanism["mechanism_graph"],
                mapping_plan=mapping_plan,
                story=revised_story,
            )
            revised_metrics = evaluate_alignment(
                mechanism_graph=mechanism["mechanism_graph"],
                alignment=revised_alignment,
                story=revised_story,
                forbidden_terms=seed.get("forbidden_terms", []),
            )
            revised_judgment, judge_trace = judge_story(
                llm=judge_llm,
                mechanism_graph=mechanism["mechanism_graph"],
                mapping_plan=mapping_plan,
                story=revised_story,
                alignment=revised_alignment,
                metrics=revised_metrics,
            )
            revised_judgment = apply_quality_gate(revised_judgment, revised_metrics)
            revision_dir.mkdir(parents=True, exist_ok=True)
            (revision_dir / "story.txt").write_text(revised_story, encoding="utf-8")
            write_json(revision_dir / "alignment.json", revised_alignment)
            write_json(revision_dir / "automatic_metrics.json", revised_metrics)
            write_json(revision_dir / "judgment.json", revised_judgment)
            write_json(
                revision_dir / "agent_calls.json",
                {"reviser": reviser_trace, "aligner": aligner_trace, "judge": judge_trace},
            )
            revised = {
                "story": revised_story,
                "alignment": revised_alignment,
                "metrics": revised_metrics,
                "judgment": revised_judgment,
                "source": "revision_001",
            }
            improved = _quality_key(revised) > _quality_key(chosen)
            if improved:
                chosen = revised
        (output_dir / "final_story.txt").write_text(chosen["story"], encoding="utf-8")
        write_json(output_dir / "final_alignment.json", chosen["alignment"])
        write_json(output_dir / "final_metrics.json", chosen["metrics"])
        write_json(output_dir / "final_judgment.json", chosen["judgment"])
        status = {
            "status": "complete",
            "concept_id": item["concept_id"],
            "strategy": item["strategy"],
            "candidate_id": item["candidate_id"],
            "selected_source": chosen["source"],
            "revision_attempted": revision_attempted,
            "revision_improved": improved,
            "node_coverage": chosen["metrics"]["node_coverage"],
            "edge_coverage": chosen["metrics"]["edge_coverage"],
            "direction_accuracy": chosen["metrics"]["direction_accuracy"],
            "hard_leakage": chosen["metrics"]["hard_leakage"],
            "length_valid": chosen["metrics"].get("length_valid", False),
            "judge_status": chosen["judgment"]["final_status"],
            "output_dir": str(output_dir),
        }
        write_json(final_status_path, status)
        return status

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run, item): item for item in inputs}
        for future in as_completed(futures):
            item = futures[future]
            try:
                completed.append(future.result())
            except Exception as exc:
                failures.append(
                    {
                        "concept_id": item["concept_id"],
                        "strategy": item["strategy"],
                        "candidate_id": item["candidate_id"],
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
    completed.sort(key=lambda row: (PILOT12_IDS.index(row["concept_id"]), STRATEGIES.index(row["strategy"]), row["candidate_id"]))
    write_jsonl(pilot_root / "final_story_status.jsonl", completed)
    write_jsonl(pilot_root / "revision_failures.jsonl", failures)
    result = {
        "story_count": len(completed),
        "failure_count": len(failures),
        "revision_attempted_count": sum(bool(row.get("revision_attempted")) for row in completed),
        "revision_improved_count": sum(bool(row.get("revision_improved")) for row in completed),
        "generator_reviser": model_identity,
        "judge": judge_identity,
        "analysis": _analyze_status_rows(completed),
    }
    write_json(pilot_root / "revision_manifest.json", result)
    return result


def analyze_results(*, pilot_root: Path) -> dict[str, Any]:
    status_path = pilot_root / "story_status.jsonl"
    rows = read_jsonl(status_path) if status_path.exists() else []
    by_strategy: dict[str, dict[str, Any]] = {}
    for strategy in STRATEGIES:
        subset = [row for row in rows if row.get("strategy") == strategy]
        by_strategy[strategy] = {
            "count": len(subset),
            "mean_node_coverage": _mean(subset, "node_coverage"),
            "mean_edge_coverage": _mean(subset, "edge_coverage"),
            "mean_direction_accuracy": _mean(subset, "direction_accuracy"),
            "accept_count": sum(row.get("judge_status") == "accept" for row in subset),
            "revise_count": sum(row.get("judge_status") == "revise" for row in subset),
            "reject_count": sum(row.get("judge_status") == "reject" for row in subset),
            "leakage_count": sum(bool(row.get("hard_leakage")) for row in subset),
        }
    return {"by_strategy": by_strategy}


def _analyze_status_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_strategy: dict[str, Any] = {}
    for strategy in STRATEGIES:
        subset = [row for row in rows if row.get("strategy") == strategy]
        by_strategy[strategy] = {
            "count": len(subset),
            "mean_node_coverage": _mean(subset, "node_coverage"),
            "mean_edge_coverage": _mean(subset, "edge_coverage"),
            "accept_count": sum(row.get("judge_status") == "accept" for row in subset),
            "revise_count": sum(row.get("judge_status") == "revise" for row in subset),
            "reject_count": sum(row.get("judge_status") == "reject" for row in subset),
            "revision_improved_count": sum(bool(row.get("revision_improved")) for row in subset),
            "leakage_count": sum(bool(row.get("hard_leakage")) for row in subset),
        }
    return {"by_strategy": by_strategy}


def _quality_key(value: dict[str, Any]) -> tuple[float, float, float, float]:
    judgment = value["judgment"]
    metrics = value["metrics"]
    status_rank = {"reject": 0.0, "revise": 1.0, "accept": 2.0}.get(str(judgment.get("final_status")), -1.0)
    scores = judgment.get("scores", {}) if isinstance(judgment.get("scores"), dict) else {}
    mean_score = sum(float(scores.get(key) or 0.0) for key in ("faithfulness", "mapping_clarity", "readability")) / 3.0
    return (
        status_rank,
        float(metrics.get("node_coverage") or 0.0) + float(metrics.get("edge_coverage") or 0.0),
        float(metrics.get("direction_accuracy") or 0.0),
        mean_score,
    )


def _build_inputs(*, preparation_root: Path, mapping_root: Path, pilot_root: Path) -> list[dict[str, Any]]:
    seeds = {str(row["concept_id"]): row for row in read_jsonl(preparation_root / "seeds.jsonl")}
    mechanisms = {
        str(row["concept_id"]): row for row in read_jsonl(preparation_root / "mechanisms.approved.jsonl")
    }
    input_root = pilot_root / "inputs"
    inputs: list[dict[str, Any]] = []
    for concept_id in PILOT12_IDS:
        seed_path = input_root / concept_id / "seed.json"
        mechanism_path = input_root / concept_id / "mechanism_record.json"
        write_json(seed_path, seeds[concept_id])
        write_json(mechanism_path, mechanisms[concept_id])
        guided_dir = pilot_root / "guided_mappings" / concept_id
        guided_rows = read_json(guided_dir / "candidate_evaluations.json")
        guided_result = read_json(guided_dir / "run_result.json")
        guided_candidates = {
            str(row["candidate"].get("candidate_id")): row["candidate"]
            for row in guided_rows
            if isinstance(row, dict) and isinstance(row.get("candidate"), dict)
        }
        guided_candidates[str(guided_result["selected_candidate_id"])] = guided_result["selected_mapping"]
        for index in range(1, 4):
            candidate_id = f"candidate_{index:03d}"
            for strategy in ("standard", "copycat"):
                plan_path = mapping_root / "concepts" / concept_id / candidate_id / f"{strategy}_mapping_plan.json"
                inputs.append(
                    _input_row(
                        concept_id=concept_id,
                        strategy=strategy,
                        candidate_id=candidate_id,
                        plan_path=plan_path,
                        seed_path=seed_path,
                        mechanism_path=mechanism_path,
                        pilot_root=pilot_root,
                    )
                )
            guided_path = input_root / concept_id / f"{candidate_id}_llm_guided_mapping.json"
            if candidate_id not in guided_candidates:
                raise ValueError(f"Missing guided mapping {concept_id}/{candidate_id}")
            write_json(guided_path, guided_candidates[candidate_id])
            inputs.append(
                _input_row(
                    concept_id=concept_id,
                    strategy="llm_guided_copycat",
                    candidate_id=candidate_id,
                    plan_path=guided_path,
                    seed_path=seed_path,
                    mechanism_path=mechanism_path,
                    pilot_root=pilot_root,
                )
            )
    return inputs


def _input_row(
    *,
    concept_id: str,
    strategy: str,
    candidate_id: str,
    plan_path: Path,
    seed_path: Path,
    mechanism_path: Path,
    pilot_root: Path,
) -> dict[str, Any]:
    return {
        "concept_id": concept_id,
        "strategy": strategy,
        "candidate_id": candidate_id,
        "mapping_plan_path": str(plan_path),
        "seed_path": str(seed_path),
        "mechanism_record_path": str(mechanism_path),
        "output_dir": str(pilot_root / "stories" / concept_id / strategy / candidate_id),
    }


def _story_side_mapping(plan: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "candidate_id",
        "source_domain",
        "domain_rationale",
        "characters",
        "objects",
        "conflict",
        "event_chain",
        "turning_point",
        "resolution_state",
        "node_mappings",
        "edge_mappings",
        "risk_notes",
    )
    return {key: plan[key] for key in fields if key in plan}


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(float(row.get(key) or 0.0) for row in rows) / len(rows), 4)
