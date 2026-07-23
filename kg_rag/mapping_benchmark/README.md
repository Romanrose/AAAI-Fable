# Core80 structural mapping benchmark

This package implements the second Concept2Fable experiment only:

```text
Approved MechanismGraph -> Mapping Plan -> plan-level evaluation
```

It does not generate fables and does not run reverse story alignment.

## Methods

- `standard`: single-pass LLM node-and-edge mapping.
- `subconcept_first`: frozen node mapping followed by edge mapping.
- `sme_inspired`: LLM source schema followed by deterministic one-to-one relational matching.
- `deterministic_copycat`: existing deterministic Copycat-inspired mapper.
- `llm_guided_copycat`: three LLM proposals with structural ranking and constrained refinement.

Every method emits three candidates using the same approved Core80 inputs. Plans are normalized to
an explicit story-side graph so one-to-one correspondence and mapped edge endpoints can be checked.

## Freeze the protocol

```bash
python3 -m kg_rag.mapping_benchmark build-protocol \
  --preparation-root data/derived/kg_rag/m2na_v2/full6574/core80 \
  --output-root data/derived/kg_rag/mapping_benchmark/core80 \
  --model deepseek-chat
```

## Run

Start with one concept:

```bash
python3 -m kg_rag.mapping_benchmark run \
  --preparation-root data/derived/kg_rag/m2na_v2/full6574/core80 \
  --output-root data/derived/kg_rag/mapping_benchmark/core80 \
  --model deepseek-chat \
  --concept-limit 1
```

After inspecting all five method outputs, remove `--concept-limit` to run Core80. Existing valid
plans are reused by default; pass `--rerun` only when an intentional rerun is required.

The frozen protocol records the plan schema and every method's prompt, adapter, pipeline, and
matcher version. Each generated plan stores the protocol hash in its provenance. Resume therefore
reuses a plan only when its structure is valid and it belongs to the current protocol; changing an
implementation version forces the affected benchmark run to be regenerated.

The complete Core80 run contains 80 concepts × 5 methods × 3 candidates = 1,200 mapping plans.
Run the one-concept smoke test first because the complete run requires roughly one thousand model
calls, depending on whether SME source-graph repair is triggered.

Automatic coverage and format metrics are diagnostics, not semantic correctness claims. The
generated `mapping_review.csv` contains the independent human-review fields required by the paper's
second experiment table.

## Current automatic results

The frozen Core80 run contains 80 concepts (20 per subject), five methods, and three candidates per
method. It produced 1,200 mapping plans, with 240 plans for each method. All values below are
percentages. `Direction Claim` measures whether a plan explicitly claims to preserve direction; it
is not the human-judged direction accuracy.

| Method | Valid ↑ | Node Coverage ↑ | Edge Coverage ↑ | 1:1 Mapping ↑ | Direction Claim ↑ | Carrier Div. ↑ | Relation Div. ↑ | Leakage ↓ | Template Issue ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Standard Mapping | **100.0** | **100.0** | **100.0** | **100.0** | **100.0** | 99.8 | 98.7 | 12.9 | 3.7 |
| Subconcept-first | **100.0** | **100.0** | **100.0** | **100.0** | **100.0** | 99.4 | 89.3 | **0.8** | 23.7 |
| SME-inspired | 98.8 | **100.0** | 99.4 | **100.0** | **100.0** | **100.0** | **99.9** | **0.4** | **0.0** |
| Deterministic Copycat | **100.0** | **100.0** | **100.0** | **100.0** | **100.0** | **100.0** | 44.7 | 6.2 | 95.0 |
| LLM-guided Copycat | **100.0** | **100.0** | **100.0** | **100.0** | **100.0** | **100.0** | 97.2 | 6.2 | 6.2 |

Three SME-inspired candidates did not cover every must-preserve edge and are retained as method
failures rather than repeatedly resampled. Standard Mapping has the highest lexical leakage rate.
Deterministic Copycat has the highest template-issue rate and the lowest relation diversity.
LLM-guided Copycat reaches 100% structural validity with 97.2% relation diversity and a 6.2%
template-issue rate. These observations remain automatic diagnostics and do not establish semantic
mapping superiority.

The source report is
`data/derived/kg_rag/mapping_benchmark/core80/automatic_report.md`.

## Pending paper main table

The paper's main comparison requires independent semantic review. No value should be filled from
automatic ID coverage or the model's direction claim.

| Method | Node Acc. ↑ | Edge Acc. ↑ | Direction Acc. ↑ | System EM ↑ | Systematicity ↑ | Domain Suitability ↑ | Narratability ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Standard Mapping | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Subconcept-first | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| SME-inspired | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Deterministic Copycat | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| LLM-guided Copycat | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

Use `data/derived/kg_rag/mapping_benchmark/core80/mapping_review.csv` for this review. The required
human judgments are node-mapping accuracy, edge-mapping accuracy, actual direction accuracy,
mapping-system exact match, structural systematicity, source-domain suitability, and mapping-plan
narratability.

## Eight-metric evaluation plan

The existing 1,200 Mapping Plans can be evaluated without another model-generation run:

```bash
python3 -m kg_rag.mapping_benchmark evaluate \
  --preparation-root data/derived/kg_rag/m2na_v2/full6574/core80 \
  --output-root data/derived/kg_rag/mapping_benchmark/core80
```

The evaluation produces six automatic diagnostics and two human-review fields:

| Metric | Evaluation source | Status |
|---|---|---|
| `semantic_mapping_score` | Human semantic judgment | Pending manual review |
| `structural_preservation_score` | Required nodes, required edges, main path, branch/feedback structure | Computed |
| `complexity_robustness_score` | High-complexity automatic selection proxy divided by overall proxy | Computed as an automatic proxy |
| `leakage_control_score` | `1 - mapping_lexical_leakage` | Computed |
| `relation_diversity_score` | Existing `relation_diversity` | Computed |
| `plan_consistency_score` | Endpoint, direction, reference, and narrative-field consistency | Computed |
| `human_semantic_quality` | Independent 1–5 review | Pending manual review |
| `human_narrative_usefulness` | Independent 1–5 review | Pending manual review |

`automatic_selection_proxy_score` is an internal sampling aid only. It combines structural
preservation, plan consistency, leakage control, and relation diversity to select informative
review cases; it is not a paper metric and must not be reported as semantic accuracy.

The evaluation writes:

- `metrics_master_table.csv/jsonl`: one row per Mapping Plan;
- `metrics_method_summary.csv/jsonl`: method-level averages and complexity robustness proxy;
- `metrics_subject_summary.csv`: subject-by-method results;
- `metrics_complexity_summary.csv`: low/medium/high complexity results;
- `mapping_review_focused.csv`: 60 focused review rows, 12 distinct concepts per method;
- `eight_metric_report.md`: automatic eight-metric status report;
- `evaluation_manifest.json`: counts, protocol hash, and output manifest.

The focused review set contains, for each method, three high-proxy cases, three low-proxy cases,
three high-complexity cases, and three cases with the largest method-level disagreement. Human
review must fill `human_semantic_quality` and `human_narrative_usefulness`; automatic coverage and
the model's direction claim must not be copied into those fields.

## Shared experiment boundary

Do not add exploratory methods or review results to this frozen Core80 benchmark. Create a separate workspace under [`kg_rag/shared/<experiment-id>/`](../shared/README.md) with its own protocol and derived-output root; see the [shared experiment policy](../SHARED_EXPERIMENTS.md).
