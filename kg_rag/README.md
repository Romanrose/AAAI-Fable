# `kg_rag`：Concept2Fable 实验包

`kg_rag` 是 Concept2Fable（M2NA）的 Python 实验包。当前正式实验围绕“知识图谱 → 可审核机制图 → 结构映射 → 寓言 → 统一评估”展开。

## 当前入口

| 模块 | 用途 | 默认产物 |
|---|---|---|
| `kg_rag.m2na_v2` | Core80 的种子、检索、机制、审核、Standard/Copycat 映射和正式双策略运行 | `data/derived/kg_rag/m2na_v2/pilot80/` |
| `kg_rag.story_pilot` | Pilot12 的三策略故事比较与人工审核 | `data/derived/kg_rag/story_pilot12/` |
| `kg_rag.aaai_eval` | 冻结数据集、实验协议、统一记录和论文结果表 | `data/derived/kg_rag/aaai_eval/` |
| `kg_rag.experiment_hub` | 本地审核与图谱可视化工作台 | 浏览器端口 `8769` |

共享实现包括：`copycat/`（确定性映射）、`llm_guided_copycat/`（第三种映射策略）、`multi_agent/`（生成与审核）、`ingest/`（图谱规范化）、`retrievers/`（检索）和 `evaluation/`（当前多智能体仍使用的 rubric）。

## 常用命令

```bash
# 查看 M2NA V2 准备状态
python -m kg_rag.m2na_v2 status

# 运行或恢复 12 概念三策略 Pilot
python -m kg_rag.story_pilot prepare-guided-mappings --model deepseek-chat
python -m kg_rag.story_pilot run-initial --generator-model deepseek-chat --judge-model deepseek-chat --workers 4

# 生成统一结果表
python -m kg_rag.aaai_eval report \
  --protocol data/derived/kg_rag/aaai_eval/story_pilot12/protocol.json

# 启动审核工作台
python -m kg_rag.experiment_hub
```

完整阶段命令见各模块 README：

- [Concept2Fable V2](m2na_v2/README.md)
- [Story Pilot](story_pilot/README.md)
- [AAAI Evaluation](aaai_eval/README.md)
- [Experiment Hub](experiment_hub/README.md)

## 数据和跨设备同步

原始图谱位于 `data/K12-KGraph/`；规范化图谱、审核记录、映射计划、生成故事和评估报告位于 `data/derived/`。这些内容应与代码一起提交，保证另一台设备可直接查看和继续实验。真实 API 密钥仅存在根 `.env`，不得提交。

## 历史兼容层

`concepts/` 中除 `jsonl.py` 外的 Concept Card 逻辑、`pipeline/`、`generation/`、`prompts/` 和 `structure_mapping/` 主要支持历史 Concept-to-Fable 流程或回归测试。根 `python -m kg_rag` CLI 也保留了相应兼容命令；它们不属于当前正式实验入口。
