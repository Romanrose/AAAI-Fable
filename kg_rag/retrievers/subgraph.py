from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.io import read_json, write_json
from kg_rag.neo4j_config import Neo4jConfig


QUERY_TEMPLATE = """
MATCH (seed:GraphNode)
WHERE toLower(seed.name) = toLower($query)
   OR $query IN [alias IN coalesce(seed.aliases, []) | toLower(alias)]
WITH seed
OPTIONAL MATCH path = (seed)-[rels:GRAPH_EDGE*1..2]-(neighbor:GraphNode)
WITH seed, collect(path) AS paths
RETURN seed, paths
LIMIT 1
"""


def query_subgraph_by_concept(
    *,
    concept_name: str,
    config: Neo4jConfig,
) -> dict[str, Any]:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(config.uri, auth=(config.username, config.password))
    try:
        with driver.session(database=config.database) as session:
            record = session.run(QUERY_TEMPLATE, query=concept_name).single()
    finally:
        driver.close()

    if record is None:
        return {
            "query": concept_name,
            "found": False,
            "seed": None,
            "nodes": [],
            "edges": [],
        }

    seed = dict(record["seed"])
    nodes_by_id: dict[str, dict[str, Any]] = {
        seed["id"]: seed,
    }
    edges: list[dict[str, Any]] = []

    for path in record["paths"]:
        if path is None:
            continue
        for node in path.nodes:
            nodes_by_id[node["id"]] = dict(node)
        for rel in path.relationships:
            edges.append(
                {
                    "source": rel.start_node["id"],
                    "target": rel.end_node["id"],
                    "type": rel["type"],
                }
            )

    unique_edges = []
    seen = set()
    for edge in edges:
        key = (edge["source"], edge["target"], edge["type"])
        if key in seen:
            continue
        seen.add(key)
        unique_edges.append(edge)

    return {
        "query": concept_name,
        "found": True,
        "seed": seed,
        "nodes": sorted(nodes_by_id.values(), key=lambda item: item["id"]),
        "edges": sorted(unique_edges, key=lambda item: (item["type"], item["source"], item["target"])),
    }


def write_subgraph_pack(*, payload: dict[str, Any], output_path: Path) -> None:
    write_json(output_path, payload)


def preview_normalized_seed(*, normalized_graph_path: Path, concept_name: str) -> dict[str, Any]:
    payload = read_json(normalized_graph_path)
    query = concept_name.casefold()
    seed = None
    for node in payload["nodes"]:
        if node["id"] == concept_name:
            seed = node
            break
        aliases = node.get("properties", {}).get("aliases", [])
        alias_matches = any(str(alias).casefold() == query for alias in aliases)
        if node["name"].casefold() == query or alias_matches:
            seed = node
            break

    if seed is None:
        return {
            "query": concept_name,
            "found": False,
            "seed": None,
            "nodes": [],
            "edges": [],
        }

    seed_id = seed["id"]
    adjacent_edges = [
        edge
        for edge in payload["edges"]
        if edge["source"] == seed_id or edge["target"] == seed_id
    ]
    neighbor_ids = {seed_id}
    for edge in adjacent_edges:
        neighbor_ids.add(edge["source"])
        neighbor_ids.add(edge["target"])

    nodes = [node for node in payload["nodes"] if node["id"] in neighbor_ids]
    return {
        "query": concept_name,
        "found": True,
        "seed": seed,
        "nodes": nodes,
        "edges": adjacent_edges,
    }
