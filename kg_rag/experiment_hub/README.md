# Concept2Fable Experiment Hub

`kg_rag.experiment_hub` 是 Concept2Fable 的统一本地审核入口。它不生成实验数据，而是启动并嵌入已有审核服务和静态图谱页；审核决定仍由各自应用追加写入实验目录。

工作台包含：

1. Concept2Fable V2 的机制审核；
2. Standard 与 Deterministic Copycat 映射审核；
3. LLM-guided Copycat 映射查看；
4. 三策略最终故事审核；
5. `data/visualization/global_kg/` 的 K12 全局图谱；
6. `data/visualization/concept_kg/` 的概念中心图谱。

```bash
python -m kg_rag.experiment_hub
```

打开 <http://127.0.0.1:8769/>。默认端口为 `8769`（Hub）、`8770`（机制）、`8771`（映射）和 `8772`（故事）；可通过 CLI 的对应 `--*-port` 参数覆盖。
