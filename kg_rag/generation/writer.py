from __future__ import annotations

from typing import Any


def _pick(items: list[str], index: int, fallback: str) -> str:
    if 0 <= index < len(items):
        return items[index]
    return fallback


def build_heuristic_draft(plan: dict[str, Any]) -> str:
    if not plan.get("found") or not plan.get("seed"):
        return ""

    seed = plan["seed"]
    entities = plan.get("entities", [])
    event_chain = plan.get("event_chain", [])
    alignments = {item.get("concept_role"): item.get("concept_items", []) for item in plan.get("alignment_plan", [])}

    caretaker = _pick(entities, 0, "a careful caretaker")
    setting = _pick(entities, 1, "a delicate plot")
    tools = _pick(entities, 2, "simple tools")

    prereqs = alignments.get("prerequisites", [])
    related = alignments.get("related concepts", [])
    outcomes = alignments.get("outcomes", [])
    experiments = alignments.get("experiments", [])
    exercises = alignments.get("exercises", [])

    p1 = (
        f"In a {plan.get('source_domain', 'quiet workshop')}, {caretaker} watched over {setting}. "
        f"Before expecting anything from it, the caretaker prepared what had to be ready first: "
        f"{', '.join(prereqs[:3]) if prereqs else 'the right hidden conditions'}. "
        f"Only after that did the caretaker trust {tools} to help the work begin."
    )

    p2 = (
        f"As days passed, the central process behind {seed['name']} started to show itself through action rather than talk. "
        f"{_pick(event_chain, 1, 'The prepared setting began to change in a visible way.')} "
        f"Nearby influences such as {', '.join(related[:2]) if related else 'other surrounding processes'} "
        f"either supported the change or revealed what could not replace it."
    )

    p3 = (
        f"To settle doubt, the caretaker relied on {', '.join(experiments[:1]) if experiments else 'a simple visible test'}. "
        f"The result made the lesson plain: {', '.join(outcomes[:2]) if outcomes else 'the right conditions produce the right result'}. "
        f"Later, even follow-up checks like {', '.join(exercises[:1]) if exercises else 'small repeated trials'} "
        f"pointed back to the same truth."
    )

    return "\n\n".join([p1, p2, p3])
