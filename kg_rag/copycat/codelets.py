from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re

from kg_rag.copycat.text import contains_term, mask_forbidden_terms, split_sentences, unique_strings
from kg_rag.copycat.coderack import (
    followup_structure_items,
    seed_structure_coderack,
    select_coderack_item,
)
from kg_rag.copycat.workspace import WorkspaceStructure


SOURCE_DOMAINS = {
    "biology": ["港口检疫站", "园圃值守所", "剧场后台", "邮局分拣房"],
    "chemistry": ["账房仓库", "铸造工坊", "印章局", "城邦交换所"],
    "physics": ["水渠调度站", "滑道试验场", "船队信号台", "秤房"],
    "math": ["规则棋局", "法庭证据室", "地图修补坊", "拼图工坊"],
}

COPY_WITH_VARIATION_DOMAINS = ["瓷器作坊", "织坊花样间", "印章拓印坊", "木偶工坊"]


@dataclass(frozen=True)
class CodeletResult:
    codelet_name: str
    target_candidate_id: str | None
    structures_added: list[dict[str, Any]] = field(default_factory=list)
    structures_removed: list[str] = field(default_factory=list)
    activations_delta: dict[str, float] = field(default_factory=dict)
    temperature_before: float | None = None
    temperature_after: float | None = None
    confidence: float = 1.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "codelet_name": self.codelet_name,
            "target_candidate_id": self.target_candidate_id,
            "structures_added": self.structures_added,
            "structures_removed": self.structures_removed,
            "activations_delta": self.activations_delta,
            "temperature_before": self.temperature_before,
            "temperature_after": self.temperature_after,
            "confidence": self.confidence,
            "notes": self.notes,
        }


class EvaluateStructureStrengthCodelet:
    name = "EvaluateStructureStrengthCodelet"

    def run(self, candidate_state: dict[str, Any]) -> CodeletResult:
        structures = candidate_state.get("structures", [])
        weak = [
            structure.get("structure_id")
            for structure in structures
            if isinstance(structure, dict) and float(structure.get("strength") or 0.0) < 0.45
        ]
        return CodeletResult(
            codelet_name=self.name,
            target_candidate_id=candidate_state.get("candidate_id"),
            temperature_before=candidate_state.get("temperature"),
            temperature_after=candidate_state.get("temperature"),
            confidence=1.0,
            notes=[f"weak_structure_count={len(weak)}"],
        )


def _forbidden_terms(card: dict[str, Any]) -> list[str]:
    return unique_strings(
        [
            card.get("canonical_name"),
            *card.get("aliases", []),
            *card.get("forbidden_terms_zh", []),
        ]
    )


class CheckLeakageCodelet:
    name = "CheckLeakageCodelet"

    def run(self, *, card: dict[str, Any], candidate_id: str, story: str) -> CodeletResult:
        leaked_terms = [term for term in _forbidden_terms(card) if contains_term(story, term)]
        return CodeletResult(
            codelet_name=self.name,
            target_candidate_id=candidate_id,
            activations_delta={"failure.leakage": 1.0 if leaked_terms else 0.0},
            confidence=1.0,
            notes=[f"leaked_terms={','.join(leaked_terms)}"] if leaked_terms else ["no_leakage_detected"],
        )


class RepairLeakageCodelet:
    name = "RepairLeakageCodelet"

    def run(self, *, card: dict[str, Any], candidate_id: str, story: str) -> tuple[str, CodeletResult]:
        repaired = mask_forbidden_terms(story, _forbidden_terms(card))
        changed = repaired != story
        return (
            repaired,
            CodeletResult(
                codelet_name=self.name,
                target_candidate_id=candidate_id,
                activations_delta={"failure.leakage": -1.0 if changed else 0.0},
                confidence=1.0,
                notes=["leakage_repaired"] if changed else ["no_repair_needed"],
            ),
        )


class CheckDirectionCodelet:
    name = "CheckDirectionCodelet"

    def run(self, *, candidate_id: str, metrics: dict[str, Any]) -> CodeletResult:
        direction = metrics.get("relation_direction_accuracy")
        if direction is None:
            return CodeletResult(
                codelet_name=self.name,
                target_candidate_id=candidate_id,
                confidence=0.7,
                notes=["direction_metric_unavailable"],
            )
        direction_value = float(direction)
        activation = max(0.0, 0.75 - direction_value) / 0.75
        return CodeletResult(
            codelet_name=self.name,
            target_candidate_id=candidate_id,
            activations_delta={"failure.direction_error": activation},
            confidence=1.0,
            notes=[f"relation_direction_accuracy={direction_value:.4f}"],
        )


