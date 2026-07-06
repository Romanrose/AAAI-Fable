"""End-to-end retrieval, generation, persistence, and evaluation."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from evaluation.evaluate_automatic import (
    aggregate,
    evaluate_record,
    group_by_method,
    validate_record,
)

from .analysis import (
    MECHANISM_KINDS,
    build_heuristic_mechanism_plan,
    classify_step_kind,
    compute_retrieval_analysis,
    validate_mechanism_plan,
)
from .backends import DeepSeekBackend, FixtureBackend
from .retrieval import load_subject_graph, normalize, retrieve_subgraph


class PipelineError(ValueError):
    """Raised when model output violates the demo contract."""


MIN_NARRATIVE_CHARS = 90
MAX_NARRATIVE_CHARS = 260
GENERATION_REPAIR_ATTEMPTS = 2


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_strings(values: list[Any]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not _is_nonempty_string(value):
            continue
        text = str(value).strip()
        key = normalize(text)
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(text)
    return results


def _string_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _available_raw_edge_ids(subgraph: dict[str, Any]) -> list[str]:
    package = subgraph.get("retrieval_package", {})
    raw_edges = package.get("raw_edges", subgraph.get("edges", []))
    return [
        str(edge.get("source_edge_id"))
        for edge in raw_edges
        if isinstance(edge, dict) and _is_nonempty_string(edge.get("source_edge_id"))
    ]


def _available_path_ids(subgraph: dict[str, Any]) -> list[str]:
    package = subgraph.get("retrieval_package", {})
    selected_paths = package.get("selected_paths", subgraph.get("selected_paths", []))
    return [
        str(path.get("path_id"))
        for path in selected_paths
        if isinstance(path, dict) and _is_nonempty_string(path.get("path_id"))
    ]


def _topic_summary_texts(subgraph: dict[str, Any]) -> list[str]:
    package = subgraph.get("retrieval_package", {})
    summary = package.get("topic_summary", subgraph.get("topic_summary", {}))
    texts: list[str] = []
    if not isinstance(summary, dict):
        return texts
    for value in summary.values():
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, list):
            texts.extend(item for item in value if _is_nonempty_string(item))
    return _unique_strings(texts)


def _fallback_step_texts(subgraph: dict[str, Any]) -> list[str]:
    target_name = str(subgraph.get("target", {}).get("name", "")).strip() or "目标概念"
    return [
        f"{target_name}发生前需要满足的条件",
        f"{target_name}依赖的关键输入或组成",
        f"{target_name}的核心变化过程",
        f"{target_name}带来的直接结果",
        f"{target_name}的后续影响或应用",
    ]


def _infer_dependency_relation(source_kind: str, target_kind: str) -> str:
    if source_kind == "condition" and target_kind in {"condition", "process"}:
        return "prerequisites_for"
    if source_kind == "process" and target_kind in {"process", "effect"}:
        return "leads_to"
    if source_kind == "effect" and target_kind == "effect":
        return "relates_to"
    return "relates_to"


def _normalize_mechanism_plan(
    plan: Any, graph: Any, subgraph: dict[str, Any]
) -> dict[str, Any]:
    heuristic_plan = build_heuristic_mechanism_plan(subgraph)
    available_raw_edge_ids = set(_available_raw_edge_ids(subgraph))
    available_path_ids = set(_available_path_ids(subgraph))
    plan_steps = plan.get("steps", []) if isinstance(plan, dict) else []
    plan_dependencies = plan.get("dependencies", []) if isinstance(plan, dict) else []
    plan_is_usable = (
        isinstance(plan, dict)
        and not validate_mechanism_plan(plan, subgraph)
        and isinstance(plan_steps, list)
        and isinstance(plan_dependencies, list)
        and 4 <= len(plan_steps) <= 6
        and 3 <= len(plan_dependencies) <= 6
    )
    if plan_is_usable:
        supporting_edge_ids = [
            edge_id
            for edge_id in _unique_strings(_string_list(plan.get("supporting_edge_ids", [])))
            if edge_id in available_raw_edge_ids
        ]
        supporting_path_ids = [
            path_id
            for path_id in _unique_strings(_string_list(plan.get("supporting_path_ids", [])))
            if path_id in available_path_ids
        ]
        target = subgraph.get("target", {})
        target_aliases = target.get("properties", {}).get("aliases", [])
        forbidden_terms = _unique_strings(
            [
                target.get("name"),
                *(list(target_aliases) if isinstance(target_aliases, list) else []),
                *_string_list(plan.get("forbidden_terms", [])),
            ]
        )
        return {
            "core_question": (
                str(plan.get("core_question")).strip()
                if _is_nonempty_string(plan.get("core_question"))
                else heuristic_plan.get("core_question")
            ),
            "steps": deepcopy(plan_steps),
            "dependencies": deepcopy(plan_dependencies),
            "supporting_edge_ids": supporting_edge_ids,
            "supporting_path_ids": supporting_path_ids,
            "forbidden_terms": forbidden_terms,
            "coverage_targets": {
                "required_step_count": len(plan_steps),
                "required_dependency_count": len(plan_dependencies),
                "must_cover_path_ids": supporting_path_ids,
            },
        }

    step_candidates: list[tuple[str, str]] = []
    seen_step_texts: set[str] = set()

    def add_step(text: Any, kind: Any = None) -> None:
        if not _is_nonempty_string(text):
            return
        normalized_text = str(text).strip()
        key = normalize(normalized_text)
        if not key or key in seen_step_texts:
            return
        seen_step_texts.add(key)
        step_candidates.append(
            (
                normalized_text,
                str(kind) if kind in MECHANISM_KINDS else classify_step_kind(normalized_text),
            )
        )

    if isinstance(plan, dict):
        for step in plan.get("steps", []):
            if isinstance(step, dict):
                add_step(step.get("text"), step.get("kind"))
    for step in heuristic_plan.get("steps", []):
        if isinstance(step, dict):
            add_step(step.get("text"), step.get("kind"))
    if isinstance(graph, dict):
        for node in graph.get("nodes", []):
            if isinstance(node, dict):
                add_step(node.get("text"))
    for text in _topic_summary_texts(subgraph):
        add_step(text)
    for text in _fallback_step_texts(subgraph):
        add_step(text)

    steps_source = step_candidates[:6]
    if len(steps_source) < 4:
        for text in _fallback_step_texts(subgraph):
            add_step(text)
            if len(step_candidates) >= 4:
                break
        steps_source = step_candidates[:6]

    normalized_steps = [
        {
            "step_id": f"s{index}",
            "text": text,
            "kind": kind,
        }
        for index, (text, kind) in enumerate(steps_source, start=1)
    ]
    dependencies = [
        {
            "source_step_id": normalized_steps[index]["step_id"],
            "target_step_id": normalized_steps[index + 1]["step_id"],
            "relation": _infer_dependency_relation(
                normalized_steps[index]["kind"], normalized_steps[index + 1]["kind"]
            ),
        }
        for index in range(max(0, len(normalized_steps) - 1))
    ]

    supporting_edge_ids = _unique_strings(
        [
            *(
                plan.get("supporting_edge_ids", [])
                if isinstance(plan, dict) and isinstance(plan.get("supporting_edge_ids"), list)
                else []
            ),
            *heuristic_plan.get("supporting_edge_ids", []),
            *_available_raw_edge_ids(subgraph)[:6],
        ]
    )
    supporting_edge_ids = [
        edge_id for edge_id in supporting_edge_ids if edge_id in available_raw_edge_ids
    ]
    supporting_path_ids = _unique_strings(
        [
            *(
                plan.get("supporting_path_ids", [])
                if isinstance(plan, dict) and isinstance(plan.get("supporting_path_ids"), list)
                else []
            ),
            *heuristic_plan.get("supporting_path_ids", []),
            *_available_path_ids(subgraph)[:5],
        ]
    )
    supporting_path_ids = [
        path_id for path_id in supporting_path_ids if path_id in available_path_ids
    ]

    target = subgraph.get("target", {})
    target_aliases = target.get("properties", {}).get("aliases", [])
    forbidden_terms = _unique_strings(
        [
            target.get("name"),
            *(
                list(target_aliases)
                if isinstance(target_aliases, list)
                else []
            ),
            *(
                plan.get("forbidden_terms", [])
                if isinstance(plan, dict) and isinstance(plan.get("forbidden_terms"), list)
                else []
            ),
            *heuristic_plan.get("forbidden_terms", []),
        ]
    )

    return {
        "core_question": (
            str(plan.get("core_question")).strip()
            if isinstance(plan, dict) and _is_nonempty_string(plan.get("core_question"))
            else heuristic_plan.get("core_question")
        ),
        "steps": normalized_steps,
        "dependencies": dependencies,
        "supporting_edge_ids": supporting_edge_ids,
        "supporting_path_ids": supporting_path_ids,
        "forbidden_terms": forbidden_terms,
        "coverage_targets": {
            "required_step_count": len(normalized_steps),
            "required_dependency_count": len(dependencies),
            "must_cover_path_ids": supporting_path_ids,
        },
    }


def _graph_is_valid_shape(graph: Any) -> bool:
    if not isinstance(graph, dict):
        return False
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not 4 <= len(nodes) <= 6:
        return False
    if not isinstance(edges, list) or not 3 <= len(edges) <= 6:
        return False
    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            return False
        if not _is_nonempty_string(node.get("id")) or not _is_nonempty_string(node.get("text")):
            return False
        node_id = str(node.get("id"))
        if node_id in node_ids:
            return False
        node_ids.add(node_id)
    edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            return False
        edge_id = edge.get("id")
        if not _is_nonempty_string(edge_id):
            return False
        edge_id = str(edge_id)
        if edge_id in edge_ids:
            return False
        edge_ids.add(edge_id)
        if not all(_is_nonempty_string(edge.get(key)) for key in ("source", "target", "relation")):
            return False
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            return False
    return True


def _normalize_mechanism_graph(
    graph: Any, mechanism_plan: dict[str, Any], force_rebuild: bool = False
) -> dict[str, Any]:
    steps = mechanism_plan.get("steps", [])
    dependencies = mechanism_plan.get("dependencies", [])
    if (
        not force_rebuild
        and _graph_is_valid_shape(graph)
        and isinstance(graph, dict)
        and len(graph.get("nodes", [])) == len(steps)
        and len(graph.get("edges", [])) == len(dependencies)
    ):
        return deepcopy(graph)

    nodes = [
        {
            "id": f"n{index}",
            "text": str(step.get("text")).strip(),
            "weight": 1.0,
        }
        for index, step in enumerate(steps, start=1)
    ]
    step_to_node_id = {
        str(step.get("step_id")): node["id"]
        for step, node in zip(steps, nodes, strict=False)
    }
    edges = []
    for index, dependency in enumerate(dependencies, start=1):
        source_id = step_to_node_id.get(str(dependency.get("source_step_id")))
        target_id = step_to_node_id.get(str(dependency.get("target_step_id")))
        if not source_id or not target_id:
            continue
        edges.append(
            {
                "id": f"e{index}",
                "source": source_id,
                "target": target_id,
                "relation": (
                    str(dependency.get("relation")).strip()
                    if _is_nonempty_string(dependency.get("relation"))
                    else _infer_dependency_relation(
                        next(
                            (
                                step.get("kind")
                                for step in steps
                                if step.get("step_id") == dependency.get("source_step_id")
                            ),
                            "process",
                        ),
                        next(
                            (
                                step.get("kind")
                                for step in steps
                                if step.get("step_id") == dependency.get("target_step_id")
                            ),
                            "process",
                        ),
                    )
                ),
                "weight": 1.0,
            }
        )
    return {"nodes": nodes, "edges": edges}


def _normalize_grounding(
    grounding: Any, mechanism_plan: dict[str, Any], subgraph: dict[str, Any]
) -> dict[str, Any]:
    available_node_ids = {
        str(node.get("source_node_id"))
        for node in subgraph.get("nodes", [])
        if isinstance(node, dict) and _is_nonempty_string(node.get("source_node_id"))
    }
    available_edge_ids = set(_available_raw_edge_ids(subgraph))
    grounding = grounding if isinstance(grounding, dict) else {}
    source_node_ids = _unique_strings(_string_list(grounding.get("source_node_ids", [])))
    source_edge_ids = _unique_strings(
        [
            *_string_list(grounding.get("source_edge_ids", [])),
            *_string_list(mechanism_plan.get("supporting_edge_ids", [])),
        ]
    )
    source_node_ids = [node_id for node_id in source_node_ids if node_id in available_node_ids]
    source_edge_ids = [edge_id for edge_id in source_edge_ids if edge_id in available_edge_ids]
    return {
        "note": (
            str(grounding.get("note")).strip()
            if _is_nonempty_string(grounding.get("note"))
            else "模型提炼，经本地结构归一化修复"
        ),
        "source_node_ids": source_node_ids,
        "source_edge_ids": source_edge_ids,
    }


def normalize_mechanism_bundle(
    bundle: Any, subgraph: dict[str, Any]
) -> dict[str, Any]:
    candidate = deepcopy(bundle) if isinstance(bundle, dict) else {}
    target = subgraph.get("target", {})
    target_aliases = target.get("properties", {}).get("aliases", [])
    concept = candidate.get("concept", {})
    if not isinstance(concept, dict):
        concept = {}
    concept_name = (
        str(concept.get("name")).strip()
        if _is_nonempty_string(concept.get("name"))
        else str(target.get("name", "")).strip()
    )
    aliases = _unique_strings(
        [
            *(
                concept.get("aliases", [])
                if isinstance(concept.get("aliases"), list)
                else []
            ),
            *(list(target_aliases) if isinstance(target_aliases, list) else []),
        ]
    )
    mechanism_plan = _normalize_mechanism_plan(
        candidate.get("mechanism_plan"), candidate.get("mechanism_graph"), subgraph
    )
    forbidden_terms = _unique_strings(
        [
            *(
                concept.get("forbidden_terms", [])
                if isinstance(concept.get("forbidden_terms"), list)
                else []
            ),
            *mechanism_plan.get("forbidden_terms", []),
        ]
    )
    normalized = dict(candidate)
    normalized["concept"] = {
        "name": concept_name,
        "aliases": aliases,
        "forbidden_terms": forbidden_terms,
    }
    normalized["mechanism_plan"] = mechanism_plan
    original_plan = candidate.get("mechanism_plan")
    original_step_count = (
        len(original_plan.get("steps", []))
        if isinstance(original_plan, dict) and isinstance(original_plan.get("steps"), list)
        else 0
    )
    original_dependency_count = (
        len(original_plan.get("dependencies", []))
        if isinstance(original_plan, dict)
        and isinstance(original_plan.get("dependencies"), list)
        else 0
    )
    force_graph_rebuild = (
        original_step_count != len(mechanism_plan.get("steps", []))
        or original_dependency_count != len(mechanism_plan.get("dependencies", []))
    )
    normalized["mechanism_graph"] = _normalize_mechanism_graph(
        candidate.get("mechanism_graph"), mechanism_plan, force_rebuild=force_graph_rebuild
    )
    normalized["grounding"] = _normalize_grounding(
        candidate.get("grounding"), mechanism_plan, subgraph
    )
    return normalized


def validate_mechanism_bundle(
    bundle: Any, subgraph: dict[str, Any] | None = None
) -> list[str]:
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return ["mechanism response must be an object"]

    concept = bundle.get("concept")
    if not isinstance(concept, dict):
        errors.append("concept must be an object")
    else:
        if not _is_nonempty_string(concept.get("name")):
            errors.append("concept.name must be a non-empty string")
        for key in ("aliases", "forbidden_terms"):
            value = concept.get(key)
            if not isinstance(value, list) or not all(
                _is_nonempty_string(item) for item in value
            ):
                errors.append(f"concept.{key} must be an array of non-empty strings")

    graph = bundle.get("mechanism_graph")
    if not isinstance(graph, dict):
        return [*errors, "mechanism_graph must be an object"]

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not 4 <= len(nodes) <= 6:
        errors.append("mechanism_graph.nodes must contain 4 to 6 items")
        nodes = [] if not isinstance(nodes, list) else nodes
    if not isinstance(edges, list) or not 3 <= len(edges) <= 6:
        errors.append("mechanism_graph.edges must contain 3 to 6 items")
        edges = [] if not isinstance(edges, list) else edges

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node[{index}] must be an object")
            continue
        node_id = node.get("id")
        if not _is_nonempty_string(node_id):
            errors.append(f"node[{index}].id must be a non-empty string")
        elif node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        else:
            node_ids.add(node_id)
        if not _is_nonempty_string(node.get("text")):
            errors.append(f"node[{index}].text must be a non-empty string")

    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge[{index}] must be an object")
            continue
        edge_id = edge.get("id")
        if not _is_nonempty_string(edge_id):
            errors.append(f"edge[{index}].id must be a non-empty string")
        elif edge_id in edge_ids:
            errors.append(f"duplicate edge id: {edge_id}")
        else:
            edge_ids.add(edge_id)
        for key in ("source", "target", "relation"):
            if not _is_nonempty_string(edge.get(key)):
                errors.append(f"edge[{index}].{key} must be a non-empty string")
        if edge.get("source") not in node_ids:
            errors.append(f"edge[{index}].source references unknown node")
        if edge.get("target") not in node_ids:
            errors.append(f"edge[{index}].target references unknown node")

    grounding = bundle.get("grounding", {})
    if grounding and not isinstance(grounding, dict):
        errors.append("grounding must be an object")
    elif isinstance(grounding, dict):
        for key in ("source_node_ids", "source_edge_ids"):
            values = grounding.get(key, [])
            if not isinstance(values, list) or not all(
                _is_nonempty_string(value) for value in values
            ):
                errors.append(f"grounding.{key} must be an array of non-empty strings")
        if subgraph:
            available_node_ids = {
                node["source_node_id"] for node in subgraph["nodes"]
            }
            available_edge_ids = {
                edge["source_edge_id"] for edge in subgraph["edges"]
            }
            unknown_nodes = set(grounding.get("source_node_ids", [])) - available_node_ids
            unknown_edges = set(grounding.get("source_edge_ids", [])) - available_edge_ids
            if unknown_nodes:
                errors.append(
                    "grounding.source_node_ids reference unavailable nodes: "
                    + ", ".join(sorted(unknown_nodes))
                )
            if unknown_edges:
                errors.append(
                    "grounding.source_edge_ids reference unavailable edges: "
                    + ", ".join(sorted(unknown_edges))
                )
    plan_errors = validate_mechanism_plan(bundle.get("mechanism_plan"), subgraph or {})
    errors.extend(plan_errors)
    return errors


def _contains(narrative: str, evidence: Any) -> bool:
    return (
        isinstance(evidence, str)
        and bool(evidence.strip())
        and "".join(evidence.split()).casefold()
        in "".join(narrative.split()).casefold()
    )


def _alignment_anchor(alignment: Any) -> str | None:
    if not isinstance(alignment, dict):
        return None
    anchor = alignment.get("narrative_anchor")
    if _is_nonempty_string(anchor):
        return str(anchor)
    evidence = alignment.get("evidence")
    if _is_nonempty_string(evidence):
        return str(evidence)
    return None


def validate_generation(
    generation: Any, mechanism_bundle: dict[str, Any]
) -> list[str]:
    if not isinstance(generation, dict):
        return ["generation response must be an object"]
    errors: list[str] = []
    narrative = generation.get("narrative")
    if not _is_nonempty_string(narrative):
        errors.append("narrative must be a non-empty string")
        narrative = ""
    elif not MIN_NARRATIVE_CHARS <= len(narrative.strip()) <= MAX_NARRATIVE_CHARS:
        errors.append(
            f"narrative must contain {MIN_NARRATIVE_CHARS} to {MAX_NARRATIVE_CHARS} characters"
        )

    concept = mechanism_bundle["concept"]
    leakage_terms = [
        concept["name"],
        *concept.get("aliases", []),
        *concept.get("forbidden_terms", []),
    ]
    leakage_hits = sorted(
        {
            term
            for term in leakage_terms
            if normalize(term) and normalize(term) in normalize(narrative)
        }
    )
    if leakage_hits:
        errors.append("narrative leaks forbidden terms: " + ", ".join(leakage_hits))

    graph = mechanism_bundle["mechanism_graph"]
    expected_node_ids = {node["id"] for node in graph["nodes"]}
    expected_edges = {edge["id"]: edge for edge in graph["edges"]}

    node_alignments = generation.get("node_alignments")
    if not isinstance(node_alignments, list):
        errors.append("node_alignments must be an array")
        node_alignments = []
    seen_node_ids: list[str] = []
    for index, alignment in enumerate(node_alignments):
        if not isinstance(alignment, dict):
            errors.append(f"node_alignment[{index}] must be an object")
            continue
        node_id = alignment.get("concept_node_id")
        seen_node_ids.append(str(node_id))
        for key in ("concept_node_id", "narrative_element", "evidence"):
            if not _is_nonempty_string(alignment.get(key)):
                errors.append(
                    f"node_alignment[{index}].{key} must be a non-empty string"
                )
        if "narrative_anchor" in alignment and not _is_nonempty_string(
            alignment.get("narrative_anchor")
        ):
            errors.append(
                f"node_alignment[{index}].narrative_anchor must be a non-empty string"
            )
        if narrative and not _contains(narrative, _alignment_anchor(alignment)):
            errors.append(f"node_alignment[{index}].narrative_anchor is not in narrative")
    if set(seen_node_ids) != expected_node_ids or len(seen_node_ids) != len(
        expected_node_ids
    ):
        errors.append("node_alignments must map every mechanism node exactly once")

    edge_alignments = generation.get("edge_alignments")
    if not isinstance(edge_alignments, list):
        errors.append("edge_alignments must be an array")
        edge_alignments = []
    seen_edge_ids: list[str] = []
    for index, alignment in enumerate(edge_alignments):
        if not isinstance(alignment, dict):
            errors.append(f"edge_alignment[{index}] must be an object")
            continue
        edge_id = alignment.get("concept_edge_id")
        seen_edge_ids.append(str(edge_id))
        for key in (
            "concept_edge_id",
            "narrative_relation",
            "evidence",
            "narrative_source_concept_node_id",
            "narrative_target_concept_node_id",
        ):
            if not _is_nonempty_string(alignment.get(key)):
                errors.append(
                    f"edge_alignment[{index}].{key} must be a non-empty string"
                )
        if "narrative_anchor" in alignment and not _is_nonempty_string(
            alignment.get("narrative_anchor")
        ):
            errors.append(
                f"edge_alignment[{index}].narrative_anchor must be a non-empty string"
            )
        if narrative and not _contains(narrative, _alignment_anchor(alignment)):
            errors.append(f"edge_alignment[{index}].narrative_anchor is not in narrative")
        mechanism_edge = expected_edges.get(edge_id)
        if mechanism_edge and (
            alignment.get("narrative_source_concept_node_id")
            != mechanism_edge["source"]
            or alignment.get("narrative_target_concept_node_id")
            != mechanism_edge["target"]
        ):
            errors.append(f"edge_alignment[{index}] reverses mechanism direction")
    if set(seen_edge_ids) != set(expected_edges) or len(seen_edge_ids) != len(
        expected_edges
    ):
        errors.append("edge_alignments must map every mechanism edge exactly once")
    return errors


def build_record(
    mechanism_bundle: dict[str, Any],
    generation: dict[str, Any],
    method: str,
    subgraph: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"{subgraph['retrieval']['subject']}-{subgraph['target']['source_node_id']}",
        "method": method,
        "concept": mechanism_bundle["concept"],
        "mechanism_graph": mechanism_bundle["mechanism_graph"],
        "output": generation,
        "retrieval": {
            "target_node_id": subgraph["target"]["source_node_id"],
            "retrieval_mode": subgraph["retrieval"].get("retrieval_mode", "one_hop"),
            "selected_edge_count": subgraph["retrieval"]["selected_edge_count"],
            "selected_path_count": subgraph["retrieval"].get("selected_path_count", 0),
        },
        "retrieval_analysis": compute_retrieval_analysis(subgraph, mechanism_bundle),
        "grounding": mechanism_bundle.get("grounding", {}),
    }


def _generate_with_validation_repair(
    backend: Any,
    mechanism_bundle: dict[str, Any],
    max_repair_attempts: int = GENERATION_REPAIR_ATTEMPTS,
) -> tuple[dict[str, Any], list[str], int]:
    generation = backend.generate_narrative(mechanism_bundle)
    generation_errors = validate_generation(generation, mechanism_bundle)
    repair_attempts = 0
    while generation_errors and repair_attempts < max_repair_attempts:
        repair_attempts += 1
        try:
            generation = backend.generate_narrative(
                mechanism_bundle, repair_errors=generation_errors
            )
        except TypeError:
            break
        generation_errors = validate_generation(generation, mechanism_bundle)
    return generation, generation_errors, repair_attempts


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_demo(
    concept: str,
    subject: str = "biology",
    backend_name: str = "fixture",
    output_dir: Path | str = Path("graph_rag_demo/output"),
    max_edges: int = 12,
    retrieval_mode: str = "one_hop",
    max_hops: int = 2,
    max_paths: int = 5,
    graph_path: Path | None = None,
    backend: Any | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    graph = load_subject_graph(subject, graph_path)
    subgraph = retrieve_subgraph(
        graph,
        concept,
        subject,
        retrieval_mode=retrieval_mode,
        max_edges=max_edges,
        max_hops=max_hops,
        max_paths=max_paths,
    )
    _write_json(output_path / "01_retrieved_subgraph.json", subgraph)

    if backend is None:
        if backend_name == "fixture":
            backend = FixtureBackend()
        elif backend_name == "deepseek":
            backend = DeepSeekBackend()
        else:
            raise PipelineError(f"unsupported backend: {backend_name}")

    mechanism_bundle = normalize_mechanism_bundle(backend.extract_mechanism(subgraph), subgraph)
    mechanism_errors = validate_mechanism_bundle(mechanism_bundle, subgraph=subgraph)
    if mechanism_errors:
        raise PipelineError("invalid mechanism response: " + "; ".join(mechanism_errors))
    _write_json(output_path / "02_mechanism_graph.json", mechanism_bundle)

    generation, generation_errors, repair_attempts = _generate_with_validation_repair(
        backend, mechanism_bundle
    )
    if generation_errors:
        raise PipelineError("invalid generation response: " + "; ".join(generation_errors))

    record = build_record(
        mechanism_bundle,
        generation,
        method=f"graph_rag_{retrieval_mode}_{backend.name}",
        subgraph=subgraph,
    )
    record_errors = validate_record(record)
    if record_errors:
        raise PipelineError("evaluation record is invalid: " + "; ".join(record_errors))
    (output_path / "03_generation.jsonl").write_text(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = evaluate_record(record)
    report = {
        "input": str(output_path / "03_generation.jsonl"),
        "retrieval_only_metrics": compute_retrieval_analysis(subgraph, mechanism_bundle),
        "generation_metrics": result,
        "generation_repair_attempts": repair_attempts,
        "summary": aggregate([result]),
        "by_method": group_by_method([result]),
        "samples": [result],
    }
    _write_json(output_path / "04_metrics.json", report)
    return report
