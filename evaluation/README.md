# M2NA Evaluation

该目录是 M2NA 工作流第三板块的首版可运行评估工具，覆盖：

- 输入格式校验；
- 概念名称与高泄露术语检测；
- 节点、关系映射覆盖率；
- 映射证据存在性与幻觉率；
- 关系方向保持率；
- 模板词命中率与基础长度统计；
- 人工评估表结构。

首版只计算可确定复现的指标。机制是否被正确表达、故事是否连贯、类比是否合理等语义判断，不使用字符串匹配冒充，需按 `annotation_guideline.md` 进行人工标注，后续也可以接入经过人工校准的 LLM judge。

## 文件

```text
evaluation/
├── README.md
├── annotation_guideline.md
├── evaluation_schema.json
├── evaluate_automatic.py
├── generate_stress_cases.py
├── evaluate_stress.py
├── human_evaluation_form.md
├── examples/
│   └── pilot_examples.jsonl
├── stress/
│   ├── base_records.jsonl
│   ├── generated_cases.jsonl
│   └── stress_report.json
└── tests/
    ├── test_evaluate_automatic.py
    └── test_stress_suite.py
```

## 数据接口

输入为 JSONL，每行一个生成结果。核心结构：

```json
{
  "id": "path-dependence-full",
  "method": "full_m2na",
  "concept": {
    "name": "路径依赖",
    "aliases": ["path dependence"],
    "forbidden_terms": ["正反馈", "转换成本", "锁定效应"]
  },
  "mechanism_graph": {
    "nodes": [{"id": "n1", "text": "初始选择"}],
    "edges": [
      {
        "id": "e1",
        "source": "n1",
        "target": "n2",
        "relation": "enables"
      }
    ]
  },
  "output": {
    "narrative": "……",
    "node_alignments": [
      {
        "concept_node_id": "n1",
        "narrative_element": "店主最初买下窄口炉",
        "evidence": "店主最初买下窄口炉"
      }
    ],
    "edge_alignments": [
      {
        "concept_edge_id": "e1",
        "narrative_relation": "最初的设备选择促使菜单围绕它形成",
        "evidence": "菜单渐渐只围着这口炉设计",
        "narrative_source_concept_node_id": "n1",
        "narrative_target_concept_node_id": "n2",
        "direction_preserved": true
      }
    ]
  }
}
```

完整约束见 `evaluation_schema.json`。

## 运行

无需安装第三方 Python 包：

```bash
python3 evaluation/evaluate_automatic.py \
  evaluation/examples/pilot_examples.jsonl \
  --output evaluation/examples/pilot_metrics.json
```

终端输出宏平均结果，`--output` 保存逐样本结果和按方法聚合结果。

运行测试：

```bash
python3 -m unittest discover -s evaluation/tests -v
```

生成并执行压力测试：

```bash
python3 evaluation/generate_stress_cases.py \
  evaluation/stress/base_records.jsonl \
  evaluation/stress/generated_cases.jsonl

python3 evaluation/evaluate_stress.py \
  evaluation/stress/generated_cases.jsonl \
  --output evaluation/stress/stress_report.json
```

压力测试包含路径依赖、认知失调、过拟合、公地悲剧和陌生化五个固定概念。每个正例生成：

- `surface_distractor`：保留主题词，但不提供可追踪结构映射；
- `relation_corruption`：保留映射和证据，但反转一条关系的结构方向；
- `mechanism_omission`：删除最高权重节点及其相关关系映射和证据。

## 自动指标定义

| 指标 | 定义 | 方向 |
|---|---|---|
| `format_validity` | 必填字段、ID 唯一性、边端点是否合法 | ↑ |
| `exact_concept_leakage` | 正文是否出现概念名或 alias | ↓ |
| `soft_term_leakage` | 正文是否出现禁用术语 | ↓ |
| `node_coverage` | 有有效证据的已对齐节点数 / 图节点数 | ↑ |
| `edge_coverage` | 有有效证据的已对齐边数 / 图边数 | ↑ |
| `alignment_precision` | 引用合法 ID 且证据存在于正文的映射数 / 全部映射数 | ↑ |
| `alignment_hallucination_rate` | 非法 ID 或证据不在正文的映射比例 | ↓ |
| `relation_direction_accuracy` | 预测 source/target 与机制边方向一致的比例 | ↑ |
| `template_hit_rate` | 命中的模板词数 / 配置模板词数 | ↓ |
| `narrative_char_count` | 正文字符数 | 按任务约束 |

边映射必须提供：

```text
narrative_source_concept_node_id
narrative_target_concept_node_id
```

评估器将它们与机制图边的 `source` 和 `target` 独立比较。旧的 `direction_preserved` 字段仅为兼容保留，不参与得分。

## 压力测试验收

默认阈值：

```text
每类负例检测率 >= 90%
干净样本误报率 <= 10%
```

当前固定压力集结果：

```text
surface_distractor: 100%
relation_corruption: 100%
mechanism_omission: 100%
clean false-positive rate: 0%
```

这些结果只证明确定性评估协议能识别预定义扰动，不代表模型生成质量。

## 推荐接入方式

生成板块应直接输出 `node_alignments` 和 `edge_alignments`，不要在评估阶段重新猜测模型原本的映射。评估板块再检查：

1. 映射引用的节点和边是否存在；
2. 引用的证据是否真的出现在正文；
3. 所有关键节点和边是否被覆盖；
4. 人工标注者是否同意关系和方向成立。

第一轮实验建议比较：

```text
direct_narrative
alignment_then_write
full_m2na
```

每种方法使用同一批概念和机制图。
