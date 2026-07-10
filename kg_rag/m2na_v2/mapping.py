from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.copycat.controller import build_copycat_plan
from kg_rag.io import read_json, write_json
from kg_rag.m2na_v2.runner import _runtime_card, build_mapping_context
from kg_rag.m2na_v2.schemas import stable_hash
from kg_rag.multi_agent.llm import ChatLLM, ensure_object, extract_json


MAPPING_SCHEMA_VERSION = "m2na-mapping-plan/v1"
STANDARD_PROMPT_VERSION = "standard-mapping-plan/v1"


def build_mapping_plans(
    *,
    seeds_path: Path,
    preparation_root: Path,
    output_root: Path,
    llm: ChatLLM,
    builder_identity: dict[str, Any],
    candidate_count: int = 3,
    only_missing: bool = False,
) -> dict[str, Any]:
    if candidate_count != 3:
        raise ValueError("V2 mapping stage fixes candidate_count at 3")
    seeds = {str(row["concept_id"]): row for row in read_jsonl(seeds_path)}
    approved = read_jsonl(preparation_root / "mechanisms.approved.jsonl")
    if not approved:
        raise ValueError("Approved mechanism dataset is empty")
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    shared_context_rows: list[dict[str, Any]] = []
    skipped_count = 0
    for record in approved:
        concept_id = str(record["concept_id"])
        seed = seeds.get(concept_id)
        if seed is None:
            failures.append({"concept_id": concept_id, "reason": "missing_seed"})
            continue
        retrieval = read_json(preparation_root / "retrieval" / f"{concept_id}.json")
        context = build_mapping_context(seed=seed, retrieval=retrieval, mechanism_record=record)
        context_hash = stable_hash(context)
        concept_dir = output_root / "concepts" / concept_id
        write_json(concept_dir / "mapping_context.json", context)
        shared_context_rows.append({"concept_id": concept_id, "mapping_context_sha256": context_hash})
        card = _runtime_card(context)
        for candidate_index in range(1, candidate_count + 1):
            candidate_id = f"candidate_{candidate_index:03d}"
            candidate_dir = concept_dir / candidate_id
            if only_missing:
                existing = _load_existing_pair(
                    candidate_dir=candidate_dir,
                    context=context,
                )
                if existing is not None:
                    rows.extend(existing)
                    skipped_count += 1
                    continue
            try:
                standard = _build_standard_plan(
                    llm=llm,
                    context=context,
                    candidate_id=candidate_id,
                    candidate_index=candidate_index,
                    builder_identity=builder_identity,
                )
                copycat_raw = build_copycat_plan(
                    card=card,
                    mechanism_graph=context["mechanism_graph"],
                    concept_relation_graph=context["concept_relation_graph"],
                    candidate_id=candidate_id,
                    candidate_index=candidate_index,
                )
                copycat = _normalize_copycat_plan(
                    plan=copycat_raw["plan"],
                    context=context,
                    candidate_id=candidate_id,
                    candidate_index=candidate_index,
                    builder_identity=builder_identity,
                )
                for plan in (standard, copycat):
                    errors = validate_mapping_plan(plan=plan, context=context)
                    if errors:
                        raise ValueError(f"{plan['strategy']} mapping invalid: {'; '.join(errors)}")
                    path = candidate_dir / f"{plan['strategy']}_mapping_plan.json"
                    write_json(path, plan)
                    rows.append(
                        {
                            "concept_id": concept_id,
                            "candidate_id": candidate_id,
                            "strategy": plan["strategy"],
                            "mapping_plan_sha256": stable_hash(plan),
                            "mapping_context_sha256": context_hash,
                            "path": str(path),
                        }
                    )
                write_json(candidate_dir / "copycat_structures.json", copycat_raw["structures"])
                write_json(candidate_dir / "copycat_codelet_trace.json", copycat_raw["codelet_trace"])
            except Exception as exc:
                failures.append(
                    {
                        "concept_id": concept_id,
                        "candidate_id": candidate_id,
                        "reason": "mapping_build_failed",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
    write_jsonl(output_root / "mapping_plan_index.jsonl", rows)
    write_jsonl(output_root / "mapping_failures.jsonl", failures)
    write_jsonl(output_root / "mapping_context_hashes.jsonl", shared_context_rows)
    result = {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "approved_concept_count": len(approved),
        "candidate_count": candidate_count,
        "only_missing": only_missing,
        "skipped_existing_candidate_count": skipped_count,
        "expected_plan_count": len(approved) * candidate_count * 2,
        "plan_count": len(rows),
        "failure_count": len(failures),
        "standard_builder": builder_identity,
        "standard_prompt_version": STANDARD_PROMPT_VERSION,
        "approved_mechanisms_sha256": stable_hash(approved),
    }
    write_json(output_root / "mapping_manifest.json", result)
    return result


def _load_existing_pair(
    *,
    candidate_dir: Path,
    context: dict[str, Any],
) -> list[dict[str, Any]] | None:
    plans: list[dict[str, Any]] = []
    for strategy in ("standard", "copycat"):
        path = candidate_dir / f"{strategy}_mapping_plan.json"
        if not path.exists():
            return None
        try:
            plan = read_json(path)
        except Exception:
            return None
        if validate_mapping_plan(plan=plan, context=context):
            return None
        plans.append(plan)
    return [
        {
            "concept_id": plan["concept_id"],
            "candidate_id": plan["candidate_id"],
            "strategy": plan["strategy"],
            "mapping_plan_sha256": stable_hash(plan),
            "mapping_context_sha256": stable_hash(context),
            "path": str(candidate_dir / f"{plan['strategy']}_mapping_plan.json"),
        }
        for plan in plans
    ]


def validate_mapping_plan(*, plan: dict[str, Any], context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("schema_version") != MAPPING_SCHEMA_VERSION:
        errors.append("invalid mapping schema version")
    if plan.get("concept_id") != context["seed"]["concept_id"]:
        errors.append("concept_id does not match context")
    if plan.get("mapping_context_sha256") != stable_hash(context):
        errors.append("mapping_context hash does not match")
    if plan.get("strategy") not in {"standard", "copycat"}:
        errors.append("invalid strategy")
    nodes = {str(item.get("id")) for item in context["mechanism_graph"].get("nodes", []) if isinstance(item, dict)}
    edges = {str(item.get("id")) for item in context["mechanism_graph"].get("edges", []) if isinstance(item, dict)}
    node_mappings = plan.get("node_mappings")
    edge_mappings = plan.get("edge_mappings")
    if not isinstance(node_mappings, list) or not node_mappings:
        errors.append("node_mappings must be a non-empty array")
        node_mappings = []
    if not isinstance(edge_mappings, list):
        errors.append("edge_mappings must be an array")
        edge_mappings = []
    mapped_nodes = {str(item.get("mechanism_node_id")) for item in node_mappings if isinstance(item, dict)}
    mapped_edges = {str(item.get("mechanism_edge_id")) for item in edge_mappings if isinstance(item, dict)}
    if any(node_id not in nodes for node_id in mapped_nodes):
        errors.append("node_mappings contains an unknown mechanism node")
    if any(edge_id not in edges for edge_id in mapped_edges):
        errors.append("edge_mappings contains an unknown mechanism edge")
    constraints = context["generation_constraints"]
    required_nodes = set(constraints.get("must_preserve_node_ids", []))
    required_edges = set(constraints.get("must_preserve_edge_ids", []))
    if not required_nodes.issubset(mapped_nodes):
        errors.append("must_preserve nodes are not all mapped")
    if not required_edges.issubset(mapped_edges):
        errors.append("must_preserve edges are not all mapped")
    for item in edge_mappings:
        if not isinstance(item, dict):
            continue
        if item.get("direction_preserved") is not True:
            errors.append("every mapped mechanism edge must preserve direction")
            break
    return errors


def _build_standard_plan(
    *,
    llm: ChatLLM,
    context: dict[str, Any],
    candidate_id: str,
    candidate_index: int,
    builder_identity: dict[str, Any],
) -> dict[str, Any]:
    system = "You are a structural analogy planner. Return strict JSON only."
    schema = {
        "source_domain": "...",
        "characters": ["..."],
        "objects": ["..."],
        "conflict": "...",
        "event_chain": ["..."],
        "turning_point": "...",
        "resolution_state": "...",
        "node_mappings": [
            {"mechanism_node_id": "n1", "story_carrier": "...", "mapping_type": "entity|condition|process|state|outcome|rule|evidence"}
        ],
        "edge_mappings": [
            {"mechanism_edge_id": "e1", "story_relation": "...", "direction_preserved": True}
        ],
        "risk_notes": ["..."],
    }
    prompt = {
        "task": "TASK:M2NA_V2_STANDARD_MAPPING_JSON",
        "candidate_index": candidate_index,
        "requirements": [
            "Build a Chinese fable analogy plan, not story prose.",
            "Map every must-preserve mechanism node and edge.",
            "Preserve every mapped mechanism edge direction.",
            "Do not treat curriculum bridge context as a causal mechanism.",
            "Do not use target concept names, aliases, or forbidden terms in proposed story carriers.",
            "Use one coherent source domain, not a list of unrelated metaphors.",
        ],
        "mapping_context": context,
        "output_schema": schema,
    }
    response = llm.complete(
        system_prompt=system,
        user_prompt=json.dumps(prompt, ensure_ascii=False, indent=2),
        max_tokens=1800,
        temperature=0.35,
    )
    payload = ensure_object(extract_json(response), context="standard mapping response")
    return _normalize_standard_plan(
        payload=payload,
        context=context,
        candidate_id=candidate_id,
        candidate_index=candidate_index,
        builder_identity=builder_identity,
        prompt_sha256=stable_hash({"system": system, "user": prompt}),
    )


def _normalize_standard_plan(
    *,
    payload: dict[str, Any],
    context: dict[str, Any],
    candidate_id: str,
    candidate_index: int,
    builder_identity: dict[str, Any],
    prompt_sha256: str,
) -> dict[str, Any]:
    return _base_plan(
        strategy="standard",
        payload=payload,
        context=context,
        candidate_id=candidate_id,
        candidate_index=candidate_index,
        provenance={
            "builder": builder_identity,
            "prompt_version": STANDARD_PROMPT_VERSION,
            "prompt_sha256": prompt_sha256,
        },
    )


def _normalize_copycat_plan(
    *,
    plan: dict[str, Any],
    context: dict[str, Any],
    candidate_id: str,
    candidate_index: int,
    builder_identity: dict[str, Any],
) -> dict[str, Any]:
    mapping_items = plan.get("mapping_plan", []) if isinstance(plan.get("mapping_plan"), list) else []
    node_mappings = [
        {
            "mechanism_node_id": item.get("mechanism_node_id"),
            "story_carrier": item.get("story_role"),
            "mapping_type": "structural_carrier",
        }
        for item in mapping_items
        if isinstance(item, dict) and item.get("mechanism_node_id")
    ]
    edge_mappings = [
        {
            "mechanism_edge_id": item.get("mechanism_edge_id"),
            "story_relation": item.get("story_relation"),
            "direction_preserved": True,
        }
        for item in mapping_items
        if isinstance(item, dict) and item.get("mechanism_edge_id")
    ]
    payload = {
        "source_domain": plan.get("source_domain"),
        "characters": plan.get("characters", []),
        "objects": plan.get("objects", []),
        "conflict": plan.get("conflict"),
        "event_chain": plan.get("event_chain", []),
        "turning_point": plan.get("turning_point"),
        "resolution_state": plan.get("resolution_state"),
        "node_mappings": node_mappings,
        "edge_mappings": edge_mappings,
        "risk_notes": plan.get("risk_notes", []),
    }
    return _base_plan(
        strategy="copycat",
        payload=payload,
        context=context,
        candidate_id=candidate_id,
        candidate_index=candidate_index,
        provenance={"builder": builder_identity, "algorithm": "copycat-inspired deterministic structure mapping"},
    )


def _base_plan(
    *,
    strategy: str,
    payload: dict[str, Any],
    context: dict[str, Any],
    candidate_id: str,
    candidate_index: int,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    def items(key: str) -> list[Any]:
        value = payload.get(key, [])
        return value if isinstance(value, list) else []

    return {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "concept_id": context["seed"]["concept_id"],
        "strategy": strategy,
        "candidate_id": candidate_id,
        "candidate_index": candidate_index,
        "source_domain": payload.get("source_domain"),
        "characters": items("characters"),
        "objects": items("objects"),
        "conflict": payload.get("conflict"),
        "event_chain": items("event_chain"),
        "turning_point": payload.get("turning_point"),
        "resolution_state": payload.get("resolution_state"),
        "node_mappings": items("node_mappings"),
        "edge_mappings": items("edge_mappings"),
        "risk_notes": items("risk_notes"),
        "mapping_context_sha256": stable_hash(context),
        "provenance": provenance,
    }
