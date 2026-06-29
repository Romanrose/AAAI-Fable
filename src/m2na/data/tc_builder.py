"""禁用词集 T_c 构建。

T_c = 正文 N 中不允许出现的「会直接点破概念」的词。reviser 用子串匹配检测泄露
（见 agents/reviser.py 的 `term.lower() in narrative.lower()`），因此 T_c 的元素应是
会原样出现在叙事里的术语本身。

本模块只做**确定性**部分：概念名 + 名称括号内别名 + aliases + 人工补充词。
更激进的「高泄露同义术语扩展」属于 soft leakage，留给 LLM/人工，不在此硬编码，
以免误伤通用词导致过度禁用。
"""

from __future__ import annotations

import re
from typing import Iterable, Tuple

from .k12_loader import ConceptRecord

# 概念名里的括号别名，如「静电力做功与路径无关（静电场力做功特点）」。中英文括号都处理。
_PAREN_RE = re.compile(r"[（(]([^（）()]+)[）)]")


def _strip_parenthetical(name: str) -> Tuple[str, Tuple[str, ...]]:
    """拆出主名与括号内别名。返回 (主名, (括号词,...))。"""

    inner = tuple(m.strip() for m in _PAREN_RE.findall(name) if m.strip())
    base = _PAREN_RE.sub("", name).strip()
    return base, inner


def _dedup_preserving_order(terms: Iterable[str]) -> Tuple[str, ...]:
    """去空白、大小写不敏感去重、保留首次出现顺序。"""

    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        cleaned = term.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return tuple(out)


def build_forbidden_terms(
    record: ConceptRecord, *, extra_terms: Iterable[str] = ()
) -> Tuple[str, ...]:
    """从概念记录构建 T_c。

    顺序：主名 → 名称括号别名 → record.aliases → 人工补充 extra_terms。
    全部去空、去重（大小写不敏感）、保序。

    Args:
        record: 概念记录。
        extra_terms: 人工/LLM 提供的额外高泄露术语（如 formula 中的关键符号词）。
    """

    base, paren_aliases = _strip_parenthetical(record.name)
    candidates = (base, *paren_aliases, *record.aliases, *extra_terms)
    return _dedup_preserving_order(candidates)