class CheckAlignmentEvidenceCodelet:
    name = "CheckAlignmentEvidenceCodelet"

    def run(
        self,
        *,
        candidate_id: str,
        story: str,
        alignment: dict[str, Any],
        metrics: dict[str, Any],
    ) -> CodeletResult:
        missing = 0
        for bucket in ("node_alignments", "edge_alignments"):
            for item in alignment.get(bucket, []):
                if not isinstance(item, dict):
                    continue
                evidence = str(item.get("evidence") or item.get("narrative_anchor") or "")
                if evidence and evidence not in story:
                    missing += 1
        precision = float(metrics.get("alignment_precision") or 0.0)
        activation = max(0.0, 0.75 - precision) / 0.75
        if missing:
            activation = max(activation, min(1.0, missing / 3.0))
        return CodeletResult(
            codelet_name=self.name,
            target_candidate_id=candidate_id,
            activations_delta={"failure.weak_alignment": activation},
            confidence=1.0,
            notes=[f"alignment_precision={precision:.4f}", f"missing_evidence_count={missing}"],
        )


class CheckTemplateRiskCodelet:
    name = "CheckTemplateRiskCodelet"

    def run(self, *, candidate_id: str, story: str, metrics: dict[str, Any]) -> CodeletResult:
        template_rate = float(metrics.get("template_hit_rate") or 0.0)
        short_sentence_count = sum(1 for sentence in split_sentences(story) if len(sentence) < 8)
        activation = min(1.0, template_rate + 0.15 * short_sentence_count)
        return CodeletResult(
            codelet_name=self.name,
            target_candidate_id=candidate_id,
            activations_delta={"failure.template_like": activation},
            confidence=0.9,
            notes=[f"template_hit_rate={template_rate:.4f}", f"short_sentence_count={short_sentence_count}"],
        )


class RealignEvidenceCodelet:
    name = "RealignEvidenceCodelet"

    def run(
        self,
        *,
        candidate_id: str,
        story: str,
        alignment: dict[str, Any],
    ) -> CodeletResult:
        sentences = split_sentences(story)
        fallback = sentences[0][:40] if sentences else story[:40]
        structures: list[dict[str, Any]] = []
        index = 1
        for bucket in ("node_alignments", "edge_alignments"):
            for item in alignment.get(bucket, []):
                if not isinstance(item, dict):
                    continue
                evidence = str(item.get("evidence") or item.get("narrative_anchor") or "")
                if evidence and evidence in story:
                    continue
                concept_id = item.get("concept_node_id") or item.get("concept_edge_id") or f"unknown_{index}"
                structures.append(
                    WorkspaceStructure(
                        structure_id=f"{candidate_id}:realign_evidence:{index:03d}",
                        structure_type="AlignmentEvidenceRepair",
                        content={
                            "alignment_type": bucket,
                            "concept_id": concept_id,
                            "suggested_evidence": fallback,
                            "repair_target": "alignment_evidence",
                        },
                        strength=0.58,
                        salience=0.72,
                        support=["story.sentences"],
                        created_by_codelet=self.name,
                        candidate_id=candidate_id,
                    ).to_dict()
                )
                index += 1
        return CodeletResult(
            codelet_name=self.name,
            target_candidate_id=candidate_id,
            structures_added=structures,
            activations_delta={"failure.weak_alignment": -0.4 if structures else 0.0},
            confidence=0.75,
            notes=[f"realignment_hints={len(structures)}"],
        )


class ProposeAlternativeSourceDomainCodelet:
    name = "ProposeAlternativeSourceDomainCodelet"

    def run(
        self,
        *,
        card: dict[str, Any],
        candidate_id: str,
        current_source_domain: str | None,
    ) -> CodeletResult:
        domains = SOURCE_DOMAINS.get(str(card.get("subject") or ""), ["修补工坊", "档案局", "港口调度站"])
        alternative = next((domain for domain in domains if domain != current_source_domain), domains[0])
        structure = WorkspaceStructure(
            structure_id=f"{candidate_id}:alternative_source_domain:001",
            structure_type="AlternativeSourceDomainStructure",
            content={
                "source_domain": alternative,
                "replaces": current_source_domain,
                "repair_target": "template_like",
            },
            strength=0.6,
            salience=0.8,
            support=["failure.template_like", "copycat.source_domain_pool"],
            created_by_codelet=self.name,
            candidate_id=candidate_id,
        )
        return CodeletResult(
            codelet_name=self.name,
            target_candidate_id=candidate_id,
            structures_added=[structure.to_dict()],
            activations_delta={"failure.template_like": -0.35},
            confidence=0.72,
            notes=[f"alternative_source_domain={alternative}"],
        )


def repair_leakage_story(
    *,
    card: dict[str, Any],
    candidate_id: str,
    story: str,
) -> tuple[str, list[dict[str, Any]]]:
    check = CheckLeakageCodelet().run(card=card, candidate_id=candidate_id, story=story)
    repaired, repair = RepairLeakageCodelet().run(card=card, candidate_id=candidate_id, story=story)
    trace = [check.to_dict()]
    if repaired != story:
        trace.append(repair.to_dict())
    return repaired, trace


