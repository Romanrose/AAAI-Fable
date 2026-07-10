from __future__ import annotations

from kg_rag.copycat.assembler import assemble_plan_from_workspace
from kg_rag.copycat.coderack import (
    followup_structure_items,
    rank_coderack_items,
    seed_coderack,
    select_coderack_item,
)
from kg_rag.copycat.codelets import repair_leakage_story, run_diagnostic_codelets
from kg_rag.copycat.controller import build_copycat_plan
from kg_rag.copycat.decision import choose_copycat_candidate
from kg_rag.copycat.slipnet import build_slipnet_state
from kg_rag.copycat.temperature import temperature_band, workspace_temperature
from kg_rag.copycat.workspace import build_candidate_state
from kg_rag.multi_agent.graph import build_concept_relation_graph
from kg_rag.multi_agent.metrics import evaluate_record


def _mechanism_graph() -> dict:
    return {
        "nodes": [
            {"id": "n1", "text": "需要先满足条件"},
            {"id": "n2", "text": "过程发生"},
            {"id": "n3", "text": "产生结果"},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2", "relation": "leads_to"},
            {"id": "e2", "source": "n2", "target": "n3", "relation": "leads_to"},
        ],
        "source": "test",
    }


def _card() -> dict:
    return {
        "concept_id": "biology_c1",
        "subject": "biology",
        "canonical_name": "光合作用",
        "aliases": ["光合"],
        "forbidden_terms_zh": ["光合作用", "光合"],
    }


def _candidate(metrics: dict, six_dim: dict | None = None) -> dict:
    return {
        "candidate_id": "candidate_001",
        "plan": {
            "source_domain": "港口调度站",
            "characters": ["调度员"],
            "objects": ["通行牌"],
            "conflict": "条件还没有核对。",
            "event_chain": ["先核对通行牌。", "再开放仓门。", "最后记录结果。"],
            "turning_point": "一次提前放行暴露了顺序问题。",
            "resolution_state": "所有环节重新按顺序执行。",
            "mapping_plan": [
                {"mechanism_node_id": "n1", "mechanism_text": "需要先满足条件", "story_role": "核对通行牌"},
                {"mechanism_node_id": "n2", "mechanism_text": "过程发生", "story_role": "开放仓门"},
            ],
        },
        "story": "港口先核对通行牌，再开放仓门，最后记录结果。",
        "alignment": {
            "node_alignments": [
                {"concept_node_id": "n1", "evidence": "先核对通行牌"},
            ],
            "edge_alignments": [
                {"concept_edge_id": "e1", "evidence": "先核对通行牌，再开放仓门"},
            ],
        },
        "automatic_metrics": metrics,
        "six_dim_eval": six_dim
        or {
            "scores": {
                "faithfulness": 4,
                "implicitness": 5,
                "mapping_clarity": 4,
                "readability": 4,
                "pedagogical_value": 4,
                "novelty": 4,
            },
            "weighted_overall": 4.2,
            "hard_flags": {
                "hard_leakage": False,
                "soft_leakage": False,
                "title_leakage": False,
                "concept_contradiction": False,
                "unmapped_core_mechanism": False,
                "template_like": False,
            },
        },
    }


def _candidate_with_id(candidate_id: str, metrics: dict) -> dict:
    candidate = _candidate(metrics)
    candidate["candidate_id"] = candidate_id
    return candidate


def test_temperature_penalizes_leakage_and_rewards_structure() -> None:
    clean_metrics = {
        "weighted_node_coverage": 0.9,
        "weighted_edge_coverage": 0.85,
        "alignment_precision": 0.9,
        "relation_direction_accuracy": 1.0,
        "exact_concept_leakage": 0.0,
        "soft_term_leakage": 0.0,
        "template_hit_rate": 0.0,
    }
    leaking_metrics = {**clean_metrics, "exact_concept_leakage": 1.0}

    clean_temperature = workspace_temperature(clean_metrics, {"weighted_overall": 4.5})
    leaking_temperature = workspace_temperature(leaking_metrics, {"weighted_overall": 4.5})

    assert temperature_band(clean_temperature) in {"stable", "repairable"}
    assert leaking_temperature > clean_temperature


def test_slipnet_activates_edge_pressure_and_seeds_coderack() -> None:
    metrics = {
        "weighted_node_coverage": 0.8,
        "weighted_edge_coverage": 0.25,
        "alignment_precision": 0.5,
        "relation_direction_accuracy": 0.6,
        "exact_concept_leakage": 0.0,
        "soft_term_leakage": 0.0,
        "template_hit_rate": 0.0,
    }

    slipnet = build_slipnet_state(metrics, {"scores": {"mapping_clarity": 2}})
    node_ids = {item["node_id"] for item in slipnet["activations"]}
    assert "failure.low_edge_coverage" in node_ids
    assert "failure.direction_error" in node_ids

    state = build_candidate_state(candidate=_candidate(metrics), mechanism_graph=_mechanism_graph()).to_dict()
    coderack = seed_coderack(state)
    codelet_types = {item["codelet_type"] for item in coderack}
    assert "ProposeEdgeCorrespondenceCodelet" in codelet_types
    assert "RepairDirectionCodelet" in codelet_types


