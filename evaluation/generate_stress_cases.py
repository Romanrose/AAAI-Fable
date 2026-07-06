#!/usr/bin/env python3
"""Generate deterministic M2NA stress cases from audited clean records."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from evaluate_automatic import load_jsonl, validate_record


STRESS_TYPES = (
    "surface_distractor",
    "relation_corruption",
    "mechanism_omission",
)


def _set_case_metadata(
    record: dict[str, Any], base: dict[str, Any], stress_type: str
) -> None:
    base_id = str(base.get("base_id") or base["id"].removesuffix("-clean"))
    record["id"] = f"{base_id}-{stress_type}"
    record["base_id"] = base_id
    record["stress_type"] = stress_type
    record["method"] = f"stress_{stress_type}"


def make_surface_distractor(base: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(base)
    _set_case_metadata(record, base, "surface_distractor")
    node_themes = "、".join(node["text"] for node in record["mechanism_graph"]["nodes"])
    record["output"] = {
        "narrative": (
            f"讲述者反复提到{node_themes}，并声称这些主题彼此相关，"
            "但没有给出角色、事件或因果过程。"
        ),
        "node_alignments": [],
        "edge_alignments": [],
    }
    return record


def make_relation_corruption(base: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(base)
    _set_case_metadata(record, base, "relation_corruption")
    alignments = record["output"]["edge_alignments"]
    if not alignments:
        raise ValueError(f"{base['id']}: relation corruption requires an edge alignment")
    alignment = alignments[0]
    alignment["narrative_source_concept_node_id"], alignment[
        "narrative_target_concept_node_id"
    ] = (
        alignment["narrative_target_concept_node_id"],
        alignment["narrative_source_concept_node_id"],
    )
    # Deliberately keep this stale legacy value to prove it is ignored.
    alignment["direction_preserved"] = True
    return record


def make_mechanism_omission(base: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(base)
    _set_case_metadata(record, base, "mechanism_omission")
    nodes = record["mechanism_graph"]["nodes"]
    omitted_node = max(
        enumerate(nodes),
        key=lambda pair: (float(pair[1].get("weight", 1.0)), -pair[0]),
    )[1]
    omitted_node_id = omitted_node["id"]

    removed_evidence: list[str] = []
    kept_node_alignments = []
    for alignment in record["output"]["node_alignments"]:
        if alignment["concept_node_id"] == omitted_node_id:
            removed_evidence.append(alignment["evidence"])
        else:
            kept_node_alignments.append(alignment)

    incident_edge_ids = {
        edge["id"]
        for edge in record["mechanism_graph"]["edges"]
        if omitted_node_id in (edge["source"], edge["target"])
    }
    kept_edge_alignments = []
    for alignment in record["output"]["edge_alignments"]:
        if alignment["concept_edge_id"] in incident_edge_ids:
            removed_evidence.append(alignment["evidence"])
        else:
            kept_edge_alignments.append(alignment)

    narrative = record["output"]["narrative"]
    for evidence in sorted(set(removed_evidence), key=len, reverse=True):
        narrative = narrative.replace(evidence, "")
    record["output"]["narrative"] = " ".join(narrative.split())
    record["output"]["node_alignments"] = kept_node_alignments
    record["output"]["edge_alignments"] = kept_edge_alignments
    record["stress_metadata"] = {
        "omitted_node_id": omitted_node_id,
        "incident_edge_ids": sorted(incident_edge_ids),
    }
    return record


def generate_cases(base_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for base in base_records:
        errors = validate_record(base)
        if errors:
            raise ValueError(f"{base.get('id')}: invalid clean record: {errors}")
        clean = copy.deepcopy(base)
        clean["stress_type"] = "clean"
        clean["base_id"] = str(
            clean.get("base_id") or clean["id"].removesuffix("-clean")
        )
        generated = [
            clean,
            make_surface_distractor(base),
            make_relation_corruption(base),
            make_mechanism_omission(base),
        ]
        for record in generated:
            if record["id"] in seen_ids:
                raise ValueError(f"duplicate generated id: {record['id']}")
            seen_ids.add(record["id"])
            cases.append(record)
    return cases


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for record in records
    )
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="audited clean-record JSONL")
    parser.add_argument("output", type=Path, help="generated stress-suite JSONL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        base_records = load_jsonl(args.input)
        cases = generate_cases(base_records)
        write_jsonl(args.output, cases)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "base_record_count": len(base_records),
                "generated_record_count": len(cases),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

