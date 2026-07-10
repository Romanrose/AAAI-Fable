# LLM-Guided Copycat MVP

This independent package explores a small hybrid between semantic LLM proposals
and explicit Copycat-inspired structural constraints. It does not replace or
modify the existing deterministic Copycat implementation.

Current MVP:

```text
Approved MechanismGraph
-> one LLM semantic-scout call proposes three coherent mapping candidates
-> deterministic full-graph coverage and diversity scoring
-> simple meta-monitor detects repetition and ordinal placeholders
-> at most one constrained LLM refinement
-> validated selected Mapping Plan
```

Run one approved concept:

```bash
python -m kg_rag.llm_guided_copycat \
  --concept-id biology_7a_rjb_cpt1 \
  --model deepseek-chat \
  --output-dir data/derived/kg_rag/llm_guided_copycat/smoke/biology_7a_rjb_cpt1
```

This is intentionally not presented as a full Copycat implementation. Later
iterations can add probabilistic coderack selection, a dynamic domain slipnet,
competing workspace structures, non-monotonic feedback temperature, and episodic
meta-level monitoring.

The current score is a structural gate and lightweight lexical-diversity signal,
not a calibrated semantic analogy-quality score. It can miss paraphrased template
repetition such as several distinct relations sharing the same sentence pattern.
