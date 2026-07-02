from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.concepts.prompts import ENRICH_SYSTEM_PROMPT, build_enrichment_prompt
from kg_rag.evaluation.parser import parse_json_object
from kg_rag.io import write_json
from kg_rag.llm_client import chat_completion
from kg_rag.llm_config import LLMConfig


def _heuristic_enrichment(card: dict[str, Any]) -> dict[str, Any]:
    definition = card.get("definition") or ""
    constraints = list(card.get("subject_constraints_zh", []))
    core = list(card.get("core_mechanism_zh", []))
    if not core and definition:
        core = [definition]
    must_preserve = list(card.get("must_preserve_zh", []))
    if not must_preserve:
        if definition:
            must_preserve.append(definition)
        must_preserve.extend(constraints[:2])
    return {
        "concept_type": card.get("concept_type") or "definition",
        "core_mechanism_zh": core[:6],
        "must_preserve_zh": must_preserve[:6],
        "common_misconceptions_zh": list(card.get("common_misconceptions_zh", [])),
        "subject_constraints_zh": constraints,
        "generation_notes_zh": list(card.get("generation_notes_zh", [])),
        "enrichment_confidence": 0.55 if card.get("data_quality", {}).get("generation_priority") == "repair" else 0.72,
    }


def _merge_enrichment(card: dict[str, Any], enrichment: dict[str, Any]) -> dict[str, Any]:
    merged = dict(card)
    for key in (
        "concept_type",
        "core_mechanism_zh",
        "must_preserve_zh",
        "common_misconceptions_zh",
        "subject_constraints_zh",
        "generation_notes_zh",
        "enrichment_confidence",
    ):
        if key in enrichment and enrichment[key] not in (None, "", [], {}):
            merged[key] = enrichment[key]
    data_quality = dict(merged.get("data_quality", {}))
    data_quality["needs_llm_enrichment"] = False
    data_quality["enrichment_confidence"] = merged.get("enrichment_confidence")
    merged["data_quality"] = data_quality
    return merged


def enrich_concept_cards(
    *,
    input_path: Path,
    output_path: Path,
    mode: str = "rules",
    config: LLMConfig | None = None,
    only_needs_enrichment: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    cards = read_jsonl(input_path)
    enriched_cards: list[dict[str, Any]] = []
    enriched_count = 0
    failed_count = 0

    for card in cards:
        should_enrich = bool(card.get("data_quality", {}).get("needs_llm_enrichment"))
        if only_needs_enrichment and not should_enrich:
            enriched_cards.append(card)
            continue
        if limit is not None and enriched_count >= limit:
            enriched_cards.append(card)
            continue

        try:
            if mode == "llm":
                if config is None:
                    raise ValueError("LLM enrichment mode requires an LLMConfig.")
                response = chat_completion(
                    config=config,
                    system_prompt=ENRICH_SYSTEM_PROMPT,
                    user_prompt=build_enrichment_prompt(card),
                )
                enrichment = parse_json_object(response)
            elif mode == "rules":
                enrichment = _heuristic_enrichment(card)
            else:
                raise ValueError(f"Unsupported enrichment mode: {mode}")
            enriched_cards.append(_merge_enrichment(card, enrichment))
            enriched_count += 1
        except Exception as exc:
            failed = dict(card)
            failed["enrichment_error"] = {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
            enriched_cards.append(failed)
            failed_count += 1

    write_jsonl(output_path, enriched_cards)
    result = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "card_count": len(cards),
        "enriched_count": enriched_count,
        "failed_count": failed_count,
        "mode": mode,
    }
    write_json(output_path.with_suffix(".summary.json"), result)
    return result

