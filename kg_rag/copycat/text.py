from __future__ import annotations

import re
from typing import Any


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


def mask_forbidden_terms(story: str, forbidden_terms: list[str]) -> str:
    masked = story
    for term in sorted(unique_strings(forbidden_terms), key=len, reverse=True):
        masked = masked.replace(term, "那条隐秘规则")
    return masked
