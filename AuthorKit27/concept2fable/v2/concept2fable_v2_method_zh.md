# Concept2Fable v2 方法部分（中文版审阅稿）

## 方法概览

直接从 K--12 知识图谱中的 Concept 节点生成教育寓言，容易得到语言流畅但教育知识机制不完整的故事。模型可能提到与概念相关的对象，却遗漏概念成立所需的条件、过程和结果；也可能产生一个情节连贯的故事，却改变原概念中的因果方向。

Concept2Fable 将故事生成拆成三个受约束的中间步骤：先从图谱证据构建概念机制图，再通过 LLM-guided Copycat-inspired Mapping 将机制关系转化为故事结构，最后生成寓言正文并进行反向对齐。整体流程为：

```text
Concept 节点
  -> 图谱证据检索
  -> 概念机制图
  -> LLM-guided Copycat-inspired Mapping
  -> 寓言生成与对齐检查
```

这里的关键不是增加更多故事提示词，而是在语言生成之前引入一个可审核的知识机制表示。图谱负责提供课程证据，机制图负责说明概念如何成立或运作，映射计划负责规定这些关系如何进入故事。

## 1. Concept 节点初始化

我们从规范化 K--12 知识图谱中筛选标签为 `Concept` 的节点作为教育寓言的目标。章节、练习、实验和技能等非 Concept 节点不作为故事目标，但可以作为目标节点的检索上下文。

对于每个目标节点 $c$，系统构建最小的 `ConceptSeed`：

```text
S_c = {concept_id, subject, canonical_name, aliases,
       definition, concept_type, forbidden_terms}
```

`ConceptSeed` 只用于定位目标概念和定义语言约束，不保存图谱上下文、机制字段、故事设定或生成质量。`forbidden_terms` 由概念名称和别名派生，用于检查故事正文是否直接暴露目标术语。这样，概念节点的选择与后续机制构建保持分离，同一批 Concept 节点可以在不同检索和映射方法下进行公平比较。

## 2. 基于 GraphRAG 的概念机制图构建

### 2.1 受控证据检索

目标节点的局部邻域包含直接教学关系，也可能包含宽泛相关节点。若无差别地扩大邻域，检索内容会增加噪声。因此，我们采用受控自适应 2-hop GraphRAG。

第一跳以目标 Concept 节点为中心，优先保留：

```text
prerequisites_for, is_a, verifies, leads_to, relates_to
```

如果直接证据已经足以形成可解释结构，检索停止；只有在一跳为空或不足以形成可审核机制时，才从第一跳的高价值节点继续扩展。第二跳优先使用 `prerequisites_for`、`is_a`、`verifies` 和 `leads_to`，并要求路径能够回到目标概念的机制解释。

每个 RetrievalPackage 默认最多保留 8 条路径、每条路径不超过 2 跳、总边数不超过 20 条。检索包保存目标节点、原始边、选中路径、摘要以及是否触发二跳的决策。检索结果只作为机制构建的证据，不直接作为故事上下文写入正文。

### 2.2 机制抽取与审核

当前实现使用 DeepSeek Chat，将 `ConceptSeed`、目标节点属性和 RetrievalPackage 转换为类型化 `MechanismRecord`。机制节点包括：

```text
entity / condition / process / state / outcome / rule / evidence
```

机制边包括：

```text
requires / enables / transforms / causes / produces
constrains / is_a / part_of / relates_to / verifies
```

每个节点和边必须引用检索包中的课程证据，引用格式限定为：

```text
kg-node:<node-id>:<property>
kg-edge:<source-edge-id>
```

随后进行规则验证，检查节点和边的唯一性、边端点、关系类型、证据可解析性、图结构连通性以及必须保持的节点和边。对于过程、规律、机制、方法和定理等多步骤概念，机制图至少包含两个节点和一条边；定义型概念可以保留单节点结构，不强行构造因果链。验证失败的记录进入失败队列，不使用定义文本自动回填机制。验证通过后再进入人工审核，只有审核通过的机制图才能进入正式故事实验。

