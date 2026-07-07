from __future__ import annotations

import json

from kg_rag.concepts.cards import infer_concept_type
from kg_rag.concepts.prompts import _clean_event_text
from kg_rag.concepts.quality import generation_priority, text_quality


def test_text_quality_accepts_chinese_definition() -> None:
    quality = text_quality(
        name="\u751f\u7269",
        definition="\u5177\u6709\u5171\u540c\u751f\u547d\u7279\u5f81\u7684\u7269\u4f53\u3002",
    )

    assert quality == "good"


def test_generation_priority_marks_good_connected_concept_as_gold() -> None:
    priority = generation_priority(quality="good", has_definition=True, degree=4)

    assert priority == "gold"


def test_generation_priority_marks_broken_missing_as_repair() -> None:
    priority = generation_priority(quality="broken", has_definition=False, degree=5)

    assert priority == "repair"


def test_math_formula_like_concept_type_is_theorem() -> None:
    concept_type = infer_concept_type(
        "math",
        "\u52fe\u80a1\u5b9a\u7406",
        "\u76f4\u89d2\u4e09\u89d2\u5f62\u4e09\u8fb9\u5173\u7cfb\u7684\u5b9a\u7406\u3002",
    )

    assert concept_type == "theorem"


def test_json_line_can_keep_chinese_runtime_values() -> None:
    payload = {"story_language": "zh-CN", "canonical_name": "\u751f\u7269"}
    encoded = json.dumps(payload, ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["canonical_name"] == "\u751f\u7269"


def test_local_story_event_text_masks_meta_language() -> None:
    cleaned = _clean_event_text("\u7528\u6545\u4e8b\u4e8b\u4ef6\u9690\u542b\u8868\u8fbe\uff1a\u8fd9\u662f\u4e00\u4e2a\u6982\u5ff5\u7684\u5b9a\u4e49\u548c\u673a\u5236")

    assert "\u6982\u5ff5" not in cleaned
    assert "\u5b9a\u4e49" not in cleaned
    assert "\u673a\u5236" not in cleaned
