"""M2NAInput 的 JSON 存取（第一部分 ↔ 第二部分的胶水）。

数据流：
    抽取草稿 -> data/concepts/raw/<id>.json -> 人工校验编辑 -> data/concepts/processed/<id>.json
    -> load_input() -> 喂给第二部分 M2NAPipeline。

JSON 是人可读可编辑的权威格式（人工校验直接改这个文件），因此存取要稳：
load 时严格校验结构并复用与 G_c 抽取相同的自洽性约束（悬空边即报错）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..types import M2NAInput, MechanismEdge, MechanismGraph, MechanismNode
from .gc_extractor import GcExtractionError, _parse_edges, _parse_nodes


def to_dict(inp: M2NAInput) -> dict[str, Any]:
    """M2NAInput -> 可序列化 dict。"""

    g = inp.mechanism
    return {
        "concept": g.concept,
        "domain": g.domain,
        "forbidden_terms": list(inp.forbidden_terms),
        "mechanism": {
            "nodes": [{"id": n.id, "label": n.label} for n in g.nodes],
            "edges": [
                {"source": e.source, "target": e.target, "relation": e.relation}
                for e in g.edges
            ],
        },
    }


def from_dict(data: Any) -> M2NAInput:
    """dict -> M2NAInput，带结构校验。"""

    if not isinstance(data, dict):
        raise GcExtractionError("概念输入顶层应为 JSON 对象")
    concept = str(data.get("concept", "")).strip()
    domain = str(data.get("domain", "")).strip()
    if not concept:
        raise GcExtractionError("缺少 concept")

    mech = data.get("mechanism")
    if not isinstance(mech, dict):
        raise GcExtractionError("缺少 mechanism 对象")
    nodes = _parse_nodes(mech.get("nodes"))
    edges = _parse_edges(mech.get("edges"), node_ids={n.id for n in nodes})

    forbidden = data.get("forbidden_terms", [])
    if not isinstance(forbidden, list):
        raise GcExtractionError("forbidden_terms 应为列表")
    forbidden_terms = tuple(str(t).strip() for t in forbidden if str(t).strip())

    mechanism = MechanismGraph(
        concept=concept, domain=domain, nodes=nodes, edges=edges
    )
    return M2NAInput(mechanism=mechanism, forbidden_terms=forbidden_terms)


def save_input(inp: M2NAInput, path: Path | str) -> Path:
    """把 M2NAInput 写成 UTF-8 JSON（缩进、保中文）。返回写入路径。"""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(to_dict(inp), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def load_input(path: Path | str) -> M2NAInput:
    """从 JSON 文件读回 M2NAInput。"""

    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GcExtractionError(f"概念文件非合法 JSON: {exc}") from exc
    return from_dict(data)
