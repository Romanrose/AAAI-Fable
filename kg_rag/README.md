# kg_rag

Minimal Python scaffold for GraphRAG work in `AAAI-Fable`.

This package intentionally stays lightweight, but now includes the first K12
Concept-to-Fable agentic workflow.

Current scope:

- define a Python project entrypoint
- centralize dataset and output paths
- provide a CLI health check
- normalize K12-KGraph into one enriched offline artifact
- provide Neo4j loading and subgraph query entrypoints
- provide dual-level GraphRAG retrieval for K12 concept cards
- run staged Concept-to-Fable generation with traceable intermediate artifacts

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
kg-rag run-concept-fable-batch \
  --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl \
  --normalized-graph-path data/derived/kg_rag/k12_kgraph_normalized.json \
  --workflow agentic \
  --retrieval-mode dual_level \
  --mode local \
  --limit 1 \
  --output-dir data/derived/kg_rag/concept_runs/smoke_dual_level
```
