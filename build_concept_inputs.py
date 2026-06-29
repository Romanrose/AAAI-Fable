#!/usr/bin/env python3
"""第一部分批处理入口：选概念 → 抽 G_c → 建 T_c → 存 data/concepts/raw/。

产出的是**草稿**，需人工校验后再复制/编辑到 data/concepts/processed/。

环境要求（DeepSeek 真实抽取）：
    export DEEPSEEK_API_KEY=...               # 必需
    export SSL_CERT_FILE=/tmp/corp_ca.pem     # TLS 拦截代理环境需要，见 PROGRESS.md A 节

用法:
    python build_concept_inputs.py                 # 跑内置 pilot 概念清单
    python build_concept_inputs.py biology 胰岛素   # 单跑指定 学科 概念名
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.m2na.agents.deepseek import DeepSeekClient
from src.m2na.data import (
    ConceptRecord,
    GcExtractionError,
    build_forbidden_terms,
    extract_mechanism_graph,
    load_subject,
    save_input,
)
from src.m2na.types import M2NAInput

RAW_DIR = Path(__file__).resolve().parent / "data" / "concepts" / "raw"

# 手选的机制清晰、适合叙事类比的 pilot 概念（避开纯列表/递变型）。
PILOT_CONCEPTS: tuple[tuple[str, str], ...] = (
    ("biology", "胰岛素"),
    ("biology", "胰高血糖素"),
    ("biology", "自由基学说"),
    ("biology", "淀粉—平衡石假说"),
    ("chemistry", "全球变暖"),
    ("chemistry", "温度对反应速率的影响"),
    ("chemistry", "火力发电的能量转化过程"),
    ("physics", "电子转移"),
)


def _find_record(subject: str, name: str) -> ConceptRecord | None:
    return next((r for r in load_subject(subject) if r.name == name), None)


def _process_one(subject: str, name: str, llm: DeepSeekClient) -> bool:
    record = _find_record(subject, name)
    if record is None:
        print(f"  [跳过] {subject}/{name}：未在学科图中找到")
        return False
    try:
        graph = extract_mechanism_graph(record, llm)
    except GcExtractionError as exc:
        print(f"  [失败] {subject}/{name}：抽取/校验出错 {exc}")
        return False

    inp = M2NAInput(mechanism=graph, forbidden_terms=build_forbidden_terms(record))
    path = save_input(inp, RAW_DIR / f"{record.id}.json")
    print(
        f"  [OK] {name:14s} 节点={len(graph.nodes):2d} 边={len(graph.edges):2d} "
        f"T_c={list(inp.forbidden_terms)}  -> {path.relative_to(RAW_DIR.parent.parent)}"
    )
    return True


def main() -> None:
    args = sys.argv[1:]
    if len(args) >= 2:
        targets = [(args[0], args[1])]
    else:
        targets = list(PILOT_CONCEPTS)

    # 低温度求稳，减少越界发挥。
    llm = DeepSeekClient(temperature=0.2, timeout=90)

    print(f"抽取 {len(targets)} 个概念 -> {RAW_DIR}\n")
    ok = 0
    for subject, name in targets:
        if _process_one(subject, name, llm):
            ok += 1
    print(f"\n完成 {ok}/{len(targets)}。草稿在 data/concepts/raw/，请人工校验后转入 processed/。")


if __name__ == "__main__":
    main()
