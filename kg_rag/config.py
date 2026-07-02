from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kg_rag.paths import DEFAULT_DERIVED_DIR, DEFAULT_GRAPH_ROOT, DEFAULT_KG_RAG_DERIVED_DIR, DEFAULT_SUBJECT_GRAPH_DIR


@dataclass(frozen=True)
class GraphPaths:
    graph_root: Path = DEFAULT_GRAPH_ROOT
    subject_graph_dir: Path = DEFAULT_SUBJECT_GRAPH_DIR
    derived_dir: Path = DEFAULT_DERIVED_DIR
    kg_rag_derived_dir: Path = DEFAULT_KG_RAG_DERIVED_DIR
