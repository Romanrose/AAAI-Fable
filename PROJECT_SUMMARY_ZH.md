# AAAI-Fable 项目中文总结

> 基于 `main` 分支当前内容整理。仓库最新提交：`53f7023`（2026-06-17）。

## 1. 项目要解决什么问题

项目研究如何让大语言模型把课程知识或抽象机制概念转换为短小、隐含、可解释的叙事类比或寓言。

目标不是单纯“让模型写一个好故事”，而是让生成结果同时满足：

- **机制保持**：故事保留原概念的关键要素、关系和因果链。
- **词汇隐藏**：正文不直接出现概念名称或高泄露术语。
- **结构可对齐**：故事中的角色、事件和状态可以映射回概念结构。
- **叙事最小性**：故事简洁、连贯，避免无关情节和模板化表达。
- **教学价值**：读者能够借助故事理解概念，并迁移到新场景。

## 2. 当前最值得采用的论文主线

仓库中存在两个相互关联、范围不同的研究版本。

### 较宽版本：Concept-to-Fable / KG-Fable

输入概念及检索知识，依次完成知识检索、概念结构抽取、类比规划、寓言生成、自我修订、映射解释和问题生成。

该版本覆盖数据集、RAG、生成、评测和人类学习实验，研究故事完整，但对单篇 AAAI 论文而言范围较大。

### 收窄版本：M2NA

当前更聚焦的任务名是：

> **Mechanism-to-Narrative Analogy Generation (M2NA)**——面向机制型概念解释的隐性叙事类比生成

形式化输入输出：

```text
Input:
  c: 目标概念
  G_c = (V_c, E_c): 概念机制图
  T_c: 禁用词集合

Output:
  N: 隐性短叙事
  A: 概念机制与叙事结构之间的对齐
```

这个版本把论文集中在一个可验证的核心问题上：模型能否在隐藏概念术语的条件下，将机制图转写为结构可对齐的短叙事。

## 3. 建议的方法框架

仓库材料提出的核心流程可以整理为：

```text
概念与知识来源
  -> 机制图构建
  -> 源域/故事情境选择
  -> 机制到叙事的结构映射规划
  -> 受约束叙事生成
  -> 泄露、遗漏、矛盾和模板检查
  -> 输出叙事与显式对齐
```

真正可能构成方法贡献的是“先建立结构映射，再生成文本”，而不是单个 prompt。

可设计的主要方法组件：

1. **Mechanism extraction**：从教材、知识图谱或可靠资料中抽取节点和关系。
2. **Analogy planning**：选择具体源域，并建立概念元素到叙事元素的映射。
3. **Constrained generation**：根据映射生成不泄露概念术语的短叙事。
4. **Self-revision**：检查机制覆盖、术语泄露、事实冲突和模板化。

## 4. 数据集与评测设想

计划中的自建数据集可命名为 `ConceptFableBench` 或围绕 M2NA 重新命名。每条样本至少应包含：

```text
目标概念
可靠知识来源
概念机制图
禁用词集合
隐性叙事
机制—叙事对齐
人工质量标签
```

仓库建议的评测分为三层：

### 自动评测

- Mechanism / Concept Coverage
- Hard / Soft Leakage Rate
- Mapping Consistency
- Contradiction Rate
- Template Rate 与文本多样性

### 专家或人工评测

- 概念忠实度
- 类比映射质量
- 隐含性
- 叙事质量
- 教学价值
- 新颖性

### 学习效果评测

- 概念理解
- 跨领域迁移
- 错误理解率
- 延迟记忆

收窄版 M2NA 建议先把机制保持、词汇隐藏、结构对齐和叙事质量做扎实；大规模学习实验可作为后续工作或辅助实验。

## 5. 已下载的数据资源

`data/K12-KGraph/` 是当前最主要的数据资产，来源于人民教育出版社课程体系，覆盖数学、物理、化学和生物。

主要规模：

| 资源 | 当前规模 |
|---|---:|
| K12-KGraph 节点 | 10,685 |
| K12-KGraph 边 | 23,278 |
| K12-Bench 多选题 | 23,640 |
| K12-Train 问答对 | 2,267 |
| SFT baseline | 8 组，每组 2,300 条 |

图谱包含 7 类节点：

```text
Concept, Skill, Experiment, Exercise, Section, Chapter, Book
```

以及 9 类关系：

```text
is_a, prerequisites_for, relates_to, verifies,
tests_concept, tests_skill, appears_in, is_part_of, leads_to
```

它可以支撑：

