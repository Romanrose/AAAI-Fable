from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kg_rag.multi_agent.agents import ArbiterAgent


@dataclass(frozen=True)
class DecisionConfig:
    min_node_coverage: float = 0.6
    min_edge_coverage: float = 0.5
    min_alignment_precision: float = 0.7


def candidate_score(metrics: dict[str, Any]) -> float:
    direction = metrics.get("relation_direction_accuracy")
    direction_value = 1.0 if direction is None else float(direction)
    leakage_penalty = 1.0 if metrics.get("exact_concept_leakage") else 0.0
    soft_penalty = 0.4 if metrics.get("soft_term_leakage") else 0.0
    return round(
        0.30 * float(metrics.get("weighted_node_coverage") or 0.0)
        + 0.25 * float(metrics.get("weighted_edge_coverage") or 0.0)
        + 0.20 * float(metrics.get("alignment_precision") or 0.0)
        + 0.15 * direction_value
        + 0.10 * (1.0 - float(metrics.get("template_hit_rate") or 0.0))
        - leakage_penalty
        - soft_penalty,
        4,
    )


def revision_reason(metrics: dict[str, Any], config: DecisionConfig | None = None) -> str | None:
    config = config or DecisionConfig()
    if metrics.get("exact_concept_leakage") or metrics.get("soft_term_leakage"):
        return "正文出现目标概念名、别名或强术语，需要只重写正文并移除泄露。"
    if float(metrics.get("weighted_node_coverage") or 0.0) < config.min_node_coverage:
        return "故事没有覆盖足够的机制节点，需要补充缺失机制事件。"
    if float(metrics.get("weighted_edge_coverage") or 0.0) < config.min_edge_coverage:
        return "故事没有覆盖足够的机制关系，需要加强事件之间的因果或顺序承接。"
    if float(metrics.get("alignment_precision") or 0.0) < config.min_alignment_precision:
        return "对齐证据不稳定，需要让正文提供更明确的可引用事件。"
    direction = metrics.get("relation_direction_accuracy")
    if direction is not None and float(direction) < 0.75:
        return "故事事件方向与机制边方向不一致，需要调整事件顺序。"
    return None


class DecisionEngine:
    def __init__(self, arbiter: ArbiterAgent | None = None, config: DecisionConfig | None = None):
        self.arbiter = arbiter
        self.config = config or DecisionConfig()

    def choose(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            raise ValueError("DecisionEngine requires at least one candidate")

        ranked = sorted(
            [
                {
                    "candidate_id": candidate["candidate_id"],
                    "score": candidate_score(candidate["automatic_metrics"]),
                    "revision_reason": revision_reason(candidate["automatic_metrics"], self.config),
                }
                for candidate in candidates
            ],
            key=lambda item: (item["revision_reason"] is not None, -item["score"], item["candidate_id"]),
        )
        deterministic_winner = ranked[0]["candidate_id"]
        eligible = [
            candidate
            for candidate in candidates
            if next(item for item in ranked if item["candidate_id"] == candidate["candidate_id"])["revision_reason"] is None
        ]
        arbiter_payload = None
        winner = deterministic_winner
        if self.arbiter and len(eligible) >= 2:
            arbiter_payload = self.arbiter.choose(
                candidates=eligible,
                deterministic_winner=deterministic_winner,
            )
            winner = arbiter_payload["winner_candidate_id"]

        selected = next(candidate for candidate in candidates if candidate["candidate_id"] == winner)
        selected_rank = next(item for item in ranked if item["candidate_id"] == winner)
        return {
            "winner_candidate_id": winner,
            "deterministic_winner_candidate_id": deterministic_winner,
            "ranked_candidates": ranked,
            "arbiter": arbiter_payload,
            "revision_reason": selected_rank["revision_reason"],
            "selected_score": selected_rank["score"],
            "selected_candidate": selected,
        }
