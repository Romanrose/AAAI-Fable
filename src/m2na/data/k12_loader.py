"""K12-KGraph 概念加载器。

只读 `data/K12-KGraph/K12-KGraph/subject_specific_KG/*.json`——subject 图带有
`definition / formula / examples / aliases` 等富属性（global_KG 只有 id/name，不够用）。

输出 ConceptRecord（不可变），作为第一部分后续步骤（机制图抽取、T_c 构建）的统一输入。
本模块不做任何机制判断，只负责「把教材概念读成结构化记录」这一件事。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple

# subject 图覆盖的四个学科。math 多为定义性概念、机制少，仍读入，由选择阶段过滤。
SUBJECTS: Tuple[str, ...] = ("biology", "chemistry", "math", "physics")

_CONCEPT_LABEL = "Concept"


@dataclass(frozen=True)
class ConceptRecord:
    """一个教材概念的结构化记录。

    字段直接来自 K12-KGraph subject 节点的 properties，做了「缺失即空」的归一化，
    使下游无需再判 None / KeyError。
    """

    id: str
    name: str
    subject: str
    definition: str
    formula: str
    examples: Tuple[str, ...]
    aliases: Tuple[str, ...]
    importance: str = ""

    def has_definition(self) -> bool:
        return bool(self.definition.strip())


def _subject_kg_root(root: Path | str | None) -> Path:
    """定位 subject_specific_KG 目录。

    默认从本文件位置回溯到仓库根（src/m2na/data/k12_loader.py -> parents[3]）。
    显式传入 root 时，root 应指向 subject_specific_KG 所在目录。
    """

    if root is not None:
        return Path(root)
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "K12-KGraph" / "K12-KGraph" / "subject_specific_KG"


def _as_str(value: Any) -> str:
    """把 properties 里可能为 None / 数字 / 列表的值归一成字符串。"""

    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return " ".join(_as_str(v) for v in value).strip()
    return str(value).strip()


def _as_str_tuple(value: Any) -> Tuple[str, ...]:
    """把 examples / aliases 归一成去空、去重(保序)的字符串元组。"""

    if value is None:
        return ()
    items = value if isinstance(value, (list, tuple)) else [value]
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = _as_str(item)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def _node_to_record(node: dict, subject: str) -> ConceptRecord | None:
    """把一个 KG 节点转成 ConceptRecord；非 Concept 或缺 id/name 则返回 None。"""

    if node.get("label") != _CONCEPT_LABEL:
        return None
    node_id = _as_str(node.get("id"))
    name = _as_str(node.get("name"))
    if not node_id or not name:
        return None

    props = node.get("properties") or {}
    return ConceptRecord(
        id=node_id,
        name=name,
        subject=subject,
        definition=_as_str(props.get("definition")),
        formula=_as_str(props.get("formula")),
        examples=_as_str_tuple(props.get("examples")),
        aliases=_as_str_tuple(props.get("aliases")),
        importance=_as_str(props.get("importance")),
    )


def load_subject(
    subject: str, root: Path | str | None = None
) -> Tuple[ConceptRecord, ...]:
    """读取单个学科的全部 Concept 记录。

    Args:
        subject: SUBJECTS 之一。
        root: subject_specific_KG 目录；None 时用默认仓库内路径。

    Raises:
        ValueError: subject 不在 SUBJECTS 内。
        FileNotFoundError: 对应 JSON 不存在。
    """

    if subject not in SUBJECTS:
        raise ValueError(f"未知学科 {subject!r}，可选: {SUBJECTS}")

    path = _subject_kg_root(root) / f"{subject}.json"
    if not path.is_file():
        raise FileNotFoundError(f"找不到学科图: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", []) if isinstance(data, dict) else data

    records = []
    for node in nodes:
        record = _node_to_record(node, subject)
        if record is not None:
            records.append(record)
    return tuple(records)


def load_all_concepts(root: Path | str | None = None) -> Tuple[ConceptRecord, ...]:
    """读取全部学科的 Concept 记录（按 SUBJECTS 顺序拼接）。"""

    out: list[ConceptRecord] = []
    for subject in SUBJECTS:
        out.extend(load_subject(subject, root=root))
    return tuple(out)
