from __future__ import annotations

import json
from pathlib import Path

import pytest

from kg_rag.aaai_eval.adapters.base import MethodAdapter, MethodRunContext
from kg_rag.aaai_eval.datasets import build_dataset_manifests
from kg_rag.aaai_eval.pipeline_reports import build_ablation_design, build_mechanism_report
from kg_rag.aaai_eval.registry import AdapterRegistry
from kg_rag.aaai_eval.reports import build_reports
from kg_rag.aaai_eval.runner import run_evaluation
from kg_rag.aaai_eval.schemas import PROTOCOL_SCHEMA_VERSION, RECORD_SCHEMA_VERSION, MethodSpec
from kg_rag.concepts.jsonl import read_jsonl, write_jsonl


class _FixtureAdapter(MethodAdapter):
    adapter_id = "fixture"

    def run(self, context: MethodRunContext) -> list[dict]:
        count = int(self.method.config.get("candidate_count", context.protocol.budget.candidate_count))
        return [
            {
                "schema_version": RECORD_SCHEMA_VERSION,
                "experiment_id": context.protocol.experiment_id,
                "dataset_id": context.protocol.dataset_id,
                "concept_id": context.dataset_row["concept_id"],
                "subject": context.dataset_row["subject"],
                "method_id": self.method.method_id,
                "candidate_id": f"candidate_{index + 1:02d}",
                "generation_status": "success",
                "evaluation_status": "accept",
                "revision_improved": index == 0,
                "metrics": {
                    "node_coverage": 1.0,
                    "edge_coverage": 1.0,
                    "direction_accuracy": 1.0,
                    "exact_evidence_precision": 1.0,
                    "hard_leakage": False,
                    "length_valid": True,
                },
                "artifacts": {"story": "fixture.txt"},
            }
            for index in range(count)
        ]


def _write_protocol(
    tmp_path: Path, *, methods: list[dict], candidate_count: int = 2
) -> Path:
    dataset_path = tmp_path / "dataset.jsonl"
    write_jsonl(
        dataset_path,
        [
            {
                "concept_id": "biology-1",
                "subject": "biology",
                "canonical_name": "Cell",
            },
            {
                "concept_id": "physics-1",
                "subject": "physics",
                "canonical_name": "Force",
            },
        ],
    )
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(
        json.dumps(
            {
                "schema_version": PROTOCOL_SCHEMA_VERSION,
                "experiment_id": "fixture-experiment",
                "dataset_id": "fixture-dataset",
                "dataset_path": str(dataset_path),
                "output_root": str(tmp_path / "output"),
                "methods": methods,
                "budget": {"candidate_count": candidate_count, "revision_rounds": 1},
            }
        ),
        encoding="utf-8",
    )
    return protocol_path


def _method(method_id: str, **config: int) -> dict:
    return {
        "method_id": method_id,
        "display_name": method_id,
        "family": "mapping",
        "version": "v1",
        "adapter": "fixture",
        "config": config,
    }


def test_method_registry_supports_external_adapters() -> None:
    registry = AdapterRegistry()
    registry.register(
        _FixtureAdapter.adapter_id,
        lambda method, base_dir: _FixtureAdapter(method=method, base_dir=base_dir),
    )
    assert registry.adapter_ids() == ["fixture"]
    with pytest.raises(ValueError, match="already registered"):
        registry.register(
            _FixtureAdapter.adapter_id,
            lambda method, base_dir: _FixtureAdapter(method=method, base_dir=base_dir),
        )
    spec = MethodSpec.from_dict(_method("mapping.fixture"))
    assert isinstance(registry.create(spec, base_dir=Path(".")), _FixtureAdapter)


