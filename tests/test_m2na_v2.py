from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.m2na_v2.pilot80 import PILOT80_IDS, pilot_subject_counts
from kg_rag.m2na_v2.preparation import build_mechanisms, build_seeds, retrieve_packages, validate_mechanisms
from kg_rag.m2na_v2.mapping import _load_existing_pair, _normalize_copycat_plan, validate_mapping_plan
from kg_rag.m2na_v2.mapping_reviews import append_mapping_review, mapping_review_status
from kg_rag.m2na_v2.retrieval import retrieve_adaptive_two_hop
from kg_rag.m2na_v2.review_app import ReviewAppState
from kg_rag.m2na_v2.reviews import export_review_sheet, import_reviews, pipeline_status
from kg_rag.m2na_v2.runner import ExperimentOptions, run_experiment
from kg_rag.m2na_v2.schemas import (
    MECHANISM_SCHEMA_VERSION,
    SEED_FIELDS,
    SEED_SCHEMA_VERSION,
    available_evidence_refs,
    stable_hash,
    validate_mechanism_record,
    validate_seed,
)


class V2FakeLLM:
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if "TASK:M2NA_V2_MECHANISM_JSON" in user_prompt:
            concept_id = re.search(r'"concept_id":\s*"([^"]+)"', user_prompt).group(1)
            evidence = f"kg-node:{concept_id}:definition"
            return json.dumps(
                {
                    "mechanism_graph": {
                        "nodes": [
                            {"id": "n1", "type": "condition", "text": "先确认必要条件", "evidence_refs": [evidence]},
                            {"id": "n2", "type": "outcome", "text": "条件成立后出现结果", "evidence_refs": [evidence]},
                        ],
                        "edges": [
                            {
                                "id": "e1",
                                "source": "n1",
                                "target": "n2",
                                "relation": "enables",
                                "evidence_refs": [evidence],
                            }
                        ],
                    },
                    "generation_constraints": {
                        "must_preserve_node_ids": ["n1", "n2"],
                        "must_preserve_edge_ids": ["e1"],
                    },
                },
                ensure_ascii=False,
            )
        if "TASK:PLANNER_JSON" in user_prompt:
            return json.dumps(
                {
                    "source_domain": "仓库验收站",
                    "characters": ["守门人"],
                    "objects": ["通行牌"],
                    "conflict": "条件尚未确认。",
                    "event_chain": ["先检查通行牌。", "确认后打开仓门。"],
                    "turning_point": "提前开门导致流程中断。",
                    "resolution_state": "重新按条件执行。",
                    "mapping_plan": [
                        {"mechanism_node_id": "n1", "mechanism_text": "先确认必要条件", "story_role": "检查通行牌"},
                        {"mechanism_node_id": "n2", "mechanism_text": "条件成立后出现结果", "story_role": "打开仓门"},
                    ],
                    "risk_notes": [],
                },
                ensure_ascii=False,
            )
        if "TASK:GENERATOR_STORY" in user_prompt:
            return "守门人先检查通行牌，确认无误后打开仓门，货物因此送入库房。"
        if "TASK:ALIGNER_JSON" in user_prompt:
            return json.dumps(
                {
                    "node_alignments": [
                        {"concept_node_id": "n1", "evidence": "先检查通行牌"},
                        {"concept_node_id": "n2", "evidence": "打开仓门"},
                    ],
                    "edge_alignments": [
                        {
                            "concept_edge_id": "e1",
                            "evidence": "确认无误后打开仓门，货物因此送入库房",
                            "narrative_source_concept_node_id": "n1",
                            "narrative_target_concept_node_id": "n2",
                            "direction_preserved": True,
                        }
                    ],
                },
                ensure_ascii=False,
            )
        if "TASK:ARBITER_JSON" in user_prompt:
            return json.dumps({"winner_candidate_id": "candidate_001", "rationale": "结构完整", "risk_notes": []}, ensure_ascii=False)
        if "TASK:SIX_DIM_JUDGE_JSON" in user_prompt:
            return json.dumps(
                {
                    "scores": {
                        "faithfulness": 5,
                        "implicitness": 5,
                        "mapping_clarity": 5,
                        "readability": 4,
                        "pedagogical_value": 5,
                        "novelty": 4,
                    },
                    "hard_flags": {
                        "hard_leakage": False,
                        "soft_leakage": False,
                        "title_leakage": False,
                        "concept_contradiction": False,
                        "unmapped_core_mechanism": False,
                        "template_like": False,
                    },
                    "rationales": {"faithfulness": "机制完整。"},
                    "evidence": {"faithfulness": "先检查后开门。"},
                    "revision_suggestions": [],
                },
                ensure_ascii=False,
            )
        if "TASK:REVISER_STORY" in user_prompt:
            return "守门人先检查通行牌，确认无误后才打开仓门，货物因此顺利入库。"
        raise AssertionError(user_prompt[:120])


