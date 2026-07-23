# Concept2Fable

Concept2Fable（M2NA，Mechanism-to-Narrative Analogy）是一个面向 K12 知识图谱的研究工程项目：先把概念构造成可追溯、可审核的机制图，再用结构映射生成中文教育寓言，并在冻结协议下比较不同方法。

## 研究主线

```text
K12-KGraph
  → 概念检索与机制构建（M2NA V2）
  → 人工审核与 must-preserve 约束
  → 结构映射基准（五种方法）
  → 寓言生成与对齐/质量评估
  → 冻结协议、报告和论文表格
```

正式实验与探索性实验严格分开：正式管线及其冻结产物位于既有模块和 `data/derived/`；每个新增或个人实验应从 [共享实验约定](kg_rag/SHARED_EXPERIMENTS.md) 开始，在 `kg_rag/shared/<experiment-id>/` 中建立自己的代码、协议和说明。

## 项目地图

```text
AAAI-Fable/
├─ kg_rag/
│  ├─ m2na_v2/              机制优先的概念准备、审核和双策略映射
│  ├─ mapping_benchmark/    Core80 五方法结构映射基准
│  ├─ core80_challenge/     隔离的 Stage 2 / Stage 3 挑战实验
│  ├─ story_pilot/          Pilot12 三策略故事比较
│  ├─ aaai_eval/            冻结协议、统一评估和论文结果表
│  ├─ experiment_hub/       本地审核与可视化工作台
│  ├─ shared/               新增个人/协作实验的工作区
│  └─ SHARED_EXPERIMENTS.md 共享实验命名、产物与评估规范
├─ data/
│  ├─ K12-KGraph/           原始 K12 图谱、基准与训练资料
│  ├─ derived/              可复现的派生产物、审核记录和评估报告
│  └─ visualization/        图谱与机制可视化页面
├─ AuthorKit27/             AAAI 论文源、图和版本稿
├─ doc/                     研究规划、调研和论文阅读站
└─ tests/                   管线与历史兼容测试
```

`kg_rag/pipeline/`、根 CLI 的部分命令及旧 Concept Card 实现属于兼容层；当前入口和边界见 [kg_rag README](kg_rag/README.md)。

## 安装与配置

```bash
git clone <repository-url>
cd AAAI-Fable

python3 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env               # Windows PowerShell: Copy-Item .env.example .env
```

在 `.env` 中配置本机模型凭据；真实 API 密钥绝不能提交。DeepSeek 配置示例：

```text
LLM_PROVIDER=deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=replace-me
DEEPSEEK_MODEL=deepseek-chat
```

也可用独立的 SiliconFlow 环境文件，避免影响已有 `.env`：

```bash
cp .env.siliconflow.example .env.siliconflow
LLM_ENV_FILE=.env.siliconflow python -m kg_rag.story_pilot run-initial \
  --generator-model Qwen/Qwen3.5-9B
```

## 正式实验入口

### 1. M2NA V2：机制准备与审核

Pilot80 用于开发和人工审核；全量构建写入独立的 `full6574/` 根目录。完整步骤见 [M2NA V2 README](kg_rag/m2na_v2/README.md)。

```bash
python -m kg_rag.m2na_v2 build-seeds
python -m kg_rag.m2na_v2 retrieve
python -m kg_rag.m2na_v2 build-mechanisms --builder-model deepseek-chat
python -m kg_rag.m2na_v2 validate-mechanisms
python -m kg_rag.m2na_v2 serve-review
```

### 2. Core80 结构映射基准

五种方法在相同的已批准机制输入、候选预算和冻结协议下比较。见 [mapping benchmark README](kg_rag/mapping_benchmark/README.md)。

```bash
python -m kg_rag.mapping_benchmark build-protocol \
  --preparation-root data/derived/kg_rag/m2na_v2/full6574/core80 \
  --output-root data/derived/kg_rag/mapping_benchmark/core80 \
  --model deepseek-chat
python -m kg_rag.mapping_benchmark run \
  --preparation-root data/derived/kg_rag/m2na_v2/full6574/core80 \
  --output-root data/derived/kg_rag/mapping_benchmark/core80 \
  --model deepseek-chat
```

### 3. Story Pilot 与 AAAI 评估

Pilot12 比较 Standard、Deterministic Copycat 和 LLM-guided Copycat；`aaai_eval` 负责冻结协议、统一记录和论文表格。

```bash
python -m kg_rag.story_pilot prepare-guided-mappings --model deepseek-chat
python -m kg_rag.story_pilot run-initial --generator-model deepseek-chat --judge-model deepseek-chat
python -m kg_rag.aaai_eval report-pipeline
```

详见 [Story Pilot](kg_rag/story_pilot/README.md)、[AAAI Evaluation](kg_rag/aaai_eval/README.md) 与 [Core80 Challenge](kg_rag/core80_challenge/README.md)。

### 4. 本地实验工作台

```bash
python -m kg_rag.experiment_hub
```

打开 <http://127.0.0.1:8769/>；它提供机制、映射与故事审核，以及静态图谱浏览。

## 产物与复现纪律

- 原始数据位于 `data/K12-KGraph/`，不得覆盖或就地修改。
- 正式和共享实验的生成结果写入相应的 `data/derived/kg_rag/<experiment-id>/` 路径；提交前保留协议、输入 manifest、模型与关键参数。
- 审核 JSONL 是追加式审计记录，不能手工覆盖历史。
- `.env`、缓存、`node_modules/`、`dist/` 和本地临时文件不提交。

## 验证

```bash
python -m pytest -q
PYTHONPYCACHEPREFIX=/tmp/aaai-fable-pycache python -m compileall -q kg_rag tests
```

阅读站有改动时，还应在 `doc/paper-reading-site/` 运行 `npm run build`。

## 相关文档

- [Python 实验包说明](kg_rag/README.md)
- [共享实验约定](kg_rag/SHARED_EXPERIMENTS.md)
- [Concept2Fable V2 管线](kg_rag/m2na_v2/README.md)
- [Core80 Mapping Benchmark](kg_rag/mapping_benchmark/README.md)
- [Story Pilot](kg_rag/story_pilot/README.md)
- [AAAI Evaluation](kg_rag/aaai_eval/README.md)
- [Experiment Hub](kg_rag/experiment_hub/README.md)
- [K12-KGraph 数据说明](data/K12-KGraph/README.md)
- [论文工作区](AuthorKit27/concept2fable/README.md)
- [论文阅读站](doc/paper-reading-site/README.md)
