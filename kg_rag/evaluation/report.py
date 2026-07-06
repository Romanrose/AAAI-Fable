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

    chart_path = path.with_name("eval_analysis.svg")
    lines = [
        "# \u516d\u7ef4\u5bd3\u8a00\u8bc4\u4f30\u62a5\u544a",
        "",
        f"- \u6837\u672c\u6570\uff1a{len(rows)}",
        f"- \u52a0\u6743\u603b\u5206\u5747\u503c\uff1a{overall_mean}",
        f"- Accept\uff1a{status_counts.get('accept', 0)}",
        f"- Revise\uff1a{status_counts.get('revise', 0)}",
        f"- Reject\uff1a{status_counts.get('reject', 0)}",
        f"- \u5206\u6790\u56fe\uff1a[{chart_path.name}]({chart_path.name})",
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


def _svg_text(x: int, y: int, text: str, *, size: int = 14, anchor: str = "start", weight: str = "400") -> str:
    escaped = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#17202a">{escaped}</text>'
    )


def write_analysis_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1040
    height = 640
    margin_left = 78
    chart_top = 104
    chart_width = 560
    chart_height = 300
    status_left = 720
    status_top = 116
    max_score = 5

    if rows:
        dimension_means = {
            dimension: round(mean(row.get("scores", {}).get(dimension, 0) for row in rows), 2)
            for dimension in DIMENSIONS
        }
        status_counts = Counter(row.get("final_status", "unknown") for row in rows)
        overall_mean = round(mean(float(row.get("weighted_overall", 0)) for row in rows), 2)
        leakage_rate = round(
            sum(1 for row in rows if row.get("hard_flags", {}).get("hard_leakage")) / len(rows) * 100,
            1,
        )
        template_rate = round(
            sum(1 for row in rows if row.get("hard_flags", {}).get("template_like")) / len(rows) * 100,
            1,
        )
    else:
        dimension_means = {dimension: 0 for dimension in DIMENSIONS}
        status_counts = Counter()
        overall_mean = 0
        leakage_rate = 0
        template_rate = 0

    palette = {
        "faithfulness": "#2563eb",
        "implicitness": "#16a34a",
        "mapping_clarity": "#7c3aed",
        "readability": "#0891b2",
        "pedagogical_value": "#ea580c",
        "novelty": "#db2777",
        "accept": "#16a34a",
        "revise": "#f59e0b",
        "reject": "#dc2626",
        "unknown": "#64748b",
    }
    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="1040" height="640" fill="#f8fafc"/>',
        '<rect x="28" y="24" width="984" height="592" rx="8" fill="#ffffff" stroke="#d8dee9"/>',
        _svg_text(52, 64, "Machine Evaluation Summary", size=24, weight="700"),
        _svg_text(52, 90, f"samples={len(rows)}  weighted_overall_mean={overall_mean}", size=14),
        _svg_text(margin_left, chart_top - 24, "Six-Dimension Mean Scores", size=17, weight="700"),
    ]

    # Y-axis guide lines for the 1-5 score range.
    for score in range(1, max_score + 1):
        y = chart_top + chart_height - int(score / max_score * chart_height)
        svg.append(f'<line x1="{margin_left}" y1="{y}" x2="{margin_left + chart_width}" y2="{y}" stroke="#e5e7eb"/>')
        svg.append(_svg_text(margin_left - 14, y + 5, str(score), size=12, anchor="end"))
    svg.append(f'<line x1="{margin_left}" y1="{chart_top}" x2="{margin_left}" y2="{chart_top + chart_height}" stroke="#94a3b8"/>')
    svg.append(
        f'<line x1="{margin_left}" y1="{chart_top + chart_height}" x2="{margin_left + chart_width}" y2="{chart_top + chart_height}" stroke="#94a3b8"/>'
    )

    bar_gap = 18
    bar_width = int((chart_width - bar_gap * (len(DIMENSIONS) + 1)) / len(DIMENSIONS))
    for index, dimension in enumerate(DIMENSIONS):
        value = float(dimension_means[dimension])
        bar_height = int(value / max_score * chart_height)
        x = margin_left + bar_gap + index * (bar_width + bar_gap)
        y = chart_top + chart_height - bar_height
        svg.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" rx="4" fill="{palette[dimension]}"/>'
        )
        svg.append(_svg_text(x + bar_width // 2, y - 8, f"{value:.2f}", size=12, anchor="middle", weight="700"))
        label = DIMENSION_NAMES_ZH[dimension]
        svg.append(_svg_text(x + bar_width // 2, chart_top + chart_height + 24, label, size=12, anchor="middle"))
        svg.append(_svg_text(x + bar_width // 2, chart_top + chart_height + 42, dimension, size=10, anchor="middle"))

    svg.append(_svg_text(status_left, chart_top - 24, "Final Status Counts", size=17, weight="700"))
    status_total = max(sum(status_counts.values()), 1)
    status_y = status_top
    for status in ("accept", "revise", "reject", "unknown"):
        count = status_counts.get(status, 0)
        if count == 0 and status == "unknown":
            continue
        width_px = int(220 * count / status_total)
        svg.append(f'<rect x="{status_left}" y="{status_y}" width="220" height="26" rx="4" fill="#e5e7eb"/>')
        svg.append(
            f'<rect x="{status_left}" y="{status_y}" width="{width_px}" height="26" rx="4" fill="{palette[status]}"/>'
        )
        svg.append(_svg_text(status_left, status_y - 7, status, size=13, weight="700"))
        svg.append(_svg_text(status_left + 236, status_y + 19, str(count), size=14, weight="700"))
        status_y += 68

    svg.extend(
        [
            _svg_text(720, 410, "Risk Rates", size=17, weight="700"),
            _svg_text(720, 442, f"hard leakage rate: {leakage_rate}%", size=14),
            _svg_text(720, 470, f"template-like rate: {template_rate}%", size=14),
            _svg_text(52, 568, "Decision rule: reject on hard leakage, contradiction, unmapped core mechanism, or low faithfulness/mapping.", size=13),
            "</svg>",
        ]
    )
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def export_reports(summary_jsonl: Path, output_dir: Path | None = None) -> dict[str, str]:
    rows = load_jsonl(summary_jsonl)
    target_dir = output_dir or summary_jsonl.parent
    csv_path = target_dir / "eval_summary.csv"
    report_path = target_dir / "eval_report.md"
    chart_path = target_dir / "eval_analysis.svg"
    write_csv(csv_path, rows)
    write_markdown_report(report_path, rows)
    write_analysis_svg(chart_path, rows)
    result = {
        "summary_jsonl": str(summary_jsonl),
        "csv_path": str(csv_path),
        "report_path": str(report_path),
        "analysis_chart_path": str(chart_path),
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


def verify_eval_run(run_dir: Path, *, expected_count: int | None = None) -> dict[str, Any]:
    required_files = [
        "summary.jsonl",
        "eval_summary.jsonl",
        "eval_summary.csv",
        "eval_report.md",
        "eval_analysis.svg",
    ]
    missing_files = [name for name in required_files if not (run_dir / name).exists()]

    summary_rows = load_jsonl(run_dir / "summary.jsonl") if (run_dir / "summary.jsonl").exists() else []
    eval_rows = load_jsonl(run_dir / "eval_summary.jsonl") if (run_dir / "eval_summary.jsonl").exists() else []
    expected = expected_count if expected_count is not None else len(eval_rows)

    concepts_dir = run_dir / "concepts"
    concept_dirs = sorted(path for path in concepts_dir.iterdir() if path.is_dir()) if concepts_dir.exists() else []
    missing_concept_outputs: list[dict[str, Any]] = []
    for concept_dir in concept_dirs:
        missing = [
            name
            for name in (
                "concept_card.json",
                "subgraph_pack.json",
                "structure_plan.json",
                "story_prompt.txt",
                "draft_story.txt",
                "six_dim_eval.json",
                "status.json",
            )
            if not (concept_dir / name).exists()
        ]
        if missing:
            missing_concept_outputs.append({"concept_dir": str(concept_dir), "missing": missing})

    failures = [
        row
        for row in summary_rows
        if str(row.get("status")) == "failed" or str(row.get("generation_status")) == "failed"
    ]
    row_count_ok = len(eval_rows) == expected and len(summary_rows) == expected
    concept_count_ok = len(concept_dirs) == expected
    ok = not missing_files and row_count_ok and concept_count_ok and not missing_concept_outputs and not failures

    return {
        "ok": ok,
        "run_dir": str(run_dir),
        "expected_count": expected,
        "summary_count": len(summary_rows),
        "eval_count": len(eval_rows),
        "concept_dir_count": len(concept_dirs),
        "missing_files": missing_files,
        "missing_concept_outputs": missing_concept_outputs,
        "failed_rows": failures,
    }
