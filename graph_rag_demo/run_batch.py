"""Batch runner for retrieval and generation comparisons on K12 concepts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

from .analysis import (
    build_heuristic_mechanism_plan,
    compute_retrieval_analysis,
    mean_numeric,
    validate_mechanism_plan,
)
from .backends import BackendError
from .pipeline import PipelineError, run_demo
from .retrieval import (
    RETRIEVAL_MODES,
    RetrievalError,
    load_subject_graph,
    normalize,
    retrieve_subgraph,
)


DEFAULT_PILOT_CONCEPTS = [
    {"subject": "biology", "concept": "光合作用"},
    {"subject": "biology", "concept": "呼吸作用"},
    {"subject": "biology", "concept": "蒸腾作用"},
    {"subject": "biology", "concept": "细胞分裂"},
    {"subject": "biology", "concept": "生态系统"},
    {"subject": "physics", "concept": "浮力"},
    {"subject": "physics", "concept": "惯性"},
    {"subject": "physics", "concept": "压强"},
    {"subject": "physics", "concept": "欧姆定律"},
    {"subject": "physics", "concept": "能量守恒"},
]

DEFAULT_MODES = ["one_hop", "path_pruned", "dual_level", "path_dual"]

RETRIEVAL_TABLE_FIELDS = [
    "subject",
    "concept",
    "retrieval_mode",
    "status",
    "retrieval_edge_count",
    "candidate_edge_count",
    "retrieval_path_count",
    "avg_path_length",
    "max_path_length",
    "retrieval_context_chars",
    "raw_edge_chars",
    "path_chars",
    "summary_chars",
    "unused_raw_edge_ratio",
    "unused_selected_path_ratio",
    "non_mechanism_node_ratio",
    "grounding_edge_usage_rate",
    "mechanism_compression_ratio",
]

GENERATION_METRICS = [
    "node_coverage",
    "weighted_node_coverage",
    "edge_coverage",
    "weighted_edge_coverage",
    "alignment_precision",
    "alignment_hallucination_rate",
    "relation_direction_accuracy",
    "exact_concept_leakage",
    "soft_term_leakage",
    "template_hit_rate",
    "narrative_char_count",
]


def _load_concept_file(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            subject = value.get("subject")
            concept = value.get("concept")
            if not isinstance(subject, str) or not isinstance(concept, str):
                raise ValueError(
                    f"{path}:{line_number}: subject and concept must be strings"
                )
            records.append({"subject": subject, "concept": concept})
    if not records:
        raise ValueError(f"{path}: no concept records found")
    return records


def _slug(value: str) -> str:
    normalized = normalize(value)
    return normalized or "item"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_dir(output_dir: Path, item: dict[str, str], mode: str) -> Path:
    return output_dir / f"{item['subject']}_{_slug(item['concept'])}" / mode


def _retrieval_only_run(
    item: dict[str, str],
    mode: str,
    output_dir: Path,
    max_edges: int,
    max_hops: int,
    max_paths: int,
) -> dict[str, Any]:
    run_dir = _run_dir(output_dir, item, mode)
    graph = load_subject_graph(item["subject"])
    subgraph = retrieve_subgraph(
        graph,
        item["concept"],
        item["subject"],
        retrieval_mode=mode,
        max_edges=max_edges,
        max_hops=max_hops,
        max_paths=max_paths,
    )
    mechanism_plan = build_heuristic_mechanism_plan(subgraph)
    plan_errors = validate_mechanism_plan(mechanism_plan, subgraph)
    if plan_errors:
        raise PipelineError("; ".join(plan_errors))
    mechanism_bundle = {"mechanism_plan": mechanism_plan, "grounding": {}}
    retrieval_analysis = compute_retrieval_analysis(subgraph, mechanism_bundle)
    _write_json(run_dir / "01_retrieved_subgraph.json", subgraph)
    _write_json(run_dir / "02_mechanism_plan.json", mechanism_bundle)
    _write_json(run_dir / "retrieval_analysis.json", retrieval_analysis)
    return {
        "subject": item["subject"],
        "concept": item["concept"],
        "retrieval_mode": mode,
        "status": "ok",
        "output_dir": str(run_dir),
        "retrieval_analysis": retrieval_analysis,
        "generation_metrics": None,
    }


def _full_generation_run(
    item: dict[str, str],
    mode: str,
    output_dir: Path,
    backend: str,
    max_edges: int,
    max_hops: int,
    max_paths: int,
) -> dict[str, Any]:
    run_dir = _run_dir(output_dir, item, mode)
    report = run_demo(
        concept=item["concept"],
        subject=item["subject"],
        backend_name=backend,
        output_dir=run_dir,
        max_edges=max_edges,
        retrieval_mode=mode,
        max_hops=max_hops,
        max_paths=max_paths,
    )
    return {
        "subject": item["subject"],
        "concept": item["concept"],
        "retrieval_mode": mode,
        "status": "ok",
        "output_dir": str(run_dir),
        "retrieval_analysis": report["retrieval_only_metrics"],
        "generation_metrics": report["summary"],
        "generation_sample": report["samples"][0],
    }


def _failed_run(
    item: dict[str, str],
    mode: str,
    output_dir: Path,
    exc: Exception | str,
) -> dict[str, Any]:
    return {
        "subject": item["subject"],
        "concept": item["concept"],
        "retrieval_mode": mode,
        "status": "failed",
        "error": str(exc),
        "output_dir": str(_run_dir(output_dir, item, mode)),
        "retrieval_analysis": None,
        "generation_metrics": None,
    }


def _summary_by_mode(runs: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        value = run.get(key)
        if run.get("status") != "ok" or not isinstance(value, dict):
            continue
        grouped.setdefault(run["retrieval_mode"], []).append(value)
    return {mode: mean_numeric(values) for mode, values in sorted(grouped.items())}


def _concept_results(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "subject": run["subject"],
            "concept": run["concept"],
            "retrieval_mode": run["retrieval_mode"],
            "status": run["status"],
            "error": run.get("error", ""),
        }
        for run in runs
    ]


def _generation_summary_by_mode(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _summary_by_mode(runs, "generation_metrics")


def _write_jsonl(path: Path, runs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n" for run in runs),
        encoding="utf-8",
    )


def _write_csv(path: Path, runs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RETRIEVAL_TABLE_FIELDS)
        writer.writeheader()
        for run in runs:
            row = {
                "subject": run["subject"],
                "concept": run["concept"],
                "retrieval_mode": run["retrieval_mode"],
                "status": run["status"],
            }
            analysis = run.get("retrieval_analysis") or {}
            for field in RETRIEVAL_TABLE_FIELDS:
                row.setdefault(field, analysis.get(field, ""))
            writer.writerow(row)


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _metric_value(summary: dict[str, Any], key: str) -> Any:
    value = summary.get(key, "")
    if isinstance(value, float):
        return round(value, 4)
    return value


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    retrieval_rows = []
    for mode, summary in report["retrieval_summary_by_mode"].items():
        retrieval_rows.append(
            [
                mode,
                _metric_value(summary, "retrieval_edge_count"),
                _metric_value(summary, "retrieval_path_count"),
                _metric_value(summary, "unused_raw_edge_ratio"),
                _metric_value(summary, "unused_selected_path_ratio"),
                _metric_value(summary, "grounding_edge_usage_rate"),
            ]
        )

    generation_rows = []
    for mode, summary in report["generation_summary_by_mode"].items():
        generation_rows.append(
            [
                mode,
                _metric_value(summary, "node_coverage"),
                _metric_value(summary, "edge_coverage"),
                _metric_value(summary, "alignment_precision"),
                _metric_value(summary, "exact_concept_leakage"),
                _metric_value(summary, "soft_term_leakage"),
            ]
        )

    concept_rows = [
        [
            item["subject"],
            item["concept"],
            item["retrieval_mode"],
            item["status"],
            item.get("error", ""),
        ]
        for item in report["concept_results"]
    ]

    context_rows = []
    for mode, summary in report["retrieval_summary_by_mode"].items():
        context_rows.append(
            [
                mode,
                _metric_value(summary, "retrieval_context_chars"),
                _metric_value(summary, "raw_edge_chars"),
                _metric_value(summary, "path_chars"),
                _metric_value(summary, "summary_chars"),
                _metric_value(summary, "mechanism_compression_ratio"),
            ]
        )

    markdown = "\n\n".join(
        [
            "# Graph RAG Batch Report",
            "## Table 1. Retrieval Noise",
            _markdown_table(
                [
                    "mode",
                    "edges",
                    "paths",
                    "unused_edges",
                    "unused_paths",
                    "edge_usage",
                ],
                retrieval_rows,
            ),
            "## Table 2. Generation Metrics",
            _markdown_table(
                [
                    "mode",
                    "node_cov",
                    "edge_cov",
                    "align_prec",
                    "exact_leak",
                    "soft_leak",
                ],
                generation_rows,
            )
            if generation_rows
            else "_No generation metrics available for this run mode._",
            "## Table 3. Concept Runs",
            _markdown_table(
                ["subject", "concept", "mode", "status", "error"], concept_rows
            ),
            "## Table 4. Context And Compression",
            _markdown_table(
                [
                    "mode",
                    "context_chars",
                    "raw_edge_chars",
                    "path_chars",
                    "summary_chars",
                    "compression",
                ],
                context_rows,
            ),
        ]
    )
    path.write_text(markdown + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--concept-file",
        type=Path,
        help="optional JSONL file with {'subject': ..., 'concept': ...} rows",
    )
    parser.add_argument(
        "--run-mode",
        choices=("retrieval_only", "full_generation"),
        default="retrieval_only",
    )
    parser.add_argument(
        "--retrieval-mode",
        action="append",
        choices=tuple(sorted(RETRIEVAL_MODES)),
        dest="retrieval_modes",
        help="repeat to select modes; defaults to all planned modes",
    )
    parser.add_argument(
        "--backend",
        choices=("fixture", "deepseek"),
        default="deepseek",
        help="fixture only supports 光合作用; use deepseek for the 10-concept pilot",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("graph_rag_demo/output_batch"),
    )
    parser.add_argument("--max-edges", type=int, default=16)
    parser.add_argument("--max-hops", type=int, default=2)
    parser.add_argument("--max-paths", type=int, default=5)
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="fail fast instead of recording failed runs in the batch report",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        concepts = (
            _load_concept_file(args.concept_file)
            if args.concept_file
            else DEFAULT_PILOT_CONCEPTS
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    modes = args.retrieval_modes or DEFAULT_MODES
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    full_generation_blocked = (
        args.run_mode == "full_generation"
        and args.backend == "deepseek"
        and not os.getenv("DEEPSEEK_API_KEY")
    )

    for item in concepts:
        for mode in modes:
            try:
                if full_generation_blocked:
                    raise BackendError("DEEPSEEK_API_KEY is not configured")
                if args.run_mode == "retrieval_only":
                    run = _retrieval_only_run(
                        item,
                        mode,
                        args.output_dir,
                        args.max_edges,
                        args.max_hops,
                        args.max_paths,
                    )
                else:
                    run = _full_generation_run(
                        item,
                        mode,
                        args.output_dir,
                        args.backend,
                        args.max_edges,
                        args.max_hops,
                        args.max_paths,
                    )
            except (RetrievalError, BackendError, PipelineError, OSError) as exc:
                if args.stop_on_error:
                    print(f"error: {item} {mode}: {exc}", file=sys.stderr)
                    return 2
                run = _failed_run(item, mode, args.output_dir, exc)
            runs.append(run)

    failures = [run for run in runs if run["status"] == "failed"]
    report = {
        "run_metadata": {
            "run_mode": args.run_mode,
            "backend": args.backend,
            "concept_count": len(concepts),
            "retrieval_modes": modes,
            "run_count": len(runs),
            "ok_count": sum(1 for run in runs if run["status"] == "ok"),
            "failed_count": len(failures),
            "full_generation_blocked": full_generation_blocked,
        },
        "retrieval_summary_by_mode": _summary_by_mode(runs, "retrieval_analysis"),
        "generation_summary_by_mode": _generation_summary_by_mode(runs),
        "concept_results": _concept_results(runs),
        "failures": failures,
    }

    _write_json(args.output_dir / "batch_report.json", report)
    _write_jsonl(args.output_dir / "batch_runs.jsonl", runs)
    _write_csv(args.output_dir / "retrieval_table.csv", runs)
    _write_markdown(args.output_dir / "batch_report.md", report)
    print(
        json.dumps(
            {
                "output": str(args.output_dir / "batch_report.json"),
                "run_mode": args.run_mode,
                "ok_count": report["run_metadata"]["ok_count"],
                "failed_count": report["run_metadata"]["failed_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
