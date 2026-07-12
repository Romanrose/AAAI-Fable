# Concept2Fable Story Pilot

`kg_rag.story_pilot` 是固定 12 概念的可复现对比实验。它复用 Concept2Fable V2 的机制与 Standard/Copycat 映射，并补充 LLM-guided Copycat，比较三种冻结策略：

```text
Standard x 3
Deterministic Copycat x 3
LLM-guided Copycat x 3
```

默认输入来自 `data/derived/kg_rag/m2na_v2/pilot80/`，产物写入 `data/derived/kg_rag/story_pilot12/`。该目录保留输入索引、候选故事、对齐和 Judge 结果、修订记录以及追加式人工审核记录，应与代码一起提交。

## 运行顺序

```bash
python -m kg_rag.story_pilot prepare-guided-mappings --model deepseek-chat
python -m kg_rag.story_pilot run-initial --generator-model deepseek-chat --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot rejudge --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot revise --reviser-model deepseek-chat --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot serve-review --port 8768
```

Generator 只接收故事侧映射字段和禁用术语；Aligner 与 Judge 使用机制图进行保守的反向证据核对。每个概念、策略和候选分别落盘，因此中断后可以继续运行而不重复已完成的 LLM 调用。

人工审核页面默认位于 <http://127.0.0.1:8768/>。审核决定追加到 `story_reviews.jsonl`；同一概念—策略下新批准的偏好候选会取代旧偏好，但审计历史保留。
