# Core80 小模型故事生成

这个目录是一个与正式 Stage 3 隔离的模型鲁棒性实验入口。它复用冻结的 Core80 输入与官方 Mapping Plan，但所有新增任务、检查点和汇总结果都写入 `data/derived/kg_rag/core80_challenge/stage3-small-models-v1/`，不会覆盖既有的 Stage 3 结果。

默认矩阵为四个硅基流动模型：`Qwen/Qwen3.5-4B`、`Qwen/Qwen3.5-9B`、`Qwen/Qwen3.5-27B` 和 `Qwen/Qwen3.5-35B-A3B`；两个生成条件是：

- `mechanism_direct`：已有最强的 Core80 对照方法；
- `graph_plus_structural_mapping`：检验小模型能否把结构性 Mapping Plan 转化为故事。

因此默认会冻结并运行 `80 × 4 × 2 = 640` 个故事。生成模型同时承担该方法的内部 judge；外部的结构和六维评测固定为 `Qwen/Qwen3.6-27B`，其模型名会保存在每条调用记录中。不要把评测模型改成待比较的小模型，否则模型间结果不可比。

先把真实 API Key 放在被忽略的 `.env.siliconflow`（不要放进 `.env.siliconflow.example`），然后冻结任务：

```bash
LLM_ENV_FILE=.env.siliconflow \
python3 -m kg_rag.core80_challenge.stage3_small_models prepare
```

同时并行跑最多四个 API 调用：

```bash
LLM_ENV_FILE=.env.siliconflow \
python3 -m kg_rag.core80_challenge.stage3_small_models run --workers 4
python3 -m kg_rag.core80_challenge.stage3_small_models aggregate
```

若使用硅基流动生成、DeepSeek V4 评测，必须新建输出目录，并在协议中冻结两个 provider：

```bash
python3 -m kg_rag.core80_challenge.stage3_small_models prepare \
  --output-dir data/derived/kg_rag/core80_challenge/stage3-small-models-9b-deepseek-v4-eval-v1 \
  --generator-model Qwen/Qwen3.5-9B \
  --generator-provider siliconflow \
  --evaluator-provider deepseek \
  --evaluator-model deepseek-v4-pro

python3 -m kg_rag.core80_challenge.stage3_small_models run \
  --output-dir data/derived/kg_rag/core80_challenge/stage3-small-models-9b-deepseek-v4-eval-v1 \
  --generator-env-file .env.siliconflow.example \
  --evaluator-env-file .env \
  --workers 4
```

若只想先做单模型烟雾实验，可新建另一输出目录，避免和正式矩阵混合：

```bash
LLM_ENV_FILE=.env.siliconflow \
python3 -m kg_rag.core80_challenge.stage3_small_models prepare \
  --output-dir data/derived/kg_rag/core80_challenge/stage3-small-models-smoke \
  --generator-model Qwen/Qwen3.5-4B
```

冻结后，`tasks.jsonl`、`inputs.jsonl`、`protocol.json` 不能用不同内容覆盖；同一任务断点重跑时会复用已有终态检查点。

## 全量机制图重评

若要将每个概念的完整 `mechanism_graph`（而非生成时使用的有效子图）作为评估标准，使用独立的重评模块。它复用冻结的可见故事，不重新生成，因此严格测量的是“故事对完整机制图的覆盖”，不能与有效子图评测混合。

```bash
python3 -m kg_rag.core80_challenge.stage3_small_models.full_graph_rescore prepare
python3 -m kg_rag.core80_challenge.stage3_small_models.full_graph_rescore run --workers 4
python3 -m kg_rag.core80_challenge.stage3_small_models.full_graph_rescore aggregate
```

评测余额耗尽时，记录会标记为 `evaluator_failure`；余额恢复后再次执行 `run` 会只重试失败项。

## 共享实验边界

新增小模型对照或评估应放在 [`kg_rag/shared/<experiment-id>/`](../../shared/README.md)，不要复用本目录的冻结协议或产物。具体要求见[共享实验约定](../../SHARED_EXPERIMENTS.md)。
