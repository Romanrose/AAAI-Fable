# M2NA 研究规划：完整思路与实验设计

## 一、研究定位

### 1.1 一句话定位

> 本文研究的不是"让模型写寓言"，而是"让模型在隐藏目标概念术语的条件下，将抽象概念的机制图转写为一个结构可对齐的短叙事类比"。

### 1.2 论文标题候选

- 主推：**M2NA: Mechanism-to-Narrative Analogy Generation for Implicit Concept Explanation**
- 备选：**Implicit Narrative Analogy Generation for Mechanism-Centric Concept Explanation**
- 偏 Benchmark：**ConceptFableBench: Evaluating Mechanism-Preserving Implicit Narrative Analogy Generation**

### 1.3 核心研究问题

> Can language models generate implicit narrative analogies that preserve the mechanism of an abstract concept without directly naming or explaining it?

中文：语言模型能否在不直接命名或解释概念的情况下，生成一段能够保持抽象概念机制结构的隐性叙事类比？

### 1.4 为什么这个问题重要

1. 人类学习抽象概念时依赖类比和故事，但 LLM 默认输出定义式解释
2. 现有工作分别覆盖类比生成、故事生成、概念解释，但没有覆盖三者交叉
3. 隐性叙事类比要求模型同时做到"结构保真 + 词汇隐藏 + 映射可验证"，这是一个可形式化的 NLP 挑战

---

## 二、任务形式化定义

### 2.1 任务名称

**Mechanism-to-Narrative Analogy Generation (M2NA)**

### 2.2 输入输出

```text
Input:
  c: target concept (目标概念)
  G_c = (V_c, E_c): mechanism graph (机制图)
    V_c: 关键要素节点（状态、角色、条件、过程、结果）
    E_c: 要素间关系（因果、时间、对比、强化、抑制、转化）
  T_c: forbidden lexical set (禁用词集合)

Output:
  N: implicit narrative analogy (隐性叙事类比)
  A: alignment V_c ∪ E_c → V_n ∪ E_n (结构映射)
```

### 2.3 示例

**路径依赖 (Path Dependence)**

机制图：
```json
{
  "concept": "path dependence",
  "nodes": ["initial choice", "reinforcing feedback", "switching cost", "lock-in", "persistence of suboptimal outcome"],
  "edges": [
    ["initial choice", "reinforcing feedback", "enables"],
    ["reinforcing feedback", "switching cost", "increases"],
    ["switching cost", "lock-in", "causes"],
    ["lock-in", "persistence of suboptimal outcome", "leads_to"]
  ]
}
```

禁用词：`path dependence, lock-in, switching cost, positive feedback, historical contingency`

期望输出叙事：一个小餐馆买了一台特殊灶台 → 菜谱和厨师技能围绕它形成 → 顾客冲着这些菜来 → 换灶台意味着重新培训+改菜单+流失顾客 → 即使有更好的灶台也无法更换

映射：
```json
[
  {"concept_element": "initial choice", "narrative_element": "餐馆最初买了一台稀有灶台"},
  {"concept_element": "reinforcing feedback", "narrative_element": "菜谱和工人习惯围绕灶台形成"},
  {"concept_element": "switching cost", "narrative_element": "换灶台需要重新培训和重新设计菜单"},
  {"concept_element": "lock-in", "narrative_element": "即使有更好的设备也无法更换"}
]
```

### 2.4 成功判定四条件

| 条件 | 含义 | 失败示例 |
|---|---|---|
| **Mechanism Preservation** | 叙事覆盖机制图关键节点和边 | 只写"做了选择后来后悔"，缺少反馈强化和转换成本 |
| **Lexical Concealment** | 正文不泄露概念名和领域术语 | 出现"路径依赖""锁定效应" |
| **Analogical Alignability** | 叙事元素可明确映射回机制节点 | 故事好看但说不清哪个情节对应哪个机制 |
| **Narrative Minimality** | 简洁具体，不堆砌无关情节 | 复杂世界观、多线并行、文学化描写 |

---

## 三、方法设计

### 3.1 方法名称

**StructNarr: Structure-Aware Narrative Analogy Generation**

（备选：KG-Fable / M2NA-Gen）

