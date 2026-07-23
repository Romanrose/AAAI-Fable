# Concept2Fable 论文实验表

此目录保存由 `python -m kg_rag.aaai_eval report-pipeline` 生成的论文表和汇总报告。它们是当前实验资产，应与输入 manifest、审核记录和故事评估结果一起提交。

```text
table_1_mechanism_graph_quality.csv
table_2_structure_mapping_quality.csv
table_3_story_generation_quality.csv
table_4_ablation_design.csv
pipeline_report.json
pipeline_report.md
```

- `table_1`：Core80 检索、机制验证与审核记录。
- `table_2`：Core80 的 Standard 与 Deterministic Copycat 映射计划。
- `table_3`：已完成的 Pilot12 三策略故事结果。
- `table_4`：当前是 `design_only` 的消融设计，而非测得结果；只有相应协议运行完成后才能替换为正式消融表。

## Shared experiment boundary

Do not add exploratory tables to this frozen paper-output directory. Start a separate experiment under [`kg_rag/shared/`](../../shared/README.md) and follow the [shared experiment policy](../../SHARED_EXPERIMENTS.md).
