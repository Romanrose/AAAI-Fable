# M2NA 核心论文包与阶段性调研

整理日期：2026-06-18

本目录收录 8 篇与 **Mechanism-to-Narrative Analogy Generation (M2NA)** 直接相关的论文。选择标准不是泛泛涉及“故事”或“类比”，而是至少覆盖以下一项：

- 叙事级结构类比；
- 复杂类比数据构建；
- 机制图到文本的规划与忠实生成；
- 类比对概念理解的作用；
- 隐性类比元素和结构映射；
- LLM 叙事质量与结构缺陷。

## 1. 论文索引

| 文件 | 论文 | 方向 | 对 M2NA 的直接价值 |
|---|---|---|---|
| [`01-ARN-TACL-2024.pdf`](01-ARN-TACL-2024.pdf) | ARN: Analogical Reasoning on Narratives | 叙事类比识别 | 提供 surface / relational / system mapping 框架，以及 near / far analogy 划分 |
| [`02-ParallelPARC-NAACL-2024.pdf`](02-ParallelPARC-NAACL-2024.pdf) | ParallelPARC | 类比数据构建 | 提供 LLM 自动生成、人工验证 gold set、自动 silver set 和 hard distractor 的构建范式 |
| [`03-Scientific-Concept-Analogy-EMNLP-2024.pdf`](03-Scientific-Concept-Analogy-EMNLP-2024.pdf) | Boosting Scientific Concepts Understanding | 教育类比 | 证明自由形式类比能够帮助模型理解科学概念，可支撑任务动机和下游效用实验 |
| [`04-Graph-to-Text-NAACL-2025.pdf`](04-Graph-to-Text-NAACL-2025.pdf) | Evaluating and Improving Graph to Text Generation with LLMs | 图到文本 | 说明复杂图上的规划是核心瓶颈，并提供 reordering、attribution 和 PlanGTG 思路 |
| [`05-Human-Level-Narratives-EMNLP-2024.pdf`](05-Human-Level-Narratives-EMNLP-2024.pdf) | Are LLMs Capable of Generating Human-Level Narratives? | 叙事生成 | 提供 story arc、turning point、arousal、valence 等叙事结构指标 |
| [`06-Historical-Analogy-ACL-2025.pdf`](06-Historical-Analogy-ACL-2025.pdf) | Past Meets Present | 类比生成 | 提供 retrieval / generation 对照和 self-reflection 降低幻觉、偏见的方法 |
| [`07-Metaphoric-Analogy-COLING-2025.pdf`](07-Metaphoric-Analogy-COLING-2025.pdf) | Automatic Extraction of Metaphoric Analogies | 隐性映射 | 直接研究从文本中抽取结构化类比映射，以及补全隐含类比元素 |
| [`08-Curious-Case-Analogies-AAAI-2026.pdf`](08-Curious-Case-Analogies-AAAI-2026.pdf) | The Curious Case of Analogies | 类比推理机制 | 说明成功类比依赖强结构对齐，失败常来自关系信息缺失或错误迁移 |

完整引用见 [`references.bib`](references.bib)。

## 2. 最重要的调研结论

### 2.1 M2NA 应被定义为结构迁移任务

ARN 和 AAAI 2026 的研究都表明，类比成功的关键不是实体或主题相似，而是关系系统能否正确对齐。M2NA 因此不应只检查故事是否“表达了同一个意思”，而应显式比较：

```text
概念节点 -> 叙事实体、状态或事件
概念关系 -> 叙事中的因果、时序、强化、抑制或转化关系
```

建议把节点覆盖与边覆盖分开报告。只覆盖概念关键词但遗漏因果边，不应算机制保持成功。

### 2.2 远域类比是核心难点，也是主要研究价值

ARN 发现模型对近域类比较容易，但对跨领域的 far analogy 明显困难。M2NA 需要把抽象概念放入新的具体故事域，本质上属于远域结构迁移。

因此，数据集应给每个概念标注：

```text
source_domain
target_domain
domain_distance
surface_overlap
structural_overlap
```

并分别报告 near / far、低表面重合 / 高表面重合条件下的结果，避免模型依赖词面捷径。

### 2.3 “先规划、后生成”不是可选模块

Graph-to-Text 工作显示，LLM 在三元组数量增加时容易出现规划错误；仅调整 prompt 或 few-shot 示例，提升通常有限。M2NA 比普通 graph-to-text 更难，因为它不能直接复述图谱，还要完成跨域转换和词汇隐藏。

推荐主流程：

```text
mechanism graph
  -> graph ordering / causal chain extraction
  -> source-domain selection
  -> node-and-edge alignment plan
  -> narrative realization
  -> alignment verification
```

主方法至少需要输出中间 alignment plan，否则论文容易退化为 prompt engineering。

### 2.4 数据集应采用 gold、silver 与 hard negative 三层结构

ParallelPARC 的数据构建范式适合直接迁移：

- **Gold set**：人工验证机制图、叙事和结构对齐，用于最终测试。
- **Silver set**：LLM 生成并通过规则与模型筛选，用于训练或开发。
- **Hard negatives**：主题相似但机制不同，或覆盖相同节点但关系错误的故事。

对 M2NA 而言，hard negative 尤其重要。否则评估器可能只凭主题词判断故事和概念是否匹配。

建议至少构造三类负例：

1. **Surface distractor**：词面和主题相似，但核心关系不同。
2. **Relation corruption**：保留节点，交换因果方向或时序。
3. **Mechanism omission**：故事合理，但遗漏关键机制阶段。

