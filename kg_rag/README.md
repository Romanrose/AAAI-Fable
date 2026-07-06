# kg_rag

Graph-grounded Concept-to-Fable prototype for `AAAI-Fable`.

This package supports a local end-to-end research loop for Chinese
Concept-to-Fable / M2NA experiments:

Current scope:

- define a Python project entrypoint
- centralize dataset and output paths
- provide a CLI health check
- normalize K12-KGraph into one enriched offline artifact
- provide Neo4j loading and subgraph query entrypoints
- select K12 Concept nodes
- build and enrich Chinese concept cards
- provide dual-level GraphRAG retrieval for K12 concept cards
- run staged Concept-to-Fable generation with traceable intermediate artifacts
- keep a concept-to-story alignment table
- evaluate generated fables with a six-dimensional rubric
- export JSONL / CSV / Markdown / SVG reports
- optionally call a multi-model LLM-as-Judge panel
- rewrite `revise` / `reject` samples

Workflow shape:

```text
Concept Card
-> Retrieval Agent
-> Mechanism Planner Agent
-> Analogy Planner Agent
-> Fable Writer Agent
-> Critic / Evaluator Agent
-> Revision Agent
-> Report Builder
```

The default GraphRAG mode for `run-concept-fable-batch` is `dual_level`. It
keeps raw KG edges for grounding and builds a high-level topic summary for
condition / process / effect planning. `selected_paths` is retained as an empty
compatibility field.

Current commands:

```bash
kg-rag doctor
kg-rag normalize-k12
kg-rag load-neo4j
kg-rag query-subgraph "光合作用" --preview-only
kg-rag query-subgraph "光合作用" --preview-only --pack-output-path data/derived/kg_rag/photosynthesis_pack.json
kg-rag build-prompt --pack-path data/derived/kg_rag/photosynthesis_pack.json --mode mapping
kg-rag build-structure-plan --pack-path data/derived/kg_rag/photosynthesis_pack.json --output-path data/derived/kg_rag/photosynthesis_plan.json
kg-rag build-story-prompt --plan-path data/derived/kg_rag/photosynthesis_plan.json --output-path data/derived/kg_rag/photosynthesis_story_prompt.txt
kg-rag build-review-prompt --plan-path data/derived/kg_rag/photosynthesis_plan.json --draft-path kg_rag/examples/sample_draft.txt
kg-rag review-checklist --plan-path data/derived/kg_rag/photosynthesis_plan.json --draft-path kg_rag/examples/sample_draft.txt
kg-rag run-local-demo "photosynthesis" --output-dir data/derived/kg_rag/demo_photosynthesis
kg-rag run-llm-demo "photosynthesis" --output-dir data/derived/kg_rag/llm_demo_photosynthesis
kg-rag run-batch-stories --mode local --limit 10 --output-dir data/derived/kg_rag/batch_runs/local_10
kg-rag run-batch-stories --mode llm --subject biology --limit 50 --sleep-seconds 1 --retry 2 --output-dir data/derived/kg_rag/batch_runs/biology_llm_50
kg-rag select-concept-nodes --limit-per-subject 5
kg-rag build-concept-cards --selection-path data/derived/kg_rag/concept_selection/k12_concepts.jsonl
kg-rag enrich-concept-cards --input data/derived/kg_rag/concept_cards/k12_concept_cards.raw.jsonl --output data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl --mode rules
kg-rag run-machine-eval --limit 20 --limit-per-subject 5 --no-resume
kg-rag run-concept-fable-batch \
  --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl \
  --normalized-graph-path data/derived/kg_rag/k12_kgraph_normalized.json \
  --workflow agentic \
  --retrieval-mode dual_level \
  --mode local \
  --language zh-CN \
  --limit 20 \
  --evaluate-mode rules \
  --auto-run-dir
kg-rag evaluate-batch data/derived/kg_rag/concept_runs/local_20_machine_eval --mode rules
kg-rag export-eval-report data/derived/kg_rag/concept_runs/local_20_machine_eval/eval_summary.jsonl
kg-rag rewrite-concept-fables --run-dir data/derived/kg_rag/concept_runs/local_20_machine_eval --status revise,reject --mode local
```

Six-dimensional evaluation outputs:

```text
eval_summary.jsonl
eval_summary.csv
eval_report.md
eval_analysis.svg
```

The detailed evaluation protocol and the current 20-sample machine run are documented in:

- `doc/机器评测流程.md`
- `doc/评估/README_机器评测与20条实验.md`
