from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.aaai_eval.datasets import build_story_pilot_dataset
from kg_rag.aaai_eval.schemas import PROTOCOL_SCHEMA_VERSION
from kg_rag.io import read_json, write_json


STORY_PILOT_METHODS = (
    ("mapping.standard", "Standard Mapping", "standard"),
    ("mapping.deterministic_copycat", "Deterministic Copycat", "copycat"),
    ("mapping.llm_guided_copycat", "LLM-guided Copycat", "llm_guided_copycat"),
)


def initialize_story_pilot_protocol(
    *,
    pilot_root: Path,
    output_root: Path,
    protocol_path: Path,
    candidate_count: int = 3,
) -> dict[str, Any]:
    dataset_path = protocol_path.parent / "datasets" / "story_pilot12.jsonl"
    dataset = build_story_pilot_dataset(pilot_root=pilot_root, output_path=dataset_path)
    revision_manifest = _optional_json(pilot_root / "revision_manifest.json")
    protocol = {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "experiment_id": "story-pilot-12-import-v1",
        "dataset_id": "story-pilot-12",
        "dataset_path": str(dataset_path.resolve()),
        "output_root": str(output_root.resolve()),
        "methods": [
            {
                "method_id": method_id,
                "display_name": display_name,
                "family": "mapping",
                "version": "v1",
                "adapter": "story_pilot_artifact",
                "config": {
                    "pilot_root": str(pilot_root.resolve()),
                    "strategy": strategy,
                },
            }
            for method_id, display_name, strategy in STORY_PILOT_METHODS
        ],
        "budget": {
            "candidate_count": candidate_count,
            "revision_rounds": 1,
            "max_story_tokens": 1800,
        },
        "generator": revision_manifest.get("generator_reviser", {}),
        "judge": revision_manifest.get("judge", {}),
        "metadata": {
            "source_pipeline": "kg_rag.story_pilot",
            "source_pilot_root": str(pilot_root.resolve()),
            "dataset_sha256": dataset["dataset_sha256"],
        },
    }
    write_json(protocol_path, protocol)
    return {
        "protocol_path": str(protocol_path.resolve()),
        "output_root": str(output_root.resolve()),
        "dataset": dataset,
        "method_count": len(protocol["methods"]),
    }


def _optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = read_json(path)
    return value if isinstance(value, dict) else {}
