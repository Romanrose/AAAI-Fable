from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from kg_rag.llm_config import LLMConfig
from kg_rag.multi_agent.llm import DeepSeekLLM
from kg_rag.paths import DEFAULT_DERIVED_DIR
from kg_rag.story_pilot.pipeline import prepare_guided_mappings, rejudge_stories, run_initial_stories, run_revisions


DEFAULT_PREPARATION = DEFAULT_DERIVED_DIR / "kg_rag" / "m2na_v2" / "pilot80"
DEFAULT_MAPPING = DEFAULT_PREPARATION / "mapping_plans"
DEFAULT_PILOT = DEFAULT_DERIVED_DIR / "kg_rag" / "story_pilot12"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Twelve-concept, three-strategy story pilot.")
    subparsers = parser.add_subparsers(dest="command")
    guided = subparsers.add_parser("prepare-guided-mappings")
    guided.add_argument("--preparation-root", type=Path, default=DEFAULT_PREPARATION)
    guided.add_argument("--output-root", type=Path, default=DEFAULT_PILOT)
    guided.add_argument("--model", default=None)
    guided.add_argument("--workers", type=int, default=3)
    initial = subparsers.add_parser("run-initial")
    initial.add_argument("--preparation-root", type=Path, default=DEFAULT_PREPARATION)
    initial.add_argument("--mapping-root", type=Path, default=DEFAULT_MAPPING)
    initial.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT)
    initial.add_argument("--generator-model", default=None)
    initial.add_argument("--judge-model", default=None)
    initial.add_argument("--workers", type=int, default=4)
    rejudge = subparsers.add_parser("rejudge")
    rejudge.add_argument("--preparation-root", type=Path, default=DEFAULT_PREPARATION)
    rejudge.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT)
    rejudge.add_argument("--judge-model", default=None)
    rejudge.add_argument("--workers", type=int, default=4)
    revise = subparsers.add_parser("revise")
    revise.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT)
    revise.add_argument("--reviser-model", default=None)
    revise.add_argument("--judge-model", default=None)
    revise.add_argument("--workers", type=int, default=4)
    serve_review = subparsers.add_parser("serve-review")
    serve_review.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT)
    serve_review.add_argument("--host", default="127.0.0.1")
    serve_review.add_argument("--port", type=int, default=8768)
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    if args.command == "serve-review":
        from kg_rag.story_pilot.review_app import serve_story_review_app

        server = serve_story_review_app(
            pilot_root=args.pilot_root,
            host=args.host,
            port=args.port,
        )
        print(f"Story Pilot review app: http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    base = LLMConfig.from_env()
    if args.command == "prepare-guided-mappings":
        config = replace(base, model=args.model) if args.model else base
        result = prepare_guided_mappings(
            preparation_root=args.preparation_root,
            output_root=args.output_root,
            llm=DeepSeekLLM(config),
            model_identity=_identity(config),
            workers=args.workers,
        )
    elif args.command == "run-initial":
        generator = replace(base, model=args.generator_model) if args.generator_model else base
        judge = replace(base, model=args.judge_model) if args.judge_model else base
        result = run_initial_stories(
            preparation_root=args.preparation_root,
            mapping_root=args.mapping_root,
            pilot_root=args.pilot_root,
            llm=DeepSeekLLM(generator),
            judge_llm=DeepSeekLLM(judge),
            model_identity=_identity(generator),
            judge_identity=_identity(judge),
            workers=args.workers,
        )
    elif args.command == "rejudge":
        judge = replace(base, model=args.judge_model) if args.judge_model else base
        result = rejudge_stories(
            preparation_root=args.preparation_root,
            pilot_root=args.pilot_root,
            judge_llm=DeepSeekLLM(judge),
            judge_identity=_identity(judge),
            workers=args.workers,
        )
    elif args.command == "revise":
        reviser = replace(base, model=args.reviser_model) if args.reviser_model else base
        judge = replace(base, model=args.judge_model) if args.judge_model else base
        result = run_revisions(
            pilot_root=args.pilot_root,
            llm=DeepSeekLLM(reviser),
            judge_llm=DeepSeekLLM(judge),
            model_identity=_identity(reviser),
            judge_identity=_identity(judge),
            workers=args.workers,
        )
    else:  # pragma: no cover - argparse constrains command values
        raise ValueError(f"Unsupported command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _identity(config: LLMConfig) -> dict[str, object]:
    return {
        "provider": config.provider,
        "base_url": config.base_url,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
