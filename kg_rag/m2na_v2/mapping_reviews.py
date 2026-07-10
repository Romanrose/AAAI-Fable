from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.io import write_json
from kg_rag.m2na_v2.schemas import stable_hash


def latest_mapping_reviews(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in read_jsonl(path):
        key = (
            str(row.get("concept_id") or ""),
            str(row.get("candidate_id") or ""),
            str(row.get("strategy") or ""),
        )
        if all(key):
            latest[key] = row
    return latest


def append_mapping_review(
    *,
    mapping_root: Path,
    concept_id: str,
    candidate_id: str,
    strategy: str,
    decision: str,
    reviewer: str,
    notes: str,
) -> dict[str, Any]:
    if strategy not in {"standard", "copycat"}:
        raise ValueError("strategy must be standard or copycat")
    if decision not in {"approve", "reject"}:
        raise ValueError("decision must be approve or reject")
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    plan_path = mapping_root / "concepts" / concept_id / candidate_id / f"{strategy}_mapping_plan.json"
    if not plan_path.exists():
        raise ValueError("mapping plan does not exist")
    review_path = mapping_root / "mapping_reviews.jsonl"
    history = read_jsonl(review_path) if review_path.exists() else []
    latest = latest_mapping_reviews(review_path)
    key = (concept_id, candidate_id, strategy)
    previous = latest.get(key, {})
    record = {
        "concept_id": concept_id,
        "candidate_id": candidate_id,
        "strategy": strategy,
        "decision": decision,
        "reviewer": reviewer.strip(),
        "notes": notes.strip(),
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if (
        previous.get("decision") == record["decision"]
        and previous.get("reviewer") == record["reviewer"]
        and previous.get("notes", "") == record["notes"]
    ):
        return {**mapping_review_status(mapping_root=mapping_root), "imported_count": 0}
    history.append(record)
    write_jsonl(review_path, history)
    status = mapping_review_status(mapping_root=mapping_root)
    write_json(mapping_root / "mapping_review_manifest.json", status)
    return {**status, "imported_count": 1}


def mapping_review_status(*, mapping_root: Path) -> dict[str, Any]:
    index_path = mapping_root / "mapping_plan_index.jsonl"
    plans = read_jsonl(index_path) if index_path.exists() else []
    latest = latest_mapping_reviews(mapping_root / "mapping_reviews.jsonl")
    keys = {
        (str(row.get("concept_id") or ""), str(row.get("candidate_id") or ""), str(row.get("strategy") or ""))
        for row in plans
    }
    approved = sum(1 for key in keys if latest.get(key, {}).get("decision") == "approve")
    rejected = sum(1 for key in keys if latest.get(key, {}).get("decision") == "reject")
    return {
        "plan_count": len(keys),
        "approved_count": approved,
        "rejected_count": rejected,
        "pending_count": len(keys) - approved - rejected,
        "review_version": stable_hash(list(latest.values())),
    }
