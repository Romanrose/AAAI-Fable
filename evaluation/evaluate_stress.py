#!/usr/bin/env python3
"""Evaluate M2NA stress cases against their clean counterparts."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from evaluate_automatic import evaluate_record, load_jsonl


NEGATIVE_TYPES = (
    "surface_distractor",
    "relation_corruption",
    "mechanism_omission",
)
METRICS = (
    "node_coverage",
    "edge_coverage",
    "weighted_node_coverage",
    "weighted_edge_coverage",
    "alignment_precision",
    "relation_direction_accuracy",
)


def _is_lower(candidate: dict[str, Any], clean: dict[str, Any], metric: str) -> bool:
    candidate_value = candidate.get(metric)
    clean_value = clean.get(metric)
    return (
        candidate_value is not None
        and clean_value is not None
        and float(candidate_value) < float(clean_value)
    )


def detect_case(
    stress_type: str, candidate: dict[str, Any], clean: dict[str, Any]
) -> tuple[bool, str]:
    if stress_type == "surface_distractor":
        detected = _is_lower(candidate, clean, "node_coverage") or _is_lower(
            candidate, clean, "edge_coverage"
        )
        reason = "node_coverage or edge_coverage must decrease"
    elif stress_type == "relation_corruption":
        detected = _is_lower(
            candidate, clean, "relation_direction_accuracy"
        )
        reason = "relation_direction_accuracy must decrease"
    elif stress_type == "mechanism_omission":
        detected = _is_lower(
            candidate, clean, "weighted_node_coverage"
        ) or _is_lower(candidate, clean, "weighted_edge_coverage")
        reason = "weighted node or edge coverage must decrease"
    else:
        raise ValueError(f"unknown stress type: {stress_type}")
    return detected, reason


def clean_is_false_positive(result: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for metric in (
        "format_validity",
        "node_coverage",
        "edge_coverage",
        "alignment_precision",
        "relation_direction_accuracy",
    ):
        if result.get(metric) != 1.0:
            failures.append(f"{metric}={result.get(metric)!r}")
    if result.get("exact_concept_leakage") != 0.0:
        failures.append("exact_concept_leakage")
    if result.get("soft_term_leakage") != 0.0:
        failures.append("soft_term_leakage")
    return bool(failures), failures


def _metric_deltas(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]]
) -> dict[str, float | None]:
    deltas: dict[str, float | None] = {}
    for metric in METRICS:
        values = []
        for candidate, clean in pairs:
            if candidate.get(metric) is None or clean.get(metric) is None:
                continue
            values.append(float(candidate[metric]) - float(clean[metric]))
        deltas[metric] = statistics.fmean(values) if values else None
    return deltas


def build_report(
    records: list[dict[str, Any]],
    minimum_detection_rate: float = 0.9,
    maximum_clean_false_positive_rate: float = 0.1,
) -> dict[str, Any]:
    evaluated = []
    for record in records:
        result = evaluate_record(record)
        result["base_id"] = record.get("base_id")
        result["stress_type"] = record.get("stress_type")
        evaluated.append(result)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in evaluated:
        base_id = result.get("base_id")
        stress_type = result.get("stress_type")
        if not isinstance(base_id, str) or not base_id:
            raise ValueError(f"{result.get('id')}: missing base_id")
        if stress_type not in ("clean", *NEGATIVE_TYPES):
            raise ValueError(f"{result.get('id')}: invalid stress_type")
        grouped[base_id].append(result)

    clean_results: dict[str, dict[str, Any]] = {}
    for base_id, items in grouped.items():
        clean = [item for item in items if item["stress_type"] == "clean"]
        if len(clean) != 1:
            raise ValueError(f"{base_id}: expected exactly one clean record")
        clean_results[base_id] = clean[0]
        counts = defaultdict(int)
        for item in items:
            counts[item["stress_type"]] += 1
        for stress_type in NEGATIVE_TYPES:
            if counts[stress_type] != 1:
                raise ValueError(
                    f"{base_id}: expected exactly one {stress_type} record"
                )

    by_type: dict[str, Any] = {}
    all_details: list[dict[str, Any]] = []
    for stress_type in NEGATIVE_TYPES:
        pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        details = []
        for base_id in sorted(grouped):
            candidate = next(
                item
                for item in grouped[base_id]
                if item["stress_type"] == stress_type
            )
            clean = clean_results[base_id]
            detected, expectation = detect_case(stress_type, candidate, clean)
            detail = {
                "id": candidate["id"],
                "base_id": base_id,
                "detected": detected,
                "expectation": expectation,
            }
            details.append(detail)
            all_details.append(detail)
            pairs.append((candidate, clean))
        detected_count = sum(detail["detected"] for detail in details)
        detection_rate = detected_count / len(details)
        by_type[stress_type] = {
            "sample_count": len(details),
            "detected_count": detected_count,
            "detection_rate": detection_rate,
            "mean_metric_delta_from_clean": _metric_deltas(pairs),
            "undetected": [
                detail for detail in details if not detail["detected"]
            ],
            "passed": detection_rate >= minimum_detection_rate,
        }

    clean_details = []
    for base_id in sorted(clean_results):
        false_positive, reasons = clean_is_false_positive(clean_results[base_id])
        clean_details.append(
            {
                "id": clean_results[base_id]["id"],
                "base_id": base_id,
                "false_positive": false_positive,
                "reasons": reasons,
            }
        )
    false_positive_count = sum(item["false_positive"] for item in clean_details)
    clean_false_positive_rate = false_positive_count / len(clean_details)

    passed = (
        all(item["passed"] for item in by_type.values())
        and clean_false_positive_rate <= maximum_clean_false_positive_rate
    )
    return {
        "suite": {
            "base_concept_count": len(grouped),
            "record_count": len(records),
            "minimum_detection_rate": minimum_detection_rate,
            "maximum_clean_false_positive_rate": maximum_clean_false_positive_rate,
        },
        "by_stress_type": by_type,
        "clean_samples": {
            "sample_count": len(clean_details),
            "false_positive_count": false_positive_count,
            "false_positive_rate": clean_false_positive_rate,
            "details": clean_details,
            "passed": clean_false_positive_rate
            <= maximum_clean_false_positive_rate,
        },
        "passed": passed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="generated stress-suite JSONL")
    parser.add_argument("--output", type=Path, help="write JSON report")
    parser.add_argument("--minimum-detection-rate", type=float, default=0.9)
    parser.add_argument("--maximum-clean-fpr", type=float, default=0.1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        records = load_jsonl(args.input)
        report = build_report(
            records,
            minimum_detection_rate=args.minimum_detection_rate,
            maximum_clean_false_positive_rate=args.maximum_clean_fpr,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    serialized = json.dumps(
        report, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "base_concept_count": report["suite"]["base_concept_count"],
                "record_count": report["suite"]["record_count"],
                "clean_false_positive_rate": report["clean_samples"][
                    "false_positive_rate"
                ],
                "detection_rates": {
                    key: value["detection_rate"]
                    for key, value in report["by_stress_type"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

