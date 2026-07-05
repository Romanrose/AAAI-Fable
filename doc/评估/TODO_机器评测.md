# 机器评测 TODO

更新时间：2026-07-05 17:42 Asia/Shanghai

## 本轮检查基线

- 工作区：`/Users/lin/Desktop/work_space/AAAI-Fable`
- 20 条机器评测结果：`data/derived/kg_rag/concept_runs/local_20_machine_eval/`
- 当前证据：`eval_summary.jsonl` 20 行，`summary.jsonl` 20 行，`eval_summary.csv`、`eval_report.md`、`eval_analysis.svg` 均存在。
- 目标边界：当前完成的是本地规则机器评测；LLM judge、人评和 baseline 对比已预留，不冒充已完成结果。

## Codex 可自动完成

- [ ] 降低本地 `local` 故事生成器模板化，减少 `template_like=true` 的比例。

## 需要用户完成或拍板

- [ ] 是否允许使用真实 LLM API key 跑 `--evaluate-mode llm` 的 judge panel。
- [ ] baseline 方法最终采用哪些：`Direct Prompting`、`CoT Planning`、`Analogy-first`、`Ours w/o KG`、`Ours w/o Alignment` 是否都保留。
- [ ] 人工评测样本量、标注者来源和费用安排。
- [ ] 论文实验主表优先报告机器评测、LLM judge 还是人工评测。

## 已完成

- [x] 项目内六维评测 rubric、权重和硬性风险标记落地。
- [x] 本地规则评测跑通 20 条数据。
- [x] 导出 `eval_summary.jsonl`、`eval_summary.csv`、`eval_report.md`、`eval_analysis.svg`。
- [x] 文档说明人工测试和对比模型为预留项。
- [x] 创建本 TODO 文件，供定时检查继续维护。
- [x] 增加 `kg-rag verify-eval-run` 完整度校验命令，检查 JSONL 行数、概念目录和 CSV/Markdown/SVG 产物。
- [x] 为机器实验增加 `--auto-run-dir` 时间戳目录和 `runs_index.jsonl` 运行索引，避免固定目录被覆盖。
- [x] 增加 `kg-rag run-machine-eval` 一键机器评测入口，串起数据准备、生成、评测、报告和完整度校验。
- [x] 增加报告图表导出测试，覆盖 `eval_analysis.svg`、Markdown 图表链接和 CSV 产物。
