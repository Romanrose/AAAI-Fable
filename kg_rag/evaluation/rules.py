from __future__ import annotations

import difflib
import re
from typing import Any

from kg_rag.evaluation.parser import strip_alignment_from_story
from kg_rag.evaluation.rubric import DIMENSIONS, EvaluationInput


TEMPLATE_PATTERNS = (
    "wise elder",
    "old man",
    "village",
    "forest animals",
    "from that day on",
    "everyone understood",
    "\u4ece\u6b64\u4ee5\u540e",
    "\u5927\u5bb6\u660e\u767d\u4e86",
    "\u667a\u8005",
    "\u8001\u4eba",
    "\u6751\u5e84",
    "\u68ee\u6797",
)

SOFT_LEAKAGE_TERMS = (
    "concept",
    "mechanism",
    "definition",
    "\u6982\u5ff5",
    "\u673a\u5236",
    "\u5b9a\u4e49",
    "\u672f\u8bed",
)


def _contains_term(text: str, term: str) -> bool:
    term = term.strip()
    if not term:
        return False
    if re.search(r"[\u4e00-\u9fff]", term):
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE) is not None


def _story_title(story_body: str) -> str:
    for line in story_body.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:160]
    return ""


def _token_count(text: str) -> int:
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    latin_words = re.findall(r"[A-Za-z0-9]+", text)
    return len(cjk_chars) + len(latin_words)


def _alignment_roles(evaluation_input: EvaluationInput) -> list[str]:
    roles = []
    for item in evaluation_input.alignment_table:
        role = item.get("concept_role") or item.get("role")
        if role:
            text = str(role).lower()
            if "\u76ee\u6807\u6982\u5ff5" in text:
                text = "target concept"
            elif "\u6838\u5fc3\u673a\u5236" in text or "\u6982\u5ff5\u673a\u5236" in text:
                text = "core mechanism"
            elif "\u5b66\u79d1\u7ea6\u675f" in text:
                text = "subject constraints"
            roles.append(text)
    return roles


