"""Command-line entry point for the Graph RAG narrative demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .backends import BackendError
from .pipeline import PipelineError, run_demo
from .retrieval import RETRIEVAL_MODES, RetrievalError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concept", required=True, help="target concept name")
    parser.add_argument(
        "--subject",
        choices=("biology", "chemistry", "math", "physics"),
        default="biology",
    )
    parser.add_argument(
        "--backend", choices=("fixture", "deepseek"), default="fixture"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("graph_rag_demo/output"),
    )
    parser.add_argument("--max-edges", type=int, default=12)
    parser.add_argument(
        "--retrieval-mode",
        choices=tuple(sorted(RETRIEVAL_MODES)),
        default="one_hop",
        help="Graph RAG retrieval strategy",
    )
    parser.add_argument("--max-hops", type=int, default=2)
    parser.add_argument("--max-paths", type=int, default=5)
    parser.add_argument(
        "--graph-path",
        type=Path,
        help="override the rich subject graph path (mainly for testing)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run_demo(
            concept=args.concept,
            subject=args.subject,
            backend_name=args.backend,
            output_dir=args.output_dir,
            max_edges=args.max_edges,
            retrieval_mode=args.retrieval_mode,
            max_hops=args.max_hops,
            max_paths=args.max_paths,
            graph_path=args.graph_path,
        )
    except (RetrievalError, BackendError, PipelineError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
