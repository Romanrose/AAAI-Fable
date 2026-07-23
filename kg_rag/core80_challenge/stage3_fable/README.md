# Core80 Challenge — Stage 3

This package implements the controlled fable-generation stage. It exposes eight
frozen conditions:

1. `concept_name_only` (concept name only)
2. `concept_direct` (concept name and definition only)
3. `mechanism_direct`
4. `plan_one_shot`
5. `graph_plus_plan_one_shot`
6. `plan_self_refine`
7. `plan_best_of_3`
8. `reverse_align_targeted_revision`

Each task has exactly one externally visible `final_story`. Intermediate drafts,
candidate stories, alignments, and revisions remain in the internal trace and
are never treated as statistical samples.

The module does not configure a model. A provider-neutral
`LLMProtocol` is injected by the shared Core80 runner, which owns request IDs,
token accounting, latency, provider retry policy, checkpoints, and protocol
hashes. Invalid structured alignment payloads may receive bounded format-only
repair attempts; visible stories are never silently regenerated.

Final structure evaluation is intentionally isolated from the Mapping Plan and
method identity. Final story-quality evaluation receives only the anonymous
story. Every non-empty evidence span is rejected unless its offsets satisfy
`story[start:end] == evidence_text` exactly.

`build_main_tasks`, `build_downstream_tasks`, and `build_human_review_tasks`
freeze the 640-story main matrix, 1,200-story downstream matrix, and Core12
two-pass human-review assignments respectively. `build_summary_tables` produces
separate main automatic, Core12 human, and downstream-transfer Markdown tables.

The formal runner evaluates every visible story with the two isolated
evaluators, combines all call metadata into one terminal checkpoint, and
refuses resume when the protocol, task, Stage-1 input, or Mapping Plan hash
changes. A length/leakage quality failure is recorded as `invalid`; it is never
regenerated.

```bash
python -m kg_rag.core80_challenge.stage3_fable build-main --help
python -m kg_rag.core80_challenge.stage3_fable run --help
python -m kg_rag.core80_challenge.stage3_fable build-downstream --help
python -m kg_rag.core80_challenge.stage3_fable export-core12-review --help
python -m kg_rag.core80_challenge.stage3_fable build-tables --help
```

## Shared experiment boundary

New Stage 3 evaluations must start in [`kg_rag/shared/<experiment-id>/`](../../shared/README.md) and retain their own protocol and outputs. See the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
