# AAAI-Fable

这个仓库沉淀一篇 AAAI 论文方向的材料与初版代码。

> **当前主线（已定稿）：M2NA — Mechanism-to-Narrative Analogy Generation**
> 给定目标概念 `c`、机制图 `G_c=(V_c,E_c)`、禁用词集 `T_c`，让模型生成一段
> **不点破概念术语、但机制结构忠实**的隐性叙事类比 `N`，并显式输出「机制零件 ↔ 情节」对齐 `A`。
> 四个成功条件：机制保持 / 词汇隐藏(concealment) / 可对齐 / 叙事最小。
>
> 早期更宽的 **Concept-to-Fable / KG-Fable**（含 RAG + 教学评估 + 人类学习实验）视为**上一版/扩展版**，
> 不作为当前主线；其评估与数据集设计中可复用的部分保留为素材。

主线权威定义见 [`doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md`](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md)，
最新决策与待办见 [`doc/后续思路与建议.md`](doc/后续思路与建议.md)。

## 仓库结构

- `src/`：**M2NA 初版代码**（当前只实现第二部分：中间分析的 agent 架构）。详见 [`src/README.md`](src/README.md)。
- `PROGRESS.md`：进度与待办交接文档（冷启动入口）。
- `doc/`：论文思路、调研、评估/数据集方案、思维导图，以及论文阅读网站。
- `data/`：根目录数据资源，含 `K12-KGraph`（课程知识图谱，备选数据源）。

## 代码：M2NA 第二部分（agent 架构）

`(G_c, T_c) → (N, A)` 的多 agent 端到端闭环，已用 Mock LLM 跑通：

```
Planner → Generator → Aligner → Reviser
(选源域+映射) (写叙事N) (回指出A) (泄露/覆盖自检)
```

```bash
python run_demo.py                 # 跑全部 fixture
python run_demo.py "overfitting"   # 指定概念
pip install pytest && pytest tests/
```

LLM 可插拔：各 agent 只依赖 `LLMClient.complete()`，换 Mock / 真实后端不改 agent。
完整说明（含数据流图）见 [`src/README.md`](src/README.md)。

## 系统三段式（整体规划）

1. **数据库 + 数据清洗** —— 产出 `G_c`/`T_c`（未实现；现用 `src/m2na/fixtures.py` 顶替）。
2. **中间分析的 agent 架构** —— 生成 `N`/`A`（✅ 已完成初版）。
3. **评估** —— 泄露率/机制覆盖/对齐一致性等（未实现；reviser 内已有确定性自检雏形）。

## doc/ 目录说明

| 路径 | 说明 | 主线相关 |
|---|---|---|
| `文章思路迭代（主要看这个）/...收窄任务_学术问题定义.md` | **M2NA 权威定义** | ⭐ 主线 |
| `后续思路与建议.md` | 最新决策、护城河、命门、待办 | ⭐ 主线 |
| `论文调研/M2NA_2024-2026相关论文检索.md` | related work 素材 | ⭐ 主线 |
| `论文调研/竞品精读_第一档.md` | 两个最危险竞品逐篇精读 + 区分度 | ⭐ 主线 |
| `文章思路迭代（主要看这个）/...问题定义方法摘要Introduction整合稿.md` | 上一版 Concept-to-Fable 完整雏形 | 📦 历史/可复用 |
| `数据集/数据集codex给的建议.md` | 上一版数据集设计建议 | 📦 历史/可复用 |
| `评估/评估部分codex给的建议{1,2}.md` | 上一版评估协议建议 | 📦 历史/可复用 |
| `寓言生成对话.xmind` | 早期思维导图 | 📦 历史 |
| `paper-reading-site/` | Astro Starlight 论文阅读网站(25 篇) | 🔧 工具 |

## 推荐阅读路径

1. [`PROGRESS.md`](PROGRESS.md) —— 一页看懂现状与待办。
2. [`doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md`](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md) —— M2NA 形式化定义。
3. [`doc/后续思路与建议.md`](doc/后续思路与建议.md) —— 已拍板方向、护城河(concealment)、G_c 命门、竞品地图。
4. [`src/README.md`](src/README.md) —— 第二部分代码与数据流。
5. [`doc/论文调研/`](doc/论文调研/) —— 写 Related Work、划清竞品界限。

## 论文阅读网站

```bash
cd doc/paper-reading-site
npm install && npm run dev
```

线上：[https://paper-reading-site.vercel.app](https://paper-reading-site.vercel.app)

## 分支说明

- `main`：合并了论文阅读网站、`doc/` 结构整理和根目录 `data/`。
- `lzf`：**当前开发分支**，在 main 基础上加入 `src/` 初版代码、`PROGRESS.md` 与最新调研材料。
