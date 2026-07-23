# `kg_rag`：Concept2Fable 实验包

`kg_rag` 实现 Concept2Fable（M2NA）的正式研究链路：知识图谱检索、机制图构建与审核、结构映射、寓言生成，以及冻结后的统一评估。

## 正式入口

| 模块 | 职责 | 默认派生产物 |
|---|---|---|
| [`m2na_v2/`](m2na_v2/README.md) | Pilot80 / 全量机制准备、审核、Standard 与确定性 Copycat 映射 | `data/derived/kg_rag/m2na_v2/` |
| [`mapping_benchmark/`](mapping_benchmark/README.md) | Core80 五方法结构映射与计划级评估 | `data/derived/kg_rag/mapping_benchmark/` |
| [`core80_challenge/`](core80_challenge/README.md) | 独立冻结的 Stage 2 / Stage 3 挑战实验 | `data/derived/kg_rag/core80_challenge/` |
| [`story_pilot/`](story_pilot/README.md) | Pilot12 三策略故事生成、审核和修订 | `data/derived/kg_rag/story_pilot12/` |
| [`aaai_eval/`](aaai_eval/README.md) | 冻结数据集、协议、统一记录和论文表格 | `data/derived/kg_rag/aaai_eval/` |
| [`experiment_hub/`](experiment_hub/README.md) | 本地审核与图谱可视化工作台 | 浏览器端口 `8769` |

通用实现包括 `copycat/`、`llm_guided_copycat/`、`multi_agent/`、`ingest/`、`retrievers/` 和 `evaluation/`。它们是正式模块的依赖，不是个人实验结果的存放位置。

## 常用命令

```bash
# 查看 M2NA V2 准备状态
python -m kg_rag.m2na_v2 status

# 冻结并运行 Core80 五方法映射基准
python -m kg_rag.mapping_benchmark build-protocol --help
python -m kg_rag.mapping_benchmark run --help

# 运行或恢复 Pilot12 三策略故事实验
python -m kg_rag.story_pilot run-initial --help

# 输出统一论文结果表
python -m kg_rag.aaai_eval report-pipeline

# 启动审核工作台
python -m kg_rag.experiment_hub
```

## 共享实验工作区

新增、个人或协作实验必须先阅读 [共享实验约定](SHARED_EXPERIMENTS.md)，并在 `kg_rag/shared/<experiment-id>/` 下建立代码、协议和说明。生成的记录、报告和大体积结果写入配套的 `data/derived/kg_rag/shared/<experiment-id>/`，不能混入上述冻结实验目录。

`core80_challenge/shared/` 是该挑战包的内部 Python 库；它不是共享实验工作区。

## 数据、版本控制与兼容层

原始图谱位于 `data/K12-KGraph/`；规范化图谱、审核记录、映射计划、故事和评估报告位于 `data/derived/`。提交可复现运行时，应同时提交代码、协议、输入 manifest 和必要的派生产物；真实 API 密钥只存在根 `.env`。

`concepts/` 中除 `jsonl.py` 外的 Concept Card 逻辑、`pipeline/`、`generation/`、`prompts/` 和 `structure_mapping/` 主要服务于历史流程或回归测试。根 `python -m kg_rag` CLI 保留部分兼容命令，但不构成当前正式入口。
