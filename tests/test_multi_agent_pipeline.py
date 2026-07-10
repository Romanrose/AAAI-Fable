from __future__ import annotations

import json
from pathlib import Path

from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.llm_client import LLMRequestError
from kg_rag.llm_config import LLMConfig
from kg_rag.multi_agent.agents import normalize_alignment
from kg_rag.multi_agent.graph import build_mechanism_graph
from kg_rag.multi_agent.metrics import evaluate_record
from kg_rag.multi_agent.llm import DeepSeekLLM
from kg_rag.multi_agent.pipeline import MultiAgentOptions, run_batch
from kg_rag.multi_agent.text import repair_mojibake_text


class FakeLLM:
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if "TASK:PLANNER_JSON" in user_prompt:
            return json.dumps(
                {
                    "source_domain": "港口调度站",
                    "characters": ["调度员", "验收员"],
                    "objects": ["通行牌", "记录册"],
                    "conflict": "货物看似已经到齐，但每道关口的条件和顺序还没有核对。",
                    "event_chain": [
                        "调度员先核对光线和水源是否同时到位。",
                        "验收员再查看小仓是否按顺序把原料转成新的存货。",
                        "最后记录册确认有新的粮包送出，也有清气被放入港口。",
                    ],
                    "turning_point": "一次提前放行导致清气缺席，记录员发现中间顺序不能跳过。",
                    "resolution_state": "港口按条件、转化和结果重新验收后，每批货都有稳定记录。",
                    "mapping_plan": [
                        {
                            "mechanism_node_id": "n1",
                            "mechanism_text": "需要光和水等条件",
                            "story_role": "光线和水源同时到位",
                        }
                    ],
                    "risk_notes": ["不要出现目标概念名。"],
                },
                ensure_ascii=False,
            )
        if "TASK:GENERATOR_STORY" in user_prompt:
            return (
                "港口调度站里，每批绿篷货都要等两枚通行牌同时亮起。"
                "调度员先核对光线和水源，缺一枚就不许开仓。"
                "验收员随后让小仓按固定顺序把送来的原料整理成新的粮包。"
                "傍晚记录册显示，粮包被送进库房，一股清气也被放入港口。"
                "有天助手想跳过中间核对，结果清气没有出现，粮包也对不上账。"
                "从那以后，调度站只承认条件、转化和结果都能互相印证的批次。"
            )
        if "TASK:ALIGNER_JSON" in user_prompt:
            return json.dumps(
                {
                    "node_alignments": [
                        {"concept_node_id": "n1", "evidence": "调度员先核对光线和水源"},
                        {"concept_node_id": "n2", "evidence": "小仓按固定顺序把送来的原料整理成新的粮包"},
                        {"concept_node_id": "n3", "evidence": "粮包被送进库房，一股清气也被放入港口"},
                    ],
                    "edge_alignments": [
                        {
                            "concept_edge_id": "e1",
                            "evidence": "调度员先核对光线和水源，缺一枚就不许开仓",
                            "narrative_source_concept_node_id": "n1",
                            "narrative_target_concept_node_id": "n2",
                            "direction_preserved": True,
                        },
                        {
                            "concept_edge_id": "e2",
                            "evidence": "验收员随后让小仓按固定顺序把送来的原料整理成新的粮包",
                            "narrative_source_concept_node_id": "n2",
                            "narrative_target_concept_node_id": "n3",
                            "direction_preserved": True,
                        },
                    ],
                },
                ensure_ascii=False,
            )
        if "TASK:ARBITER_JSON" in user_prompt:
            return json.dumps(
                {
                    "winner_candidate_id": "candidate_001",
                    "rationale": "候选一没有直接泄露，且机制顺序清楚。",
                    "risk_notes": [],
                },
                ensure_ascii=False,
            )
        if "TASK:SIX_DIM_JUDGE_JSON" in user_prompt:
            return json.dumps(
                {
                    "scores": {
                        "faithfulness": 4,
                        "implicitness": 5,
                        "mapping_clarity": 4,
                        "readability": 4,
                        "pedagogical_value": 4,
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
                    "rationales": {
                        "faithfulness": "故事保留了条件、转化和结果。",
                        "implicitness": "正文没有直接出现目标概念名。",
                        "mapping_clarity": "故事事件能对应机制节点和边。",
                        "readability": "语言连贯。",
                        "pedagogical_value": "有助于理解机制顺序。",
                        "novelty": "设定不依赖常见模板。",
                    },
                    "evidence": {
                        "faithfulness": "条件、转化和结果都被呈现。",
                        "implicitness": "未出现目标概念名。",
                        "mapping_clarity": "港口验收流程对应机制链。",
                        "readability": "故事有完整起承转合。",
                        "pedagogical_value": "读者能看出顺序不能跳过。",
                        "novelty": "使用港口调度设定。",
                    },
                    "revision_suggestions": [],
                },
                ensure_ascii=False,
            )
        if "TASK:REVISER_STORY" in user_prompt:
            return "港口按隐含顺序重新安排后，条件、转化和结果都能互相印证。"
        raise AssertionError(user_prompt[:120])


class NoPlannerFakeLLM(FakeLLM):
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if "TASK:PLANNER_JSON" in user_prompt:
            raise AssertionError("copycat strategy should not call PlannerAgent")
        return super().complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )


class RejectingJudgeFakeLLM(FakeLLM):
    def __init__(self) -> None:
        self.revision_calls = 0

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if "TASK:SIX_DIM_JUDGE_JSON" in user_prompt:
            payload = json.loads(
                super().complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            payload["scores"]["faithfulness"] = 2
            payload["scores"]["mapping_clarity"] = 2
            payload["hard_flags"]["unmapped_core_mechanism"] = True
            payload["revision_suggestions"] = ["补充缺失的机制事件。"]
            return json.dumps(payload, ensure_ascii=False)
        if "TASK:REVISER_STORY" in user_prompt:
            self.revision_calls += 1
            return f"第{self.revision_calls}次修订仍只保留了一个模糊事件。"
        return super().complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )


class AlwaysFailLLM:
    def complete(self, **_: object) -> str:
        raise RuntimeError("synthetic model failure")


class CountingFakeLLM(FakeLLM):
    def __init__(self) -> None:
        self.generation_calls = 0

    def complete(self, **kwargs: object) -> str:
        if "TASK:GENERATOR_STORY" in str(kwargs.get("user_prompt") or ""):
            self.generation_calls += 1
        return super().complete(**kwargs)


def _card() -> dict:
    return {
        "concept_id": "biology_c1",
        "subject": "biology",
        "story_language": "zh-CN",
        "canonical_name": "光合作用",
        "definition": "植物利用光能合成有机物并释放氧气。",
        "aliases": [],
        "examples": [],
        "concept_type": "process",
        "core_mechanism_zh": ["需要光和水等条件", "合成有机物", "释放氧气"],
        "must_preserve_zh": [],
        "common_misconceptions_zh": [],
        "forbidden_terms_zh": ["光合作用"],
        "subject_constraints_zh": ["避免目的论解释。"],
        "data_quality": {"generation_priority": "gold"},
    }


def _graph() -> dict:
    return {
        "nodes": [
            {"id": "biology_c1", "label": "Concept", "name": "光合作用", "properties": {"definition": "植物利用光能合成有机物并释放氧气。"}},
            {"id": "biology_light", "label": "Concept", "name": "光", "properties": {}},
            {"id": "biology_water", "label": "Concept", "name": "水", "properties": {}},
            {"id": "biology_organic", "label": "Concept", "name": "有机物", "properties": {}},
        ],
        "edges": [
            {"source": "biology_light", "target": "biology_c1", "type": "prerequisites_for"},
            {"source": "biology_water", "target": "biology_c1", "type": "prerequisites_for"},
            {"source": "biology_c1", "target": "biology_organic", "type": "leads_to"},
        ],
    }


def test_repair_mojibake_text_handles_k12_style_corruption() -> None:
    assert repair_mojibake_text("鐢熺墿") == "生物"