def run_diagnostic_codelets(
    *,
    card: dict[str, Any],
    candidate_id: str,
    story: str,
    alignment: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    trace = [
        CheckLeakageCodelet().run(card=card, candidate_id=candidate_id, story=story).to_dict(),
        CheckDirectionCodelet().run(candidate_id=candidate_id, metrics=metrics).to_dict(),
        CheckAlignmentEvidenceCodelet()
        .run(candidate_id=candidate_id, story=story, alignment=alignment, metrics=metrics)
        .to_dict(),
        CheckTemplateRiskCodelet().run(candidate_id=candidate_id, story=story, metrics=metrics).to_dict(),
        EvaluateStructureStrengthCodelet()
        .run(
            {
                "candidate_id": candidate_id,
                "structures": [],
                "temperature": None,
            }
        )
        .to_dict(),
    ]
    alignment_check = trace[2]
    template_check = trace[3]
    if alignment_check.get("activations_delta", {}).get("failure.weak_alignment", 0.0) > 0:
        trace.append(
            RealignEvidenceCodelet()
            .run(candidate_id=candidate_id, story=story, alignment=alignment)
            .to_dict()
        )
    if template_check.get("activations_delta", {}).get("failure.template_like", 0.0) > 0:
        trace.append(
            ProposeAlternativeSourceDomainCodelet()
            .run(card=card, candidate_id=candidate_id, current_source_domain=None)
            .to_dict()
        )
    return trace


def _is_copy_with_variation_card(card: dict[str, Any]) -> bool:
    text = " ".join(
        str(part or "")
        for part in [
            card.get("canonical_name"),
            card.get("definition"),
            card.get("core_mechanism_zh"),
            card.get("must_preserve_zh"),
            *card.get("aliases", []),
        ]
    )
    lineage_hits = sum(1 for term in ("亲代", "子代", "上一代", "下一代") if term in text)
    variation_hits = sum(1 for term in ("相同特征", "不同特征", "差异", "变异") if term in text)
    return "遗传" in text or (lineage_hits >= 1 and variation_hits >= 1)


def _domain_for(card: dict[str, Any], candidate_index: int) -> str:
    if _is_copy_with_variation_card(card):
        return COPY_WITH_VARIATION_DOMAINS[(candidate_index - 1) % len(COPY_WITH_VARIATION_DOMAINS)]
    domains = SOURCE_DOMAINS.get(str(card.get("subject") or ""), ["修补工坊", "档案局", "港口调度站"])
    return domains[(candidate_index - 1) % len(domains)]


def _node_role(index: int, total: int) -> str:
    if total <= 1:
        return "核心隐含环节"
    if index == 0:
        return "入口条件核对"
    if index == total - 1:
        return "结果验收记录"
    return f"第{index + 1}道转化环节"


def propose_source_domain_structure(
    *,
    card: dict[str, Any],
    candidate_id: str,
    candidate_index: int,
) -> WorkspaceStructure:
    source_domain = _domain_for(card, candidate_index)
    return WorkspaceStructure(
        structure_id=f"{candidate_id}:source_domain:001",
        structure_type="SourceDomainStructure",
        content={
            "source_domain": source_domain,
            "selection_basis": (
                "copy_with_variation_role_compatibility"
                if _is_copy_with_variation_card(card)
                else "subject_rotating_domain_pool"
            ),
        },
        strength=0.72,
        salience=0.82,
        support=["copycat.source_domain_pool", f"subject={card.get('subject')}"],
        created_by_codelet="ProposeSourceDomainCodelet",
        candidate_id=candidate_id,
    )


def bootstrap_target_concept_structure(
    *,
    card: dict[str, Any],
    candidate_id: str,
) -> WorkspaceStructure:
    return WorkspaceStructure(
        structure_id=f"{candidate_id}:target_concept:001",
        structure_type="TargetConceptStructure",
        content={
            "concept_id": card.get("concept_id"),
            "name": card.get("canonical_name") or card.get("concept_id"),
            "definition": card.get("definition", ""),
            "forbidden_terms": _forbidden_terms(card),
        },
        strength=0.9,
        salience=1.0,
        support=["concept_card"],
        created_by_codelet="BootstrapTargetConceptCodelet",
        candidate_id=candidate_id,
    )


def build_concept_relation_structures(
    *,
    concept_relation_graph: dict[str, Any],
    mechanism_graph: dict[str, Any],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    relations = [
        relation
        for relation in concept_relation_graph.get("relations", [])
        if isinstance(relation, dict)
    ]
    if not relations:
        for edge in mechanism_graph.get("edges", []):
            if not isinstance(edge, dict):
                continue
            relations.append(
                {
                    "edge_id": edge.get("source_edge_id") or edge.get("id"),
                    "source_id": edge.get("source"),
                    "source_name": edge.get("source_name") or edge.get("source"),
                    "target_id": edge.get("target"),
                    "target_name": edge.get("target_name") or edge.get("target"),
                    "relation": edge.get("kg_relation") or edge.get("relation"),
                    "relation_semantic_role": edge.get("relation_semantic_role", "association"),
                    "direction": "mechanism",
                    "neighbor_name": edge.get("target_name") or edge.get("target"),
                }
            )
    structures: list[WorkspaceStructure] = []
    for index, relation in enumerate(relations, start=1):
        relation_type = str(relation.get("relation") or "relates_to")
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:concept_relation:{index:03d}",
                structure_type="ConceptRelationStructure",
                content={
                    "source_edge_id": relation.get("edge_id"),
                    "source_id": relation.get("source_id"),
                    "source_name": relation.get("source_name"),
                    "target_id": relation.get("target_id"),
                    "target_name": relation.get("target_name"),
                    "neighbor_name": relation.get("neighbor_name"),
                    "kg_relation": relation_type,
                    "relation_semantic_role": relation.get("relation_semantic_role"),
                    "direction": relation.get("direction"),
                },
                strength=0.76,
                salience=0.96,
                support=["concept_relation_graph.relations"],
                created_by_codelet="BuildConceptRelationStructuresCodelet",
                candidate_id=candidate_id,
            )
        )
    return structures