def test_coderack_selection_uses_temperature_adjusted_urgency() -> None:
    items = [
        {
            "item_id": "low",
            "codelet_type": "LowSensitivityCodelet",
            "urgency": 0.7,
            "temperature_sensitivity": 0.0,
        },
        {
            "item_id": "high",
            "codelet_type": "HighSensitivityCodelet",
            "urgency": 0.6,
            "temperature_sensitivity": 0.8,
        },
    ]

    assert select_coderack_item(items, temperature=0)["item_id"] == "low"
    assert select_coderack_item(items, temperature=100)["item_id"] == "high"
    ranked = rank_coderack_items(items, temperature=100)
    assert ranked[0]["adjusted_urgency"] > ranked[1]["adjusted_urgency"]


def test_structure_coderack_followups_have_distinct_item_ids() -> None:
    after_edge = followup_structure_items(
        candidate_id="candidate_001",
        completed_codelet="ProposeEdgeCorrespondenceCodelet",
        step=3,
    )
    after_strengthen = followup_structure_items(
        candidate_id="candidate_001",
        completed_codelet="StrengthenEdgeCausalityCodelet",
        step=4,
    )
    ids = [item["item_id"] for item in [*after_edge, *after_strengthen]]
    assert len(ids) == len(set(ids))


def test_candidate_state_extracts_structures_and_assembles_plan() -> None:
    metrics = {
        "weighted_node_coverage": 0.75,
        "weighted_edge_coverage": 0.7,
        "alignment_precision": 0.8,
        "relation_direction_accuracy": 1.0,
        "exact_concept_leakage": 0.0,
        "soft_term_leakage": 0.0,
        "template_hit_rate": 0.0,
    }
    state = build_candidate_state(candidate=_candidate(metrics), mechanism_graph=_mechanism_graph()).to_dict()
    structure_types = {structure["structure_type"] for structure in state["structures"]}

    assert "SourceDomainStructure" in structure_types
    assert "NodeCorrespondence" in structure_types
    assert "EdgeCorrespondence" in structure_types
    assert "EventChainFragment" in structure_types

    assembled = assemble_plan_from_workspace(state)
    assert assembled["source_domain"] == "港口调度站"
    assert assembled["event_chain"]
    assert assembled["mapping_plan"]


def test_copycat_plan_includes_causality_and_direction_repair_fragments() -> None:
    payload = build_copycat_plan(
        card=_card(),
        mechanism_graph=_mechanism_graph(),
        candidate_id="candidate_001",
        candidate_index=1,
    )
    trace_names = [item["codelet_name"] for item in payload["codelet_trace"]]
    created_by = {structure["created_by_codelet"] for structure in payload["structures"]}
    event_chain = payload["plan"]["event_chain"]

    assert "StrengthenEdgeCausalityCodelet" in trace_names
    assert "RepairDirectionCodelet" in trace_names
    assert "StrengthenEdgeCausalityCodelet" in created_by
    assert "RepairDirectionCodelet" in created_by
    assert any("因此" in event for event in event_chain)
    assert any("倒过来安排" in event for event in event_chain)


def test_copycat_max_steps_limits_structure_codelets() -> None:
    payload = build_copycat_plan(
        card=_card(),
        mechanism_graph=_mechanism_graph(),
        candidate_id="candidate_001",
        candidate_index=1,
        max_steps=1,
    )

    assert len(payload["codelet_trace"]) == 1
    assert payload["codelet_trace"][0]["codelet_name"] == "BootstrapTargetConceptCodelet"


def test_repair_leakage_codelet_masks_forbidden_terms() -> None:
    story = "这篇故事直接说出了光合作用和光合两个词。"
    repaired, trace = repair_leakage_story(card=_card(), candidate_id="candidate_001", story=story)

    assert "光合作用" not in repaired
    assert "光合" not in repaired
    assert repaired.count("那条隐秘规则") >= 1
    assert [item["codelet_name"] for item in trace] == ["CheckLeakageCodelet", "RepairLeakageCodelet"]


