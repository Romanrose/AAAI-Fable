# Core80 Challenge selection

This module rebuilds Core80 from the full mechanism collection using the
effective P90/Top-K constraints as the only difficulty and closure source.

```bash
python -m kg_rag.core80_challenge.selection prepare
python -m kg_rag.core80_challenge.selection serve-review --port 8771
python -m kg_rag.core80_challenge.selection status
python -m kg_rag.core80_challenge.selection freeze
```

`prepare` excludes invalid mechanisms, empty effective edge sets,
`passthrough_infeasible`, broken endpoint closure, missing forbidden terms, and
source-hash mismatches. It writes deterministic initial and reserve queues.

Review decisions are append-only and irreversible. A rejection activates the
next unused row from the same subject/difficulty reserve queue. `freeze` fails
until every quota has real approval events, then writes `core80.jsonl`,
`core20_robust.jsonl`, `core12_human.jsonl`, and
`stage1_frozen_inputs.jsonl`. A frozen manifest cannot be silently replaced.

## Shared experiment boundary

Do not reuse this selection package as a scratch area. Create a separate workspace in [`kg_rag/shared/`](../../shared/README.md) under the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
