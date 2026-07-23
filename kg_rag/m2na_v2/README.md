# Concept2Fable（M2NA）V2

`kg_rag.m2na_v2` 是当前机制优先的正式准备管线。Pilot80 用于开发和审核标定；全量模式从规范化 K12 图中的全部合格概念构建可追溯机制图，并把缺少定义的概念单独隔离。

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

## 学科自适应设计

四个学科共享相同的证据约束、图结构 schema 和验证器，但不再共享同一套“机制”判定模板：

| 学科 | 优先机制视角 | 重点限制 |
| --- | --- | --- |
| 生物 | 条件—生命过程—状态变化—结果；结构—功能 | 不拟人化，不把并列生命特征强串为因果 |
| 化学 | 反应物/对象—条件或催化—转化—产物/现象 | 合并平行反应路线；催化剂不作为反应物或产物 |
| 数学 | 输入—规则/操作—结果；前提—推理—结论 | 不把数学关系写成自然因果；简单定义允许单节点 |
| 物理 | 对象/物理量—条件—规律/相互作用—现象/结果 | 保留公式方向、变量关系和适用条件 |

`must_preserve` 表示后续叙事不可缺失的最小机制骨架，不等于“所有已抽取节点和边”。阈值和 Top-K 暂不在抽取阶段硬编码：应先保留完整原始机制图，完成全量生成后根据各学科的节点数、边数和人工审核分布，生成一份独立的有效约束派生版本。

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

## 全量构建

全量输出与 Pilot80 分离到 `data/derived/kg_rag/m2na_v2/full6574/`。当前规范化图中有 6,574 个概念，其中 3 个数学概念缺少定义，因此正常种子数应为 6,571；排除项记录在 `seed_exclusions.jsonl`。

```bash
python -m kg_rag.m2na_v2 build-seeds --scope all

python -m kg_rag.m2na_v2 retrieve \
  --seeds data/derived/kg_rag/m2na_v2/full6574/seeds.jsonl \
  --output-root data/derived/kg_rag/m2na_v2/full6574

# 先做一个小批次冒烟测试；每个概念都会单独落盘，可安全断点续跑。
python -m kg_rag.m2na_v2 build-mechanisms \
  --seeds data/derived/kg_rag/m2na_v2/full6574/seeds.jsonl \
  --output-root data/derived/kg_rag/m2na_v2/full6574 \
  --builder-model deepseek-chat --per-subject-limit 5 --workers 2

# 确认模型限流和输出质量后继续全量；workers 应按供应商限流调整。
python -m kg_rag.m2na_v2 build-mechanisms \
  --seeds data/derived/kg_rag/m2na_v2/full6574/seeds.jsonl \
  --output-root data/derived/kg_rag/m2na_v2/full6574 \
  --builder-model deepseek-chat --resume --workers 4

python -m kg_rag.m2na_v2 validate-mechanisms \
  --seeds data/derived/kg_rag/m2na_v2/full6574/seeds.jsonl \
  --output-root data/derived/kg_rag/m2na_v2/full6574
```

全量检索只建立一次图索引并在所有概念间复用；机制抽取按概念写入 `mechanisms/raw/<concept_id>.json` 检查点。即使进程中断，`--resume` 也会跳过已经有效的记录，只补齐缺失、失败或验证无效的概念。

## Must-preserve Top-K 准备

原始机制图不做覆盖式裁剪。先运行下面的分析命令，生成 `constraints/threshold_manifest.json` 和 `constraints/topk_candidates.jsonl`：

```bash
python -m kg_rag.m2na_v2 analyze-must-preserve \
  --output-root data/derived/kg_rag/m2na_v2/full6574
```

该版本使用“学科 P90 触发、学科 P90 Top-K”的保守策略：只有节点或边数量超过该学科 P90 的记录会进入候选队列，后续才由 LLM 在保留端点闭包、连通性、方向和核心机制角色的约束下把它们压回该学科 P90 范围。候选选择写入新的派生约束文件，不会修改 `mechanisms/raw/`。

```bash
python -m kg_rag.m2na_v2 select-must-preserve-topk \
  --output-root data/derived/kg_rag/m2na_v2/full6574 \
  --selector-model deepseek-chat --workers 4
```

Top-K 只处理 `topk_candidates.jsonl` 中的超限记录。每个选择结果单独落盘，可通过 `--resume` 重试未生成或无效的选择。

选择完成后，生成供下游映射使用的完整派生约束文件：

```bash
python -m kg_rag.m2na_v2 materialize-must-preserve \
  --output-root data/derived/kg_rag/m2na_v2/full6574
```

`effective_constraints.jsonl` 包含所有通过机制验证的概念；超限概念使用 Top-K 结果，其他概念保留原有约束并补齐被保留边的端点。任何无法在 P90 上限内保持有效主链的概念会以 `passthrough_infeasible` 明确标记，不会被静默删减。

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

## 共享实验边界

不要在 Pilot80 或全量机制根目录中混入个人评估。新的机制、映射或故事对照应从 [`kg_rag/shared/`](../shared/README.md) 开始，并按[共享实验约定](../SHARED_EXPERIMENTS.md)创建独立协议和派生产物路径。