class BrokenBuilderLLM:
    def complete(self, **_: object) -> str:
        return "not-json"


class AlwaysFailLLM:
    def complete(self, **_: object) -> str:
        raise RuntimeError("synthetic failure")


def _graph() -> dict:
    subjects = ("biology", "chemistry", "math", "physics")
    nodes = []
    edges = []
    for index, subject in enumerate(subjects):
        concept_id = f"{subject}_c1"
        neighbor_id = f"{subject}_neighbor"
        nodes.extend(
            [
                {
                    "id": concept_id,
                    "label": "Concept",
                    "name": f"{subject}目标",
                    "properties": {
                        "definition": "这是一个过程，需要先确认条件，随后才会出现结果。",
                        "aliases": [f"{subject}别名"],
                    },
                },
                {"id": neighbor_id, "label": "Concept", "name": f"{subject}条件", "properties": {}},
            ]
        )
        edges.append({"source": neighbor_id, "target": concept_id, "type": "prerequisites_for"})
    return {"nodes": nodes, "edges": edges}


def _prepare(tmp_path: Path, *, llm=None) -> tuple[Path, Path, list[str]]:
    graph_path = tmp_path / "graph.json"
    root = tmp_path / "pilot"
    ids = ["biology_c1", "chemistry_c1", "math_c1", "physics_c1"]
    write_json(graph_path, _graph())
    build_seeds(normalized_graph_path=graph_path, output_root=root, concept_ids=ids)
    retrieve_packages(normalized_graph_path=graph_path, seeds_path=root / "seeds.jsonl", output_root=root)
    build_mechanisms(
        seeds_path=root / "seeds.jsonl",
        output_root=root,
        llm=llm or V2FakeLLM(),
        builder_identity={"model": "fake-builder"},
    )
    validate_mechanisms(seeds_path=root / "seeds.jsonl", output_root=root)
    return graph_path, root, ids


def _approve_all(root: Path) -> None:
    sheet = root / "review.csv"
    export_review_sheet(seeds_path=root / "seeds.jsonl", output_root=root, output_path=sheet)
    with sheet.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["review_decision"] = "approve"
        row["reviewer"] = "tester"
    with sheet.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    import_reviews(review_sheet_path=sheet, seeds_path=root / "seeds.jsonl", output_root=root)


def test_frozen_pilot_has_twenty_concepts_per_subject() -> None:
    assert len(PILOT80_IDS) == 80
    assert pilot_subject_counts() == {"biology": 20, "chemistry": 20, "math": 20, "physics": 20}


def test_seed_is_minimal_and_has_no_legacy_card_fields(tmp_path: Path) -> None:
    graph_path, root, _ = _prepare(tmp_path)
    seed = read_json(root / "seed_manifest.json")
    rows = read_jsonl(root / "seeds.jsonl")

    assert seed["seed_count"] == 4
    assert set(rows[0]) == SEED_FIELDS
    assert rows[0]["schema_version"] == SEED_SCHEMA_VERSION
    assert not validate_seed(rows[0])
    assert "graph_context" not in rows[0]
    assert "core_mechanism_zh" not in rows[0]
    assert graph_path.exists()


