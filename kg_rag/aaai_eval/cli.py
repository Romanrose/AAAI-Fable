from __future__ import annotations

import argparse
import json
from pathlib import Path

from kg_rag.aaai_eval.datasets import build_dataset_manifests
from kg_rag.aaai_eval.protocols import initialize_story_pilot_protocol
from kg_rag.aaai_eval.pipeline_reports import build_pipeline_reports
from kg_rag.aaai_eval.registry import default_registry
from kg_rag.aaai_eval.reports import build_reports
from kg_rag.aaai_eval.runner import run_evaluation
from kg_rag.paths import DEFAULT_DERIVED_DIR


DEFAULT_EVAL_ROOT = DEFAULT_DERIVED_DIR / "kg_rag" / "aaai_eval"
DEFAULT_PREPARATION_ROOT = DEFAULT_DERIVED_DIR / "kg_rag" / "m2na_v2" / "pilot80"
DEFAULT_STORY_PILOT_ROOT = DEFAULT_DERIVED_DIR / "kg_rag" / "story_pilot12"
DEFAULT_PAPER_TABLE_ROOT = Path(__file__).resolve().parent / "paper_tables"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m kg_rag.aaai_eval",
        description="Extensible evaluation framework for M2NA AAAI experiments.",
    )
    subparsers = parser.add_subparsers(dest="command")

    datasets = subparsers.add_parser("build-datasets", help="Build reproducible Core/Human dataset manifests.")
    datasets.add_argument("--seeds", type=Path, default=DEFAULT_PREPARATION_ROOT / "seeds.jsonl")
    datasets.add_argument("--output-root", type=Path, default=DEFAULT_EVAL_ROOT / "datasets")
    datasets.add_argument("--core-per-subject", type=int, default=20)
    datasets.add_argument("--human-per-subject", type=int, default=8)
    datasets.add_argument("--sampling-seed", default="aaai-eval-v1")

    init_pilot = subparsers.add_parser(
        "init-story-pilot",
        help="Create a protocol that imports the existing three-strategy Story Pilot.",
    )
    init_pilot.add_argument("--pilot-root", type=Path, default=DEFAULT_STORY_PILOT_ROOT)
    init_pilot.add_argument(
        "--protocol",
        type=Path,
        default=DEFAULT_EVAL_ROOT / "story_pilot12" / "protocol.json",
    )
    init_pilot.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_EVAL_ROOT / "story_pilot12" / "run",
    )
    init_pilot.add_argument("--candidate-count", type=int, default=3)

    evaluate = subparsers.add_parser("evaluate", help="Run all methods declared in a frozen protocol.")
    evaluate.add_argument("--protocol", type=Path, required=True)

    report = subparsers.add_parser("report", help="Generate method and subject result tables.")
    report.add_argument("--protocol", type=Path, required=True)

    pipeline_report = subparsers.add_parser(
        "report-pipeline",
        help="Generate the ordered mechanism, mapping, story, and ablation report sections.",
    )
    pipeline_report.add_argument(
        "--preparation-root", type=Path, default=DEFAULT_PREPARATION_ROOT
    )
    pipeline_report.add_argument(
        "--story-protocol",
        type=Path,
        default=DEFAULT_EVAL_ROOT / "story_pilot12" / "protocol.json",
    )
    pipeline_report.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_PAPER_TABLE_ROOT,
        help="Directory for the four paper tables and the consolidated manifest.",
    )

    subparsers.add_parser("list-adapters", help="List installed method adapter types.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build-datasets":
        result = build_dataset_manifests(
            seeds_path=args.seeds,
            output_root=args.output_root,
            core_per_subject=args.core_per_subject,
            human_per_subject=args.human_per_subject,
            sampling_seed=args.sampling_seed,
        )
    elif args.command == "init-story-pilot":
        result = initialize_story_pilot_protocol(
            pilot_root=args.pilot_root,
            output_root=args.output_root,
            protocol_path=args.protocol,
            candidate_count=args.candidate_count,
        )
    elif args.command == "evaluate":
        result = run_evaluation(protocol_path=args.protocol)
    elif args.command == "report":
        result = build_reports(protocol_path=args.protocol)
    elif args.command == "report-pipeline":
        result = build_pipeline_reports(
            preparation_root=args.preparation_root,
            story_protocol_path=args.story_protocol,
            output_root=args.output_root,
        )
    elif args.command == "list-adapters":
        result = {"adapters": default_registry().adapter_ids()}
    else:
        parser.print_help()
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
