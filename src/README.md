9，。# M2NA 初版代码 — 第二部分：中间分析的 agent 架构

任务：**Mechanism-to-Narrative Analogy Generation**
输入 `(G_c, T_c)` → 输出 `(N, A)`，并附流水线内自检。

> 当前只实现三段式中的**第二部分**（agent 架构）。第一部分（数据库+清洗）与第三部分（独立评估）暂未实现：
> 输入先用 `fixtures.py` 的手写 `G_c+T_c` 顶替；reviser 的泄露/覆盖自检属于 agent 架构内的质检环，不是独立评估模块。

## 流水线

```
                          ┌─────────────────────────────────────────────┐
                          │         LLMClient (可插拔注入)               │
                          │   MockLLMClient ──now    真实后端 ──later     │
                          │   各 agent 只调 .complete(prompt)->str        │
                          └───────┬───────┬───────┬─────────────────────┘
                                  │       │       │
                                  ▼       ▼       ▼
  输入 (来自第一部分,现用 fixture 顶替)
  ┌──────────────────────────────┐
  │ G_c  概念机制图              │
  │   initial_choice             │        ① Planner          ② Generator         ③ Aligner
  │     →reinforcing_feedback    │      ┌────────────┐     ┌────────────┐     ┌────────────┐
  │     →switching_cost          │      │ G_c        │     │ plan       │     │ N + G_c    │
  │     →lock_in                 │ ───► │  ↓         │ ──► │  ↓         │ ──► │  ↓         │
  │     →suboptimal_persistence  │      │ 选源域+    │     │ 实例化成   │     │ 叙事元素   │
  │                              │      │ 要素→载体  │     │ 短叙事 N   │     │ 回指机制   │
  │ T_c  禁用词集               │      │ 映射 plan  │     │(不出现T_c) │     │ 节点 → A   │
  │  path dependence, lock-in,   │      └─────┬──────┘     └─────┬──────┘     └─────┬──────┘
  │  switching cost, ...         │            │                  │                  │
  └──────────────────────────────┘            ▼                  ▼                  ▼
                                          source_domain:      N:                 A:
                                          "餐馆和它的       "开张那天小店      initial_choice
                                           第一台炉子"        买下唯一买得起    ←买下唯一买得起的炉子
                                                              的炉子…几年后     switching_cost
                                                              换炉子要重训厨师   ←重训厨师、重画菜单
                                                              重画菜单,于是       lock_in
                                                              老炉子留了下来"     ←老炉子年复一年留下
                                                                                  ... (5/5 节点)
                                  │
                                  ▼
                          ④ Reviser  ── 确定性自检 (不调 LLM, 可复现)
                          ┌──────────────────────────────────────────────┐
                          │ Lexical Concealment: N 是否命中 T_c?  → 泄露   │
                          │ Mechanism Preservation: A 是否覆盖 G_c 全节点? │
                          └──────────────────────┬───────────────────────┘
                                                 ▼
                          M2NAResult(N, A, report)
                          report: hard_leaks=none  uncovered=none  → PASS
```

三个关键点：

1. **①②③ 走 LLM，④ 不走**。前三步是创作/分析，需要模型；自检是确定性规则
   （字符串匹配 + 集合覆盖），结果可复现、可当指标。
2. **LLM 是横切依赖，不是流程里的一环**。最上面那条横线表示三个 agent 共享同一个注入的
   client——换 Mock 还是真模型，流程图本身不变。
3. **当前 PASS 是「管路通」，不是「模型强」**。Mock 的预设答案本就对齐好；等 ④ 接上真模型的
   N/A，`report` 的泄露率与未覆盖节点才会变成论文要的真实信号。

## 目录

| 路径 | 职责 |
|---|---|
| `m2na/types.py` | 不可变核心数据结构（G_c / 输入 / 中间产物 / 输出） |
| `m2na/agents/llm.py` | 可插拔 LLM 接口 `LLMClient` + 离线 `MockLLMClient` |
| `m2na/agents/planner.py` | Planner agent |
| `m2na/agents/generator.py` | Generator agent |
| `m2na/agents/aligner.py` | Aligner agent |
| `m2na/agents/reviser.py` | Reviser 自检（无 LLM，结果可复现） |
| `m2na/agents/pipeline.py` | 四 agent 编排 |
| `m2na/fixtures.py` | 最小输入 fixture（path dependence / overfitting） |

## 运行

```bash
python run_demo.py                 # 跑全部 fixture
python run_demo.py "overfitting"   # 指定概念
pytest tests/                      # 测试
```

## 接真实 LLM

各 agent 只依赖 `LLMClient.complete(prompt) -> str`。新增一个调用真实 API
（OpenAI / DeepSeek / 本地）的后端实现该方法，注入 `M2NAPipeline(your_client)` 即可，
无需改动任何 agent。prompt 中的 `[[STAGE:...]] [[CONCEPT:...]]` 标签对真实模型是有效上下文，
对 Mock 用于分发预设响应。
```
