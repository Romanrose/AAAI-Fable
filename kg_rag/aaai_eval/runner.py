from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kg_rag.aaai_eval.adapters.base import MethodRunContext
from kg_rag.aaai_eval.registry import AdapterRegistry, default_registry
from kg_rag.aaai_eval.schemas import (
    load_protocol,
    validate_dataset_row,
    validate_evaluation_record,
)
from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.io import write_json
from kg_rag.m2na_v2.schemas import stable_hash


RUNNER_VERSION = "aaai-eval-runner/v1"


def run_evaluation(
    *, protocol_path: Path, registry: AdapterRegistry | None = None
) -> dict[str, Any]:
    registry = registry or default_registry()
    protocol = load_protocol(protocol_path)
    dataset = read_jsonl(protocol.dataset_path)
    _validate_dataset(dataset)
    output_root = protocol.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for method in protocol.methods:
        try:
            adapter = registry.create(method, base_dir=protocol.base_dir)
        except Exception as exc:
            failures.append(_failure(method.method_id, None, "adapter_init_failed", exc))
            continue
        for dataset_row in dataset:
            concept_id = str(dataset_row["concept_id"])
            context = MethodRunContext(
                protocol=protocol,
                method=method,
                dataset_row=dataset_row,
                method_output_dir=output_root / "methods" / method.method_id / concept_id,
            )
            try:
                method_records = adapter.run(context)
                if len(method_records) != protocol.budget.candidate_count:
                    raise ValueError(
                        f"expected {protocol.budget.candidate_count} records, "
                        f"received {len(method_records)}"
                    )
                for record in method_records:
                    errors = validate_evaluation_record(record)
                    if errors:
                        raise ValueError("; ".join(errors))
                    records.append(record)
            except Exception as exc:
                failures.append(_failure(method.method_id, concept_id, "method_run_failed", exc))
    method_counts = Counter(record["method_id"] for record in records)
    expected_per_method = len(dataset) * protocol.budget.candidate_count
    fairness = {
        method.method_id: {
            "expected_record_count": expected_per_method,
            "actual_record_count": method_counts.get(method.method_id, 0),
            "budget_complete": method_counts.get(method.method_id, 0) == expected_per_method,
        }
        for method in protocol.methods
    }
    records.sort(
        key=lambda row: (
            str(row["concept_id"]),
            [method.method_id for method in protocol.methods].index(str(row["method_id"])),
            str(row["candidate_id"]),
        )
    )
    write_jsonl(output_root / "evaluation_records.jsonl", records)
    write_jsonl(output_root / "evaluation_failures.jsonl", failures)
    manifest = {
        "runner_version": RUNNER_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": protocol.experiment_id,
        "dataset_id": protocol.dataset_id,
        "protocol_path": str(protocol_path.resolve()),
        "protocol_sha256": protocol.protocol_hash,
        "dataset_path": str(protocol.dataset_path),
        "dataset_sha256": stable_hash(dataset),
        "concept_count": len(dataset),
        "method_count": len(protocol.methods),
        "record_count": len(records),
        "failure_count": len(failures),
        "expected_record_count": expected_per_method * len(protocol.methods),
        "official_ready": not failures and all(row["budget_complete"] for row in fairness.values()),
        "fairness": fairness,
        "methods": [method.to_dict() for method in protocol.methods],
        "budget": protocol.budget.to_dict(),
    }
    write_json(output_root / "evaluation_manifest.json", manifest)
    return manifest


def _validate_dataset(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Evaluation dataset is empty")
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        errors = validate_dataset_row(row)
        if errors:
            raise ValueError(f"Invalid dataset row {index}: {'; '.join(errors)}")
        concept_id = str(row["concept_id"])
        if concept_id in seen:
            raise ValueError(f"Duplicate concept_id in dataset: {concept_id}")
        seen.add(concept_id)


def _failure(method_id: str, concept_id: str | None, stage: str, exc: Exception) -> dict[str, Any]:
    return {
        "method_id": method_id,
        "concept_id": concept_id,
        "stage": stage,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }
