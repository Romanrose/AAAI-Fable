# Concept2Fable Paper Workspace

这是 Concept2Fable AAAI 论文的版本化工作区。当前活跃稿件为 `v2/`；`v1/` 保留为 Pilot12 可行性稿和历史对照，不应被覆盖。

## 目录与命名

```text
concept2fable/
├─ v1/  首版论文与 Pilot12 历史结果
└─ v2/  当前方法重写稿、参考文献和中英文方法说明
```

版本化文件使用：

```text
concept2fable_v{VERSION}_{DOCUMENT_TYPE}.{EXTENSION}
```

同一版本的 TeX、BibTeX、写作说明和 PDF 必须一致。实验数字只能引用已提交的 manifest、审核记录或 `kg_rag/aaai_eval/` 报告；Core80、Human32 或消融尚未完成时必须明确标注为未完成，不得用预期结果替代。

## 编译 v2

从 `v2/` 目录运行，AAAI 样式位于两级上方的 `AuthorKit27/`：

```bash
export TEXINPUTS="$(cd ../.. && pwd):${TEXINPUTS}"
export BIBINPUTS="$(pwd):$(cd ../.. && pwd):${BIBINPUTS}"
export BSTINPUTS="$(cd ../.. && pwd):${BSTINPUTS}"
latexmk -pdf -interaction=nonstopmode -halt-on-error concept2fable_v2_paper.tex
```

Windows PowerShell 可使用 v2 README 中的等价命令。`.aux`、`.log`、`.fls`、`.fdb_latexmk` 等编译缓存可再生；TeX、BibTeX、图、方法稿和需要保留的 PDF 是论文资产。