SUBJECT_ROLE_RULES = {
    "biology": [
        ("parent_generation", "亲代", "source_entity", ("亲代", "上一代", "母体", "父本", "母本")),
        ("offspring_generation", "子代", "target_entity", ("子代", "后代", "幼体", "新一代")),
        ("shared_traits", "相同特征", "preserved_property", ("相同", "共同", "一致", "相似")),
        ("variant_traits", "不同特征", "changed_property", ("不同", "不相同", "差异", "变异")),
        ("environment", "环境", "condition", ("环境", "条件", "光", "水", "温度")),
        ("process", "过程", "process", ("过程", "发生", "进行", "形成")),
        ("result", "结果", "outcome", ("结果", "现象", "表现", "产生")),
    ],
    "chemistry": [
        ("reactants", "反应物", "input", ("反应物", "原料", "物质")),
        ("products", "生成物", "outcome", ("生成物", "产物", "新物质")),
        ("condition", "条件", "condition", ("条件", "温度", "催化", "溶液")),
        ("change", "变化", "process", ("变化", "转化", "反应", "生成")),
        ("conservation", "守恒", "constraint", ("守恒", "不变", "总量")),
        ("state", "状态", "state", ("状态", "气体", "固体", "液体", "溶液")),
    ],
    "physics": [
        ("object", "对象", "entity", ("物体", "对象", "小车", "光", "力")),
        ("variable", "变量", "variable", ("变量", "速度", "距离", "时间", "质量")),
        ("direction", "方向", "direction", ("方向", "向", "角度")),
        ("magnitude", "大小", "magnitude", ("大小", "强弱", "多少", "数值")),
        ("condition", "条件", "condition", ("条件", "边界", "介质")),
        ("result", "结果", "outcome", ("结果", "现象", "成像", "运动")),
        ("law", "规律", "rule", ("规律", "定律", "关系")),
    ],
    "math": [
        ("object", "对象", "entity", ("数", "图形", "对象", "集合")),
        ("condition", "条件", "condition", ("条件", "已知", "前提")),
        ("operation", "操作", "process", ("运算", "操作", "计算", "变换")),
        ("relation", "关系", "relation", ("关系", "等于", "大于", "小于", "对应")),
        ("conclusion", "结论", "outcome", ("结论", "结果", "推出")),
        ("constraint", "约束", "constraint", ("约束", "范围", "限制", "必须")),
    ],
}


def _concept_text_pool(card: dict[str, Any], mechanism_graph: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("definition", "canonical_name"):
        if card.get(key):
            parts.append(str(card[key]))
    for key in ("core_mechanism_zh", "must_preserve_zh"):
        for item in card.get(key, []):
            if isinstance(item, str):
                parts.append(item)
    for node in mechanism_graph.get("nodes", []):
        if isinstance(node, dict) and node.get("text"):
            parts.append(str(node["text"]))
    return "。".join(parts)


def extract_concept_role_structures(
    *,
    card: dict[str, Any],
    mechanism_graph: dict[str, Any],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    text = _concept_text_pool(card, mechanism_graph)
    subject = str(card.get("subject") or "")
    rules = SUBJECT_ROLE_RULES.get(subject, [])
    roles: list[tuple[str, str, str, str]] = []
    for role_id, label, role_type, keywords in rules:
        if any(keyword in text for keyword in keywords):
            roles.append((role_id, label, role_type, next(keyword for keyword in keywords if keyword in text)))
    if not roles:
        fragments = [
            fragment.strip()
            for fragment in re.split(r"[。；;，,、]", text)
            if fragment.strip()
        ][:4]
        roles = [
            (f"role_{index:03d}", fragment[:12], "concept_fragment", fragment)
            for index, fragment in enumerate(fragments or [str(card.get("canonical_name") or "target concept")], start=1)
        ]
    structures: list[WorkspaceStructure] = []
    for index, (role_id, label, role_type, evidence) in enumerate(roles, start=1):
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:concept_role:{index:03d}",
                structure_type="ConceptRoleStructure",
                content={
                    "concept_role_id": role_id,
                    "role_label": label,
                    "role_type": role_type,
                    "source_evidence": evidence,
                },
                strength=0.7,
                salience=0.88,
                support=["concept_card.definition", "mechanism_graph.nodes"],
                created_by_codelet="ExtractConceptRolesCodelet",
                candidate_id=candidate_id,
            )
        )
    return structures


