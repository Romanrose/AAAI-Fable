# Concept2Fable AAAI Evaluation

`kg_rag.aaai_eval` 冻结实验数据集和协议，并把不同方法的既有产物转换为统一评估记录。它不修改图谱检索、机制抽取、映射或故事生成产物。

```text
Core80   机制、映射、自动故事与消融实验
Human32  盲评人工评价子集
FullKG   后续规模化覆盖率、成功率和成本统计
```

默认评估产物根目录：`data/derived/kg_rag/aaai_eval/`。协议、记录和报告应与实验代码一起提交，作为跨设备复现的冻结证据。

## 当前命令

```bash
# 从冻结的 Pilot80 种子构建 Core80 / Human32 manifest
python -m kg_rag.aaai_eval build-datasets

# 将现有 Pilot12 三策略故事导入冻结协议并输出可比较结果
python -m kg_rag.aaai_eval init-story-pilot
python -m kg_rag.aaai_eval evaluate \
  --protocol data/derived/kg_rag/aaai_eval/story_pilot12/protocol.json
python -m kg_rag.aaai_eval report \
  --protocol data/derived/kg_rag/aaai_eval/story_pilot12/protocol.json

# 输出机制、映射、故事和消融顺序的论文报告
python -m kg_rag.aaai_eval report-pipeline
```

`report` 在协议指定的输出目录生成 JSON、UTF-8 CSV 和 Markdown 表。`report-pipeline` 默认更新包内的 [paper_tables](paper_tables/README.md)。

## 方法扩展

每个比较方法由 `MethodSpec` 声明，并通过 `MethodAdapter` 导入或运行。新增方法需要：实现 `MethodAdapter.run()`、注册 adapter factory，并在协议中加入方法声明。Runner 会检查固定概念集、候选预算、记录 schema 和失败样本；缺失产物、无效记录或不同候选数会阻止结果被标记为 `official_ready`。

内置 `story_pilot_artifact` adapter 导入 Standard、Deterministic Copycat 和 LLM-guided Copycat 的 Pilot12 产物。
