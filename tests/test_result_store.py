"""运行产物落盘测试（不调 LLM）。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na.result_store import result_to_dict, save_run
from src.m2na.types import (
    AlignmentPair,
    M2NAInput,
    M2NAResult,
    MechanismEdge,
    MechanismGraph,
    MechanismNode,
    NarrativePlan,
    PlannedMapping,
    RevisionReport,
)


def _sample() -> tuple[M2NAInput, M2NAResult]:
    mech = MechanismGraph(
        concept="胰岛素",
        domain="biology",
        nodes=(MechanismNode("high", "血糖升高"), MechanismNode("low", "血糖降低")),
        edges=(MechanismEdge("high", "low", "导致"),),
    )
    inp = M2NAInput(mechanism=mech, forbidden_terms=("胰岛素", "insulin"))
    result = M2NAResult(
        concept="胰岛素",
        plan=NarrativePlan(
            source_domain="港口调度",
            mappings=(PlannedMapping("high", "车流涌入"),),
        ),
        narrative="车流涌入后调度中心放行，很快恢复通畅。",
        alignment=(AlignmentPair("high", "车流涌入"), AlignmentPair("low", "恢复通畅")),
        report=RevisionReport(hard_leaks=(), uncovered_elements=(), passed=True),
    )
    return inp, result


def test_save_run_creates_all_files() -> None:
    inp, result = _sample()
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = save_run(inp, result, output_root=tmp, timestamp="20260623_120000")

        assert run_dir.name == "20260623_120000_胰岛素"
        for fname in (
            "input.json",
            "plan.json",
            "narrative.txt",
            "alignment.json",
            "report.json",
            "result.json",
            "summary.md",
        ):
            assert (run_dir / fname).is_file(), f"缺文件 {fname}"

        # narrative.txt 原样
        assert (run_dir / "narrative.txt").read_text(encoding="utf-8").startswith("车流涌入")
        # report.json 内容正确
        report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        assert report["passed"] is True
        # summary.md 含关键段
        summary = (run_dir / "summary.md").read_text(encoding="utf-8")
        assert "胰岛素" in summary and "港口调度" in summary


def test_result_to_dict_shape() -> None:
    inp, result = _sample()
    d = result_to_dict(inp, result)
    assert d["concept"] == "胰岛素"
    assert d["narrative"].startswith("车流涌入")
    assert d["input"]["forbidden_terms"] == ["胰岛素", "insulin"]
    assert len(d["alignment"]) == 2
    assert d["report"]["passed"] is True


def test_unsafe_concept_name_sanitized() -> None:
    inp, result = _sample()
    # 构造含路径分隔符的概念名
    bad = M2NAResult(
        concept="a/b:c",
        plan=result.plan,
        narrative=result.narrative,
        alignment=result.alignment,
        report=result.report,
    )
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = save_run(inp, bad, output_root=tmp, timestamp="t")
        assert "/" not in run_dir.name.replace(tmp, "")
        assert run_dir.is_dir()


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