def test_mechanism_validation_rejects_unknown_evidence_and_duplicate_ids(tmp_path: Path) -> None:
    _, root, _ = _prepare(tmp_path)
    seed = read_jsonl(root / "seeds.jsonl")[0]
    retrieval = read_json(root / "retrieval" / f"{seed['concept_id']}.json")
    record = read_jsonl(root / "mechanisms.raw.jsonl")[0]
    broken = json.loads(json.dumps(record, ensure_ascii=False))
    broken["mechanism_graph"]["nodes"][1]["id"] = "n1"
    broken["mechanism_graph"]["nodes"][0]["evidence_refs"] = ["kg-edge:not-available"]

    errors = validate_mechanism_record(broken, seed=seed, retrieval_package=retrieval)

    assert any("duplicate node id" in error for error in errors)
    assert any("unavailable evidence" in error for error in errors)


def test_definition_can_be_single_node_but_process_requires_an_edge(tmp_path: Path) -> None:
    _, root, _ = _prepare(tmp_path)
    seed = read_jsonl(root / "seeds.jsonl")[0]
    retrieval = read_json(root / "retrieval" / f"{seed['concept_id']}.json")
    evidence = f"kg-node:{seed['concept_id']}:definition"

    def record_for(concept_type: str) -> tuple[dict, dict]:
        typed_seed = {**seed, "concept_type": concept_type}
        record = {
            "schema_version": MECHANISM_SCHEMA_VERSION,
            "concept_id": seed["concept_id"],
            "mechanism_graph": {
                "nodes": [{"id": "n1", "type": "entity", "text": "目标定义", "evidence_refs": [evidence]}],
                "edges": [],
            },
            "generation_constraints": {
                "forbidden_terms": seed["forbidden_terms"],
                "must_preserve_node_ids": ["n1"],
                "must_preserve_edge_ids": [],
            },
            "provenance": {
                "seed_sha256": stable_hash(typed_seed),
                "retrieval_sha256": stable_hash(retrieval),
                "builder": {"model": "test"},
                "prompt_version": "test",
            },
        }
        return typed_seed, record

    definition_seed, definition_record = record_for("definition")
    process_seed, process_record = record_for("process")

    assert not validate_mechanism_record(definition_record, seed=definition_seed, retrieval_package=retrieval)
    process_errors = validate_mechanism_record(process_record, seed=process_seed, retrieval_package=retrieval)
    assert any("at least 2 mechanism nodes" in error for error in process_errors)
    assert any("at least 1 mechanism edge" in error for error in process_errors)


def test_adaptive_retrieval_expands_insufficient_multistep_concept_to_two_hops() -> None:
    graph = {
        "nodes": [
            {"id": "physics_c1", "label": "Concept", "name": "目标过程", "properties": {"definition": "需要条件"}},
            {"id": "physics_condition", "label": "Concept", "name": "条件", "properties": {"definition": "前提"}},
            {"id": "physics_outcome", "label": "Concept", "name": "结果", "properties": {"definition": "变化"}},
        ],
        "edges": [
            {"source": "physics_condition", "target": "physics_c1", "type": "prerequisites_for"},
            {"source": "physics_condition", "target": "physics_outcome", "type": "leads_to"},
        ],
    }
    seed = {
        "schema_version": SEED_SCHEMA_VERSION,
        "concept_id": "physics_c1",
        "subject": "physics",
        "canonical_name": "目标过程",
        "aliases": [],
        "definition": "需要条件",
        "concept_type": "mechanism",
        "forbidden_terms": ["目标过程"],
    }

    package = retrieve_adaptive_two_hop(normalized_graph=graph, seed=seed)

    assert package["retrieval_stats"]["retrieval_mode"] == "adaptive_two_hop"
    assert package["retrieval_decision"]["expanded_to_two_hop"] is True
    assert package["retrieval_decision"]["expansion_mode"] == "semantic_relation_paths"
    assert len(package["selected_paths"]) == 1
    assert package["selected_paths"][0]["hop_count"] == 2
    assert package["selected_paths"][0]["node_ids"] == ["physics_c1", "physics_condition", "physics_outcome"]
    assert {edge["source_edge_id"] for edge in package["raw_edges"]} == {
        "normalized:edge:0",
        "normalized:edge:1",
    }
    assert {node["source_node_id"] for node in package["retrieved_nodes"]} == {
        "physics_condition",
        "physics_outcome",
    }


