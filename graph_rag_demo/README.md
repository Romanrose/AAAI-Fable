# Graph RAG 叙事生成 Demo

该 demo 展示以下最小链路：

```text
K12-KGraph 图检索
  -> 检索证据序列化
  -> 机制图提炼
  -> 隐性叙事与结构映射生成
  -> M2NA 自动评测
```

离线运行：

```bash
python3 -m graph_rag_demo.run \
  --concept 光合作用 \
  --subject biology \
  --backend fixture \
  --retrieval-mode path_dual \
  --max-hops 2 \
  --max-paths 5 \
  --max-edges 16 \
  --output-dir graph_rag_demo/output
```

在线运行：

```bash
export DEEPSEEK_API_KEY=...
python3 -m graph_rag_demo.run \
  --concept 光合作用 \
  --subject biology \
  --backend deepseek \
  --retrieval-mode path_dual \
  --output-dir graph_rag_demo/output
```

可选环境变量：

```text
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

输出文件：

```text
01_retrieved_subgraph.json
02_mechanism_graph.json
03_generation.jsonl
04_metrics.json
```

`01` 是原始课程图检索结果；`02` 是模型根据证据提炼的机制图，两者不会混为同一种事实来源。

## 检索模式

```text
one_hop      原始 baseline，只取目标概念一跳邻域。
path_pruned  PathRAG 风格，检索 1-2 hop 候选路径并裁剪为高分机制路径。
dual_level   LightRAG 风格，输出低层关系证据和规则生成的高层主题摘要。
path_dual    推荐默认模式，先做路径裁剪，再补充高层结构摘要。
```

`path_pruned` 和 `path_dual` 会在 `01_retrieved_subgraph.json` 中增加
`selected_paths`；`dual_level` 和 `path_dual` 会增加 `topic_summary`。
序列化给模型时三类上下文会被明确区分：

```text
raw_edges      原始 KG 边证据，可用于 grounding。
selected_paths PathRAG 裁剪后的机制路径，优先用于机制图提炼。
topic_summary  LightRAG 高层摘要，只作辅助背景，不作为原始事实来源。
```

## 批量对比

默认批量脚本包含 10 个 pilot 概念和 4 种检索模式。无 API key 时先跑
检索干跑轨：

```bash
python3 -m graph_rag_demo.run_batch \
  --run-mode retrieval_only \
  --output-dir graph_rag_demo/output_batch
```

在线正式轨需要 `DEEPSEEK_API_KEY`：

```bash
export DEEPSEEK_API_KEY=...
python3 -m graph_rag_demo.run_batch \
  --run-mode full_generation \
  --backend deepseek \
  --output-dir graph_rag_demo/output_batch
```

批量输出：

```text
batch_report.json
batch_report.md
batch_runs.jsonl
retrieval_table.csv
```

`retrieval_only` 会生成 `retrieval_package`、启发式 `mechanism_plan` 和检索质量指标；
`full_generation` 会额外生成机制图、叙事和自动评测结果。若正式轨缺少
`DEEPSEEK_API_KEY`，报告会明确标记失败，不会伪造生成结果。
`fixture` 后端只支持“光合作用”，用于单样本回归测试；10 个概念 pilot
需要使用在线后端或替换为支持更多概念的本地后端。

## 结构化中间表示

`01_retrieved_subgraph.json` 保留旧字段，同时新增 `retrieval_package`：

```text
target           目标概念节点。
raw_edges        可用于 grounding 的原始 KG 边。
selected_paths   PathRAG 裁剪后的机制路径。
topic_summary    LightRAG 高层摘要，只作辅助背景。
retrieval_stats  检索数量、路径长度、上下文长度和噪声指标。
```

`02_mechanism_graph.json` 在完整生成时要求包含 `mechanism_plan`：

```text
core_question
steps                  kind 只能是 condition / process / effect。
dependencies
supporting_edge_ids    必须来自 retrieval_package.raw_edges。
supporting_path_ids    必须来自 retrieval_package.selected_paths。
coverage_targets
```

`03_generation.jsonl` 新增 `retrieval_analysis`，现有自动评估字段保持兼容。
