from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from kg_rag.paths import DEFAULT_KG_RAG_DERIVED_DIR


DEFAULT_CONCEPT_RUNS_DIR = DEFAULT_KG_RAG_DERIVED_DIR / "concept_runs"
RUNS_INDEX_PATH = DEFAULT_CONCEPT_RUNS_DIR / "runs_index.jsonl"


def build_run_name(
    *,
    mode: str,
    limit: int | None,
    evaluate_mode: str,
    now: datetime | None = None,
) -> str:
    current = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    count = str(limit) if limit is not None else "all"
    return f"{current:%Y%m%d_%H%M%S}_{mode}_{count}_{evaluate_mode}"


def auto_concept_run_dir(
    *,
    mode: str,
    limit: int | None,
    evaluate_mode: str,
    runs_root: Path = DEFAULT_CONCEPT_RUNS_DIR,
    now: datetime | None = None,
) -> Path:
    return runs_root / build_run_name(mode=mode, limit=limit, evaluate_mode=evaluate_mode, now=now)


def append_run_index(
    *,
    result: dict[str, Any],
    manifest: dict[str, Any],
    index_path: Path = RUNS_INDEX_PATH,
) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "recorded_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "output_dir": result.get("output_dir"),
        "mode": result.get("mode"),
        "language": result.get("language"),
        "evaluate_mode": manifest.get("evaluate_mode"),
        "concept_count": result.get("concept_count"),
        "success_count": result.get("success_count"),
        "failed_count": result.get("failed_count"),
        "skipped_count": result.get("skipped_count"),
        "summary_path": result.get("summary_path"),
        "eval_summary_path": result.get("eval_summary_path"),
        "csv_path": result.get("csv_path"),
        "report_path": result.get("report_path"),
        "analysis_chart_path": result.get("analysis_chart_path"),
    }
    with index_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
