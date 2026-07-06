# M2NA 人工标注规范

## 1. 标注目标

人工标注用于判断自动脚本无法可靠处理的语义问题：

1. 叙事是否保持概念机制；
2. 节点和关系映射是否正确；
3. 叙事是否在不泄露术语的情况下仍可理解；
4. 故事是否简洁、连贯并具有教学价值。

自动脚本给出的 `node_coverage` 和 `edge_coverage` 只说明生成结果声明了映射且证据字符串存在，不代表映射在语义上正确。

## 2. 标注前材料

每位标注者应获得：

- 目标概念的标准定义；
- 机制图节点和边；
- 禁用词集合；
- 生成叙事；
- 模型输出的节点映射和关系映射。

建议先看概念机制图，再看叙事，最后看模型映射，避免映射说明诱导对故事的判断。

## 3. 样本级评分

所有维度采用 1–5 分。

### Mechanism Faithfulness

| 分数 | 标准 |
|---:|---|
| 1 | 核心机制相反或基本无关 |
| 2 | 只有主题相似，关键机制多数缺失 |
| 3 | 覆盖部分机制，但遗漏重要阶段或关系 |
| 4 | 核心节点和关系基本保持，仅有轻微模糊 |
| 5 | 完整、准确地保持关键节点、因果方向和边界 |

### Analogical Alignment Quality

| 分数 | 标准 |
|---:|---|
| 1 | 映射大多不存在或错误 |
| 2 | 少量映射成立，整体不可追踪 |
| 3 | 主要节点可对应，但关系映射不稳定 |
| 4 | 节点和主要关系清楚，少量证据不精确 |
| 5 | 每项映射均有明确文本证据且结构一致 |

### Lexical Concealment

| 分数 | 标准 |
|---:|---|
| 1 | 直接出现概念名或定义句 |
| 2 | 多个高泄露术语，几乎直接揭题 |
| 3 | 有明显提示，但未直接命名 |
| 4 | 只有轻微提示词 |
| 5 | 无直接或软性泄露，意义由情节承载 |

### Narrative Quality

| 分数 | 标准 |
|---:|---|
| 1 | 不连贯或不是叙事 |
| 2 | 有事件但因果断裂、冗余明显 |
| 3 | 基本连贯，但冲突或转折较弱 |
| 4 | 连贯简洁，状态变化清楚 |
| 5 | 情节自然、紧凑，所有事件服务于机制表达 |

### Pedagogical Usefulness

| 分数 | 标准 |
|---:|---|
| 1 | 容易产生严重误解 |
| 2 | 对理解帮助很小 |
| 3 | 能帮助理解部分机制 |
| 4 | 有助于理解并回忆核心机制 |
| 5 | 有助于理解、回忆并迁移到新场景 |

## 4. 映射级标注

对每条 `node_alignment` 标注：

```text
existence: 证据是否存在于叙事
correctness: 叙事元素是否表达该概念节点
specificity: 证据是否足够具体
```

对每条 `edge_alignment` 额外标注：

```text
relation_correctness: 关系类型是否保持
direction_correctness: source -> target 方向是否保持
```

均使用 `0 = 否`、`1 = 部分`、`2 = 是`。

自动评估中的方向分数由
`narrative_source_concept_node_id` 和
`narrative_target_concept_node_id` 与机制图边直接比较。人工标注仍需判断这种结构声明是否被正文语义真正支持。

## 5. 关键错误标签

标注者可多选：

```text
missing_node
missing_edge
reversed_causality
wrong_relation
spurious_mapping
unsupported_evidence
exact_leakage
soft_leakage
theme_only_analogy
irrelevant_plot
template_story
misleading_pedagogy
```

## 6. 标注流程

1. 独立标注，不讨论样本。
2. 每个样本至少 3 人。
3. 先完成 20 个校准样本。
4. 对评分差大于 2 的样本进行仲裁。
5. 报告 Krippendorff's alpha 或 ICC；映射级二元标签可报告 Fleiss' kappa。
6. 在正式标注前冻结规范和示例。

## 7. 与自动评估的关系

最终论文至少报告：

- 自动指标与人工评分的 Spearman 相关性；
- 自动评估在 relation corruption、mechanism omission、surface distractor 上的识别率；
- LLM judge 如被采用，也必须在同一批人工 gold 样本上校准。
