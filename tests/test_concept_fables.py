from __future__ import annotations

from kg_rag.concepts.prompts import build_chinese_structure_plan, build_local_chinese_story
from kg_rag.concepts.quality import chinese_char_ratio


def test_local_chinese_story_avoids_target_name_in_body() -> None:
    card = {
        "concept_id": "biology_test_cpt1",
        "subject": "biology",
        "canonical_name": "\u751f\u7269",
        "definition": "\u5177\u6709\u5171\u540c\u751f\u547d\u7279\u5f81\u7684\u7269\u4f53\u3002",
        "aliases": ["\u751f\u547d\u4f53"],
        "examples": [],
        "core_mechanism_zh": ["\u9700\u8981\u8425\u517b", "\u80fd\u591f\u751f\u957f\u548c\u7e41\u6b96"],
        "must_preserve_zh": [],
        "subject_constraints_zh": [],
        "forbidden_terms_zh": ["\u751f\u7269", "\u751f\u547d\u4f53"],
    }
    plan = build_chinese_structure_plan(card)
    story = build_local_chinese_story(card, plan)
    body = story.split("```json", 1)[0]

    assert "\u751f\u7269" not in body
    assert chinese_char_ratio(story) >= 0.8
    assert plan["story_language"] == "zh-CN"

