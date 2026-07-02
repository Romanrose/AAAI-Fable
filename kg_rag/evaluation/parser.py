from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from kg_rag.io import read_json
from kg_rag.text_cleaning import clean_value


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", stripped)
        if not match:
            raise ValueError("Evaluator output did not contain a JSON object.")
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Evaluator output JSON must be an object.")
    return payload


def extract_alignment_table(draft_story: str, structure_plan: dict[str, Any]) -> list[dict[str, Any]]:
    fenced_matches = re.findall(r"```(?:json)?\s*([\s\S]*?)```", draft_story, flags=re.IGNORECASE)
    for block in fenced_matches:
        try:
            payload = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
            return payload

    alignment = structure_plan.get("alignment_plan", [])
    if isinstance(alignment, list):
        return [item for item in alignment if isinstance(item, dict)]
    return []


def strip_alignment_from_story(draft_story: str) -> str:
    return re.sub(r"```(?:json)?\s*[\s\S]*?```", "", draft_story, flags=re.IGNORECASE).strip()


def build_evaluation_input_from_dir(story_dir: Path):
    from kg_rag.evaluation.rubric import EvaluationInput

    pack_path = story_dir / "subgraph_pack.json"
    plan_path = story_dir / "structure_plan.json"
    draft_path = story_dir / "draft_story.txt"
    missing = [path.name for path in (pack_path, plan_path, draft_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"{story_dir} is missing required files: {', '.join(missing)}")

    subgraph_pack = clean_value(read_json(pack_path))
    structure_plan = clean_value(read_json(plan_path))
    draft_story = draft_path.read_text(encoding="utf-8")

    seed = subgraph_pack.get("seed", {}) if isinstance(subgraph_pack, dict) else {}
    concept_id = str(seed.get("id") or structure_plan.get("query") or story_dir.name)
    target_concept = str(seed.get("name") or concept_id)
    concept_definition = str(seed.get("definition") or "")
    aliases = seed.get("aliases") if isinstance(seed.get("aliases"), list) else []
    forbidden_terms = sorted({term for term in [target_concept, concept_id, *aliases] if isinstance(term, str) and term})

    return EvaluationInput(
        concept_id=concept_id,
        target_concept=target_concept,
        concept_definition=concept_definition,
        subgraph_pack=subgraph_pack,
        structure_plan=structure_plan,
        draft_story=draft_story,
        alignment_table=extract_alignment_table(draft_story, structure_plan),
        forbidden_terms=forbidden_terms,
    )

