#!/usr/bin/env python3
"""批量跑第二部分：对 data/concepts/raw/ 下所有概念真实生成 N+A，各存 output，汇总成表。

环境要求：DEEPSEEK_API_KEY；TLS 代理环境另需 SSL_CERT_FILE（见 PROGRESS.md A 节）。

用法:
    python run_real_batch.py
"""

from __future__ import annotations

import glob

from src.m2na import M2NAPipeline
from src.m2na.agents.deepseek import DeepSeekClient
from src.m2na.data import load_input
from src.m2na.data.gc_extractor import _strip_code_fence
from src.m2na.result_store import save_run


class _StripFenceClient:
    """剥掉真实模型常带的 ```json 围栏，让各 agent 的 json.loads 可用。"""

    def __init__(self, inner: DeepSeekClient) -> None:
        self._inner = inner

    def complete(self, prompt: str, system: str | None = None) -> str:
        return _strip_code_fence(self._inner.complete(prompt, system))


def main() -> None:
    paths = sorted(glob.glob("data/concepts/raw/*.json"))
    if not paths:
        raise SystemExit("data/concepts/raw/ 下没有概念，先跑 build_concept_inputs.py")

    pipeline = M2NAPipeline(_StripFenceClient(DeepSeekClient(temperature=0.7, timeout=90)))

    rows: list[tuple[str, int, int, int, str]] = []
    for path in paths:
        inp = load_input(path)
        concept = inp.mechanism.concept
        n_nodes = len(inp.mechanism.nodes)
        try:
            result = pipeline.run(inp)
        except Exception as exc:  # noqa: BLE001 - 单个失败不中断批处理
            print(f"[失败] {concept}: {exc!r}")
            rows.append((concept, n_nodes, -1, -1, "ERROR"))
            continue

        run_dir = save_run(inp, result)
        rep = result.report
        covered = n_nodes - len(rep.uncovered_elements)
        rows.append(
            (concept, n_nodes, covered, len(rep.hard_leaks),
             "PASS" if rep.passed else "FAIL")
        )
        print(f"[OK] {concept:14s} 覆盖 {covered}/{n_nodes} 泄露 {len(rep.hard_leaks)} "
              f"-> {run_dir.name}")

    # 汇总表
    print("\n" + "=" * 64)
    print(f"{'概念':<16}{'节点':>4}{'覆盖':>8}{'硬泄露':>8}{'结果':>8}")
    print("-" * 64)
    for concept, n, covered, leaks, status in rows:
        cov = f"{covered}/{n}" if covered >= 0 else "—"
        lk = str(leaks) if leaks >= 0 else "—"
        print(f"{concept:<16}{n:>4}{cov:>8}{lk:>8}{status:>8}")
    print("=" * 64)
    passed = sum(1 for r in rows if r[4] == "PASS")
    print(f"PASS {passed}/{len(rows)}。详见各 output/<时间戳>_<概念>/ 文件夹。")


if __name__ == "__main__":
    main()
