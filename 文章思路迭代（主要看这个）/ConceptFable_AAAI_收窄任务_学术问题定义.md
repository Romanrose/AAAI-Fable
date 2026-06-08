# 收窄版 AAAI 任务：机制概念的隐性叙事类比生成

## 1. 论文定位

上一版任务把“知识检索、寓言生成、映射解释、问题生成、人类学习实验”都包含进来，作为完整研究计划是成立的，但对一篇 AAAI 论文来说可能过宽。更适合收窄成一个明确、可评估、可复现实验的新任务：

> **Implicit Narrative Analogy Generation for Mechanism-Centric Concept Explanation**

中文：

> **面向机制型概念解释的隐性叙事类比生成**

这版不再主打“寓言 prompt”，也不把重点放在“让模型讲一个有趣故事”。核心问题是：

> 给定一个抽象概念的机制结构，模型能否生成一段不直接暴露概念名称和术语、但在结构上忠实表达该概念机制的短叙事类比？

这里的研究对象不是泛化的“寓言”，而是更学术化的：

> **implicit narrative analogy**

也就是一种隐性叙事类比：它通过具体角色、事件和因果关系承载抽象概念机制，但在正文中不直接解释概念。

---

## 2. 为什么要这样收窄

“抽象概念到寓言生成”这个题很有想象力，但如果直接作为论文任务，容易被审稿人质疑三个问题：

1. **任务边界过宽**  
   什么都可以是寓言，故事好坏、教学价值、文学性和概念准确性混在一起，评估会散。

2. **贡献像 prompt engineering**  
   如果论文看起来只是把微信公众号里的 prompt 改写成实验，很难形成 AAAI 级别的技术问题。

3. **人类学习实验成本高**  
   要证明“寓言帮助学习”，需要严谨的人类实验。如果放在第一篇论文里作为主贡献，时间和风险都很大。

因此更稳的做法是：先把任务定义成一个 **机制保持的隐性类比生成问题**。这样它可以连接到已有的 NLP 研究问题：

- analogy generation
- story generation
- controllable generation
- concept explanation
- semantic faithfulness
- structure-to-text generation

---

## 3. 收窄后的核心问题

本文关注一类特定概念：**机制型抽象概念**。

所谓机制型概念，是指其含义不是一个孤立定义，而是由若干关键要素及其关系构成。例如：

```text
path dependence:
initial choice -> reinforcement -> increasing switching cost -> lock-in

cognitive dissonance:
inconsistent beliefs/actions -> psychological tension -> rationalization or attitude change

overfitting:
model adapts to training-specific patterns -> performs well on seen data -> generalizes poorly to unseen data

defamiliarization:
ordinary object/event -> presented through unusual perspective/form -> renewed perception
```

这类概念适合用结构化类比表达，因为它们包含清晰的角色、关系、状态变化或因果链。

本文的问题可以定义为：

> **Can language models generate implicit narrative analogies that preserve the mechanism of an abstract concept without directly naming or explaining it?**

中文：

> **语言模型能否在不直接命名或解释概念的情况下，生成一段能够保持抽象概念机制结构的隐性叙事类比？**

---

## 4. 学术化任务定义

我们定义一个新任务：**Mechanism-to-Narrative Analogy Generation**，简称 **M2NA**。

给定一个目标概念 `c` 及其机制表示 `G_c`，模型需要生成一个短叙事 `N` 和一个结构映射 `A`。

```text
Input:
  c: target concept
  G_c: mechanism graph of the concept
  T_c: forbidden lexical set

Output:
  N: implicit narrative analogy
  A: alignment between concept mechanism and narrative structure
```

其中，`G_c` 是一个机制图：

```text
G_c = (V_c, E_c)
```

`V_c` 表示概念中的关键要素，例如状态、角色、条件、过程或结果；`E_c` 表示要素之间的关系，例如因果、时间、对比、强化、抑制或转化关系。

例如，路径依赖可以表示为：

