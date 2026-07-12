# Concept2Fable v2 Paper Draft

`v2/` 是当前活跃的 Concept2Fable AAAI 论文工作目录。方法描述必须以实际代码和已提交实验产物为准：

- `kg_rag/m2na_v2/`：机制优先的 Core80 准备、审核与双策略正式运行；
- `kg_rag/story_pilot/`：Pilot12 的 Standard、Deterministic Copycat、LLM-guided Copycat 比较；
- `kg_rag/aaai_eval/`：数据集、协议、统一记录和论文结果表。

## 文件

- `concept2fable_v2_paper.tex`：AAAI 风格英文稿。
- `concept2fable_v2_paper.pdf`：当前编译预览。
- `concept2fable_v2_references.bib`：参考文献。
- `concept2fable_v2_method_zh.md` / `concept2fable_v2_method_en.md`：中英文方法参考稿。

Pilot12 的已完成结果可以引用；Core80、Human32、FullKG 和尚未实际运行的消融必须继续标注为待完成。教育价值是研究动机，除非已完成相应学习实验，不得写成已验证的学习效果。

## 编译

macOS/Linux：

```bash
export TEXINPUTS="$(cd ../.. && pwd):${TEXINPUTS}"
export BIBINPUTS="$(pwd):$(cd ../.. && pwd):${BIBINPUTS}"
export BSTINPUTS="$(cd ../.. && pwd):${BSTINPUTS}"
latexmk -pdf -interaction=nonstopmode -halt-on-error concept2fable_v2_paper.tex
```

Windows PowerShell：

```powershell
$env:TEXINPUTS="$(Resolve-Path ..\..);" + $env:TEXINPUTS
$env:BIBINPUTS="$(Resolve-Path .);$(Resolve-Path ..\..);" + $env:BIBINPUTS
$env:BSTINPUTS="$(Resolve-Path ..\..);" + $env:BSTINPUTS
latexmk -pdf -interaction=nonstopmode -halt-on-error .\concept2fable_v2_paper.tex
```
