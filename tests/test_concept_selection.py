"""第一部分机制筛选单元测试。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na.data.concept_selection import (
    DEFAULT_MIN_DEFINITION_LEN,
    rank_candidates,
    score_mechanism,
)
from src.m2na.data.k12_loader import ConceptRecord


def _record(
    cid: str,
    definition: str,
    *,
    name: str = "概念",
    formula: str = "",
) -> ConceptRecord:
    return ConceptRecord(
        id=cid,
        name=name,
        subject="physics",
        definition=definition,
        formula=formula,
        examples=(),
        aliases=(),
        importance="",
    )


def test_score_counts_distinct_signals() -> None:
    # Arrange：精选互不为子串的三个信号词「进而 / 推动 / 促使」，避免误命中其它
    rec = _record("c1", "初始优势进而被放大，推动规模扩张，促使局面固定。")

    # Act
    scored = score_mechanism(rec)

    # Assert
    assert set(scored.signal_hits) == {"进而", "推动", "促使"}
    assert scored.distinct_signals == 3
    assert scored.score == 3  # 无公式，无加成


def test_formula_adds_bonus() -> None:
    rec = _record("c1", "初始优势进而被放大，推动规模扩张。", formula="A → B → C")
    scored = score_mechanism(rec)
    # 命中「进而 / 推动」2 个 + 公式加成 1
    assert set(scored.signal_hits) == {"进而", "推动"}
    assert scored.distinct_signals == 2
    assert scored.score == 3


def test_rank_filters_short_and_low_signal() -> None:
    long_mech = "随着温度升高，分子运动增强，从而导致反应速率增大。" * 2  # 长 + 多信号
    records = [
        _record("good", long_mech),
        _record("too_short", "导致从而反应"),  # 信号够但太短
        _record("low_signal", "这是一个没有任何因果线索的纯定义性概念条目说明。" * 2),
    ]

    candidates = rank_candidates(records)

    ids = [c.record.id for c in candidates]
    assert ids == ["good"]  # 只有 good 同时满足长度 + 信号阈值


def test_rank_is_sorted_desc_and_deterministic() -> None:
    base = "随着温度升高，反应加快，从而导致速率增大，进而促使平衡移动。"
    records = [
        _record("low", "氧化反应导致放热，从而升温。"),  # 2-3 信号
        _record("high_b", base, name="B"),
        _record("high_a", base, name="A"),  # 与 high_b 同定义同分
    ]

    candidates = rank_candidates(records)
    scores = [c.score for c in candidates]

    # 降序
    assert scores == sorted(scores, reverse=True)
    # 同分按 id 升序（high_a 在 high_b 前）确定性
    top_ids = [c.record.id for c in candidates if c.score == scores[0]]
    assert top_ids == sorted(top_ids)


def test_default_threshold_is_reasonable() -> None:
    # 防御性：阈值不应被误改成 0/负数导致全量通过
    assert DEFAULT_MIN_DEFINITION_LEN >= 20


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc!r}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
