# Copycat v4 isolated experiment

This package develops Copycat v4 without changing the archived Stage 2 v3
implementation or outputs. Prompt text is inline in `method.py`; therefore the
prompt bundle AST-extracts all four actual LLM call sites and content-addresses
the complete method source, rather than trusting version labels alone.

Formal order:

```bash
python -m kg_rag.core80_challenge.stage2_copycat_v4 freeze-prompt-bundle \
  --output /path/to/dev_01/prompt_bundle.json

python -m kg_rag.core80_challenge.stage2_copycat_v4 freeze-protocol \
  --experiment-id copycat-v4-dev \
  --phase development --iteration-id dev_01 \
  --base-v3-protocol /path/to/core80-v3/protocol.json \
  --frozen-inputs /path/to/dev40_inputs.jsonl \
  --prompt-bundle /path/to/dev_01/prompt_bundle.json \
  --output /path/to/dev_01/protocol.json

python -m kg_rag.core80_challenge.stage2_copycat_v4 build-tasks \
  --protocol /path/to/dev_01/protocol.json \
  --frozen-inputs /path/to/dev40_inputs.jsonl \
  --output /path/to/dev_01/tasks.jsonl

python -m kg_rag.core80_challenge.stage2_copycat_v4 run \
  --protocol /path/to/dev_01/protocol.json \
  --tasks /path/to/dev_01/tasks.jsonl \
  --frozen-inputs /path/to/dev40_inputs.jsonl \
  --output-root /path/to/dev_01/runs --workers 4

python -m kg_rag.core80_challenge.stage2_copycat_v4 aggregate \
  --protocol /path/to/dev_01/protocol.json \
  --tasks /path/to/dev_01/tasks.jsonl \
  --output-root /path/to/dev_01/runs \
  --output /path/to/dev_01/run_index.jsonl --require-complete
```

Use `run --task-key ... --dry-run` to validate a canary selection without an
LLM request. Real `run` reads the existing `LLMConfig` environment, forces the
frozen `deepseek-v4-flash` model, permits four workers at most, and uses no
model fallback. Checkpoints are immutable terminal records; `aggregate` checks
their task, protocol, and record hashes before writing the index.

## Shared experiment boundary

Place new Copycat evaluations in [`kg_rag/shared/<experiment-id>/`](../../shared/README.md), not in this frozen v4 directory. The [shared experiment policy](../../SHARED_EXPERIMENTS.md) defines the required protocol and output layout.
