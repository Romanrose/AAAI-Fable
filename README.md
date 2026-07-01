# AAAI-Fable

AAAI-Fable 是一个面向 **Concept-to-Fable Synthesis / Conceptual Fable Generation** 的研究原型项目。项目目标是把 K12 课程知识图谱中的概念节点，转化为忠实、隐含、可映射、可解释、具有教学价值的中文寓言故事。

当前主线不是泛化的“让 LLM 写故事”，而是：

```text
课程知识图谱 / Graph RAG
-> 概念关联子图
-> 寓言结构映射
-> 中文寓言生成
-> 六维自动评估
-> revise/reject 重写
```

第一阶段聚焦四个学科的 `Concept` 节点，并以简体中文故事为主。

## Current Status

当前 Python 原型已经支持：

- K12-KGraph 离线规范化。
- Concept-centered 子图检索和 context pack 构建。
- 基于结构映射的故事 prompt 生成。
- DeepSeek-compatible LLM 调用。
- 批量中文 Concept 寓言生成。
- 六维寓言评估。
- revise/reject 样本重写。
- 中文 Concept card 构建和分层。
- 本地 smoke test 与 pytest 覆盖。

已经确认的 Concept 节点规模：

| Subject | Concept Nodes |
|---|---:|
| Chemistry | 2,302 |
| Biology | 1,648 |
| Math | 1,470 |
| Physics | 1,154 |
| **Total** | **6,574** |

当前 Concept 分层结果：

| Priority | Count |
|---|---:|
| gold | 3,854 |
| silver | 2,706 |
| repair | 14 |

已完成四科 `gold` pilot：

```text
biology   20
physics   20
chemistry 20
math      20
```

共 80 个中文故事，首次生成全部成功；经过一轮 LLM 重写后，80 个样本全部达到 `accept`。

## Repository Layout

```text
.
├── kg_rag/                         # Python 原型包
│   ├── concepts/                   # Concept 选择、concept_card、中文 prompt、补充
│   ├── evaluation/                 # 六维评估、报告导出
│   ├── generation/                 # 基础故事生成与 review prompt
│   ├── ingest/                     # K12-KGraph 规范化与 Neo4j 导入
│   ├── pipeline/                   # demo、batch、Concept fable、rewrite runner
│   ├── prompts/                    # GraphRAG prompt 组装
│   ├── retrievers/                 # 子图检索与 context pack
│   └── structure_mapping/          # 概念到寓言结构映射
├── tests/                          # pytest 测试
├── data/K12-KGraph/                # 原始 K12-KGraph 数据
├── data/derived/                   # 派生数据，默认不提交
├── doc/                            # 研究材料、评估设计、论文调研、图示
├── AGENT.md                        # Agent 工程协作约束
├── CLAUDE.md                       # Claude/Codex 风格项目约束
├── pyproject.toml                  # Python 包配置
└── .env.example                    # 本地配置模板
```

`data/derived/`、`.env`、缓存文件和输出目录都在 `.gitignore` 中，不应提交。

## Setup

建议使用 Python 3.11+。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -e .[dev]
```

检查本地路径和 scaffold 状态：

```bash
python -m kg_rag doctor
```

也可以使用安装后的 console script：

```bash
kg-rag doctor
```

## Environment

复制 `.env.example` 为 `.env`，并填入本地配置：

```bash
copy .env.example .env
```

核心环境变量：

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=change-me
NEO4J_DATABASE=neo4j

LLM_PROVIDER=deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=replace-me
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TEMPERATURE=0.3
DEEPSEEK_MAX_TOKENS=1200
```

安全要求：

- 不要提交 `.env`。
- 不要把真实 API key 写进 README、代码、报告或聊天记录。
- 如果 key 已经泄露，应立即到服务商控制台轮换。

## Data Preparation

从 K12-KGraph 原始文件构建规范化图：

```bash
python -m kg_rag normalize-k12
```

默认输出：

```text
data/derived/kg_rag/k12_kgraph_normalized.json
```

统计四科 Concept 节点并生成第一阶段选择文件：

```bash
python -m kg_rag select-concept-nodes ^
  --subjects biology,chemistry,math,physics ^
  --normalized-graph-path data/derived/kg_rag/k12_kgraph_normalized.json ^
  --output data/derived/kg_rag/concept_selection/k12_concepts.jsonl
```

构建中文 `concept_card`：

```bash
python -m kg_rag build-concept-cards ^
  --selection-path data/derived/kg_rag/concept_selection/k12_concepts.jsonl ^
  --normalized-graph-path data/derived/kg_rag/k12_kgraph_normalized.json ^
  --output data/derived/kg_rag/concept_cards/k12_concept_cards.raw.jsonl
```

