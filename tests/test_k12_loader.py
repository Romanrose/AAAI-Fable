"""第一部分 K12 加载器单元测试。

用合成的最小 subject JSON（tmp 目录）测试，不依赖仓库内 18MB 真实数据；
末尾另有一个真实数据集成测试，数据缺失时自动跳过。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na.data.k12_loader import (
    SUBJECTS,
    ConceptRecord,
    load_all_concepts,
    load_subject,
)


def _write_subject(root: Path, subject: str, nodes: list[dict]) -> None:
    (root / f"{subject}.json").write_text(
        json.dumps({"nodes": nodes, "edges": []}, ensure_ascii=False),
        encoding="utf-8",
    )


def _sample_nodes() -> list[dict]:
    return [
        {
            "id": "physics_cpt1",
            "label": "Concept",
            "name": "电子转移",
            "properties": {
                "definition": "在外界作用下，电子从一个物体转移到另一个物体，从而导致带电。",
                "importance": "掌握",
                "formula": "摩擦 → 电子转移 → 带电",
                "examples": ["摩擦起电", "摩擦起电"],  # 故意重复，测去重
                "aliases": ["电荷转移"],
            },
        },
        {  # 缺 properties，应归一成空字段而非报错
            "id": "physics_cpt2",
            "label": "Concept",
            "name": "参照物",
        },
        {  # 非 Concept，应被跳过
            "id": "physics_chap1",
            "label": "Chapter",
            "name": "第一章 机械运动",
        },
        {  # 缺 name，应被跳过
            "id": "physics_cpt3",
            "label": "Concept",
            "name": "",
        },
    ]


def test_load_subject_parses_concept_fields() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_subject(root, "physics", _sample_nodes())

        # Act
        records = load_subject("physics", root=root)

    # Assert：4 个节点里只有 2 个合法 Concept
    assert len(records) == 2
    first = records[0]
    assert isinstance(first, ConceptRecord)
    assert first.name == "电子转移"
    assert first.subject == "physics"
    assert first.definition.startswith("在外界作用下")
    assert first.formula == "摩擦 → 电子转移 → 带电"
    assert first.aliases == ("电荷转移",)


def test_load_subject_normalizes_missing_and_duplicate_props() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_subject(root, "physics", _sample_nodes())
        records = load_subject("physics", root=root)

    by_id = {r.id: r for r in records}
    # examples 去重保序
    assert by_id["physics_cpt1"].examples == ("摩擦起电",)
    # 缺 properties 的概念：字段空、has_definition False
    bare = by_id["physics_cpt2"]
    assert bare.definition == ""
    assert bare.formula == ""
    assert bare.examples == ()
    assert bare.has_definition() is False


def test_load_subject_rejects_unknown_subject() -> None:
    try:
        load_subject("history")
    except ValueError as exc:
        assert "未知学科" in str(exc)
    else:
        raise AssertionError("未知学科应抛 ValueError")


def test_load_subject_raises_on_missing_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            load_subject("physics", root=Path(tmp))
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("缺文件应抛 FileNotFoundError")


def _real_data_present() -> bool:
    repo_root = Path(__file__).resolve().parents[1]
    return (
        repo_root
        / "data"
        / "K12-KGraph"
        / "K12-KGraph"
        / "subject_specific_KG"
        / "physics.json"
    ).is_file()


def test_load_all_concepts_real_data_smoke() -> None:
    """集成：真实数据存在时，四学科都应读出概念且全部带定义大头。"""
    if not _real_data_present():
        print("  [skip] 真实 K12-KGraph 数据缺失，跳过集成测试")
        return
    records = load_all_concepts()
    assert len(records) > 5000
    assert {r.subject for r in records} == set(SUBJECTS)
    with_def = sum(1 for r in records if r.has_definition())
    assert with_def / len(records) > 0.9  # README 称几乎全有定义


# --------------------------------------------------------------------------- #
# 无 pytest 环境下的自运行 harness（pytest 仍可正常收集上面的 test_*）。
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 - 测试 harness 需汇总所有失败
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc!r}")
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
