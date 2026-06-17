下面是一套比较适合 AAAI 投稿的 **Conceptual Fable Generation 评估标准**。我建议把它命名为：

> **CF-Eval: Evaluation Protocol for Conceptual Fable Generation**

它分成三层：**自动评估、专家/人工评估、人类学习实验**。这样既有计算机评估的规模和可复现性，也有人类学习效果的说服力。

**1. Automatic Evaluation**

用于大规模评估所有生成结果。

| 维度 | 指标 | 说明 |
|---|---|---|
| Constraint Following | Format Validity | 是否按要求输出寓言、映射、问题 |
| Constraint Following | Length / Role Constraint | 是否满足篇幅、角色数等约束 |
| Implicitness | Hard Leakage Rate ↓ | 寓言正文是否直接出现概念名 |
| Implicitness | Soft Leakage Rate ↓ | 是否出现明显领域术语或定义性表达 |
| Concept Grounding | Concept Coverage ↑ | 是否覆盖概念结构中的关键元素 |
| Faithfulness | Contradiction Rate ↓ | 是否与检索知识或标准定义冲突 |
| Mapping | Mapping Consistency ↑ | 故事元素和概念元素是否对应 |
| Diversity | Self-BLEU ↓ | 生成寓言之间是否模板化 |
| Diversity | Template Rate ↓ | 是否频繁使用黑名单意象/套路 |
| Readability | Readability Score ↑ | 文本是否易读 |

其中最重要的自动指标是：

```text
Concept Coverage
Mapping Consistency
Hard / Soft Leakage Rate
Contradiction Rate
Template Rate
```

**自动评估公式示例**

假设每个概念有 `m` 个关键元素，每个元素得分为 0/1/2：

```text
Concept Coverage = Σ element_score / (2m)
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

**2. Expert / Human Evaluation**

用于验证自动评估可靠性，也用于评估自动指标难以覆盖的质量。

建议每个样本 3 位标注者，使用 1-5 Likert 评分。

| 维度 | 标注问题 |
|---|---|
| Concept Faithfulness | 这则寓言是否准确表达了目标概念？ |
| Analogical Mapping Quality | 故事元素与概念结构之间的映射是否清楚、合理？ |
| Implicitness | 寓言是否没有直接暴露概念名或术语？ |
| Narrative Quality | 故事是否连贯、简洁、有冲突或转折？ |
| Pedagogical Usefulness | 这则寓言是否有助于初学者理解概念？ |
| Novelty / Non-template | 故事是否避免模板化、陈词滥调？ |

可以报告：

```text
Average Human Rating
Inter-annotator Agreement
Correlation between automatic metrics and human ratings
```

这个相关性分析很重要，可以证明你的自动评估不是拍脑袋。

**3. Human Learning Evaluation**

这是 AAAI 最有说服力的部分。目标是证明寓言不只是生成得好，而是真的帮助学习。

**对照组设置**

至少比较 5 组：

```text
A. Definition-only
B. Definition + Example
C. Direct Analogy Explanation
D. Vanilla LLM Fable
E. Ours: Knowledge-grounded Conceptual Fable
```

如果空间允许，加消融：

```text
Ours w/o RAG
Ours w/o Concept Structure
Ours w/o Analogy Planning
Ours w/o Self-Revision
```

**学习效果指标**

| 指标 | 测什么 |
|---|---|
| Understanding Score | 学习者能否用自己的话解释概念 |
| Transfer Score | 能否把概念迁移到新领域/新场景 |
| Misconception Rate ↓ | 是否产生错误理解 |
| Retention Score | 延迟 24 小时或 1 周后是否还能记住 |
| Engagement / Preference | 学习者是否更愿意阅读和继续学习 |

其中 AAAI 主打：

```text
Understanding Score
Transfer Score
Retention Score
Misconception Rate
```

Preference 只能做辅助，不要作为主结果。

**测试题设计**

每个概念至少设计三类题：

```text
1. Definition Recall:
请用自己的话解释这个概念。

2. Mechanism Understanding:
这个概念成立需要哪些关键条件？

3. Transfer:
请在另一个领域中举一个例子，并说明为什么它符合该概念。
```

评分可以用 0-4 rubric：

```text
0 = 无关或错误
1 = 只复述表面词
2 = 理解部分要素
3 = 准确理解核心机制
4 = 准确理解并能说明边界/反例
```

**4. Ablation Study**

AAAI 会很看重这个。你的方法如果包含：

```text
RAG
Concept Structure Extraction
Analogy Planning
Self-Revision
```

就做：

| Variant | 用途 |
|---|---|
| w/o RAG | 看知识检索是否提升忠实度 |
| w/o Concept Structure | 看结构化概念抽取是否提升覆盖率 |
| w/o Analogy Planning | 看类比规划是否提升映射质量 |
| w/o Self-Revision | 看自检是否降低泄露和错误 |
| Full Model | 完整方法 |

消融指标建议用：

```text
Faithfulness
Coverage
Mapping Quality
Leakage Rate
Transfer Score
```

**5. 最终主结果表**

论文主表可以这样设计：

| Method | Faithfulness ↑ | Coverage ↑ | Mapping ↑ | Leakage ↓ | Narrative ↑ | Understanding ↑ | Transfer ↑ | Retention ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Definition | - | - | - | - | - |  |  |  |
| Definition+Example | - | - | - | - | - |  |  |  |
| Direct Analogy |  |  |  |  |  |  |  |  |
| Vanilla Fable |  |  |  |  |  |  |  |  |
| Ours |  |  |  |  |  |  |  |  |

补充表：

| Variant | Coverage ↑ | Mapping ↑ | Contradiction ↓ | Leakage ↓ | Template ↓ |
|---|---:|---:|---:|---:|---:|
| w/o RAG |  |  |  |  |  |
| w/o Structure |  |  |  |  |  |
| w/o Planning |  |  |  |  |  |
| w/o Revision |  |  |  |  |  |
| Full |  |  |  |  |  |

**6. 推荐最终采用的核心指标**

如果只能保留最核心的一套，我建议是：

```text
Automatic:
- Concept Coverage
- Contradiction Rate
- Hard/Soft Leakage Rate
- Mapping Consistency
- Template Rate

Human Expert:
- Concept Faithfulness
- Analogical Mapping Quality
- Narrative Quality
- Pedagogical Usefulness

Human Learning:
- Understanding Score
- Transfer Score
- Retention Score
- Misconception Rate
```

**一句话版本**

适合 AAAI 的评估标准应该证明三件事：

> 生成的寓言 **忠实于概念**，通过 **结构化类比映射** 隐性表达概念，并且比普通解释更能提升学习者的 **理解、迁移和记忆**。