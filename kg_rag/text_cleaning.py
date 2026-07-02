from __future__ import annotations

from typing import Any


MOJIBAKE_MARKERS = (
    "�",
    "Ã",
    "Â",
    "Ð",
    "鈥",
    "鈴",
    "涓",
    "嬫",
    "勫",
    "鐨",
    "绱",
    "鍏",
    "浣",
    "滅",
    "敤",
)


def mojibake_score(text: str) -> int:
    return sum(text.count(marker) for marker in MOJIBAKE_MARKERS)


def repair_text(text: str) -> str:
    if not text:
        return text

    candidates = [text]
    for encoding in ("gb18030", "gbk", "cp936", "latin1"):
        try:
            candidates.append(text.encode(encoding).decode("utf-8"))
        except UnicodeError:
            continue

    return min(candidates, key=lambda value: (mojibake_score(value), -len(value)))


def clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return repair_text(value)
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    return value


def count_text_issues(value: Any) -> int:
    if isinstance(value, str):
        return mojibake_score(value)
    if isinstance(value, list):
        return sum(count_text_issues(item) for item in value)
    if isinstance(value, dict):
        return sum(count_text_issues(item) for item in value.values())
    return 0