### 3.2 整体流程

```text
┌─────────────────────────────────────────────────────┐
│  Stage 1: Concept Structure Extraction              │
│  Input: concept knowledge K                         │
│  Output: mechanism graph G_c + forbidden set T_c    │
├─────────────────────────────────────────────────────┤
│  Stage 2: Source Domain Selection                   │
│  Input: G_c                                         │
│  Output: concrete source domain + character sketch  │
├─────────────────────────────────────────────────────┤
│  Stage 3: Analogical Alignment Planning             │
│  Input: G_c + source domain                         │
│  Output: planned mapping A_plan                     │
├─────────────────────────────────────────────────────┤
│  Stage 4: Constrained Narrative Generation          │
│  Input: A_plan + T_c + constraints                  │
│  Output: draft narrative N_0                        │
├─────────────────────────────────────────────────────┤
│  Stage 5: Self-Revision                             │
│  Input: N_0, G_c, T_c                              │
│  Output: final narrative N + alignment A            │
│  Checks: leakage / faithfulness / coverage /        │
│          mapping / template                         │
└─────────────────────────────────────────────────────┘
```

### 3.3 各阶段详细设计

#### Stage 1: Concept Structure Extraction

- 输入：Wikipedia/教材/论文中的概念描述
- 用 LLM 抽取为结构化表示：
  ```text
  definition, key_elements, causal_mechanism, examples, counterexamples
  ```
- 同时生成禁用词集 T_c（概念名 + 同义词 + 高泄露术语）

#### Stage 2: Source Domain Selection

- 为机制结构寻找日常化、非模板化的具体源域
- 约束：避免高频寓言意象（河流、镜子、钟、村庄、智者）
- 输出：源域描述 + 核心角色 + 基本设定

#### Stage 3: Analogical Alignment Planning

- 将 G_c 中每个节点/边 对应到 源域中的具体叙事元素
- 输出 planned mapping 表

#### Stage 4: Constrained Narrative Generation

- 约束条件：
  - 不出现 T_c 中任何词
  - 篇幅限制（150-300 词）
  - 角色数量有限（≤3）
  - 情节承载意义，不直接说教
  - 避免模板化结构

#### Stage 5: Self-Revision

- 五项检查：
  1. Leakage check：是否泄露概念名或术语？
  2. Faithfulness check：是否与概念知识冲突？
  3. Coverage check：是否覆盖关键机制节点？
  4. Mapping check：映射是否真实存在且合理？
  5. Template check：是否使用黑名单意象/套路？
- 不通过则修改重生成

### 3.4 与 Prompt Engineering 的区别

本方法的核心贡献不是 prompt design，而是：
1. 将任务形式化为 graph-to-implicit-narrative 的结构保持生成
2. 显式的 alignment planning 中间表示
3. 可量化的多维约束（覆盖、隐藏、映射）
4. 消融可验证：每个 stage 的贡献可以独立测试

---

## 四、数据集设计：ConceptFableBench

### 4.1 数据集定位

> ConceptFableBench evaluates whether language models can transform abstract concept mechanisms into faithful, implicit, and structurally alignable narrative analogies.

### 4.2 样本结构

```json
{
  "id": "pd_001",
  "concept": "path dependence",
  "domain": "economics",
  "difficulty": "intermediate",
  "source_knowledge": [...],
  "mechanism_graph": {
    "nodes": [...],
    "edges": [...]
  },
  "forbidden_terms": [...],
  "narrative": "...",
  "alignment": [...],
  "understanding_question": "...",
  "transfer_question": "...",
  "quality_labels": {
    "mechanism_preservation": 5,
    "lexical_concealment": 5,
    "analogical_alignability": 4,
    "narrative_minimality": 4
  }
}
```

### 4.3 概念领域覆盖

| 领域 | 示例概念 | 数量目标 |
|---|---|---:|
| 认知心理学 | cognitive dissonance, confirmation bias, framing effect, anchoring | 60-80 |
| 经济学 | opportunity cost, path dependence, sunk cost fallacy, moral hazard | 60-80 |
| 社会学 | social capital, role conflict, norm internalization, groupthink | 40-60 |
| 文学/传播 | defamiliarization, agenda setting, narrative framing | 30-40 |
| AI/计算机 | overfitting, gradient descent, emergence, alignment | 40-60 |
| 哲学/逻辑 | falsifiability, induction problem, reductionism | 30-40 |
| **合计** | | **260-360** |

