# 进度与待办 (Handoff)

> 给后续 agent：本文件是冷启动入口。读完它 + `src/README.md` 即可接手，无需翻聊天记录。
> 最近更新：2026-06-28。分支：`lzf`。项目根：`~/Desktop/work_space/AAAI-Fable`。

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
- README（仓库根的 `README.md`）已同步到 M2NA 口径；当前流程图见 `doc/当前系统流程图.md`。

### 系统三段式（用户的划分）
1. 第一部分：数据库 + 数据清洗（产出 `G_c` / `T_c`）
2. 第二部分：中间分析的 agent 架构（生成 `N` / `A`）
3. 第三部分：评估

---

## 2. 已完成 ✅ — 第二部分（agent 架构）

`(G_c, T_c) → (N, A)` 的多 agent 端到端闭环，已用 Mock 与 DeepSeek 跑通。

```
Planner → Generator → Aligner → Reviser
(寓言蓝图) (写隐性寓言N) (回指出A) (确定性自检)
```

文件（均在 `src/`，遵循小文件 + frozen dataclass 不可变）：

| 文件 | 职责 |
|---|---|
| `m2na/types.py` | 核心数据结构：`MechanismGraph(G_c)` / `M2NAInput` / `NarrativePlan` / `FableCharacter` / `PlotBeat` / `M2NAResult` 等 |
| `m2na/agents/llm.py` | 可插拔 `LLMClient` 协议 + 离线 `MockLLMClient`（按 prompt 标签返回预设） |
| `m2na/agents/planner.py` | Planner：`G_c` + `T_c` → 寓言蓝图（角色/冲突/情节节拍/结局/映射） |
| `m2na/agents/generator.py` | Generator：寓言蓝图 + `T_c` → 隐性寓言 `N` |
| `m2na/agents/aligner.py` | Aligner：`N` + `G_c` → 对齐 `A` |
| `m2na/agents/reviser.py` | Reviser：确定性自检（泄露 + 覆盖），**不调 LLM** |
| `m2na/agents/pipeline.py` | `M2NAPipeline` 编排四 agent |
| `m2na/fixtures.py` | 手写输入 fixture：`path dependence` / `overfitting`（用于 Mock 离线 demo） |
| `m2na/result_store.py` | 保存 `input/plan/narrative/alignment/report/result/summary` |
| `run_demo.py` | 端到端 demo 入口 |
| `run_real_demo.py` | 真实 DeepSeek 单样本运行并保存到 `output/` |
| `run_real_batch.py` | 批量真实运行并保存到 `output/` |
| `tests/test_pipeline.py` | pytest 测试（含泄露/覆盖反向用例） |
| `src/README.md` | 第二部分详细说明 + 数据流图 |

### 验证状态
- `uv run python run_demo.py` ✅ 两个 Mock 概念都跑出 N+A，自检 PASS。
- `uv run pytest` ✅ 41 个测试全过。
- DeepSeek 真实运行 ✅ 3 个简单对话机制样例全 PASS，结果见 `output/20260628_*`。

### 关键设计决策
1. **LLM 是横切注入依赖**：①②③ 共享同一个 `LLMClient`，④ 不用。换 Mock / 真模型不改 agent。
2. **Reviser 是确定性规则**（字符串匹配 + 集合覆盖），所以可复现、可当指标——它是质检环，不是第三部分的独立评估模块。
3. **Planner 现在产出寓言蓝图**：不仅选源域和映射，还生成 `characters / conflict / plot_beats / ending / implied_moral`，避免 Generator 只写普通案例。
4. ⚠️ **当前 self-check PASS 不代表模型强**：它只证明硬泄露和节点覆盖通过；寓言质量、自然度、软泄露和学习效果仍需第三部分评估。

---

## 3. 待办 📋

### A. 接真实 LLM 后端 ✅ 已完成（2026-06-23）
- `src/m2na/agents/deepseek.py`：`DeepSeekClient` 实现 `LLMClient.complete`，stdlib urllib 直连
  DeepSeek OpenAI 兼容接口，无第三方依赖。注入方式与 Mock 一致。
- API key 从项目根 `.env` 或环境变量 `DEEPSEEK_API_KEY` 读；`.env` 已加入 `.gitignore`，模板见 `.env.example`。
- ⚠️ **SSL 注意**：本机在 TLS 拦截代理后（自签名根证书），Python certifi 不认。
  需用系统钥匙串导出 CA bundle 再指给它：
  ```bash
  security find-certificate -a -p /Library/Keychains/System.keychain > /tmp/corp_ca.pem
  security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain >> /tmp/corp_ca.pem
  export SSL_CERT_FILE=/tmp/corp_ca.pem   # 或 DeepSeekClient(ca_bundle=...) / 环境变量 DEEPSEEK_CA_BUNDLE
  ```
- `run_real_demo.py` 已接入 `M2NAPipeline(DeepSeekClient())`，并会把运行产物保存到 `output/`。

### A2. 真实样例运行 ✅ 已完成（2026-06-28）
已构建 3 个简单对话机制输入并真实跑通：

