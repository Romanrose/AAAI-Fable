from __future__ import annotations

import argparse
from pathlib import Path

from kg_rag.ingest.normalize_k12 import normalize_k12_graph
from kg_rag.io import read_json, write_json
from kg_rag.paths import DEFAULT_DERIVED_DIR, DEFAULT_GRAPH_ROOT, DEFAULT_SUBJECT_GRAPH_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kg-rag",
        description="Minimal CLI scaffold for AAAI-Fable GraphRAG experiments.",
    )
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Print local project paths and scaffold status.")
    doctor.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Override the inferred project root.",
    )

    normalize = subparsers.add_parser(
        "normalize-k12",
        help="Build a normalized offline graph artifact from K12-KGraph source files.",
    )
    normalize.add_argument(
        "--nodes-path",
        type=Path,
        default=DEFAULT_GRAPH_ROOT / "nodes.json",
        help="Path to global_KG nodes.json.",
    )
    normalize.add_argument(
        "--edges-path",
        type=Path,
        default=DEFAULT_GRAPH_ROOT / "edges.json",
        help="Path to global_KG edges.json.",
    )
    normalize.add_argument(
        "--subject-graph-dir",
        type=Path,
        default=DEFAULT_SUBJECT_GRAPH_DIR,
        help="Directory containing subject-specific graph JSON files.",
    )
    normalize.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Output path for the normalized graph artifact.",
    )

    load_neo4j = subparsers.add_parser(
        "load-neo4j",
        help="Load the normalized K12 graph artifact into Neo4j.",
    )
    load_neo4j.add_argument(
        "--normalized-graph-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Path to the normalized graph artifact.",
    )
    load_neo4j.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for Neo4j writes.",
    )

    query_subgraph = subparsers.add_parser(
        "query-subgraph",
        help="Query a 1-2 hop concept-centered subgraph from Neo4j.",
    )
    query_subgraph.add_argument("concept_name", help="Concept name or alias to query.")
    query_subgraph.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional path to write the subgraph pack as JSON.",
    )
    query_subgraph.add_argument(
        "--normalized-graph-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Optional offline artifact path used for local preview when Neo4j is unavailable.",
    )
    query_subgraph.add_argument(
        "--preview-only",
        action="store_true",
        help="Use the normalized JSON artifact for seed preview only, without querying Neo4j.",
    )
    query_subgraph.add_argument(
        "--pack-output-path",
        type=Path,
        default=None,
        help="Optional path to write an LLM-ready subgraph pack as JSON.",
    )

    build_prompt = subparsers.add_parser(
        "build-prompt",
        help="Assemble an LLM prompt from a subgraph pack.",
    )
    build_prompt.add_argument(
        "--pack-path",
        type=Path,
        required=True,
        help="Path to a subgraph pack JSON file.",
    )
    build_prompt.add_argument(
        "--mode",
        choices=("teaching", "mapping"),
        default="mapping",
        help="Prompt mode to assemble.",
    )
    build_prompt.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional path to write the prompt text.",
    )

    structure_plan = subparsers.add_parser(
        "build-structure-plan",
        help="Build a minimal story skeleton / alignment plan from a subgraph pack.",
    )
    structure_plan.add_argument(
        "--pack-path",
        type=Path,
        required=True,
        help="Path to a subgraph pack JSON file.",
    )
    structure_plan.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional path to write the structure plan JSON.",
    )

    story_prompt = subparsers.add_parser(
        "build-story-prompt",
        help="Build a story-generation prompt from a structure plan.",
    )
    story_prompt.add_argument(
        "--plan-path",
        type=Path,
        required=True,
        help="Path to a structure plan JSON file.",
    )
    story_prompt.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional path to write the story prompt text.",
    )

    review_prompt = subparsers.add_parser(
        "build-review-prompt",
        help="Build a reviewer prompt from a structure plan and a draft story file.",
    )
    review_prompt.add_argument(
        "--plan-path",
        type=Path,
        required=True,
        help="Path to a structure plan JSON file.",
    )
    review_prompt.add_argument(
        "--draft-path",
        type=Path,
        required=True,
        help="Path to a text file containing the draft story.",
    )
    review_prompt.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional path to write the review prompt text.",
    )

    review_check = subparsers.add_parser(
        "review-checklist",
        help="Produce a lightweight local review checklist from a structure plan and a draft story.",
    )
    review_check.add_argument(
        "--plan-path",
        type=Path,
        required=True,
        help="Path to a structure plan JSON file.",
    )
    review_check.add_argument(
        "--draft-path",
        type=Path,
        required=True,
        help="Path to a text file containing the draft story.",
    )
    review_check.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional path to write the checklist JSON.",
    )

    local_demo = subparsers.add_parser(
        "run-local-demo",
        help="Run the local end-to-end preview pipeline without external model calls.",
    )
    local_demo.add_argument("concept_name", help="Concept name or alias to run through the local pipeline.")
    local_demo.add_argument(
        "--normalized-graph-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Path to the normalized graph artifact.",
    )
    local_demo.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "demo_run",
        help="Directory for demo pipeline outputs.",
    )

    llm_demo = subparsers.add_parser(
        "run-llm-demo",
        help="Run the end-to-end preview pipeline with a configured DeepSeek-compatible LLM.",
    )
    llm_demo.add_argument("concept_name", help="Concept name or alias to run through the LLM pipeline.")
    llm_demo.add_argument(
        "--normalized-graph-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Path to the normalized graph artifact.",
    )
    llm_demo.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "llm_demo_run",
        help="Directory for LLM demo outputs.",
    )

    batch_stories = subparsers.add_parser(
        "run-batch-stories",
        help="Run story generation for a batch of concepts.",
    )
    batch_stories.add_argument(
        "--normalized-graph-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Path to the normalized graph artifact.",
    )
    batch_stories.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "batch_runs" / "run_001",
        help="Batch output directory.",
    )
    batch_stories.add_argument("--mode", choices=("local", "llm"), default="local", help="Generation mode.")
    batch_stories.add_argument("--label", default="Concept", help="Node label to batch over.")
    batch_stories.add_argument("--subject", default=None, help="Optional subject prefix, e.g. biology, physics, chemistry, math.")
    batch_stories.add_argument("--limit", type=int, default=10, help="Maximum concepts to run.")
    batch_stories.add_argument("--offset", type=int, default=0, help="Concept offset after label filtering.")
    batch_stories.add_argument("--sleep-seconds", type=float, default=0.0, help="Delay between concepts.")
    batch_stories.add_argument("--retry", type=int, default=1, help="Retry count for LLM calls.")
    batch_stories.add_argument("--no-resume", action="store_true", help="Do not skip existing completed concept outputs.")

    evaluate_story = subparsers.add_parser(
        "evaluate-story",
        help="Evaluate one generated fable directory with the six-dimensional rubric.",
    )
    evaluate_story.add_argument("story_dir", type=Path, help="Directory containing subgraph_pack.json, structure_plan.json, and draft_story.txt.")
    evaluate_story.add_argument("--mode", choices=("rules", "llm"), default="rules", help="Use local rules only or call the configured LLM judge.")

    evaluate_batch = subparsers.add_parser(
        "evaluate-batch",
        help="Evaluate every generated fable under a batch output directory.",
    )
    evaluate_batch.add_argument("batch_dir", type=Path, help="Batch directory containing concepts/* outputs.")
    evaluate_batch.add_argument("--mode", choices=("rules", "llm"), default="rules", help="Use local rules only or call the configured LLM judge.")
    evaluate_batch.add_argument("--no-resume", action="store_true", help="Re-evaluate concepts even when six_dim_eval.json already exists.")

    export_eval_report = subparsers.add_parser(
        "export-eval-report",
        help="Export eval_summary.csv and eval_report.md from an eval_summary.jsonl file.",
    )
    export_eval_report.add_argument("summary_jsonl", type=Path, help="Path to eval_summary.jsonl.")
    export_eval_report.add_argument("--output-dir", type=Path, default=None, help="Optional output directory for report files.")

    select_concepts = subparsers.add_parser(
        "select-concept-nodes",
        help="Select K12 Concept nodes for first-stage Chinese fable generation.",
    )
    select_concepts.add_argument(
        "--subjects",
        default="biology,chemistry,math,physics",
        help="Comma-separated subject prefixes.",
    )
    select_concepts.add_argument(
        "--normalized-graph-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Path to the normalized graph artifact.",
    )
    select_concepts.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "concept_selection" / "k12_concepts.jsonl",
        help="Output JSONL path.",
    )
    select_concepts.add_argument("--limit-per-subject", type=int, default=None, help="Optional smoke-test limit per subject.")

    build_concept_cards = subparsers.add_parser(
        "build-concept-cards",
        help="Build Chinese concept_card JSONL records from selected Concept nodes.",
    )
    build_concept_cards.add_argument("--selection-path", type=Path, required=True, help="Path to selected Concept JSONL.")
    build_concept_cards.add_argument(
        "--normalized-graph-path",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "k12_kgraph_normalized.json",
        help="Path to the normalized graph artifact.",
    )
    build_concept_cards.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "concept_cards" / "k12_concept_cards.raw.jsonl",
        help="Output concept_card JSONL path.",
    )

    enrich_concept_cards = subparsers.add_parser(
        "enrich-concept-cards",
        help="Enrich Chinese concept_cards with structure fields for fable generation.",
    )
    enrich_concept_cards.add_argument("--input", type=Path, required=True, help="Input concept_card JSONL path.")
    enrich_concept_cards.add_argument("--output", type=Path, required=True, help="Output enriched concept_card JSONL path.")
    enrich_concept_cards.add_argument("--mode", choices=("rules", "llm"), default="rules", help="Use heuristic enrichment or LLM enrichment.")
    enrich_concept_cards.add_argument("--language", choices=("zh-CN",), default="zh-CN", help="Enrichment language.")
    enrich_concept_cards.add_argument("--only-needs-enrichment", action="store_true", help="Only enrich cards marked needs_llm_enrichment.")
    enrich_concept_cards.add_argument("--limit", type=int, default=None, help="Optional maximum cards to enrich.")

    concept_fables = subparsers.add_parser(
        "run-concept-fable-batch",
        help="Generate first-stage Simplified Chinese fables from concept_cards.",
    )
    concept_fables.add_argument("--concept-cards", type=Path, required=True, help="Input enriched concept_card JSONL path.")
    concept_fables.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DERIVED_DIR / "kg_rag" / "concept_runs" / "k12_concepts_zh_v1",
        help="Output run directory.",
    )
    concept_fables.add_argument("--mode", choices=("local", "llm"), default="local", help="Story generation mode.")
    concept_fables.add_argument("--language", choices=("zh-CN",), default="zh-CN", help="Story language.")
    concept_fables.add_argument("--subject", default=None, help="Optional subject filter.")
    concept_fables.add_argument("--priority", default=None, help="Optional priority filter, e.g. gold or gold,silver.")
    concept_fables.add_argument("--limit", type=int, default=10, help="Maximum concepts to run.")
    concept_fables.add_argument("--offset", type=int, default=0, help="Offset after filters.")
    concept_fables.add_argument("--batch-size", type=int, default=100, help="Recorded batch size for run metadata.")
    concept_fables.add_argument("--retry", type=int, default=1, help="Retry count for LLM generation.")
    concept_fables.add_argument("--sleep-seconds", type=float, default=0.0, help="Delay between concepts.")
    concept_fables.add_argument("--evaluate-mode", choices=("rules", "llm"), default="rules", help="Evaluation mode after generation.")
    concept_fables.add_argument("--no-resume", action="store_true", help="Do not skip existing completed concept outputs.")

    rewrite_concept_fables = subparsers.add_parser(
        "rewrite-concept-fables",
        help="Rewrite revise/reject Chinese concept fables in a concept run directory.",
    )
    rewrite_concept_fables.add_argument("--run-dir", type=Path, required=True, help="Concept fable run directory.")
    rewrite_concept_fables.add_argument("--status", default="revise,reject", help="Comma-separated evaluation statuses to rewrite.")
    rewrite_concept_fables.add_argument("--language", choices=("zh-CN",), default="zh-CN", help="Story language.")
    rewrite_concept_fables.add_argument("--mode", choices=("local", "llm"), default="local", help="Rewrite mode.")
    rewrite_concept_fables.add_argument("--retry", type=int, default=1, help="Recorded rewrite retry count.")

    return parser


