# Copycat v4 Core12 human review

This package reads the frozen Test80 inputs and the immutable Final 01 run
index. It never edits either source artifact and it does not generate human
scores.

Build the two frozen review packets:

```bash
python3 -m kg_rag.core80_challenge.stage2_mapping.human_review build \
  --run-index data/derived/kg_rag/core80_challenge/copycat-v4-iteration/final_01/run_index.jsonl \
  --frozen-inputs data/derived/kg_rag/core80_challenge/copycat-v4-iteration/selection/test80_frozen_inputs.private.jsonl \
  --output-root data/derived/kg_rag/core80_challenge/copycat-v4-iteration/final_01/human_review
```

The outcome-independent `primary_core12` is reconstructed from the frozen
Test80 inputs with a fixed seed. It keeps the Physics/High terminal failure and
therefore exposes 59 plans. Because Core12 itself was not frozen before model
generation, this packet is not a preregistered or confirmatory subset. The
website uses the separate 60-plan `calibration_core12_complete_case` packet.
That packet additionally makes one post-hoc same-cell replacement and is for
Judge calibration only; neither packet can replace the Test80
intention-to-treat denominator or support confirmatory significance claims.

Start the review website:

```bash
python3 -m kg_rag.core80_challenge.stage2_mapping.human_review serve \
  --review-root data/derived/kg_rag/core80_challenge/copycat-v4-iteration/final_01/human_review/calibration_core12_complete_case \
  --host 127.0.0.1 \
  --port 8774
```

Open `http://127.0.0.1:8774/`. Each reviewer uses one fixed reviewer slot.
Formal submissions are appended to `human_review_completed.jsonl` in the
selected review packet and cannot be overwritten through the site. Method
identity stays only in `human_review_private_key.jsonl`; public review items do
not contain generator method, model, automatic metrics, or internal traces.

## Shared experiment boundary

For a new review or evaluation design, use [`kg_rag/shared/<experiment-id>/`](../../../shared/README.md) rather than altering this packet. See the [shared experiment policy](../../../SHARED_EXPERIMENTS.md).
