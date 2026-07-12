# Concept2Fable

Concept2Fable（M2NA，Mechanism-to-Narrative Analogy）是一个从 K12 知识图谱构建可审核概念机制，并将其映射为中文教育寓言的研究项目。项目比较 Standard Mapping、Deterministic Copycat 和 LLM-guided Copycat 三种结构映射策略。

## 当前主线

```text
K12-KGraph
→ Concept2Fable（M2NA）V2：80 概念的检索、机制构建与人工审核
→ 结构映射：Standard / Deterministic Copycat / LLM-guided Copycat
→ Story Pilot：12 概念、三策略故事生成与审核
→ AAAI Evaluation：冻结协议、统一记录和论文结果表
```

## 项目地图

```text
AAAI-Fable/
├─ kg_rag/
│  ├─ m2na_v2/              Concept2Fable 正式机制优先管线
│  ├─ story_pilot/          12 概念三策略对比实验
│  ├─ llm_guided_copycat/   LLM-guided Copycat 映射策略
│  ├─ aaai_eval/            实验协议、统一评估与论文表格
│  ├─ experiment_hub/       本地审核和可视化工作台
│  ├─ copycat/              Deterministic Copycat 实现
│  └─ multi_agent/          生成、对齐、Judge 与修订基础设施
├─ data/
│  ├─ K12-KGraph/           原始 K12 知识图谱、K12-Bench 和训练资料
│  ├─ derived/              规范化图谱、过程记录、故事、审核和评估产物
│  └─ visualization/        global_kg 与 concept_kg 静态图谱页面
├─ AuthorKit27/             AAAI 论文源、图、模板和版本稿
├─ doc/                     研究规划、调研、幻灯片与阅读站
├─ evaluation/              历史评估目录的迁移说明
└─ tests/                   主线和历史兼容测试
```

`kg_rag/pipeline/`、旧 Concept Card 逻辑以及根 `kg_rag` CLI 中的部分命令属于历史兼容层；它们不构成当前正式实验入口。具体边界见 [kg_rag README](kg_rag/README.md)。

## 跨设备同步与安装

本仓库的原始数据、`data/derived/` 下的实验过程记录和生成寓言、以及 `data/visualization/` 均应随 Git 提交，以便在 MacBook 上获得同一份可复现实验状态。机密和本机构建缓存仍不会提交：根目录 `.env`、Python 缓存，以及阅读站的 `node_modules/`、`dist/`、`.vercel/`。

在新设备上克隆后：

```bash
git clone <repository-url>
cd AAAI-Fable

python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env               # Windows PowerShell: Copy-Item .env.example .env
```

在 `.env` 中填写本机的 API 配置；真实密钥不得提交。常用配置为：

```text
LLM_PROVIDER=deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=replace-me
DEEPSEEK_MODEL=deepseek-chat
```

提交迁移内容前，建议检查：

```bash
git status
git add -A
git status
```

当前仓库没有超过 GitHub 常规单文件限制的大文件；如果后续加入更大的 PDF、模型或二进制文件，再为相应扩展名启用 Git LFS。

## 运行当前实验

### 1. Concept2Fable（M2NA）V2：机制准备与审核

默认产物目录：`data/derived/kg_rag/m2na_v2/pilot80/`。

```bash
python -m kg_rag.m2na_v2 build-seeds
python -m kg_rag.m2na_v2 retrieve
python -m kg_rag.m2na_v2 build-mechanisms --builder-model deepseek-chat
python -m kg_rag.m2na_v2 validate-mechanisms
python -m kg_rag.m2na_v2 export-review-sheet
python -m kg_rag.m2na_v2 serve-review
```

审核完成后构建并审核 Standard / Deterministic Copycat 映射：

```bash
python -m kg_rag.m2na_v2 import-reviews --reviewer <name>
python -m kg_rag.m2na_v2 build-mappings --standard-model deepseek-chat
python -m kg_rag.m2na_v2 serve-mapping-review
```

详见 [M2NA V2 README](kg_rag/m2na_v2/README.md)。

### 2. Story Pilot：三策略故事比较

```bash
python -m kg_rag.story_pilot prepare-guided-mappings --model deepseek-chat
python -m kg_rag.story_pilot run-initial --generator-model deepseek-chat --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot rejudge --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot revise --reviser-model deepseek-chat --judge-model deepseek-chat --workers 4
python -m kg_rag.story_pilot serve-review --port 8768
```

详见 [Story Pilot README](kg_rag/story_pilot/README.md)。

### 3. AAAI Evaluation：统一评估与论文表格

```bash
python -m kg_rag.aaai_eval build-datasets
python -m kg_rag.aaai_eval init-story-pilot
python -m kg_rag.aaai_eval evaluate \
  --protocol data/derived/kg_rag/aaai_eval/story_pilot12/protocol.json
python -m kg_rag.aaai_eval report \
  --protocol data/derived/kg_rag/aaai_eval/story_pilot12/protocol.json
python -m kg_rag.aaai_eval report-pipeline
```

详见 [AAAI Evaluation README](kg_rag/aaai_eval/README.md)。

### 4. 实验工作台

```bash
python -m kg_rag.experiment_hub
```

打开 <http://127.0.0.1:8769/>。工作台嵌入机制审核、映射审核、故事审核，以及位于 `data/visualization/` 的两张静态知识图谱。

## 验证

```bash
python -m pytest -q
python -m compileall -q kg_rag tests
python -m kg_rag.m2na_v2 status
python -m kg_rag.aaai_eval list-adapters
```

## 相关文档

- [Python 实验包说明](kg_rag/README.md)
- [Concept2Fable V2 管线](kg_rag/m2na_v2/README.md)
- [Story Pilot](kg_rag/story_pilot/README.md)
- [AAAI Evaluation](kg_rag/aaai_eval/README.md)
- [Experiment Hub](kg_rag/experiment_hub/README.md)
- [K12-KGraph 数据说明](data/K12-KGraph/README.md)
- [论文工作区](AuthorKit27/concept2fable/README.md)
- [论文阅读站](doc/paper-reading-site/README.md)
