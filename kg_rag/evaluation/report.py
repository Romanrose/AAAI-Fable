from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from kg_rag.evaluation.rubric import DIMENSIONS, DIMENSION_NAMES_ZH


CSV_FIELDS = [
    "concept_id",
    "target_concept",
    "faithfulness",
    "implicitness",
    "mapping_clarity",
    "readability",
    "pedagogical_value",
    "novelty",
    "weighted_overall",
    "final_status",
    "hard_leakage",
    "concept_contradiction",
    "template_like",
]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            scores = row.get("scores", {})
            flags = row.get("hard_flags", {})
            writer.writerow(
                {
                    "concept_id": row.get("concept_id"),
                    "target_concept": row.get("target_concept"),
                    "faithfulness": scores.get("faithfulness"),
                    "implicitness": scores.get("implicitness"),
                    "mapping_clarity": scores.get("mapping_clarity"),
                    "readability": scores.get("readability"),
                    "pedagogical_value": scores.get("pedagogical_value"),
                    "novelty": scores.get("novelty"),
                    "weighted_overall": row.get("weighted_overall"),
                    "final_status": row.get("final_status"),
                    "hard_leakage": flags.get("hard_leakage"),
                    "concept_contradiction": flags.get("concept_contradiction"),
                    "template_like": flags.get("template_like"),
                }
            )


def write_markdown_report(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(
            "# \u516d\u7ef4\u5bd3\u8a00\u8bc4\u4f30\u62a5\u544a\n\n"
            "\u6ca1\u6709\u53ef\u6c47\u603b\u7684\u8bc4\u4f30\u7ed3\u679c\u3002\n",
            encoding="utf-8",
        )
        return

    status_counts = Counter(row.get("final_status", "unknown") for row in rows)
    dimension_means = {
        dimension: round(mean(row.get("scores", {}).get(dimension, 0) for row in rows), 2)
        for dimension in DIMENSIONS
    }
    overall_mean = round(mean(float(row.get("weighted_overall", 0)) for row in rows), 2)

    lines = [
        "# \u516d\u7ef4\u5bd3\u8a00\u8bc4\u4f30\u62a5\u544a",
        "",
        f"- \u6837\u672c\u6570\uff1a{len(rows)}",
        f"- \u52a0\u6743\u603b\u5206\u5747\u503c\uff1a{overall_mean}",
        f"- Accept\uff1a{status_counts.get('accept', 0)}",
        f"- Revise\uff1a{status_counts.get('revise', 0)}",
        f"- Reject\uff1a{status_counts.get('reject', 0)}",
        "",
        "## \u7ef4\u5ea6\u5747\u503c",
        "",
        "| \u7ef4\u5ea6 | \u5747\u503c |",
        "|---|---:|",
    ]
    for dimension in DIMENSIONS:
        lines.append(f"| {DIMENSION_NAMES_ZH[dimension]} `{dimension}` | {dimension_means[dimension]} |")

    lines.extend(
        [
            "",
            "## \u4f4e\u5206\u6216\u5931\u8d25\u6837\u672c",
            "",
            "| concept_id | final_status | weighted_overall | main_issue |",
            "|---|---|---:|---|",
        ]
    )
    for row in rows:
        if row.get("final_status") == "accept":
            continue
        flags = row.get("hard_flags", {})
        active_flags = [key for key, value in flags.items() if value]
        main_issue = ", ".join(active_flags) if active_flags else "score_threshold"
        lines.append(
            f"| {row.get('concept_id')} | {row.get('final_status')} | {row.get('weighted_overall')} | {main_issue} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_reports(summary_jsonl: Path, output_dir: Path | None = None) -> dict[str, str]:
    rows = load_jsonl(summary_jsonl)
    target_dir = output_dir or summary_jsonl.parent
    csv_path = target_dir / "eval_summary.csv"
    report_path = target_dir / "eval_report.md"
    write_csv(csv_path, rows)
    write_markdown_report(report_path, rows)
    result = {
        "summary_jsonl": str(summary_jsonl),
        "csv_path": str(csv_path),
        "report_path": str(report_path),
        "row_count": str(len(rows)),
    }
    subject_paths = write_subject_reports(target_dir, rows)
    result.update(subject_paths)
    return result


def _subject_from_row(row: dict[str, Any]) -> str:
    concept_id = str(row.get("concept_id", "unknown"))
    return concept_id.split("_", 1)[0] if "_" in concept_id else "unknown"


def write_subject_reports(output_dir: Path, rows: list[dict[str, Any]]) -> dict[str, str]:
    if not rows:
        return {}
    subjects = sorted({_subject_from_row(row) for row in rows})
    result: dict[str, str] = {}
    index_lines = [
        "# Subject Evaluation Reports",
        "",
        "| subject | samples | report |",
        "|---|---:|---|",
    ]
    for subject in subjects:
        subject_rows = [row for row in rows if _subject_from_row(row) == subject]
        report_path = output_dir / f"{subject}_eval_report.md"
        write_markdown_report(report_path, subject_rows)
        result[f"{subject}_report_path"] = str(report_path)
        index_lines.append(f"| {subject} | {len(subject_rows)} | {report_path.name} |")
    subject_index_path = output_dir / "subject_eval_report.md"
    subject_index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    result["subject_eval_report_path"] = str(subject_index_path)
    return result
