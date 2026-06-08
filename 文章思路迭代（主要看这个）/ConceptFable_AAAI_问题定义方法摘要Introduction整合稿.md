# ConceptFable AAAI 整合稿

本文档整合了三份 Codex 建议：

- `数据集codex给的建议.md`
- `评估部分codex给的建议1.md`
- `评估部分codex给的建议2.md`

核心定位：不要把论文写成“一个寓言 prompt”，而要写成一个可定义、可构建数据集、可自动评估、可做人类学习实验的新任务：

> Knowledge-Grounded Pedagogical Fable Generation for Abstract Concept Learning

中文定位：

> 面向抽象概念学习的知识增强教学寓言生成。

---

## 1. 推荐题目

主标题建议：

> ConceptFableBench: Evaluating Knowledge-Grounded Fable Generation for Abstract Concept Learning

或者更偏方法：

> Teaching Abstract Concepts through Fables: Knowledge-Grounded Narrative Analogical Explanation with Large Language Models

如果论文主贡献更偏数据集和评估，建议用第一个。如果方法框架更强，建议用第二个。

---

## 2. 问题动机

大语言模型已经能够生成概念解释，但现有解释形式大多是定义式、说明式和列表式的。对于“路径依赖”“认知失调”“陌生化”“机会成本”“涌现”等抽象概念，学习者往往不只是需要知道定义，还需要理解概念背后的结构、条件、机制和可迁移边界。

人类学习抽象概念时，常常依赖类比、隐喻和故事。寓言是一种特殊的教学叙事：它不直接给出定义，而是通过角色、情节、冲突和转折，把抽象结构编码进具体事件中，使读者通过类比推理获得理解。这种形式可能比直白定义更容易被记住，也更有利于迁移到新情境。

然而，现有研究和数据集通常只覆盖其中一部分：

- 概念解释数据集关注如何用简单语言解释知识，但不要求叙事化或隐含表达。
- 故事生成数据集关注故事连贯性和创造性，但不要求忠实表达某个抽象概念。
- 类比/隐喻数据集关注跨域映射或类比理解，但通常不是完整寓言，也不评估学习效果。

因此，当前缺少一个系统任务来回答：

> 大语言模型能否基于可靠知识，将抽象概念转化为忠实、隐含、可映射、具有教学效果的寓言？

这个问题的关键不在于模型是否“会写故事”，而在于模型是否能完成一种结构化转换：

```text
abstract concept knowledge
-> concept structure
-> analogical narrative plan
-> implicit fable
-> story-concept mapping
-> understanding / transfer questions
```

---

## 3. 问题定义

本文定义一个新任务：Concept-to-Fable Generation。

给定一个抽象概念 `c`，相关领域 `d`，外部知识材料 `K`，以及生成约束 `R`，模型需要生成一个教学寓言输出 `Y`：

```text
Input:
  c: target concept
  d: domain of the concept
  K: retrieved or curated knowledge
  R: generation constraints

Output:
  Y = (F, M, Q)

  F: an implicit fable
  M: a story-concept mapping
  Q: understanding and transfer questions
```

其中，`K` 包含定义、关键属性、核心机制、典型例子和反例。模型首先需要从 `K` 中抽取概念结构 `S`：

```text
S = {
  definition,
  key_elements,
  causal_or_relational_mechanism,
  typical_examples,
  counterexamples
}
```

生成的寓言 `F` 需要满足以下约束：

1. Concept Faithfulness  
   寓言必须忠实表达目标概念的核心机制，不能产生与定义或知识来源冲突的解释。

2. Implicitness  
   寓言正文不应直接出现概念名称，也不应使用明显领域术语或定义性表达。

3. Analogical Mappability  
   故事中的角色、事件、冲突和转折必须能够映射到概念结构中的关键元素。

4. Narrative Quality  
   寓言应简洁、连贯、有核心冲突或转折，并通过情节表达寓意，而不是让角色直接说教。

5. Pedagogical Utility  
   寓言应帮助学习者理解概念、记忆概念，并能将概念迁移到新场景。

6. Diversity / Anti-template  
   寓言应避免反复使用模板化意象和结构，例如“智者点醒旅行者”“村庄异象”“河流、镜子、钟表”等高频套路。

