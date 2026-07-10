# M2NA V2

This package is an independent mechanism-first experiment pipeline. It does
not read or modify legacy enriched concept cards.

```text
ConceptSeed
-> GraphRAG RetrievalPackage
-> LLM MechanismRecord
-> strict validation
-> human review
-> approved mechanisms
-> standard/copycat mapping
-> shared multi-agent generation and evaluation
```

Default preparation root:

```text
data/derived/kg_rag/m2na_v2/pilot80/
```

Run the preparation stages in order:

```bash
python -m kg_rag.m2na_v2 build-seeds
python -m kg_rag.m2na_v2 retrieve
python -m kg_rag.m2na_v2 build-mechanisms --builder-model deepseek-chat
python -m kg_rag.m2na_v2 validate-mechanisms
python -m kg_rag.m2na_v2 export-review-sheet
```

`retrieve` uses target-centered adaptive graph retrieval. It keeps ranked
one-hop evidence first, then expands to at most eight two-hop paths only when
the direct structure is insufficient. A transparent curriculum-section bridge
is permitted only when the target has no core direct relation; bridge edges are
context only and cannot be cited as mechanism evidence.

For browser-based local review, run:

```bash
python -m kg_rag.m2na_v2 serve-review
```

The app binds to `127.0.0.1:8765` by default. It renders seed metadata,
retrieval decisions and paths, mechanism nodes/edges, evidence references, and
validation results. Approve/reject actions append to `mechanism_reviews.jsonl`
and refresh `mechanisms.approved.jsonl` immediately.

After the approved mechanism set is ready, build the explicit analogy layer
before story generation:

```bash
python -m kg_rag.m2na_v2 build-mappings --standard-model deepseek-chat
```

This writes three Standard and three Copycat-inspired mapping plans per
approved concept. A plan must explicitly map every `must_preserve` mechanism
node and edge, preserving edge direction, or it is placed in
`mapping_failures.jsonl` rather than entering story generation.
Use `--only-missing` to resume an interrupted build without repeating validated
Standard/Copycat plan pairs.

Review the paired plans in a local browser:

```bash
python -m kg_rag.m2na_v2 serve-mapping-review
```

The reviewer can inspect the same concept/candidate under both strategies,
approve or reject each strategy independently, and append review history to
`mapping_reviews.jsonl`.

Fill `review_decision` with `approve` or `reject`, provide a reviewer, then:

```bash
python -m kg_rag.m2na_v2 import-reviews --reviewer reviewer-name
python -m kg_rag.m2na_v2 status
python -m kg_rag.m2na_v2 run-experiment \
  --strategy both \
  --generator-model deepseek-chat \
  --judge-model deepseek-chat \
  --output-dir data/derived/kg_rag/m2na_v2/pilot80/runs/run_001
```

Official experiment results always use three candidates and at most two
revision rounds for both strategies. Any model fallback invalidates that
concept-strategy result for official evaluation.
