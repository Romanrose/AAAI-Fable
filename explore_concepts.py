#!/usr/bin/env python3
"""第一部分数据摸底：从 K12-KGraph 筛出「机制富集」概念候选并打印。

用于人工肉眼核验筛选质量，决定后续 G_c 抽取的范围与 prompt。

用法:
    python explore_concepts.py                 # 各学科 Top 10 候选 + 统计
    python explore_concepts.py physics 20      # 指定学科 Top 20
"""

from __future__ import annotations

import sys

from src.m2na.data import (
    SUBJECTS,
    load_subject,
    rank_candidates,
)


def _print_subject(subject: str, top_n: int) -> None:
    records = load_subject(subject)
    candidates = rank_candidates(records)
    print(f"\n{'=' * 72}")
    print(
        f"{subject.upper()}  概念={len(records)}  机制候选={len(candidates)}  "
        f"(展示 Top {min(top_n, len(candidates))})"
    )
    print("=" * 72)
    for i, cand in enumerate(candidates[:top_n], 1):
        rec = cand.record
        print(f"\n{i:>2}. [{rec.name}]  score={cand.score}  signals={list(cand.signal_hits)}")
        print(f"    def: {rec.definition[:120]}")
        if rec.formula:
            print(f"    formula: {rec.formula[:80]}")
        if rec.aliases:
            print(f"    aliases: {list(rec.aliases)}")


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] in SUBJECTS:
        subjects = [args[0]]
        top_n = int(args[1]) if len(args) > 1 else 20
    else:
        subjects = list(SUBJECTS)
        top_n = int(args[0]) if args and args[0].isdigit() else 10

    for subject in subjects:
        _print_subject(subject, top_n)


if __name__ == "__main__":
    main()