可以进一步拆成三个可评估子任务：

### Task 1: Concept Structure Extraction

```text
Input: concept knowledge K
Output: structured concept representation S
```

目标是从检索知识中提取定义、关键机制、条件、例子和反例。

### Task 2: Concept-to-Fable Generation

```text
Input: concept structure S and constraints R
Output: implicit fable F
```

目标是把抽象概念结构转化为一则不直接泄题的寓言。

### Task 3: Fable-to-Concept Mapping

```text
Input: fable F and concept structure S
Output: story-concept mapping M
```

目标是解释故事元素如何对应概念结构。

---

## 4. 解决办法：KG-Fable

建议方法名：

> KG-Fable: Knowledge-Grounded Fable Generation with Structured Analogical Planning

整体流程：

```text
Concept
-> Knowledge Retrieval
-> Concept Structure Extraction
-> Analogical Fable Planning
-> Constrained Fable Generation
-> Self-Revision
-> Mapping and Question Generation
```

### 4.1 Knowledge Retrieval

根据目标概念检索或整理可靠知识来源，例如百科、教材、课程 glossary、论文摘要或已有教育解释数据。目标不是让模型凭参数记忆解释概念，而是用外部知识约束概念定义和机制。

输出：

```text
definition
key properties
mechanism
examples
counterexamples
key terms
```

### 4.2 Concept Structure Extraction

将自然语言知识转换成结构化概念表示。

例如“路径依赖”可以抽取为：

```text
initial choice
positive feedback
increasing switching cost
lock-in
suboptimal persistence
```

这一步是整篇论文的方法核心之一，因为寓言需要表达的不是概念名本身，而是概念的内部结构。

### 4.3 Analogical Fable Planning

为概念结构寻找具体、日常、非模板化的故事源域，并建立初步映射。

例如：

```text
Concept structure:
initial choice -> positive feedback -> switching cost -> lock-in

Narrative plan:
a small restaurant buys one unusual stove
-> recipes and workers adapt to it
-> customers come for dishes shaped by that stove
-> replacing it becomes increasingly costly
```

规划阶段输出：

```text
source domain
characters
central conflict
turning point
story elements
concept-element mapping
forbidden terms
template risks
```

### 4.4 Constrained Fable Generation

根据规划生成寓言。约束包括：

- 不出现概念名。
- 不出现关键术语。
- 篇幅有限。
- 角色数量有限。
- 情节承载意义，不直接说教。
- 避免高频寓言模板和意象。

### 4.5 Self-Revision

生成后进行自我检查和修订：

```text
Leakage check: 是否泄露概念名或术语？
Faithfulness check: 是否与知识来源冲突？
Coverage check: 是否覆盖关键概念元素？
Mapping check: 故事元素是否真实存在且映射合理？
Template check: 是否使用黑名单意象或套路？
```

### 4.6 Mapping and Question Generation

最后输出：

1. 映射解释：故事元素如何对应概念结构。
2. 理解问题：检验学习者是否理解概念核心。
3. 迁移问题：检验学习者是否能把概念应用到新领域。

---

## 5. 数据集设计：ConceptFableBench

推荐数据集名称：

> ConceptFableBench: A Benchmark for Knowledge-Grounded Pedagogical Fable Generation

一句话定义：

> ConceptFableBench evaluates whether language models can transform abstract concepts into faithful, implicit, and pedagogically useful fables through analogical mapping.

### 5.1 数据来源

现有数据集可以作为支撑，但没有一个直接等于目标任务。

概念解释来源：

- ELI5
- Simple English Wikipedia
- ScienceQA
- WorldTree

故事和寓言来源：

- Aesop's Fables
- ROCStories
- WritingPrompts
- Moral Stories
- DS-TF1-EN-3M

类比和隐喻来源：

- StoryAnalogy
- SCAN
- FLUTE

论文可以明确说：这些资源分别覆盖概念解释、故事生成、类比理解，但没有覆盖“抽象概念 -> 隐性寓言 -> 概念映射 -> 学习效果评估”的完整链条。因此本文构建 ConceptFableBench。

### 5.2 样本结构

每条样本建议包含：

