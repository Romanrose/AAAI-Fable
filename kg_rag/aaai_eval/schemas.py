from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kg_rag.m2na_v2.schemas import stable_hash


PROTOCOL_SCHEMA_VERSION = "aaai-eval-protocol/v1"
RECORD_SCHEMA_VERSION = "aaai-eval-record/v1"
DATASET_SCHEMA_VERSION = "aaai-eval-dataset/v1"
METHOD_FAMILIES = {"retrieval", "mapping", "end_to_end"}
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class MethodSpec:
    method_id: str
    display_name: str
    family: str
    version: str
    adapter: str
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MethodSpec":
        spec = cls(
            method_id=str(value.get("method_id") or ""),
            display_name=str(value.get("display_name") or ""),
            family=str(value.get("family") or ""),
            version=str(value.get("version") or ""),
            adapter=str(value.get("adapter") or ""),
            config=dict(value.get("config") or {}),
        )
        errors = spec.validate()
        if errors:
            raise ValueError("Invalid method specification: " + "; ".join(errors))
        return spec

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not _ID_RE.fullmatch(self.method_id):
            errors.append(f"invalid method_id {self.method_id!r}")
        if not self.display_name.strip():
            errors.append("display_name is required")
        if self.family not in METHOD_FAMILIES:
            errors.append(f"family must be one of {sorted(METHOD_FAMILIES)}")
        if not self.version.strip():
            errors.append("version is required")
        if not _ID_RE.fullmatch(self.adapter):
            errors.append(f"invalid adapter {self.adapter!r}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "display_name": self.display_name,
            "family": self.family,
            "version": self.version,
            "adapter": self.adapter,
            "config": self.config,
        }


@dataclass(frozen=True)
class ExperimentBudget:
    candidate_count: int = 1
    revision_rounds: int = 0
    max_story_tokens: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ExperimentBudget":
        budget = cls(
            candidate_count=int(value.get("candidate_count", 1)),
            revision_rounds=int(value.get("revision_rounds", 0)),
            max_story_tokens=(
                int(value["max_story_tokens"])
                if value.get("max_story_tokens") is not None
                else None
            ),
        )
        if budget.candidate_count < 1:
            raise ValueError("candidate_count must be positive")
        if budget.revision_rounds < 0:
            raise ValueError("revision_rounds cannot be negative")
        if budget.max_story_tokens is not None and budget.max_story_tokens < 1:
            raise ValueError("max_story_tokens must be positive when set")
        return budget

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_count": self.candidate_count,
            "revision_rounds": self.revision_rounds,
            "max_story_tokens": self.max_story_tokens,
        }


@dataclass(frozen=True)
class EvaluationProtocol:
    experiment_id: str
    dataset_id: str
    dataset_path: Path
    output_root: Path
    methods: tuple[MethodSpec, ...]
    budget: ExperimentBudget
    generator: dict[str, Any] = field(default_factory=dict)
    judge: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    base_dir: Path = field(default=Path("."), repr=False, compare=False)
    schema_version: str = PROTOCOL_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: dict[str, Any], *, base_dir: Path) -> "EvaluationProtocol":
        if value.get("schema_version") != PROTOCOL_SCHEMA_VERSION:
            raise ValueError(f"Expected protocol schema {PROTOCOL_SCHEMA_VERSION}")
        methods = tuple(MethodSpec.from_dict(item) for item in value.get("methods", []))
        method_ids = [item.method_id for item in methods]
        if not methods:
            raise ValueError("Protocol must contain at least one method")
        if len(method_ids) != len(set(method_ids)):
            raise ValueError("Protocol method_id values must be unique")
        experiment_id = str(value.get("experiment_id") or "")
        dataset_id = str(value.get("dataset_id") or "")
        if not _ID_RE.fullmatch(experiment_id):
            raise ValueError(f"Invalid experiment_id: {experiment_id!r}")
        if not _ID_RE.fullmatch(dataset_id):
            raise ValueError(f"Invalid dataset_id: {dataset_id!r}")
        return cls(
            experiment_id=experiment_id,
            dataset_id=dataset_id,
            dataset_path=_resolve_path(base_dir, value.get("dataset_path")),
            output_root=_resolve_path(base_dir, value.get("output_root")),
            methods=methods,
            budget=ExperimentBudget.from_dict(dict(value.get("budget") or {})),
            generator=dict(value.get("generator") or {}),
            judge=dict(value.get("judge") or {}),
            metadata=dict(value.get("metadata") or {}),
            base_dir=base_dir.resolve(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "dataset_id": self.dataset_id,
            "dataset_path": str(self.dataset_path),
            "output_root": str(self.output_root),
            "methods": [item.to_dict() for item in self.methods],
            "budget": self.budget.to_dict(),
            "generator": self.generator,
            "judge": self.judge,
            "metadata": self.metadata,
        }

    @property
    def protocol_hash(self) -> str:
        return stable_hash(self.to_dict())


def load_protocol(path: Path) -> EvaluationProtocol:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Experiment protocol must be a JSON object")
    return EvaluationProtocol.from_dict(value, base_dir=path.parent)


def validate_dataset_row(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["dataset row must be an object"]
    errors: list[str] = []
    for key in ("concept_id", "subject", "canonical_name"):
        if not str(value.get(key) or "").strip():
            errors.append(f"{key} is required")
    return errors


def validate_evaluation_record(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["evaluation record must be an object"]
    errors: list[str] = []
    if value.get("schema_version") != RECORD_SCHEMA_VERSION:
        errors.append("invalid evaluation record schema")
    for key in ("experiment_id", "dataset_id", "concept_id", "subject", "method_id", "candidate_id"):
        if not str(value.get(key) or "").strip():
            errors.append(f"{key} is required")
    if value.get("generation_status") not in {"success", "failed", "invalid_for_official_eval"}:
        errors.append("invalid generation_status")
    if not isinstance(value.get("metrics"), dict):
        errors.append("metrics must be an object")
    if not isinstance(value.get("artifacts"), dict):
        errors.append("artifacts must be an object")
    return errors


def _resolve_path(base_dir: Path, raw: Any) -> Path:
    if not str(raw or "").strip():
        raise ValueError("Protocol path is required")
    path = Path(str(raw))
    return path.resolve() if path.is_absolute() else (base_dir / path).resolve()
