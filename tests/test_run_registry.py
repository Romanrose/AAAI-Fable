from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kg_rag.pipeline.run_registry import auto_concept_run_dir, build_run_name


def test_build_run_name_uses_timestamp_mode_count_and_eval_mode() -> None:
    now = datetime(2026, 7, 5, 17, 30, 0)

    assert build_run_name(mode="local", limit=20, evaluate_mode="rules", now=now) == "20260705_173000_local_20_rules"


def test_auto_concept_run_dir_uses_runs_root() -> None:
    now = datetime(2026, 7, 5, 17, 30, 0)
    run_dir = auto_concept_run_dir(
        mode="llm",
        limit=None,
        evaluate_mode="llm",
        runs_root=Path("runs"),
        now=now,
    )

    assert run_dir == Path("runs") / "20260705_173000_llm_all_llm"
