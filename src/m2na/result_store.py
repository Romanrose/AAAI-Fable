"""运行产物落盘：把一次 M2NA 运行的全部中间产物 + 结果存成单独文件夹。

每次运行一个 `output/<时间戳>_<概念>/` 目录，便于回看、对比、附进论文附录。
目录内容：
    input.json      输入 (G_c + T_c)
    plan.json       Planner 产物（源域 + 要素→载体映射）
    narrative.txt   N：隐性叙事
    alignment.json  A：机制节点 ↔ 叙事元素
    report.json     reviser 自检（硬泄露 / 未覆盖节点 / 是否通过）
    result.json     上述汇总（机器可读）
    summary.md      人可读汇总
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .data.concept_store import to_dict as input_to_dict
from .types import M2NAInput, M2NAResult

_DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "output"
# 概念名里可能含路径不安全字符，做轻量清洗用于目录名。
_UNSAFE = '/\\:*?"<>|'


def _safe(name: str) -> str:
    return "".join("_" if c in _UNSAFE else c for c in name).strip() or "concept"


def _plan_to_dict(result: M2NAResult) -> dict[str, Any]:
    plan = result.plan
    return {
        "source_domain": plan.source_domain,
        "setting": plan.setting,
        "conflict": plan.conflict,
        "characters": [
            {"name": c.name, "role": c.role, "mapped_element": c.mapped_element}
            for c in plan.characters
        ],
        "mappings": [
            {"concept_element": m.concept_element, "narrative_carrier": m.narrative_carrier}
            for m in plan.mappings
        ],
        "plot_beats": [
            {"beat_id": b.beat_id, "event": b.event, "mapped_elements": list(b.mapped_elements)}
            for b in plan.plot_beats
        ],
        "turning_point": plan.turning_point,
        "ending": plan.ending,
        "implied_moral": plan.implied_moral,
    }


def _alignment_to_list(result: M2NAResult) -> list[dict[str, str]]:
    return [
        {"concept_element": p.concept_element, "narrative_element": p.narrative_element}
        for p in result.alignment
    ]


def _report_to_dict(result: M2NAResult) -> dict[str, Any]:
    r = result.report
    return {
        "passed": r.passed,
        "hard_leaks": list(r.hard_leaks),
        "uncovered_elements": list(r.uncovered_elements),
    }


def result_to_dict(inp: M2NAInput, result: M2NAResult) -> dict[str, Any]:
    """完整运行 → 机器可读 dict。"""

    return {
        "concept": result.concept,
        "input": input_to_dict(inp),
        "plan": _plan_to_dict(result),
        "narrative": result.narrative,
        "alignment": _alignment_to_list(result),
        "report": _report_to_dict(result),
    }


def _render_summary(inp: M2NAInput, result: M2NAResult) -> str:
    lines = [
        f"# M2NA 运行结果：{result.concept}",
        "",
        f"- 生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 禁用词 T_c：{', '.join(inp.forbidden_terms) or '（无）'}",
        f"- 机制规模：{len(inp.mechanism.nodes)} 节点 / {len(inp.mechanism.edges)} 边",
        "",
        f"## 源域\n\n{result.plan.source_domain}",
        "",
        "## 要素 → 叙事载体",
        "",
    ]
    lines += [f"- `{m.concept_element}` → {m.narrative_carrier}" for m in result.plan.mappings]
    lines += ["", "## N：叙事", "", result.narrative, "", "## A：对齐", ""]
    lines += [f"- `{p.concept_element}` ← {p.narrative_element}" for p in result.alignment]
    r = result.report
    lines += [
        "",
        "## 自检",
        "",
        f"- 结果：{'PASS' if r.passed else 'FAIL'}",
        f"- 硬泄露：{', '.join(r.hard_leaks) or 'none'}",
        f"- 未覆盖节点：{', '.join(r.uncovered_elements) or 'none'}",
        "",
    ]
    return "\n".join(lines)


def save_run(
    inp: M2NAInput,
    result: M2NAResult,
    output_root: Path | str | None = None,
    *,
    timestamp: str | None = None,
) -> Path:
    """把一次运行写入 `output/<时间戳>_<概念>/`，返回该目录路径。

    Args:
        timestamp: 目录名时间戳；None 时取当前时间（精确到秒）。
    """

    import json

    root = Path(output_root) if output_root is not None else _DEFAULT_OUTPUT_ROOT
    stamp = timestamp or f"{datetime.now():%Y%m%d_%H%M%S}"
    run_dir = root / f"{stamp}_{_safe(result.concept)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    def _dump(name: str, obj: Any) -> None:
        (run_dir / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    _dump("input.json", input_to_dict(inp))
    _dump("plan.json", _plan_to_dict(result))
    _dump("alignment.json", _alignment_to_list(result))
    _dump("report.json", _report_to_dict(result))
    _dump("result.json", result_to_dict(inp, result))
    (run_dir / "narrative.txt").write_text(result.narrative, encoding="utf-8")
    (run_dir / "summary.md").write_text(_render_summary(inp, result), encoding="utf-8")

    return run_dir