```json
{
  "concept": "path dependence",
  "nodes": [
    "initial choice",
    "reinforcing feedback",
    "switching cost",
    "lock-in",
    "persistence of possibly suboptimal outcome"
  ],
  "edges": [
    ["initial choice", "reinforcing feedback", "enables"],
    ["reinforcing feedback", "switching cost", "increases"],
    ["switching cost", "lock-in", "causes"],
    ["lock-in", "persistence of possibly suboptimal outcome", "leads_to"]
  ]
}
```

`T_c` 是禁用词集合，包括概念名称、同义表达和高泄露术语。例如对 path dependence：

```text
path dependence, lock-in, switching cost, positive feedback, historical contingency
```

模型需要生成：

### 4.1 隐性叙事类比 `N`

`N` 是一个短叙事文本。它应通过具体人物、物体、事件或制度表达 `G_c` 的机制结构，但不能直接出现 `c` 或 `T_c` 中的词。

### 4.2 结构映射 `A`

`A` 是概念机制和叙事结构之间的对齐关系：

```text
A: V_c ∪ E_c -> V_n ∪ E_n
```

其中 `V_n` 是叙事中的角色、物体、状态或事件，`E_n` 是叙事中的关系或变化。

例如：

```json
[
  {
    "concept_element": "initial choice",
    "narrative_element": "the shop first bought a rare stove"
  },
  {
    "concept_element": "reinforcing feedback",
    "narrative_element": "new recipes and worker habits gradually formed around the stove"
  },
  {
    "concept_element": "switching cost",
    "narrative_element": "replacing the stove would require retraining workers and redesigning the menu"
  }
]
```

---

## 5. 成功输出的判定条件

一个成功的输出需要同时满足四个条件。

### 5.1 Mechanism Preservation

叙事必须覆盖概念机制图中的关键节点和边。也就是说，它不仅要表达某个模糊主题，还要表达概念内部的结构。

不合格例子：

```text
只写“一个人做了选择后来后悔”，但没有体现反馈强化、转换成本和锁定。
```

合格目标：

```text
故事中能找到初始选择、后续强化、改变代价升高、最终难以退出这几个结构。
```

### 5.2 Lexical Concealment

叙事正文不能直接泄露目标概念名称，也不能使用高提示性的领域术语。

这让任务不同于普通解释生成。普通解释追求清楚，而该任务追求：

```text
semantic preservation under lexical concealment
```

即在词面隐藏的条件下保持语义结构。

### 5.3 Analogical Alignability

叙事元素必须能被明确映射回概念机制元素。若故事很好看，但无法说明哪个情节对应哪个机制节点，就不算成功。

### 5.4 Narrative Minimality

叙事应尽量短小、具体、连贯，避免无关人物、复杂世界观和文学化堆砌。该任务不是文学创作，而是结构化解释。

---

## 6. 任务与原“寓言生成”的区别

本文不研究广义寓言生成。广义寓言生成可能关注：

- 道德教训
- 文学风格
- 童话感
- 情节趣味
- 角色拟人
- 结尾反转

本文研究的是：

```text
abstract mechanism -> implicit narrative analogy
```

因此，“寓言”只是一个直观名称，真正的学术对象是 **narrative analogy with hidden target concept**。

换句话说，这篇论文不是问：

> 模型能不能写一则关于某个概念的寓言？

而是问：

> 模型能不能在不直接暴露概念词汇的情况下，把一个抽象概念的机制图转写为一个可对齐、可验证的叙事结构？

---

## 7. 推荐论文任务边界

为了适合一篇 AAAI 的体量，建议第一篇论文只做以下内容：

### 包含

1. 定义 M2NA 任务。
2. 构建一个中等规模 benchmark。
3. 标注或半自动构建概念机制图。
4. 生成隐性叙事类比和映射。
5. 评估机制覆盖、泄露率、映射质量、叙事质量。
6. 做小规模人类偏好或理解验证作为辅助。

### 暂不作为主贡献