def test_diagnostic_codelets_report_direction_alignment_and_template_pressure() -> None:
    metrics = {
        "relation_direction_accuracy": 0.2,
        "alignment_precision": 0.25,
        "template_hit_rate": 0.4,
    }
    trace = run_diagnostic_codelets(
        card=_card(),
        candidate_id="candidate_001",
        story="短。光合作用。",
        alignment={"node_alignments": [{"concept_node_id": "n1", "evidence": "不存在的证据"}], "edge_alignments": []},
        metrics=metrics,
    )
    by_name = {item["codelet_name"]: item for item in trace}

    assert by_name["CheckLeakageCodelet"]["activations_delta"]["failure.leakage"] == 1.0
    assert by_name["CheckDirectionCodelet"]["activations_delta"]["failure.direction_error"] > 0
    assert by_name["CheckAlignmentEvidenceCodelet"]["activations_delta"]["failure.weak_alignment"] > 0
    assert by_name["CheckTemplateRiskCodelet"]["activations_delta"]["failure.template_like"] > 0
    assert by_name["RealignEvidenceCodelet"]["structures_added"][0]["structure_type"] == "AlignmentEvidenceRepair"
    assert by_name["ProposeAlternativeSourceDomainCodelet"]["structures_added"][0]["structure_type"] == "AlternativeSourceDomainStructure"


def test_copycat_decision_prefers_low_temperature_candidate() -> None:
    leaking = _candidate_with_id(
        "candidate_001",
        {
            "weighted_node_coverage": 0.9,
            "weighted_edge_coverage": 0.9,
            "alignment_precision": 0.9,
            "relation_direction_accuracy": 1.0,
            "exact_concept_leakage": 1.0,
            "soft_term_leakage": 0.0,
            "template_hit_rate": 0.0,
        },
    )
    stable = _candidate_with_id(
        "candidate_002",
        {
            "weighted_node_coverage": 0.75,
            "weighted_edge_coverage": 0.7,
            "alignment_precision": 0.8,
            "relation_direction_accuracy": 1.0,
            "exact_concept_leakage": 0.0,
            "soft_term_leakage": 0.0,
            "template_hit_rate": 0.0,
        },
    )

    decision = choose_copycat_candidate(
        candidates=[leaking, stable],
        mechanism_graph=_mechanism_graph(),
        temperature_threshold=60.0,
    )

    assert decision["winner_candidate_id"] == "candidate_002"
    assert decision["selection_mode"] == "copycat_temperature"
    assert decision["selected_within_temperature_threshold"] is True
    assert decision["temperature_threshold"] == 60.0
    assert decision["ranked_candidates"][0]["temperature"] < decision["ranked_candidates"][1]["temperature"]


def test_concept_relation_graph_preserves_typed_raw_edges() -> None:
    graph = build_concept_relation_graph(
        card={"concept_id": "biology_c1", "canonical_name": "遗传和变异"},
        retrieval_package={
            "target": {
                "source_node_id": "biology_c1",
                "label": "Concept",
                "name": "遗传和变异",
                "properties": {"definition": "同中有异。"},
            },
            "raw_edges": [
                {
                    "source_edge_id": "normalized:edge:1",
                    "source": "biology_c1",
                    "source_name": "遗传和变异",
                    "target": "biology_parent",
                    "target_name": "生物的共同特征",
                    "relation": "is_a",
                    "score": 1.0,
                }
            ],
        },
    )

    assert graph["target_concept"]["id"] == "biology_c1"
    assert graph["relations"][0]["source_name"] == "遗传和变异"
    assert graph["relations"][0]["target_name"] == "生物的共同特征"
    assert graph["relations"][0]["relation"] == "is_a"
    assert graph["relations"][0]["direction"] == "outgoing"
    assert graph["relations"][0]["relation_semantic_role"] == "category_membership"


def test_copycat_plan_maps_is_a_without_turning_it_into_sequence() -> None:
    mechanism_graph = {
        "nodes": [
            {"id": "n1", "text": "同中有异的现象。"},
            {"id": "n2", "text": "生物的共同特征。"},
        ],
        "edges": [
            {
                "id": "e1",
                "source": "n1",
                "target": "n2",
                "relation": "leads_to",
                "kg_relation": "is_a",
                "source_edge_id": "normalized:edge:1",
                "relation_semantic_role": "category_membership",
                "source_name": "遗传和变异",
                "target_name": "生物的共同特征",
            }
        ],
    }
    payload = build_copycat_plan(
        card={
            "concept_id": "biology_c1",
            "subject": "biology",
            "canonical_name": "遗传和变异",
            "definition": "子代与亲代有相同特征，也有不同特征。",
            "forbidden_terms_zh": ["遗传和变异"],
        },
        mechanism_graph=mechanism_graph,
        concept_relation_graph={
            "relations": [
                {
                    "edge_id": "normalized:edge:1",
                    "source_name": "遗传和变异",
                    "target_name": "生物的共同特征",
                    "neighbor_name": "生物的共同特征",
                    "relation": "is_a",
                    "relation_semantic_role": "category_membership",
                    "direction": "outgoing",
                }
            ]
        },
        candidate_id="candidate_001",
        candidate_index=1,
    )
    structure_types = {structure["structure_type"] for structure in payload["structures"]}
    relation_mappings = payload["plan"]["concept_relation_mappings"]

    assert "ConceptRelationStructure" in structure_types
    assert "RelationCorrespondence" in structure_types
    assert relation_mappings[0]["kg_relation"] == "is_a"
    assert relation_mappings[0]["story_relation_type"] == "category_membership"
    assert "归入" in relation_mappings[0]["story_relation"]
    assert "同出一件母版" in relation_mappings[0]["story_relation"]
    assert "生物" not in relation_mappings[0]["story_relation"]
    assert "先稳定" not in relation_mappings[0]["story_relation"]
    assert "再推动" not in relation_mappings[0]["story_relation"]


