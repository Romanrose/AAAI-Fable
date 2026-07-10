from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import append_jsonl, read_jsonl
from kg_rag.io import write_json
from kg_rag.story_pilot.pipeline import STRATEGIES
from kg_rag.story_pilot.selection import PILOT12_IDS


ReviewKey = tuple[str, str, str]


def latest_story_reviews(path: Path) -> dict[ReviewKey, dict[str, Any]]:
    if not path.exists():
        return {}
    latest: dict[ReviewKey, dict[str, Any]] = {}
    for row in read_jsonl(path):
        key = _review_key(row)
        if all(key):
            latest[key] = row
    return latest


def append_story_review(
    *,
    pilot_root: Path,
    concept_id: str,
    strategy: str,
    candidate_id: str,
    decision: str,
    reviewer: str,
    notes: str = "",
    preferred: bool = False,
) -> dict[str, Any]:
    concept_id = concept_id.strip()
    strategy = strategy.strip()
    candidate_id = candidate_id.strip()
    decision = decision.strip().lower()
    reviewer = reviewer.strip()
    notes = notes.strip()
    _validate_identity(
        pilot_root=pilot_root,
        concept_id=concept_id,
        strategy=strategy,
        candidate_id=candidate_id,
    )
    if decision not in {"approve", "reject"}:
        raise ValueError(f"Invalid story review decision: {decision}")
    if not reviewer:
        raise ValueError("Reviewer is required.")
    if preferred and decision != "approve":
        raise ValueError("A preferred story must also be approved.")

    review_path = pilot_root / "story_reviews.jsonl"
    latest = latest_story_reviews(review_path)
    now = datetime.now(timezone.utc).isoformat()
    if preferred:
        for key, previous in latest.items():
            if key[:2] != (concept_id, strategy) or key[2] == candidate_id:
                continue
            if previous.get("preferred"):
                append_jsonl(
                    review_path,
                    {
                        **previous,
                        "preferred": False,
                        "reviewer": reviewer,
                        "reviewed_at_utc": now,
                        "superseded_by_candidate_id": candidate_id,
                    },
                )

    row = {
        "concept_id": concept_id,
        "strategy": strategy,
        "candidate_id": candidate_id,
        "decision": decision,
        "preferred": preferred,
        "reviewer": reviewer,
        "notes": notes,
        "reviewed_at_utc": now,
    }
    previous = latest.get((concept_id, strategy, candidate_id), {})
    comparable_fields = ("decision", "preferred", "reviewer", "notes")
    if all(previous.get(field) == row.get(field) for field in comparable_fields):
        return story_review_status(pilot_root=pilot_root)
    append_jsonl(review_path, row)
    status = story_review_status(pilot_root=pilot_root)
    write_json(pilot_root / "story_review_manifest.json", status)
    return status


def story_review_status(*, pilot_root: Path) -> dict[str, Any]:
    final_status_path = pilot_root / "final_story_status.jsonl"
    candidates = read_jsonl(final_status_path) if final_status_path.exists() else []
    latest = latest_story_reviews(pilot_root / "story_reviews.jsonl")
    known_keys = {
        (str(row.get("concept_id")), str(row.get("strategy")), str(row.get("candidate_id")))
        for row in candidates
    }
    reviews = [row for key, row in latest.items() if key in known_keys]
    return {
        "story_count": len(candidates),
        "reviewed_count": len(reviews),
        "pending_count": max(0, len(candidates) - len(reviews)),
        "approved_count": sum(row.get("decision") == "approve" for row in reviews),
        "rejected_count": sum(row.get("decision") == "reject" for row in reviews),
        "preferred_count": sum(
            row.get("decision") == "approve" and bool(row.get("preferred")) for row in reviews
        ),
    }


def _validate_identity(*, pilot_root: Path, concept_id: str, strategy: str, candidate_id: str) -> None:
    if concept_id not in PILOT12_IDS:
        raise ValueError(f"Unknown pilot concept: {concept_id}")
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown story strategy: {strategy}")
    if candidate_id not in {"candidate_001", "candidate_002", "candidate_003"}:
        raise ValueError(f"Unknown story candidate: {candidate_id}")
    output_dir = pilot_root / "stories" / concept_id / strategy / candidate_id
    if not (output_dir / "final_status.json").exists():
        raise ValueError(f"Final story does not exist: {concept_id}/{strategy}/{candidate_id}")


def _review_key(row: dict[str, Any]) -> ReviewKey:
    return (
        str(row.get("concept_id") or ""),
        str(row.get("strategy") or ""),
        str(row.get("candidate_id") or ""),
    )