```json
{
  "concept": "path dependence",
  "domain": "economics / social science",
  "difficulty": "intermediate",
  "source_knowledge": [
    {
      "source": "textbook / wikipedia / paper",
      "text": "..."
    }
  ],
  "concept_structure": {
    "definition": "...",
    "key_mechanism": [
      "initial choice",
      "positive feedback",
      "switching cost",
      "lock-in"
    ],
    "examples": ["QWERTY keyboard"],
    "counterexamples": ["..."]
  },
  "fable": "...",
  "mapping": [
    {
      "story_element": "the first machine the shop bought",
      "concept_element": "initial choice"
    }
  ],
  "understanding_question": "...",
  "transfer_question": "...",
  "quality_labels": {
    "faithfulness": 1,
    "implicitness": 1,
    "narrative_quality": 4,
    "mapping_quality": 5
  }
}
```

### 5.3 规模建议

AAAI 投稿建议规模：

| 子集 | 数量 | 用途 |
|---|---:|---|
| Concept Pool | 300-500 concepts | 全部概念集合 |
| Auto-generated Fables | 3,000-5,000 | 训练、对比、分析 |
| Human-verified Fables | 500-1,000 | 主评测集 |
| Human-written Gold Fables | 100-200 | 高质量参考 |
| Learning Evaluation Set | 50-100 concepts | 人类学习实验 |

### 5.4 概念领域

建议覆盖：

- Psychology: cognitive dissonance, confirmation bias, framing effect
- Economics: opportunity cost, path dependence, sunk cost fallacy
- Sociology: social capital, role conflict, norm
- Literary studies / communication: defamiliarization, agenda setting, framing
- AI / computer science: overfitting, gradient descent, emergence, alignment
- Philosophy / logic: falsifiability, induction, reductionism

---

## 6. 评估协议：CF-Eval

推荐评估名称：

> CF-Eval: Evaluation Protocol for Conceptual Fable Generation

整体分成三层：

```text
Intrinsic automatic evaluation
Expert / human evaluation
Human learning evaluation
```

### 6.1 Automatic Evaluation

自动评估用于大规模筛选和可复现比较。

核心指标：

| 维度 | 指标 | 说明 |
|---|---|---|
| Constraint Following | Format Validity | 是否输出寓言、映射、问题 |
| Implicitness | Hard Leakage Rate | 是否直接出现概念名 |
| Implicitness | Soft Leakage Rate | 是否出现明显术语 |
| Concept Grounding | Concept Coverage | 是否覆盖关键概念元素 |
| Faithfulness | Contradiction Rate | 是否与知识来源冲突 |
| Mapping | Mapping Consistency | 故事元素和概念元素是否对应 |
| Diversity | Template Rate | 是否使用模板化意象和结构 |
| Diversity | Self-BLEU | 生成结果是否过度相似 |
| Readability | Readability Score | 是否易读 |

概念覆盖率：

```text
Concept Coverage = sum(element_score) / (2m)
```

其中每个关键元素得分为：

```text
0 = not expressed
1 = weakly expressed
2 = clearly expressed
```

泄露率：

```text
Hard Leakage Rate = #fables containing concept name / #all fables
Soft Leakage Rate = #fables containing key terms / #all fables
```

映射一致性：

```text
Mapping Consistency = average(Existence, Correctness, Specificity, Non-spuriousness)
```

### 6.2 Expert / Human Evaluation

建议每个样本 3 位标注者，使用 1-5 Likert 分。

维度：

| 维度 | 标注问题 |
|---|---|
| Concept Faithfulness | 这则寓言是否准确表达了目标概念？ |
| Analogical Mapping Quality | 故事元素与概念结构之间的映射是否清楚、合理？ |
| Implicitness | 寓言是否没有直接暴露概念名或术语？ |
| Narrative Quality | 故事是否连贯、简洁、有冲突或转折？ |
| Pedagogical Usefulness | 这则寓言是否有助于初学者理解概念？ |
| Novelty / Non-template | 故事是否避免模板化、陈词滥调？ |

报告：

```text
Average Human Rating
Inter-annotator Agreement
Correlation between automatic metrics and human ratings
```

### 6.3 Human Learning Evaluation

人类学习实验是最有说服力的部分，因为它回答寓言是否真的帮助学习。

对照组：

