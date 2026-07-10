from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.llm_guided_copycat.scoring import score_candidate, validate_candidate
from kg_rag.m2na_v2.runner import build_mapping_context
from kg_rag.m2na_v2.schemas import stable_hash
from kg_rag.multi_agent.llm import ChatLLM, ensure_object, extract_json


PIPELINE_VERSION = "llm-guided-copycat-mvp/v1"
PROMPT_VERSION = "semantic-scout/v1"
REFINER_PROMPT_VERSION = "meta-monitor-refiner/v1"


def run_one(
    *,
    concept_id: str,
    preparation_root: Path,
    output_dir: Path,
    llm: ChatLLM,
    model_identity: dict[str, Any],
) -> dict[str, Any]:
    context = _load_context(concept_id=concept_id, preparation_root=preparation_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "mapping_context.json", context)
    proposals, scout_trace = _propose_candidates(llm=llm, context=context, model_identity=model_identity)
    evaluated = [
        {"candidate": candidate, "evaluation": score_candidate(candidate, context)}
        for candidate in proposals
    ]
    evaluated.sort(key=lambda item: (-float(item["evaluation"]["score"]), str(item["candidate"].get("candidate_id"))))
    if not evaluated:
        raise ValueError("Semantic scout returned no candidates")
    initial_winner = evaluated[0]
    winner = initial_winner
    refiner_trace: dict[str, Any] = {"status": "not_needed"}
    if initial_winner["evaluation"]["template_issues"]:
        refined, refiner_trace = _refine_candidate(
            llm=llm,
            context=context,
            candidate=initial_winner["candidate"],
            issues=initial_winner["evaluation"]["template_issues"],
            model_identity=model_identity,
        )
        refined_evaluation = score_candidate(refined, context)
        if not refined_evaluation["validation_errors"] and refined_evaluation["score"] >= initial_winner["evaluation"]["score"]:
            winner = {"candidate": refined, "evaluation": refined_evaluation}
            refiner_trace["accepted"] = True
        else:
            refiner_trace["accepted"] = False
            refiner_trace["rejection_reason"] = "refinement did not improve a valid candidate"
    final_errors = validate_candidate(winner["candidate"], context)
    if final_errors:
        raise ValueError("Winning mapping is invalid: " + "; ".join(final_errors))
    result = {
        "pipeline_version": PIPELINE_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "concept_id": concept_id,
        "mapping_context_sha256": stable_hash(context),
        "candidate_count": len(evaluated),
        "selected_candidate_id": winner["candidate"].get("candidate_id"),
        "selected_mapping": winner["candidate"],
        "selected_evaluation": winner["evaluation"],
        "scout_trace": scout_trace,
        "refiner_trace": refiner_trace,
        "model": model_identity,
    }
    write_json(output_dir / "candidate_evaluations.json", evaluated)
    write_json(output_dir / "selected_mapping_plan.json", winner["candidate"])
    write_json(output_dir / "run_result.json", result)
    return result


def _load_context(*, concept_id: str, preparation_root: Path) -> dict[str, Any]:
    seeds = {str(row["concept_id"]): row for row in read_jsonl(preparation_root / "seeds.jsonl")}
    records = {
        str(row["concept_id"]): row
        for row in read_jsonl(preparation_root / "mechanisms.approved.jsonl")
    }
    seed = seeds.get(concept_id)
    record = records.get(concept_id)
    if seed is None:
        raise ValueError(f"Unknown ConceptSeed: {concept_id}")
    if record is None:
        raise ValueError(f"Concept is not in approved mechanisms: {concept_id}")
    retrieval = read_json(preparation_root / "retrieval" / f"{concept_id}.json")
    return build_mapping_context(seed=seed, retrieval=retrieval, mechanism_record=record)


def _propose_candidates(
    *,
    llm: ChatLLM,
    context: dict[str, Any],
    model_identity: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    schema = {
        "candidates": [
            {
                "candidate_id": "candidate_001",
                "source_domain": "...",
                "domain_rationale": "...",
                "conflict": "...",
                "event_chain": ["..."],
                "turning_point": "...",
                "resolution_state": "...",
                "node_mappings": [
                    {"mechanism_node_id": "n1", "story_carrier": "...", "mapping_type": "..."}
                ],
                "edge_mappings": [
                    {"mechanism_edge_id": "e1", "story_relation": "...", "direction_preserved": True}
                ],
            }
        ]
    }
    prompt = {
        "task": "TASK:LLM_GUIDED_COPYCAT_SCOUT",
        "requirements": [
            "Return exactly three coherent Chinese fable mapping candidates, not story prose.",
            "Use a different source domain for each candidate.",
            "Map every mechanism node and every mechanism edge, including all must-preserve structure, and preserve edge direction.",
            "Use specific story carriers; never use ordinal placeholders such as 第2道环节.",
            "Give each mechanism edge a distinguishable story relation.",
            "Do not use target concept names, aliases, or forbidden terms in story-side text.",
            "Curriculum bridge context is not a mechanism relation.",
        ],
        "mapping_context": context,
        "output_schema": schema,
    }
    system = "You are a semantic scout for an LLM-guided Copycat-inspired analogy system. Return strict JSON only."
    response = llm.complete(
        system_prompt=system,
        user_prompt=json.dumps(prompt, ensure_ascii=False, indent=2),
        max_tokens=3600,
        temperature=0.75,
    )
    payload = ensure_object(extract_json(response), context="semantic scout response")
    candidates = [item for item in payload.get("candidates", []) if isinstance(item, dict)]
    return candidates, {
        "status": "success",
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": stable_hash({"system": system, "user": prompt}),
        "model": model_identity,
    }


def _refine_candidate(
    *,
    llm: ChatLLM,
    context: dict[str, Any],
    candidate: dict[str, Any],
    issues: list[str],
    model_identity: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = {
        "task": "TASK:LLM_GUIDED_COPYCAT_META_REFINER",
        "issues": issues,
        "requirements": [
            "Return one corrected mapping candidate as JSON only.",
            "Keep candidate_id, source_domain, every mechanism_node_id and mechanism_edge_id unchanged.",
            "Keep all edge directions true.",
            "Replace repeated, generic, or ordinal story carriers and relations with specific distinct realizations.",
            "Do not add or delete mechanism structure.",
        ],
        "mapping_context": context,
        "candidate": candidate,
    }
    system = "You are a meta-monitor that repairs repetitive analogy mappings without changing their deep structure."
    response = llm.complete(
        system_prompt=system,
        user_prompt=json.dumps(prompt, ensure_ascii=False, indent=2),
        max_tokens=2200,
        temperature=0.35,
    )
    refined = ensure_object(extract_json(response), context="meta-monitor refiner response")
    return refined, {
        "status": "success",
        "prompt_version": REFINER_PROMPT_VERSION,
        "prompt_sha256": stable_hash({"system": system, "user": prompt}),
        "model": model_identity,
        "issues": issues,
    }
