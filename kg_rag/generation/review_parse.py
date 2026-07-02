from __future__ import annotations

import json
import re
from typing import Any


def parse_review_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", stripped)
        if not match:
            raise ValueError("Reviewer output did not contain a JSON object.")
        payload = json.loads(match.group(0))

    if not isinstance(payload, dict):
        raise ValueError("Reviewer output JSON must be an object.")

    return {
        "pass_fail": bool(payload.get("pass_fail", False)),
        "missing_roles": list(payload.get("missing_roles", [])),
        "unsupported_story_parts": list(payload.get("unsupported_story_parts", [])),
        "coherence_issues": list(payload.get("coherence_issues", [])),
        "suggested_revision": list(payload.get("suggested_revision", [])),
    }
