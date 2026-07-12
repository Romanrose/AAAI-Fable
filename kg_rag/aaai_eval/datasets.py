from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from kg_rag.aaai_eval.schemas import DATASET_SCHEMA_VERSION
from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.m2na_v2.schemas import stable_hash


DEFAULT_SUBJECTS = ("biology", "chemistry", "math", "physics")


def build_dataset_manifests(
    *,
    seeds_path: Path,
    output_root: Path,
    core_per_subject: int = 20,
    human_per_subject: int = 8,
    sampling_seed: str = "aaai-eval-v1",
    subjects: tuple[str, ...] = DEFAULT_SUBJECTS,
) -> dict[str, Any]:
    if core_per_subject < 1:
        raise ValueError("core_per_subject must be positive")
    if not 0 < human_per_subject <= core_per_subject:
        raise ValueError("human_per_subject must be between 1 and core_per_subject")
    seeds = read_jsonl(seeds_path)
    rows = [_dataset_row(seed) for seed in seeds if str(seed.get("subject")) in subjects]
    by_subject = {subject: [row for row in rows if row["subject"] == subject] for subject in subjects}
    for subject, candidates in by_subject.items():
        if len(candidates) < core_per_subject:
            raise ValueError(
                f"Subject {subject} has {len(candidates)} seeds; {core_per_subject} are required"
            )
    core: list[dict[str, Any]] = []
    human: list[dict[str, Any]] = []
    for subject in subjects:
        ranked = sorted(
            by_subject[subject],
            key=lambda row: stable_hash(
                {"sampling_seed": sampling_seed, "concept_id": row["concept_id"]}
            ),
        )
        selected = ranked[:core_per_subject]
        core.extend(selected)
        human.extend(selected[:human_per_subject])
    output_root.mkdir(parents=True, exist_ok=True)
    all_path = output_root / "all_concepts.jsonl"
    core_path = output_root / f"core{len(core)}.jsonl"
    human_path = output_root / f"human{len(human)}.jsonl"
    write_jsonl(all_path, sorted(rows, key=lambda row: (row["subject"], row["concept_id"])))
    write_jsonl(core_path, core)
    write_jsonl(human_path, human)
    result = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_seeds_path": str(seeds_path.resolve()),
        "source_seeds_sha256": stable_hash(seeds),
        "sampling_seed": sampling_seed,
        "subjects": list(subjects),
        "all_count": len(rows),
        "core_count": len(core),
        "human_count": len(human),
        "core_subject_counts": dict(Counter(row["subject"] for row in core)),
        "human_subject_counts": dict(Counter(row["subject"] for row in human)),
        "all_path": str(all_path.resolve()),
        "core_path": str(core_path.resolve()),
        "human_path": str(human_path.resolve()),
        "core_sha256": stable_hash(core),
        "human_sha256": stable_hash(human),
    }
    write_json(output_root / "dataset_manifest.json", result)
    return result


def build_story_pilot_dataset(*, pilot_root: Path, output_path: Path) -> dict[str, Any]:
    index = read_jsonl(pilot_root / "story_input_index.jsonl")
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for item in index:
        concept_id = str(item["concept_id"])
        if concept_id in seen:
            continue
        seen.add(concept_id)
        seed = read_json(Path(str(item["seed_path"])))
        rows.append(_dataset_row(seed))
    write_jsonl(output_path, rows)
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "dataset_id": f"story-pilot-{len(rows)}",
        "concept_count": len(rows),
        "subject_counts": dict(Counter(row["subject"] for row in rows)),
        "dataset_path": str(output_path.resolve()),
        "dataset_sha256": stable_hash(rows),
    }


def _dataset_row(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "concept_id": str(seed["concept_id"]),
        "subject": str(seed["subject"]),
        "canonical_name": str(seed.get("canonical_name") or ""),
        "concept_type": str(seed.get("concept_type") or ""),
        "seed_sha256": stable_hash(seed),
    }
