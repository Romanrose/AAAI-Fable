from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import write_jsonl
from kg_rag.io import write_json
from kg_rag.multi_agent.metrics import aggregate


CSV_FIELDS = [
    "concept_id",
    "subject",
    "strategy",
    "generation_status",
    "fallback_count",
    "revision_attempted_rounds",
    "evaluation_status",
    "selected_candidate_id",
    "selection_mode",
    "selected_score",
    "selected_temperature",
    "weighted_overall",
    "six_dim_mode",
    "format_validity",
    "exact_concept_leakage",
    "soft_term_leakage",
    "weighted_node_coverage",
    "weighted_edge_coverage",
    "alignment_precision",
    "alignment_hallucination_rate",
    "relation_direction_accuracy",
    "concept_relation_coverage",
    "typed_relation_preservation",
    "template_hit_rate",
    "narrative_char_count",
]


def export_run_reports(
    *,
    output_dir: Path,
    records: list[dict[str, Any]],
    metric_rows: list[dict[str, Any]],
    six_dim_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    failed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    records_path = output_dir / "records.jsonl"
    summary_path = output_dir / "summary.jsonl"
    metrics_jsonl_path = output_dir / "automatic_metrics.jsonl"
    six_dim_path = output_dir / "six_dim_eval_summary.jsonl"
    failed_path = output_dir / "failed_queue.jsonl"
    csv_path = output_dir / "automatic_metrics.csv"
    report_path = output_dir / "eval_report.md"
    metrics_json_path = output_dir / "automatic_metrics.json"

    write_jsonl(records_path, records)
    write_jsonl(summary_path, summary_rows)
    write_jsonl(metrics_jsonl_path, metric_rows)
    write_jsonl(six_dim_path, six_dim_rows)
    write_jsonl(failed_path, failed_rows)
    _write_csv(csv_path, summary_rows)

    metrics_report = {
        "summary": aggregate(metric_rows) if metric_rows else {"sample_count": 0},
        "samples": metric_rows,
    }
    write_json(metrics_json_path, metrics_report)
    report_path.write_text(
        build_markdown_report(
            summary=metrics_report["summary"],
            summary_rows=summary_rows,
            failed_rows=failed_rows,
        ),
        encoding="utf-8",
    )
    return {
        "records_path": str(records_path),
        "summary_path": str(summary_path),
        "automatic_metrics_path": str(metrics_json_path),
        "automatic_metrics_jsonl_path": str(metrics_jsonl_path),
        "six_dim_eval_summary_path": str(six_dim_path),
        "failed_queue_path": str(failed_path),
        "csv_path": str(csv_path),
        "report_path": str(report_path),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_markdown_report(
    *,
    summary: dict[str, Any],
    summary_rows: list[dict[str, Any]],
    failed_rows: list[dict[str, Any]],
) -> str:
    status_counts: dict[str, int] = {}
    for row in summary_rows:
        status = str(row.get("evaluation_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [
        "# 多 Agent 概念寓言生成评估报告",
        "",
        "## 总览",
        "",
        f"- 样本数：{summary.get('sample_count', 0)}",
        f"- 失败数：{len(failed_rows)}",
        f"- 状态分布：{status_counts}",
        "",
        "## 自动指标均值",
        "",
    ]
    for key, value in summary.items():
        if key == "sample_count":
            continue
        if isinstance(value, float):
            lines.append(f"- `{key}`: {value:.4f}")
        else:
            lines.append(f"- `{key}`: {value}")

    if failed_rows:
        lines.extend(["", "## 失败样本", ""])
        for row in failed_rows[:20]:
            lines.append(f"- `{row.get('concept_id')}`: {row.get('error')}")
    return "\n".join(lines) + "\n"
