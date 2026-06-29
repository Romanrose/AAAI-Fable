"""机制富集度筛选。

M2NA 要的是「有内部因果机制、值得演成叙事」的概念，而非纯定义/术语/事实。
本模块用一份确定性的因果/过程信号词表给概念定义打分，筛出候选并排序。

刻意保持确定性 + 可解释（命中的信号词会回传），原因有二：
1. 结果可复现，能写进论文的数据构建协议；
2. 它是 LLM 抽机制图前的「粗筛」，不替代人工校验，只是把 6000+ 概念压到可人工过的量级。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from .k12_loader import ConceptRecord

# 因果 / 过程 / 转化类信号词：定义里出现得越多，越可能描述一条机制链而非静态定义。
# 选词偏中文理科教材语体（K12-KGraph 为人教版中文教材）。
MECHANISM_SIGNALS: Tuple[str, ...] = (
    "导致",
    "使得",
    "引起",
    "因此",
    "从而",
    "进而",
    "造成",
    "随着",
    "增大",
    "减小",
    "增强",
    "减弱",
    "升高",
    "降低",
    "转化",
    "转移",
    "反应",
    "作用",
    "变化",
    "运动",
    "则",
    "所以",
    "促使",
    "推动",
    "形成",
)

# 默认粗筛阈值：定义足够长 + 命中足够多不同信号词，才算机制候选。
DEFAULT_MIN_DEFINITION_LEN = 40
DEFAULT_MIN_DISTINCT_SIGNALS = 2
# 带公式的概念往往刻画了量间依赖关系，给一点机制加成。
_FORMULA_BONUS = 1


@dataclass(frozen=True)
class ScoredConcept:
    """打分后的概念候选，按机制富集度排序时使用。"""

    record: ConceptRecord
    score: int
    signal_hits: Tuple[str, ...]  # 命中的不同信号词，供人工核验

    @property
    def distinct_signals(self) -> int:
        return len(self.signal_hits)


def _matched_signals(text: str) -> Tuple[str, ...]:
    """返回 text 中命中的不同机制信号词（保 MECHANISM_SIGNALS 顺序）。"""

    return tuple(sig for sig in MECHANISM_SIGNALS if sig in text)


def score_mechanism(record: ConceptRecord) -> ScoredConcept:
    """给单个概念打机制富集分。

    分数 = 命中的不同信号词数 + 公式加成（有公式 +1）。
    分数低不代表概念差，只代表「不像一条可叙事的因果机制」。
    """

    hits = _matched_signals(record.definition)
    score = len(hits) + (_FORMULA_BONUS if record.formula else 0)
    return ScoredConcept(record=record, score=score, signal_hits=hits)


def rank_candidates(
    records: Iterable[ConceptRecord],
    *,
    min_definition_len: int = DEFAULT_MIN_DEFINITION_LEN,
    min_distinct_signals: int = DEFAULT_MIN_DISTINCT_SIGNALS,
) -> Tuple[ScoredConcept, ...]:
    """筛出机制候选并按分数降序排列。

    过滤条件（同时满足）：
      - 定义长度 >= min_definition_len（太短的多是术语条目）；
      - 命中不同信号词数 >= min_distinct_signals。

    排序：分数降序；同分时按定义长度降序、再按 id 升序，保证确定性。
    """

    scored = []
    for record in records:
        if len(record.definition) < min_definition_len:
            continue
        candidate = score_mechanism(record)
        if candidate.distinct_signals < min_distinct_signals:
            continue
        scored.append(candidate)

    scored.sort(
        key=lambda c: (-c.score, -len(c.record.definition), c.record.id)
    )
    return tuple(scored)
