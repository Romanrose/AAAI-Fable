from __future__ import annotations

import json

from kg_rag.evaluation.parser import strip_alignment_from_story
from kg_rag.evaluation.rubric import DIMENSION_NAMES_ZH, EvaluationInput, WEIGHTS


SYSTEM_PROMPT = """You are a strict evaluator of concept-grounded educational fables.
Evaluate whether the generated fable teaches the target concept faithfully, implicitly, and pedagogically.

General judging principles:
- Judge the story body, structure plan, graph context, and alignment table together.
- Do not reward fluent writing if the target concept mechanism is wrong, incomplete, or unmapped.
- Do not reward a story that directly reveals the target concept name, aliases, or forbidden terms.
- A high score in readability or novelty must never compensate for low faithfulness or low mapping clarity.
- Prefer conservative scores when evidence is missing from the story or alignment table.
- Return valid JSON only. Do not include markdown, prose outside JSON, or code fences."""


DIMENSION_RUBRICS = {
    "faithfulness": {
        "name_zh": "忠实度",
        "core_question": "故事是否准确保留目标概念的核心机制、必要条件、因果关系和学科约束。",
        "evidence_to_check": [
            "concept_definition",
            "subgraph_pack_summary.seed",
            "subgraph_pack_summary.sections",
            "structure_plan.event_chain",
            "structure_plan.alignment_plan",
            "alignment_table",
            "story_body_to_evaluate_for_leakage",
        ],
        "score_5": "核心机制完整、因果链正确、没有概念误导；故事中的关键事件能支持概念定义和 KG 上下文。",
        "score_4": "核心机制基本正确，仅有轻微遗漏或表述不够精确，但不会误导学习者。",
        "score_3": "故事与概念相关，但只覆盖部分机制；存在明显简化，教学时需要补充解释。",
        "score_2": "机制覆盖很弱，重要条件或因果关系缺失；读者可能学到片面的理解。",
        "score_1": "故事传达的机制与目标概念冲突，或几乎没有表达目标概念。",
        "hard_downgrade_rules": [
            "If the story contradicts the concept definition, set concept_contradiction=true and faithfulness<=2.",
            "If the main concept mechanism cannot be recovered from story events, set unmapped_core_mechanism=true and faithfulness<=3.",
            "If the story only gives a moral lesson without the target mechanism, faithfulness<=2.",
        ],
    },
    "implicitness": {
        "name_zh": "隐含性",
        "core_question": "故事正文和标题是否避免直接暴露目标概念名、别名、禁用词或过强术语线索。",
        "evidence_to_check": [
            "forbidden_terms_for_story_body",
            "story_body_to_evaluate_for_leakage",
            "rule_findings.leaked_terms",
            "rule_findings.title_leaks",
            "rule_findings.soft_leakage_terms",
        ],
        "score_5": "正文和标题不出现目标概念名、别名、禁用词或明显术语；概念只通过情节结构隐含表达。",
        "score_4": "没有硬泄露，但存在少量较弱的学科线索；仍需要通过故事推理才能猜到概念。",
        "score_3": "没有直接写出概念名，但出现'概念/机制/定义/术语'等解释性词，隐含性一般。",
        "score_2": "出现接近目标概念的强提示、别名变体或过于直白的解释，学习者几乎无需推理。",
        "score_1": "正文或标题直接出现目标概念名、别名、禁用词，或直接说明'这个故事解释的是 X'。",
        "hard_downgrade_rules": [
            "If hard_leakage or title_leakage is true, implicitness=1.",
            "If soft_leakage is true but no hard leakage appears, implicitness<=3.",
            "Do not penalize target terms that appear only inside the JSON alignment metadata, unless they appear in the story body or title.",
        ],
    },
    "mapping_clarity": {
        "name_zh": "映射清晰度",
        "core_question": "目标概念中的实体、条件、关系、过程和结果是否能稳定映射到故事角色、物件、冲突、行动和结局。",
        "evidence_to_check": [
            "structure_plan",
            "alignment_table",
            "rule_findings.alignment_roles_present",
            "rule_findings.missing_alignment_roles",
        ],
        "score_5": "alignment_table 明确覆盖目标概念、核心机制、前置条件、相关概念、结果/应用和验证环节；故事证据具体可定位。",
        "score_4": "映射覆盖核心机制和主要因果链，但部分辅助角色或验证环节略简略。",
        "score_3": "能看出大致类比关系，但映射表或故事证据较泛；部分重要关系需要读者自行补齐。",
        "score_2": "只有零散角色或表层相似，核心机制和故事事件之间缺少稳定对应。",
        "score_1": "没有有效 alignment table，或故事与概念结构无法建立对应。",
        "hard_downgrade_rules": [
            "If alignment_table is empty or only contains vague generic evidence, mapping_clarity<=2.",
            "If target concept and core mechanism roles are both missing, set unmapped_core_mechanism=true.",
            "If the mapping relies on post-hoc explanation not present in the story, mapping_clarity<=3.",
        ],
    },
    "readability": {
        "name_zh": "可读性",
        "core_question": "故事是否是自然、连贯、适合目标年级的中文短寓言。",
        "evidence_to_check": [
            "story_body_to_evaluate_for_leakage",
            "rule_findings.story_token_count",
            "grade",
            "subject",
        ],
        "score_5": "中文自然流畅，叙事有起承转合，长度适中，目标年级学习者无需额外解释即可读懂故事情节。",
        "score_4": "整体通顺，少量句子生硬或信息密度略高，但不影响阅读。",
        "score_3": "基本可读，但情节跳跃、重复、过短或过长；需要教师辅助理解。",
        "score_2": "语言明显机械，故事结构不完整，或大量堆砌抽象说明。",
        "score_1": "文本不连贯、难以读懂、不是故事，或语言不符合要求。",
        "hard_downgrade_rules": [
            "If the story is mostly exposition rather than narrative, readability<=3.",
            "If the story is too short to form a complete conflict-resolution arc, readability<=2.",
            "Do not give readability>3 when the text is fluent but not age-appropriate.",
        ],
    },
    "pedagogical_value": {
        "name_zh": "教学价值",
        "core_question": "故事是否能帮助学习者理解、记忆、解释或迁移目标概念。",
        "evidence_to_check": [
            "concept_definition",
            "subgraph_pack_summary.sections.prerequisites",
            "subgraph_pack_summary.sections.outcomes",
            "structure_plan.resolution_state",
            "alignment_table",
            "story_body_to_evaluate_for_leakage",
        ],
        "score_5": "故事能自然引导学习者形成正确机制理解，并支持事后回映射、课堂提问或迁移应用。",
        "score_4": "有明确教学帮助，能辅助理解核心机制，但迁移或诊断误区的能力略弱。",
        "score_3": "有启发性，但主要停留在记忆或兴趣层面；概念理解仍需教师补充。",
        "score_2": "教学作用弱，故事好看但不能稳定帮助理解目标概念。",
        "score_1": "可能造成误解，或完全没有教育价值。",
        "hard_downgrade_rules": [
            "If faithfulness<=2, pedagogical_value<=2.",
            "If mapping_clarity<=2, pedagogical_value<=2.",
            "If the story cannot support a follow-up question about the target mechanism, pedagogical_value<=3.",
        ],
    },
    "novelty": {
        "name_zh": "新颖性",
        "core_question": "故事是否避免常见寓言模板、同质化场景、套话结尾和同批次高度相似情节。",
        "evidence_to_check": [
            "story_body_to_evaluate_for_leakage",
            "rule_findings.template_hits",
            "rule_findings.template_similarity",
        ],
        "score_5": "场景、角色、冲突和解决方式具体且少见；没有明显模板句式，同批故事中区分度高。",
        "score_4": "有一定新意，虽包含常见叙事结构，但关键设定和冲突较具体。",
        "score_3": "可接受但普通；存在常见寓言套路或较泛化的场景。",
        "score_2": "明显模板化，使用常见套话、相似角色或同批故事高度相似。",
        "score_1": "几乎是通用模板替换概念，缺乏任何具体创意。",
        "hard_downgrade_rules": [
            "If template_like is true, novelty<=2.",
            "If template_similarity>=0.82, novelty<=2.",
            "If the story uses generic wise elder/village/everyone understood style closure, novelty<=3.",
        ],
    },
}


