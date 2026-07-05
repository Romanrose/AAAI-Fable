# Concept-to-Fable 机器评测 README

本文档说明如何在本项目中复现中文 Concept 寓言的机器评测流程，以及当前 20 条本地实验包含哪些测试。

## 当前实现范围

已实现：

- 从 K12-KGraph 构建 Concept card。
- 基于 Concept card 生成中文寓言和 alignment table。
- 对每个样本进行六维机器评测。
- 批量导出 `eval_summary.jsonl`、`eval_summary.csv`、`eval_report.md`、`eval_analysis.svg`。
- 预留多模型 LLM-as-Judge panel。
- 预留人工测试和 baseline 对比模型，不把未执行的人评结果写入当前机器实验。

六维指标：

| 维度 | 含义 |
|---|---|
| `faithfulness` | 知识机制是否忠实 |
| `implicitness` | 是否避免术语直露 |
| `mapping_clarity` | 概念结构和故事元素是否可对齐 |
| `readability` | 中文故事是否自然可读 |
| `pedagogical_value` | 是否支持教学理解和迁移 |
| `novelty` | 是否避免模板化 |

## 安装与测试

推荐使用 `uv`：

```bash
uv sync --dev
uv run pytest tests/test_evaluation.py tests/test_judge_panel.py tests/test_concept_fables.py
```

如果本地已经安装项目依赖，也可以使用：

```bash
python3 -m pytest tests/test_evaluation.py tests/test_judge_panel.py tests/test_concept_fables.py
```

这些测试覆盖：

- 术语硬泄露会降低 `implicitness`。
- 缺少核心映射会进入 `reject`。
- 同批故事模板相似会触发 `template_like`。
- 本地中文故事生成不会在正文直接暴露目标概念名。
- 多 judge panel 的分数 median 聚合和硬标记多数投票。

## 从零构建输入数据

```bash
python3 -m kg_rag normalize-k12

python3 -m kg_rag select-concept-nodes \
  --limit-per-subject 5

python3 -m kg_rag build-concept-cards \
  --selection-path data/derived/kg_rag/concept_selection/k12_concepts.jsonl

python3 -m kg_rag enrich-concept-cards \
  --input data/derived/kg_rag/concept_cards/k12_concept_cards.raw.jsonl \
  --output data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl \
  --mode rules
```

## 跑 20 条生成与评测

```bash
python3 -m kg_rag run-concept-fable-batch \
  --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl \
  --output-dir data/derived/kg_rag/concept_runs/local_20_machine_eval \
  --mode local \
  --language zh-CN \
  --limit 20 \
  --evaluate-mode rules \
  --no-resume
```

这一步会生成每个概念的：

```text
concept_card.json
subgraph_pack.json
structure_plan.json
story_prompt.txt
draft_story.txt
six_dim_eval.json
status.json
```

## 单独重跑批量评测

```bash
python3 -m kg_rag evaluate-batch \
  data/derived/kg_rag/concept_runs/local_20_machine_eval \
  --mode rules \
  --no-resume
```

校验本次实验产物是否完整：

```bash
python3 -m kg_rag verify-eval-run \
  data/derived/kg_rag/concept_runs/local_20_machine_eval \
  --expected-count 20
```

输出文件：

```text
data/derived/kg_rag/concept_runs/local_20_machine_eval/eval_summary.jsonl
data/derived/kg_rag/concept_runs/local_20_machine_eval/eval_summary.csv
data/derived/kg_rag/concept_runs/local_20_machine_eval/eval_report.md
data/derived/kg_rag/concept_runs/local_20_machine_eval/eval_analysis.svg
```

当前已跑通的 20 条结果：

| 项目 | 数值 |
|---|---:|
| 样本数 | 20 |
| 评测成功 | 20 |
| 评测失败 | 0 |
| 加权总分均值 | 4.03 |
| Accept | 8 |
| Revise | 12 |
| Reject | 0 |

## LLM Judge 预留

`.env.example` 已预留：

```text
EVAL_JUDGE_COUNT=3
EVAL_JUDGE_1_PROVIDER=openai-compatible
EVAL_JUDGE_2_PROVIDER=anthropic
EVAL_JUDGE_3_PROVIDER=gemini
```

配置 key 和 model 后可运行：

```bash
python3 -m kg_rag evaluate-batch \
  data/derived/kg_rag/concept_runs/local_20_machine_eval \
  --mode llm \
  --no-resume
```

LLM 模式会为每个样本保存：

```text
six_dim_eval_prompt.txt
six_dim_eval_response_{index}_{judge}.txt
six_dim_eval_judge_{index}_{judge}.json
six_dim_eval.json
```

## 人工测试和对比模型预留

人工测试暂不在当前机器实验中执行。建议后续新增：

- 专家标注：`faithfulness`、`mapping_clarity`、概念覆盖。
- 普通读者标注：`implicitness`、`readability`、`pedagogical_value`。
- 前后测：阅读前解释概念、阅读后机制选择题、迁移类比题。
- 一致性：Krippendorff's alpha / ICC。

对比模型暂不在当前 20 条结果中执行。建议后续新增：

- `Direct Prompting`
- `CoT Planning`
- `Analogy-first`
- `Ours`
- `Ours w/o KG`
- `Ours w/o Alignment`

主实验报告应区分“已执行的机器评测结果”和“预留的人评/baseline 方案”。