def test_dataset_manifests_are_balanced_and_reproducible(tmp_path: Path) -> None:
    seeds_path = tmp_path / "seeds.jsonl"
    subjects = ("biology", "chemistry", "math", "physics")
    write_jsonl(
        seeds_path,
        [
            {
                "concept_id": f"{subject}-{index}",
                "subject": subject,
                "canonical_name": f"{subject} {index}",
            }
            for subject in subjects
            for index in range(5)
        ],
    )
    first = build_dataset_manifests(
        seeds_path=seeds_path,
        output_root=tmp_path / "first",
        core_per_subject=3,
        human_per_subject=2,
    )
    second = build_dataset_manifests(
        seeds_path=seeds_path,
        output_root=tmp_path / "second",
        core_per_subject=3,
        human_per_subject=2,
    )
    assert first["core_subject_counts"] == {subject: 3 for subject in subjects}
    assert first["human_subject_counts"] == {subject: 2 for subject in subjects}
    assert read_jsonl(Path(first["core_path"])) == read_jsonl(Path(second["core_path"]))


def test_runner_enforces_equal_budget_and_builds_reports(tmp_path: Path) -> None:
    protocol_path = _write_protocol(
        tmp_path,
        methods=[_method("mapping.standard"), _method("mapping.copycat")],
    )
    registry = AdapterRegistry()
    registry.register(
        _FixtureAdapter.adapter_id,
        lambda method, base_dir: _FixtureAdapter(method=method, base_dir=base_dir),
    )
    manifest = run_evaluation(protocol_path=protocol_path, registry=registry)
    assert manifest["official_ready"] is True
    assert manifest["record_count"] == 8
    assert all(item["budget_complete"] for item in manifest["fairness"].values())

    report = build_reports(protocol_path=protocol_path)
    assert report["record_count"] == 8
    assert [row["method_id"] for row in report["main_results"]] == [
        "mapping.standard",
        "mapping.copycat",
    ]
    assert all(row["system_exact_match_rate"] == 1.0 for row in report["main_results"])


def test_runner_excludes_method_with_incomplete_candidate_budget(tmp_path: Path) -> None:
    protocol_path = _write_protocol(
        tmp_path,
        methods=[_method("mapping.standard"), _method("mapping.incomplete", candidate_count=1)],
    )
    registry = AdapterRegistry()
    registry.register(
        _FixtureAdapter.adapter_id,
        lambda method, base_dir: _FixtureAdapter(method=method, base_dir=base_dir),
    )
    manifest = run_evaluation(protocol_path=protocol_path, registry=registry)
    assert manifest["official_ready"] is False
    assert manifest["failure_count"] == 2
    assert manifest["fairness"]["mapping.incomplete"]["budget_complete"] is False


def test_pipeline_report_groups_mechanisms_by_subject_and_keeps_ablation_planned(tmp_path: Path) -> None:
    write_jsonl(
        tmp_path / "seeds.jsonl",
        [
            {"concept_id": "biology-1", "subject": "biology"},
            {"concept_id": "physics-1", "subject": "physics"},
        ],
    )
    write_jsonl(
        tmp_path / "retrieval_index.jsonl",
        [
            {"concept_id": "biology-1", "edge_count": 2, "path_count": 1, "expanded_to_two_hop": False},
            {"concept_id": "physics-1", "edge_count": 3, "path_count": 2, "expanded_to_two_hop": True},
        ],
    )
    write_jsonl(
        tmp_path / "mechanism_validation.jsonl",
        [
            {"concept_id": "biology-1", "status": "valid", "errors": []},
            {"concept_id": "physics-1", "status": "invalid", "errors": ["bad evidence"]},
        ],
    )
    report = build_mechanism_report(preparation_root=tmp_path)
    assert report["record_count"] == 2
    assert [row["group"] for row in report["main_results"]] == [
        "overall",
        "biology",
        "physics",
    ]
    assert report["main_results"][1]["valid_rate"] == 1.0
    assert report["main_results"][2]["valid_rate"] == 0.0
    ablation = build_ablation_design()
    assert ablation["status"] == "design_only"
    assert len(ablation["variants"]) == 4
