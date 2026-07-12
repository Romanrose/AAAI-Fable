# Concept2Fable（M2NA）V2

`kg_rag.m2na_v2` 是当前机制优先的正式准备管线。它从冻结的 Core80 概念集构建可追溯机制图，并在机制与映射均经审核后运行 Standard 和 Deterministic Copycat 的公平对比。

```text
ConceptSeed
→ GraphRAG RetrievalPackage
→ LLM MechanismRecord
→ 严格验证与人工机制审核
→ Standard / Deterministic Copycat Mapping Plan
→ 人工映射审核
→ 共享多智能体故事生成与评估
```

默认根目录：`data/derived/kg_rag/m2na_v2/pilot80/`。该目录是版本控制中的实验资产；不要手工覆盖 JSONL 审核记录或已生成的 manifest。

## 准备与机制审核

```bash
python -m kg_rag.m2na_v2 build-seeds
python -m kg_rag.m2na_v2 retrieve
python -m kg_rag.m2na_v2 build-mechanisms --builder-model deepseek-chat
python -m kg_rag.m2na_v2 validate-mechanisms
python -m kg_rag.m2na_v2 export-review-sheet
python -m kg_rag.m2na_v2 serve-review
```

`retrieve` 先保留一跳证据；仅在直接结构不足时扩展至最多 8 条两跳路径。课程章节桥接仅提供上下文，不能作为机制证据。

审核完成后导入决定并检查状态：

```bash
python -m kg_rag.m2na_v2 import-reviews --reviewer <name>
python -m kg_rag.m2na_v2 status
```

只有规则有效且最新人工决定为 `approve` 的机制记录能够进入正式故事实验。

## 映射与正式运行

```bash
python -m kg_rag.m2na_v2 build-mappings --standard-model deepseek-chat
python -m kg_rag.m2na_v2 serve-mapping-review

python -m kg_rag.m2na_v2 run-experiment \
  --strategy both \
  --generator-model deepseek-chat \
  --judge-model deepseek-chat \
  --output-dir data/derived/kg_rag/m2na_v2/pilot80/runs/run_001
```

每个已批准概念生成三个 Standard 和三个 Copycat 候选映射。每个计划都必须覆盖全部 `must_preserve` 节点和边，并保留边方向；失败计划写入 `mapping_failures.jsonl`。正式结果采用相同候选预算、最多两轮修订；任何模型 fallback 都会使对应概念—策略结果失去正式评估资格。

LLM-guided Copycat 的三策略对比入口位于 [Story Pilot](../story_pilot/README.md)，不在本模块的双策略 `run-experiment` 中。
