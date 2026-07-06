"""第一部分 concept_store 序列化往返测试。"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na.data.concept_store import (
    from_dict,
    load_input,
    save_input,
    to_dict,
)
from src.m2na.data.gc_extractor import GcExtractionError
from src.m2na.types import (
    M2NAInput,
    MechanismEdge,
    MechanismGraph,
    MechanismNode,
)


def _sample_input() -> M2NAInput:
    mech = MechanismGraph(
        concept="胰岛素",
        domain="biology",
        nodes=(
            MechanismNode("high", "血糖升高"),
            MechanismNode("secrete", "胰岛素分泌"),
            MechanismNode("low", "血糖降低"),
        ),
        edges=(
            MechanismEdge("high", "secrete", "导致"),
            MechanismEdge("secrete", "low", "导致"),
        ),
    )
    return M2NAInput(mechanism=mech, forbidden_terms=("胰岛素", "insulin"))


def test_roundtrip_dict() -> None:
    # Arrange
    inp = _sample_input()

    # Act
    restored = from_dict(to_dict(inp))

    # Assert：完全等价
    assert restored == inp


def test_roundtrip_file() -> None:
    inp = _sample_input()
    with tempfile.TemporaryDirectory() as tmp:
        path = save_input(inp, Path(tmp) / "sub" / "胰岛素.json")
        assert path.is_file()  # 自动建父目录
        restored = load_input(path)
    assert restored == inp


def test_from_dict_requires_concept() -> None:
    try:
        from_dict({"domain": "biology", "mechanism": {"nodes": [{"id": "a", "label": "A"}]}})
    except GcExtractionError as exc:
        assert "concept" in str(exc)
    else:
        raise AssertionError("缺 concept 应抛错")


def test_from_dict_rejects_dangling_edge() -> None:
    data = {
        "concept": "x",
        "domain": "physics",
        "forbidden_terms": [],
        "mechanism": {
            "nodes": [{"id": "a", "label": "A"}],
            "edges": [{"source": "a", "target": "ghost", "relation": "导致"}],
        },
    }
    try:
        from_dict(data)
    except GcExtractionError as exc:
        assert "悬空边" in str(exc)
    else:
        raise AssertionError("悬空边应抛错")


def test_forbidden_terms_filtered_on_load() -> None:
    data = {
        "concept": "x",
        "domain": "physics",
        "forbidden_terms": ["酶", "", "  ", "enzyme"],
        "mechanism": {"nodes": [{"id": "a", "label": "A"}], "edges": []},
    }
    inp = from_dict(data)
    assert inp.forbidden_terms == ("酶", "enzyme")


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
