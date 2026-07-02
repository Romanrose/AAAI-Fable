from __future__ import annotations

from typing import Any


def _section_to_lines(title: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return f"{title}:\n- None"
    lines = [f"{title}:"]
    for item in items:
        line = f"- {item['name']}"
        if item.get("definition"):
            line += f": {item['definition']}"
        lines.append(line)
    return "\n".join(lines)


def build_teaching_prompt(pack: dict[str, Any]) -> str:
    if not pack.get("found") or not pack.get("seed"):
        return "No concept was found. Ask the retriever for a valid concept first."

    seed = pack["seed"]
    sections = pack.get("sections", {})
    blocks = [
        "You are an educational explanation assistant.",
        "Explain the target concept clearly using only the retrieved graph-grounded context.",
        "Do not invent facts outside the provided context.",
        "",
        f"Target Concept: {seed['name']}",
        f"Definition: {seed.get('definition') or 'N/A'}",
        f"Importance: {seed.get('importance') or 'N/A'}",
        _section_to_lines("Prerequisites", sections.get("prerequisites", [])),
        _section_to_lines("Related Concepts", sections.get("related_concepts", [])),
        _section_to_lines("Downstream Outcomes", sections.get("outcomes", [])),
        _section_to_lines("Experiments", sections.get("experiments", [])),
        _section_to_lines("Exercises", sections.get("exercises", [])),
        "",
        "Write a concise educational explanation in 3 parts:",
        "1. Core idea",
        "2. How it connects to nearby concepts",
        "3. One concrete example or application",
    ]
    return "\n".join(blocks)


def build_mapping_prompt(pack: dict[str, Any]) -> str:
    if not pack.get("found") or not pack.get("seed"):
        return "No concept was found. Ask the retriever for a valid concept first."

    seed = pack["seed"]
    sections = pack.get("sections", {})
    blocks = [
        "You are a structure-mapping planner for concept-to-story generation.",
        "Use only the retrieved graph-grounded information.",
        "Transform the concept neighborhood into a story skeleton that can later support fable generation.",
        "",
        f"Target Concept: {seed['name']}",
        f"Definition: {seed.get('definition') or 'N/A'}",
        _section_to_lines("Prerequisites", sections.get("prerequisites", [])),
        _section_to_lines("Related Concepts", sections.get("related_concepts", [])),
        _section_to_lines("Downstream Outcomes", sections.get("outcomes", [])),
        "",
        "Produce:",
        "- source_domain",
        "- entities",
        "- event_chain",
        "- conflict",
        "- turning_point",
        "- resolution_state",
        "- concept_to_story_alignment",
        "",
        "The output should preserve the concept mechanism and remain suitable for later fable generation.",
    ]
    return "\n".join(blocks)