def test_multi_agent_batch_writes_traceable_outputs(tmp_path: Path) -> None:
    cards_path = tmp_path / "cards.jsonl"
    graph_path = tmp_path / "graph.json"
    output_dir = tmp_path / "run"
    write_jsonl(cards_path, [_card()])
    write_json(graph_path, _graph())

    result = run_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=MultiAgentOptions(
            subjects="biology",
            priority="gold",
            limit_per_subject=1,
            num_plans=2,
            revision_rounds=0,
            six_dim_mode="llm",
            resume=False,
        ),
        llm=FakeLLM(),
    )

    concept_dir = output_dir / "concepts" / "biology_c1"
    final_story = (concept_dir / "final_story.txt").read_text(encoding="utf-8")
    metrics = read_json(concept_dir / "automatic_metrics.json")
    six_dim = read_json(concept_dir / "six_dim_eval.json")

    assert result["success_count"] == 1
    assert (concept_dir / "retrieval_package.json").exists()
    assert (concept_dir / "mechanism_graph.json").exists()
    assert (concept_dir / "candidates" / "candidate_001" / "narrative_plan.json").exists()
    assert (concept_dir / "candidates" / "candidate_001" / "copycat_state.json").exists()
    assert (concept_dir / "copycat_workspace.json").exists()
    assert (concept_dir / "slipnet_activations.json").exists()
    assert (concept_dir / "coderack.final.json").exists()
    assert (concept_dir / "temperature_trace.jsonl").exists()
    assert (concept_dir / "decision.json").exists()
    assert (output_dir / "records.jsonl").exists()
    assert (output_dir / "automatic_metrics.csv").exists()
    assert "光合作用" not in final_story
    assert metrics["format_validity"] == 1.0
    assert metrics["exact_concept_leakage"] == 0.0
    assert metrics["valid_node_alignment_count"] == 3
    assert metrics["valid_edge_alignment_count"] == 2
    assert six_dim["mode"] == "llm"
    assert six_dim["scores"]["faithfulness"] == 4

    copycat_state = read_json(concept_dir / "candidates" / "candidate_001" / "copycat_state.json")
    copycat_workspace = read_json(concept_dir / "copycat_workspace.json")
    assert copycat_state["candidate_id"] == "candidate_001"
    assert copycat_state["structures"]
    assert copycat_workspace["best_candidate_id"] == "candidate_001"


def test_empty_alignment_does_not_create_coverage() -> None:
    graph = {
        "nodes": [{"id": "n1", "text": "条件"}, {"id": "n2", "text": "结果"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2", "relation": "leads_to"}],
    }
    story = "守门人先检查通行牌，随后才打开仓门。"
    alignment = normalize_alignment(
        {"node_alignments": [], "edge_alignments": []},
        mechanism_graph=graph,
        story=story,
    )
    record = {
        "id": "demo",
        "method": "test",
        "concept": {"name": "目标概念", "aliases": [], "forbidden_terms": ["目标概念"]},
        "mechanism_graph": graph,
        "output": {"narrative": story, **alignment},
    }

    metrics = evaluate_record(record)

    assert alignment == {"node_alignments": [], "edge_alignments": []}
    assert metrics["weighted_node_coverage"] == 0.0
    assert metrics["weighted_edge_coverage"] == 0.0
    assert metrics["alignment_precision"] == 0.0
    assert metrics["relation_direction_accuracy"] is None


def test_revision_rounds_are_executed_and_traced(tmp_path: Path) -> None:
    cards_path = tmp_path / "cards.jsonl"
    graph_path = tmp_path / "graph.json"
    output_dir = tmp_path / "run"
    llm = RejectingJudgeFakeLLM()
    write_jsonl(cards_path, [_card()])
    write_json(graph_path, _graph())

    result = run_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=MultiAgentOptions(
            num_plans=1,
            revision_rounds=3,
            six_dim_mode="llm",
            resume=False,
        ),
        llm=llm,
    )

    concept_dir = output_dir / "concepts" / "biology_c1"
    revision = read_json(concept_dir / "revision.json")
    status = read_json(concept_dir / "status.json")

    assert result["success_count"] == 1
    assert llm.revision_calls == 3
    assert revision["attempted_rounds"] == 3
    assert status["revision_attempted_rounds"] == 3
    assert (concept_dir / "revisions" / "round_003" / "result.json").exists()


def test_generation_fallbacks_are_visible_in_status(tmp_path: Path) -> None:
    cards_path = tmp_path / "cards.jsonl"
    graph_path = tmp_path / "graph.json"
    output_dir = tmp_path / "run"
    write_jsonl(cards_path, [_card()])
    write_json(graph_path, _graph())

    result = run_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=MultiAgentOptions(num_plans=1, revision_rounds=0, resume=False),
        llm=AlwaysFailLLM(),
    )

    concept_dir = output_dir / "concepts" / "biology_c1"
    status = read_json(concept_dir / "status.json")
    calls = read_json(concept_dir / "agent_calls.json")

    assert result["success_count"] == 1
    assert result["fallback_concept_count"] == 1
    assert status["generation_status"] == "success_with_fallback"
    assert status["fallback_count"] == 3
    assert calls["selected_candidate"]["generator"]["error"] == "synthetic model failure"


