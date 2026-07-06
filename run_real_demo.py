#!/usr/bin/env python3
"""第二部分接真实 LLM 的端到端 demo：拿第一部分校验过的 G_c 跑出真实 N+A。

读 data/concepts/raw|processed 里的某个概念 JSON（M2NAInput），用 DeepSeek 真实生成
叙事 N、对齐 A，并打印 reviser 自检报告（泄露/覆盖）。

环境要求：DEEPSEEK_API_KEY；TLS 代理环境另需 SSL_CERT_FILE（见 PROGRESS.md A 节）。

用法:
    python run_real_demo.py                          # 默认胰岛素
    python run_real_demo.py data/concepts/raw/xxx.json
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

from src.m2na import M2NAPipeline
from src.m2na.agents.deepseek import DeepSeekClient
from src.m2na.data import load_input
from src.m2na.data.gc_extractor import _strip_code_fence
from src.m2na.result_store import save_run
from src.m2na.types import M2NAResult


class _StripFenceClient:
    """薄包装：剥掉真实模型常带的 ```json 代码围栏，让各 agent 的 json.loads 可用。"""

    def __init__(self, inner: DeepSeekClient) -> None:
        self._inner = inner

    def complete(self, prompt: str, system: str | None = None) -> str:
        return _strip_code_fence(self._inner.complete(prompt, system))


def _resolve_path(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    # 默认找概念名为「胰岛素」的草稿
    for f in sorted(glob.glob("data/concepts/raw/*.json")):
        if '"concept": "胰岛素"' in Path(f).read_text(encoding="utf-8"):
            return Path(f)
    raise SystemExit("未找到胰岛素草稿，请显式传入 JSON 路径")


def _print(result: M2NAResult) -> None:
    print(f"\n{'=' * 72}\nCONCEPT: {result.concept}\n{'=' * 72}")
    print(f"\n[Plan] 源域: {result.plan.source_domain}")
    print("\n[Plan] 要素→载体:")
    for m in result.plan.mappings:
        print(f"  - {m.concept_element:<28} -> {m.narrative_carrier}")
    print("\n[N] 叙事:")
    print(f"  {result.narrative}")
    print("\n[A] 对齐:")
    for pair in result.alignment:
        print(f"  - {pair.concept_element:<28} <- {pair.narrative_element}")
    report = result.report
    print(f"\n[自检] {'PASS' if report.passed else 'FAIL'}")
    print(f"  硬泄露   : {list(report.hard_leaks) or 'none'}")
    print(f"  未覆盖节点: {list(report.uncovered_elements) or 'none'}")


def main() -> None:
    path = _resolve_path(sys.argv[1] if len(sys.argv) > 1 else None)
    inp = load_input(path)
    print(f"输入: {path}  (节点{len(inp.mechanism.nodes)} 边{len(inp.mechanism.edges)} "
          f"禁用词{list(inp.forbidden_terms)})")

    pipeline = M2NAPipeline(_StripFenceClient(DeepSeekClient(temperature=0.7, timeout=90)))
    result = pipeline.run(inp)
    _print(result)

    run_dir = save_run(inp, result)
    print(f"\n[已保存] {run_dir}")
    print("  input.json / plan.json / narrative.txt / alignment.json / report.json / result.json / summary.md")


if __name__ == "__main__":
    main()