用规则模式补齐结构字段，不消耗 API：

```bash
python -m kg_rag enrich-concept-cards ^
  --input data/derived/kg_rag/concept_cards/k12_concept_cards.raw.jsonl ^
  --output data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl ^
  --mode rules ^
  --only-needs-enrichment
```

如果需要用 LLM 补充低质量卡片：

```bash
python -m kg_rag enrich-concept-cards ^
  --input data/derived/kg_rag/concept_cards/k12_concept_cards.raw.jsonl ^
  --output data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl ^
  --mode llm ^
  --language zh-CN ^
  --only-needs-enrichment
```

## Chinese Concept Fable Pipeline

第一阶段生成语言为 `zh-CN`。非 Concept 节点不单独生成故事，只作为图上下文使用。

本地 smoke test，不调用 API：

```bash
python -m kg_rag select-concept-nodes ^
  --limit-per-subject 2 ^
  --output data/derived/kg_rag/concept_selection/smoke_concepts.jsonl

python -m kg_rag build-concept-cards ^
  --selection-path data/derived/kg_rag/concept_selection/smoke_concepts.jsonl ^
  --output data/derived/kg_rag/concept_cards/smoke_concept_cards.raw.jsonl

python -m kg_rag enrich-concept-cards ^
  --input data/derived/kg_rag/concept_cards/smoke_concept_cards.raw.jsonl ^
  --output data/derived/kg_rag/concept_cards/smoke_concept_cards.enriched.jsonl ^
  --mode rules

python -m kg_rag run-concept-fable-batch ^
  --concept-cards data/derived/kg_rag/concept_cards/smoke_concept_cards.enriched.jsonl ^
  --output-dir data/derived/kg_rag/concept_runs/smoke_zh_local ^
  --mode local ^
  --language zh-CN ^
  --limit 4 ^
  --evaluate-mode rules
```

使用 DeepSeek API 跑小规模真实生成和评估：

```bash
python -m kg_rag run-concept-fable-batch ^
  --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl ^
  --output-dir data/derived/kg_rag/concept_runs/biology_zh_gold_20_llm ^
  --mode llm ^
  --language zh-CN ^
  --subject biology ^
  --priority gold ^
  --limit 20 ^
  --evaluate-mode llm ^
  --retry 2
```

四科 pilot 推荐顺序：

```bash
python -m kg_rag run-concept-fable-batch --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl --output-dir data/derived/kg_rag/concept_runs/biology_zh_gold_20_llm --mode llm --language zh-CN --subject biology --priority gold --limit 20 --evaluate-mode llm --retry 2
python -m kg_rag run-concept-fable-batch --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl --output-dir data/derived/kg_rag/concept_runs/physics_zh_gold_20_llm --mode llm --language zh-CN --subject physics --priority gold --limit 20 --evaluate-mode llm --retry 2
python -m kg_rag run-concept-fable-batch --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl --output-dir data/derived/kg_rag/concept_runs/chemistry_zh_gold_20_llm --mode llm --language zh-CN --subject chemistry --priority gold --limit 20 --evaluate-mode llm --retry 2
python -m kg_rag run-concept-fable-batch --concept-cards data/derived/kg_rag/concept_cards/k12_concept_cards.enriched.jsonl --output-dir data/derived/kg_rag/concept_runs/math_zh_gold_20_llm --mode llm --language zh-CN --subject math --priority gold --limit 20 --evaluate-mode llm --retry 2
```

全量 `gold` 生成建议按学科分批执行，不要一次性启动 3,854 个任务。

## Rewrite

对 `revise` / `reject` 样本做一轮重写：

```bash
python -m kg_rag rewrite-concept-fables ^
  --run-dir data/derived/kg_rag/concept_runs/biology_zh_gold_20_llm ^
  --status revise,reject ^
  --language zh-CN ^
  --mode llm
```

重写会保留旧版本：

```text
draft_story.v1.txt
six_dim_eval.v1.json
rewrite_prompt.txt
```

重写后会刷新：

```text
eval_summary.jsonl
eval_summary.csv
eval_report.md
subject_eval_report.md
{subject}_eval_report.md
```

## Evaluation

六维评估维度：

| Dimension | 中文问题 |
|---|---|
| faithfulness | 这个寓言是否准确表达了目标概念？ |
| implicitness | 寓言是否没有直接暴露概念名或术语？ |
| mapping_clarity | 故事元素和概念机制是否能对应起来？ |
| readability | 故事是否自然、连贯、易读？ |
| pedagogical_value | 读完后是否有助于理解该概念？ |
| novelty | 故事是否避免模板化、陈词滥调？ |