def test_resume_requires_matching_input_signature(tmp_path: Path) -> None:
    cards_path = tmp_path / "cards.jsonl"
    graph_path = tmp_path / "graph.json"
    output_dir = tmp_path / "run"
    llm = CountingFakeLLM()
    write_jsonl(cards_path, [_card()])
    write_json(graph_path, _graph())

    base_options = MultiAgentOptions(num_plans=1, revision_rounds=0, resume=True)
    run_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=base_options,
        llm=llm,
    )
    assert llm.generation_calls == 1

    run_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=base_options,
        llm=llm,
    )
    assert llm.generation_calls == 1

    run_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=MultiAgentOptions(num_plans=1, revision_rounds=0, resume=True, max_edges=2),
        llm=llm,
    )
    assert llm.generation_calls == 2


def test_deepseek_llm_retries_transient_failures(monkeypatch) -> None:
    attempts = 0

    def fake_chat_completion(**_: object) -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise LLMRequestError("temporary", retriable=True)
        return "ok"

    monkeypatch.setattr("kg_rag.multi_agent.llm.chat_completion", fake_chat_completion)
    llm = DeepSeekLLM(
        LLMConfig(
            provider="deepseek",
            base_url="https://example.invalid",
            api_key="test",
            model="test-model",
        ),
        max_attempts=3,
        retry_base_seconds=0,
    )

    result = llm.complete(system_prompt="system", user_prompt="user")

    assert result == "ok"
    assert attempts == 3


def test_mechanism_graph_does_not_attach_unrelated_kg_relation() -> None:
    mechanism_graph = build_mechanism_graph(
        card=_card(),
        retrieval_package={
            "raw_edges": [
                {
                    "source_edge_id": "normalized:edge:1",
                    "relation": "is_a",
                    "source_name": "光合作用",
                    "target_name": "生理过程",
                }
            ]
        },
    )

    assert mechanism_graph["edges"]
    assert all("kg_relation" not in edge for edge in mechanism_graph["edges"])
    assert all(edge["relation_semantic_role"] == "mechanism_sequence" for edge in mechanism_graph["edges"])


