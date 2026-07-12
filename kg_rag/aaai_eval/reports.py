from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from kg_rag.aaai_eval.schemas import load_protocol
from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.io import write_json


REPORT_VERSION = "aaai-eval-report/v1"


def build_reports(*, protocol_path: Path) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    records_path = protocol.output_root / "evaluation_records.jsonl"
    if not records_path.exists():
        raise ValueError("evaluation_records.jsonl is missing; run evaluate first")
    records = read_jsonl(records_path)
    method_order = [method.method_id for method in protocol.methods]
    display_names = {method.method_id: method.display_name for method in protocol.methods}
    main_rows = [
        _aggregate(method_id, display_names[method_id], [r for r in records if r["method_id"] == method_id])
        for method_id in method_order
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(str(record["method_id"]), str(record["subject"]))].append(record)
    subject_rows = [
        {
            "subject": subject,
            **_aggregate(method_id, display_names[method_id], subset),
        }
        for (method_id, subject), subset in sorted(
            grouped.items(), key=lambda item: (method_order.index(item[0][0]), item[0][1])
        )
    ]
    report_root = protocol.output_root / "reports"
    report_root.mkdir(parents=True, exist_ok=True)
    _write_csv(report_root / "main_results.csv", main_rows)
    _write_csv(report_root / "results_by_subject.csv", subject_rows)
    markdown = _main_markdown(main_rows)
    (report_root / "main_results.md").write_text(markdown, encoding="utf-8")
    result = {
        "report_version": REPORT_VERSION,
        "experiment_id": protocol.experiment_id,
        "record_count": len(records),
        "main_results": main_rows,
        "by_subject": subject_rows,
        "main_csv": str((report_root / "main_results.csv").resolve()),
        "subject_csv": str((report_root / "results_by_subject.csv").resolve()),
        "main_markdown": str((report_root / "main_results.md").resolve()),
    }
    write_json(report_root / "report.json", result)
    return result


def _aggregate(method_id: str, display_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if row.get("generation_status") == "success"]
    return {
        "method_id": method_id,
        "method": display_name,
        "concepts": len({str(row["concept_id"]) for row in rows}),
        "candidates": len(rows),
        "success_rate": _ratio(len(successful), len(rows)),
        "accept_rate": _ratio(sum(row.get("evaluation_status") == "accept" for row in rows), len(rows)),
        "node_coverage": _mean(rows, "node_coverage"),
        "edge_coverage": _mean(rows, "edge_coverage"),
        "direction_accuracy": _mean(rows, "direction_accuracy"),
        "exact_evidence_precision": _mean(rows, "exact_evidence_precision"),
        "system_exact_match_rate": _ratio(sum(_system_exact(row) for row in rows), len(rows)),
        "leakage_count": sum(bool(row.get("metrics", {}).get("hard_leakage")) for row in rows),
        "length_violation_count": sum(not bool(row.get("metrics", {}).get("length_valid")) for row in rows),
        "revision_improved_count": sum(bool(row.get("revision_improved")) for row in rows),
    }


def _system_exact(row: dict[str, Any]) -> bool:
    metrics = row.get("metrics", {})
    return (
        float(metrics.get("node_coverage") or 0.0) == 1.0
        and float(metrics.get("edge_coverage") or 0.0) == 1.0
        and float(metrics.get("direction_accuracy") or 0.0) == 1.0
        and not metrics.get("hard_leakage")
        and bool(metrics.get("length_valid"))
    )


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(float(row.get("metrics", {}).get(key) or 0.0) for row in rows) / len(rows), 4)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _main_markdown(rows: list[dict[str, Any]]) -> str:
    headers = [
        "Method",
        "Success",
        "Accept",
        "Node Cov.",
        "Edge Cov.",
        "Direction",
        "Exact Match",
        "Leakage",
        "Length Viol.",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["method"]),
                    _pct(row["success_rate"]),
                    _pct(row["accept_rate"]),
                    _pct(row["node_coverage"]),
                    _pct(row["edge_coverage"]),
                    _pct(row["direction_accuracy"]),
                    _pct(row["system_exact_match_rate"]),
                    str(row["leakage_count"]),
                    str(row["length_violation_count"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _pct(value: Any) -> str:
    return f"{100.0 * float(value):.2f}%"