```text
A. Definition-only
B. Definition + Example
C. Direct Analogy Explanation
D. Vanilla LLM Fable
E. RAG-only Fable
F. Ours: KG-Fable
```

学习效果指标：

| 指标 | 含义 |
|---|---|
| Understanding Score | 学习者能否用自己的话解释概念 |
| Transfer Score | 能否把概念迁移到新领域 |
| Misconception Rate | 是否产生错误理解 |
| Retention Score | 24 小时或 1 周后是否还能记住 |
| Engagement / Preference | 是否更愿意阅读和继续学习 |

测试题：

```text
Definition Recall:
请用自己的话解释这个概念。

Mechanism Understanding:
这个概念成立需要哪些关键条件？

Transfer:
请在另一个领域中举一个例子，并说明为什么它符合该概念。
```

评分 rubric：

```text
0 = 无关或错误
1 = 只复述表面词
2 = 理解部分要素
3 = 准确理解核心机制
4 = 准确理解并能说明边界或反例
```

### 6.4 Ablation Study

方法消融：

| Variant | 目的 |
|---|---|
| w/o RAG | 检验知识检索是否提升忠实度 |
| w/o Concept Structure | 检验结构化抽取是否提升覆盖率 |
| w/o Analogy Planning | 检验类比规划是否提升映射质量 |
| w/o Self-Revision | 检验自检是否降低泄露和错误 |
| Full KG-Fable | 完整方法 |

核心消融指标：

```text
Concept Coverage
Contradiction Rate
Mapping Consistency
Hard / Soft Leakage Rate
Transfer Score
```

---

## 7. 创新点思考

### 创新点 1：提出 Concept-to-Fable Generation 新任务

现有 story generation 关注故事本身，现有 concept explanation 关注解释清楚，现有 analogy generation 多是直接类比。本文提出的任务要求模型把抽象概念结构转化为隐含寓言，并显式输出故事-概念映射。这使任务从 creative writing 变成了可评估的教学型类比生成。

### 创新点 2：构建 ConceptFableBench

现有数据集分别覆盖概念解释、故事生成、类比理解，但缺少三者交叉的基准。ConceptFableBench 将概念知识、概念结构、寓言、映射、理解问题、迁移问题和质量标签组织在同一条样本中。

### 创新点 3：提出 KG-Fable 方法

KG-Fable 不直接让模型写寓言，而是将生成过程拆成知识检索、概念结构抽取、类比规划、受控生成和自我修订。方法核心是 structured analogical planning，而不是简单 prompt engineering。

### 创新点 4：提出 CF-Eval 三层评估协议

CF-Eval 同时评估文本内在质量和外在学习效果：

- 自动评估：忠实度、泄露率、映射一致性、模板化。
- 专家评估：概念准确性、故事性、教学价值。
- 人类学习实验：理解、迁移、记忆和误解率。

这能回应审稿人最可能提出的问题：寓言是不是只是好看，还是确实有效？

### 创新点 5：将寓言定义为一种 human-centered knowledge interface

本文可以提出一个更高层的观点：寓言是抽象知识和人类理解之间的自然接口。模型不只是生成文本，而是在把概念结构编码进叙事事件，让学习者通过类比推理完成理解和迁移。

---

## 8. 可能风险与强化方向

### 风险 1：被认为只是 prompt engineering

应对：强调任务、数据集、结构化中间表示、消融实验和人类学习实验。不要把贡献写成“我们设计了一个 prompt”。

### 风险 2：寓言未必比直接类比更好

应对：必须加入 Direct Analogy Explanation baseline。论文主张不要写成“寓言一定全面优于类比”，而要更精确：

> Fables may provide stronger retention and transfer benefits by embedding analogical structures in memorable narratives.

### 风险 3：LLM judge 不可靠

应对：自动评估只作为 scalable proxy；主结论需要专家标注和人类学习实验支持。同时报告自动指标与人工评分的相关性。

### 风险 4：概念过难或跨领域不公平

应对：概念池分领域、分难度；人类实验采用随机分配和 counterbalancing，避免某一组刚好拿到更简单概念。

### 风险 5：数据集质量被质疑

应对：采用 LLM generation + human verification，而不是纯自动生成。为主评测集提供人工标注和 agreement。

---

## 9. Abstract Draft

