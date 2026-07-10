from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from kg_rag.llm_config import LLMConfig
from kg_rag.llm_guided_copycat.pipeline import run_one
from kg_rag.multi_agent.llm import DeepSeekLLM
from kg_rag.paths import DEFAULT_DERIVED_DIR


DEFAULT_ROOT = DEFAULT_DERIVED_DIR / "kg_rag" / "m2na_v2" / "pilot80"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Minimal LLM-guided Copycat-inspired mapping prototype.")
    parser.add_argument("--concept-id", required=True)
    parser.add_argument("--preparation-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)
    config = LLMConfig.from_env()
    if args.model:
        config = replace(config, model=args.model)
    result = run_one(
        concept_id=args.concept_id,
        preparation_root=args.preparation_root,
        output_dir=args.output_dir,
        llm=DeepSeekLLM(config),
        model_identity={
            "provider": config.provider,
            "base_url": config.base_url,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        },
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
