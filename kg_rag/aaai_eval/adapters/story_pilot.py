from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kg_rag.aaai_eval.adapters.base import MethodAdapter, MethodRunContext
from kg_rag.aaai_eval.schemas import RECORD_SCHEMA_VERSION
from kg_rag.io import read_json
from kg_rag.m2na_v2.schemas import stable_hash


class StoryPilotArtifactAdapter(MethodAdapter):
    """Imports final candidates produced by ``kg_rag.story_pilot``."""

    adapter_id = "story_pilot_artifact"

    def __init__(self, *, method: Any, base_dir: Path) -> None:
        super().__init__(method=method, base_dir=base_dir)
        raw_root = str(method.config.get("pilot_root") or "")
        if not raw_root:
            raise ValueError(f"{method.method_id}: pilot_root is required")
        path = Path(raw_root)
        self.pilot_root = path.resolve() if path.is_absolute() else (base_dir / path).resolve()
        self.strategy = str(method.config.get("strategy") or "")
        if not self.strategy:
            raise ValueError(f"{method.method_id}: strategy is required")

    def run(self, context: MethodRunContext) -> list[dict[str, Any]]:
        concept_id = str(context.dataset_row["concept_id"])
        root = self.pilot_root / "stories" / concept_id / self.strategy
        if not root.exists():
            raise ValueError(f"Story Pilot artifacts are missing: {root}")
        candidate_dirs = sorted(path for path in root.glob("candidate_*") if path.is_dir())
        expected = context.protocol.budget.candidate_count
        if len(candidate_dirs) != expected:
            raise ValueError(
                f"{concept_id}/{self.method.method_id}: expected {expected} candidates, "
                f"found {len(candidate_dirs)}"
            )
        return [self._record(context, path) for path in candidate_dirs]

    def _record(self, context: MethodRunContext, candidate_dir: Path) -> dict[str, Any]:
        required = {
            "status": candidate_dir / "final_status.json",
            "metrics": candidate_dir / "final_metrics.json",
            "judgment": candidate_dir / "final_judgment.json",
            "alignment": candidate_dir / "final_alignment.json",
            "mapping": candidate_dir / "frozen_mapping_plan.json",
            "story": candidate_dir / "final_story.txt",
        }
        missing = [name for name, path in required.items() if not path.exists()]
        if missing:
            raise ValueError(f"Missing final artifacts in {candidate_dir}: {', '.join(missing)}")
        status = read_json(required["status"])
        metrics = read_json(required["metrics"])
        judgment = read_json(required["judgment"])
        alignment = read_json(required["alignment"])
        mapping = read_json(required["mapping"])
        story = required["story"].read_text(encoding="utf-8")
        generation_status = (
            "success"
            if status.get("status") == "complete" and not status.get("invalid_for_official_eval")
            else "invalid_for_official_eval"
        )
        return {
            "schema_version": RECORD_SCHEMA_VERSION,
            "experiment_id": context.protocol.experiment_id,
            "dataset_id": context.protocol.dataset_id,
            "concept_id": str(context.dataset_row["concept_id"]),
            "subject": str(context.dataset_row["subject"]),
            "canonical_name": str(context.dataset_row.get("canonical_name") or ""),
            "method_id": self.method.method_id,
            "method_display_name": self.method.display_name,
            "method_family": self.method.family,
            "method_version": self.method.version,
            "candidate_id": candidate_dir.name,
            "generation_status": generation_status,
            "evaluation_status": str(judgment.get("final_status") or status.get("judge_status") or "missing"),
            "selected_source": status.get("selected_source"),
            "revision_attempted": bool(status.get("revision_attempted")),
            "revision_improved": bool(status.get("revision_improved")),
            "metrics": {
                "node_coverage": _number(metrics.get("node_coverage")),
                "edge_coverage": _number(metrics.get("edge_coverage")),
                "direction_accuracy": _number(metrics.get("direction_accuracy")),
                "exact_evidence_precision": _number(metrics.get("exact_evidence_precision")),
                "hard_leakage": bool(metrics.get("hard_leakage")),
                "length_valid": bool(metrics.get("length_valid")),
                "story_chars": int(metrics.get("story_chars") or len(story)),
            },
            "judge_scores": dict(judgment.get("scores") or {}),
            "cost": dict(status.get("cost") or {}),
            "artifacts": {name: str(path.resolve()) for name, path in required.items()},
            "artifact_hashes": {
                "story_sha256": hashlib.sha256(story.encode("utf-8")).hexdigest(),
                "mapping_sha256": stable_hash(mapping),
                "alignment_sha256": stable_hash(alignment),
                "judgment_sha256": stable_hash(judgment),
            },
        }


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
