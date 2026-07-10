from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from kg_rag.llm_config import LLMConfig
from kg_rag.multi_agent.pipeline import MultiAgentOptions, evaluate_existing_run, run_batch, run_one
from kg_rag.paths import DEFAULT_DERIVED_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m kg_rag.multi_agent",
        description="XZT-based multi-agent Chinese concept-to-fable pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_one_parser = subparsers.add_parser("run-one", help="Run one concept card.")
    run_one_parser.add_argument("--concept-card", type=Path, required=True)
    run_one_parser.add_argument(
        "--normalized-graph",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
    )
    run_one_parser.add_argument("--output-dir", type=Path, required=True)
    add_common_options(run_one_parser)

    run_batch_parser = subparsers.add_parser("run-batch", help="Run a concept-card batch.")
    run_batch_parser.add_argument("--concept-cards", type=Path, required=True)
    run_batch_parser.add_argument(
        "--normalized-graph",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
    )
    run_batch_parser.add_argument("--output-dir", type=Path, required=True)
    run_batch_parser.add_argument("--subjects", default=None)
    run_batch_parser.add_argument("--priority", default=None)
    run_batch_parser.add_argument("--limit-per-subject", type=int, default=None)
    run_batch_parser.add_argument("--limit", type=int, default=None)
    run_batch_parser.add_argument("--offset", type=int, default=0)
    run_batch_parser.add_argument("--sleep-seconds", type=float, default=0.0)
    add_common_options(run_batch_parser)

    eval_parser = subparsers.add_parser(
        "evaluate-six-dim",
        help="Run rules or LLM six-dimensional evaluation for an existing run directory.",
    )
    eval_parser.add_argument("--run-dir", type=Path, required=True)
    eval_parser.add_argument("--mode", choices=("rules", "llm"), default="llm")
    eval_parser.add_argument("--judge-model", default=None)
    eval_parser.add_argument("--no-resume", action="store_true")

    return parser


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--language", choices=("zh-CN",), default="zh-CN")
    parser.add_argument(
        "--strategy",
        choices=("standard", "copycat"),
        default="standard",
        help="Use the current multi-agent pipeline or the Copycat-inspired structure-mapping strategy.",
    )
    parser.add_argument("--provider", choices=("deepseek",), default="deepseek")
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Optional independent model name for six-dimensional judging.",
    )
    parser.add_argument("--max-edges", type=int, default=16)
    parser.add_argument("--num-plans", type=int, default=3)
    parser.add_argument("--revision-rounds", type=int, default=1)
    parser.add_argument("--copycat-steps", type=int, default=30)
    parser.add_argument("--copycat-initial-candidates", type=int, default=3)
    parser.add_argument("--copycat-temperature-threshold", type=float, default=35.0)
    parser.add_argument(
        "--six-dim-mode",
        choices=("rules", "llm"),
        default="rules",
        help="Use deterministic rule projection or a real LLM judge for six-dimensional evaluation.",
    )
    parser.add_argument("--no-resume", action="store_true")


def _options(args: argparse.Namespace) -> MultiAgentOptions:
    return MultiAgentOptions(
        language=args.language,
        strategy=args.strategy,
        subjects=getattr(args, "subjects", None),
        priority=getattr(args, "priority", None),
        limit_per_subject=getattr(args, "limit_per_subject", None),
        limit=getattr(args, "limit", None),
        offset=getattr(args, "offset", 0),
        max_edges=args.max_edges,
        num_plans=args.num_plans,
        revision_rounds=args.revision_rounds,
        six_dim_mode=args.six_dim_mode,
        resume=not args.no_resume,
        sleep_seconds=getattr(args, "sleep_seconds", 0.0),
        copycat_steps=args.copycat_steps,
        copycat_initial_candidates=args.copycat_initial_candidates,
        copycat_temperature_threshold=args.copycat_temperature_threshold,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run-one":
        config = LLMConfig.from_env()
        result = run_one(
            concept_card_path=args.concept_card,
            normalized_graph_path=args.normalized_graph,
            output_dir=args.output_dir,
            options=_options(args),
            config=config,
            judge_config=replace(config, model=args.judge_model) if args.judge_model else None,
        )
        print(f"concept_dir={result['concept_dir']}")
        print(f"evaluation_status={result['status']['evaluation_status']}")
        print(f"weighted_overall={result['status']['weighted_overall']}")
        return 0
    if args.command == "run-batch":
        config = LLMConfig.from_env()
        result = run_batch(
            concept_cards_path=args.concept_cards,
            normalized_graph_path=args.normalized_graph,
            output_dir=args.output_dir,
            options=_options(args),
            config=config,
            judge_config=replace(config, model=args.judge_model) if args.judge_model else None,
        )
        print(f"records_path={result['records_path']}")
        print(f"summary_path={result['summary_path']}")
        print(f"automatic_metrics_path={result['automatic_metrics_path']}")
        print(f"report_path={result['report_path']}")
        print(f"concept_count={result['concept_count']}")
        print(f"success_count={result['success_count']}")
        print(f"failed_count={result['failed_count']}")
        print(f"fallback_concept_count={result['fallback_concept_count']}")
        return 0
    if args.command == "evaluate-six-dim":
        judge_config = None
        if args.mode == "llm":
            judge_config = LLMConfig.from_env()
            if args.judge_model:
                judge_config = replace(judge_config, model=args.judge_model)
        result = evaluate_existing_run(
            run_dir=args.run_dir,
            six_dim_mode=args.mode,
            config=judge_config,
            resume=not args.no_resume,
        )
        print(f"six_dim_eval_summary_path={result['six_dim_eval_summary_path']}")
        print(f"summary_path={result['summary_path']}")
        print(f"report_path={result['report_path']}")
        print(f"evaluated_count={result['evaluated_count']}")
        print(f"failed_count={result['failed_count']}")
        return 0

    parser.print_help()
    return 0
