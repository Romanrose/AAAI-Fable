# 历史评估目录说明

`evaluation/` 不再承载当前 Concept2Fable 的正式评估代码；原有独立评估脚本已移除。保留本 README 是为了说明迁移后的入口，避免将历史目录误作可运行实验。

当前正式流程位于：

```text
kg_rag/m2na_v2/      Concept2Fable V2：机制构建、审核、映射和正式双策略运行
kg_rag/story_pilot/  Pilot12：三策略故事对比与人工审核
kg_rag/aaai_eval/    数据集 manifest、冻结协议、统一评估和论文表
kg_rag/experiment_hub/ 本地审核与图谱查看工作台
```

跨设备同步时应提交 `data/derived/` 中的机制、映射、故事、审核和评估记录；不要恢复或依赖本目录过去的独立脚本。执行入口和安装说明见项目根 [README](../README.md)。