- 从课程图谱检索概念邻域和先修链。
- 构建 Graph RAG 输入。
- 比较 No Retrieval、Text RAG、Graph RAG 和结构映射方法。
- 设计去除知识图谱、先修关系或结构规划的消融实验。

需要注意：K12-KGraph 是课程知识结构，而 M2NA 文档中的典型目标是“路径依赖、认知失调、过拟合”等机制型抽象概念。两者尚未自然连通，需要团队决定是聚焦 K12 概念，还是另建跨学科机制概念集。

## 6. 论文阅读网站

`doc/paper-reading-site/` 是一个 Astro Starlight 网站，主要包含：

- 25 篇相关论文的阅读卡和本地 PDF。
- 知识图谱、结构映射、层次化生成、教育评测四个研究支柱。
- 基于服务器端 DeepSeek API 的单篇论文问答接口。
- Vercel 部署配置。

本地运行：

```bash
cd doc/paper-reading-site
npm ci
npm run dev
```

论文问答功能还需要创建 `.env` 并配置有效的：

```text
DEEPSEEK_API_KEY
DEEPSEEK_MODEL
DEEPSEEK_BASE_URL
```

本次已使用临时 npm 缓存完成 `npm ci` 和 `npm run build`，网站可以成功构建。当前构建环境同时报告：

- npm 依赖审计发现 7 个漏洞（4 low、3 high），应单独评估后再升级，避免直接执行带破坏性升级的修复。
- 本地 Node.js 25 不受 Vercel Serverless Functions 支持，Vercel 会改用 Node.js 24；协作环境最好统一到 Node.js 24。
- `astro.config.mjs` 未设置 `site`，因此构建时跳过 sitemap。

## 7. 当前仓库成熟度

### 已有内容

- 相对完整的问题定义、论文定位和 Introduction 草稿。
- 数据集结构、baseline、消融和评测方案。
- 2024–2026 年相关工作整理。
- K12-KGraph、K12-Bench、K12-Train 和 SFT baseline 数据。
- 可构建、可部署的论文阅读网站。

### 当前实现状态

- 已实现 K12-KGraph 规范化、双层 GraphRAG 检索与子图序列化。
- 已实现概念卡、机制图、结构映射、受约束生成和多轮自我修订 pipeline。
- 已实现标准多 Agent 与 Copycat-inspired 两种生成策略。
- 已实现确定性自动指标、规则/LLM 六维评测和批量报告导出。
- 已有跨生物、化学、数学、物理的小规模运行产物。
- 仍需完成独立人工标注、严格 baseline/消融、统计显著性分析和投稿 LaTeX 工程。

因此，当前阶段应理解为“核心实验管线已经具备可运行性与可追溯产物，但还缺少独立人工验证、严格对照实验和投稿级实验报告”。

## 8. 需要尽快统一的关键决策

1. **任务范围**：继续做较宽的 Concept-to-Fable，还是以 M2NA 作为第一篇论文的唯一主任务。
2. **目标概念域**：只使用 K12 课程概念，还是构建跨心理学、经济学、计算机等领域的机制概念集。
3. **知识图谱定位**：KG 是论文核心输入，还是只作为知识来源与一个实验条件。
4. **主贡献类型**：benchmark、方法，还是二者并重。
5. **教育效果强度**：首篇论文是否只做小规模人工理解实验。

我的判断是：先选择 M2NA，完成 20–50 个概念的 pilot，再根据机制图质量、生成可控性和评测一致性决定是否扩大到完整 benchmark。

## 9. 推荐阅读顺序

1. [`README.md`](README.md)
2. [`ConceptFable_AAAI_收窄任务_学术问题定义.md`](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md)
3. [`ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md`](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md)
4. [`M2NA_2024-2026相关论文检索.md`](doc/论文调研/M2NA_2024-2026相关论文检索.md)
5. [`数据集codex给的建议.md`](doc/数据集/数据集codex给的建议.md)
6. [`评估部分codex给的建议2.md`](doc/评估/评估部分codex给的建议2.md)
7. [`K12-KGraph README`](data/K12-KGraph/README.md)

## 10. 分支协作建议

当前检出的是 `main`，工作区在新增本总结文件前保持干净。你准备开始工作时，可以从最新 `main` 创建自己的分支：

```bash
git switch main
git pull --ff-only
git switch -c <你的分支名>
```

建议按工作内容命名，例如：

```text
feat/m2na-pilot
feat/graph-rag
exp/baseline-evaluation
docs/problem-formulation
```

当前数据目录 README 标注为 `CC-BY-NC-SA-4.0`，但仓库根目录没有独立 `LICENSE` 文件。后续公开发布、复用数据或引入其他数据集时，应逐项核对许可和署名要求。
