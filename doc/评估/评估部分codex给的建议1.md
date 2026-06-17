
介绍一下我该如何设置评估



评估建议分成两层：**文本本身是否合格**，以及 **它是否真的帮助人学习**。前者可以自动评估 + 专家评估，后者最好做人类实验。AAAI 里真正能打的是第二层，但第一层必须先站住。

**一、评估目标**

你的任务不是普通故事生成，所以不能只评 fluency、coherence。核心要回答四个问题：

1. 寓言是否忠实表达了原概念？
2. 寓言是否足够“隐含”，没有直接泄题？
3. 故事元素和概念结构之间是否存在清晰映射？
4. 读者看完后是否更理解、更记得、能迁移？

可以把评估维度定义成：

`Concept Faithfulness Implicitness Analogical Mapping Quality Narrative Quality Pedagogical Effectiveness Diversity / Anti-template`

**二、自动评估**

自动评估用于大规模筛选，不作为最终唯一结论。

**1. Concept Faithfulness**

检查寓言是否覆盖概念结构中的关键要素。

比如“路径依赖”的结构是：

`initial choice positive feedback switching cost lock-in suboptimal persistence`

让 LLM judge 判断故事是否表达了这些要素，每个要素打 0/1/2 分：

`0 = 未体现 1 = 弱体现 2 = 清楚体现`

最终得到：

`Faithfulness = covered_key_elements / total_key_elements`

**2. Implicitness**

检查寓言正文是否泄露概念名或术语。

可以分两类：

- **Hard leakage**：直接出现概念名，例如“路径依赖”“认知失调”。
- **Soft leakage**：出现明显术语，例如“转换成本”“正反馈”“锁定效应”。

自动做法：

`term matching + LLM judge`

指标：

`Leakage Rate = 泄露样本数 / 总样本数`

越低越好。

**3. Mapping Quality**

输入：

`concept structure fable model-generated mapping`

让评估器判断每个 mapping 是否成立：

`story_element 是否真实存在？ concept_element 是否对应正确？ 两者关系是否清楚？`

可打 1-5 分。

这项很关键，因为它证明模型不是随便写了个故事，而是真的构造了类比。

**4. Narrative Quality**

人工或 LLM 评估：

`coherence: 情节是否连贯 conciseness: 是否简洁 conflict: 是否有核心冲突/转折 show-not-tell: 是否通过情节表达，而不是角色说教 readability: 是否容易读`

每项 1-5 分。

**5. Diversity / Anti-template**

这个可以做自动指标：

- distinct-n / self-BLEU：衡量文本多样性
- 高频意象统计：河流、镜子、钟、村庄、智者等模板词出现率
- embedding clustering：看故事是否集中在少数模板

你可以定义：

`Template Rate = 出现黑名单意象或结构的样本比例`

**三、人工专家评估**

建议找 3 类标注者：

1. **领域专家/研究生**：判断概念是否准确。
2. **普通学习者**：判断是否容易理解。
3. **写作/教育背景标注者**：判断故事性和教学性。

每个样本 3 人标注，使用 Likert 1-5 分。

标注维度可以这样写：

|维度|问题|
|---|---|
|忠实度|这个寓言是否准确表达了目标概念？|
|隐含性|寓言是否没有直接暴露概念名或术语？|
|映射清晰度|故事元素和概念机制是否能对应起来？|
|可读性|故事是否自然、连贯、易读？|
|教学价值|读完后是否有助于理解该概念？|
|新颖性|故事是否避免模板化、陈词滥调？|

**四、人类学习实验**

这是最重要的部分。你要证明：寓言不是“好看”，而是“有效”。

实验可以设 4 个组：

`A: Definition-only B: Definition + Example C: Direct Analogy Explanation D: Your Fable Method`

每个被试随机学习若干概念，避免某组概念本身更难。

评估三类题：

**1. Understanding Test**

看是否理解核心定义。

例子：

`请用自己的话解释“路径依赖”的核心机制。`

由人工或 rubric 打分。

**2. Transfer Test**

看能否迁移到新场景。

`请举一个不属于经济学领域的“路径依赖”例子，并解释为什么它符合这个概念。`

这是最能体现寓言价值的指标。

**3. Retention Test**

隔 24 小时或 1 周后再测：

`你还记得这个概念的核心意思吗？ 请写出一个例子。`

如果时间紧，至少做 24 小时延迟测试。

**五、推荐主实验指标**

你论文里可以主打这些：

`Faithfulness Score Implicitness Score Mapping Quality Score Narrative Quality Score Understanding Gain Transfer Accuracy Retention Score`

其中前三个证明生成质量，后三个证明教育效果。

**六、Baseline 设置**

建议至少比较：

1. **Definition-only**
2. **Definition + Example**
3. **Vanilla LLM Fable**
4. **RAG-only Fable**
5. **RAG + Structured Planning，也就是你的方法**

如果你还想更强，可以加：

`Direct Analogy Explanation`

这个 baseline 很重要，因为审稿人会问：为什么非要寓言？普通类比不行吗？

**七、最推荐的评估表述**

你可以把评估分成：

`Intrinsic Evaluation: 评估生成文本是否忠实、隐含、有映射、有故事质量。 Extrinsic Evaluation: 评估生成文本是否提升人类学习者的理解、迁移和记忆。`

这套说法很学术，也很好写进论文。