def run_doctor(project_root: Path | None) -> int:
    root = project_root.resolve() if project_root else Path(__file__).resolve().parent.parent
    print("AAAI-Fable GraphRAG scaffold")
    print(f"project_root={root}")
    print(f"graph_root={DEFAULT_GRAPH_ROOT}")
    print(f"subject_graph_dir={DEFAULT_SUBJECT_GRAPH_DIR}")
    print(f"derived_dir={DEFAULT_DERIVED_DIR}")
    print(f"graph_root_exists={DEFAULT_GRAPH_ROOT.exists()}")
    print(f"subject_graph_dir_exists={DEFAULT_SUBJECT_GRAPH_DIR.exists()}")
    print(f"derived_dir_exists={DEFAULT_DERIVED_DIR.exists()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return run_doctor(args.project_root)
    if args.command == "normalize-k12":
        payload = normalize_k12_graph(
            nodes_path=args.nodes_path,
            edges_path=args.edges_path,
            subject_graph_dir=args.subject_graph_dir,
            output_path=args.output_path,
        )
        print(f"wrote={args.output_path}")
        print(f"node_count={payload['meta']['node_count']}")
        print(f"edge_count={payload['meta']['edge_count']}")
        return 0
    if args.command == "load-neo4j":
        from kg_rag.ingest.neo4j_loader import load_normalized_graph_to_neo4j
        from kg_rag.neo4j_config import Neo4jConfig

        result = load_normalized_graph_to_neo4j(
            normalized_graph_path=args.normalized_graph_path,
            config=Neo4jConfig.from_env(),
            batch_size=args.batch_size,
        )
        print(f"loaded_nodes={result['node_count']}")
        print(f"loaded_edges={result['edge_count']}")
        return 0
    if args.command == "query-subgraph":
        from kg_rag.retrievers.context_pack import build_subgraph_pack
        from kg_rag.retrievers.subgraph import preview_normalized_seed, query_subgraph_by_concept, write_subgraph_pack
        from kg_rag.neo4j_config import Neo4jConfig

        if args.preview_only:
            payload = preview_normalized_seed(
                normalized_graph_path=args.normalized_graph_path,
                concept_name=args.concept_name,
            )
        else:
            payload = query_subgraph_by_concept(
                concept_name=args.concept_name,
                config=Neo4jConfig.from_env(),
            )

        print(f"found={payload['found']}")
        if payload["seed"]:
            print(f"seed_id={payload['seed']['id']}")
            print(f"seed_name={payload['seed']['name']}")
        if "nodes" in payload:
            print(f"node_count={len(payload['nodes'])}")
            print(f"edge_count={len(payload['edges'])}")
        if args.output_path:
            write_subgraph_pack(payload=payload, output_path=args.output_path)
            print(f"wrote={args.output_path}")
        if args.pack_output_path:
            pack = build_subgraph_pack(payload)
            write_subgraph_pack(payload=pack, output_path=args.pack_output_path)
            print(f"wrote_pack={args.pack_output_path}")
        return 0
    if args.command == "build-prompt":
        from kg_rag.prompts.assembler import build_mapping_prompt, build_teaching_prompt

        pack = read_json(args.pack_path)
        prompt = build_mapping_prompt(pack) if args.mode == "mapping" else build_teaching_prompt(pack)
        print(prompt)
        if args.output_path:
            args.output_path.parent.mkdir(parents=True, exist_ok=True)
            args.output_path.write_text(prompt, encoding="utf-8")
            print(f"wrote={args.output_path}")
        return 0
    if args.command == "build-structure-plan":
        from kg_rag.structure_mapping.planner import build_structure_plan

        pack = read_json(args.pack_path)
        plan = build_structure_plan(pack)
        if args.output_path:
            write_json(args.output_path, plan)
            print(f"wrote={args.output_path}")
        else:
            print(plan)
        return 0
    if args.command == "build-story-prompt":
        from kg_rag.generation.prompts import build_story_prompt

        plan = read_json(args.plan_path)
        prompt = build_story_prompt(plan)
        print(prompt)
        if args.output_path:
            args.output_path.parent.mkdir(parents=True, exist_ok=True)
            args.output_path.write_text(prompt, encoding="utf-8")
            print(f"wrote={args.output_path}")
        return 0
    if args.command == "build-review-prompt":
        from kg_rag.generation.prompts import build_review_prompt

        plan = read_json(args.plan_path)
        draft_story = args.draft_path.read_text(encoding="utf-8")
        prompt = build_review_prompt(plan, draft_story)
        print(prompt)
        if args.output_path:
            args.output_path.parent.mkdir(parents=True, exist_ok=True)
            args.output_path.write_text(prompt, encoding="utf-8")
            print(f"wrote={args.output_path}")
        return 0
    if args.command == "review-checklist":
        from kg_rag.generation.review import build_review_checklist

        plan = read_json(args.plan_path)
        draft_story = args.draft_path.read_text(encoding="utf-8")
        checklist = build_review_checklist(plan, draft_story)
        if args.output_path:
            write_json(args.output_path, checklist)
            print(f"wrote={args.output_path}")
        else:
            print(checklist)
        return 0
    if args.command == "run-local-demo":
        from kg_rag.pipeline.local_demo import run_local_demo_pipeline

        result = run_local_demo_pipeline(
            concept_name=args.concept_name,
            normalized_graph_path=args.normalized_graph_path,
            output_dir=args.output_dir,
        )
        print(f"draft_path={result['draft_path']}")
        print(f"review_prompt_path={result['review_prompt_path']}")
        print(f"checklist_path={result['checklist_path']}")
        print(f"pass_fail={result['checklist']['pass_fail']}")
        return 0
    if args.command == "run-llm-demo":
        from kg_rag.llm_config import LLMConfig
        from kg_rag.pipeline.llm_demo import run_llm_demo_pipeline

        result = run_llm_demo_pipeline(
            concept_name=args.concept_name,
            normalized_graph_path=args.normalized_graph_path,
            output_dir=args.output_dir,
            config=LLMConfig.from_env(),
        )
        print(f"draft_path={result['draft_path']}")
        print(f"review_response_path={result['review_response_path']}")
        print(f"checklist_path={result['checklist_path']}")
        print(f"pass_fail={result['checklist']['pass_fail']}")
        return 0
    if args.command == "run-batch-stories":
        from kg_rag.llm_config import LLMConfig
        from kg_rag.pipeline.batch_stories import BatchOptions, run_batch_stories

        config = LLMConfig.from_env() if args.mode == "llm" else None
        result = run_batch_stories(
            normalized_graph_path=args.normalized_graph_path,
            output_dir=args.output_dir,
            options=BatchOptions(
                mode=args.mode,
                label=args.label,
                subject=args.subject,
                limit=args.limit,
                offset=args.offset,
                sleep_seconds=args.sleep_seconds,
                retry=args.retry,
                resume=not args.no_resume,
            ),
            config=config,
        )
        print(f"summary_path={result['summary_path']}")
        print(f"concept_count={result['concept_count']}")
        print(f"success_count={result['success_count']}")
        print(f"failed_count={result['failed_count']}")
        print(f"skipped_count={result['skipped_count']}")
        return 0
    if args.command == "evaluate-story":
        from kg_rag.evaluation.pipeline import evaluate_story_dir
        from kg_rag.llm_config import LLMConfig

        config = LLMConfig.from_env() if args.mode == "llm" else None
        result = evaluate_story_dir(args.story_dir, mode=args.mode, config=config)
        print(f"eval_path={args.story_dir / 'six_dim_eval.json'}")
        print(f"final_status={result['final_status']}")
        print(f"weighted_overall={result['weighted_overall']}")
        return 0
    if args.command == "evaluate-batch":
        from kg_rag.evaluation.pipeline import evaluate_batch_dir
        from kg_rag.llm_config import LLMConfig

        config = LLMConfig.from_env() if args.mode == "llm" else None
        result = evaluate_batch_dir(
            args.batch_dir,
            mode=args.mode,
            config=config,
            resume=not args.no_resume,
        )
        print(f"summary_path={result['summary_path']}")
        print(f"csv_path={result.get('csv_path')}")
        print(f"report_path={result.get('report_path')}")
        print(f"evaluated_count={result['evaluated_count']}")
        print(f"skipped_count={result['skipped_count']}")
        print(f"failed_count={result['failed_count']}")
        return 0
    if args.command == "export-eval-report":
        from kg_rag.evaluation.report import export_reports

        result = export_reports(args.summary_jsonl, output_dir=args.output_dir)
        print(f"csv_path={result['csv_path']}")
        print(f"report_path={result['report_path']}")
        print(f"row_count={result['row_count']}")
        return 0
    if args.command == "select-concept-nodes":
        from kg_rag.concepts.selection import select_concept_nodes

        result = select_concept_nodes(
            normalized_graph_path=args.normalized_graph_path,
            output_path=args.output,
            subjects=args.subjects,
            limit_per_subject=args.limit_per_subject,
        )
        print(f"output_path={result['output_path']}")
        print(f"concept_count={result['concept_count']}")
        print(f"subjects={result['subjects']}")
        print(f"priorities={result['priorities']}")
        return 0
    if args.command == "build-concept-cards":
        from kg_rag.concepts.cards import build_concept_cards

        result = build_concept_cards(
            selection_path=args.selection_path,
            normalized_graph_path=args.normalized_graph_path,
            output_path=args.output,
        )
        print(f"output_path={result['output_path']}")
        print(f"concept_card_count={result['concept_card_count']}")
        return 0
    if args.command == "enrich-concept-cards":
        from kg_rag.concepts.enrichment import enrich_concept_cards
        from kg_rag.llm_config import LLMConfig

        config = LLMConfig.from_env() if args.mode == "llm" else None
        result = enrich_concept_cards(
            input_path=args.input,
            output_path=args.output,
            mode=args.mode,
            config=config,
            only_needs_enrichment=args.only_needs_enrichment,
            limit=args.limit,
        )
        print(f"output_path={result['output_path']}")
        print(f"card_count={result['card_count']}")
        print(f"enriched_count={result['enriched_count']}")
        print(f"failed_count={result['failed_count']}")
        return 0
    if args.command == "run-concept-fable-batch":
        from kg_rag.llm_config import LLMConfig
        from kg_rag.pipeline.concept_fables import ConceptFableOptions, run_concept_fable_batch

        needs_config = args.mode == "llm" or args.evaluate_mode == "llm"
        config = LLMConfig.from_env() if needs_config else None
        result = run_concept_fable_batch(
            concept_cards_path=args.concept_cards,
            output_dir=args.output_dir,
            options=ConceptFableOptions(
                mode=args.mode,
                language=args.language,
                subject=args.subject,
                priority=args.priority,
                limit=args.limit,
                offset=args.offset,
                batch_size=args.batch_size,
                retry=args.retry,
                sleep_seconds=args.sleep_seconds,
                resume=not args.no_resume,
                evaluate_mode=args.evaluate_mode,
            ),
            config=config,
        )
        print(f"summary_path={result['summary_path']}")
        print(f"eval_summary_path={result['eval_summary_path']}")
        print(f"concept_count={result['concept_count']}")
        print(f"success_count={result['success_count']}")
        print(f"failed_count={result['failed_count']}")
        print(f"skipped_count={result['skipped_count']}")
        print(f"csv_path={result.get('csv_path')}")
        print(f"report_path={result.get('report_path')}")
        return 0
    if args.command == "rewrite-concept-fables":
        from kg_rag.llm_config import LLMConfig
        from kg_rag.pipeline.rewrite_concept_fables import rewrite_concept_fables

        config = LLMConfig.from_env() if args.mode == "llm" else None
        result = rewrite_concept_fables(
            run_dir=args.run_dir,
            status=args.status,
            language=args.language,
            mode=args.mode,
            retry=args.retry,
            config=config,
        )
        print(f"rewrite_summary_path={result['rewrite_summary_path']}")
        print(f"rewritten_count={result['rewritten_count']}")
        print(f"skipped_count={result['skipped_count']}")
        print(f"failed_count={result['failed_count']}")
        return 0

    parser.print_help()
    return 0