下面这版不编造未完成实验结果。等实验完成后，可以在最后一句补上具体提升数字。

```text
Large language models can generate fluent explanations of abstract concepts, yet their explanations often remain definition-centric, explicit, and weakly aligned with how humans naturally learn through stories, analogies, and metaphorical situations. We introduce Concept-to-Fable Generation, a task that asks models to transform an abstract concept and its supporting knowledge into a faithful, implicit, and pedagogically useful fable, accompanied by an explicit story-concept mapping and understanding-oriented questions. The task requires models not only to write coherent narratives, but also to preserve conceptual mechanisms, avoid directly leaking the target concept, and construct interpretable analogical mappings between abstract knowledge and concrete narrative events. To study this problem, we propose ConceptFableBench, a benchmark that combines curated concept knowledge, structured concept representations, fables, story-concept mappings, and understanding and transfer questions across multiple domains. We further present KG-Fable, a knowledge-grounded generation framework that retrieves concept evidence, extracts conceptual structure, plans narrative analogies, generates constrained fables, and revises outputs with faithfulness, leakage, and mapping checks. Finally, we introduce CF-Eval, a three-level evaluation protocol covering automatic metrics, expert judgments, and human learning outcomes, including understanding, transfer, retention, and misconception rate. This work positions fables as a human-centered interface for abstract concept learning and provides a systematic foundation for evaluating narrative analogical explanations generated by language models.
```

带实验结果后的最后一句可以替换成：

```text
Experiments with multiple LLMs and a human learning study show that KG-Fable improves concept faithfulness and analogical mapping quality while yielding higher transfer and retention scores than definition-based, example-based, direct-analogy, and vanilla fable baselines.
```

前提是这些结果真实跑出来。

---

## 10. Introduction Draft

