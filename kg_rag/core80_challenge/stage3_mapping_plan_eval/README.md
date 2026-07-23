# Stage 3 Mapping Plan effectiveness evaluation

This isolated experiment evaluates whether exposing a frozen Copycat v4
Mapping Plan makes a story follow that mapping. It does not regenerate or
modify stories.

Every story is evaluated against the same concept-specific structural mapping,
including the matched Graph Only baseline whose generator never saw the Plan.
The Plan-aware evaluator remains blind to the generation condition and selects
only program-owned exact story span IDs.

Primary Plan-control metrics:

- node mapping realization;
- edge relation realization;
- edge direction realization;
- source-domain adherence;
- carrier consistency;
- strict Mapping System EM.

The report also carries forward mechanism accuracy, six-dimension quality, and
length compliance, then computes concept-level paired added value versus Graph
Only with deterministic bootstrap confidence intervals. This separates Plan
control benefit from mechanism or story-quality cost.

```bash
python -m kg_rag.core80_challenge.stage3_mapping_plan_eval freeze-protocol --help
python -m kg_rag.core80_challenge.stage3_mapping_plan_eval build-tasks --help
python -m kg_rag.core80_challenge.stage3_mapping_plan_eval run --help
python -m kg_rag.core80_challenge.stage3_mapping_plan_eval aggregate --help
python -m kg_rag.core80_challenge.stage3_mapping_plan_eval build-report --help
```

## Shared experiment boundary

Create new mapping-plan evaluations under [`kg_rag/shared/<experiment-id>/`](../../shared/README.md). Keep their protocol and derived outputs distinct as required by the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