def map_concept_roles_to_source_domain_structures(
    *,
    source_domain: str,
    role_structures: list[WorkspaceStructure],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    role_ids = {str(role.content.get("concept_role_id") or "") for role in role_structures}
    has_copy_with_variation_roles = {
        "parent_generation",
        "offspring_generation",
        "shared_traits",
        "variant_traits",
    } <= role_ids
    if has_copy_with_variation_roles or source_domain in COPY_WITH_VARIATION_DOMAINS:
        story_roles_by_type = {
            "source_entity": "作为来源的母版器物",
            "target_entity": "按母版新做出的一批器物",
            "preserved_property": "保留下来的轮廓、纹样骨架和比例",
            "changed_property": "局部釉色、纹理疏密和边角细节差异",
            "condition": "开工前必须确认的母版形制",
            "process": "从母版到新件的制作过程",
            "outcome": "同出一源但各有细节差别的验收记录",
            "input": "入窑前准备好的泥坯和母版",
            "constraint": "新件必须保留的基本形制",
            "state": "新件被记录下来的细节状态",
            "entity": "被比对的新制器物",
            "variable": "每件器物局部细节的变化栏",
            "direction": "从母版到新件的来源方向",
            "magnitude": "细节差异的明显程度",
            "rule": "同出一件母版的新件可归入同一类的判断规则",
            "relation": "母版与新件之间的来源对应关系",
        }
        mapping_reason = "copy-with-variation concept role mapped to a source-domain lineage"
    else:
        story_roles_by_type = {
            "source_entity": "旧样本册中的原始记录",
            "target_entity": "新到场的待验对象",
            "preserved_property": "相同封条、编号规则和基础印记",
            "changed_property": "新增划痕、颜色深浅和局部差异",
            "condition": "入场前必须核对的条件牌",
            "process": "按顺序推进的中间流程",
            "outcome": "最终验收记录",
            "input": "入库前的原始材料",
            "constraint": "不能被破坏的登记规则",
            "state": "被记录下来的状态标签",
            "entity": "被观察和登记的对象",
            "variable": "记录册上变化的数值栏",
            "direction": "通行路线上的方向标记",
            "magnitude": "刻度牌上的大小标记",
            "rule": "众人共同遵守的判断规则",
            "relation": "两份记录之间的对应关系",
        }
        mapping_reason = "concept role mapped into the selected source domain"
    structures: list[WorkspaceStructure] = []
    for index, role in enumerate(role_structures, start=1):
        role_type = str(role.content.get("role_type") or "")
        story_role = story_roles_by_type.get(role_type, f"{source_domain}中的{role.content.get('role_label')}")
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:role_correspondence:{index:03d}",
                structure_type="RoleCorrespondence",
                content={
                    "concept_role_id": role.content.get("concept_role_id"),
                    "role_label": role.content.get("role_label"),
                    "role_type": role_type,
                    "story_role": f"{source_domain}中的{story_role}",
                    "mapping_reason": mapping_reason,
                },
                strength=0.69,
                salience=0.86,
                support=[role.structure_id, "copycat.source_domain"],
                created_by_codelet="MapConceptRolesToSourceDomainCodelet",
                candidate_id=candidate_id,
            )
        )
    return structures


def _story_relation_for_type(source_domain: str, relation: dict[str, Any]) -> tuple[str, str]:
    kg_relation = str(relation.get("kg_relation") or "relates_to")
    neighbor = str(relation.get("neighbor_name") or relation.get("target_name") or "相关记录")
    is_copy_with_variation_domain = source_domain in COPY_WITH_VARIATION_DOMAINS
    if kg_relation == "prerequisites_for":
        return (
            "prerequisite",
            f"主角先确认{source_domain}里的前置条件牌；缺少这一步，后面的登记不能开始。",
        )
    if kg_relation == "is_a":
        if is_copy_with_variation_domain:
            return (
                "category_membership",
                "主角把这些同出一件母版、又各有细节差别的新件归入同一类制作规则，而不是当成彼此无关的孤立物。",
            )
        return (
            "category_membership",
            f"主角把这个具体现象归入“{neighbor}”这类更大的共同规则，而不是当成孤立事件。",
        )
    if kg_relation == "verifies":
        return (
            "evidence_verification",
            f"主角用记录、比较和复查来检验这条判断，证据对上后才允许通过。",
        )
    if kg_relation == "leads_to":
        return (
            "causal_or_supportive_outcome",
            f"主角先稳定前一项安排，再推动后一项结果出现，前后形成因果承接。",
        )
    return (
        "association",
        f"主角把两份相关记录放在一起比较，发现它们共同约束最后判断。",
    )


