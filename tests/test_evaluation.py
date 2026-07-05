from __future__ import annotations

import json
from pathlib import Path

from kg_rag.evaluation.report import verify_eval_run
from kg_rag.evaluation.rubric import EvaluationInput, decide_status
from kg_rag.evaluation.rules import evaluate_rules


PHOTOSYNTHESIS_ZH = "\u5149\u5408\u4f5c\u7528"
TRANSPIRATION_ZH = "\u84b8\u817e\u4f5c\u7528"


def _eval_input(story: str, concept: str = PHOTOSYNTHESIS_ZH) -> EvaluationInput:
    return EvaluationInput(
        concept_id="c1",
        target_concept=concept,
        concept_definition="\u690d\u7269\u5229\u7528\u5149\u80fd\u5408\u6210\u6709\u673a\u7269\u5e76\u91ca\u653e\u6c27\u6c14\u3002",
        subgraph_pack={
            "seed": {
                "id": "c1",
                "name": concept,
                "definition": "\u690d\u7269\u5229\u7528\u5149\u80fd\u5408\u6210\u6709\u673a\u7269\u5e76\u91ca\u653e\u6c27\u6c14\u3002",
            }
        },
        structure_plan={"alignment_plan": []},
        draft_story=story,
        alignment_table=[
            {"concept_role": "target concept", "story_evidence": "workshop"},
            {"concept_role": "prerequisites", "story_evidence": "light and water"},
            {"concept_role": "related concepts", "story_evidence": "neighbors"},
            {"concept_role": "outcomes", "story_evidence": "stored food"},
            {"concept_role": "experiments", "story_evidence": "covered leaf"},
            {"concept_role": "exercises", "story_evidence": "follow-up check"},
        ],
        forbidden_terms=[concept, "photosynthesis"],
    )


def test_hard_leakage_forces_low_implicitness() -> None:
    story = "\u8fd9\u4e2a\u6545\u4e8b\u76f4\u63a5\u89e3\u91ca\u5149\u5408\u4f5c\u7528\u3002"
    scores, flags, _, _, findings = evaluate_rules(_eval_input(story))

    assert flags["hard_leakage"] is True
    assert scores["implicitness"] == 1
    assert PHOTOSYNTHESIS_ZH in findings["leaked_terms"]


def test_missing_mapping_rejects_by_status_rule() -> None:
    scores, flags, _, _, _ = evaluate_rules(
        EvaluationInput(
            concept_id="c1",
            target_concept=TRANSPIRATION_ZH,
            concept_definition="\u6c34\u5206\u4ee5\u6c14\u4f53\u5f62\u5f0f\u4ece\u690d\u7269\u4f53\u5185\u6563\u5931\u3002",
            subgraph_pack={},
            structure_plan={},
            draft_story="A polished story without any mapping table.",
            alignment_table=[],
            forbidden_terms=[TRANSPIRATION_ZH],
        )
    )

    assert flags["unmapped_core_mechanism"] is True
    assert scores["mapping_clarity"] <= 2
    assert decide_status(scores, flags) == "reject"


def test_template_similarity_marks_template_like() -> None:
    story = "In a village, everyone understood the lesson from that day on."
    scores, flags, _, _, findings = evaluate_rules(_eval_input(story), peer_stories=[story])

    assert flags["template_like"] is True
    assert scores["novelty"] <= 2
    assert findings["template_similarity"] >= 0.82


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_verify_eval_run_accepts_complete_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    concept_dir = run_dir / "concepts" / "c1"
    concept_dir.mkdir(parents=True)
    row = {
        "concept_id": "c1",
        "status": "success",
        "scores": {
            "faithfulness": 4,
            "implicitness": 5,
            "mapping_clarity": 4,
            "readability": 4,
            "pedagogical_value": 4,
            "novelty": 4,
        },
        "hard_flags": {},
        "weighted_overall": 4.15,
        "final_status": "accept",
    }
    _write_jsonl(run_dir / "summary.jsonl", [row])
    _write_jsonl(run_dir / "eval_summary.jsonl", [row])
    for filename in ("eval_summary.csv", "eval_report.md", "eval_analysis.svg"):
        (run_dir / filename).write_text("ok", encoding="utf-8")
    for filename in (
        "concept_card.json",
        "subgraph_pack.json",
        "structure_plan.json",
        "story_prompt.txt",
        "draft_story.txt",
        "six_dim_eval.json",
        "status.json",
    ):
        (concept_dir / filename).write_text("{}", encoding="utf-8")

    result = verify_eval_run(run_dir, expected_count=1)

    assert result["ok"] is True
    assert result["eval_count"] == 1
    assert result["missing_files"] == []