def evaluate_rules(
    evaluation_input: EvaluationInput,
    *,
    peer_stories: list[str] | None = None,
) -> tuple[dict[str, int], dict[str, bool], dict[str, str], list[str], dict[str, Any]]:
    story_body = strip_alignment_from_story(evaluation_input.draft_story)
    story_lower = story_body.lower()
    title = _story_title(story_body)
    token_count = _token_count(story_body)

    leaked_terms = [
        term for term in evaluation_input.forbidden_terms if len(term.strip()) >= 2 and _contains_term(story_body, term)
    ]
    title_leaks = [term for term in leaked_terms if _contains_term(title, term)]
    soft_terms = [term for term in SOFT_LEAKAGE_TERMS if _contains_term(story_body, term)]

    roles = _alignment_roles(evaluation_input)
    expected_roles = ("target concept", "prerequisites", "related concepts", "outcomes", "experiments", "exercises")
    missing_roles = [role for role in expected_roles if role not in roles]
    mapped_role_count = len(set(roles))
    has_zh_core_mapping = "target concept" in roles and "core mechanism" in roles

    template_hits = [pattern for pattern in TEMPLATE_PATTERNS if pattern.lower() in story_lower]
    peer_similarity = 0.0
    if peer_stories:
        peer_similarity = max(
            (difflib.SequenceMatcher(a=story_body, b=strip_alignment_from_story(peer)).ratio() for peer in peer_stories),
            default=0.0,
        )

    hard_flags = {
        "hard_leakage": bool(leaked_terms),
        "soft_leakage": bool(soft_terms),
        "title_leakage": bool(title_leaks),
        "concept_contradiction": False,
        "unmapped_core_mechanism": mapped_role_count < 2 and not has_zh_core_mapping,
        "template_like": len(template_hits) >= 2 or peer_similarity >= 0.82,
    }

    scores = {dimension: 4 for dimension in DIMENSIONS}
    if hard_flags["hard_leakage"]:
        scores["implicitness"] = 1
    elif hard_flags["soft_leakage"]:
        scores["implicitness"] = 3
    else:
        scores["implicitness"] = 5

    if has_zh_core_mapping:
        scores["mapping_clarity"] = 4
    elif mapped_role_count >= 5:
        scores["mapping_clarity"] = 4
    elif mapped_role_count >= 3:
        scores["mapping_clarity"] = 3
    else:
        scores["mapping_clarity"] = 2

    if token_count < 120 or token_count > 1200:
        scores["readability"] = 3
    if token_count < 60:
        scores["readability"] = 2

    if scores["mapping_clarity"] <= 2:
        scores["faithfulness"] = min(scores["faithfulness"], 3)
        scores["pedagogical_value"] = min(scores["pedagogical_value"], 2)
    elif missing_roles:
        scores["faithfulness"] = min(scores["faithfulness"], 3)
        scores["pedagogical_value"] = min(scores["pedagogical_value"], 3)

    if hard_flags["template_like"]:
        scores["novelty"] = 2
    elif template_hits:
        scores["novelty"] = 3

    rationales = {
        "faithfulness": "\u89c4\u5219\u5c42\u6309\u6620\u5c04\u8986\u76d6\u5ea6\u7ed9\u51fa\u4fdd\u5b88\u4f30\u8ba1\uff1b\u79d1\u5b66\u6027\u4ecd\u5efa\u8bae\u4f7f\u7528 LLM judge \u6216\u4eba\u5de5\u590d\u6838\u3002",
        "implicitness": "\u68c0\u67e5\u6545\u4e8b\u6b63\u6587\u548c\u6807\u9898\u662f\u5426\u76f4\u63a5\u51fa\u73b0\u76ee\u6807\u6982\u5ff5\u540d\u3001\u522b\u540d\u6216\u5f3a\u672f\u8bed\u7ebf\u7d22\u3002",
        "mapping_clarity": "\u4f9d\u636e alignment_table / structure_plan \u4e2d\u6982\u5ff5\u89d2\u8272\u8986\u76d6\u60c5\u51b5\u4f30\u8ba1\u6620\u5c04\u6e05\u6670\u5ea6\u3002",
        "readability": "\u4f9d\u636e\u6b63\u6587\u957f\u5ea6\u548c\u57fa\u672c\u7ed3\u6784\u505a\u8f7b\u91cf\u4f30\u8ba1\u3002",
        "pedagogical_value": "\u4f9d\u636e\u6838\u5fc3\u6620\u5c04\u8986\u76d6\u5ea6\u505a\u8f7b\u91cf\u4f30\u8ba1\u3002",
        "novelty": "\u4f9d\u636e\u5e38\u89c1\u6a21\u677f\u77ed\u8bed\u548c\u540c\u6279\u6b21\u76f8\u4f3c\u5ea6\u505a\u8f7b\u91cf\u4f30\u8ba1\u3002",
    }
    suggestions: list[str] = []
    if leaked_terms:
        suggestions.append(
            "\u79fb\u9664\u5bd3\u8a00\u6b63\u6587\u4e2d\u7684\u76ee\u6807\u6982\u5ff5\u540d\u6216\u522b\u540d\uff0c\u6539\u7528\u6545\u4e8b\u4e8b\u4ef6\u9690\u542b\u8868\u8fbe\u3002"
        )
    if missing_roles:
        suggestions.append(
            "\u8865\u5168\u6838\u5fc3\u6982\u5ff5\u89d2\u8272\u5230\u6545\u4e8b\u4e8b\u4ef6\u7684\u6620\u5c04\uff0c\u5c24\u5176\u662f\u56e0\u679c\u94fe\u3001\u7ed3\u679c\u548c\u9a8c\u8bc1\u8fc7\u7a0b\u3002"
        )
    if hard_flags["template_like"]:
        suggestions.append(
            "\u66f4\u6362\u5e38\u89c1\u5bd3\u8a00\u6a21\u677f\uff0c\u4f7f\u7528\u66f4\u5177\u4f53\u3001\u5c11\u89c1\u7684\u573a\u666f\u548c\u51b2\u7a81\u3002"
        )

    findings = {
        "story_token_count": token_count,
        "leaked_terms": leaked_terms,
        "title_leaks": title_leaks,
        "soft_leakage_terms": soft_terms,
        "alignment_roles_present": roles,
        "missing_alignment_roles": missing_roles,
        "template_hits": template_hits,
        "template_similarity": round(peer_similarity, 4),
    }
    return scores, hard_flags, rationales, suggestions, findings