### 4.4 数据构建流程

```text
Step 1: 概念池构建
  - 来源：Wikipedia、OpenStax、课程 glossary、教材索引
  - 筛选标准：必须有可抽取的多步机制结构（≥3 节点）
  - 目标：300+ concepts

Step 2: 机制图标注
  - LLM 初始抽取 + 人工校验
  - 每个概念产出 G_c 和 T_c

Step 3: 叙事生成
  - 用 StructNarr 方法生成候选叙事
  - 每个概念生成 3-5 个候选

Step 4: 人工筛选与标注
  - 3 位标注者评分
  - 选最佳 1-2 个进入 gold set
  - 标注 alignment 和 quality labels

Step 5: 理解/迁移题编写
  - 每个概念 2 道理解题 + 1 道迁移题
```

### 4.5 规模

| 子集 | 数量 | 用途 |
|---|---:|---|
| Concept Pool | 300+ concepts | 全部概念 |
| Mechanism Graphs | 300+ | 评测输入 |
| Generated Narratives | 1,500-3,000 | 自动评估/分析 |
| Human-verified Gold | 300-500 | 主评测集 |
| Expert-written Reference | 50-100 | 高质量参考 |
| Learning Evaluation Subset | 30-50 concepts | 小规模人类理解验证 |

---

## 五、评估设计：CF-Eval

### 5.1 三层评估架构

```text
Layer 1: Automatic Evaluation (全量，可复现)
Layer 2: Expert Human Evaluation (抽样，建立可信度)
Layer 3: Human Understanding Verification (小规模，辅助证据)
```

### 5.2 Layer 1: 自动评估

| 维度 | 指标 | 计算方式 |
|---|---|---|
| Mechanism Preservation | **Concept Coverage ↑** | Σ element_score / (2m), each element 0/1/2 |
| Mechanism Preservation | **Contradiction Rate ↓** | #contradicted / #all |
| Lexical Concealment | **Hard Leakage Rate ↓** | #fables containing concept name / #all |
| Lexical Concealment | **Soft Leakage Rate ↓** | #fables containing key terms / #all |
| Analogical Alignability | **Mapping Consistency ↑** | avg(Existence, Correctness, Specificity, Non-spuriousness) |
| Narrative Minimality | **Length Compliance** | 是否在目标词数范围内 |
| Diversity | **Template Rate ↓** | 黑名单意象/套路出现比例 |
| Diversity | **Self-BLEU ↓** | 生成之间的相似度 |

**评估执行方式：**
- Leakage：keyword matching + LLM judge
- Coverage & Contradiction：LLM judge (GPT-4 / Claude) with rubric
- Mapping Consistency：LLM judge 逐条验证

### 5.3 Layer 2: 专家评估

每个样本 3 位标注者，1-5 Likert 评分：

| 维度 | 标注问题 |
|---|---|
| Mechanism Faithfulness | 这段叙事是否准确表达了目标概念的核心机制？ |
| Analogical Mapping Quality | 叙事元素与机制结构之间的映射是否清楚、合理？ |
| Lexical Concealment | 叙事是否成功避免暴露概念名或领域术语？ |
| Narrative Quality | 叙事是否连贯、简洁、有因果推进？ |
| Novelty | 叙事是否避免模板化、老套的意象？ |

报告：
- 各维度均值 + 标准差
- Fleiss' κ / Krippendorff's α (inter-annotator agreement)
- 自动指标与人工评分的 Pearson/Spearman 相关

### 5.4 Layer 3: 人类理解验证（辅助，非主贡献）

注意：收窄版论文不以人类学习实验为主贡献，但做小规模验证增强说服力。

**设计：**
- 30-50 个概念
- 每个概念，被试阅读一种形式后回答理解/迁移题
- 4 组对照：

```text
A. Definition-only（只看定义）
B. Direct Analogy（显式类比解释）
C. Vanilla LLM Narrative（普通 LLM 故事）
D. Ours: M2NA output（隐性叙事类比）
```

