from __future__ import annotations

from typing import Any


def _names(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    return [item["name"] for item in items[:limit]]


def build_structure_plan(pack: dict[str, Any]) -> dict[str, Any]:
    if not pack.get("found") or not pack.get("seed"):
        return {
            "found": False,
            "query": pack.get("query"),
            "seed": None,
            "source_domain": None,
            "entities": [],
            "event_chain": [],
            "conflict": None,
            "turning_point": None,
            "resolution_state": None,
            "alignment_plan": [],
        }

    seed = pack["seed"]
    sections = pack.get("sections", {})
    prereqs = sections.get("prerequisites", [])
    related = sections.get("related_concepts", [])
    outcomes = sections.get("outcomes", [])
    experiments = sections.get("experiments", [])
    exercises = sections.get("exercises", [])

    source_domain = "garden workshop"
    entities = [
        "a careful caretaker",
        "a plot that depends on the right conditions",
        "tools and routines that reveal whether growth is real",
    ]

    event_chain = [
        "The caretaker prepares the conditions that must already be in place.",
        "The plot uses those conditions to produce visible growth.",
        "Nearby processes either support or compete with that growth.",
        "Observation and trials reveal whether the growth is genuine and sustained.",
    ]

    conflict = "The central process cannot succeed unless the hidden prerequisites are present and correctly coordinated."
    turning_point = (
        "A concrete test or observation reveals which condition actually controls the outcome."
        if experiments
        else "A visible change reveals which condition actually controls the outcome."
    )
    resolution_state = "The system stabilizes once the enabling conditions are understood and the resulting effects become observable."

    alignment_plan = [
        {
            "concept_role": "target concept",
            "concept_items": [seed["name"]],
            "story_role": "central productive process",
        },
        {
            "concept_role": "prerequisites",
            "concept_items": _names(prereqs),
            "story_role": "conditions or resources that must be prepared first",
        },
        {
            "concept_role": "related concepts",
            "concept_items": _names(related),
            "story_role": "neighboring processes that contextualize or contrast the main process",
        },
        {
            "concept_role": "outcomes",
            "concept_items": _names(outcomes),
            "story_role": "visible consequences produced by the core process",
        },
        {
            "concept_role": "experiments",
            "concept_items": _names(experiments),
            "story_role": "tests that reveal whether the process truly happened",
        },
        {
            "concept_role": "exercises",
            "concept_items": _names(exercises),
            "story_role": "follow-up checks that reinforce the lesson",
        },
    ]

    return {
        "found": True,
        "query": pack.get("query"),
        "seed": seed,
        "source_domain": source_domain,
        "entities": entities,
        "event_chain": event_chain,
        "conflict": conflict,
        "turning_point": turning_point,
        "resolution_state": resolution_state,
        "alignment_plan": alignment_plan,
    }
