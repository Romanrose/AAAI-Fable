# AAAI-Fable

这个仓库用于沉淀 AAAI 论文方向 **ConceptFable / Conceptual Fable Generation** 的阶段性材料。当前文件主要围绕一个问题展开：如何让语言模型把抽象概念转化为忠实、隐含、可映射、并具有教学价值的寓言。

为了方便后续协作，建议优先按时间顺序阅读。这样能看到项目从“数据集与评估可行性”逐步收敛到“AAAI 任务定义、方法、论文主线和相关工作”的过程。

## 时间顺序

| 时间 | 文件 | 作用 |
|---|---|---|
| 2026-06-08 20:42 | [数据集/数据集codex给的建议.md](数据集/数据集codex给的建议.md) | 最早的数据集方案。提出没有现成数据集完全覆盖“抽象概念 -> 教学寓言 -> 概念映射 -> 理解/迁移问题”，因此建议构建组合式基准 **ConceptFableBench**。 |
| 2026-06-08 20:43 | [评估/评估部分codex给的建议1.md](评估/评估部分codex给的建议1.md) | 第一版评估方案。区分文本本身是否合格，以及是否真的帮助人学习；提出自动评估、专家评估、人类学习实验三层思路。 |
| 2026-06-08 20:44 | [评估/评估部分codex给的建议2.md](评估/评估部分codex给的建议2.md) | 更系统的评估协议 **CF-Eval**。细化 Concept Coverage、Leakage Rate、Mapping Consistency、Human Learning Evaluation 和 Ablation Study。 |
| 2026-06-08 20:49 | [文章思路迭代（主要看这个）/ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md](文章思路迭代（主要看这个）/ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md) | 第一版完整论文整合稿。包括推荐题目、问题动机、任务定义、KG-Fable 方法、ConceptFableBench、CF-Eval、创新点、风险、Abstract 和 Introduction draft。 |
| 2026-06-08 20:54 | [文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md](文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md) | 后续收窄版任务定义，也是当前最重要的方向文件。把任务聚焦为“机制概念的隐性叙事类比生成”，明确成功条件：机制保持、词汇隐藏、类比可对齐、叙事最小性。 |
| 2026-06-08 21:32 | [论文调研/M2NA_2024-2026相关论文检索.md](论文调研/M2NA_2024-2026相关论文检索.md) | 相关工作检索与组织建议。覆盖类比推理、叙事生成、结构到文本、隐喻/概念映射等方向，并给出 baseline 与 related work 的组织方式。 |
| 2026-06-08 21:48 | [寓言生成对话.xmind](寓言生成对话.xmind) | 思维导图/对话图，用于回看想法展开过程和分支。适合作为补充材料，不建议作为第一入口。 |

## 推荐阅读路径

如果是第一次进入这个项目，建议按下面顺序读：

1. 先读 [ConceptFable_AAAI_收窄任务_学术问题定义.md](文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md)，把当前最收敛的问题定义、任务边界和创新点抓住。
2. 再读 [ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md](文章思路迭代（主要看这个）/ConceptFable_AAAI_问题定义方法摘要Introduction整合稿.md)，了解完整论文雏形，包括方法、数据集、评估和写作版本。
3. 然后读 [数据集codex给的建议.md](数据集/数据集codex给的建议.md) 和两份评估建议，补齐实验设计的来源。
4. 最后读 [M2NA_2024-2026相关论文检索.md](论文调研/M2NA_2024-2026相关论文检索.md)，用于写 Related Work、确认 baseline 和定位 gap。

## 当前主线

当前更推荐的论文主线不是泛化的“寓言生成”，而是：

> 面向抽象机制概念的隐性叙事类比生成。

核心思想是：模型不能只是写一个好看的故事，而要把抽象概念中的关键机制转译为一个表面不泄露术语、内部又可回映射的短叙事。也就是说，故事需要同时满足：

- **Mechanism Preservation**：保留原概念的关键机制。
- **Lexical Concealment**：不直接暴露概念名或明显术语。
- **Analogical Alignability**：故事元素可以和概念结构清楚对齐。
- **Narrative Minimality**：叙事简洁，不用无关情节稀释机制。

## 目录说明

- `文章思路迭代（主要看这个）/`：论文主线和任务定义文件，优先级最高。
- `数据集/`：ConceptFableBench 的早期数据集设计建议。
- `评估/`：CF-Eval、人类学习实验、baseline 和消融设计。
- `论文调研/`：2024-2026 年相关论文与 related work 组织方式。
- `寓言生成对话.xmind`：思维导图，记录讨论和想法分支。

## 后续协作建议

后续如果继续推进，建议优先围绕这几件事协作：

1. 把收窄版任务定义整理成论文中的 **Problem Formulation**。
2. 从整合稿里抽出稳定的 **Method / Dataset / Evaluation** 三节骨架。
3. 根据论文调研文件确认 6-8 篇必须精读的 related work。
4. 设计 20-50 个 pilot concepts，用于快速验证数据结构、生成流程和评估 rubric。
5. 明确 baseline：Definition-only、Definition + Example、Direct Analogy、Vanilla LLM Fable、Ours。
