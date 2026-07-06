#!/usr/bin/env python3
"""M2NA 第二部分端到端 demo。

用 MockLLMClient 跑通 plan -> generate -> align -> review，打印 N、A 与自检报告。
接真实 LLM 时，只需把 MockLLMClient 换成实现了 LLMClient.complete 的后端。

用法:
    python run_demo.py                 # 跑全部 fixture
    python run_demo.py "overfitting"   # 跑指定概念
"""

from __future__ import annotations

import sys

from src.m2na import M2NAPipeline, MockLLMClient
from src.m2na.fixtures import ALL_FIXTURES
from src.m2na.types import M2NAResult


def _print_result(result: M2NAResult) -> None:
    print(f"\n{'=' * 70}\nCONCEPT: {result.concept}\n{'=' * 70}")
    print(f"\n[Plan] source domain: {result.plan.source_domain}")

    print("\n[N] Narrative:")
    print(f"  {result.narrative}")

    print("\n[A] Alignment:")
    for pair in result.alignment:
        print(f"  - {pair.concept_element:<24} <- {pair.narrative_element}")

    report = result.report
    status = "PASS" if report.passed else "FAIL"
    print(f"\n[Self-check] {status}")
    print(f"  hard leaks        : {list(report.hard_leaks) or 'none'}")
    print(f"  uncovered elements: {list(report.uncovered_elements) or 'none'}")


def main() -> None:
    pipeline = M2NAPipeline(MockLLMClient())
    requested = sys.argv[1:] or list(ALL_FIXTURES)

    for concept in requested:
        if concept not in ALL_FIXTURES:
            print(f"[skip] 未知概念: {concept!r} (可选: {list(ALL_FIXTURES)})")
            continue
        result = pipeline.run(ALL_FIXTURES[concept]())
        _print_result(result)


if __name__ == "__main__":
    main()