def map_typed_relation_structures(
    *,
    source_domain: str,
    relation_structures: list[WorkspaceStructure],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    structures: list[WorkspaceStructure] = []
    for index, relation in enumerate(relation_structures, start=1):
        story_relation_type, story_relation = _story_relation_for_type(source_domain, relation.content)
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:relation_correspondence:{index:03d}",
                structure_type="RelationCorrespondence",
                content={
                    "source_edge_id": relation.content.get("source_edge_id"),
                    "kg_relation": relation.content.get("kg_relation"),
                    "relation_semantic_role": relation.content.get("relation_semantic_role"),
                    "story_relation_type": story_relation_type,
                    "story_relation": story_relation,
                    "source_name": relation.content.get("source_name"),
                    "target_name": relation.content.get("target_name"),
                },
                strength=0.71,
                salience=0.9,
                support=[relation.structure_id, "copycat.typed_relation_mapping"],
                created_by_codelet="MapTypedRelationCodelet",
                candidate_id=candidate_id,
            )
        )
    return structures


def propose_node_correspondence_structures(
    *,
    mechanism_graph: dict[str, Any],
    source_domain: str,
    candidate_id: str,
) -> list[WorkspaceStructure]:
    nodes = [node for node in mechanism_graph.get("nodes", []) if isinstance(node, dict)]
    structures: list[WorkspaceStructure] = []
    total = len(nodes)
    for index, node in enumerate(nodes):
        role = _node_role(index, total)
        carrier = f"{source_domain}中的{role}"
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:node_correspondence:{index + 1:03d}",
                structure_type="NodeCorrespondence",
                content={
                    "mechanism_node_id": node.get("id"),
                    "mechanism_text": node.get("text"),
                    "narrative_carrier": carrier,
                    "role": role,
                },
                strength=0.68,
                salience=0.9,
                support=["mechanism_graph.nodes"],
                created_by_codelet="ProposeNodeCorrespondenceCodelet",
                candidate_id=candidate_id,
            )
        )
    return structures


def _carrier_by_node_id(structures: list[WorkspaceStructure]) -> dict[str, str]:
    carriers: dict[str, str] = {}
    for structure in structures:
        if structure.structure_type != "NodeCorrespondence":
            continue
        node_id = structure.content.get("mechanism_node_id")
        carrier = structure.content.get("narrative_carrier")
        if node_id and carrier:
            carriers[str(node_id)] = str(carrier)
    return carriers


def propose_edge_correspondence_structures(
    *,
    mechanism_graph: dict[str, Any],
    node_structures: list[WorkspaceStructure],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    carriers = _carrier_by_node_id(node_structures)
    structures: list[WorkspaceStructure] = []
    for index, edge in enumerate([edge for edge in mechanism_graph.get("edges", []) if isinstance(edge, dict)]):
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        source_carrier = carriers.get(source, source)
        target_carrier = carriers.get(target, target)
        kg_relation = str(edge.get("kg_relation") or edge.get("relation") or "leads_to")
        if kg_relation in {"leads_to", "prerequisites_for"}:
            relation = f"先稳定{source_carrier}，再推动{target_carrier}"
        else:
            _, relation = _story_relation_for_type(
                str(source_carrier).split("中的", 1)[0],
                {
                    "kg_relation": kg_relation,
                    "neighbor_name": edge.get("target_name") or target_carrier,
                },
            )
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:edge_correspondence:{index + 1:03d}",
                structure_type="EdgeCorrespondence",
                content={
                    "mechanism_edge_id": edge.get("id"),
                    "source": source,
                    "target": target,
                    "relation": edge.get("relation"),
                    "kg_relation": kg_relation,
                    "source_edge_id": edge.get("source_edge_id"),
                    "narrative_relation": relation,
                    "event_evidence": relation,
                },
                strength=0.66,
                salience=0.92,
                support=["mechanism_graph.edges", "copycat.node_correspondences"],
                created_by_codelet="ProposeEdgeCorrespondenceCodelet",
                candidate_id=candidate_id,
            )
        )
    return structures


