**目前没有一个现成数据集直接等于“抽象概念 → 教学寓言 → 概念映射 → 理解/迁移问题”**。所以更合理的做法是：用现有数据集分别支撑四个部分，再构建你自己的 **ConceptFableBench**。

我建议把数据集设计成一个“组合式基准”，而不是从零硬标全部。

**1. 相关数据集梳理**

| 类别 | 数据集 | 可借用什么 | 局限 |
|---|---|---|---|
| 概念解释 | [ELI5](https://modeldatabase.com/datasets/eli5.html) | 面向普通人的长解释，适合做“直白解释 baseline” | 问答形式，不是结构化概念定义 |
| 简明百科 | [Simple English Wikipedia](https://huggingface.co/datasets/juno-labs/simple_wikipedia/blob/main/README.md) | 简单语言解释概念，可抽取概念定义 | 不一定有教学结构 |
| 教育解释 | [ScienceQA](https://scienceqa.github.io/index.html) | 有 lecture 和 explanation，可用于教育型解释评估 | 偏中小学科学，不是抽象人文/社科概念 |
| 多跳解释 | [WorldTree V2](https://aclanthology.org/2020.lrec-1.671/) | 结构化 explanation graph，适合参考“概念结构抽取” | 领域偏科学问答 |
| 故事生成 | [ROCStories](https://cs.rochester.edu/nlp/rocstories/) | 五句短故事，有因果和时间结构 | 太短，不是寓言，也没有概念映射 |
| 故事生成 | WritingPrompts | 长故事生成常用数据集 | 太开放，故事质量参差，和教学无关 |
| 寓言/道德故事 | [Aesop’s Fables / Project Gutenberg](https://gutenberg.org/ebooks/28) | 经典寓言文本，可学寓言风格 | 规模小，概念主要是道德教训 |
| 大规模寓言 | [DS-TF1-EN-3M](https://huggingface.co/datasets/klusai/ds-tf1-en-3m) | 300万合成 moral fables，有故事 scaffold | 合成数据，偏儿童道德寓言，不是学术概念 |
| 道德叙事 | [Moral Stories](https://huggingface.co/datasets/demelin/moral_stories/blob/main/README.md) | 结构化叙事：norm、context、intention、action、consequence | 面向社会规范，不是概念学习 |
| 故事级类比 | [StoryAnalogy](https://aclanthology.org/2023.emnlp-main.706/) | 最相关之一：故事级类比和类比识别 | 目标是 analogical understanding，不是概念教学 |
| 科学/创意类比 | [SCAN](https://arxiv.org/abs/2211.15268) | 多属性、多关系的跨域类比映射 | 不是生成寓言 |
| 隐喻/修辞理解 | [FLUTE](https://arxiv.org/abs/2205.12404) | 有 metaphor、simile、idiom 的解释型标注 | 偏理解/NLI，不是生成任务 |

**2. 最相关的不是一个，而是三组**

你这个任务最该借鉴的是：

第一组：**概念解释数据**
- ELI5
- Simple Wikipedia
- ScienceQA
- WorldTree

它们解决的是：概念知识从哪里来，直白解释 baseline 怎么设。

第二组：**寓言/故事数据**
- Aesop’s Fables
- ROCStories
- Moral Stories
- DS-TF1-EN-3M

它们解决的是：寓言/短故事的叙事结构怎么建模。

第三组：**类比/隐喻数据**
- StoryAnalogy
- SCAN
- FLUTE

它们解决的是：故事和抽象概念之间如何建立映射。

你的创新点正好在三者交叉处：

```text
Concept Explanation
      +
Narrative / Fable Generation
      +
Analogical Mapping
      =
Concept-to-Fable Generation
```

**3. 我建议你的数据集结构**

数据集每条样本不要只存一篇寓言，而要存成这种结构：

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
    "examples": ["QWERTY keyboard", "..."],
    "counterexamples": ["..."]
  },
  "fable": "...",
  "mapping": [
    {
      "story_element": "the first machine the shop bought",
      "concept_element": "initial choice"
    },
    {
      "story_element": "workers trained only on that machine",
      "concept_element": "increasing switching cost"
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

**4. 数据来源怎么设置**

我建议分三层：

**Layer A：概念池**

先做 300-500 个抽象概念，覆盖：

- 认知心理学：cognitive dissonance, confirmation bias, framing effect
- 经济学：opportunity cost, path dependence, sunk cost fallacy
- 社会学：social capital, norm, role conflict
- 文学/传播：defamiliarization, agenda setting, framing
- AI/计算机：overfitting, gradient descent, emergence, alignment
- 哲学/逻辑：falsifiability, induction, reductionism

概念可以从 Wikipedia、Simple Wikipedia、OpenStax、课程 glossary、教材索引中抽取。

**Layer B：知识材料**

每个概念配 2-5 条来源：

```text
definition
key properties
mechanism
example
non-example
```

这部分是 RAG 的依据，也是 faithfulness 评估的依据。

**Layer C：寓言与映射**

这里可以采用两阶段：

1. LLM 生成候选寓言、映射和问题。
2. 人工标注/筛选高质量样本。

不要全靠人工从零写，会太慢；也不要全靠 LLM，不然 AAAI 审稿会质疑质量。

**5. 数据集规模建议**

如果目标是 AAAI，我建议这样做：

| 子集 | 数量 | 用途 |
|---|---:|---|
| Concept Pool | 500 concepts | 全部概念集合 |
| Auto-generated Fables | 3,000-5,000 | 训练/对比/分析 |
| Human-verified Fables | 500-1,000 | 主评测集 |
| Human-written Gold Fables | 100-200 | 高质量参考集 |
| Learning Evaluation Set | 50-100 concepts | 做真人学习实验 |

这样规模不会太夸张，但看起来完整。

**6. 数据集可以分成三个任务**

为了论文更稳，别只设一个生成任务。可以拆成：

**Task 1: Concept Structure Extraction**

输入概念知识，输出结构化概念机制。

```text
definition → key elements / causal mechanism / examples
```

**Task 2: Concept-to-Fable Generation**

输入概念结构，输出寓言。

```text
concept structure → implicit fable
```

**Task 3: Fable-to-Concept Mapping**

输入寓言和概念，输出映射解释。

```text
fable + concept → story-concept mapping
```

这个拆法很好，因为它让数据集不只是 creative writing，而是有可评估的中间推理。

**7. 最推荐的最终数据集定位**

我建议你的数据集叫：

> **ConceptFableBench: A Benchmark for Knowledge-Grounded Pedagogical Fable Generation**

一句话定义：

> ConceptFableBench evaluates whether language models can transform abstract concepts into faithful, implicit, and pedagogically useful fables through analogical mapping.

中文：

> ConceptFableBench 用于评估语言模型能否通过类比映射，将抽象概念转化为忠实、隐含且具有教学价值的寓言。

我的建议是：**不要找一个现成数据集硬改；你应该明确说现有数据集分别覆盖“解释”“故事”“类比”，但没有覆盖三者交叉，因此我们构建 ConceptFableBench。**这会更像一篇论文的贡献。