def test_adaptive_retrieval_keeps_sufficient_direct_structure_at_one_hop() -> None:
    graph = {
        "nodes": [
            {"id": "chemistry_c1", "label": "Concept", "name": "目标反应", "properties": {"definition": "条件与结果"}},
            {"id": "chemistry_condition", "label": "Concept", "name": "条件", "properties": {}},
            {"id": "chemistry_result", "label": "Concept", "name": "结果", "properties": {}},
            {"id": "chemistry_extra", "label": "Concept", "name": "额外节点", "properties": {}},
        ],
        "edges": [
            {"source": "chemistry_condition", "target": "chemistry_c1", "type": "prerequisites_for"},
            {"source": "chemistry_c1", "target": "chemistry_result", "type": "leads_to"},
            {"source": "chemistry_condition", "target": "chemistry_extra", "type": "verifies"},
        ],
    }
    seed = {
        "schema_version": SEED_SCHEMA_VERSION,
        "concept_id": "chemistry_c1",
        "subject": "chemistry",
        "canonical_name": "目标反应",
        "aliases": [],
        "definition": "条件与结果",
        "concept_type": "process",
        "forbidden_terms": ["目标反应"],
    }

    package = retrieve_adaptive_two_hop(normalized_graph=graph, seed=seed)

    assert package["retrieval_decision"]["direct_structure_sufficient"] is True
    assert package["retrieval_decision"]["expanded_to_two_hop"] is False
    assert package["selected_paths"] == []
    assert {edge["source_edge_id"] for edge in package["raw_edges"]} == {
        "normalized:edge:0",
        "normalized:edge:1",
    }


def test_isolated_seed_uses_lexical_curriculum_bridge_without_bridge_evidence() -> None:
    graph = {
        "nodes": [
            {
                "id": "biology_c1",
                "label": "Concept",
                "name": "生物",
                "properties": {"definition": "生物需要营养，能进行呼吸，通常由细胞构成。"},
            },
            {"id": "biology_s1", "label": "Section", "name": "认识生物", "properties": {}},
            {"id": "biology_cell", "label": "Concept", "name": "细胞", "properties": {"definition": "生命结构单位"}},
            {
                "id": "biology_nutrition",
                "label": "Concept",
                "name": "营养（生物的生活需要营养）",
                "properties": {"definition": "生活需要"},
            },
            {"id": "biology_unrelated", "label": "Concept", "name": "生态系统", "properties": {}},
        ],
        "edges": [
            {"source": "biology_c1", "target": "biology_s1", "type": "appears_in"},
            {"source": "biology_cell", "target": "biology_s1", "type": "appears_in"},
            {"source": "biology_nutrition", "target": "biology_s1", "type": "appears_in"},
            {"source": "biology_unrelated", "target": "biology_s1", "type": "appears_in"},
        ],
    }
    seed = {
        "schema_version": SEED_SCHEMA_VERSION,
        "concept_id": "biology_c1",
        "subject": "biology",
        "canonical_name": "生物",
        "aliases": [],
        "definition": "生物需要营养，能进行呼吸，通常由细胞构成。",
        "concept_type": "definition",
        "forbidden_terms": ["生物"],
    }

    package = retrieve_adaptive_two_hop(normalized_graph=graph, seed=seed)
    evidence_refs = available_evidence_refs(package)

    assert package["retrieval_decision"]["expansion_mode"] == "curriculum_lexical_bridge"
    assert {path["lexical_anchor"] for path in package["selected_paths"]} == {"细胞", "营养"}
    assert all(edge["evidence_eligible"] is False for edge in package["raw_edges"])
    assert not any(ref.startswith("kg-edge:") for ref in evidence_refs)
    assert "kg-node:biology_cell:definition" in evidence_refs


