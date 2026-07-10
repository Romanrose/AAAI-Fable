from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from kg_rag.llm_config import LLMConfig
from kg_rag.m2na_v2.mapping import build_mapping_plans
from kg_rag.m2na_v2.preparation import build_mechanisms, build_seeds, retrieve_packages, validate_mechanisms
from kg_rag.m2na_v2.reviews import export_review_sheet, import_reviews, pipeline_status
from kg_rag.m2na_v2.runner import ExperimentOptions, run_experiment
from kg_rag.multi_agent.llm import DeepSeekLLM
from kg_rag.paths import DEFAULT_DERIVED_DIR


DEFAULT_ROOT = DEFAULT_DERIVED_DIR / "kg_rag" / "m2na_v2" / "pilot80"
DEFAULT_GRAPH = DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m kg_rag.m2na_v2",
        description="Independent mechanism-first M2NA V2 experiment pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command")

    seeds = subparsers.add_parser("build-seeds", help="Build the frozen 80-concept ConceptSeed dataset.")
    seeds.add_argument("--normalized-graph", type=Path, default=DEFAULT_GRAPH)
    seeds.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)

    retrieve = subparsers.add_parser("retrieve", help="Build one GraphRAG RetrievalPackage per seed.")
    retrieve.add_argument("--normalized-graph", type=Path, default=DEFAULT_GRAPH)
    retrieve.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    retrieve.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    retrieve.add_argument("--max-edges", type=int, default=20)
    retrieve.add_argument("--max-paths", type=int, default=8)

    mechanisms = subparsers.add_parser("build-mechanisms", help="Extract evidence-grounded mechanisms with an LLM.")
    mechanisms.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    mechanisms.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    mechanisms.add_argument("--builder-model", default=None)
    mechanisms.add_argument("--limit", type=int, default=None)
    mechanisms.add_argument("--only-invalid", action="store_true", help="Retry only invalid, missing, or failed mechanism records.")

    validate = subparsers.add_parser("validate-mechanisms", help="Re-run strict mechanism validation.")
    validate.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    validate.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)

    export_review = subparsers.add_parser("export-review-sheet", help="Export the human mechanism review CSV.")
    export_review.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    export_review.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    export_review.add_argument("--output", type=Path, default=DEFAULT_ROOT / "mechanism_review.csv")

    import_review = subparsers.add_parser("import-reviews", help="Import append-only human review decisions.")
    import_review.add_argument("--input", type=Path, default=DEFAULT_ROOT / "mechanism_review.csv")
    import_review.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    import_review.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    import_review.add_argument("--reviewer", default=None)

    mappings = subparsers.add_parser("build-mappings", help="Build traceable Standard and Copycat mapping plans.")
    mappings.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    mappings.add_argument("--preparation-root", type=Path, default=DEFAULT_ROOT)
    mappings.add_argument("--output-root", type=Path, default=DEFAULT_ROOT / "mapping_plans")
    mappings.add_argument("--standard-model", default=None)
    mappings.add_argument("--only-missing", action="store_true", help="Resume by skipping complete, validated plan pairs.")

    run = subparsers.add_parser("run-experiment", help="Run the approved dataset through fair dual strategies.")
    run.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    run.add_argument("--preparation-root", type=Path, default=DEFAULT_ROOT)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--strategy", choices=("both", "standard", "copycat"), default="both")
    run.add_argument("--generator-model", default=None)
    run.add_argument("--judge-model", default=None)
    run.add_argument("--six-dim-mode", choices=("rules", "llm"), default="llm")

    status = subparsers.add_parser("status", help="Report V2 preparation and review counts.")
    status.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    status.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)

    serve_review = subparsers.add_parser("serve-review", help="Serve the local browser-based mechanism review app.")
    serve_review.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    serve_review.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    serve_review.add_argument("--host", default="127.0.0.1")
    serve_review.add_argument("--port", type=int, default=8765)

    serve_mapping_review = subparsers.add_parser(
        "serve-mapping-review",
        help="Serve the local browser-based Standard/Copycat mapping-plan review app.",
    )
    serve_mapping_review.add_argument("--mapping-root", type=Path, default=DEFAULT_ROOT / "mapping_plans")
    serve_mapping_review.add_argument("--seeds", type=Path, default=DEFAULT_ROOT / "seeds.jsonl")
    serve_mapping_review.add_argument("--host", default="127.0.0.1")
    serve_mapping_review.add_argument("--port", type=int, default=8767)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build-seeds":
        result = build_seeds(normalized_graph_path=args.normalized_graph, output_root=args.output_root)
    elif args.command == "retrieve":
        result = retrieve_packages(
            normalized_graph_path=args.normalized_graph,
            seeds_path=args.seeds,
            output_root=args.output_root,
            max_edges=args.max_edges,
            max_paths=args.max_paths,
        )
    elif args.command == "build-mechanisms":
        config = LLMConfig.from_env()
        if args.builder_model:
            config = replace(config, model=args.builder_model)
        llm = DeepSeekLLM(config)
        result = build_mechanisms(
            seeds_path=args.seeds,
            output_root=args.output_root,
            llm=llm,
            builder_identity=_config_identity(config),
            limit=args.limit,
            only_invalid=args.only_invalid,
        )
    elif args.command == "validate-mechanisms":
        result = validate_mechanisms(seeds_path=args.seeds, output_root=args.output_root)
    elif args.command == "export-review-sheet":
        result = export_review_sheet(
            seeds_path=args.seeds,
            output_root=args.output_root,
            output_path=args.output,
        )
    elif args.command == "import-reviews":
        result = import_reviews(
            review_sheet_path=args.input,
            seeds_path=args.seeds,
            output_root=args.output_root,
            default_reviewer=args.reviewer,
        )
    elif args.command == "build-mappings":
        config = LLMConfig.from_env()
        if args.standard_model:
            config = replace(config, model=args.standard_model)
        result = build_mapping_plans(
            seeds_path=args.seeds,
            preparation_root=args.preparation_root,
            output_root=args.output_root,
            llm=DeepSeekLLM(config),
            builder_identity=_config_identity(config),
            only_missing=args.only_missing,
        )
    elif args.command == "run-experiment":
        base = LLMConfig.from_env()
        generator_config = replace(base, model=args.generator_model) if args.generator_model else base
        judge_config = replace(base, model=args.judge_model) if args.judge_model else base
        strategies = ("standard", "copycat") if args.strategy == "both" else (args.strategy,)
        result = run_experiment(
            seeds_path=args.seeds,
            preparation_root=args.preparation_root,
            output_dir=args.output_dir,
            llm=DeepSeekLLM(generator_config),
            judge_llm=DeepSeekLLM(judge_config),
            options=ExperimentOptions(strategies=strategies, six_dim_mode=args.six_dim_mode),
        )
    elif args.command == "status":
        result = pipeline_status(seeds_path=args.seeds, output_root=args.output_root)
    elif args.command == "serve-review":
        from kg_rag.m2na_v2.review_app import serve_review_app

        server = serve_review_app(
            seeds_path=args.seeds,
            output_root=args.output_root,
            host=args.host,
            port=args.port,
        )
        print(f"M2NA V2 review app: http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    elif args.command == "serve-mapping-review":
        from kg_rag.m2na_v2.mapping_review_app import serve_mapping_review_app

        server = serve_mapping_review_app(
            mapping_root=args.mapping_root,
            seeds_path=args.seeds,
            host=args.host,
            port=args.port,
        )
        print(f"M2NA V2 mapping review app: http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    else:
        parser.print_help()
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _config_identity(config: LLMConfig) -> dict[str, object]:
    return {
        "provider": config.provider,
        "base_url": config.base_url,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