```text
Understanding abstract concepts is a central challenge in human learning. Concepts such as path dependence, cognitive dissonance, defamiliarization, opportunity cost, emergence, and falsifiability cannot be fully acquired by memorizing a short definition. Learners must grasp the underlying structure of the concept: the entities involved, the relations among them, the conditions under which the concept applies, and the boundaries that distinguish valid examples from superficial associations. Although large language models (LLMs) have become increasingly capable of producing fluent explanations, their default responses to conceptual questions are often explicit, definition-centric, and organized as lists of properties or examples. Such explanations may be informative, but they do not necessarily provide the kind of memorable and transferable representation through which humans often internalize abstract knowledge.

Stories, analogies, and fables offer a different route to conceptual understanding. A fable does not simply state a definition; it encodes an abstract structure into concrete narrative events. Characters, conflicts, actions, and consequences can serve as analogical carriers of conceptual mechanisms. When a reader infers the underlying idea from the story, the concept is no longer only a verbal label but becomes associated with a memorable situation. This makes fables a potentially powerful form of human-centered explanation: they can hide formal terminology while preserving conceptual structure, invite learners to infer rather than merely receive an explanation, and support later transfer by grounding an abstract relation in an interpretable narrative.

Despite this potential, current research does not provide a systematic framework for generating and evaluating such explanations. Existing concept explanation datasets focus on simplifying knowledge or answering educational questions, but they typically do not require implicit narrative generation. Story generation benchmarks evaluate coherence, creativity, or plot structure, but they do not require the story to faithfully express a target concept. Analogy and metaphor datasets study cross-domain correspondences, yet they often operate at the level of phrases, sentence pairs, or story-to-story relations, rather than the transformation from an abstract concept into an instructional fable. As a result, we lack a task definition, benchmark, and evaluation protocol for asking whether LLMs can convert abstract knowledge into faithful, implicit, and pedagogically useful narrative analogies.

This paper introduces Concept-to-Fable Generation, a task in which a model is given an abstract concept, supporting knowledge, and generation constraints, and must produce three outputs: an implicit fable, an explicit mapping between story elements and conceptual elements, and questions that test understanding and transfer. This formulation distinguishes the task from ordinary story generation. A successful output must satisfy multiple constraints simultaneously: it must preserve the core mechanism of the target concept, avoid directly revealing the concept name or domain-specific terms, construct a clear analogical mapping, remain narratively coherent, and support human learning. The task therefore requires both knowledge grounding and structured analogical planning.

To support this task, we propose ConceptFableBench, a benchmark for knowledge-grounded pedagogical fable generation. Each example contains a target concept, domain information, curated or retrieved source knowledge, a structured representation of the concept, an implicit fable, story-concept mappings, understanding and transfer questions, and quality annotations. The benchmark is designed to cover concepts from multiple domains, including psychology, economics, sociology, literary studies, communication, artificial intelligence, computer science, philosophy, and logic. Rather than treating fables as unconstrained creative texts, ConceptFableBench treats them as structured explanatory artifacts whose conceptual faithfulness and pedagogical value can be evaluated.

We further present KG-Fable, a knowledge-grounded generation framework for this task. KG-Fable first retrieves or uses curated evidence for the target concept, then extracts a structured concept representation including definitions, key elements, mechanisms, examples, and counterexamples. It next performs analogical fable planning by selecting a concrete source domain and aligning narrative elements with conceptual elements. Based on this plan, the model generates a constrained fable that avoids concept leakage and template-like story patterns. A self-revision stage then checks for contradictions, missing concept elements, direct or indirect leakage, weak mappings, and overused narrative templates. Finally, the framework produces an explicit story-concept mapping and questions for understanding and transfer.

Evaluation is a central challenge for this problem. Fluency and coherence alone are insufficient: a fable can be well written while misrepresenting the target concept, or it can be faithful while revealing the answer too directly. We therefore introduce CF-Eval, a three-level evaluation protocol. First, automatic evaluation measures format validity, concept coverage, contradiction rate, hard and soft leakage, mapping consistency, template rate, diversity, and readability. Second, expert and human evaluation assesses conceptual faithfulness, analogical mapping quality, implicitness, narrative quality, pedagogical usefulness, and novelty. Third, human learning evaluation compares fable-based explanations with definition-only, definition-plus-example, direct analogy, vanilla LLM fable, and RAG-only baselines, measuring understanding, transfer, retention, and misconception rate. This evaluation design allows us to ask not only whether a model can generate plausible fables, but whether those fables actually help learners acquire and apply abstract concepts.

Our work makes four main contributions. First, we formulate Concept-to-Fable Generation as a new task for studying narrative analogical explanation of abstract concepts. Second, we propose ConceptFableBench, a benchmark that integrates concept knowledge, structured conceptual mechanisms, fables, mappings, and learning-oriented questions. Third, we introduce KG-Fable, a knowledge-grounded framework that combines concept structure extraction, analogical planning, constrained generation, and self-revision. Fourth, we present CF-Eval, an evaluation protocol that connects intrinsic generation quality with extrinsic human learning outcomes. Together, these contributions provide a foundation for studying fables as a human-centered interface between abstract knowledge and conceptual understanding.
```

---

## 11. 可以放进论文里的 Contribution 写法

```text
In summary, our contributions are:

1. We introduce Concept-to-Fable Generation, a new task that requires models to convert abstract concepts into faithful, implicit, and pedagogically useful fables through analogical mapping.

2. We construct ConceptFableBench, a benchmark containing concept knowledge, structured concept representations, fables, story-concept mappings, understanding questions, transfer questions, and quality annotations across multiple domains.

3. We propose KG-Fable, a knowledge-grounded framework that retrieves concept evidence, extracts conceptual structure, plans narrative analogies, generates constrained fables, and revises outputs for faithfulness, leakage, mapping consistency, and template avoidance.

4. We design CF-Eval, a three-level evaluation protocol combining automatic metrics, expert evaluation, and human learning studies on understanding, transfer, retention, and misconception rate.
```

---

## 12. 当前最推荐的论文主线

最终论文故事线建议：

```text
LLMs can explain concepts, but current explanations are often explicit and definition-centric.
Humans often learn abstract concepts through stories and analogies.
Fables can encode abstract conceptual structures into concrete narrative events.
However, no existing task or benchmark evaluates knowledge-grounded conceptual fable generation.
We define Concept-to-Fable Generation.
We build ConceptFableBench.
We propose KG-Fable.
We evaluate with CF-Eval, including human learning experiments.
```

最重要的一句话：

> This paper is not about making LLMs write better stories; it is about evaluating whether LLMs can transform abstract knowledge into faithful, implicit, and learnable narrative analogies.