一句话总结：**自动评估负责规模，专家评估负责可信度，人类学习实验负责论文说服力。**

20:12

有没有类似的文章

20:12

已处理 10s

有，而且能分成三类。**但我目前没看到和你完全一样的“抽象概念 → 隐性寓言 → 概念映射 → 学习效果评估”的论文**。最像的是“类比教学”和“故事级类比”，不是“寓言生成”。

**1. 最接近你的：LLM 用类比教概念**

这篇最该重点看：

[Can LLMs Teach Human Learners to Understand Concepts Through Analogies?](https://proceedings.mlr.press/v273/ye25a.html)

它的问题是：LLM 能不能通过类比帮助学生理解复杂概念。它设计了两阶段框架：先让 LLM tutor 生成类比，再让学习者看类比并做选择题测试理解。初步结果显示 analogy-based tutoring 能提升 engagement 和 conceptual mastery。

它和你的区别：

- 它做的是 **analogy tutoring**，不是寓言。
- 它的类比一般更直接，你想做的是 **隐性叙事类比**。
- 它没有强调 RAG、概念结构抽取、寓言风格控制、故事-概念映射标注。

所以你的论文可以说：已有工作证明类比对概念学习有用，但还没有系统研究 **narrative fables as implicit analogical explanations**。

**2. 类比生成相关**

这篇是 NLP 里很直接的前作：

[Analogy Generation by Prompting Large Language Models](https://aclanthology.org/2022.inlg-main.25/)

它研究如何用 InstructGPT 生成类比，任务是给定目标概念，生成 source concept analogy。它证明 LLM 可以做 analogy generation，但也暴露出质量和评估问题。

和你的区别：

- 它生成的是“类比解释”，不是“完整寓言故事”。
- 它没有面向教学效果做人类学习实验。
- 它没有要求隐含表达，也不需要读者通过故事自己悟出概念。

还有这篇：

[![](https://arxiv.org/favicon.ico)Scientific and Creative Analogies in Pretrained Language Models](https://arxiv.org/abs/2211.15268)

它提出 SCAN 数据集，关注跨域类比中的多属性、多关系映射。它很适合作为你的理论支撑，因为你的寓言本质上也是一种跨域结构映射。

你的差异：

- SCAN 偏类比理解/识别。
- 你做的是 **类比生成 + 叙事生成 + 教学评估**。

**3. 故事级类比相关**

这篇非常重要：

[StoryAnalogy: Deriving Story-level Analogies from Large Language Models to Unlock Analogical Understanding](https://aclanthology.org/2023.emnlp-main.706/)

它构建了故事级类比数据，研究模型是否能理解两个故事之间的 analogical relation。论文里提到 StoryAnalogy 可提升 LLM 的 analogy generation 质量。

和你的关系很近，因为你不是句子级类比，而是故事级类比。

区别是：

- StoryAnalogy 是 **story-to-story analogy**。
- 你是 **concept-to-story analogy**。
- 它主要评估类比识别/生成能力。
- 你评估的是概念忠实度、隐含性、映射质量和学习效果。

这可以成为你最核心的 related work 对照。

**4. 寓言/道德故事生成相关**

有一篇很近但目标不同：

[![](https://huggingface.co/favicon.ico)TF1-EN-3M: Three Million Synthetic Moral Fables for Training Small, Open Language Models](https://huggingface.co/papers/2504.20605)

它构建了 300 万英文道德寓言，每个故事有结构化 scaffold，比如 character、trait、setting、conflict、resolution、moral。

和你的区别：

- 它是 **moral fable generation**，教的是道德训诫。
- 你是 **conceptual fable generation**，教的是抽象知识概念。
- 它关注大规模合成语料和小模型训练。
- 你关注知识忠实、类比映射和人类学习收益。

这篇可以帮你论证：寓言作为数据类型已经进入 NLP，但还没有被用于抽象概念学习。

**5. 教育解释/可解释推理相关**

可以参考：

[WorldTree V2](https://aclanthology.org/2020.lrec-1.671/)  
它做的是科学问答的多事实 explanation graph。

[ScienceQA](https://scienceqa.github.io/index.html)  
它包含 grounded lectures 和 detailed explanations。

它们不是寓言，但可以支撑你做“concept structure extraction”和“explanation evaluation”。你可以借鉴它们的思想：解释不是一段散文，而是由多个知识事实/推理节点组成。

**我的判断**

最像你的论文组合是：

1. **Ye & Wu 2025**：LLM analogy tutoring，证明类比教学有教育意义。
2. **Bhavya et al. 2022**：LLM analogy generation，证明类比生成是 NLP 任务。
3. **StoryAnalogy 2023**：故事级类比，证明 narrative-level analogy 可研究。
4. **TF1-EN-3M 2025**：寓言数据集，证明 fable generation 有数据集价值。
5. **WorldTree / ScienceQA**：教育解释和结构化知识支撑。

你的差异化可以这样写：

> Existing studies have explored analogy generation, story-level analogy understanding, moral fable generation, and educational explanations. However, little work has studied how to transform abstract concepts into faithful, implicit, and pedagogically useful fables through structured analogical mapping.

中文就是：

> 现有工作分别研究了类比生成、故事级类比理解、道德寓言生成和教育解释，但尚未系统研究如何把抽象概念通过结构化类比映射转化为忠实、隐含且具有教学价值的寓言。

所以这个方向不是凭空来的，有明确前作；但你的交叉点还比较新。

