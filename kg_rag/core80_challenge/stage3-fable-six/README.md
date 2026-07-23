# Core80 Challenge — Stage 3 with the six-dimension rubric

This isolated Stage 3 variant uses the eight frozen generation conditions from
`stage3_fable`, including `concept_name_only`, which receives only the frozen
concept name, and `concept_direct`, which receives only the frozen
concept name and definition and never receives a mechanism graph or Mapping
Plan, and `graph_plus_plan_one_shot`, which treats the effective graph as
structural truth and the Mapping Plan as narrative guidance. It replaces the
four-dimension story-only evaluator with the
project's existing six-dimension rubric:

```text
faithfulness, implicitness, mapping_clarity,
readability, pedagogical_value, novelty
```

It uses the v4 span-ID structural evaluator. Python first freezes exact story
sentence spans, and the model may only select their IDs. Invalid
evaluator payloads receive up to two method-blind repair attempts; persistent
format failures are reported as `evaluator_failure`, not story-generation
failures. Structure and six-dimension evaluation run independently, so one
judge cannot suppress the other judge's result. The six-dimension judge
receives only the anonymous final story, the effective mechanism graph, and
the forbidden-term list. It never receives a Mapping Plan, method ID,
generation condition, automatic structure metrics, or internal traces.
If an edge is labeled semantically correct while its direction is labeled
incorrect, v4 deterministically canonicalizes the edge status to `incorrect`
and retains the selected evidence and direction flag; this no longer discards
the entire evaluation.

The dimension definitions, weights, hard flags, and accept/revise/reject rule
are imported from `kg_rag.evaluation.rubric`; this directory only adapts that
unchanged rubric to the method-blind Stage 3 inputs.

The output therefore separates two claims:

- structural recoverability: node/edge/direction accuracy and System EM;
- six-dimension fable quality: the existing weighted rubric and hard flags.

From v7 onward, producing a non-empty visible story is recorded separately
from format compliance. The 450--750 Unicode-code-point interval and forbidden
term check remain frozen measurements, but a length deviation is not labeled
as a generation failure. Reports expose generation completion, length
compliance, leakage freedom, and evaluator completion as separate rates.
Every new task also freezes the generation prompt version and prompt-file
SHA-256 in its task hash to prevent accidental cross-prompt story reuse.

The main matrix contains 80 concepts × 8 conditions = 640 visible stories.
Core12 human review contains 12 concepts × 8 conditions × 3 raters = 288
assignments in each locked pass.

The Core12 human packet likewise uses two locked passes. Pass 1 is story-only
for implicitness, readability, novelty, and surface flags. Pass 2 adds the
effective mechanism graph for faithfulness, mapping clarity, pedagogical
value, and mechanism-specific flags. Both passes remain method blind.

This module is intentionally separate from `stage3_fable/`; outputs and
protocols must not be mixed across the two variants.

## Commands

```bash
python -m kg_rag.core80_challenge.stage3-fable-six freeze-protocol --help
python -m kg_rag.core80_challenge.stage3-fable-six repair-official-plan --help
python -m kg_rag.core80_challenge.stage3-fable-six freeze-stage3-core80 --help
python -m kg_rag.core80_challenge.stage3-fable-six freeze-stage3-core12 --help
python -m kg_rag.core80_challenge.stage3-fable-six build-main --help
python -m kg_rag.core80_challenge.stage3-fable-six build-core12-graph-plus-plan-pilot --help
python -m kg_rag.core80_challenge.stage3-fable-six run --help
python -m kg_rag.core80_challenge.stage3-fable-six build-downstream --help
python -m kg_rag.core80_challenge.stage3-fable-six export-core12-review --help
python -m kg_rag.core80_challenge.stage3-fable-six build-tables --help
python -m kg_rag.core80_challenge.stage3-fable-six build-comparable-audit --help
python -m kg_rag.core80_challenge.stage3-fable-six freeze-plan-ablation-core20 --help
```

The isolated Plan ablation freezes twenty non-Core12 concepts with subject and
difficulty quotas and compares four matched prompt conditions: graph only,
graph plus minimal narrative carriers, graph plus compressed structural
mapping, and graph plus the full Mapping Plan. These ablation conditions do not
alter the eight-condition main matrix or its human-review packet sizes.

`build-comparable-audit` requires complete 80-concept record sets, supports an
isolated evaluator-retry replacement, and writes deterministic 5,000-sample
concept-level bootstrap confidence intervals plus paired differences against
Mechanism Direct. It refuses incomplete evaluator coverage instead of silently
averaging only successful judge outputs.

To preserve stories from an earlier run, write rescored results to a new
directory and pass the old run as `--reuse-generation-root`. Tasks with a
visible frozen story are only re-evaluated; tasks without one are generated
normally. The two roots must be different so historical checkpoints remain
immutable.

The v5 Graph+Plan pilot changes only that condition's requested target length
from the broad validity interval to 550--700 Chinese characters. The frozen
quality gate remains 450--750 characters, and the structure and six-dimension
evaluators are unchanged. Rerun the twelve Graph+Plan tasks into a new output
root without generation reuse; retain v4 as the development baseline.
Use `build-core12-graph-plus-plan-pilot --graph-plus-plan-only` to freeze the
twelve-task v5 task list.

For a frozen single-condition Core80 confirmation run, use
`build-main --condition graph_plus_plan_one_shot`; this retains all eighty
frozen inputs but writes only the eighty selected generation tasks.

## Shared experiment boundary

Keep new story-quality evaluations in [`kg_rag/shared/<experiment-id>/`](../../shared/README.md), not in this frozen six-dimension protocol. The [shared experiment policy](../../SHARED_EXPERIMENTS.md) applies.