def test_copycat_strategy_builds_plan_from_codelets_without_planner(tmp_path: Path) -> None:
    cards_path = tmp_path / "cards.jsonl"
    graph_path = tmp_path / "graph.json"
    output_dir = tmp_path / "run"
    write_jsonl(cards_path, [_card()])
    write_json(graph_path, _graph())

    result = run_batch(
        concept_cards_path=cards_path,
        normalized_graph_path=graph_path,
        output_dir=output_dir,
        options=MultiAgentOptions(
            strategy="copycat",
            subjects="biology",
            priority="gold",
            limit_per_subject=1,
            num_plans=1,
            copycat_initial_candidates=2,
            revision_rounds=0,
            six_dim_mode="rules",
            resume=False,
        ),
        llm=NoPlannerFakeLLM(),
    )

    concept_dir = output_dir / "concepts" / "biology_c1"
    candidate_dir = concept_dir / "candidates" / "candidate_001"
    plan = read_json(candidate_dir / "narrative_plan.json")
    structures = read_json(candidate_dir / "copycat_structures.json")
    trace = read_json(candidate_dir / "copycat_codelet_trace.json")
    repair_trace = read_json(candidate_dir / "copycat_repair_trace.json")
    check_trace = read_json(candidate_dir / "copycat_check_trace.json")
    state = read_json(candidate_dir / "copycat_state.json")
    status = read_json(concept_dir / "status.json")
    decision = read_json(concept_dir / "decision.json")
    concept_relation_graph = read_json(concept_dir / "concept_relation_graph.json")
    metrics = read_json(concept_dir / "automatic_metrics.json")
    codelet_trace_path = concept_dir / "codelet_trace.jsonl"
    codelet_trace = [
        json.loads(line)
        for line in codelet_trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result["success_count"] == 1
    assert status["strategy"] == "copycat"
    assert decision["selection_mode"] == "copycat_temperature"
    assert status["selection_mode"] == "copycat_temperature"
    assert status["selected_temperature"] == decision["selected_temperature"]
    assert plan["source_domain"] == "港口检疫站"
    assert plan["mapping_plan"]
    assert plan["event_chain"]
    assert (concept_dir / "candidates" / "candidate_002").exists()
    assert not (concept_dir / "candidates" / "candidate_003").exists()
    assert codelet_trace_path.exists()
    assert {"structure_build", "diagnostic"} <= {item["phase"] for item in codelet_trace}
    assert concept_relation_graph["relations"]
    assert trace[0]["coderack_item"]["codelet_type"] == "BootstrapTargetConceptCodelet"
    assert trace[0]["temperature_before"] > trace[-1]["temperature_after"]
    assert {item["created_by_codelet"] for item in structures} >= {
        "BootstrapTargetConceptCodelet",
        "ProposeSourceDomainCodelet",
        "BuildConceptRelationStructuresCodelet",
        "ExtractConceptRolesCodelet",
        "MapConceptRolesToSourceDomainCodelet",
        "MapTypedRelationCodelet",
        "ProposeNodeCorrespondenceCodelet",
        "ProposeEdgeCorrespondenceCodelet",
        "BuildEventChainFragmentCodelet",
    }
    trace_names = [item["codelet_name"] for item in trace]
    assert trace_names[:6] == [
        "BootstrapTargetConceptCodelet",
        "ProposeSourceDomainCodelet",
        "BuildConceptRelationStructuresCodelet",
        "ExtractConceptRolesCodelet",
        "MapConceptRolesToSourceDomainCodelet",
        "MapTypedRelationCodelet",
    ]
    legacy_trace_order = [
        name
        for name in trace_names
        if name
        in {
            "ProposeSourceDomainCodelet",
            "ProposeNodeCorrespondenceCodelet",
            "ProposeEdgeCorrespondenceCodelet",
        }
    ]
    assert legacy_trace_order == [
        "ProposeSourceDomainCodelet",
        "ProposeNodeCorrespondenceCodelet",
        "ProposeEdgeCorrespondenceCodelet",
    ]
    assert "StrengthenEdgeCausalityCodelet" in trace_names
    assert "RepairDirectionCodelet" in trace_names
    assert trace_names[-1] == "BuildEventChainFragmentCodelet"
    assert {item["structure_type"] for item in structures} >= {
        "TargetConceptStructure",
        "ConceptRelationStructure",
        "ConceptRoleStructure",
        "RoleCorrespondence",
        "RelationCorrespondence",
    }
    assert state["structures"][0]["created_by_codelet"] == "BootstrapTargetConceptCodelet"
    assert "concept_relation_coverage" in metrics
    assert "typed_relation_preservation" in metrics
    assert repair_trace[0]["codelet_name"] == "CheckLeakageCodelet"
    assert {item["codelet_name"] for item in check_trace} >= {
        "CheckLeakageCodelet",
        "CheckDirectionCodelet",
        "CheckAlignmentEvidenceCodelet",
        "CheckTemplateRiskCodelet",
    }
    summary_text = (output_dir / "automatic_metrics.csv").read_text(encoding="utf-8-sig")
    assert "strategy" in summary_text.splitlines()[0]
    assert "selected_temperature" in summary_text.splitlines()[0]
    assert "concept_relation_coverage" in summary_text.splitlines()[0]
    assert "typed_relation_preservation" in summary_text.splitlines()[0]
