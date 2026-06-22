"""M2NA 任务的核心数据结构。

任务：Mechanism-to-Narrative Analogy Generation
输入 (G_c, T_c) -> 输出 (N, A)

所有结构均为不可变 (frozen dataclass + tuple)，避免流水线各阶段产生隐性副作用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


# --------------------------------------------------------------------------- #
# 输入：概念机制 (G_c) 与禁用词集 (T_c)
# 第一部分(数据库+清洗)负责产出这些结构，这里只定义契约。
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MechanismNode:
    """机制图中的一个关键要素：状态、角色、条件、过程或结果。"""

    id: str
    label: str


@dataclass(frozen=True)
class MechanismEdge:
    """机制要素之间的关系：因果、强化、抑制、转化等。"""

    source: str  # MechanismNode.id
    target: str  # MechanismNode.id
    relation: str


@dataclass(frozen=True)
class MechanismGraph:
    """G_c：抽象概念的机制图。"""

    concept: str
    domain: str
    nodes: Tuple[MechanismNode, ...]
    edges: Tuple[MechanismEdge, ...]

    def node_ids(self) -> Tuple[str, ...]:
        return tuple(node.id for node in self.nodes)


@dataclass(frozen=True)
class M2NAInput:
    """单个样本的完整输入。"""

    mechanism: MechanismGraph  # G_c
    forbidden_terms: Tuple[str, ...]  # T_c：概念名 + 高泄露术语


# --------------------------------------------------------------------------- #
# 中间产物：叙事规划
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PlannedMapping:
    """规划阶段建立的「概念要素 -> 叙事载体」初步对应。"""

    concept_element: str  # MechanismNode.id
    narrative_carrier: str


@dataclass(frozen=True)
class NarrativePlan:
    source_domain: str
    mappings: Tuple[PlannedMapping, ...]


# --------------------------------------------------------------------------- #
# 输出：隐性叙事类比 (N) 与结构映射 (A)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AlignmentPair:
    concept_element: str  # MechanismNode.id
    narrative_element: str


@dataclass(frozen=True)
class RevisionReport:
    """自检结果：词汇泄露 + 机制覆盖。"""

    hard_leaks: Tuple[str, ...]  # 命中的禁用词
    uncovered_elements: Tuple[str, ...]  # 未被对齐覆盖的机制节点 id
    passed: bool


@dataclass(frozen=True)
class M2NAResult:
    concept: str
    plan: NarrativePlan
    narrative: str  # N
    alignment: Tuple[AlignmentPair, ...]  # A
    report: RevisionReport
