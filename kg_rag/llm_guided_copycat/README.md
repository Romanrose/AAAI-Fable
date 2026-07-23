# Concept2Fable LLM-guided Copycat

`kg_rag.llm_guided_copycat` 是 Concept2Fable Story Pilot 的第三种结构映射策略。它不替代 `kg_rag.copycat` 的确定性实现，而是将 LLM 的语义候选提议与明确的 Copycat-inspired 结构约束结合。

```text
Approved MechanismGraph
→ LLM semantic scout 提议 3 个映射候选
→ 全图覆盖与差异性评分
→ 重复/序号占位符检测
→ 最多一次受约束 LLM refinement
→ 验证后的 Mapping Plan
```

单概念调试入口：

```bash
python -m kg_rag.llm_guided_copycat \
  --concept-id biology_7a_rjb_cpt1 \
  --model deepseek-chat \
  --output-dir data/derived/kg_rag/llm_guided_copycat/smoke/biology_7a_rjb_cpt1
```

正式的三策略比较应通过 [Story Pilot](../story_pilot/README.md) 的 `prepare-guided-mappings` 运行，使三种策略共享同一概念、机制、候选和评估预算。

当前评分是结构门控和轻量词汇多样性信号，不是校准后的语义类比质量分数；它仍可能遗漏同义改写形式的模板重复。

## 共享实验边界

新的 LLM-guided Copycat 对照应使用 [`kg_rag/shared/<experiment-id>/`](../shared/README.md)，并保留独立的协议和派生产物；请遵循[共享实验约定](../SHARED_EXPERIMENTS.md)。
