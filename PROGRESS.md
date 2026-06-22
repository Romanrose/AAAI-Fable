# 进度与待办 (Handoff)

> 给后续 agent：本文件是冷启动入口。读完它 + `src/README.md` 即可接手，无需翻聊天记录。
> 最近更新：2026-06-22。分支：`lzf`。项目根：`~/Desktop/workspace/AAAI-Fable`。

---

## 1. 这个项目在做什么

一篇 AAAI 论文的初版代码。论文任务（**已收窄定稿**）：

> **M2NA — Mechanism-to-Narrative Analogy Generation**
> 输入概念机制图 `G_c` + 禁用词集 `T_c`，输出隐性叙事类比 `N` + 结构映射 `A`。
> 核心约束四条：机制保持、词汇隐藏(concealment)、可对齐、叙事最小。

权威定义见 `doc/文章思路迭代（主要看这个）/ConceptFable_AAAI_收窄任务_学术问题定义.md`。

### 路线决策（重要，别走回头路）
- 仓库里有**两套**论文框架：M2NA（收窄）与 Concept-to-Fable / KG-Fable（整合，含 RAG + 人类学习实验）。
- **已定主线 = M2NA**。整合稿（`...问题定义方法摘要Introduction整合稿.md`）视为上一版/扩展版，不作为代码目标。
- README（仓库根的 `README.md`）仍以整合版口径写，**尚未同步到 M2NA**，注意别被它带偏。

### 系统三段式（用户的划分）
1. 第一部分：数据库 + 数据清洗（产出 `G_c` / `T_c`）
2. 第二部分：中间分析的 agent 架构（生成 `N` / `A`）
3. 第三部分：评估

---

## 2. 已完成 ✅ — 第二部分（agent 架构）

`(G_c, T_c) → (N, A)` 的多 agent 端到端闭环，已跑通。

```
Planner → Generator → Aligner → Reviser
(选源域+映射) (写叙事N) (回指出A) (确定性自检)
```

文件（均在 `src/`，遵循小文件 + frozen dataclass 不可变）：

| 文件 | 职责 |
|---|---|
| `m2na/types.py` | 核心数据结构：`MechanismGraph(G_c)` / `M2NAInput` / `NarrativePlan` / `M2NAResult` 等 |
| `m2na/agents/llm.py` | 可插拔 `LLMClient` 协议 + 离线 `MockLLMClient`（按 prompt 标签返回预设） |
| `m2na/agents/planner.py` | Planner：`G_c` → 源域 + 「要素→载体」映射 |
| `m2na/agents/generator.py` | Generator：plan + `T_c` → 叙事 `N` |
| `m2na/agents/aligner.py` | Aligner：`N` + `G_c` → 对齐 `A` |
| `m2na/agents/reviser.py` | Reviser：确定性自检（泄露 + 覆盖），**不调 LLM** |
| `m2na/agents/pipeline.py` | `M2NAPipeline` 编排四 agent |
| `m2na/fixtures.py` | 手写输入 fixture：`path dependence` / `overfitting`（顶替尚未做的第一部分） |
| `run_demo.py` | 端到端 demo 入口 |
| `tests/test_pipeline.py` | pytest 测试（含泄露/覆盖反向用例） |
| `src/README.md` | 第二部分详细说明 + 数据流图 |

### 验证状态
- `python run_demo.py` ✅ 两个概念都跑出 N+A，自检 PASS。
- 测试逻辑 ✅ 全部断言通过——但 ⚠️ **是用 stdlib 等价脚本验证的**，因为 sandbox 无网络装不上 pytest。
  接手后请在有网环境跑 `pip install pytest && pytest tests/` 做正式确认。

### 关键设计决策
1. **LLM 是横切注入依赖**：①②③ 共享同一个 `LLMClient`，④ 不用。换 Mock / 真模型不改 agent。
2. **Reviser 是确定性规则**（字符串匹配 + 集合覆盖），所以可复现、可当指标——它是质检环，不是第三部分的独立评估模块。
3. ⚠️ **当前 self-check PASS 不代表模型强**：Mock 的预设答案本就对齐好的，只证明「管路通」。
   接真模型后 `report` 的泄露率/未覆盖节点才是论文要的真实信号。

---

## 3. 待办 📋

### A. 接真实 LLM 后端（建议优先，能立刻产出有意义信号）
- 写一个实现 `LLMClient.complete(prompt)->str` 的真实后端（OpenAI 兼容 / DeepSeek / 本地）。
- 注入 `M2NAPipeline(real_client)` 即可，agent 一行不用改。
- prompt 里的 `[[STAGE:...]] [[CONCEPT:...]]` 标签对真模型是有效上下文，可保留。
- 需要用户提供 API key / endpoint。

### B. 第一部分：数据库 + 数据清洗（`G_c` 的来源 = 论文命门）
- 定义概念库 schema，把 `fixtures.py` 换成清洗管线产出的真实数据。
- ⚠️ **`G_c` 怎么来是审稿人必问、也最致命的点**：
  - 人手标 → 规模上不去、主观性被攻击；
  - LLM 抽 → 循环论证（同源 LLM 抽图+生成+评分，覆盖率高只证明前后一致）。
  - 必须把 `G_c` 构建本身写成方法贡献（来源、验证、IAA），否则任务退化成「带禁用词的 graph-to-text」。
- 可考虑接入仓库已有的 `data/K12-KGraph/`。

### C. 第三部分：评估（独立模块）
- 把 reviser 的自检升级 / 扩展为正式评估协议：硬泄露率、软泄露率、机制覆盖、对齐一致性、叙事质量。
- ⚠️ **Soft Leakage 当前定义太软**（"明显领域术语"边界不清）。需要可操作的判定协议
  （固定 `T_c` 词表 + 同义扩展 + 人工裁定 IAA），否则 concealment 这个最大卖点不可复现。

### D. 杂项
- 同步根 `README.md` 到 M2NA 口径（消除与整合版的路线分叉）。
- 正式跑通 pytest（见上）。

---

## 4. 竞品距离（写 Related Work / 守护差异化时看）
最近四篇：**ARN (TACL'24)**、**ParallelPARC (NAACL'24)**、EMNLP'24 teacher-analogy、CHI'25。
与最近的 ParallelPARC 真正区别只有两点：**生成方向(generation vs recognition)** + **lexical concealment**。
→ 这两点必须做硬做实，它们是全部差异化。详见 `doc/论文调研/M2NA_2024-2026相关论文检索.md`。

---

## 5. 怎么继续

```bash
cd ~/Desktop/workspace/AAAI-Fable
git branch --show-current          # 应是 lzf
python run_demo.py                 # 跑全部 fixture
python run_demo.py "overfitting"   # 跑指定概念
pip install pytest && pytest tests/   # 正式测试(需联网)
```
