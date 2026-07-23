# Core80 Stage 3 Joint Fable Realization

This package is a new, isolated Stage 3 protocol.  It does not modify or read
historical `stage3_fable` or `stage3-fable-six` run records.  New artifacts
belong under a distinct experiment root such as:

```text
data/derived/kg_rag/core80_challenge/stage3-joint-bilingual-v1/
```

## Research question

Stage 3 is a joint realization task, not story generation alone:

```text
(effective mechanism graph, frozen Copycat mapping, forbidden terms, language)
  -> (final fable, final mechanism-to-narrative alignment)
```

The final alignment is a public output.  A diagnostic alignment used before a
revision remains internal, but the alignment regenerated from the final story
is stored beside `final_story` as `final_alignment`.

The experiment tests three claims:

- H1: a frozen Copycat mapping improves mechanism realization (`C2 - C1`);
- H2: reverse-alignment feedback outperforms a generic refinement with the
  same four-call budget (`C4 - C3`);
- H3: structural gains do not materially reduce narrative quality.

H3 is treated as a paired non-inferiority check on the 1--5 narrative score.
The default margin is 0.25 points and is frozen before any formal run; the
lower 95% paired-bootstrap bound for `C4 - C3` must exceed `-0.25`. At least
90% of concepts must have paired Chinese-and-English Narrative Judge results;
otherwise H3 is reported as inconclusive rather than filling missing Judge
calls with zero.

It does **not** test student learning outcomes.

## Main conditions

| ID | Condition | Frozen input | Generation-stage calls |
|---|---|---|---:|
| C1 | `mechanism_direct_joint` | masked mechanism graph | 2 |
| C2 | `copycat_one_shot_joint` | masked graph + frozen Copycat mapping | 2 |
| C3 | `copycat_generic_self_refine` | C2 input + generic critique/rewrite | 4 |
| C4 | `copycat_reverse_align_revision` | C2 input + reverse alignment/targeted revision | 4 |

C3 and C4 have the same draft, feedback, revision, and final-alignment call
slots.  The main protocol intentionally excludes Best-of-3.  A future
Best-of-3 experiment must compare quality-only and alignment-aware selectors
under the same three-sample budget and remain outside this main matrix.

C4 is mechanically local, not only prompt-local: every patch must address a
localized defect ID, every defect must be covered, insertions must anchor to
defect evidence unless a missing item has no span, and all replacement text
combined is capped at 35% of the draft length. Chinese uses Unicode code points
for this cap and English uses whitespace-delimited words. Violations terminate
the task instead of falling back to a global rewrite.

The bilingual Test80 matrix contains:

```text
80 concepts x 2 languages x 4 conditions = 640 final joint outputs
```

The frozen generation/alignment budget is 1,920 calls: C1 and C2 use two
calls per language-concept, while C3 and C4 use four. Three independent final
evaluators add 1,920 calls, for 3,840 expected calls before network retries.

Chinese and English share the same mechanism graph and frozen mapping, but
have separate stories, evidence spans, alignments, and forbidden-term lists.

## Formal output

The core of each successful task is shown below; provenance fields such as the
schema versions, input/output hashes, task key, concept metadata, and source
hashes surround this payload in the actual record:

```json
{
  "final_story": "...",
  "final_alignment": {
    "span_catalog": [
      {"span_id": "s001", "text": "...", "start": 0, "end": 25},
      {"span_id": "s002", "text": "...", "start": 26, "end": 51}
    ],
    "story_elements": [
      {
        "story_element_id": "event_02",
        "element_type": "event",
        "description": "the action that triggers the outcome",
        "evidence_span_ids": ["s001"]
      },
      {
        "story_element_id": "event_03",
        "element_type": "outcome",
        "description": "the resulting change",
        "evidence_span_ids": ["s002"]
      }
    ],
    "node_alignments": [
      {
        "mechanism_node_id": "n1",
        "story_element_ids": ["event_02"],
        "evidence_span_ids": ["s001"],
        "status": "realized"
      },
      {
        "mechanism_node_id": "n2",
        "story_element_ids": ["event_03"],
        "evidence_span_ids": ["s002"],
        "status": "realized"
      }
    ],
    "edge_alignments": [
      {
        "mechanism_edge_id": "e3",
        "story_element_ids": ["event_02", "event_03"],
        "evidence_span_ids": ["s001", "s002"],
        "direction": "correct",
        "status": "realized"
      }
    ]
  }
}
```

Every effective node and edge must occur exactly once. Multiple exact spans
are allowed. Python owns the span catalog and validates each entry using
`story[start:end] == text`; the model can only reference frozen span IDs.

## Independent evaluation

Three evaluator calls have strict input allowlists:

1. Story recovery receives only `(P, Y)` and computes Node Accuracy, Edge
   Accuracy, Direction Accuracy, and Story System EM.
2. Alignment verification receives only `(P, Y, L)` and computes Alignment
   Item Accuracy, Evidence Validity, and Alignment System EM.
3. Narrative evaluation receives only anonymous `Y` and scores coherence,
   readability, fable quality, and implicitness.

Target-term leakage is deterministic language-specific string matching, not an
LLM judgment.  The primary metrics are:

