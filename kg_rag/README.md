# kg_rag

Minimal Python scaffold for GraphRAG work in `AAAI-Fable`.

This package intentionally starts small. It is not yet a full pipeline.

Current scope:

- define a Python project entrypoint
- centralize dataset and output paths
- provide a CLI health check
- normalize K12-KGraph into one enriched offline artifact
- provide Neo4j loading and subgraph query entrypoints
- reserve a stable package location for future ingestion and retrieval modules

Planned next steps:

1. improve query ranking and neighborhood selection
2. package retrieved subgraphs into LLM-ready context blocks
3. add GraphRAG prompt/context assembly
4. connect downstream structure mapping and generation

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
```