def build_event_chain_structures(
    *,
    source_domain: str,
    node_structures: list[WorkspaceStructure],
    edge_structures: list[WorkspaceStructure],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    structures: list[WorkspaceStructure] = [
        WorkspaceStructure(
            structure_id=f"{candidate_id}:conflict:001",
            structure_type="ConflictStructure",
            content={"conflict": f"{source_domain}里表面流程已经启动，但关键条件、顺序和结果还没有互相核对。"},
            strength=0.62,
            salience=0.62,
            support=["copycat.source_domain", "copycat.node_correspondences"],
            created_by_codelet="BuildEventChainFragmentCodelet",
            candidate_id=candidate_id,
        )
    ]
    for index, structure in enumerate(node_structures):
        carrier = structure.content.get("narrative_carrier")
        mechanism_text = structure.content.get("mechanism_text")
        if index == 0:
            event = f"主角先在{source_domain}中确认{carrier}是否成立。"
        elif index == len(node_structures) - 1:
            event = f"最后，众人用{carrier}核对整条安排是否得到可靠结果。"
        else:
            event = f"随后，{carrier}按前一步留下的条件继续推进。"
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:event_fragment:{index + 1:03d}",
                structure_type="EventChainFragment",
                content={
                    "event": event,
                    "position": index + 1,
                    "mapped_mechanism_node_id": structure.content.get("mechanism_node_id"),
                    "mapped_mechanism_text": mechanism_text,
                },
                strength=0.67,
                salience=0.75,
                support=[structure.structure_id],
                created_by_codelet="BuildEventChainFragmentCodelet",
                candidate_id=candidate_id,
            )
        )

    if edge_structures:
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:turning_point:001",
                structure_type="TurningPointStructure",
                content={"turning_point": "一次提前跳过中间承接的尝试暴露了方向和顺序不能颠倒。"},
                strength=0.63,
                salience=0.7,
                support=[edge_structures[0].structure_id],
                created_by_codelet="BuildEventChainFragmentCodelet",
                candidate_id=candidate_id,
            )
        )
    structures.append(
        WorkspaceStructure(
            structure_id=f"{candidate_id}:resolution_state:001",
            structure_type="ResolutionStructure",
            content={"resolution_state": "所有环节按条件、过程和结果重新衔接后，记录终于能够互相印证。"},
            strength=0.63,
            salience=0.68,
            support=["copycat.event_chain"],
            created_by_codelet="BuildEventChainFragmentCodelet",
            candidate_id=candidate_id,
        )
    )
    return structures


