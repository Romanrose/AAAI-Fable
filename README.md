# AAAI-Fable

这个仓库沉淀 AAAI 论文方向的研究材料与两套原型代码：

- **M2NA - Mechanism-to-Narrative Analogy Generation**：当前收窄主线，聚焦“机制结构忠实、术语隐藏、可对齐、叙事最小”的隐性叙事类比生成。
- **Graph-grounded Concept-to-Fable Generation**：课程知识图谱 / Graph RAG 方向，聚焦 K12 Concept 节点检索、结构映射、中文寓言生成、六维自动评估和重写闭环。

两条线都围绕“把抽象概念转化为可教学、可映射的短叙事”，但实验重点不同：`src/m2na/` 更强调机制图到隐性寓言，`kg_rag/` 更强调课程知识图谱约束下的批量生成与评估。

## Repository Layout

```text
.
├── src/m2na/                       # M2NA 初版代码
├── kg_rag/                         # GraphRAG / Concept-to-Fable 原型包
├── tests/                          # pytest 测试
├── data/K12-KGraph/                # 原始 K12-KGraph 数据
├── data/concepts/                  # M2NA concept 输入样例
├── data/derived/                   # 派生数据，默认不提交
├── doc/                            # 研究材料、评估设计、论文调研、图示
├── PROGRESS.md                     # M2NA 进度与待办交接
├── AGENT.md                        # Agent 工程协作约束
├── CLAUDE.md                       # Claude/Codex 风格项目约束
└── .env.example                    # 本地配置模板
```

## M2NA Mainline

当前主线权威定义见：

- [`doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md`](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md)
- [`doc/后续思路与建议.md`](doc/后续思路与建议.md)
- [`PROGRESS.md`](PROGRESS.md)
- [`src/README.md`](src/README.md)

M2NA 形式化输入包括目标概念 `c`、机制图 `G_c=(V_c,E_c)`、禁用词集 `T_c`。输出包括不点破概念术语但机制结构忠实的隐性叙事类比 `N`，以及「机制零件 ↔ 情节」对齐 `A`。

运行示例：

```bash
uv sync --dev
uv run python run_demo.py
uv run python run_demo.py "overfitting"
uv run pytest
```

真实 LLM 运行使用 `.env` 中的 DeepSeek 配置：

```bash
uv run python run_real_demo.py
uv run python run_real_batch.py
```

## GraphRAG Prototype

GraphRAG 方向代码在 `kg_rag/`，支持：

- K12-KGraph 离线规范化。
- Concept-centered 子图检索和 context pack 构建。
- 结构映射故事 prompt 生成。
- DeepSeek-compatible LLM 调用。
- 批量中文 Concept 寓言生成。
- 六维寓言评估。
- revise/reject 样本重写。

更多命令和流程见 [`kg_rag/README.md`](kg_rag/README.md)。

基础安装：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e .[dev]
python -m kg_rag doctor
```

## Environment

复制 `.env.example` 为 `.env`，并填入本地配置。真实 API key 只放在本地 `.env`，不要提交到 README、代码、报告或聊天记录。

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
```

## Data And Outputs

- 默认不要修改 `data/K12-KGraph/` 原始数据。
- GraphRAG 清洗、补充、生成、评估结果写入 `data/derived/kg_rag/`。
- M2NA 运行结果默认写入 `output/<timestamp>_<concept>/`。
- `data/derived/`、`.env`、缓存文件和输出目录都在 `.gitignore` 中，不应提交。

## Testing

```bash
pytest -q
python -m compileall kg_rag src tests
```

当前测试覆盖 M2NA 输入构建/生成闭环、GraphRAG 六维评估规则、Concept 选择、中文故事本地生成和 JSONL 稳定性。

## Research Notes

推荐阅读路径：

1. [`PROGRESS.md`](PROGRESS.md)
2. [`doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md`](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md)
3. [`doc/后续思路与建议.md`](doc/后续思路与建议.md)
4. [`src/README.md`](src/README.md)
5. [`kg_rag/README.md`](kg_rag/README.md)
6. [`doc/论文调研/`](doc/论文调研/)

论文阅读网站：

```bash
cd doc/paper-reading-site
npm install
npm run dev
```

线上：[https://paper-reading-site.vercel.app](https://paper-reading-site.vercel.app)