### 2.5 自我修订应检查结构，不只是语言

Historical Analogy 工作表明 self-reflection 能改善类比生成中的幻觉和刻板印象。M2NA 的 revision 模块可以拆成：

```text
Coverage check: 是否覆盖关键节点和边？
Leakage check: 是否出现概念名、同义词或高泄露术语？
Alignment check: 映射的叙事元素是否真实存在？
Causal check: 因果方向和时序是否保持？
Narrative check: 是否存在冲突、转折和冗余情节？
```

相比笼统要求“请改进故事”，逐项检查更容易做消融和错误分析。

### 2.6 叙事质量需要独立评价

EMNLP 2024 的研究发现，LLM 故事往往结构同质、整体偏正向、缺乏张力。即使机制映射正确，也可能不是合格短叙事。

M2NA 的叙事指标建议保留：

- 情节连贯性；
- 明确的状态变化或转折；
- 冲突是否服务于机制表达；
- 无关角色和事件数量；
- 模板化率；
- 故事长度与机制复杂度的匹配程度。

但不能让叙事质量掩盖结构错误。主指标应优先是机制保持和结构对齐。

## 3. 推荐任务定义

```text
Input:
  c: target concept
  G_c = (V_c, E_c): mechanism graph
  T_c: forbidden lexical set
  R: optional narrative constraints

Output:
  N: lexically concealed narrative analogy
  A_V: node-level alignment
  A_E: relation-level alignment
```

其中：

```text
A_V: V_c -> narrative entities / states / events
A_E: E_c -> narrative causal / temporal / relational links
```

相比当前只写一个统一映射 `A`，拆成 `A_V` 和 `A_E` 更便于构建数据、计算覆盖率和定位错误。

## 4. 推荐 baseline

| Baseline | 输入与过程 | 检验点 |
|---|---|---|
| Direct Narrative | 概念定义直接生成故事 | 最弱生成基线 |
| Graph-to-Text | 机制图直接转解释文本 | 图结构能否被忠实表达 |
| Direct Analogy | 生成显式类比，不隐藏术语 | 隐性叙事约束带来的难度 |
| Plan-and-Write | 先生成普通故事计划，再写正文 | 一般叙事规划是否足够 |
| Alignment-then-Write | 先输出节点映射，再生成 | 节点对齐规划的作用 |
| Full M2NA | 节点与边对齐、禁词、修订 | 完整方法 |

关键消融：

```text
w/o edge alignment
w/o forbidden lexical set
w/o source-domain selection
w/o hard-negative training
w/o structural self-revision
```

## 5. 推荐评测

### 结构正确性

- Node Coverage
- Edge Coverage
- Relation Direction Accuracy
- Alignment Precision
- Alignment Hallucination Rate

### 隐性表达

- Exact Concept Leakage
- Soft Terminology Leakage
- Target Identifiability

`Target Identifiability` 需要谨慎解释：完全无法识别可能意味着机制没有保留；一眼识别则可能说明泄露过强。可把它设计成候选概念检索或多选实验，并同时观察结构指标。

### 叙事质量

- Coherence
- Turning-point Presence
- Narrative Minimality
- Template Rate
- Human Preference

### 评估可靠性

- 人类标注者一致性；
- 自动指标与人工评分的相关性；
- LLM judge 在 hard negatives 上的区分能力；
- 对节点扰动、边扰动和词面扰动的敏感性。

## 6. 建议优先阅读顺序

1. ARN：先确定叙事类比中的结构映射概念。
2. Graph-to-Text：明确机制图规划和忠实生成的技术难点。
3. ParallelPARC：确定数据集、gold/silver 和 hard negative 设计。
4. Metaphoric Analogy：确定隐性元素和结构化映射标注方式。
5. Curious Case of Analogies：补充结构对齐的模型机制依据。
6. Human-Level Narratives：设计叙事质量指标。
7. Historical Analogy：设计 retrieval、generation 和 self-reflection。
8. Scientific Concept Analogy：支撑教育价值和下游效用实验。

## 7. 当前最小可行实验

建议先做 20–50 个机制型概念，每个概念人工整理 4–8 个节点和 3–7 条关系。

每个概念生成：

- 1 个人工验证叙事；
- 3 个模型候选叙事；
- 1 个 surface distractor；
- 1 个 relation-corruption negative；
- 1 个 mechanism-omission negative。

第一轮只比较：

```text
Direct Narrative
Alignment-then-Write
Full M2NA with structural revision
```

如果节点/边覆盖、泄露率和人工对齐质量能形成稳定差异，再扩大数据规模。这样可以先验证问题是否成立，避免在任务定义未稳定前投入大规模数据构建。

## 8. 官方页面

- [ARN, TACL 2024](https://aclanthology.org/2024.tacl-1.59/)
- [ParallelPARC, NAACL 2024](https://aclanthology.org/2024.naacl-long.329/)
- [Boosting Scientific Concepts Understanding, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.346/)
- [Graph-to-Text with LLMs, NAACL 2025](https://aclanthology.org/2025.naacl-long.513/)
- [Human-Level Narratives, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.978/)
- [Past Meets Present, ACL 2025](https://aclanthology.org/2025.acl-long.200/)
- [Metaphoric Analogies, COLING 2025](https://aclanthology.org/2025.coling-main.448/)
- [The Curious Case of Analogies, AAAI 2026](https://ojs.aaai.org/index.php/AAAI/article/view/40414)

