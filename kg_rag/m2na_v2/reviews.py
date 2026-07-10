from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.io import write_json
from kg_rag.m2na_v2.schemas import stable_hash


REVIEW_FIELDS = [
    "concept_id",
    "subject",
    "canonical_name",
    "concept_type",
    "validation_status",
    "validation_errors",
    "mechanism_nodes",
    "mechanism_edges",
    "review_decision",
    "reviewer",
    "notes",
]


def export_review_sheet(*, seeds_path: Path, output_root: Path, output_path: Path) -> dict[str, Any]:
    seeds = {str(item["concept_id"]): item for item in read_jsonl(seeds_path)}
    records = {str(item["concept_id"]): item for item in read_jsonl(output_root / "mechanisms.raw.jsonl")}
    validations = {
        str(item["concept_id"]): item for item in read_jsonl(output_root / "mechanism_validation.jsonl")
    }
    latest = latest_reviews(output_root / "mechanism_reviews.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for concept_id, seed in seeds.items():
            record = records.get(concept_id, {})
            validation = validations.get(concept_id, {"status": "missing", "errors": ["missing record"]})
            review = latest.get(concept_id, {})
            graph = record.get("mechanism_graph", {})
            writer.writerow(
                {
                    "concept_id": concept_id,
                    "subject": seed.get("subject"),
                    "canonical_name": seed.get("canonical_name"),
                    "concept_type": seed.get("concept_type"),
                    "validation_status": validation.get("status"),
                    "validation_errors": json.dumps(validation.get("errors", []), ensure_ascii=False),
                    "mechanism_nodes": json.dumps(graph.get("nodes", []), ensure_ascii=False),
                    "mechanism_edges": json.dumps(graph.get("edges", []), ensure_ascii=False),
                    "review_decision": review.get("decision", ""),
                    "reviewer": review.get("reviewer", ""),
                    "notes": review.get("notes", ""),
                }
            )
    result = {"output_path": str(output_path), "row_count": len(seeds)}
    write_json(output_path.with_suffix(".summary.json"), result)
    return result


def import_reviews(
    *,
    review_sheet_path: Path,
    seeds_path: Path,
    output_root: Path,
    default_reviewer: str | None = None,
) -> dict[str, Any]:
    valid_concepts = {str(item["concept_id"]) for item in read_jsonl(seeds_path)}
    review_path = output_root / "mechanism_reviews.jsonl"
    history = read_jsonl(review_path) if review_path.exists() else []
    existing_latest = latest_reviews(review_path)
    imported: list[dict[str, Any]] = []
    with review_sheet_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            concept_id = str(row.get("concept_id") or "").strip()
            decision = str(row.get("review_decision") or "").strip().lower()
            if not decision:
                continue
            if concept_id not in valid_concepts:
                raise ValueError(f"Review references unknown concept: {concept_id}")
            if decision not in {"approve", "reject"}:
                raise ValueError(f"Invalid review decision for {concept_id}: {decision}")
            reviewer = str(row.get("reviewer") or default_reviewer or "").strip()
            if not reviewer:
                raise ValueError(f"Reviewer is required for {concept_id}")
            notes = str(row.get("notes") or "").strip()
            previous = existing_latest.get(concept_id, {})
            if (
                previous.get("decision") == decision
                and previous.get("reviewer") == reviewer
                and previous.get("notes", "") == notes
            ):
                continue
            imported.append(
                {
                    "concept_id": concept_id,
                    "decision": decision,
                    "reviewer": reviewer,
                    "notes": notes,
                    "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )
    history.extend(imported)
    write_jsonl(review_path, history)
    approved_result = export_approved_records(output_root=output_root)
    result = {
        "imported_count": len(imported),
        "history_count": len(history),
        **approved_result,
    }
    write_json(output_root / "review_import.summary.json", result)
    return result


def append_review_decisions(
    *,
    decisions: list[dict[str, Any]],
    seeds_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Append changed review decisions and refresh the approved-record gate."""
    valid_concepts = {str(item["concept_id"]) for item in read_jsonl(seeds_path)}
    review_path = output_root / "mechanism_reviews.jsonl"
    history = read_jsonl(review_path) if review_path.exists() else []
    latest = latest_reviews(review_path)
    imported: list[dict[str, Any]] = []
    for item in decisions:
        concept_id = str(item.get("concept_id") or "").strip()
        decision = str(item.get("decision") or "").strip().lower()
        reviewer = str(item.get("reviewer") or "").strip()
        notes = str(item.get("notes") or "").strip()
        if concept_id not in valid_concepts:
            raise ValueError(f"Review references unknown concept: {concept_id}")
        if decision not in {"approve", "reject"}:
            raise ValueError(f"Invalid review decision for {concept_id}: {decision}")
        if not reviewer:
            raise ValueError(f"Reviewer is required for {concept_id}")
        previous = latest.get(concept_id, {})
        if (
            previous.get("decision") == decision
            and previous.get("reviewer") == reviewer
            and previous.get("notes", "") == notes
        ):
            continue
        imported.append(
            {
                "concept_id": concept_id,
                "decision": decision,
                "reviewer": reviewer,
                "notes": notes,
                "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
    history.extend(imported)
    write_jsonl(review_path, history)
    approved_result = export_approved_records(output_root=output_root)
    result = {
        "imported_count": len(imported),
        "history_count": len(history),
        **approved_result,
    }
    write_json(output_root / "review_import.summary.json", result)
    return result


def latest_reviews(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        concept_id = str(row.get("concept_id") or "")
        if concept_id:
            latest[concept_id] = row
    return latest


def export_approved_records(*, output_root: Path) -> dict[str, Any]:
    records = read_jsonl(output_root / "mechanisms.raw.jsonl")
    validations = {
        str(item["concept_id"]): item for item in read_jsonl(output_root / "mechanism_validation.jsonl")
    }
    latest = latest_reviews(output_root / "mechanism_reviews.jsonl")
    approved = [
        record
        for record in records
        if validations.get(str(record.get("concept_id")), {}).get("status") == "valid"
        and latest.get(str(record.get("concept_id")), {}).get("decision") == "approve"
    ]
    write_jsonl(output_root / "mechanisms.approved.jsonl", approved)
    review_rows = list(latest.values())
    result = {
        "approved_count": len(approved),
        "rejected_count": sum(1 for row in review_rows if row.get("decision") == "reject"),
        "review_version": stable_hash(review_rows),
    }
    write_json(output_root / "approved_manifest.json", result)
    return result


def pipeline_status(*, seeds_path: Path, output_root: Path) -> dict[str, Any]:
    def count(path: Path) -> int:
        return len(read_jsonl(path)) if path.exists() else 0

    latest = latest_reviews(output_root / "mechanism_reviews.jsonl")
    validations_path = output_root / "mechanism_validation.jsonl"
    validations = read_jsonl(validations_path) if validations_path.exists() else []
    approved_count = count(output_root / "mechanisms.approved.jsonl")
    return {
        "seed_count": count(seeds_path),
        "retrieval_count": count(output_root / "retrieval_index.jsonl"),
        "mechanism_count": count(output_root / "mechanisms.raw.jsonl"),
        "valid_count": sum(1 for row in validations if row.get("status") == "valid"),
        "invalid_count": sum(1 for row in validations if row.get("status") == "invalid"),
        "approved_count": approved_count,
        "review_approve_count": sum(1 for row in latest.values() if row.get("decision") == "approve"),
        "rejected_count": sum(1 for row in latest.values() if row.get("decision") == "reject"),
        "pending_review_count": max(0, count(seeds_path) - len(latest)),
        "failed_count": count(output_root / "failed_queue.jsonl"),
    }
