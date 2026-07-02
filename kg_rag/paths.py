from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DERIVED_DIR = DEFAULT_DATA_DIR / "derived"
DEFAULT_KG_RAG_DERIVED_DIR = DEFAULT_DERIVED_DIR / "kg_rag"

DEFAULT_K12_ROOT = DEFAULT_DATA_DIR / "K12-KGraph"
DEFAULT_GRAPH_ROOT = DEFAULT_K12_ROOT / "K12-KGraph" / "global_KG"
DEFAULT_SUBJECT_GRAPH_DIR = DEFAULT_K12_ROOT / "K12-KGraph" / "subject_specific_KG"
DEFAULT_BENCH_DIR = DEFAULT_K12_ROOT / "K12-Bench"
DEFAULT_TRAIN_DIR = DEFAULT_K12_ROOT / "K12-Train"
