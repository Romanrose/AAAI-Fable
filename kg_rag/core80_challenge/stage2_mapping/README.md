# Core80 Challenge — Stage 2 structural mapping

This package implements the frozen Stage 2 protocol without running a model at
import time.  Every `(scope, replicate, concept, method)` task produces one
terminal, atomically-written run record and exactly one externally visible
Mapping Plan.  The Copycat-inspired method may compare three internal
candidates; those candidates remain method trace data and are never treated as
statistical samples.

## Methods

- `direct_llm`: one-pass direct mapping.
- `subconcept_modular`: frozen node mapping followed by relation mapping.
- `sme_inspired`: source-graph generation followed by deterministic one-to-one
  systematicity matching.
- `plan_reflect`: one draft and one global critique/rewrite.
- `llm_guided_copycat`: relation activation, three-candidate competition,
  structural and low-temperature semantic validation, lexicographic selection,
  and at most one targeted repair.

The formal task matrix contains 400 Core80 main runs, 200 additional Core20
stability runs, and 100 Core20 model-capacity runs.  `build_tasks` enforces these
counts by default.  Tests can opt out with `require_full_design=False`.

## Input contract

`normalize_frozen_input` accepts the selection package's frozen record.  If an
`effective_constraints` object exists, its `selected_node_ids` and
`selected_edge_ids` override all raw must-preserve fields.  The module rejects
unknown IDs and edges whose endpoints fall outside the effective node set.

## Human review

`export_core12_review` writes 60 method-blind items and 180 blank assignments
for three reviewers.  A separate private key retains method identity.  Review
import requires exact node/edge coverage and derives Node Accuracy, Edge
Accuracy, Direction Accuracy, and Mapping System EM mechanically.  The summary
first takes three-reviewer majority votes for each node and edge, then uses one
concept/method item as the statistical unit. It explicitly limits claims to the
balanced Core12 subset.

The local review website keeps method identity hidden, stores unfinished drafts
in the current browser, and appends formal submissions to
`human_review_completed.jsonl`. Formal submissions are immutable; identical
retries are idempotent and conflicting replacements are rejected. The completed
file can be passed directly to `import_and_summarize_reviews`.

## Independent LLM judge

`llm_judge.py` adds a post-hoc evaluator without changing the frozen Stage 2
generation protocol. The judge receives only the effective graph and an
anonymous Mapping Plan; method identity, generator model, automatic metrics,
and internal traces are excluded from its prompt. It returns exact per-node and
per-edge labels plus four anchored ratings. Metrics are then derived
mechanically rather than asking the model for a weighted total score.

The frozen design contains 400 main task slots and two extra blind judge
replicates for all 100 Core20 plans, for 600 terminal slots. A missing source
plan remains a terminal zero under intention-to-treat and triggers no judge
call. Judge parse failures are terminal and are not regenerated. Once all 180
human assignments are complete, `calibrate-judge` reports pooled label
agreement, Cohen's kappa, and Spearman correlations on the balanced Core12.

## Commands

```bash
python -m kg_rag.core80_challenge.stage2_mapping build-tasks --help
python -m kg_rag.core80_challenge.stage2_mapping run --help
python -m kg_rag.core80_challenge.stage2_mapping aggregate --help
python -m kg_rag.core80_challenge.stage2_mapping freeze-current-plans --help
python -m kg_rag.core80_challenge.stage2_mapping export-core12-review --help
python -m kg_rag.core80_challenge.stage2_mapping serve-review \
  --review-root data/derived/kg_rag/core80_challenge/core80-challenge-v3/stage2/core12_human_review \
  --port 8774
python -m kg_rag.core80_challenge.stage2_mapping freeze-judge-protocol --help
python -m kg_rag.core80_challenge.stage2_mapping build-judge-tasks --help
python -m kg_rag.core80_challenge.stage2_mapping judge-canary --help
python -m kg_rag.core80_challenge.stage2_mapping run-judge --help
python -m kg_rag.core80_challenge.stage2_mapping aggregate-judge --help
python -m kg_rag.core80_challenge.stage2_mapping calibrate-judge --help
```

`run` defaults to four workers. The task file freezes the explicit model for
each run (`deepseek-v4-flash`, or `deepseek-v4-pro` only for the registered
capacity scope), and the runner rejects a client configured for another model.
No model fallback is implemented.

## Shared experiment boundary

New mapping evaluations must be isolated in [`kg_rag/shared/<experiment-id>/`](../../shared/README.md). Do not edit this frozen protocol or write exploratory results here; follow the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