因此，Concept2Fable 中的概念机制图不是 Concept 定义的改写，也不是检索邻域的简单摘要，而是一个由图谱证据支持、能够被规则检查和人工审核的中间知识结构。

## 3. LLM-guided Copycat-inspired Mapping

得到概念机制图后，系统不直接要求 LLM 写寓言，而是先生成 Mapping Plan。LLM 在必须保持的机制节点、机制边和关系方向约束下选择故事源域，并将机制结构转化为故事结构：

| 概念机制 | 故事结构 |
|---|---|
| entity | 角色或物体 |
| condition | 环境条件或情境限制 |
| process | 行动序列 |
| state | 故事状态变化 |
| outcome | 结果或后果 |
| rule/constraint | 故事世界规则 |
| causal direction | 事件顺序和依赖关系 |

例如，“种子萌发”可以表示为“适宜的外界条件”和“种子自身状态”共同使萌发过程发生。映射到“煮饭”时，火候、水量和锅盖承载外界条件，米粒是否新鲜承载内部条件，米粒吸水膨胀和煮熟承载过程与结果。该映射需要保持两个 `enables` 关系的方向，而不是只寻找种子和米之间的表面相似。

LLM-guided Copycat-inspired Mapping 的输入包括 `ConceptSeed`、审核通过的 `MechanismRecord`、禁用词和生成预算，输出包括：

- 源域及其选择理由。
- 机制节点到故事载体的映射。
- 机制边到故事关系的映射。
- 事件链、冲突、转折点和结局状态。
- 必须保持的节点、边和方向标记。

Mapping Plan 在生成前被冻结，并保存输入哈希。Copycat-inspired 表示对关系保持和灵活类比思想的借鉴，不宣称复现经典 Copycat 的完整认知架构。故事中的角色和情境可以变化，但审核通过的核心机制不能被故事需要静默删除或改向。

## 4. 寓言生成与反向对齐

Generator 根据冻结的 Mapping Plan 生成中文教育寓言。寓言的角色、行动和结果应当承载概念机制，同时避免在正文中出现目标概念及其高泄漏术语。寓言的优势在于角色较少、事件链较短、行为后果较清晰，适合帮助学习者复述概念关系；但拟人化和戏剧冲突也可能引入错误因果，因此生成后必须进行结构检查。

生成结果由三个 Agent 处理：

- **Aligner** 将机制节点和边对齐到故事中的具体证据，并检查关系方向。
- **Judge** 评价概念忠实度、映射清晰度、因果连贯性、可读性、隐含性和教学价值，同时检查概念矛盾、机制遗漏和术语泄漏。
- **Reviser** 根据具体错误修订故事：机制遗漏时补充对应事件，方向错误时调整事件顺序，术语泄漏时重写表达，语言问题则进行表层修改。

最终输出包括寓言正文、机制到故事的 Alignment 和运行记录。Alignment 用于回答“哪个故事片段表达了哪个机制节点或机制边”，运行记录保存模型、提示版本、输入哈希和修订结果。任何 Planner、Generator、Aligner、Judge 或 Reviser fallback 都标记为 `invalid_for_official_eval`，不进入正式汇总。

当前正式协议固定每个 Concept 每种方法生成 3 个候选，并使用统一的生成、对齐、评估和修订预算。Standard Mapping 和 Deterministic Copycat-inspired Mapping 作为后续实验中的对比方法，不属于本文主方法定义。

## 方法边界

Concept2Fable 从 Concept 节点出发，而不是从旧版 Concept Card 出发。当前 V2 已实现 ConceptSeed、受控自适应 GraphRAG、DeepSeek 机制抽取、规则验证、人工审核接口和统一评估框架。Story Pilot12 已生成 108 条候选记录，可用于后续方法对比；Core80、Human32 和全部 6574 个 Concept 节点的规模化实验仍属于后续工作。