| 概念 | 输入 | 输出目录 | 自检 |
|---|---|---|---|
| 误会升级 | `data/concepts/raw/simple_dialogue_misunderstanding.json` | `output/20260628_142504_误会升级/` | PASS |
| 主动倾听 | `data/concepts/raw/simple_dialogue_active_listening.json` | `output/20260628_142545_主动倾听/` | PASS |
| 轮流发言 | `data/concepts/raw/simple_dialogue_turn_taking.json` | `output/20260628_142634_轮流发言/` | PASS |

每个输出目录包含：`input.json / plan.json / narrative.txt / alignment.json / report.json / result.json / summary.md`。

### B. 第一部分：数据库 + 数据清洗 🚧 已起步（2026-06-23）
**决策已拍板**：主战场=**理科，全用 K12-KGraph**；`G_c`=**从教材定义半自动抽取+人工校验**。

已完成 `src/m2na/data/`（均带自运行测试，无 pytest 也能跑，共 29 个全过）：

| 文件 | 职责 |
|---|---|
| `k12_loader.py` | 读 `data/K12-KGraph/.../subject_specific_KG/*.json` → 不可变 `ConceptRecord`(def/formula/examples/aliases) |
| `concept_selection.py` | 确定性机制信号词打分，6574 概念粗筛成候选（化学300/生物156/物理/数学少） |
| `gc_extractor.py` | LLM 抽 `MechanismGraph`（prompt+解析+严格校验，解析确定性可测；调用走可注入 LLMClient） |
| `tc_builder.py` | 确定性构建 `T_c`（名+括号别名+aliases+人工补充，去重保序） |
| `concept_store.py` | `M2NAInput ↔ JSON` 序列化（raw 草稿→人工编辑→processed→读回喂第二部分） |
| `explore_concepts.py`(根) | 候选肉眼核验 CLI |

**已真跑验证**（DeepSeek，2 概念）：胰岛素 G_c 近乎完美；但「化学反应速率」⚠️ **LLM 注入了定义里没有的内容**（温度/压强/催化剂）。
→ **这就是 faithfulness/循环论证风险的现场证据**。结论：抽取 prompt 需更强「严格只用定义」约束 + 人工校验剔越界节点，**半自动是对的，纯自动不行**。

**第一部分剩余**：
- [x] 调强 `gc_extractor` 的 prompt：明确抽**核心机制图**，优先 3–6 节点，最多 8 节点，只保留主因果链和必要分叉。
- [x] 写 `build_concept_inputs.py`：选概念→抽 G_c→建 T_c→`save_input` 落盘的批处理入口。
- [x] 把 raw 的 `M2NAInput` 用 `load_input` 接进 `M2NAPipeline(DeepSeekClient())` 跑真实 N+A。
- [ ] 批量抽 5–10 个 K12 pilot 概念 → 存 `data/concepts/raw/` → 人工校验 → `processed/`。
- [ ] 建立 `processed/` 的人工校验规范，避免 raw 草稿越界节点进入正式实验。

### C. 第三部分：评估（独立模块）
- 把 reviser 的自检升级 / 扩展为正式评估协议：硬泄露率、软泄露率、机制覆盖、对齐一致性、叙事质量。
- ⚠️ **Soft Leakage 当前定义太软**（"明显领域术语"边界不清）。需要可操作的判定协议
  （固定 `T_c` 词表 + 同义扩展 + 人工裁定 IAA），否则 concealment 这个最大卖点不可复现。

### D. 杂项
- 同步根 `README.md` 到 M2NA 口径（消除与整合版的路线分叉）。
- 正式跑通 pytest（见上）。

### E. 环境管理 ✅ 已完成（2026-06-28）
- 新增 `pyproject.toml`，用 `uv` 管理 Python 环境。
- 运行期依赖为空（标准库）；`pytest>=7.0` 放入 `dev` 依赖组。
- 推荐命令：`uv sync --dev`、`uv run python run_demo.py`、`uv run pytest`。

### F. 当前流程图 ✅ 已完成（2026-06-28）
- 新增 `doc/当前系统流程图.md`，用 Mermaid 描述：输入构建 → 寓言 agent 流水线 → 自检 → output 落盘。
- 根 `README.md` 与 `src/README.md` 已同步到当前流程。

---

## 4. 竞品距离（写 Related Work / 守护差异化时看）
最近四篇：**ARN (TACL'24)**、**ParallelPARC (NAACL'24)**、EMNLP'24 teacher-analogy、CHI'25。
与最近的 ParallelPARC 真正区别只有两点：**生成方向(generation vs recognition)** + **lexical concealment**。
→ 这两点必须做硬做实，它们是全部差异化。详见 `doc/论文调研/M2NA_2024-2026相关论文检索.md`。

---

## 5. 怎么继续

```bash
cd ~/Desktop/work_space/AAAI-Fable
git branch --show-current          # 应是 lzf
uv sync --dev
uv run python run_demo.py                 # 跑全部 fixture
uv run python run_demo.py "overfitting"   # 跑指定概念
uv run pytest                             # 正式测试
```
