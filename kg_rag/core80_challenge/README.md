# Core80 Challenge

This package contains the new, isolated Stage 2 structural-mapping and Stage 3
fable-generation experiments.  It never reads legacy mapping rankings or story
selection results.

The formal dependency chain is:

```text
full6574 mechanisms + effective constraints
  -> deterministic Core80 queue
  -> human approve/reject gate
  -> frozen Core80/Core20/Core12 + protocol
  -> Stage 2 mapping
  -> Stage 3 generation
```

All generated artifacts belong under
`data/derived/kg_rag/core80_challenge/<experiment_id>/`; code directories never
contain experiment results.

## Safety and reproducibility

- The effective P90 node/edge set is the only formal evaluation denominator.
- `passthrough_infeasible` records and records without effective edges are not
  eligible for the challenge set.
- A terminal failed run is a result and is never silently regenerated.
- Every LLM call records the model, prompt hash, request ID when supplied,
  usage, latency, retry count, and raw-response hash.
- The primary model is explicitly `deepseek-v4-flash`; no fallback is allowed.
- Human results remain pending until real append-only review records exist.

Run the command overview with:

```bash
python -m kg_rag.core80_challenge --help
```

The executable stage commands are isolated from legacy experiments:

```bash
python -m kg_rag.core80_challenge.selection --help
python -m kg_rag.core80_challenge.stage2_mapping --help
python -m kg_rag.core80_challenge.stage3_fable --help
python -m kg_rag.core80_challenge.stage3-fable-six --help
```

`stage3-fable-six/` is a separate Stage 3 protocol variant: it retains the
original exact-span structural evaluation, while replacing the four-dimension
story-only judge with the existing six-dimension story rubric. Its artifacts
must not be pooled with `stage3_fable/` results.

The formal order is enforced rather than advisory: selection cannot freeze
before 80 real approvals; Stage 3 input construction requires 80 successful,
hash-frozen plans from the current method. Both experiment runners use four
workers by default, write one checkpoint per task, and treat invalid or failed
outputs as terminal evidence.

## Shared experiment boundary

`core80_challenge/shared/` is an internal implementation package. New personal or collaborative evaluations belong in [`kg_rag/shared/<experiment-id>/`](../shared/README.md), with generated outputs in `data/derived/kg_rag/shared/<experiment-id>/`; see the [shared experiment policy](../SHARED_EXPERIMENTS.md).
