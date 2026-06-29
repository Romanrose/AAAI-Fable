"""Reviser 自检测试，重点锁定"客观评判未实现(空片段)=未覆盖"的新语义。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na.agents.reviser import Reviser
from src.m2na.types import (
    AlignmentPair,
    M2NAInput,
    MechanismEdge,
    MechanismGraph,
    MechanismNode,
)


def _inp() -> M2NAInput:
    mech = MechanismGraph(
        concept="x",
        domain="d",
        nodes=(MechanismNode("a", "A"), MechanismNode("b", "B")),
        edges=(MechanismEdge("a", "b", "导致"),),
    )
    return M2NAInput(mechanism=mech, forbidden_terms=("禁词",))


def test_empty_narrative_element_counts_as_uncovered() -> None:
    # Arrange：aligner 客观判定 b 未实现（片段留空）
    alignment = (
        AlignmentPair("a", "具体情节"),
        AlignmentPair("b", "   "),  # 空白=未实现
    )
    # Act
    report = Reviser().review(_inp(), "一段没有禁词的叙事", alignment)
    # Assert：b 算未覆盖，整体 FAIL
    assert report.uncovered_elements == ("b",)
    assert report.passed is False


def test_all_realized_passes() -> None:
    alignment = (AlignmentPair("a", "情节1"), AlignmentPair("b", "情节2"))
    report = Reviser().review(_inp(), "干净叙事", alignment)
    assert report.uncovered_elements == ()
    assert report.passed is True


def test_hard_leak_detected() -> None:
    alignment = (AlignmentPair("a", "x"), AlignmentPair("b", "y"))
    report = Reviser().review(_inp(), "这段叙事出现了禁词二字", alignment)
    assert report.hard_leaks == ("禁词",)
    assert report.passed is False


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
