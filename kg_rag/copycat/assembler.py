from __future__ import annotations

from typing import Any


def _structure_dict(structure: Any) -> dict[str, Any]:
    if hasattr(structure, "to_dict"):
        return structure.to_dict()
    return structure if isinstance(structure, dict) else {}


def assemble_plan_from_structures(structures: list[Any]) -> dict[str, Any]:
    structure_dicts = [
        _structure_dict(structure)
        for structure in structures
        if _structure_dict(structure)
        and float(_structure_dict(structure).get("strength") or 0.0) >= 0.4
    ]
    return _assemble_plan(structure_dicts)


def assemble_plan_from_workspace(candidate_state: dict[str, Any]) -> dict[str, Any]:
    """Assemble a generator-compatible plan from strong workspace structures.

    This is intentionally conservative for the first Copycat slice: it reconstructs
    the current plan-shaped fields from structures instead of inventing new story
    content.
    """
    return _assemble_plan(
        [
            structure
            for structure in candidate_state.get("structures", [])
            if isinstance(structure, dict) and float(structure.get("strength") or 0.0) >= 0.4
        ]
    )


def _assemble_plan(structures: list[dict[str, Any]]) -> dict[str, Any]:
    structures = [
        structure
        for structure in structures
        if isinstance(structure, dict) and float(structure.get("strength") or 0.0) >= 0.4
    ]
    plan: dict[str, Any] = {
        "source_domain": None,
        "characters": [],
        "objects": [],
        "conflict": None,
        "event_chain": [],
        "turning_point": None,
        "resolution_state": None,
        "mapping_plan": [],
        "concept_role_mappings": [],
        "concept_relation_mappings": [],
        "risk_notes": [],
    }
    for structure in structures:
        content = structure.get("content", {}) if isinstance(structure.get("content"), dict) else {}
        structure_type = structure.get("structure_type")
        if structure_type == "SourceDomainStructure":
            plan["source_domain"] = content.get("source_domain")
        elif structure_type == "NodeCorrespondence":
            plan["mapping_plan"].append(
                {
                    "mechanism_node_id": content.get("mechanism_node_id"),
                    "mechanism_text": content.get("mechanism_text"),
                    "story_role": content.get("narrative_carrier"),
                }
            )
        elif structure_type == "RoleCorrespondence":
            role_mapping = {
                "concept_role_id": content.get("concept_role_id"),
                "role_label": content.get("role_label"),
                "role_type": content.get("role_type"),
                "story_role": content.get("story_role"),
            }
            plan["concept_role_mappings"].append(role_mapping)
            plan["mapping_plan"].append(role_mapping)
        elif structure_type == "RelationCorrespondence":
            relation_mapping = {
                "source_edge_id": content.get("source_edge_id"),
                "kg_relation": content.get("kg_relation"),
                "relation_semantic_role": content.get("relation_semantic_role"),
                "story_relation_type": content.get("story_relation_type"),
                "story_relation": content.get("story_relation"),
                "source_name": content.get("source_name"),
                "target_name": content.get("target_name"),
            }
            plan["concept_relation_mappings"].append(relation_mapping)
            plan["mapping_plan"].append(relation_mapping)
            if content.get("story_relation"):
                plan["event_chain"].append(content["story_relation"])
        elif structure_type == "EdgeCorrespondence":
            plan["mapping_plan"].append(
                {
                    "mechanism_edge_id": content.get("mechanism_edge_id"),
                    "kg_relation": content.get("kg_relation"),
                    "story_relation": content.get("narrative_relation"),
                    "source_edge_id": content.get("source_edge_id"),
                }
            )
        elif structure_type == "EventChainFragment" and content.get("event"):
            plan["event_chain"].append(content["event"])
        elif structure_type == "ConflictStructure":
            plan["conflict"] = content.get("conflict")
        elif structure_type == "TurningPointStructure":
            plan["turning_point"] = content.get("turning_point")
        elif structure_type == "ResolutionStructure":
            plan["resolution_state"] = content.get("resolution_state")
    if plan["source_domain"]:
        if plan["source_domain"] in {"瓷器作坊", "织坊花样间", "印章拓印坊", "木偶工坊"}:
            plan["characters"] = ["老匠人", "学徒", "验收员"]
            plan["objects"] = ["母版", "新件", "细节记录册"]
        else:
            plan["characters"] = ["记录员", "调度员", "验收员"]
            plan["objects"] = ["分段记录册", "封存箱", "通行牌"]
    plan["risk_notes"] = [
        "正文不能出现目标概念名、别名或禁用术语。",
        "事件必须保留 GraphRAG 概念关系的类型语义，不要把 is_a、verifies、relates_to 全部写成顺序因果。",
    ]
    return plan