def test_relation_aware_codelets_encode_prerequisite_and_verification_semantics() -> None:
    mechanism_graph = {
        "nodes": [
            {"id": "n1", "text": "前置条件。"},
            {"id": "n2", "text": "证据检验。"},
            {"id": "n3", "text": "结论。"},
        ],
        "edges": [
            {
                "id": "e1",
                "source": "n1",
                "target": "n2",
                "relation": "leads_to",
                "kg_relation": "prerequisites_for",
                "source_edge_id": "normalized:edge:1",
            },
            {
                "id": "e2",
                "source": "n2",
                "target": "n3",
                "relation": "leads_to",
                "kg_relation": "verifies",
                "source_edge_id": "normalized:edge:2",
            },
        ],
    }
    payload = build_copycat_plan(
        card=_card(),
        mechanism_graph=mechanism_graph,
        concept_relation_graph={
            "relations": [
                {"edge_id": "normalized:edge:1", "relation": "prerequisites_for", "neighbor_name": "前置知识"},
                {"edge_id": "normalized:edge:2", "relation": "verifies", "neighbor_name": "实验记录"},
            ]
        },
        candidate_id="candidate_001",
        candidate_index=1,
    )
    event_chain = "\n".join(payload["plan"]["event_chain"])

    assert "前置" in event_chain
    assert "缺少" in event_chain
    assert "检验" in event_chain
    assert "证据" in event_chain


def test_heredity_variation_plan_extracts_concept_roles() -> None:
    payload = build_copycat_plan(
        card={
            "concept_id": "biology_c1",
            "subject": "biology",
            "canonical_name": "遗传和变异",
            "definition": "子代与亲代在很多方面表现出相同特征，但总有一部分特征不相同。",
            "forbidden_terms_zh": ["遗传和变异"],
        },
        mechanism_graph={
            "nodes": [
                {
                    "id": "n1",
                    "text": "子代与亲代在很多方面表现出相同特征，但总有一部分特征不相同。",
                }
            ],
            "edges": [],
        },
        concept_relation_graph={"relations": []},
        candidate_id="candidate_001",
        candidate_index=1,
    )
    role_ids = {
        mapping["concept_role_id"]
        for mapping in payload["plan"]["concept_role_mappings"]
    }
    story_roles = "\n".join(
        mapping["story_role"]
        for mapping in payload["plan"]["concept_role_mappings"]
    )

    assert payload["plan"]["source_domain"] == "瓷器作坊"
    assert {"parent_generation", "offspring_generation", "shared_traits", "variant_traits"} <= role_ids
    assert "母版" in story_roles
    assert "新做出" in story_roles
    assert "轮廓、纹样骨架和比例" in story_roles
    assert "局部釉色、纹理疏密和边角细节差异" in story_roles
    assert "编号规则" not in story_roles
    assert "封条" not in story_roles
    assert "新增划痕" not in story_roles


def test_metrics_report_concept_relation_coverage_and_typed_preservation() -> None:
    record = {
        "id": "c1",
        "method": "test",
        "concept": {"name": "目标", "aliases": [], "forbidden_terms": ["目标"]},
        "mechanism_graph": {
            "nodes": [{"id": "n1", "text": "前置条件"}, {"id": "n2", "text": "结果"}],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "relation": "leads_to",
                    "kg_relation": "prerequisites_for",
                }
            ],
        },
        "output": {
            "narrative": "主角先确认前置条件牌，缺少这一步就不能开始。",
            "node_alignments": [
                {"concept_node_id": "n1", "evidence": "前置条件牌"},
                {"concept_node_id": "n2", "evidence": "不能开始"},
            ],
            "edge_alignments": [
                {
                    "concept_edge_id": "e1",
                    "narrative_relation": "先确认前置条件，缺少就不能开始",
                    "evidence": "先确认前置条件牌",
                    "narrative_source_concept_node_id": "n1",
                    "narrative_target_concept_node_id": "n2",
                }
            ],
        },
    }
    metrics = evaluate_record(record)

    assert metrics["concept_relation_coverage"] == 1.0
    assert metrics["typed_relation_preservation"] == 1.0
