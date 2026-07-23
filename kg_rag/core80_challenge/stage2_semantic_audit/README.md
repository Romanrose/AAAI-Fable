# Stage 2 source-only semantic audit

This isolated post-hoc evaluation audits already-frozen Stage 2 Mapping Plans.
It does not rerun generation or change the source records.

The earlier independent Judge could see target-linked Mapping Plan fields such
as target IDs, `story_relation_type`, `direction_preserved`, and
`mapping_type`. This audit removes those fields, deterministically anonymizes
and shuffles source-node IDs, and redacts exact target terms, forbidden terms,
and target graph IDs before a method-blind Judge sees the source material.

The Judge proposes a one-to-one target-node-to-anonymous-source-node alignment
and source-edge choices. The evaluator then mechanically derives endpoint
consistency and, for directional target relations, direction from that
alignment and the anonymous source graph; it does not accept self-reported
endpoint or direction booleans. Node evidence must quote the selected source
carrier, and edge evidence must quote the selected source relation.

The primary metrics are deliberately separated:

- **plan availability and structural validity**: end-to-end reliability;
- **source-only reverse recovery**: evidence-grounded node roles, mechanical
  edge endpoints, relation semantics, and direction only for directional
  target relations;
- **mechanistic-subgraph recovery**: a stricter EM that excludes weak
  `relates_to` edge checks; it is reported only for graphs with at least one
  directional mechanism edge;
- **domain class**: identity/translation, near-domain instantiation,
  cross-domain analogy, or uncertain;
- **strict cross-domain reverse EM**: all reverse-recovery fields correct,
  domain class is cross-domain, and raw lexical target leakage is absent;
- **two falsification controls**: 20 endpoint-reversal tasks and 20
  cross-subject target-swap tasks. The four source concepts are shared by all
  methods and are structurally valid for every method.

The main table uses all 400 frozen concept/method slots (ITT): missing or
structurally invalid source plans score zero and are not sent to the Judge. A
secondary table reports recovery conditional on a valid source plan.

The audit is still post-hoc: its inputs are canonical Stage 2 plans, because
the raw generator JSON payload was not frozen. It evaluates
**canonical-plan source-only recoverability**, not a claim that every source
edge was independently emitted by the generator. It therefore cannot
establish how much earlier structural correctness came from canonicalization
defaults. Human calibration remains required for publication claims about
cross-domain quality.

Example:

```bash
python -m kg_rag.core80_challenge.stage2_semantic_audit freeze \
  --generation-index data/derived/kg_rag/core80_challenge/restart80-full-graph-five-methods-v1/run_index.jsonl \
  --frozen-inputs data/derived/kg_rag/core80_challenge/restart80-full-graph-v1/selection/full_graph_inputs.jsonl \
  --output-dir data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4

python -m kg_rag.core80_challenge.stage2_semantic_audit run \
  --protocol data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/protocol.json \
  --generation-index data/derived/kg_rag/core80_challenge/restart80-full-graph-five-methods-v1/run_index.jsonl \
  --frozen-inputs data/derived/kg_rag/core80_challenge/restart80-full-graph-v1/selection/full_graph_inputs.jsonl \
  --source-views data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/source_views.jsonl \
  --tasks data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/tasks.jsonl \
  --output-root data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/run \
  --workers 4

python -m kg_rag.core80_challenge.stage2_semantic_audit aggregate \
  --protocol data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/protocol.json \
  --tasks data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/tasks.jsonl \
  --output-root data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/run \
  --output data/derived/kg_rag/core80_challenge/restart80-full-graph-source-only-semantic-audit-v4/run_index.jsonl \
  --require-complete
```

## Shared experiment boundary

New semantic-audit variants belong in [`kg_rag/shared/<experiment-id>/`](../../shared/README.md), with separate derived outputs. Follow the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