```text
Joint EM       = Story System EM AND Alignment System EM
Valid Joint EM = Joint EM AND no target-term leakage
```

Failures remain in the fixed denominator for structural metrics. If one of the
two structural Judges fails, only that Judge's side scores zero; a successful
independent Judge is retained. Narrative quality remains on its declared 1--5
scale, so missing Narrative Judge calls are not silently converted to zero and
their paired coverage is reported separately. Paired bootstrap resamples
concepts. For macro bilingual results, Chinese and English are averaged within
each concept before resampling.

## Bilingual lexicon gate

Existing Core80 inputs contain mostly Chinese forbidden terms.  A formal run
therefore requires a separately frozen JSONL lexicon with one row per concept:

```json
{
  "concept_id": "biology_...",
  "forbidden_terms_by_language": {
    "zh": ["目标术语"],
    "en": ["target term", "target-term variant"]
  },
  "review_status": "approved",
  "source_stage1_input_sha256": "..."
}
```

Missing terms, a stale Stage-1 hash, or a review status other than `approved`
block `freeze-inputs`. All known target-term surface variants should be listed;
masking and deterministic leakage checks use this same frozen lexicon.

## Freeze order

The current Stage-2 run index contains all comparison methods, so the first
command filters and validates only successful `llm_guided_copycat_v4` plans.
It refuses duplicate successful plans and refuses to freeze fewer than 80.
`freeze-protocol` then recomputes the joint inputs from all three source
artifacts; a self-hashed, manually assembled input file cannot bypass the
official-plan or bilingual-lexicon gates:

```bash
python -m kg_rag.core80_challenge.stage3_joint freeze-copycat-plans \
  --stage1-inputs /path/to/test80_frozen_inputs.jsonl \
  --stage2-run-index /path/to/primary_run_index.jsonl \
  --stage2-run-index /path/to/documented_recovery_run_index.jsonl \
  --output /path/to/official_copycat_v4_plans.jsonl

python -m kg_rag.core80_challenge.stage3_joint build-term-lexicon-template \
  --stage1-inputs /path/to/test80_frozen_inputs.jsonl \
  --output /path/to/bilingual_terms.review.jsonl

# Fill English variants and set review_status=approved before this step.
python -m kg_rag.core80_challenge.stage3_joint freeze-inputs \
  --stage1-inputs /path/to/test80_frozen_inputs.jsonl \
  --official-mapping-plans /path/to/official_copycat_v4_plans.jsonl \
  --term-lexicon /path/to/bilingual_terms.review.jsonl \
  --output /path/to/stage3_joint_inputs.jsonl

python -m kg_rag.core80_challenge.stage3_joint freeze-protocol \
  --experiment-root /path/to/stage3-joint-bilingual-v1 \
  --experiment-id stage3-joint-bilingual-v1 \
  --stage1-inputs /path/to/test80_frozen_inputs.jsonl \
  --official-mapping-plans /path/to/official_copycat_v4_plans.jsonl \
  --term-lexicon /path/to/bilingual_terms.review.jsonl \
  --frozen-inputs /path/to/stage3_joint_inputs.jsonl \
  --core12 /path/to/preselected_core12.jsonl
```

The Core12 source is hashed before generation and must contain one concept from
every subject-by-difficulty cell. This prevents selecting the human subset after
seeing automatic results.

## Core12 human validation

The balanced Core12 packet contains 96 story-language-condition items.  With
three raters, each locked pass contains 288 assignments:

- Pass 1: anonymous story only, for narrative quality;
- Pass 2: mechanism graph, story, and final alignment, for mechanism and
  alignment validation.

Pass 1 must be locked before Pass 2 is shown.  Conditions and method identity
remain hidden in both passes. Reviewer packets and the private condition key are
written to disjoint directories so a static review site cannot expose the key.
Anonymous story IDs, concept blocks, and display orders use an experiment-level
secret HMAC rather than a public deterministic seed. The public manifest stores
only the secret commitment; the secret and condition key remain together under
the experiment's `private/core12_human_review/` directory.

## Commands

```bash
python -m kg_rag.core80_challenge.stage3_joint build-term-lexicon-template --help
python -m kg_rag.core80_challenge.stage3_joint freeze-copycat-plans --help
python -m kg_rag.core80_challenge.stage3_joint freeze-inputs --help
python -m kg_rag.core80_challenge.stage3_joint freeze-protocol --help
python -m kg_rag.core80_challenge.stage3_joint build-main --help
python -m kg_rag.core80_challenge.stage3_joint run --help
python -m kg_rag.core80_challenge.stage3_joint aggregate --help
python -m kg_rag.core80_challenge.stage3_joint export-core12-review --help
python -m kg_rag.core80_challenge.stage3_joint build-tables --help
```

No command defaults to an old Stage 3 result directory.  Formal run commands
require an explicit experiment root with a matching joint-protocol marker.
The table command reads its Bootstrap sample count, seed, H3 margin, and minimum
paired coverage only from the frozen protocol. It writes a main table, bilingual
tables, structural/alignment diagnostics, completion coverage, paired causal
contrasts, and the H3 non-inferiority decision.

## Shared experiment boundary

Do not add a new joint condition to this frozen experiment in place. Create it in [`kg_rag/shared/<experiment-id>/`](../../shared/README.md) under the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