def strengthen_edge_causality_structures(
    *,
    edge_structures: list[WorkspaceStructure],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    structures: list[WorkspaceStructure] = []
    for index, edge_structure in enumerate(edge_structures):
        relation = edge_structure.content.get("narrative_relation")
        edge_id = edge_structure.content.get("mechanism_edge_id")
        kg_relation = edge_structure.content.get("kg_relation")
        if kg_relation not in {"leads_to", "prerequisites_for"}:
            continue
        if not relation:
            continue
        structures.append(
            WorkspaceStructure(
                structure_id=f"{candidate_id}:edge_causality_repair:{index + 1:03d}",
                structure_type="EventChainFragment",
                content={
                    "event": f"因此，{relation}，前后两步必须能在记录中互相承接。",
                    "position": 100 + index,
                    "mapped_mechanism_edge_id": edge_id,
                    "repair_target": "edge_causality",
                },
                strength=0.74,
                salience=0.88,
                support=[edge_structure.structure_id],
                created_by_codelet="StrengthenEdgeCausalityCodelet",
                candidate_id=candidate_id,
            )
        )
    return structures


def repair_direction_structures(
    *,
    edge_structures: list[WorkspaceStructure],
    candidate_id: str,
) -> list[WorkspaceStructure]:
    if not edge_structures:
        return []
    sequential_edges = [
        structure
        for structure in edge_structures
        if structure.content.get("kg_relation") in {"leads_to", "prerequisites_for"}
    ]
    if not sequential_edges:
        return []
    first = sequential_edges[0]
    last = sequential_edges[-1]
    first_relation = first.content.get("narrative_relation") or "起始环节先成立"
    last_relation = last.content.get("narrative_relation") or "结果环节随后出现"
    return [
        WorkspaceStructure(
            structure_id=f"{candidate_id}:direction_repair:001",
            structure_type="EventChainFragment",
            content={
                "event": f"有人试着倒过来安排，却发现只有{first_relation}，后面的验收才可能接上{last_relation}。",
                "position": 200,
                "repair_target": "direction_preservation",
            },
            strength=0.72,
            salience=0.84,
            support=[first.structure_id, last.structure_id],
            created_by_codelet="RepairDirectionCodelet",
            candidate_id=candidate_id,
        )
    ]


def build_copycat_structures(
    *,
    card: dict[str, Any],
    mechanism_graph: dict[str, Any],
    concept_relation_graph: dict[str, Any] | None = None,
    candidate_id: str,
    candidate_index: int,
    max_steps: int = 30,
) -> tuple[list[WorkspaceStructure], list[dict[str, Any]]]:
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    structures: list[WorkspaceStructure] = []
    trace: list[dict[str, Any]] = []
    pending = seed_structure_coderack(candidate_id)
    temperature = 72.0
    source_domain = ""
    source_structure: WorkspaceStructure | None = None
    relation_structures: list[WorkspaceStructure] = []
    role_structures: list[WorkspaceStructure] = []
    role_correspondences: list[WorkspaceStructure] = []
    relation_correspondences: list[WorkspaceStructure] = []
    node_structures: list[WorkspaceStructure] = []
    edge_structures: list[WorkspaceStructure] = []
    step = 0

    while pending and step < max_steps:
        step += 1
        selected = select_coderack_item(pending, temperature)
        pending = [item for item in pending if item.get("item_id") != selected.get("item_id")]
        codelet_type = str(selected.get("codelet_type") or "")
        temperature_before = temperature
        added: list[WorkspaceStructure] = []
        confidence = 0.7
        notes: list[str] = []

        if codelet_type == "BootstrapTargetConceptCodelet":
            target_structure = bootstrap_target_concept_structure(
                card=card,
                candidate_id=candidate_id,
            )
            added = [target_structure]
            confidence = 0.9
            notes = [f"target_concept={target_structure.content.get('name')}"]
            temperature = max(20.0, temperature - 6.0)
        elif codelet_type == "ProposeSourceDomainCodelet":
            source_structure = propose_source_domain_structure(
                card=card,
                candidate_id=candidate_id,
                candidate_index=candidate_index,
            )
            source_domain = str(source_structure.content["source_domain"])
            added = [source_structure]
            confidence = 0.82
            notes = [f"source_domain={source_domain}"]
            temperature = max(20.0, temperature - 8.0)
        elif codelet_type == "BuildConceptRelationStructuresCodelet":
            relation_structures = build_concept_relation_structures(
                concept_relation_graph=concept_relation_graph or {},
                mechanism_graph=mechanism_graph,
                candidate_id=candidate_id,
            )
            added = relation_structures
            confidence = 0.82
            notes = [f"concept_relation_count={len(relation_structures)}"]
            temperature = max(20.0, temperature - 10.0)
        elif codelet_type == "ExtractConceptRolesCodelet":
            role_structures = extract_concept_role_structures(
                card=card,
                mechanism_graph=mechanism_graph,
                candidate_id=candidate_id,
            )
            added = role_structures
            confidence = 0.8
            notes = [f"concept_role_count={len(role_structures)}"]
            temperature = max(20.0, temperature - 10.0)
        elif codelet_type == "MapConceptRolesToSourceDomainCodelet":
            if not source_domain:
                source_domain = _domain_for(card, candidate_index)
            role_correspondences = map_concept_roles_to_source_domain_structures(
                source_domain=source_domain,
                role_structures=role_structures,
                candidate_id=candidate_id,
            )
            added = role_correspondences
            confidence = 0.78
            notes = [f"role_correspondence_count={len(role_correspondences)}"]
            temperature = max(20.0, temperature - 9.0)
        elif codelet_type == "MapTypedRelationCodelet":
            if not source_domain:
                source_domain = _domain_for(card, candidate_index)
            relation_correspondences = map_typed_relation_structures(
                source_domain=source_domain,
                relation_structures=relation_structures,
                candidate_id=candidate_id,
            )
            added = relation_correspondences
            confidence = 0.8
            notes = [f"relation_correspondence_count={len(relation_correspondences)}"]
            temperature = max(20.0, temperature - 11.0)
        elif codelet_type == "ProposeNodeCorrespondenceCodelet":
            if not source_domain and source_structure is not None:
                source_domain = str(source_structure.content.get("source_domain") or "")
            if not source_domain:
                source_domain = _domain_for(card, candidate_index)
            node_structures = propose_node_correspondence_structures(
                mechanism_graph=mechanism_graph,
                source_domain=source_domain,
                candidate_id=candidate_id,
            )
            added = node_structures
            confidence = 0.78
            notes = [f"node_count={len(node_structures)}"]
            temperature = max(20.0, temperature - 12.0)
        elif codelet_type == "ProposeEdgeCorrespondenceCodelet":
            edge_structures = propose_edge_correspondence_structures(
                mechanism_graph=mechanism_graph,
                node_structures=node_structures,
                candidate_id=candidate_id,
            )
            added = edge_structures
            confidence = 0.76
            notes = [f"edge_count={len(edge_structures)}"]
            temperature = max(20.0, temperature - 14.0)
        elif codelet_type == "BuildEventChainFragmentCodelet":
            if not source_domain:
                source_domain = _domain_for(card, candidate_index)
            added = build_event_chain_structures(
                source_domain=source_domain,
                node_structures=node_structures,
                edge_structures=edge_structures,
                candidate_id=candidate_id,
            )
            confidence = 0.74
            notes = [f"fragment_count={len(added)}"]
            temperature = max(20.0, temperature - 10.0)
        elif codelet_type == "StrengthenEdgeCausalityCodelet":
            added = strengthen_edge_causality_structures(
                edge_structures=edge_structures,
                candidate_id=candidate_id,
            )
            confidence = 0.8
            notes = [f"edge_causality_repairs={len(added)}"]
            temperature = max(20.0, temperature - 9.0)
        elif codelet_type == "RepairDirectionCodelet":
            added = repair_direction_structures(
                edge_structures=edge_structures,
                candidate_id=candidate_id,
            )
            confidence = 0.77
            notes = [f"direction_repairs={len(added)}"]
            temperature = max(20.0, temperature - 7.0)
        else:
            notes = [f"unsupported_codelet={codelet_type}"]

        structures.extend(added)
        result = CodeletResult(
            codelet_name=codelet_type,
            target_candidate_id=candidate_id,
            structures_added=[structure.to_dict() for structure in added],
            temperature_before=temperature_before,
            temperature_after=temperature,
            confidence=confidence,
            notes=notes,
        ).to_dict()
        result["step"] = step
        result["coderack_item"] = selected
        trace.append(result)
        pending.extend(
            followup_structure_items(
                candidate_id=candidate_id,
                completed_codelet=codelet_type,
                step=step,
            )
        )
    return structures, trace
