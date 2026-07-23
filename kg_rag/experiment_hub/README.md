# Concept2Fable Experiment Hub

`kg_rag.experiment_hub` 是 Concept2Fable 的统一本地审核入口。它不生成实验数据，而是启动并嵌入已有审核服务和静态图谱页；审核决定仍由各自应用追加写入实验目录。

工作台包含：

1. Pilot80 的 Concept2Fable V2 机制审核；
2. `full6574` 的全量概念机制图：按概念搜索并查看机制节点、边与证据；
3. Standard 与 Deterministic Copycat 映射审核；
4. LLM-guided Copycat 映射查看；
5. 三策略最终故事审核；
6. `data/visualization/global_kg/` 的 K12 全局图谱；
7. `data/visualization/concept_kg/` 的概念中心图谱。

```bash
python -m kg_rag.experiment_hub
```

打开 <http://127.0.0.1:8769/>。默认端口为 `8769`（Hub）、`8770`（Pilot80 机制）、`8773`（全量机制）、`8771`（映射）和 `8772`（故事）；可通过 CLI 的对应 `--*-port` 参数覆盖。全量机制数据默认读取 `data/derived/kg_rag/m2na_v2/full6574/`，也可通过 `--full-preparation-root` 指向其他全量产物目录。

各标签直接读取同步到当前工作区的产物：Pilot80 与全量机制图分别读取各自的 `m2na_v2` 目录；映射审核读取 `mapping_plans/concepts/`；LLM-guided 映射与最终故事审核读取 `story_pilot12/`。索引内遗留的旧设备绝对路径仅作溯源记录，工作台会按当前目录解析实际文件。

## 共享实验边界

工作台当前只展示既有正式实验。新个人评估请在 [`kg_rag/shared/`](../shared/README.md) 建立独立实验，并遵循[共享实验约定](../SHARED_EXPERIMENTS.md)；不要直接把探索性产物接入默认页面。
