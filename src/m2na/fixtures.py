"""最小输入 fixture。

第二部分先用手写的 G_c + T_c 跑通流程；待第一部分(数据库+清洗)就绪后，
这些 fixture 将被清洗管线产出的真实数据替换。
"""

from __future__ import annotations

from .types import M2NAInput, MechanismEdge, MechanismGraph, MechanismNode


def path_dependence() -> M2NAInput:
    mechanism = MechanismGraph(
        concept="path dependence",
        domain="economics / social science",
        nodes=(
            MechanismNode("initial_choice", "an initial, somewhat arbitrary choice"),
            MechanismNode("reinforcing_feedback", "feedback that reinforces the choice"),
            MechanismNode("switching_cost", "rising cost of switching away"),
            MechanismNode("lock_in", "the choice becomes locked in"),
            MechanismNode("suboptimal_persistence", "a possibly worse option persists"),
        ),
        edges=(
            MechanismEdge("initial_choice", "reinforcing_feedback", "enables"),
            MechanismEdge("reinforcing_feedback", "switching_cost", "increases"),
            MechanismEdge("switching_cost", "lock_in", "causes"),
            MechanismEdge("lock_in", "suboptimal_persistence", "leads_to"),
        ),
    )
    forbidden = (
        "path dependence",
        "lock-in",
        "switching cost",
        "positive feedback",
        "historical contingency",
    )
    return M2NAInput(mechanism=mechanism, forbidden_terms=forbidden)


def overfitting() -> M2NAInput:
    mechanism = MechanismGraph(
        concept="overfitting",
        domain="machine learning",
        nodes=(
            MechanismNode("fit_training_pattern", "adapts to training-specific patterns"),
            MechanismNode("high_seen_performance", "performs well on seen data"),
            MechanismNode("poor_generalization", "generalizes poorly to unseen data"),
        ),
        edges=(
            MechanismEdge("fit_training_pattern", "high_seen_performance", "causes"),
            MechanismEdge("fit_training_pattern", "poor_generalization", "causes"),
        ),
    )
    forbidden = ("overfitting", "overfit", "training set", "generalization", "regularization")
    return M2NAInput(mechanism=mechanism, forbidden_terms=forbidden)


ALL_FIXTURES = {
    "path dependence": path_dependence,
    "overfitting": overfitting,
}
