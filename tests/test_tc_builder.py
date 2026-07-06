"""第一部分 T_c 构建单元测试。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na.data.k12_loader import ConceptRecord
from src.m2na.data.tc_builder import build_forbidden_terms


def _record(name: str, aliases=()) -> ConceptRecord:
    return ConceptRecord(
        id="c1",
        name=name,
        subject="physics",
        definition="d",
        formula="",
        examples=(),
        aliases=tuple(aliases),
    )


def test_includes_name_and_aliases() -> None:
    rec = _record("酶", aliases=("enzyme",))
    terms = build_forbidden_terms(rec)
    assert "酶" in terms
    assert "enzyme" in terms


def test_splits_parenthetical_alias_from_name() -> None:
    # Arrange：名称带括号别名（中文括号）
    rec = _record("静电力做功与路径无关（静电场力做功特点）")

    # Act
    terms = build_forbidden_terms(rec)

    # Assert：主名与括号词都成为禁用词，且主名已去掉括号
    assert "静电力做功与路径无关" in terms
    assert "静电场力做功特点" in terms
    assert all("（" not in t for t in terms)


def test_dedup_case_insensitive_preserves_order() -> None:
    rec = _record("Insulin", aliases=("insulin", "INSULIN", "胰岛素"))
    terms = build_forbidden_terms(rec)
    # 三个大小写变体只保留首次出现的 "Insulin"
    lowered = [t.lower() for t in terms]
    assert lowered.count("insulin") == 1
    assert terms[0] == "Insulin"
    assert "胰岛素" in terms


def test_extra_terms_appended_and_empty_filtered() -> None:
    rec = _record("光合作用")
    terms = build_forbidden_terms(rec, extra_terms=("", "  ", "叶绿体"))
    assert "叶绿体" in terms
    assert "" not in terms
    assert all(t.strip() for t in terms)


def test_returns_tuple_immutable() -> None:
    terms = build_forbidden_terms(_record("酶"))
    assert isinstance(terms, tuple)


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