1. 大规模人类学习实验。
2. 24 小时或 1 周 retention study。
3. 复杂 RAG 系统。
4. 多 agent 自动科研框架。
5. 连环画、多模态、情感支持对话。
6. 所有领域概念的全覆盖。

这样论文可以更聚焦：

```text
Problem: mechanism-preserving implicit narrative analogy generation
Dataset: concept mechanism graphs + narratives + alignments
Method: structure-aware planning and constrained generation
Evaluation: preservation, concealment, alignability, narrative quality
```

---

## 8. 更正式的问题定义段落

下面这段可以直接作为论文 Problem Definition 的初稿。

```text
We study Mechanism-to-Narrative Analogy Generation (M2NA), a task that requires a model to verbalize the mechanism of an abstract concept as an implicit narrative analogy. Given a target concept c, a mechanism graph G_c = (V_c, E_c) describing its key conceptual elements and relations, and a forbidden lexical set T_c containing the concept name and high-leakage domain terms, the model must generate a short narrative N and an alignment A between the concept mechanism and the narrative structure. The narrative N should instantiate the abstract mechanism in a concrete situation while avoiding terms in T_c. The alignment A maps conceptual nodes and relations in G_c to narrative entities, events, states, and relations in N. A valid output must satisfy four requirements: mechanism preservation, lexical concealment, analogical alignability, and narrative minimality. Unlike standard concept explanation, M2NA evaluates whether a model can preserve conceptual structure without explicit terminology. Unlike open-ended story generation, it requires the generated narrative to be structurally grounded in a target concept mechanism. Unlike direct analogy generation, it realizes the analogy as an implicit narrative whose target concept is hidden from the reader.
```

中文对应：

> 我们研究机制到叙事类比生成（Mechanism-to-Narrative Analogy Generation, M2NA）任务。该任务要求模型将抽象概念的机制结构转写为一段隐性叙事类比。给定目标概念 `c`、描述其关键概念要素和关系的机制图 `G_c = (V_c, E_c)`，以及包含概念名称和高泄露领域术语的禁用词集合 `T_c`，模型需要生成一段短叙事 `N` 和概念机制与叙事结构之间的对齐 `A`。叙事 `N` 应在具体情境中实例化抽象机制，同时避免使用 `T_c` 中的词。对齐 `A` 将 `G_c` 中的概念节点和关系映射到 `N` 中的叙事实体、事件、状态和关系。有效输出需要满足四个要求：机制保持、词汇隐藏、类比可对齐和叙事最小性。不同于标准概念解释，M2NA 评估模型能否在不使用显式术语的情况下保持概念结构；不同于开放式故事生成，它要求生成叙事必须由目标概念机制约束；不同于直接类比生成，它将类比实现为一种目标概念被隐藏的隐性叙事。

---

## 9. 这版任务的创新点

这版的创新更清楚，建议压成三个：

### 9.1 Task Innovation

提出 M2NA，将“抽象概念解释”形式化为“机制图到隐性叙事类比”的结构保持生成任务。

### 9.2 Benchmark Innovation

构建包含概念机制图、禁用术语、隐性叙事、结构映射和质量标注的 benchmark，使该任务可评估。

### 9.3 Method Innovation

提出 structure-aware generation 方法，先规划机制到叙事的对齐，再生成文本，并通过自检降低术语泄露和结构遗漏。

---

## 10. 这版更适合 AAAI 的原因

1. 任务边界清楚：机制图到叙事类比。
2. 输入输出形式化：`G_c, T_c -> N, A`。
3. 评估更可控：机制覆盖、泄露率、映射质量都能直接测。
4. 不依赖大规模人类学习实验作为主证明。
5. 和已有 NLP 问题连接紧：structure-to-text、controlled generation、analogy generation、faithfulness evaluation。
6. 避免被认为是微信公众号 prompt 的学术包装。

---

## 11. 一句话版

> 本文研究的不是“让模型写寓言”，而是“让模型在隐藏目标概念术语的条件下，将抽象概念的机制图转写为一个结构可对齐的短叙事类比”。

