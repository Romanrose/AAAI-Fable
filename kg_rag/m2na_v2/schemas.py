from __future__ import annotations

import hashlib
import json
from typing import Any


SEED_SCHEMA_VERSION = "m2na-concept-seed/v1"
MECHANISM_SCHEMA_VERSION = "m2na-mechanism-record/v1"

SEED_FIELDS = {
    "schema_version",
    "concept_id",
    "subject",
    "canonical_name",
    "aliases",
    "definition",
    "concept_type",
    "forbidden_terms",
}
NODE_TYPES = {"entity", "condition", "process", "state", "outcome", "rule", "evidence"}
EDGE_TYPES = {
    "requires",
    "enables",
    "transforms",
    "causes",
    "produces",
    "constrains",
    "is_a",
    "part_of",
    "relates_to",
    "verifies",
}
MULTISTEP_CONCEPT_TYPES = {"process", "law", "mechanism", "method", "theorem"}


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def unique_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.strip()
        if text not in seen:
            seen.add(text)
            results.append(text)
    return results


def validate_seed(seed: Any) -> list[str]:
    if not isinstance(seed, dict):
        return ["seed must be an object"]
    errors: list[str] = []
    extra = set(seed) - SEED_FIELDS
    if extra:
        errors.append(f"seed contains unsupported fields: {sorted(extra)}")
    if seed.get("schema_version") != SEED_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SEED_SCHEMA_VERSION}")
    for key in ("concept_id", "subject", "canonical_name", "concept_type"):
        if not isinstance(seed.get(key), str) or not seed[key].strip():
            errors.append(f"{key} must be a non-empty string")
    if not isinstance(seed.get("definition", ""), str):
        errors.append("definition must be a string")
    for key in ("aliases", "forbidden_terms"):
        values = seed.get(key)
        if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
            errors.append(f"{key} must be an array of non-empty strings")
    return errors


def available_evidence_refs(retrieval_package: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    target = retrieval_package.get("target", {})
    target_id = target.get("source_node_id")
    properties = target.get("properties", {}) if isinstance(target.get("properties"), dict) else {}
    if isinstance(target_id, str) and target_id:
        refs.add(f"kg-node:{target_id}:name")
        for key, value in properties.items():
            if value not in (None, "", [], {}):
                refs.add(f"kg-node:{target_id}:{key}")
    for node in retrieval_package.get("retrieved_nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("source_node_id")
        properties = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
        if isinstance(node_id, str) and node_id:
            refs.add(f"kg-node:{node_id}:name")
            for key, value in properties.items():
                if value not in (None, "", [], {}):
                    refs.add(f"kg-node:{node_id}:{key}")
    for edge in retrieval_package.get("raw_edges", []):
        if (
            isinstance(edge, dict)
            and edge.get("evidence_eligible", True)
            and isinstance(edge.get("source_edge_id"), str)
        ):
            refs.add(f"kg-edge:{edge['source_edge_id']}")
    return refs


def validate_mechanism_record(
    record: Any,
    *,
    seed: dict[str, Any],
    retrieval_package: dict[str, Any],
) -> list[str]:
    if not isinstance(record, dict):
        return ["mechanism record must be an object"]
    errors: list[str] = []
    if record.get("schema_version") != MECHANISM_SCHEMA_VERSION:
        errors.append(f"schema_version must be {MECHANISM_SCHEMA_VERSION}")
    if record.get("concept_id") != seed.get("concept_id"):
        errors.append("concept_id does not match seed")
    graph = record.get("mechanism_graph")
    if not isinstance(graph, dict):
        return [*errors, "mechanism_graph must be an object"]
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not nodes:
        errors.append("mechanism_graph.nodes must be a non-empty array")
        nodes = []
    if not isinstance(edges, list):
        errors.append("mechanism_graph.edges must be an array")
        edges = []
    if len(nodes) > 8:
        errors.append("mechanism_graph.nodes must contain at most 8 nodes")
    if len(edges) > 12:
        errors.append("mechanism_graph.edges must contain at most 12 edges")

    evidence_refs = available_evidence_refs(retrieval_package)
    node_ids: set[str] = set()
    edge_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"node[{index}] must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"node[{index}].id is required")
        elif node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        else:
            node_ids.add(node_id)
        if node.get("type") not in NODE_TYPES:
            errors.append(f"node[{index}].type is invalid")
        if not isinstance(node.get("text"), str) or not node["text"].strip():
            errors.append(f"node[{index}].text is required")
        refs = unique_strings(node.get("evidence_refs"))
        if not refs:
            errors.append(f"node[{index}] requires evidence_refs")
        for ref in refs:
            if ref not in evidence_refs:
                errors.append(f"node[{index}] references unavailable evidence: {ref}")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge[{index}] must be an object")
            continue
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id.strip():
            errors.append(f"edge[{index}].id is required")
        elif edge_id in edge_ids:
            errors.append(f"duplicate edge id: {edge_id}")
        else:
            edge_ids.add(edge_id)
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            errors.append(f"edge[{index}] references unknown endpoint")
        if edge.get("relation") not in EDGE_TYPES:
            errors.append(f"edge[{index}].relation is invalid")
        refs = unique_strings(edge.get("evidence_refs"))
        if not refs:
            errors.append(f"edge[{index}] requires evidence_refs")
        for ref in refs:
            if ref not in evidence_refs:
                errors.append(f"edge[{index}] references unavailable evidence: {ref}")

    if str(seed.get("concept_type")) in MULTISTEP_CONCEPT_TYPES:
        if len(nodes) < 2:
            errors.append("multistep concept requires at least 2 mechanism nodes")
        if not edges:
            errors.append("multistep concept requires at least 1 mechanism edge")
        if nodes and not _is_connected(node_ids, edges):
            errors.append("multistep mechanism graph must be weakly connected")

    constraints = record.get("generation_constraints")
    if not isinstance(constraints, dict):
        errors.append("generation_constraints must be an object")
        constraints = {}
    forbidden = unique_strings(constraints.get("forbidden_terms"))
    if forbidden != unique_strings(seed.get("forbidden_terms")):
        errors.append("generation_constraints.forbidden_terms must match seed")
    for key, valid_ids in (
        ("must_preserve_node_ids", node_ids),
        ("must_preserve_edge_ids", edge_ids),
    ):
        values = unique_strings(constraints.get(key))
        if any(value not in valid_ids for value in values):
            errors.append(f"{key} contains an unknown id")
        if key == "must_preserve_node_ids" and not values:
            errors.append("must_preserve_node_ids must not be empty")
        if key == "must_preserve_edge_ids" and edges and not values:
            errors.append("must_preserve_edge_ids must not be empty when edges exist")

    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
    else:
        if provenance.get("seed_sha256") != stable_hash(seed):
            errors.append("provenance.seed_sha256 does not match seed")
        if provenance.get("retrieval_sha256") != stable_hash(retrieval_package):
            errors.append("provenance.retrieval_sha256 does not match retrieval package")
    return errors


def _is_connected(node_ids: set[str], edges: list[Any]) -> bool:
    if len(node_ids) <= 1:
        return True
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)
    seen: set[str] = set()
    pending = [next(iter(node_ids))]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency[current] - seen)
    return seen == node_ids
