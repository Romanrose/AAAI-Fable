# M2NA 评估板块执行计划

## 目标

建立可复现的评估体系，回答三个问题：

1. 生成叙事是否保持机制节点和关系；
2. 生成叙事是否避免概念与术语泄露；
3. 自动指标是否与人工判断一致且能识别困难错误。

## Phase 1：评估接口与确定性指标

状态：已完成。

- 冻结首版 JSONL 输入结构；
- 将概念图拆为节点与边；
- 将生成映射拆为节点映射与边映射；
- 实现格式、泄露、覆盖、证据、方向和模板指标；
- 建立测试和示例报告。

验收条件：

```text
python3 -m unittest discover -s evaluation/tests -v
python3 evaluation/evaluate_automatic.py \
  evaluation/examples/pilot_examples.jsonl \
  --output evaluation/examples/pilot_metrics.json
```

## Phase 2：20–50 个概念 pilot

状态：待团队提供或冻结概念机制图后执行。

每个概念需要：

- 4–8 个机制节点；
- 3–7 条有方向的机制边；
- 概念名、别名和禁用术语；
- 三种方法的生成结果；
- 节点与边映射证据。

方法：

```text
direct_narrative
alignment_then_write
full_m2na
```

自动执行：

```bash
python3 evaluation/evaluate_automatic.py \
  path/to/pilot_predictions.jsonl \
  --output path/to/pilot_metrics.json
```

## Phase 3：困难负例与评估器压力测试

状态：已完成首版。

已为 5 个固定概念分别生成：

- surface distractor；
- relation corruption；
- mechanism omission。

验收条件：

- 三类负例各 5 条，检测率均为 100%；
- 5 条干净样本误报率为 0%；
- 关系方向由结构字段独立计算，不信任旧自报字段；
- 生成数据和报告可重复生成。

## Phase 4：人工标注与指标校准

状态：标注规范已完成，正式标注待执行。

- 先做 20 个校准样本；
- 每个正式样本至少 3 位标注者；
- 报告一致性；
- 计算自动指标与人工评分的 Spearman 相关性；
- 若加入 LLM judge，必须在相同 gold set 上校准。

## Phase 5：论文结果表

状态：待 pilot 数据完成后执行。

主表至少包含：

```text
Node Coverage
Edge Coverage
Alignment Precision
Relation Direction Accuracy
Exact / Soft Leakage
Mechanism Faithfulness (human)
Alignment Quality (human)
Narrative Quality (human)
```

消融：

```text
w/o edge alignment
w/o forbidden lexical set
w/o source-domain selection
w/o structural self-revision
```

## 当前外部依赖

评估代码和确定性压力测试均已可运行。下一阶段需要上游提供统一格式的概念机制图和三个方法的真实生成结果；当前压力集不能用于得出模型优劣结论。
