from __future__ import annotations

from typing import Any

from kg_rag.copycat.workspace import build_candidate_state


def _revision_reason(metrics: dict[str, Any]) -> str | None:
    if metrics.get("exact_concept_leakage") or metrics.get("soft_term_leakage"):
        return "正文出现目标概念名、别名或强术语，需要只重写正文并移除泄露。"
    if float(metrics.get("weighted_node_coverage") or 0.0) < 0.6:
        return "故事没有覆盖足够的机制节点，需要补充缺失机制事件。"
    if float(metrics.get("weighted_edge_coverage") or 0.0) < 0.5:
        return "故事没有覆盖足够的机制关系，需要加强事件之间的因果或顺序承接。"
    if float(metrics.get("alignment_precision") or 0.0) < 0.7:
        return "对齐证据不稳定，需要让正文提供更明确的可引用事件。"
    direction = metrics.get("relation_direction_accuracy")
    if direction is not None and float(direction) < 0.75:
        return "故事事件方向与机制边方向不一致，需要调整事件顺序。"
    return None


def _hard_copycat_failure(state: dict[str, Any]) -> bool:
    failures = set(state.get("failure_summary", []))
    return bool({"failure.leakage", "failure.direction_error"} & failures)


def choose_copycat_candidate(
    *,
    candidates: list[dict[str, Any]],
    mechanism_graph: dict[str, Any],
    temperature_threshold: float = 35.0,
) -> dict[str, Any]:
    if not candidates:
        raise ValueError("choose_copycat_candidate requires at least one candidate")

    states = [
        build_candidate_state(candidate=candidate, mechanism_graph=mechanism_graph).to_dict()
        for candidate in candidates
    ]
    ranked = sorted(
        [
            {
                "candidate_id": state["candidate_id"],
                "copycat_score": state["copycat_score"],
                "temperature": state["temperature"],
                "temperature_band": state["temperature_band"],
                "failure_summary": state["failure_summary"],
                "hard_copycat_failure": _hard_copycat_failure(state),
                "within_temperature_threshold": float(state["temperature"]) <= temperature_threshold,
            }
            for state in states
        ],
        key=lambda item: (
            item["hard_copycat_failure"],
            not item["within_temperature_threshold"],
            float(item["temperature"]),
            -float(item["copycat_score"]),
            str(item["candidate_id"]),
        ),
    )
    winner = str(ranked[0]["candidate_id"])
    selected = next(candidate for candidate in candidates if candidate["candidate_id"] == winner)
    reason = _revision_reason(selected["automatic_metrics"])
    if reason is None and not ranked[0]["within_temperature_threshold"]:
        reason = (
            f"Copycat 工作区温度 {ranked[0]['temperature']:.2f} 高于配置阈值 "
            f"{temperature_threshold:.2f}，需要继续降低结构不稳定性。"
        )
    return {
        "winner_candidate_id": winner,
        "deterministic_winner_candidate_id": winner,
        "ranked_candidates": ranked,
        "arbiter": None,
        "revision_reason": reason,
        "selected_score": ranked[0]["copycat_score"],
        "selected_temperature": ranked[0]["temperature"],
        "temperature_threshold": temperature_threshold,
        "selected_within_temperature_threshold": ranked[0]["within_temperature_threshold"],
        "selection_mode": "copycat_temperature",
        "selected_candidate": selected,
    }