**测试题：**
1. 请用自己的话解释这个概念的核心机制
2. 这个概念成立需要哪些关键条件？
3. 请在另一个领域举例，说明为什么它符合该概念

**评分 rubric (0-4)：**
```text
0 = 无关或错误
1 = 只复述表面词
2 = 理解部分要素
3 = 准确理解核心机制
4 = 准确理解并能说明边界/反例
```

---

## 六、实验设计

### 6.1 主实验：方法对比

| Method | 说明 |
|---|---|
| Direct Explanation | G_c → 直白文字解释 |
| Direct Analogy | concept + definition → 显式类比 |
| Vanilla Narrative | concept + definition → 普通短故事 |
| Analogical Prompting | 先自生成类似案例再写故事 (ICLR 2024) |
| Plan-then-Write | 先生成 narrative plan 再写 |
| **StructNarr (Ours)** | 完整五阶段方法 |

**测试模型：**
- GPT-4o
- Claude 3.5 Sonnet
- DeepSeek-V3
- Llama 3.1 70B (开源代表)

**主结果表：**

| Method | Coverage ↑ | Mapping ↑ | Hard Leak ↓ | Soft Leak ↓ | Template ↓ | Narrative ↑ |
|---|---|---|---|---|---|---|
| Direct Explanation | - | - | - | - | - | - |
| Direct Analogy | | | | | | |
| Vanilla Narrative | | | | | | |
| Analogical Prompting | | | | | | |
| Plan-then-Write | | | | | | |
| **StructNarr** | | | | | | |

### 6.2 消融实验

| Variant | 检验什么 |
|---|---|
| w/o Mechanism Graph | 输入机制图 vs 只输入定义 → 覆盖率变化 |
| w/o Forbidden Set | 有无禁用词约束 → 泄露率变化 |
| w/o Alignment Planning | 有无显式映射规划 → 映射质量变化 |
| w/o Source Domain Selection | 有无源域选择 → 模板率/多样性变化 |
| w/o Self-Revision | 有无自检修改 → 泄露+覆盖+矛盾变化 |
| Full StructNarr | 完整方法 |

**消融结果表：**

| Variant | Coverage ↑ | Mapping ↑ | Leakage ↓ | Contradiction ↓ | Template ↓ |
|---|---|---|---|---|---|
| w/o Mechanism Graph | | | | | |
| w/o Forbidden Set | | | | | |
| w/o Alignment Planning | | | | | |
| w/o Source Domain Selection | | | | | |
| w/o Self-Revision | | | | | |
| Full | | | | | |

### 6.3 分析实验

1. **按概念难度分析**：easy / intermediate / hard 概念的各指标分布
2. **按领域分析**：不同领域（心理学/经济学/CS...）的生成质量差异
3. **机制图复杂度影响**：节点数/边数与覆盖率的关系
4. **LLM judge 可靠性**：自动指标 vs 人工评分的相关性分析
5. **Case Study**：3-5 个典型 good/bad case 详细分析

### 6.4 人类理解验证实验

- 被试：30-50 人（大学生/研究生）
- 概念数：30-50 个
- 设计：between-subject per concept, within-subject across concepts
- 报告：Understanding Score, Transfer Score, Misconception Rate
- 统计检验：paired t-test / Wilcoxon signed-rank

---

## 七、论文结构

```text
1. Introduction (1.5 pages)
   - 动机：LLM 解释概念 = 定义式，人类学习依赖类比和故事
   - Gap：没有任务/数据集/评估研究"机制→隐性叙事类比"
   - 贡献列表

2. Related Work (1 page)
   - Analogical Reasoning and Analogy Generation
   - Narrative Analogies and Story-Level Analogy
   - Educational Analogies for Concept Understanding
   - Structure-to-Text Generation

3. Task Definition (1 page)
   - M2NA 形式化定义
   - 四条成功条件
   - 与相邻任务的区别

4. ConceptFableBench (1.5 pages)
   - 数据集设计与构建流程
   - 统计信息
   - 与已有数据集的对比

5. Method: StructNarr (1.5 pages)
   - 五阶段流程
   - 各阶段 prompt/策略
   - 与 baseline 的区别

6. Evaluation Protocol: CF-Eval (1 page)
   - 自动评估指标
   - 人工评估设计
   - 人类理解验证设计

7. Experiments (2 pages)
   - 主实验结果
   - 消融实验
   - 分析实验
   - 人类理解验证

8. Conclusion (0.5 pages)
```

