"""第一部分：数据库 + 数据清洗。

职责：把 K12-KGraph 的课程概念，清洗/筛选/抽取成 M2NA 任务的输入 (G_c, T_c)。

子模块：
- k12_loader      读取 K12-KGraph subject_specific_KG，产出不可变 ConceptRecord。
- concept_selection  确定性地给概念打「机制富集」分，筛出适合做类比的候选。

后续（接 LLM / 人工校验）：
- gc_extractor    从概念定义半自动抽取机制图 MechanismGraph。
- tc_builder      构建禁用词集 T_c。
"""

from __future__ import annotations

from .concept_selection import ScoredConcept, rank_candidates, score_mechanism
from .concept_store import from_dict, load_input, save_input, to_dict
from .gc_extractor import (
    GcExtractionError,
    build_extraction_prompt,
    extract_mechanism_graph,
    parse_mechanism_graph,
)
from .k12_loader import (
    SUBJECTS,
    ConceptRecord,
    load_all_concepts,
    load_subject,
)
from .tc_builder import build_forbidden_terms

__all__ = [
    "ConceptRecord",
    "SUBJECTS",
    "load_subject",
    "load_all_concepts",
    "ScoredConcept",
    "score_mechanism",
    "rank_candidates",
    "build_forbidden_terms",
    "build_extraction_prompt",
    "parse_mechanism_graph",
    "extract_mechanism_graph",
    "GcExtractionError",
    "to_dict",
    "from_dict",
    "save_input",
    "load_input",
]
