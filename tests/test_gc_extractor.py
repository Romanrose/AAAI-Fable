"""第一部分 G_c 抽取的解析/校验单元测试（不依赖真实 LLM）。"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na.data.gc_extractor import (
    GcExtractionError,
    build_extraction_prompt,
    extract_mechanism_graph,
    parse_mechanism_graph,
)
from src.m2na.data.k12_loader import ConceptRecord


def _record() -> ConceptRecord:
    return ConceptRecord(
        id="physics_cpt1",
        name="电子转移",
        subject="physics",
        definition="在外界作用下，电子从一个物体转移到另一个物体，从而导致带电。",
        formula="摩擦 → 电子转移 → 带电",
        examples=("摩擦起电",),
        aliases=(),
    )


_GOOD = {
    "nodes": [
        {"id": "external_action", "label": "外界作用"},
        {"id": "electron_move", "label": "电子转移"},
        {"id": "charged", "label": "物体带电"},
    ],
    "edges": [
        {"source": "external_action", "target": "electron_move", "relation": "引起"},
        {"source": "electron_move", "target": "charged", "relation": "导致"},
    ],
}


def test_prompt_contains_material() -> None:
    prompt = build_extraction_prompt(_record())
    assert "电子转移" in prompt
    assert "在外界作用下" in prompt
    assert "摩擦 → 电子转移 → 带电" in prompt  # formula 入 prompt
    assert "[[CONCEPT:电子转移]]" in prompt


def test_parse_valid_graph() -> None:
    g = parse_mechanism_graph(_record(), json.dumps(_GOOD, ensure_ascii=False))
    assert g.concept == "电子转移"
    assert g.domain == "physics"
    assert len(g.nodes) == 3
    assert len(g.edges) == 2
    assert set(g.node_ids()) == {"external_action", "electron_move", "charged"}


def test_parse_strips_code_fence() -> None:
    raw = "```json\n" + json.dumps(_GOOD, ensure_ascii=False) + "\n```"
    g = parse_mechanism_graph(_record(), raw)
    assert len(g.nodes) == 3


def test_parse_rejects_invalid_json() -> None:
    try:
        parse_mechanism_graph(_record(), "这不是JSON")
    except GcExtractionError:
        pass
    else:
        raise AssertionError("非法 JSON 应抛 GcExtractionError")


def test_parse_rejects_empty_nodes() -> None:
    try:
        parse_mechanism_graph(_record(), json.dumps({"nodes": [], "edges": []}))
    except GcExtractionError:
        pass
    else:
        raise AssertionError("空节点应抛 GcExtractionError")


def test_parse_rejects_dangling_edge() -> None:
    bad = {
        "nodes": [{"id": "a", "label": "A"}],
        "edges": [{"source": "a", "target": "ghost", "relation": "导致"}],
    }
    try:
        parse_mechanism_graph(_record(), json.dumps(bad))
    except GcExtractionError as exc:
        assert "悬空边" in str(exc)
    else:
        raise AssertionError("悬空边应抛 GcExtractionError")


def test_parse_rejects_duplicate_node_id() -> None:
    bad = {"nodes": [{"id": "a", "label": "A"}, {"id": "a", "label": "A2"}], "edges": []}
    try:
        parse_mechanism_graph(_record(), json.dumps(bad))
    except GcExtractionError as exc:
        assert "重复" in str(exc)
    else:
        raise AssertionError("重复 id 应抛 GcExtractionError")


def test_parse_edge_missing_relation() -> None:
    bad = {
        "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
        "edges": [{"source": "a", "target": "b"}],
    }
    try:
        parse_mechanism_graph(_record(), json.dumps(bad))
    except GcExtractionError:
        pass
    else:
        raise AssertionError("缺 relation 应抛 GcExtractionError")


def test_extract_end_to_end_with_fake_llm() -> None:
    # Arrange：内联 fake LLM，验证 extract 把 prompt→响应→图 串起来
    class _FakeLLM:
        def complete(self, prompt: str) -> str:
            assert "电子转移" in prompt  # 确认 prompt 被传入
            return json.dumps(_GOOD, ensure_ascii=False)

    # Act
    g = extract_mechanism_graph(_record(), _FakeLLM())

    # Assert
    assert len(g.nodes) == 3 and len(g.edges) == 2


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
