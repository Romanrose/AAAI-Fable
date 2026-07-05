"""Audited offline responses for the photosynthesis demo."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PHOTOSYNTHESIS_MECHANISM = {
    "concept": {
        "name": "光合作用",
        "aliases": ["photosynthesis", "植物制造有机物的过程"],
        "forbidden_terms": [
            "叶绿体",
            "叶绿素",
            "二氧化碳",
            "氧气",
            "有机物",
            "光能",
        ],
    },
    "mechanism_plan": {
        "core_question": "光合作用如何把外部能量和原料转化为支持生长与环境维持的产物？",
        "steps": [
            {
                "step_id": "s1",
                "text": "捕获外部光照提供的能量",
                "kind": "condition",
            },
            {
                "step_id": "s2",
                "text": "获得水和空气中的含碳原料",
                "kind": "condition",
            },
            {
                "step_id": "s3",
                "text": "利用能量把原料合成为可储存物质",
                "kind": "process",
            },
            {
                "step_id": "s4",
                "text": "合成过程中释放可供呼吸的气体",
                "kind": "effect",
            },
            {
                "step_id": "s5",
                "text": "产物支持生长并维持周围环境",
                "kind": "effect",
            },
        ],
        "dependencies": [
            {"source_step_id": "s1", "target_step_id": "s3", "relation": "enables"},
            {
                "source_step_id": "s2",
                "target_step_id": "s3",
                "relation": "supplies_materials",
            },
            {
                "source_step_id": "s3",
                "target_step_id": "s4",
                "relation": "co_produces",
            },
            {"source_step_id": "s3", "target_step_id": "s5", "relation": "supports"},
        ],
        "supporting_edge_ids": [
            "biology:edge:137",
            "biology:edge:138",
            "biology:edge:140",
            "biology:edge:141",
            "biology:edge:146",
            "biology:edge:147",
            "biology:edge:156",
        ],
        "supporting_path_ids": [],
        "forbidden_terms": [
            "光合作用",
            "photosynthesis",
            "植物制造有机物的过程",
            "叶绿体",
            "叶绿素",
            "二氧化碳",
            "氧气",
            "有机物",
            "光能",
        ],
        "coverage_targets": {
            "required_step_count": 5,
            "required_dependency_count": 4,
            "must_cover_path_ids": [],
        },
    },
    "mechanism_graph": {
        "nodes": [
            {"id": "n1", "text": "捕获外部光照提供的能量", "weight": 1.2},
            {"id": "n2", "text": "获得水和空气中的含碳原料", "weight": 1.0},
            {"id": "n3", "text": "利用能量把原料合成为可储存物质", "weight": 1.3},
            {"id": "n4", "text": "合成过程中释放可供呼吸的气体", "weight": 1.0},
            {"id": "n5", "text": "产物支持生长并维持周围环境", "weight": 1.1},
        ],
        "edges": [
            {
                "id": "e1",
                "source": "n1",
                "target": "n3",
                "relation": "enables",
                "weight": 1.2,
            },
            {
                "id": "e2",
                "source": "n2",
                "target": "n3",
                "relation": "supplies_materials",
                "weight": 1.1,
            },
            {
                "id": "e3",
                "source": "n3",
                "target": "n4",
                "relation": "co_produces",
                "weight": 1.0,
            },
            {
                "id": "e4",
                "source": "n3",
                "target": "n5",
                "relation": "supports",
                "weight": 1.1,
            },
        ],
    },
    "grounding": {
        "note": "The mechanism graph is a model-derived abstraction, not a raw KG subgraph.",
        "source_node_ids": [
            "biology_7a_rjb_cpt4",
            "biology_7a_rjb_cpt52",
            "biology_7a_rjb_cpt131",
            "biology_7a_rjb_cpt132",
            "biology_7a_rjb_cpt133",
            "biology_7a_rjb_cpt140",
            "biology_7a_rjb_cpt141",
            "biology_7a_rjb_cpt147",
        ],
        "source_edge_ids": [
            "biology:edge:137",
            "biology:edge:138",
            "biology:edge:140",
            "biology:edge:141",
            "biology:edge:146",
            "biology:edge:147",
            "biology:edge:156",
        ],
    },
}


PHOTOSYNTHESIS_GENERATION = {
    "narrative": (
        "海边工坊每天打开屋顶的绿色薄板，让晨光驱动机器。"
        "两条管道分别送来井水和空气中的一种废气，车间把它们合成耐储存的糖砖，"
        "并把多余的清新气体排回街巷。糖砖既供工坊建造新屋，也把白昼的力量留到夜间使用；"
        "久而久之，整座城的居民都依靠这间工坊获得食物与可呼吸的空气。"
    ),
    "node_alignments": [
        {
            "concept_node_id": "n1",
            "narrative_element": "绿色薄板接收晨光并驱动机器",
            "evidence": "绿色薄板接收晨光并为工坊提供动力",
            "narrative_anchor": "打开屋顶的绿色薄板，让晨光驱动机器",
        },
        {
            "concept_node_id": "n2",
            "narrative_element": "两条管道送入水和废气",
            "evidence": "工坊从两条管道接收两种关键原料",
            "narrative_anchor": "两条管道分别送来井水和空气中的一种废气",
        },
        {
            "concept_node_id": "n3",
            "narrative_element": "工坊将原料合成可储存糖砖",
            "evidence": "工坊把输入原料转化成可储存的产物",
            "narrative_anchor": "车间把它们合成耐储存的糖砖",
        },
        {
            "concept_node_id": "n4",
            "narrative_element": "工坊向外排出清新气体",
            "evidence": "工坊在转化过程中释放额外产物",
            "narrative_anchor": "把多余的清新气体排回街巷",
        },
        {
            "concept_node_id": "n5",
            "narrative_element": "糖砖和清新空气支持工坊与城市",
            "evidence": "产物继续支持城市的生存与扩张",
            "narrative_anchor": "整座城的居民都依靠这间工坊获得食物与可呼吸的空气",
        },
    ],
    "edge_alignments": [
        {
            "concept_edge_id": "e1",
            "narrative_relation": "晨光为合成糖砖的机器提供动力",
            "evidence": "动力输入促成后续转化",
            "narrative_anchor": "让晨光驱动机器",
            "narrative_source_concept_node_id": "n1",
            "narrative_target_concept_node_id": "n3",
            "direction_preserved": True,
        },
        {
            "concept_edge_id": "e2",
            "narrative_relation": "管道输入的两种原料被合成为糖砖",
            "evidence": "输入的两种原料共同导向主要产物",
            "narrative_anchor": "两条管道分别送来井水和空气中的一种废气，车间把它们合成耐储存的糖砖",
            "narrative_source_concept_node_id": "n2",
            "narrative_target_concept_node_id": "n3",
            "direction_preserved": True,
        },
        {
            "concept_edge_id": "e3",
            "narrative_relation": "合成糖砖时同时排出清新气体",
            "evidence": "主要转化过程伴随额外产物释放",
            "narrative_anchor": "车间把它们合成耐储存的糖砖，并把多余的清新气体排回街巷",
            "narrative_source_concept_node_id": "n3",
            "narrative_target_concept_node_id": "n4",
            "direction_preserved": True,
        },
        {
            "concept_edge_id": "e4",
            "narrative_relation": "储存的产物为工坊和居民提供支持",
            "evidence": "形成的产物继续支撑后续生存与应用",
            "narrative_anchor": "糖砖既供工坊建造新屋，也把白昼的力量留到夜间使用",
            "narrative_source_concept_node_id": "n3",
            "narrative_target_concept_node_id": "n5",
            "direction_preserved": True,
        },
    ],
}


def mechanism_fixture() -> dict[str, Any]:
    return deepcopy(PHOTOSYNTHESIS_MECHANISM)


def generation_fixture() -> dict[str, Any]:
    return deepcopy(PHOTOSYNTHESIS_GENERATION)
