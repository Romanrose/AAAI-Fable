# Restart80 information ladder

This isolated experiment compares six increasingly structured inputs on the
same 80 reviewed concepts:

1. concept name only;
2. concept seed (name and definition);
3. concept seed plus frozen adaptive retrieval evidence;
4. effective mechanism graph;
5. mechanism graph plus minimal Copycat-v4 mapping;
6. mechanism graph plus the full Copycat-v4 plan.

The sample is selected deterministically from the already reviewed, disjoint
Core240 set without consulting mapping or story outcomes. It contains 20
concepts per subject and 7/6/7 low/medium/high concepts per subject. A failed
upstream mapping remains a failed formal slot under the ITT policy.

```bash
python3 -m kg_rag.core80_challenge.restart80_ladder prepare
python3 -m kg_rag.core80_challenge.restart80_ladder run --canary --canary-id canary_001 --workers 1
python3 -m kg_rag.core80_challenge.restart80_ladder run --workers 4
python3 -m kg_rag.core80_challenge.restart80_ladder status
python3 -m kg_rag.core80_challenge.restart80_ladder aggregate
```

Outputs are written below
`data/derived/kg_rag/core80_challenge/restart80-ladder-v2/`. Frozen artifacts
refuse content drift, and terminal checkpoints are resumed rather than
overwritten.

If a canary terminates because the provider is unavailable, preserve that
attempt and use a new `--canary-id` after service is restored.

## Shared experiment boundary

New evaluation variants belong in [`kg_rag/shared/<experiment-id>/`](../../shared/README.md); keep their generated outputs in `data/derived/kg_rag/shared/`. See the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
