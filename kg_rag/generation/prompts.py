from __future__ import annotations

from typing import Any


def _bullet_list(items: list[str], fallback: str = "None") -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def build_story_prompt(plan: dict[str, Any]) -> str:
    if not plan.get("found") or not plan.get("seed"):
        return "No valid structure plan was found. Build a structure plan first."

    seed = plan["seed"]
    alignment_lines = []
    for item in plan.get("alignment_plan", []):
        concept_items = ", ".join(item.get("concept_items", [])) or "None"
        alignment_lines.append(
            f"- Concept role: {item.get('concept_role')} | Concept items: {concept_items} | Story role: {item.get('story_role')}"
        )

    blocks = [
        "You are a fable-writing assistant.",
        "Write a short concept-grounded fable from the provided structure plan.",
        "Preserve the mechanism implied by the structure plan.",
        "Do not introduce unrelated subplots or excessive exposition.",
        "Do not collapse the target concept into a vague notion like general growth, improvement, or success.",
        "If an experiment role and an exercise role both exist, keep them distinct.",
        "The experiment should demonstrate or reveal the mechanism.",
        "The exercise should act as a follow-up check, question, or reinforcing task.",
        "",
        f"Target Concept: {seed['name']}",
        f"Definition: {seed.get('definition') or 'N/A'}",
        f"Source Domain: {plan.get('source_domain') or 'N/A'}",
        "Entities:",
        _bullet_list(plan.get("entities", [])),
        "Event Chain:",
        _bullet_list(plan.get("event_chain", [])),
        f"Conflict: {plan.get('conflict') or 'N/A'}",
        f"Turning Point: {plan.get('turning_point') or 'N/A'}",
        f"Resolution State: {plan.get('resolution_state') or 'N/A'}",
        "Concept-to-Story Alignment:",
        "\n".join(alignment_lines) if alignment_lines else "- None",
        "",
        "Write one concise story with:",
        "- 120 to 220 words",
        "- a clear beginning, development, and resolution",
        "- concrete actions instead of abstract explanation",
        "- explicit realization of the target concept mechanism, not just its broad effects",
        "- no bullet points in the story body",
        "",
        "After the story, output a short alignment table in JSON with fields:",
        '  [{"concept_role": "...", "story_evidence": "..."}]',
    ]
    return "\n".join(blocks)


def build_review_prompt(plan: dict[str, Any], draft_story: str) -> str:
    if not plan.get("found") or not plan.get("seed"):
        return "No valid structure plan was found. Build a structure plan first."

    seed = plan["seed"]
    alignment_roles = [item.get("concept_role") for item in plan.get("alignment_plan", [])]

    blocks = [
        "You are a strict reviewer for concept-grounded story generation.",
        "Evaluate whether the draft story preserves the intended concept structure.",
        "Focus on fidelity, coverage, coherence, and whether the story actually realizes the planned mapping.",
        "Reject stories that replace the target mechanism with a vague proxy such as generic growth or improvement.",
        "Check whether experiment and exercise are clearly distinct when both roles are expected.",
        "Return valid JSON only. Do not use markdown. Do not add prose outside the JSON object.",
        "",
        f"Target Concept: {seed['name']}",
        f"Definition: {seed.get('definition') or 'N/A'}",
        "Expected Alignment Roles:",
        _bullet_list([role for role in alignment_roles if role]),
        "",
        "Draft Story:",
        draft_story.strip() or "[EMPTY DRAFT]",
        "",
        "Return a JSON object with exactly these fields:",
        '{',
        '  "pass_fail": true,',
        '  "missing_roles": ["..."],',
        '  "unsupported_story_parts": ["..."],',
        '  "coherence_issues": ["..."],',
        '  "suggested_revision": ["..."]',
        '}',
    ]
    return "\n".join(blocks)
