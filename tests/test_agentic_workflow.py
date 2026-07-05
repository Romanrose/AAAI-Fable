from __future__ import annotations

from pathlib import Path

from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.pipeline.concept_fables import ConceptFableOptions, run_concept_fable_batch
from kg_rag.pipeline.agentic_workflow import build_agentic_workflow_artifacts


def _card() -> dict:
    return {
        "concept_id": "biology_c1",
        "subject": "biology",
        "story_language": "zh-CN",
        "canonical_name": "光合作用",
        "definition": "植物利用光能合成有机物并释放氧气。",
        "aliases": [],
        "examples": [],
        "teaching_level": "middle_school",
        "concept_type": "process",
        "graph_context": {},
        "core_mechanism_zh": ["需要光和水等条件", "合成有机物", "释放氧气"],
        "must_preserve_zh": [],
        "common_misconceptions_zh": [],
        "forbidden_terms_zh": ["光合作用"],
        "subject_constraints_zh": ["避免目的论解释。"],
        "generation_notes_zh": [],
        "data_quality": {"generation_priority": "gold"},
    }


def _graph() -> dict:
    nodes = [
        {"id": "biology_c1", "label": "Concept", "name": "光合作用", "properties": {"definition": "植物利用光能合成有机物并释放氧气。"}},
        {"id": "biology_light", "label": "Concept", "name": "光", "properties": {}},
        {"id": "biology_water", "label": "Concept", "name": "水", "properties": {}},
        {"id": "biology_organic", "label": "Concept", "name": "有机物", "properties": {}},
        {"id": "biology_oxygen", "label": "Concept", "name": "氧气", "properties": {}},
    ]
    edges = [
        {"source": "biology_light", "target": "biology_c1", "type": "prerequisites_for"},
        {"source": "biology_water", "target": "biology_c1", "type": "prerequisites_for"},
        {"source": "biology_c1", "target": "biology_organic", "type": "leads_to"},
        {"source": "biology_c1", "target": "biology_oxygen", "type": "leads_to"},
    ]
    return {"meta": {}, "nodes": nodes, "edges": edges}


def test_agentic_dual_level_artifacts_are_traceable() -> None:
    artifacts = build_agentic_workflow_artifacts(
        card=_card(),
        normalized_graph=_graph(),
        retrieval_mode="dual_level",
        max_edges=16,
    )
    retrieval_package = artifacts["retrieval_package"]
    mechanism_plan = artifacts["mechanism_plan"]
    raw_edge_ids = {edge["source_edge_id"] for edge in retrieval_package["raw_edges"]}

    assert retrieval_package["selected_paths"] == []
    assert retrieval_package["topic_summary"]["condition_summary"]
    assert retrieval_package["topic_summary"]["effect_summary"]
    assert retrieval_package["retrieval_stats"]["retrieval_mode"] == "dual_level"
    assert set(mechanism_plan["supporting_edge_ids"]).issubset(raw_edge_ids)


def test_agentic_batch_writes_new_and_compatibility_files(tmp_path: Path) -> None:
    cards_path = tmp_path / "cards.jsonl"
    graph_path = tmp_path / "graph.json"
    output_dir = tmp_path / "run"
    write_jsonl(cards_path, [_card()])
    write_json(graph_path, _graph())

    result = run_concept_fable_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=ConceptFableOptions(
            workflow="agentic",
            mode="local",
            language="zh-CN",
            subject=None,
            priority="gold",
            limit=1,
            offset=0,
            batch_size=1,
            retry=0,
            sleep_seconds=0.0,
            resume=False,
            evaluate_mode="rules",
            retrieval_mode="dual_level",
            max_edges=16,
            revision_rounds=0,
            template_blacklist="default",
        ),
    )
    concept_dir = output_dir / "concepts" / "biology_c1"
    story_body = (concept_dir / "draft_story.txt").read_text(encoding="utf-8").split("```json", 1)[0]

    assert result["success_count"] == 1
    assert (concept_dir / "retrieval_package.json").exists()
    assert (concept_dir / "mechanism_plan.json").exists()
    assert (concept_dir / "analogy_plan.json").exists()
    assert (concept_dir / "subgraph_pack.json").exists()
    assert (concept_dir / "structure_plan.json").exists()
    assert "光合作用" not in story_body
    assert read_json(concept_dir / "retrieval_package.json")["selected_paths"] == []

