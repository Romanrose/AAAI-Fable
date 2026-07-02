from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from kg_rag.io import read_json
from kg_rag.neo4j_config import Neo4jConfig


def _chunked(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _build_node_payload(raw_node: dict[str, Any]) -> dict[str, Any]:
    properties = dict(raw_node.get("properties", {}))
    payload = {
        "id": raw_node["id"],
        "label": raw_node["label"],
        "name": raw_node["name"],
        "properties": properties,
    }
    return payload


def load_normalized_graph_to_neo4j(
    *,
    normalized_graph_path: Path,
    config: Neo4jConfig,
    batch_size: int = 500,
) -> dict[str, int]:
    from neo4j import GraphDatabase

    payload = read_json(normalized_graph_path)
    nodes = [_build_node_payload(node) for node in payload["nodes"]]
    edges = payload["edges"]

    driver = GraphDatabase.driver(config.uri, auth=(config.username, config.password))
    try:
        with driver.session(database=config.database) as session:
            session.run("CREATE CONSTRAINT graph_node_id IF NOT EXISTS FOR (n:GraphNode) REQUIRE n.id IS UNIQUE")

            for batch in _chunked(nodes, batch_size):
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (n:GraphNode {id: row.id})
                    SET n.label = row.label,
                        n.name = row.name
                    SET n += row.properties
                    """,
                    rows=batch,
                )

            for batch in _chunked(edges, batch_size):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (source:GraphNode {id: row.source})
                    MATCH (target:GraphNode {id: row.target})
                    MERGE (source)-[r:GRAPH_EDGE {type: row.type, source_id: row.source, target_id: row.target}]->(target)
                    """,
                    rows=batch,
                )
    finally:
        driver.close()

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
