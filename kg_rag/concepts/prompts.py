from __future__ import annotations

import json
from typing import Any


ENRICH_SYSTEM_PROMPT = "You enrich K12 concept cards. Return strict JSON only."
STORY_SYSTEM_PROMPT = "You write concise Simplified Chinese educational fables. Return the requested text only."


def build_enrichment_prompt(card: dict[str, Any]) -> str:
    payload = {
        "task": "Enrich this K12 concept card for Simplified Chinese fable generation. Return strict JSON only.",
        "language": "zh-CN",
        "requirements": [
            "All values in *_zh fields must be natural Simplified Chinese.",
            "Do not write a story.",
            "Do not drop forbidden_terms_zh.",
            "If the source text is uncertain, lower enrichment_confidence.",
        ],
        "required_schema": {
            "concept_type": "definition | mechanism | process | entity | relation | method | law | theorem",
            "core_mechanism_zh": ["..."],
            "must_preserve_zh": ["..."],
            "common_misconceptions_zh": ["..."],
            "subject_constraints_zh": ["..."],
            "generation_notes_zh": ["..."],
            "enrichment_confidence": 0.0,
        },
        "concept_card": card,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_chinese_structure_plan(card: dict[str, Any]) -> dict[str, Any]:
    subject = card.get("subject")
    domains = {
        "biology": "\u56ed\u5703\u5de5\u574a",
        "chemistry": "\u57ce\u90a6\u8d26\u623f",
        "physics": "\u949f\u697c\u4ea4\u901a\u7ad9",
        "math": "\u89c4\u5219\u8c1c\u57ce",
    }
    source_domain = domains.get(subject, "\u5c0f\u9547\u5de5\u574a")
    core = card.get("core_mechanism_zh") or card.get("must_preserve_zh") or [card.get("definition") or card.get("canonical_name")]
    event_chain = [f"\u7528\u6545\u4e8b\u4e8b\u4ef6\u9690\u542b\u8868\u8fbe\uff1a{item}" for item in core[:4] if item]
    if not event_chain:
        event_chain = [
            "\u4e3b\u89d2\u8fdb\u5165\u4e00\u4e2a\u6709\u660e\u786e\u89c4\u5219\u7684\u60c5\u5883\u3002",
            "\u4e3b\u89d2\u901a\u8fc7\u884c\u52a8\u53d1\u73b0\u9690\u85cf\u7684\u6761\u4ef6\u548c\u5173\u7cfb\u3002",
            "\u7ed3\u679c\u8bc1\u660e\u8fd9\u4e9b\u6761\u4ef6\u5fc5\u987b\u534f\u540c\u6210\u7acb\u3002",
        ]
    return {
        "found": True,
        "query": card["concept_id"],
        "concept_id": card["concept_id"],
        "story_language": "zh-CN",
        "seed": {
            "id": card["concept_id"],
            "label": "Concept",
            "name": card.get("canonical_name"),
            "definition": card.get("definition"),
            "aliases": card.get("aliases", []),
            "examples": card.get("examples", []),
        },
        "source_domain": source_domain,
        "entities": [
            "\u8d1f\u8d23\u89c2\u5bdf\u89c4\u5219\u7684\u4e3b\u89d2",
            "\u4e00\u4e2a\u9700\u8981\u6309\u6761\u4ef6\u8fd0\u8f6c\u7684\u573a\u6240",
            "\u7528\u6765\u663e\u793a\u53d8\u5316\u7684\u7269\u4ef6\u6216\u884c\u52a8",
        ],
        "event_chain": event_chain,
        "conflict": "\u8868\u9762\u73b0\u8c61\u5bb9\u6613\u8bef\u5bfc\u4e3b\u89d2\uff0c\u771f\u6b63\u7684\u89c4\u5219\u9700\u8981\u901a\u8fc7\u8fde\u7eed\u4e8b\u4ef6\u624d\u80fd\u88ab\u770b\u89c1\u3002",
        "turning_point": "\u4e00\u6b21\u5177\u4f53\u89c2\u5bdf\u6216\u68c0\u9a8c\u8ba9\u4e3b\u89d2\u53d1\u73b0\u5173\u952e\u5173\u7cfb\u3002",
        "resolution_state": "\u4e3b\u89d2\u7528\u65b0\u7684\u89c4\u5219\u91cd\u65b0\u7406\u89e3\u6574\u4e2a\u60c5\u5883\uff0c\u5e76\u80fd\u5224\u65ad\u7c7b\u4f3c\u60c5\u51b5\u3002",
        "alignment_plan": [
            {
                "concept_role": "\u76ee\u6807\u6982\u5ff5",
                "concept_items": [card.get("canonical_name")],
                "story_role": "\u6545\u4e8b\u4e2d\u9690\u542b\u7684\u6838\u5fc3\u89c4\u5219",
            },
            {
                "concept_role": "\u6838\u5fc3\u673a\u5236",
                "concept_items": core[:5],
                "story_role": "\u4e3b\u8981\u4e8b\u4ef6\u94fe\u548c\u8f6c\u6298",
            },
            {
                "concept_role": "\u5b66\u79d1\u7ea6\u675f",
                "concept_items": card.get("subject_constraints_zh", [])[:5],
                "story_role": "\u907f\u514d\u8bef\u5bfc\u6027\u7c7b\u6bd4\u7684\u5199\u4f5c\u7ea6\u675f",
            },
        ],
    }


def build_chinese_story_prompt(card: dict[str, Any], plan: dict[str, Any]) -> str:
    payload = {
        "task": "Write one Simplified Chinese fable for the target concept.",
        "language": "zh-CN",
        "hard_requirements": [
            "The story body must be Simplified Chinese.",
            "Do not directly mention the target concept name or forbidden terms in the story body.",
            "Do not write an expository science explanation.",
            "Preserve the concept mechanism and the subject constraints.",
            "Use 450-800 Chinese characters for the story body.",
            "After the story, output one JSON alignment table fenced in ```json.",
        ],
        "forbidden_terms_zh": card.get("forbidden_terms_zh", []),
        "concept_card": card,
        "structure_plan": plan,
        "output_format": "\u6807\u9898\uff1a...\n\n\u6545\u4e8b\u6b63\u6587...\n\n```json\n[{\"concept_role\":\"...\",\"story_evidence\":\"...\"}]\n```",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _mask_forbidden_terms(text: str, forbidden_terms: list[str]) -> str:
    masked = text
    for term in sorted((item for item in forbidden_terms if item), key=len, reverse=True):
        masked = masked.replace(term, "\u8fd9\u4e00\u9690\u85cf\u89c4\u5219")
    return masked


def _names_from_context(items: list[dict[str, Any]] | None, *, limit: int = 3) -> list[str]:
    names: list[str] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("id")
        if name:
            names.append(str(name))
        if len(names) >= limit:
            break
    return names


def build_local_chinese_story(card: dict[str, Any], plan: dict[str, Any]) -> str:
    name = card.get("canonical_name") or "\u76ee\u6807\u6982\u5ff5"
    domain = plan.get("source_domain") or "\u5c0f\u9547"
    forbidden_terms = [str(item) for item in card.get("forbidden_terms_zh", []) if item]
    events = [_mask_forbidden_terms(str(item), forbidden_terms) for item in plan.get("event_chain", [])]
    context = card.get("graph_context", {})
    prerequisites = _names_from_context(context.get("prerequisites"))
    related = _names_from_context(context.get("related_concepts"))
    outcomes = _names_from_context(context.get("outcomes"))
    experiments = _names_from_context(context.get("experiments"), limit=2)
    exercises = _names_from_context(context.get("exercises"), limit=2)
    variants = [
        ("\u8bb0\u5f55\u5458", "\u6728\u724c", "\u95e8\u5eca"),
        ("\u5b66\u5f92", "\u94dc\u724c", "\u68da\u67b6"),
        ("\u5de1\u67e5\u5458", "\u7eb8\u5e26", "\u957f\u684c"),
        ("\u5c0f\u5de5\u5320", "\u77f3\u724c", "\u4ed3\u95e8"),
    ]
    variant = variants[sum(ord(ch) for ch in str(card.get("concept_id", ""))) % len(variants)]
    protagonist, marker, place = variant
    prereq_hint = "\u4ed6\u5148\u786e\u8ba4\u5165\u53e3\u6761\u4ef6\u5df2\u7ecf\u51c6\u5907\u9f50\u5168\u3002" if prerequisites else "\u4ed6\u5148\u786e\u8ba4\u6bcf\u4e2a\u5165\u53e3\u6761\u4ef6\u90fd\u4e0d\u80fd\u88ab\u7701\u7565\u3002"
    related_hint = "\u65c1\u8fb9\u7684\u76f8\u90bb\u5de5\u4f4d\u4e5f\u51fa\u73b0\u7c7b\u4f3c\u79e9\u5e8f\u3002" if related else "\u65c1\u8fb9\u7684\u5de5\u4f4d\u4e0d\u65f6\u63d0\u9192\u4ed6\u533a\u5206\u76f8\u4f3c\u73b0\u8c61\u3002"
    outcome_hint = "\u6700\u540e\u7684\u53d8\u5316\u8bc1\u660e\u65e9\u5148\u7684\u5224\u65ad\u53ef\u4ee5\u88ab\u91cd\u590d\u9a8c\u8bc1\u3002" if outcomes else "\u6700\u540e\u7684\u53d8\u5316\u8ba9\u4ed6\u80fd\u9884\u5224\u4e0b\u4e00\u6b21\u7ed3\u679c\u3002"
    experiment_hint = "\u4ed6\u6545\u610f\u6539\u53d8\u5176\u4e2d\u4e00\u4e2a\u6761\u4ef6\uff0c\u518d\u6bd4\u5bf9\u524d\u540e\u5dee\u5f02\u3002" if experiments else "\u4ed6\u7559\u4e0b\u4e00\u6b21\u5c0f\u68c0\u67e5\uff0c\u770b\u8fd9\u5957\u987a\u5e8f\u662f\u5426\u4ecd\u7136\u6210\u7acb\u3002"
    body_parts = [
        f"\u6807\u9898\uff1a{domain}\u91cc\u7684\u9690\u85cf\u89c4\u5219",
        "",
        f"{domain}\u7684{place}\u8fb9\u6709\u4e00\u4f4d\u5e74\u8f7b\u7684{protagonist}\uff0c\u4ed6\u603b\u89c9\u5f97\u773c\u524d\u7684\u53d8\u5316\u53ea\u662f\u5de7\u5408\u3002",
        f"\u4e00\u5929\uff0c\u4ed6\u628a\u6761\u4ef6\u3001\u884c\u52a8\u548c\u7ed3\u679c\u4e00\u4e00\u5199\u5728{marker}\u4e0a\u3002{prereq_hint}{related_hint}",
    ]
    for event in events[:3]:
        body_parts.append(str(event))
    body_parts.append(
        f"{experiment_hint}{outcome_hint}\u540e\u6765\uff0c{protagonist}\u4e0d\u518d\u53ea\u770b\u8868\u9762\u7ed3\u679c\uff0c\u800c\u662f\u5148\u627e\u6761\u4ef6\uff0c\u518d\u770b\u8fc7\u7a0b\uff0c\u6700\u540e\u68c0\u67e5\u7ed3\u679c\u662f\u5426\u80fd\u91cd\u590d\u51fa\u73b0\u3002"
    )
    alignment = [
        {
            "concept_role": "target concept",
            "story_evidence": "\u6545\u4e8b\u7528\u9690\u85cf\u89c4\u5219\u548c\u8fde\u7eed\u53d8\u5316\u6765\u5bf9\u5e94\u76ee\u6807\u6982\u5ff5\u3002",
        },
        {
            "concept_role": "core mechanism",
            "story_evidence": "\u6761\u4ef6\u3001\u8fc7\u7a0b\u548c\u7ed3\u679c\u88ab\u8bb0\u5f55\u5458\u6309\u987a\u5e8f\u68c0\u67e5\u3002",
        },
        {
            "concept_role": "prerequisites",
            "concept_items": prerequisites,
            "story_evidence": prereq_hint,
        },
        {
            "concept_role": "related concepts",
            "concept_items": related,
            "story_evidence": related_hint,
        },
        {
            "concept_role": "outcomes",
            "concept_items": outcomes,
            "story_evidence": outcome_hint,
        },
        {
            "concept_role": "experiments",
            "concept_items": experiments,
            "story_evidence": experiment_hint,
        },
        {
            "concept_role": "exercises",
            "concept_items": exercises,
            "story_evidence": "\u6545\u4e8b\u7ed3\u5c3e\u4fdd\u7559\u4e86\u53ef\u590d\u67e5\u3001\u53ef\u8fc1\u79fb\u7684\u5224\u65ad\u4efb\u52a1\u3002",
        },
    ]
    # The target name is intentionally kept out of the story body, but allowed in this metadata table.
    alignment[0]["concept_items"] = [name]
    return "\n".join(body_parts) + "\n\n```json\n" + json.dumps(alignment, ensure_ascii=False, indent=2) + "\n```"
