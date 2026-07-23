# Shared experiment workspace

Create one directory per new personal or collaborative experiment here:
`kg_rag/shared/<experiment-id>/`.

Read [the shared experiment policy](../SHARED_EXPERIMENTS.md) before creating
an experiment. Keep code, a frozen protocol, the experiment README, and (when
needed) its evaluator under the experiment directory:

```text
kg_rag/shared/<experiment-id>/
├─ README.md
├─ protocol.json
├─ run.py or cli.py
└─ evaluation/
```

Write generated stories, model responses, per-item judgments, failure records,
and summary tables to the matching derived directory:
`data/derived/kg_rag/shared/<experiment-id>/`. Keep the complete denominator
visible; do not replace failed items with successful samples.