def test_broken_builder_goes_to_failed_queue_without_definition_fallback(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.json"
    root = tmp_path / "pilot"
    write_json(graph_path, _graph())
    build_seeds(normalized_graph_path=graph_path, output_root=root, concept_ids=["biology_c1"])
    retrieve_packages(normalized_graph_path=graph_path, seeds_path=root / "seeds.jsonl", output_root=root)

    result = build_mechanisms(
        seeds_path=root / "seeds.jsonl",
        output_root=root,
        llm=BrokenBuilderLLM(),
        builder_identity={"model": "broken"},
    )

    assert result["record_count"] == 0
    assert result["failed_count"] == 1
    assert read_jsonl(root / "mechanisms.raw.jsonl") == []
    assert read_jsonl(root / "failed_queue.jsonl")[0]["stage"] == "builder"


def test_builder_canonicalizes_safe_inverse_contains_relation(tmp_path: Path) -> None:
    class ContainsBuilder(V2FakeLLM):
        def complete(self, **kwargs: object) -> str:
            if "TASK:M2NA_V2_MECHANISM_JSON" in str(kwargs.get("user_prompt") or ""):
                payload = json.loads(super().complete(**kwargs))
                payload["mechanism_graph"]["edges"][0]["relation"] = "contains"
                payload["mechanism_graph"]["edges"][0]["source"] = "n2"
                payload["mechanism_graph"]["edges"][0]["target"] = "n1"
                return json.dumps(payload, ensure_ascii=False)
            return super().complete(**kwargs)

    graph_path = tmp_path / "graph.json"
    root = tmp_path / "pilot"
    write_json(graph_path, _graph())
    build_seeds(normalized_graph_path=graph_path, output_root=root, concept_ids=["biology_c1"])
    retrieve_packages(normalized_graph_path=graph_path, seeds_path=root / "seeds.jsonl", output_root=root)
    result = build_mechanisms(
        seeds_path=root / "seeds.jsonl",
        output_root=root,
        llm=ContainsBuilder(),
        builder_identity={"model": "contains"},
    )
    edge = read_jsonl(root / "mechanisms.raw.jsonl")[0]["mechanism_graph"]["edges"][0]

    assert result["valid_count"] == 1
    assert edge["relation"] == "part_of"
    assert edge["source"] == "n1"
    assert edge["target"] == "n2"
    assert edge["canonicalized_from"] == "contains"


def test_review_gate_exports_only_valid_and_approved_records(tmp_path: Path) -> None:
    _, root, _ = _prepare(tmp_path)
    assert pipeline_status(seeds_path=root / "seeds.jsonl", output_root=root)["approved_count"] == 0

    _approve_all(root)

    status = pipeline_status(seeds_path=root / "seeds.jsonl", output_root=root)
    approved = read_jsonl(root / "mechanisms.approved.jsonl")
    assert status["approved_count"] == 4
    assert len(approved) == 4
    assert all(record["schema_version"] == MECHANISM_SCHEMA_VERSION for record in approved)

    sheet = root / "review.csv"
    export_review_sheet(seeds_path=root / "seeds.jsonl", output_root=root, output_path=sheet)
    with sheet.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["review_decision"] = "reject"
    rows[0]["reviewer"] = "second-reviewer"
    with sheet.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    import_reviews(review_sheet_path=sheet, seeds_path=root / "seeds.jsonl", output_root=root)
    assert len(read_jsonl(root / "mechanisms.approved.jsonl")) == 3


def test_review_app_state_exposes_evidence_and_appends_decision(tmp_path: Path) -> None:
    _, root, _ = _prepare(tmp_path)
    app = ReviewAppState(seeds_path=root / "seeds.jsonl", output_root=root)

    before = app.payload()
    row = before["rows"][0]
    concept_id = row["seed"]["concept_id"]
    result = app.save(
        {
            "concept_id": concept_id,
            "decision": "approve",
            "reviewer": "web-reviewer",
            "notes": "Evidence and mechanism are acceptable.",
        }
    )
    after = app.payload()
    updated = next(item for item in after["rows"] if item["seed"]["concept_id"] == concept_id)

    assert row["retrieval"]["target"]["source_node_id"] == concept_id
    assert row["mechanism_graph"]["nodes"]
    assert row["validation"]["status"] == "valid"
    assert result["imported_count"] == 1
    assert result["approved_count"] == 1
    assert updated["review"]["decision"] == "approve"
    assert updated["review"]["reviewer"] == "web-reviewer"
    assert len(read_jsonl(root / "mechanism_reviews.jsonl")) == 1


def test_mapping_context_excludes_curriculum_only_edges_and_mapping_gate_requires_preservation(tmp_path: Path) -> None:
    graph = {
        "nodes": [
            {"id": "biology_c1", "label": "Concept", "name": "生物", "properties": {"definition": "由细胞构成。"}},
            {"id": "biology_s1", "label": "Section", "name": "认识生物", "properties": {}},
            {"id": "biology_cell", "label": "Concept", "name": "细胞", "properties": {"definition": "结构单位"}},
        ],
        "edges": [
            {"source": "biology_c1", "target": "biology_s1", "type": "appears_in"},
            {"source": "biology_cell", "target": "biology_s1", "type": "appears_in"},
        ],
    }
    seed = {
        "schema_version": SEED_SCHEMA_VERSION,
        "concept_id": "biology_c1",
        "subject": "biology",
        "canonical_name": "生物",
        "aliases": [],
        "definition": "由细胞构成。",
        "concept_type": "definition",
        "forbidden_terms": ["生物"],
    }
    retrieval = retrieve_adaptive_two_hop(normalized_graph=graph, seed=seed)
    record = {
        "schema_version": MECHANISM_SCHEMA_VERSION,
        "concept_id": "biology_c1",
        "mechanism_graph": {
            "nodes": [
                {"id": "n1", "type": "entity", "text": "目标", "evidence_refs": ["kg-node:biology_c1:definition"]},
                {"id": "n2", "type": "state", "text": "由细胞构成", "evidence_refs": ["kg-node:biology_cell:definition"]},
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "relation": "requires",
                    "evidence_refs": ["kg-node:biology_c1:definition"],
                }
            ],
        },
        "generation_constraints": {
            "forbidden_terms": ["生物"],
            "must_preserve_node_ids": ["n1", "n2"],
            "must_preserve_edge_ids": ["e1"],
        },
        "provenance": {
            "seed_sha256": stable_hash(seed),
            "retrieval_sha256": stable_hash(retrieval),
            "builder": {"model": "test"},
        },
    }
    from kg_rag.m2na_v2.runner import build_mapping_context

    context = build_mapping_context(seed=seed, retrieval=retrieval, mechanism_record=record)
    incomplete = {
        "schema_version": "m2na-mapping-plan/v1",
        "concept_id": "biology_c1",
        "strategy": "standard",
        "mapping_context_sha256": stable_hash(context),
        "node_mappings": [{"mechanism_node_id": "n1", "story_carrier": "登记员"}],
        "edge_mappings": [],
    }

    assert context["concept_relation_graph"]["relations"] == []
    errors = validate_mapping_plan(plan=incomplete, context=context)
    assert any("must_preserve nodes" in error for error in errors)
    assert any("must_preserve edges" in error for error in errors)


