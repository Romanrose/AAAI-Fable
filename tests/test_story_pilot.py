from __future__ import annotations

import json
from pathlib import Path

from kg_rag.story_pilot.metrics import evaluate_alignment
from kg_rag.story_pilot.reviews import append_story_review, latest_story_reviews
from kg_rag.story_pilot.selection import PILOT12_IDS, subject_counts


def test_pilot_has_three_concepts_per_subject() -> None:
    assert len(PILOT12_IDS) == 12
    assert subject_counts() == {"biology": 3, "chemistry": 3, "math": 3, "physics": 3}


def test_alignment_metrics_require_exact_story_evidence_and_direction() -> None:
    graph = {
        "nodes": [{"id": "n1"}, {"id": "n2"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2", "relation": "requires"}],
    }
    story = "守门人先检查通行牌，确认无误后才打开仓门。"
    alignment = {
        "node_alignments": [
            {"mechanism_node_id": "n1", "story_evidence": "守门人"},
            {"mechanism_node_id": "n2", "story_evidence": "不存在的证据"},
        ],
        "edge_alignments": [
            {"mechanism_edge_id": "e1", "story_evidence": "确认无误后才打开仓门", "direction_preserved": True}
        ],
    }

    metrics = evaluate_alignment(
        mechanism_graph=graph,
        alignment=alignment,
        story=story,
        forbidden_terms=["目标概念"],
    )

    assert metrics["node_coverage"] == 0.5
    assert metrics["edge_coverage"] == 1.0
    assert metrics["direction_accuracy"] == 1.0
    assert metrics["exact_evidence_precision"] == 0.6667


def test_story_reviews_are_candidate_specific_and_preferred_is_unique(tmp_path: Path) -> None:
    pilot_root = tmp_path / "pilot"
    concept_id = PILOT12_IDS[0]
    for candidate_id in ("candidate_001", "candidate_002"):
        output_dir = pilot_root / "stories" / concept_id / "standard" / candidate_id
        output_dir.mkdir(parents=True)
        (output_dir / "final_status.json").write_text("{}", encoding="utf-8")
    statuses = [
        {"concept_id": concept_id, "strategy": "standard", "candidate_id": candidate_id}
        for candidate_id in ("candidate_001", "candidate_002")
    ]
    (pilot_root / "final_story_status.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in statuses),
        encoding="utf-8",
    )

    append_story_review(
        pilot_root=pilot_root,
        concept_id=concept_id,
        strategy="standard",
        candidate_id="candidate_001",
        decision="approve",
        reviewer="reviewer",
        preferred=True,
    )
    result = append_story_review(
        pilot_root=pilot_root,
        concept_id=concept_id,
        strategy="standard",
        candidate_id="candidate_002",
        decision="approve",
        reviewer="reviewer",
        preferred=True,
    )

    latest = latest_story_reviews(pilot_root / "story_reviews.jsonl")
    assert latest[(concept_id, "standard", "candidate_001")]["preferred"] is False
    assert latest[(concept_id, "standard", "candidate_002")]["preferred"] is True
    assert result == {
        "story_count": 2,
        "reviewed_count": 2,
        "pending_count": 0,
        "approved_count": 2,
        "rejected_count": 0,
        "preferred_count": 1,
    }