def build_six_dim_eval_prompt(evaluation_input: EvaluationInput, rule_findings: dict | None = None) -> str:
    story_body = strip_alignment_from_story(evaluation_input.draft_story)
    payload = {
        "task": "Evaluate one concept-grounded fable on six dimensions. Return strict JSON only.",
        "target_concept": evaluation_input.target_concept,
        "concept_id": evaluation_input.concept_id,
        "concept_definition": evaluation_input.concept_definition,
        "forbidden_terms_for_story_body": evaluation_input.forbidden_terms,
        "subgraph_pack_summary": {
            "seed": evaluation_input.subgraph_pack.get("seed"),
            "sections": evaluation_input.subgraph_pack.get("sections"),
            "meta": evaluation_input.subgraph_pack.get("meta"),
        },
        "structure_plan": evaluation_input.structure_plan,
        "alignment_table": evaluation_input.alignment_table,
        "story_body_to_evaluate_for_leakage": story_body,
        "rule_findings": rule_findings or {},
        "dimensions": DIMENSION_NAMES_ZH,
        "dimension_rubrics": DIMENSION_RUBRICS,
        "weights": WEIGHTS,
        "required_output_schema": {
            "scores": {
                "faithfulness": "integer 1-5",
                "implicitness": "integer 1-5",
                "mapping_clarity": "integer 1-5",
                "readability": "integer 1-5",
                "pedagogical_value": "integer 1-5",
                "novelty": "integer 1-5",
            },
            "hard_flags": {
                "hard_leakage": "boolean",
                "soft_leakage": "boolean",
                "title_leakage": "boolean",
                "concept_contradiction": "boolean",
                "unmapped_core_mechanism": "boolean",
                "template_like": "boolean",
            },
            "rationales": {
                "faithfulness": "1-3 sentences",
                "implicitness": "1-3 sentences",
                "mapping_clarity": "1-3 sentences",
                "readability": "1-3 sentences",
                "pedagogical_value": "1-3 sentences",
                "novelty": "1-3 sentences",
            },
            "revision_suggestions": ["short actionable suggestions"],
        },
        "scoring_rules": [
            "The story body must not directly expose the target concept name or aliases.",
            "Do not let high readability compensate for a wrong or unmapped concept mechanism.",
            "Set concept_contradiction=true when the story teaches a mechanism that conflicts with the concept definition.",
            "Set unmapped_core_mechanism=true when story elements cannot recover the main concept mechanism.",
            "Use 1 as unacceptable, 3 as acceptable but weak, and 5 as excellent.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