def test_mapping_resume_skips_complete_validated_pair(tmp_path: Path) -> None:
    context = {
        "seed": {"concept_id": "biology_c1"},
        "mechanism_graph": {
            "nodes": [{"id": "n1", "type": "entity", "text": "目标"}],
            "edges": [],
        },
        "generation_constraints": {
            "must_preserve_node_ids": ["n1"],
            "must_preserve_edge_ids": [],
        },
    }
    context["seed"].update(
        {
            "subject": "biology",
            "canonical_name": "目标",
            "aliases": [],
            "definition": "",
            "concept_type": "definition",
            "forbidden_terms": ["目标"],
        }
    )
    candidate_dir = tmp_path / "candidate_001"
    for strategy in ("standard", "copycat"):
        write_json(
            candidate_dir / f"{strategy}_mapping_plan.json",
            {
                "schema_version": "m2na-mapping-plan/v1",
                "concept_id": "biology_c1",
                "strategy": strategy,
                "candidate_id": "candidate_001",
                "candidate_index": 1,
                "node_mappings": [{"mechanism_node_id": "n1", "story_carrier": "门票"}],
                "edge_mappings": [],
                "mapping_context_sha256": stable_hash(context),
            },
        )

    rows = _load_existing_pair(candidate_dir=candidate_dir, context=context)

    assert rows is not None
    assert {row["strategy"] for row in rows} == {"standard", "copycat"}


