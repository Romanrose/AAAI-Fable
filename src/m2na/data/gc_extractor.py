"""机制图 G_c 半自动抽取。

从 K12 概念记录（definition / formula / examples）抽出机制图 MechanismGraph，
作为人工校验前的草稿。设计要点：

1. **LLM 可注入**：抽取调用走 agents/llm.py 的 LLMClient 协议，与第二部分共用同一
   契约——换 Mock / 真实后端不改本模块。需要真实 API 才能产出有意义的 G_c。
2. **解析与校验是确定性的**：`parse_mechanism_graph` 不依赖 LLM，可单测、可复现。
   它对 LLM 的 JSON 输出做严格校验（悬空边、空节点直接报错），把「图是否自洽」从
   模型能力里剥离出来——这是切断循环论证的一环。
3. 抽出的只是**草稿**：definition 来自人教教材（非同源 LLM），但拓扑结构仍需人工定稿，
   存盘到 data/concepts/ 后由人校验。
"""

from __future__ import annotations

import json
from typing import Tuple

from ..agents.llm import LLMClient
from ..types import MechanismEdge, MechanismGraph, MechanismNode
from .k12_loader import ConceptRecord

# 抽取阶段标签：与第二部分的 [[STAGE:...]] 风格一致，对真实 LLM 是有效上下文。
STAGE_EXTRACT = "extract"


class GcExtractionError(RuntimeError):
    """LLM 输出无法解析成自洽机制图时抛出，避免静默产出残图。"""


def build_extraction_prompt(record: ConceptRecord) -> str:
    """构造抽取 prompt。把教材定义/公式/例子作为唯一事实来源喂给模型。"""

    parts = [
        f"[[STAGE:{STAGE_EXTRACT}]] [[CONCEPT:{record.name}]]",
        "你是严谨的知识工程师。请把下面这个概念定义中**已明确陈述的核心因果/转化机制**抽成一张有向图。",
        "注意：这里要的是核心机制图，不是关键词附近知识子图；只保留让这个概念'如何运作'成立的主链条。",
        "",
        "严格规则（违反会使数据作废）：",
        "1. 只能使用定义/公式/例子里**明确出现**的因果、转化、增强、抑制关系；",
        "2. 禁止补充你自己的学科背景知识——即使你知道还有别的环节或影响因素，材料没写就不能加；",
        "3. 节点数优先控制在 3-6 个；复杂机制最多 8 个；超过 8 个时必须合并相近状态/过程；",
        "4. 边只保留主因果链和必要分叉，避免把相关背景、上下位概念、并列知识点放进图里；",
        "5. 若材料只是静态定义或表示方法、没有因果过程，宁可只输出 1-2 个节点、0 条边，也不要编造机制；",
        "6. 每个节点都必须能在定义文本里找到出处。",
        "",
        f"概念名：{record.name}",
        f"学科：{record.subject}",
        f"定义：{record.definition}",
    ]
    if record.formula:
        parts.append(f"公式/过程：{record.formula}")
    if record.examples:
        parts.append(f"例子：{' / '.join(record.examples)}")
    parts += [
        "",
        "输出严格的 JSON，格式：",
        '{"nodes":[{"id":"英文蛇形id","label":"该机制要素的简短中文描述"}],'
        '"edges":[{"source":"节点id","target":"节点id","relation":"因果关系如 导致/增强/抑制/转化"}]}',
        "要求：节点=机制中的关键状态/过程/结果；边=它们之间的因果或转化关系；",
        "每个 source/target 必须是上面 nodes 里出现过的 id；只输出 JSON，不要解释。",
    ]
    return "\n".join(parts)


def _strip_code_fence(raw: str) -> str:
    """去掉 ```json ... ``` 代码围栏（真实 LLM 常带）。"""

    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # 去掉首行 ``` 或 ```json 与末行 ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def parse_mechanism_graph(record: ConceptRecord, raw: str) -> MechanismGraph:
    """把 LLM 的 JSON 输出解析+校验成 MechanismGraph（确定性、可单测）。

    校验：JSON 合法、nodes 非空且 id/label 齐全且 id 唯一、每条 edge 的
    source/target 指向已知节点且 relation 非空。任一不满足抛 GcExtractionError。
    """

    try:
        data = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise GcExtractionError(f"LLM 输出非合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GcExtractionError("LLM 输出顶层应为 JSON 对象")

    nodes = _parse_nodes(data.get("nodes"))
    edges = _parse_edges(data.get("edges"), node_ids={n.id for n in nodes})

    return MechanismGraph(
        concept=record.name,
        domain=record.subject,
        nodes=nodes,
        edges=edges,
    )


def _parse_nodes(raw_nodes: object) -> Tuple[MechanismNode, ...]:
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise GcExtractionError("nodes 缺失或为空")
    seen: set[str] = set()
    out: list[MechanismNode] = []
    for item in raw_nodes:
        if not isinstance(item, dict):
            raise GcExtractionError(f"节点应为对象: {item!r}")
        nid = str(item.get("id", "")).strip()
        label = str(item.get("label", "")).strip()
        if not nid or not label:
            raise GcExtractionError(f"节点缺 id 或 label: {item!r}")
        if nid in seen:
            raise GcExtractionError(f"节点 id 重复: {nid!r}")
        seen.add(nid)
        out.append(MechanismNode(id=nid, label=label))
    return tuple(out)


def _parse_edges(raw_edges: object, node_ids: set[str]) -> Tuple[MechanismEdge, ...]:
    if raw_edges is None:
        return ()
    if not isinstance(raw_edges, list):
        raise GcExtractionError("edges 应为列表")
    out: list[MechanismEdge] = []
    for item in raw_edges:
        if not isinstance(item, dict):
            raise GcExtractionError(f"边应为对象: {item!r}")
        source = str(item.get("source", "")).strip()
        target = str(item.get("target", "")).strip()
        relation = str(item.get("relation", "")).strip()
        if not relation:
            raise GcExtractionError(f"边缺 relation: {item!r}")
        for endpoint in (source, target):
            if endpoint not in node_ids:
                raise GcExtractionError(f"边端点 {endpoint!r} 不在节点集合中（悬空边）")
        out.append(MechanismEdge(source=source, target=target, relation=relation))
    return tuple(out)


def extract_mechanism_graph(record: ConceptRecord, llm: LLMClient) -> MechanismGraph:
    """端到端：构造 prompt → 调 LLM → 解析校验成 G_c 草稿。"""

    raw = llm.complete(build_extraction_prompt(record))
    return parse_mechanism_graph(record, raw)
