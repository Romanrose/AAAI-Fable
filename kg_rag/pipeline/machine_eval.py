from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kg_rag.concepts.cards import build_concept_cards
from kg_rag.concepts.enrichment import enrich_concept_cards
from kg_rag.concepts.selection import select_concept_nodes
from kg_rag.evaluation.report import verify_eval_run
from kg_rag.ingest.normalize_k12 import normalize_k12_graph
from kg_rag.paths import DEFAULT_DERIVED_DIR, DEFAULT_GRAPH_ROOT, DEFAULT_SUBJECT_GRAPH_DIR
from kg_rag.pipeline.concept_fables import ConceptFableOptions, run_concept_fable_batch
from kg_rag.pipeline.run_registry import DEFAULT_CONCEPT_RUNS_DIR, auto_concept_run_dir


@dataclass(frozen=True)
class MachineEvalOptions:
    subjects: str
    limit: int
    limit_per_subject: int | None
    mode: str
    evaluate_mode: str
    language: str
    no_normalize: bool
    no_resume: bool


def run_machine_eval(
    *,
    output_root: Path = DEFAULT_DERIVED_DIR / "kg_rag",
    normalized_graph_path: Path = DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
    concept_runs_root: Path = DEFAULT_CONCEPT_RUNS_DIR,
    options: MachineEvalOptions,
) -> dict[str, Any]:
    if options.mode != "local":
        raise ValueError("run-machine-eval currently orchestrates local generation only; use run-concept-fable-batch for LLM generation.")
    if options.evaluate_mode != "rules":
        raise ValueError("run-machine-eval currently orchestrates rules evaluation only; use evaluate-batch for LLM judge runs.")

    output_root.mkdir(parents=True, exist_ok=True)
    if not options.no_normalize or not normalized_graph_path.exists():
        normalize_k12_graph(
            nodes_path=DEFAULT_GRAPH_ROOT / "nodes.json",
            edges_path=DEFAULT_GRAPH_ROOT / "edges.json",
            subject_graph_dir=DEFAULT_SUBJECT_GRAPH_DIR,
            output_path=normalized_graph_path,
        )

    selection_path = output_root / "concept_selection" / "machine_eval_concepts.jsonl"
    raw_cards_path = output_root / "concept_cards" / "machine_eval_concept_cards.raw.jsonl"
    enriched_cards_path = output_root / "concept_cards" / "machine_eval_concept_cards.enriched.jsonl"

    selection = select_concept_nodes(
        normalized_graph_path=normalized_graph_path,
        output_path=selection_path,
        subjects=options.subjects,
        limit_per_subject=options.limit_per_subject,
    )
    cards = build_concept_cards(
        selection_path=selection_path,
        normalized_graph_path=normalized_graph_path,
        output_path=raw_cards_path,
    )
    enrichment = enrich_concept_cards(
        input_path=raw_cards_path,
        output_path=enriched_cards_path,
        mode="rules",
    )

    run_dir = auto_concept_run_dir(
        mode=options.mode,
        limit=options.limit,
        evaluate_mode=options.evaluate_mode,
        runs_root=concept_runs_root,
    )
    batch = run_concept_fable_batch(
        concept_cards_path=enriched_cards_path,
        output_dir=run_dir,
        normalized_graph_path=normalized_graph_path,
        options=ConceptFableOptions(
            workflow="agentic",
            mode=options.mode,
            language=options.language,
            subject=None,
            priority=None,
            limit=options.limit,
            offset=0,
            batch_size=options.limit,
            retry=1,
            sleep_seconds=0.0,
            resume=not options.no_resume,
            evaluate_mode=options.evaluate_mode,
            retrieval_mode="dual_level",
            max_edges=16,
            revision_rounds=0,
            template_blacklist="default",
        ),
    )
    verification = verify_eval_run(run_dir, expected_count=options.limit)
    return {
        "normalized_graph_path": str(normalized_graph_path),
        "selection": selection,
        "cards": cards,
        "enrichment": enrichment,
        "batch": batch,
        "verification": verification,
        "ok": verification["ok"] and batch["failed_count"] == 0,
    }