单篇评估：

```bash
python -m kg_rag evaluate-story data/derived/kg_rag/concept_runs/biology_zh_gold_20_llm/concepts/biology_7a_rjb_cpt10 --mode llm
```

批量评估：

```bash
python -m kg_rag evaluate-batch data/derived/kg_rag/concept_runs/biology_zh_gold_20_llm --mode llm
```

从 JSONL 导出报告：

```bash
python -m kg_rag export-eval-report data/derived/kg_rag/concept_runs/biology_zh_gold_20_llm/eval_summary.jsonl
```

评估输出：

```text
six_dim_eval.json
eval_summary.jsonl
eval_summary.csv
eval_report.md
subject_eval_report.md
{subject}_eval_report.md
```

## Graph RAG Utilities

本地预览某个概念的 1-hop 子图：

```bash
python -m kg_rag query-subgraph "光合作用" --preview-only
```

写出子图 pack：

```bash
python -m kg_rag query-subgraph "光合作用" ^
  --preview-only ^
  --pack-output-path data/derived/kg_rag/photosynthesis_pack.json
```

构建结构映射：

```bash
python -m kg_rag build-structure-plan ^
  --pack-path data/derived/kg_rag/photosynthesis_pack.json ^
  --output-path data/derived/kg_rag/photosynthesis_plan.json
```

构建故事 prompt：

```bash
python -m kg_rag build-story-prompt ^
  --plan-path data/derived/kg_rag/photosynthesis_plan.json ^
  --output-path data/derived/kg_rag/photosynthesis_story_prompt.txt
```

运行本地 demo：

```bash
python -m kg_rag run-local-demo "photosynthesis" ^
  --output-dir data/derived/kg_rag/demo_photosynthesis
```

运行 LLM demo：

```bash
python -m kg_rag run-llm-demo "photosynthesis" ^
  --output-dir data/derived/kg_rag/llm_demo_photosynthesis
```

## Neo4j

如果需要把 normalized graph 导入 Neo4j：

```bash
python -m kg_rag load-neo4j ^
  --normalized-graph-path data/derived/kg_rag/k12_kgraph_normalized.json
```

Neo4j 配置来自 `.env`：

```text
NEO4J_URI
NEO4J_USERNAME
NEO4J_PASSWORD
NEO4J_DATABASE
```

当前大部分 prototype 命令可以使用离线 JSON，不强制依赖 Neo4j。

## Outputs

典型 run 目录：

```text
data/derived/kg_rag/concept_runs/biology_zh_gold_20_llm/
├── manifest.json
├── concept_cards.jsonl
├── summary.jsonl
├── eval_summary.jsonl
├── eval_summary.csv
├── eval_report.md
├── subject_eval_report.md
├── biology_eval_report.md
├── run_result.json
└── concepts/
    └── biology_7a_rjb_cpt10/
        ├── concept_card.json
        ├── subgraph_pack.json
        ├── structure_plan.json
        ├── story_prompt.txt
        ├── draft_story.txt
        ├── six_dim_eval.json
        └── status.json
```

这些文件都属于派生结果，默认位于 `data/derived/`，不提交到 Git。

## Testing

运行测试：

```bash
pytest -q
```

运行 Python 编译检查：

```bash
python -m compileall kg_rag tests
```

当前测试覆盖：

- 六维评估硬性规则。
- Concept 选择与文本质量分层。
- 中文故事本地生成的隐含性和中文占比。
- JSONL 和中文字段基本稳定性。

## Research Notes

当前论文方法可以概括为：

```text
Graph-grounded Concept-to-Fable Generation
```

核心研究问题：

- 如何用课程知识图谱约束寓言生成？
- 如何把概念机制映射到故事角色、事件和冲突？
- 如何避免故事直接暴露概念名？
- 如何自动评估寓言的忠实度、隐含性、映射清晰度、可读性、教学价值和新颖性？

推荐论文实验路径：

```text
1. gold Concept 中文全量
2. gold + silver 中文扩展
3. 中英双语翻译 pilot
4. Graph RAG / no Graph RAG / no structure mapping 消融
5. 人工抽检与学习效果评估
```

## Development Notes

- 默认不要修改 `data/K12-KGraph/` 原始数据。
- 所有清洗、补充、生成、评估结果写入 `data/derived/kg_rag/`。
- 大批量 LLM 任务应按学科和 priority 分批运行。
- `repair` 样本不要直接进入论文主实验集，先做文本修复或低置信度标注。
- 真实 API key 只放在本地 `.env`。

