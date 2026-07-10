from __future__ import annotations

import re
from typing import Any


MOJIBAKE_MARKERS = (
    "鐢",
    "鍏",
    "閬",
    "涓",
    "浣",
    "鏄",
    "鐨",
    "绗",
    "銆",
    "锛",
    "紝",
    "€",
    "侊",
    "熺",
    "ョ",
    "�",
)


def chinese_char_count(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def chinese_char_ratio(text: str) -> float:
    stripped = "".join(str(text or "").split())
    if not stripped:
        return 0.0
    return chinese_char_count(stripped) / len(stripped)


def mojibake_score(text: str) -> int:
    return sum(str(text or "").count(marker) for marker in MOJIBAKE_MARKERS)


def _repair_score(text: str) -> tuple[int, int, int, int]:
    replacement = text.count("�")
    marker_score = mojibake_score(text)
    suspicious_pairs = len(re.findall(r"[A-Za-z0-9]?[€侊锛紝銆]", text))
    return (replacement, marker_score, suspicious_pairs, -chinese_char_count(text))


def repair_mojibake_text(text: str) -> str:
    if not text:
        return text

    candidates = [text]
    for encoding in ("gb18030", "gbk", "cp936", "latin1"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
        candidates.append(candidate)

    return min(candidates, key=_repair_score)


def clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return repair_mojibake_text(value).strip()
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    return value


def normalize_text(text: Any) -> str:
    return "".join(str(text or "").casefold().split())


def contains_term(text: str, term: str) -> bool:
    normalized_term = normalize_text(term)
    return bool(normalized_term) and normalized_term in normalize_text(text)


def unique_strings(values: list[Any]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[。！？!?；;])\s*|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def first_story_anchor(story: str, index: int = 0) -> str:
    sentences = split_sentences(story)
    if not sentences:
        return story.strip()[:24]
    return sentences[min(index, len(sentences) - 1)][:40]


def mask_forbidden_terms(story: str, forbidden_terms: list[str]) -> str:
    masked = story
    for term in sorted(unique_strings(forbidden_terms), key=len, reverse=True):
        masked = masked.replace(term, "那条隐秘规则")
    return masked
