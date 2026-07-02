from __future__ import annotations

import re
from typing import Any

from kg_rag.text_cleaning import repair_text


def subject_from_id(node_id: str) -> str:
    return node_id.split("_", 1)[0]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return repair_text(str(value)).strip()


def cjk_ratio(text: str) -> float:
    if not text:
        return 0.0
    non_space = [char for char in text if not char.isspace()]
    if not non_space:
        return 0.0
    cjk_count = sum(1 for char in non_space if "\u4e00" <= char <= "\u9fff")
    return cjk_count / len(non_space)


def text_quality(*, name: str, definition: str) -> str:
    if not name.strip():
        return "missing"
    joined = f"{name}\n{definition}".strip()
    if "\ufffd" in joined:
        return "broken"
    if not definition.strip():
        return "missing"
    ratio = cjk_ratio(joined)
    if ratio >= 0.45:
        return "good"
    if ratio >= 0.2:
        return "suspicious"
    return "broken"


def context_quality(degree: int) -> str:
    if degree >= 6:
        return "high"
    if degree >= 2:
        return "medium"
    return "low"


def generation_priority(*, quality: str, has_definition: bool, degree: int) -> str:
    if quality in {"broken", "missing"} and not has_definition:
        return "repair"
    if quality == "broken":
        return "repair"
    if has_definition and quality == "good" and degree >= 3:
        return "gold"
    if has_definition and quality in {"good", "suspicious"}:
        return "silver"
    return "bronze"


def safe_dir_name(value: str) -> str:
    safe = []
    for char in value:
        if char.isalnum() or char in ("-", "_"):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("_") or "concept"


def chinese_char_ratio(text: str) -> float:
    return cjk_ratio(re.sub(r"```[\s\S]*?```", "", text))

