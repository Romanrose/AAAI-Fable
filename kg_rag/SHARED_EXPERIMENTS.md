# 共享实验工作区约定

本文件规定新增、个人和协作实验的放置方式。它的目标是让探索可以并行进行，同时不修改或污染已冻结的 Concept2Fable 正式实验。

## 必须使用的目录

每个新实验使用一个稳定、描述性的 ID，并建立：

```text
kg_rag/shared/<experiment-id>/
├─ README.md           # 研究问题、范围、输入与运行方式
├─ protocol.json       # 冻结的模型、提示词版本、预算和评估规则（如适用）
├─ run.py 或 cli.py    # 实验入口
├─ evaluation/         # 该实验自己的评估器、打分脚本和评估说明（如适用）
└─ tests/              # 与该实验一起维护的窄范围测试（如适用）

data/derived/kg_rag/shared/<experiment-id>/
├─ input_manifest.json
├─ runs/               # 每次运行的检查点、记录和失败样本
└─ reports/            # 可复查的汇总、表格和图
```

`kg_rag/shared/` 保存代码、协议和可读说明；生成的 JSONL、模型响应、评估记录和大体积报告写入对应的 `data/derived/` 路径。请不要把生成结果放在 Python 包目录中，也不要复用另一个实验的输出目录。

评估也必须与实验绑定：评估脚本放在该实验目录的 `evaluation/`（或入口脚本旁的同一实验模块）中，评估输入、逐样本判断、失败记录和汇总表放在对应的 `data/derived/kg_rag/shared/<experiment-id>/reports/`。不得直接覆盖其他实验的评分文件，也不得把“成功样本”筛选后冒充全量结果。

## 开始一个实验

1. 选择新的 `<experiment-id>`，例如 `relation-ablation-001`；不要使用模糊的 `test`、`new` 或他人正在使用的名称。
2. 在该目录的 README 写明研究问题、对照条件、输入数据、输出路径和成功判据。
3. 在运行前冻结输入 manifest、模型名称、关键参数、提示词/代码版本和预算；需要调用模型时记录请求 ID、重试与失败原因。
4. 先运行小规模冒烟测试，再运行完整评估。每次运行必须可安全恢复，且失败样本应保留为结果而不是静默重试或删除。
5. 提交时一并提交实验代码、README、协议、输入 manifest 和可复查的报告；不得提交 API 密钥、本地缓存或未说明用途的临时文件。

## 边界

- 不修改 `m2na_v2/`、`mapping_benchmark/`、`story_pilot/`、`aaai_eval/` 或 `core80_challenge/` 的冻结协议和正式产物，除非任务明确要求更新该正式实验。
- `kg_rag/core80_challenge/shared/` 是 Core80 Challenge 的内部实现，不是新增实验的放置位置。
- 原始数据只能从 `data/K12-KGraph/` 读取；任何派生数据都应有清晰的输入与生成记录。
- 若实验结论要进入论文表格，先将其协议和报告提交审查，再考虑迁入正式评估模块。

## 最小 README 模板

```md
# <experiment-id>

## 研究问题

## 输入与对照条件

## 运行

## 输出与评估标准

评估代码位于本实验的 `evaluation/`；同时报告全量样本、失败样本和适用的 conditional 指标。

## 复现信息
```
