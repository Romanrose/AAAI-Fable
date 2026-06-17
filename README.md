# AAAI-Fable

这个仓库用于沉淀 AAAI 论文方向 **Concept-to-Fable Synthesis / Conceptual Fable Generation** 的阶段性材料。当前主线是：如何让语言模型把课程知识或抽象机制概念，稳定转化为忠实、可映射、可解释、并具有教学价值的寓言故事。

目前仓库已经整理为两个主要入口：

- `doc/`：论文阅读网站、论文思路、数据集方案、评估方案、调研材料和思维导图。
- `data/`：根目录数据资源，目前包含 `K12-KGraph` 相关数据，用于课程知识图谱、Graph RAG 和知识约束生成实验。

线上论文阅读网站：

[https://paper-reading-site.vercel.app](https://paper-reading-site.vercel.app)

本地网站项目路径：

`doc/paper-reading-site/`

## 当前主线

当前更推荐的论文主线不是泛化的“让 LLM 写寓言”，而是：

> 面向课程知识与抽象机制概念的可控、可解释教学寓言生成。

更具体地说，论文可以定义为 **Concept-to-Fable Synthesis** 任务：给定知识点、年级、学科、教学目标、课程知识图谱或 Graph RAG 检索子图，模型需要生成一篇寓言故事，并同时输出概念到故事元素的映射说明。

故事需要同时满足：

- **Knowledge Grounding**：故事内容受课程知识图谱和知识链约束。
- **Mechanism Preservation**：保留原概念的关键机制和因果关系。
- **Structure Mapping**：概念实体、关系和过程能映射到角色、冲突、行动和结局。
- **Controllable Generation**：通过规划、storyline 和生成约束提高稳定性。
- **Educational Evaluation**：评测知识准确性、映射忠实性、故事质量、年级适配和教学有效性。

## 目录说明

- `doc/paper-reading-site/`：Astro Starlight 论文阅读网站。包含 25 篇论文页面、PDF、研究导向 Q&A、四个核心支柱和 DeepSeek 论文问答入口。
- `doc/文章思路迭代（主要看这个）/`：论文主线、任务定义、方法摘要和 Introduction 草稿，优先级最高。
- `doc/数据集/`：ConceptFableBench / Concept-to-Fable 数据集设计建议。
- `doc/评估/`：CF-Eval、人类学习实验、baseline 和消融设计建议。
- `doc/论文调研/`：相关论文检索与 related work 组织方式。
- `doc/寓言生成对话.xmind`：思维导图，记录讨论过程和想法分支。
- `data/K12-KGraph/`：课程知识图谱与教育任务数据，可用于 Graph RAG、知识链检索和消融实验。

## 推荐阅读路径

如果是第一次进入这个项目，建议按下面顺序读：

1. 先读 `doc/paper-reading-site/` 对应的网站首页，快速了解 Concept-to-Fable 的四个支柱：知识图谱、结构映射、层次化生成、评测。
2. 再读 [ConceptFable_AAAI_收窄任务_学术问题定义.md](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md)，抓住最收敛的问题定义、任务边界和创新点。
3. 然后读 [ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md](doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md)，了解完整论文雏形，包括方法、数据集、评估和写作版本。
4. 接着读 [数据集codex给的建议.md](doc/数据集/数据集codex给的建议.md) 和 `doc/评估/` 下的两份评估建议，补齐实验设计来源。
5. 最后读 [M2NA_2024-2026相关论文检索.md](doc/论文调研/M2NA_2024-2026相关论文检索.md)，用于写 Related Work、确认 baseline 和定位 gap。

## 论文阅读网站

网站使用 Astro Starlight 搭建，位置在：

`doc/paper-reading-site/`

常用命令：

```bash
cd doc/paper-reading-site
npm install
npm run dev
npm run build
```

网站内容按四个核心支柱组织：

- 知识图谱：课程对齐、前置依赖、知识结构。
- 结构映射：概念结构到寓言角色、冲突、行动、结局的对应。
- 层次化生成：Plan-and-Write、多智能体流程、可控故事生成。
- 评测：知识准确性、映射忠实性、分级阅读适配、教学有效性。

每篇论文页面包含论文信息、与 Concept-to-Fable 的关系、可借鉴点、局限、研究导向 Q&A、PDF 链接和原文链接。

## 数据与实验方向

`data/K12-KGraph/` 已提交到仓库，可作为以下实验模块的基础：

- Graph RAG 检索课程知识子图。
- 构建知识链和先修关系约束。
- 对比 `No Retrieval`、`Text RAG`、`Graph RAG` 和 `Graph RAG + Structure Mapping`。
- 支撑 `w/o KG`、`w/o prerequisite relations`、`w/o structure mapping` 等消融实验。

## 分支说明

当前两个主要分支：

- `main`：主分支，已经合并论文阅读网站、`doc/` 结构整理和根目录 `data/`。
- `codex/paper-reading-site`：网站和材料整理的开发分支，保留完整变更历史。

两个分支的 README 应保持同步，避免路径说明和网站位置不一致。

## 后续协作建议

后续如果继续推进，建议优先围绕这几件事协作：

1. 把任务定义整理成论文中的 **Problem Formulation**。
2. 从现有材料里抽出稳定的 **Method / Dataset / Evaluation** 三节骨架。
3. 明确 Graph RAG 在方法中的位置：它是知识约束引擎，不是论文全部贡献。
4. 设计 20-50 个 pilot concepts，用于快速验证数据结构、生成流程和评估 rubric。
5. 明确 baseline 和消融：Definition-only、Vanilla LLM Fable、Text RAG、Graph RAG、w/o Structure Mapping、w/o Storyline Planning、Full Method。
