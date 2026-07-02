from __future__ import annotations

import json

from kg_rag.evaluation.parser import strip_alignment_from_story
from kg_rag.evaluation.rubric import DIMENSION_NAMES_ZH, EvaluationInput, WEIGHTS


SYSTEM_PROMPT = "You are a strict evaluator of concept-grounded educational fables. Return JSON only."


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

