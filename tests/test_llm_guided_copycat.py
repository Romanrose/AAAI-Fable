from __future__ import annotations

import json
from pathlib import Path

from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.llm_guided_copycat.pipeline import run_one
from kg_rag.llm_guided_copycat.scoring import inspect_template_risk, score_candidate, validate_candidate
from kg_rag.m2na_v2.schemas import MECHANISM_SCHEMA_VERSION, SEED_SCHEMA_VERSION, stable_hash


class FakeGuidedLLM:
    def complete(self, *, user_prompt: str, **_: object) -> str:
        payload = json.loads(user_prompt)
        if payload["task"] == "TASK:LLM_GUIDED_COPYCAT_META_REFINER":
            fixed = dict(payload["candidate"])
            fixed["node_mappings"] = [
                {"mechanism_node_id": "n1", "story_carrier": "港口通行资格", "mapping_type": "entity"},
                {"mechanism_node_id": "n2", "story_carrier": "补给仓持续获得物资", "mapping_type": "condition"},
            ]
            fixed["edge_mappings"] = [
                {"mechanism_edge_id": "e1", "story_relation": "缺少补给时通行资格不能成立", "direction_preserved": True}
            ]
            fixed["event_chain"] = ["登记员检查补给记录", "补给中断使通行申请被退回"]
            return json.dumps(fixed, ensure_ascii=False)
        candidates = []
        for index, domain in enumerate(("港口", "工坊", "藏书楼"), start=1):
            candidates.append(
                {
                    "candidate_id": f"candidate_{index:03d}",
                    "source_domain": domain,
                    "domain_rationale": "能够表达必要条件",
                    "conflict": "资格是否成立",
                    "event_chain": ["重复事件", "重复事件"] if index == 1 else ["先检查条件", "再判断结果"],
                    "turning_point": "缺少条件",
                    "resolution_state": "恢复条件后成立",
                    "node_mappings": [
                        {"mechanism_node_id": "n1", "story_carrier": "第1道环节" if index == 1 else f"{domain}资格", "mapping_type": "entity"},
                        {"mechanism_node_id": "n2", "story_carrier": "第2道环节" if index == 1 else f"{domain}补给", "mapping_type": "condition"},
                    ],
                    "edge_mappings": [
                        {"mechanism_edge_id": "e1", "story_relation": f"{domain}补给是资格前提", "direction_preserved": True}
                    ],
                }
            )
        return json.dumps({"candidates": candidates}, ensure_ascii=False)


def _context() -> dict:
    return {
        "seed": {"concept_id": "biology_c1", "canonical_name": "目标"},
        "mechanism_graph": {
            "nodes": [{"id": "n1"}, {"id": "n2"}],
            "edges": [{"id": "e1", "source": "n1", "target": "n2", "relation": "requires"}],
        },
        "generation_constraints": {
            "forbidden_terms": ["目标"],
            "must_preserve_node_ids": ["n1", "n2"],
            "must_preserve_edge_ids": ["e1"],
        },
    }


def test_scoring_penalizes_ordinal_and_repeated_mapping() -> None:
    context = _context()
    candidate = {
        "source_domain": "工坊",
        "conflict": "冲突",
        "event_chain": ["重复", "重复"],
        "turning_point": "转折",
        "resolution_state": "结局",
        "node_mappings": [
            {"mechanism_node_id": "n1", "story_carrier": "第1道环节"},
            {"mechanism_node_id": "n2", "story_carrier": "第2道环节"},
        ],
        "edge_mappings": [
            {"mechanism_edge_id": "e1", "story_relation": "条件成立", "direction_preserved": True}
        ],
    }

    assert not validate_candidate(candidate, context)
    assert "ordinal_placeholder_carriers" in inspect_template_risk(candidate)
    assert "repeated_events" in inspect_template_risk(candidate)
    assert score_candidate(candidate, context)["temperature"] > 10


def test_run_one_selects_valid_diverse_mapping(tmp_path: Path) -> None:
    root = tmp_path / "pilot"
    seed = {
        "schema_version": SEED_SCHEMA_VERSION,
        "concept_id": "biology_c1",
        "subject": "biology",
        "canonical_name": "目标",
        "aliases": [],
        "definition": "满足条件后成立",
        "concept_type": "definition",
        "forbidden_terms": ["目标"],
    }
    retrieval = {
        "target": {"source_node_id": "biology_c1", "name": "目标", "properties": {"definition": "满足条件后成立"}},
        "raw_edges": [],
        "topic_summary": {},
    }
    mechanism = {
        "schema_version": MECHANISM_SCHEMA_VERSION,
        "concept_id": "biology_c1",
        "mechanism_graph": _context()["mechanism_graph"],
        "generation_constraints": _context()["generation_constraints"],
        "provenance": {"seed_sha256": stable_hash(seed), "retrieval_sha256": stable_hash(retrieval)},
    }
    write_jsonl(root / "seeds.jsonl", [seed])
    write_jsonl(root / "mechanisms.approved.jsonl", [mechanism])
    write_json(root / "retrieval" / "biology_c1.json", retrieval)

    result = run_one(
        concept_id="biology_c1",
        preparation_root=root,
        output_dir=tmp_path / "run",
        llm=FakeGuidedLLM(),
        model_identity={"model": "fake"},
    )

    selected = read_json(tmp_path / "run" / "selected_mapping_plan.json")
    assert result["candidate_count"] == 3
    assert result["selected_evaluation"]["validation_errors"] == []
    assert not inspect_template_risk(selected)
    assert selected["source_domain"] in {"工坊", "藏书楼"}