def test_mapping_review_history_is_strategy_specific_and_append_only(tmp_path: Path) -> None:
    mapping_root = tmp_path / "mapping_plans"
    plan_path = mapping_root / "concepts" / "biology_c1" / "candidate_001" / "standard_mapping_plan.json"
    write_json(plan_path, {"concept_id": "biology_c1", "strategy": "standard"})
    write_json(
        mapping_root / "concepts" / "biology_c1" / "candidate_001" / "copycat_mapping_plan.json",
        {"concept_id": "biology_c1", "strategy": "copycat"},
    )
    write_jsonl(
        mapping_root / "mapping_plan_index.jsonl",
        [
            {"concept_id": "biology_c1", "candidate_id": "candidate_001", "strategy": "standard"},
            {"concept_id": "biology_c1", "candidate_id": "candidate_001", "strategy": "copycat"},
        ],
    )

    first = append_mapping_review(
        mapping_root=mapping_root,
        concept_id="biology_c1",
        candidate_id="candidate_001",
        strategy="standard",
        decision="approve",
        reviewer="tester",
        notes="Standard plan preserves all required relations.",
    )
    second = append_mapping_review(
        mapping_root=mapping_root,
        concept_id="biology_c1",
        candidate_id="candidate_001",
        strategy="copycat",
        decision="reject",
        reviewer="tester",
        notes="Copycat plan needs a better story carrier.",
    )

    assert first["approved_count"] == 1
    assert second["approved_count"] == 1
    assert second["rejected_count"] == 1
    assert second["pending_count"] == 0
    assert len(read_jsonl(mapping_root / "mapping_reviews.jsonl")) == 2
    assert mapping_review_status(mapping_root=mapping_root)["plan_count"] == 2


def test_dual_strategy_runner_uses_identical_context_and_budget(tmp_path: Path) -> None:
    _, root, _ = _prepare(tmp_path)
    _approve_all(root)
    run_dir = root / "runs" / "test"

    result = run_experiment(
        seeds_path=root / "seeds.jsonl",
        preparation_root=root,
        output_dir=run_dir,
        llm=V2FakeLLM(),
        judge_llm=V2FakeLLM(),
        options=ExperimentOptions(six_dim_mode="llm"),
    )

    standard_hashes = read_jsonl(run_dir / "standard" / "mapping_context_hashes.jsonl")
    copycat_hashes = read_jsonl(run_dir / "copycat" / "mapping_context_hashes.jsonl")
    assert result["standard"]["official_count"] == 4
    assert result["copycat"]["official_count"] == 4
    assert result["standard"]["candidate_count"] == result["copycat"]["candidate_count"] == 3
    assert standard_hashes == copycat_hashes
    context = read_json(run_dir / "standard" / "concepts" / "biology_c1" / "mapping_context.json")
    assert "graph_context" not in json.dumps(context, ensure_ascii=False)
    assert stable_hash(context) == standard_hashes[0]["mapping_context_sha256"]


def test_runner_excludes_fallback_from_official_results(tmp_path: Path) -> None:
    _, root, _ = _prepare(tmp_path)
    _approve_all(root)
    run_dir = root / "runs" / "fallback"

    result = run_experiment(
        seeds_path=root / "seeds.jsonl",
        preparation_root=root,
        output_dir=run_dir,
        llm=AlwaysFailLLM(),
        judge_llm=V2FakeLLM(),
        options=ExperimentOptions(strategies=("standard",), six_dim_mode="rules"),
    )

    invalid = read_jsonl(run_dir / "standard" / "invalid_for_official_eval.jsonl")
    assert result["standard"]["official_count"] == 0
    assert result["standard"]["invalid_count"] == 4
    assert all(row["generation_status"] == "invalid_for_official_eval" for row in invalid)
