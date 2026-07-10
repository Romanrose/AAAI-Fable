# Story Pilot 12

Independent 12-concept pilot comparing three frozen mapping strategies:

```text
Standard x 3
Deterministic Copycat x 3
LLM-guided Copycat x 3
```

The Generator receives only story-side mapping fields and forbidden terms. The
Aligner and Judge receive the mechanism graph for conservative reverse evidence
checking. Every artifact is written per concept/strategy/candidate so interrupted
runs can resume without repeating completed calls.

```bash
python -m kg_rag.story_pilot prepare-guided-mappings --model deepseek-chat
python -m kg_rag.story_pilot run-initial \
  --generator-model deepseek-chat \
  --judge-model deepseek-chat \
  --workers 4
python -m kg_rag.story_pilot rejudge --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot revise --reviser-model deepseek-chat --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot serve-review --port 8768
```

The review app compares the three final candidates for one strategy side by
side. Decisions are append-only in `story_reviews.jsonl`; approving a preferred
candidate supersedes the previous preferred candidate for the same
concept/strategy while retaining the audit history.