---

## 八、Contributions 定稿

```text
1. We formulate Mechanism-to-Narrative Analogy Generation (M2NA), a new task 
   requiring models to convert abstract concept mechanisms into implicit, 
   structurally alignable narrative analogies under lexical concealment constraints.

2. We construct ConceptFableBench, a benchmark containing mechanism graphs, 
   forbidden term sets, implicit narratives, structural alignments, and quality 
   annotations across 300+ concepts from 6 domains.

3. We propose StructNarr, a structure-aware generation framework that plans 
   mechanism-to-narrative alignments before generating constrained narratives, 
   with self-revision for faithfulness, leakage, and mapping verification.

4. We design CF-Eval, a multi-level evaluation protocol covering automatic 
   metrics for mechanism preservation and lexical concealment, expert judgments 
   for mapping quality, and human understanding verification.
```

---

## 九、Related Work 定位 (Gap Statement)

> Recent work has studied analogy generation (ANALOGYKB, ACL 2024), narrative analogy recognition (ARN, TACL 2024; ParallelPARC, NAACL 2024), educational analogies (Boosting Scientific Concepts, EMNLP 2024), and graph-to-text generation (PlanGTG, NAACL 2025). However, none addresses whether language models can transform an abstract concept mechanism into a lexically concealed narrative analogy with explicit structure-level alignment. M2NA fills this gap.

---

## 十、风险与应对

| 风险 | 应对策略 |
|---|---|
| 被认为是 prompt engineering | 强调形式化任务定义、中间表示、消融实验、数据集构建 |
| LLM judge 不可靠 | 报告自动-人工相关性；主结论基于人工评估 |
| 隐性叙事不一定比显式类比好 | 不声称全面优于，强调 M2NA 是独立任务；人类验证只作辅助 |
| 概念难度不公平 | 分层采样，按难度/领域报告 |
| 数据集规模质疑 | LLM generation + human verification，报告 agreement |
| 审稿人问"为什么不做完整人类学习实验" | 明确定位为第一篇任务定义论文，人类学习实验留 future work |

---

## 十一、执行时间线（建议）

| 阶段 | 任务 | 时间 |
|---|---|---:|
| Phase 1 | 概念池构建 + 机制图标注（pilot 50 个） | 1-2 周 |
| Phase 2 | 方法实现 + pilot 生成验证 | 1-2 周 |
| Phase 3 | 全量概念池 + 机制图（300+） | 2-3 周 |
| Phase 4 | 全量生成 + baseline 实验 | 2-3 周 |
| Phase 5 | 人工评估标注 | 2-3 周 |
| Phase 6 | 人类理解验证实验 | 1-2 周 |
| Phase 7 | 论文写作 | 2-3 周 |
| **合计** | | **11-18 周** |

---

## 十二、关键决策点

开始实验前需要确认：

1. **概念粒度**：机制图节点数目标 3-7，边数 2-6？
2. **叙事长度**：目标 150-300 词 (English) 还是更短？
3. **LLM judge 模型选择**：用哪个模型做自动评估？需验证其与人工评分的一致性
4. **人类验证规模**：最少做多少概念/多少被试？
5. **是否中英双语**：数据集是否做英文为主 + 中文子集？
6. **Benchmark 开源策略**：是否 submission 时开源？

---

## 十三、与现有工作的关键区别总结

| 维度 | 现有工作 | M2NA |
|---|---|---|
| 输入 | 概念名/定义 | 结构化机制图 G_c |
| 输出 | 显式类比/故事 | 隐性叙事 + 结构映射 |
| 约束 | 无词汇限制 | 禁用词集 T_c |
| 评估 | fluency/coherence | 机制覆盖+泄露率+映射一致性 |
| 目标 | 故事好看/类比恰当 | 机制保持+词汇隐藏+可对齐 |
| 与教育的关系 | 直接教学 | 隐性推理（读者自己悟） |
