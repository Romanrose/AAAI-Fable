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


def _pick(options: list[str], seed: int, offset: int = 0) -> str:
    return options[(seed + offset) % len(options)]


def _clean_event_text(event: str) -> str:
    prefixes = (
        "\u7528\u6545\u4e8b\u4e8b\u4ef6\u9690\u542b\u8868\u8fbe\uff1a",
        "\u7528\u6545\u4e8b\u4e8b\u4ef6\u9690\u542b\u8868\u8fbe:",
    )
    cleaned = event.strip()
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned or "\u524d\u540e\u6761\u4ef6\u4e4b\u95f4\u5b58\u5728\u53ef\u8ffd\u8e2a\u7684\u5173\u7cfb"


def _event_sentence(event: str, *, seed: int, index: int, protagonist: str, marker: str, motif: str) -> str:
    clue = _clean_event_text(event)
    templates = [
        f"{protagonist}\u5728{marker}\u89d2\u4e0a\u753b\u4e0b{motif}\uff0c\u56e0\u4e3a\u8fd9\u6761\u7ebf\u7d22\u6307\u5411\uff1a{clue}\u3002",
        f"\u7b2c{index + 1}\u6b21\u590d\u67e5\u65f6\uff0c{motif}\u65c1\u7684\u75d5\u8ff9\u63d0\u9192\u4ed6\uff1a{clue}\u3002",
        f"\u4ed6\u6ca1\u628a{motif}\u5f53\u4f5c\u88c5\u9970\uff0c\u800c\u662f\u7528\u5b83\u6807\u51fa\u4e00\u6bb5\u5fc5\u987b\u4fdd\u7559\u7684\u987a\u5e8f\uff1a{clue}\u3002",
        f"{marker}\u4e0a\u7684{motif}\u88ab\u79fb\u5230\u53e6\u4e00\u884c\u540e\uff0c\u4ed6\u770b\u51fa\u540c\u4e00\u6761\u9690\u7ebf\u4ecd\u7136\u901a\u5411\uff1a{clue}\u3002",
        f"\u5f53\u65c1\u4eba\u53ea\u770b\u89c1\u8868\u9762\u8ff9\u8c61\u65f6\uff0c{protagonist}\u6307\u7740{motif}\u8bf4\uff0c\u5148\u522b\u8df3\u8fc7\u8fd9\u4e00\u6bb5\uff1a{clue}\u3002",
    ]
    return _pick(templates, seed, index)


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
    seed = sum(ord(ch) for ch in str(card.get("concept_id", "")))
    variants = [
        ("\u8bb0\u5f55\u5458", "\u6728\u724c", "\u95e8\u5eca"),
        ("\u5b66\u5f92", "\u94dc\u724c", "\u68da\u67b6"),
        ("\u5de1\u67e5\u5458", "\u7eb8\u5e26", "\u957f\u684c"),
        ("\u5c0f\u5de5\u5320", "\u77f3\u724c", "\u4ed3\u95e8"),
        ("\u5b88\u5e93\u4eba", "\u7af9\u7b7e", "\u56de\u5eca"),
        ("\u4fe1\u53f7\u5458", "\u706f\u76d2", "\u7a97\u53f0"),
        ("\u8bd5\u8f66\u5458", "\u7ebf\u8f74", "\u5c0f\u8f68\u9053"),
        ("\u8c03\u5f26\u5e08", "\u58a8\u683c", "\u5c4b\u89d2"),
    ]
    variant = variants[seed % len(variants)]
    protagonist, marker, place = variant
    motif = _pick(
        [
            "\u84dd\u8272\u8721\u70b9",
            "\u65b9\u5f62\u7f3a\u53e3",
            "\u4e09\u9053\u659c\u7eb9",
            "\u7ec6\u94f6\u7ebf",
            "\u6d45\u7eff\u5370\u8bb0",
            "\u534a\u5708\u58a8\u75d5",
            "\u7c73\u7c92\u5927\u7684\u51f9\u70b9",
            "\u6de1\u9ec4\u7eb8\u89d2",
            "\u53cc\u5c42\u7ed3\u7ef3",
            "\u77ed\u77ed\u7684\u7ea2\u7ebf",
        ],
        seed,
    )
    openings = [
        f"{domain}\u7684{place}\u8fb9\u7ecf\u5e38\u51fa\u73b0\u4ee4\u4eba\u6478\u4e0d\u7740\u5934\u8111\u7684\u53d8\u5316\uff0c\u5e74\u8f7b\u7684{protagonist}\u51b3\u5b9a\u628a\u5b83\u8ffd\u67e5\u5230\u5e95\u3002",
        f"{protagonist}\u521a\u5230{domain}\u65f6\uff0c\u53ea\u76ef\u7740{place}\u91cc\u6700\u663e\u773c\u7684\u7ed3\u679c\uff0c\u5374\u603b\u662f\u5224\u65ad\u5931\u51c6\u3002",
        f"{domain}\u7684{place}\u6709\u4e00\u5957\u4e0d\u5199\u5728\u5899\u4e0a\u7684\u89c4\u77e9\uff0c{protagonist}\u8d77\u521d\u4ee5\u4e3a\u51ed\u76f4\u89c9\u5c31\u80fd\u770b\u61c2\u3002",
        f"\u6bcf\u5230\u65e5\u843d\uff0c{domain}\u7684{place}\u90fd\u4f1a\u7559\u4e0b\u4e00\u4e32\u5947\u602a\u8ff9\u8c61\uff0c{protagonist}\u628a\u5b83\u4eec\u6536\u8fdb{marker}\u91cc\u9010\u4e00\u5bf9\u7167\u3002",
    ]
    prereq_options = [
        "\u4ed6\u5148\u67e5\u770b\u524d\u9762\u51e0\u9053\u95e8\u69db\u662f\u5426\u90fd\u5df2\u5230\u4f4d\u3002",
        "\u4ed6\u628a\u8d77\u70b9\u5904\u7684\u6750\u6599\u3001\u65f6\u673a\u548c\u65b9\u5411\u5206\u522b\u7559\u4e0b\u6807\u8bb0\u3002",
        "\u4ed6\u6ca1\u6709\u7acb\u523b\u884c\u52a8\uff0c\u800c\u662f\u5148\u628a\u4f1a\u5f71\u54cd\u540e\u7eed\u7684\u5c0f\u6761\u4ef6\u6392\u6210\u4e00\u5217\u3002",
        "\u4ed6\u8981\u6c42\u81ea\u5df1\u5148\u6838\u5bf9\u7b2c\u4e00\u6b65\uff0c\u56e0\u4e3a\u6f0f\u6389\u5b83\u65f6\u540e\u9762\u7684\u8ff9\u8c61\u4f1a\u5168\u90e8\u53d8\u6837\u3002",
    ]
    related_options = [
        "\u9644\u8fd1\u51e0\u5904\u76f8\u4f3c\u5de5\u4f4d\u4e5f\u6709\u56de\u54cd\uff0c\u4f46\u54cd\u5e94\u7684\u5148\u540e\u5e76\u4e0d\u5b8c\u5168\u4e00\u6837\u3002",
        "\u65c1\u8fb9\u7684\u51e0\u4ef6\u4e8b\u770b\u4f3c\u76f8\u8fd1\uff0c\u4ed6\u5374\u5728{marker}\u4e0a\u7528\u4e0d\u540c\u7b26\u53f7\u533a\u5206\u3002",
        "\u4e00\u4e2a\u76f8\u90bb\u8bbe\u5907\u7ed9\u51fa\u4e86\u5bf9\u7167\uff1a\u5916\u8868\u5dee\u4e0d\u591a\uff0c\u5185\u91cc\u7684\u987a\u5e8f\u5374\u53e6\u6709\u5dee\u522b\u3002",
        "\u4ed6\u6ca1\u628a\u5468\u56f4\u7684\u76f8\u4f3c\u73b0\u8c61\u6df7\u5728\u4e00\u8d77\uff0c\u800c\u662f\u5148\u627e\u5171\u540c\u70b9\uff0c\u518d\u627e\u5dee\u5f02\u70b9\u3002",
    ]
    outcome_options = [
        "\u7ed3\u679c\u7b2c\u4e8c\u6b21\u51fa\u73b0\u65f6\uff0c\u4ed6\u624d\u786e\u8ba4\u4e0d\u662f\u5076\u7136\u7684\u5de7\u5408\u3002",
        "\u540e\u6765\u7684\u75d5\u8ff9\u4e0e\u4ed6\u7684\u8bb0\u5f55\u5bf9\u4e0a\u4e86\uff0c\u539f\u6765\u53d8\u5316\u5e76\u975e\u968f\u610f\u800c\u6765\u3002",
        "\u5f53\u540c\u6837\u7684\u987a\u5e8f\u518d\u6b21\u5e26\u6765\u76f8\u8fd1\u7684\u7ed3\u679c\uff0c\u4ed6\u624d\u6562\u5728\u65c1\u8fb9\u753b\u4e0b\u5c0f\u5708\u3002",
        "\u6700\u672b\u90a3\u4e2a\u53d8\u5316\u6ca1\u6709\u7a81\u7136\u964d\u4e34\uff0c\u800c\u662f\u6cbf\u7740\u524d\u9762\u7684\u8def\u5f84\u6162\u6162\u663e\u5f62\u3002",
    ]
    experiment_options = [
        "\u4e3a\u4e86\u786e\u8ba4\uff0c\u4ed6\u6084\u6084\u62bd\u8d70\u5176\u4e2d\u4e00\u679a\u6807\u8bb0\uff0c\u518d\u89c2\u5bdf\u540e\u9762\u54ea\u4e00\u73af\u5f00\u59cb\u504f\u79bb\u3002",
        "\u4ed6\u628a\u540c\u4e00\u5957\u987a\u5e8f\u6362\u5230\u53e6\u4e00\u5904\u89d2\u843d\uff0c\u770b\u5b83\u662f\u5426\u4ecd\u80fd\u7559\u4e0b\u76f8\u8fd1\u8ff9\u8c61\u3002",
        "\u4ed6\u7279\u610f\u5ef6\u540e\u4e00\u4e2a\u5c0f\u6b65\u9aa4\uff0c\u5e76\u628a\u524d\u540e\u4e24\u6b21\u7ed3\u679c\u653e\u5728\u4e00\u8d77\u6bd4\u5bf9\u3002",
        "\u4ed6\u8bf7\u540c\u4f34\u91cd\u590d\u4e00\u904d\u8bb0\u5f55\uff0c\u81ea\u5df1\u53ea\u5728\u8fb9\u4e0a\u68c0\u67e5\u54ea\u4e9b\u73af\u8282\u4e0d\u80fd\u4e22\u3002",
    ]
    closing_options = [
        f"\u4ece\u90a3\u4ee5\u540e\uff0c{protagonist}\u6bcf\u9047\u5230\u65b0\u8ff9\u8c61\uff0c\u90fd\u5148\u753b\u51fa\u8d77\u70b9\uff0c\u518d\u6cbf\u7740\u7ebf\u7d22\u8ffd\u5230\u7ed3\u5c3e\u3002",
        f"{protagonist}\u628a{marker}\u6536\u597d\uff0c\u5b66\u4f1a\u4e86\u7528\u8def\u5f84\u800c\u4e0d\u662f\u5370\u8c61\u5224\u65ad\u4e8b\u60c5\u3002",
        f"\u540e\u6765\uff0c{protagonist}\u4e0d\u6025\u7740\u7ed9\u7ed3\u679c\u8d77\u540d\uff0c\u800c\u662f\u5148\u95ee\uff1a\u5b83\u662f\u600e\u6837\u4e00\u6b65\u6b65\u8d70\u5230\u8fd9\u91cc\u7684\uff1f",
        f"\u65b0\u6765\u7684\u4eba\u8bf7\u6559\u65f6\uff0c{protagonist}\u53ea\u628a{marker}\u63a8\u8fc7\u53bb\uff0c\u8ba9\u5bf9\u65b9\u6309\u987a\u5e8f\u81ea\u5df1\u67e5\u770b\u3002",
    ]
    prereq_hint = _pick(prereq_options, seed, 1)
    related_hint = _pick(related_options, seed, 2) if related else _pick(related_options, seed, 5)
    outcome_hint = _pick(outcome_options, seed, 3) if outcomes else _pick(outcome_options, seed, 6)
    experiment_hint = _pick(experiment_options, seed, 4) if experiments else _pick(experiment_options, seed, 7)
    body_parts = [
        f"\u6807\u9898\uff1a{_pick(['\u6697\u683c\u91cc\u7684\u987a\u5e8f', '\u56de\u5eca\u4e0a\u7684\u8bb0\u53f7', '\u6162\u6162\u663e\u5f62\u7684\u8def', '\u4e0d\u4f1a\u8bf4\u8bdd\u7684\u7ebf\u7d22'], seed)}",
        "",
        _pick(openings, seed),
        f"\u4e00\u5929\uff0c\u4ed6\u6ca1\u6709\u7acb\u523b\u4e0b\u7ed3\u8bba\uff0c\u800c\u662f\u628a\u6240\u89c1\u7684\u524d\u540e\u53d8\u5316\u5206\u6bb5\u5199\u5728{marker}\u4e0a\u3002{prereq_hint}{related_hint}",
    ]
    for index, event in enumerate(events[:3]):
        body_parts.append(_event_sentence(str(event), seed=seed, index=index, protagonist=protagonist, marker=marker, motif=motif))
    body_parts.append(f"{experiment_hint}{outcome_hint}{_pick(closing_options, seed, 8)}")
    alignment = [
        {
            "concept_role": "target concept",
            "story_evidence": "\u6545\u4e8b\u7528\u9690\u85cf\u89c4\u5219\u548c\u8fde\u7eed\u53d8\u5316\u6765\u5bf9\u5e94\u76ee\u6807\u6982\u5ff5\u3002",
        },
        {
            "concept_role": "core mechanism",
            "story_evidence": f"\u524d\u540e\u53d8\u5316\u88ab{protagonist}\u6309\u987a\u5e8f\u8bb0\u5f55\u3001\u6539\u52a8\u548c\u590d\u67e5\u3002",
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
