# Core240-Confirm

This workflow freezes a new confirmatory set that is disjoint by concept ID and
canonical name from the legacy Core80, Copycat Dev40, and Copycat Test80.

The selection target is four subjects times 60 concepts.  Each subject uses the
same effective-graph difficulty allocation: low=21, medium=18, high=21.  Rejects
are replaced only from the same subject and difficulty stratum.

```bash
uv run python -m kg_rag.core80_challenge.core240_confirm prepare
uv run python -m kg_rag.core80_challenge.core240_confirm serve-review --port 8782
uv run python -m kg_rag.core80_challenge.core240_confirm status
uv run python -m kg_rag.core80_challenge.core240_confirm freeze
```

All review decisions are append-only and hash chained.  `freeze` remains blocked
until 240 genuine approvals exist.  The frozen output also preselects a balanced
Core40 stability subset and Core24 human-evaluation subset.

## Stage 2 and independent Judge CLI

The post-review command surface keeps every frozen artifact under
`data/derived/kg_rag/core80_challenge/core240-confirm-v1/` by default:

```bash
# Freeze the generation protocol and its 240 x five-method task matrix.
uv run python -m kg_rag.core80_challenge.core240_confirm freeze-stage2
uv run python -m kg_rag.core80_challenge.core240_confirm build-tasks

# Checkpoints are resumable; --task-key may be repeated for a canary batch.
uv run python -m kg_rag.core80_challenge.core240_confirm run --workers 4
uv run python -m kg_rag.core80_challenge.core240_confirm aggregate

# Freeze and execute the method-blind independent Judge matrix.
uv run python -m kg_rag.core80_challenge.core240_confirm freeze-judge
uv run python -m kg_rag.core80_challenge.core240_confirm build-judge-tasks
uv run python -m kg_rag.core80_challenge.core240_confirm run-judge --workers 4
uv run python -m kg_rag.core80_challenge.core240_confirm aggregate-judge
```

The default Stage-2 artifacts are `stage2/protocol.json`, `stage2/tasks.jsonl`,
checkpoint files, and `stage2/run_index.jsonl`.  Judge artifacts use the
parallel `judge/` directory.  All paths can be overridden explicitly.  Judge
tasks are method-blind and resumable, and `aggregate-judge` remains blocked
until all 1,200 frozen Judge slots have terminal checkpoints; it never falls
back to the legacy Core80 Judge design.

## Shared experiment boundary

Keep exploratory variants outside this frozen confirmation protocol. Create them under [`kg_rag/shared/`](../../shared/README.md) and follow the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
