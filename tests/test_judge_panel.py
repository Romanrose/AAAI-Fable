from __future__ import annotations

from kg_rag.evaluation.pipeline import _aggregate_judge_payloads


def test_judge_panel_uses_median_scores_and_majority_flags() -> None:
    payloads = [
        {
            "scores": {
                "faithfulness": 5,
                "implicitness": 5,
                "mapping_clarity": 4,
                "readability": 4,
                "pedagogical_value": 5,
                "novelty": 2,
            },
            "hard_flags": {"template_like": True, "hard_leakage": False},
            "rationales": {"faithfulness": "strong"},
            "revision_suggestions": ["make the plot less templated"],
        },
        {
            "scores": {
                "faithfulness": 4,
                "implicitness": 5,
                "mapping_clarity": 4,
                "readability": 5,
                "pedagogical_value": 4,
                "novelty": 3,
            },
            "hard_flags": {"template_like": True, "hard_leakage": False},
        },
        {
            "scores": {
                "faithfulness": 2,
                "implicitness": 1,
                "mapping_clarity": 2,
                "readability": 3,
                "pedagogical_value": 2,
                "novelty": 1,
            },
            "hard_flags": {"template_like": False, "hard_leakage": True},
        },
    ]

    scores, flags, rationales, suggestions, aggregation = _aggregate_judge_payloads(
        judge_payloads=payloads,
        rule_scores={
            "faithfulness": 4,
            "implicitness": 4,
            "mapping_clarity": 4,
            "readability": 4,
            "pedagogical_value": 4,
            "novelty": 4,
        },
        rule_flags={
            "hard_leakage": False,
            "soft_leakage": False,
            "title_leakage": False,
            "concept_contradiction": False,
            "unmapped_core_mechanism": False,
            "template_like": False,
        },
        rule_rationales={},
        rule_suggestions=[],
    )

    assert scores["faithfulness"] == 4
    assert scores["implicitness"] == 5
    assert scores["mapping_clarity"] == 4
    assert flags["template_like"] is True
    assert flags["hard_leakage"] is False
    assert "faithfulness" in rationales
    assert suggestions == ["make the plot less templated"]
    assert aggregation["judge_count"] == 3
