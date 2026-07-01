from __future__ import annotations

import json
import re
from typing import Any


def _extract_alignment_table(draft_story: str) -> list[dict[str, Any]]:
    match = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", draft_story, flags=re.IGNORECASE)
    if not match:
        return []
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _story_body_only(draft_story: str) -> str:
    return draft_story.split("**Alignment Table:**", 1)[0].strip()


def build_review_checklist(plan: dict[str, Any], draft_story: str) -> dict[str, Any]:
    if not plan.get("found") or not plan.get("seed"):
        return {
            "pass_fail": False,
            "reason": "missing_structure_plan",
        }

    alignment_rows = _extract_alignment_table(draft_story)
    alignment_roles_present = {
        str(item.get("concept_role")).strip().casefold()
        for item in alignment_rows
        if item.get("concept_role")
    }

    missing_roles: list[str] = []
    draft_lower = draft_story.casefold()
    for item in plan.get("alignment_plan", []):
        concept_role = item.get("concept_role")
        concept_items = item.get("concept_items", [])
        if not concept_role:
            continue
        role_key = str(concept_role).casefold()
        if role_key in alignment_roles_present:
            continue
        if concept_items and any(str(value).casefold() in draft_lower for value in concept_items):
            continue
        missing_roles.append(concept_role)

    body = _story_body_only(draft_story)
    body_length = len(body.split())

    return {
        "pass_fail": len(missing_roles) == 0 and bool(body.strip()),
        "missing_roles": missing_roles,
        "draft_length": body_length,
        "alignment_roles_present": sorted(alignment_roles_present),
        "seed_concept": plan["seed"]["name"],
    }
