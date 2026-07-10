from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kg_rag.concepts.jsonl import read_jsonl, write_jsonl
from kg_rag.io import read_json, write_json
from kg_rag.m2na_v2.pilot80 import PILOT80_IDS, pilot_subject_counts
from kg_rag.m2na_v2.schemas import (
    EDGE_TYPES,
    MECHANISM_SCHEMA_VERSION,
    NODE_TYPES,
    SEED_SCHEMA_VERSION,
    available_evidence_refs,
    stable_hash,
    unique_strings,
    validate_mechanism_record,
    validate_seed,
)
from kg_rag.multi_agent.llm import ChatLLM, ensure_object, extract_json
from kg_rag.m2na_v2.retrieval import retrieve_adaptive_two_hop
from kg_rag.text_cleaning import repair_text


PROMPT_VERSION = "mechanism-builder-v1"
INVERSE_RELATION_ALIASES = {
    "contains": "part_of",
    "has_part": "part_of",
}


def _node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(node["id"]): node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }


def build_seeds(
    *,
    normalized_graph_path: Path,
    output_root: Path,
    concept_ids: list[str] | None = None,
) -> dict[str, Any]:
    graph = read_json(normalized_graph_path)
    nodes = _node_map(graph)
    ids = list(concept_ids or PILOT80_IDS)
    seeds: list[dict[str, Any]] = []
    missing: list[str] = []
    for concept_id in ids:
        node = nodes.get(concept_id)
        if node is None or node.get("label") != "Concept":
            missing.append(concept_id)
            continue
        props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
        name = _clean_text(node.get("name"))
        definition = _clean_text(props.get("definition"))
        aliases = unique_strings([_clean_text(item) for item in props.get("aliases", [])])
        subject = concept_id.split("_", 1)[0]
        seed = {
            "schema_version": SEED_SCHEMA_VERSION,
            "concept_id": concept_id,
            "subject": subject,
            "canonical_name": name,
            "aliases": aliases,
            "definition": definition,
            "concept_type": _infer_concept_type(subject, name, definition),
            "forbidden_terms": unique_strings([name, *aliases]),
        }
        errors = validate_seed(seed)
        if errors:
            raise ValueError(f"Invalid seed {concept_id}: {'; '.join(errors)}")
        seeds.append(seed)
    if missing:
        raise ValueError(f"Pilot concept ids missing from normalized graph: {missing}")
    output_path = output_root / "seeds.jsonl"
    write_jsonl(output_path, seeds)
    result = {
        "schema_version": SEED_SCHEMA_VERSION,
        "normalized_graph_path": str(normalized_graph_path),
        "normalized_graph_sha256": stable_hash(graph),
        "output_path": str(output_path),
        "seed_count": len(seeds),
        "concept_ids_sha256": stable_hash(ids),
        "subject_counts": _count_subjects(seeds),
        "frozen_pilot_subject_counts": pilot_subject_counts() if concept_ids is None else None,
    }
    write_json(output_root / "seed_manifest.json", result)
    return result


def retrieve_packages(
    *,
    normalized_graph_path: Path,
    seeds_path: Path,
    output_root: Path,
    max_edges: int = 20,
    max_paths: int = 8,
) -> dict[str, Any]:
    graph = read_json(normalized_graph_path)
    seeds = read_jsonl(seeds_path)
    retrieval_dir = output_root / "retrieval"
    index_rows: list[dict[str, Any]] = []
    for seed in seeds:
        errors = validate_seed(seed)
        if errors:
            raise ValueError(f"Invalid seed {seed.get('concept_id')}: {'; '.join(errors)}")
        package = retrieve_adaptive_two_hop(
            normalized_graph=graph,
            seed=seed,
            max_edges=max_edges,
            max_paths=max_paths,
        )
        concept_id = str(seed["concept_id"])
        path = retrieval_dir / f"{concept_id}.json"
        write_json(path, package)
        index_rows.append(
            {
                "concept_id": concept_id,
                "path": str(path),
                "sha256": stable_hash(package),
                "edge_count": len(package.get("raw_edges", [])),
                "path_count": len(package.get("selected_paths", [])),
                "expanded_to_two_hop": bool(package.get("retrieval_decision", {}).get("expanded_to_two_hop")),
            }
        )
    index_path = output_root / "retrieval_index.jsonl"
    write_jsonl(index_path, index_rows)
    result = {
        "seed_count": len(seeds),
        "retrieval_count": len(index_rows),
        "max_edges": max_edges,
        "max_paths": max_paths,
        "index_path": str(index_path),
        "adaptive_two_hop_count": sum(
            1
            for row in index_rows
            if row.get("expanded_to_two_hop")
        ),
    }
    write_json(output_root / "retrieval_manifest.json", result)
    return result


def build_mechanisms(
    *,
    seeds_path: Path,
    output_root: Path,
    llm: ChatLLM,
    builder_identity: dict[str, Any],
    limit: int | None = None,
    only_invalid: bool = False,
) -> dict[str, Any]:
    all_seeds = read_jsonl(seeds_path)
    raw_path = output_root / "mechanisms.raw.jsonl"
    validation_path = output_root / "mechanism_validation.jsonl"
    failure_path = output_root / "failed_queue.jsonl"
    existing_records = {
        str(record["concept_id"]): record for record in read_jsonl(raw_path)
    } if only_invalid and raw_path.exists() else {}
    existing_validation = {
        str(row["concept_id"]): row for row in read_jsonl(validation_path)
    } if only_invalid and validation_path.exists() else {}
    existing_failures = read_jsonl(failure_path) if only_invalid and failure_path.exists() else []
    retry_ids = {
        concept_id
        for concept_id, row in existing_validation.items()
        if row.get("status") != "valid"
    }
    retry_ids.update(
        str(row.get("concept_id") or "")
        for row in existing_failures
        if row.get("concept_id")
    )
    if only_invalid:
        retry_ids.update(concept_id for concept_id in (str(seed["concept_id"]) for seed in all_seeds) if concept_id not in existing_records)
        seeds = [seed for seed in all_seeds if str(seed["concept_id"]) in retry_ids]
    else:
        seeds = list(all_seeds)
    if limit is not None:
        seeds = seeds[:limit]
    target_ids = {str(seed["concept_id"]) for seed in seeds}
    raw_dir = output_root / "mechanisms" / "raw"
    response_dir = output_root / "mechanisms" / "responses"
    records_by_id = dict(existing_records)
    validation_by_id = dict(existing_validation)
    failures: list[dict[str, Any]] = [
        row for row in existing_failures if str(row.get("concept_id") or "") not in target_ids
    ]
    for seed in seeds:
        concept_id = str(seed["concept_id"])
        retrieval_path = output_root / "retrieval" / f"{concept_id}.json"
        try:
            retrieval = read_json(retrieval_path)
            system_prompt = _mechanism_system_prompt()
            previous_errors = existing_validation.get(concept_id, {}).get("errors", [])
            user_prompt = _mechanism_user_prompt(seed, retrieval, repair_errors=previous_errors)
            response = llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2200,
                temperature=0.1,
            )
            response_dir.mkdir(parents=True, exist_ok=True)
            (response_dir / f"{concept_id}.txt").write_text(response, encoding="utf-8")
            payload = ensure_object(extract_json(response), context="mechanism builder response")
            record = _normalize_mechanism_record(
                payload=payload,
                seed=seed,
                retrieval=retrieval,
                builder_identity=builder_identity,
                prompt_sha256=stable_hash({"system": system_prompt, "user": user_prompt}),
            )
            errors = validate_mechanism_record(record, seed=seed, retrieval_package=retrieval)
            record["validation"] = {
                "status": "valid" if not errors else "invalid",
                "errors": errors,
            }
            write_json(raw_dir / f"{concept_id}.json", record)
            records_by_id[concept_id] = record
            validation_by_id[concept_id] = {
                "concept_id": concept_id,
                "status": record["validation"]["status"],
                "errors": errors,
            }
            if errors:
                failures.append({"concept_id": concept_id, "stage": "validation", "errors": errors})
        except Exception as exc:
            records_by_id.pop(concept_id, None)
            validation_by_id.pop(concept_id, None)
            failures.append(
                {
                    "concept_id": concept_id,
                    "stage": "builder",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    records = [records_by_id[str(seed["concept_id"])] for seed in all_seeds if str(seed["concept_id"]) in records_by_id]
    validation_rows = [validation_by_id[str(seed["concept_id"])] for seed in all_seeds if str(seed["concept_id"]) in validation_by_id]
    write_jsonl(raw_path, records)
    write_jsonl(validation_path, validation_rows)
    write_jsonl(failure_path, failures)
    result = {
        "requested_count": len(seeds),
        "only_invalid": only_invalid,
        "record_count": len(records),
        "valid_count": sum(1 for row in validation_rows if row["status"] == "valid"),
        "invalid_count": sum(1 for row in validation_rows if row["status"] == "invalid"),
        "failed_count": len(failures),
        "builder": builder_identity,
        "prompt_version": PROMPT_VERSION,
    }
    write_json(output_root / "mechanism_build_manifest.json", result)
    return result


def validate_mechanisms(*, seeds_path: Path, output_root: Path) -> dict[str, Any]:
    seeds = {str(item["concept_id"]): item for item in read_jsonl(seeds_path)}
    records = read_jsonl(output_root / "mechanisms.raw.jsonl")
    rows: list[dict[str, Any]] = []
    for record in records:
        concept_id = str(record.get("concept_id") or "")
        seed = seeds.get(concept_id)
        if seed is None:
            errors = ["mechanism record has no matching seed"]
        else:
            retrieval = read_json(output_root / "retrieval" / f"{concept_id}.json")
            errors = validate_mechanism_record(record, seed=seed, retrieval_package=retrieval)
        rows.append({"concept_id": concept_id, "status": "valid" if not errors else "invalid", "errors": errors})
    write_jsonl(output_root / "mechanism_validation.jsonl", rows)
    result = {
        "record_count": len(records),
        "valid_count": sum(1 for row in rows if row["status"] == "valid"),
        "invalid_count": sum(1 for row in rows if row["status"] == "invalid"),
    }
    write_json(output_root / "mechanism_validation.summary.json", result)
    return result


def _normalize_mechanism_record(
    *,
    payload: dict[str, Any],
    seed: dict[str, Any],
    retrieval: dict[str, Any],
    builder_identity: dict[str, Any],
    prompt_sha256: str,
) -> dict[str, Any]:
    graph = payload.get("mechanism_graph", {}) if isinstance(payload.get("mechanism_graph"), dict) else {}
    nodes = []
    for item in graph.get("nodes", []):
        if isinstance(item, dict):
            nodes.append(
                {
                    "id": item.get("id"),
                    "type": item.get("type"),
                    "text": item.get("text"),
                    "weight": item.get("weight", 1.0),
                    "evidence_refs": unique_strings(item.get("evidence_refs")),
                }
            )
    edges = []
    for item in graph.get("edges", []):
        if isinstance(item, dict):
            relation = item.get("relation")
            source = item.get("source")
            target = item.get("target")
            canonicalized_from = None
            if relation in INVERSE_RELATION_ALIASES:
                canonicalized_from = relation
                relation = INVERSE_RELATION_ALIASES[relation]
                source, target = target, source
            edge = {
                "id": item.get("id"),
                "source": source,
                "target": target,
                "relation": relation,
                "weight": item.get("weight", 1.0),
                "evidence_refs": unique_strings(item.get("evidence_refs")),
            }
            if canonicalized_from:
                edge["canonicalized_from"] = canonicalized_from
            edges.append(edge)
    constraints = payload.get("generation_constraints", {})
    constraints = constraints if isinstance(constraints, dict) else {}
    return {
        "schema_version": MECHANISM_SCHEMA_VERSION,
        "concept_id": seed["concept_id"],
        "mechanism_graph": {"nodes": nodes, "edges": edges},
        "generation_constraints": {
            "forbidden_terms": list(seed["forbidden_terms"]),
            "must_preserve_node_ids": unique_strings(constraints.get("must_preserve_node_ids")),
            "must_preserve_edge_ids": unique_strings(constraints.get("must_preserve_edge_ids")),
        },
        "provenance": {
            "seed_sha256": stable_hash(seed),
            "retrieval_sha256": stable_hash(retrieval),
            "builder": builder_identity,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": prompt_sha256,
        },
    }


def _mechanism_system_prompt() -> str:
    return (
        "你是课程概念机制图抽取器。只输出严格 JSON。每个机制节点和边都必须引用给定证据，"
        "不得从常识补写，也不得把列表顺序自动解释为因果关系。"
    )


def _mechanism_user_prompt(
    seed: dict[str, Any],
    retrieval: dict[str, Any],
    *,
    repair_errors: list[Any] | None = None,
) -> str:
    schema = {
        "mechanism_graph": {
            "nodes": [
                {"id": "n1", "type": "condition", "text": "...", "weight": 1.0, "evidence_refs": ["..."]}
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2", "relation": "enables", "weight": 1.0, "evidence_refs": ["..."]}
            ],
        },
        "generation_constraints": {
            "must_preserve_node_ids": ["n1"],
            "must_preserve_edge_ids": ["e1"],
        },
    }
    sections = [
            "TASK:M2NA_V2_MECHANISM_JSON",
            "Return JSON only. Node type must be exactly one of entity, condition, process, state, outcome, rule, evidence. "
            "Never use skill, concept, action, event, input, output, or another label. A skill source item may be represented "
            "only as process or evidence when its supplied evidence supports that role.",
            "硬约束：最多 8 个节点、最多 12 条边；process/law/mechanism/method/theorem 必须是弱连通图。"
            "请把并列事实合并为紧凑机制节点，不要逐项拆分定义中的示例或枚举。",
            "不得使用未列出的节点类型或边关系；不要输出 caused_by、leads_to、contains 等自造关系。",
            "允许的节点类型：\n" + json.dumps(sorted(NODE_TYPES), ensure_ascii=False),
            "允许的边类型：\n" + json.dumps(sorted(EDGE_TYPES), ensure_ascii=False),
            "可用证据引用：\n" + json.dumps(sorted(available_evidence_refs(retrieval)), ensure_ascii=False),
            "retrieval_role 为 curriculum_bridge 或 curriculum_peer 的边仅用于定位课程上下文，"
            "不得把这些边解释为概念机制，也不得把它们作为 evidence_refs。",
            "ConceptSeed：\n" + json.dumps(seed, ensure_ascii=False, indent=2),
            "RetrievalPackage：\n" + json.dumps(retrieval, ensure_ascii=False, indent=2),
            "输出结构：\n" + json.dumps(schema, ensure_ascii=False, indent=2),
        ]
    if repair_errors:
        sections.insert(1, "上一次输出未通过验证；必须修复这些问题：\n" + json.dumps(repair_errors, ensure_ascii=False))
    return "\n\n".join(sections)


def _count_subjects(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        subject = str(row.get("subject") or "")
        counts[subject] = counts.get(subject, 0) + 1
    return counts


def _clean_text(value: Any) -> str:
    return repair_text(str(value or "")).strip()


def _infer_concept_type(subject: str, name: str, definition: str) -> str:
    text = f"{name}\n{definition}"
    if subject == "math":
        if any(token in text for token in ("定理", "性质", "公式", "法则")):
            return "theorem"
        if any(token in text for token in ("计算", "运算", "方法", "解法")):
            return "method"
        return "relation"
    if subject == "chemistry":
        if any(token in text for token in ("反应", "氧化", "还原", "中和")):
            return "process"
        if any(token in text for token in ("物质", "元素", "分子", "原子", "离子")):
            return "entity"
        return "mechanism"
    if subject == "physics":
        return "law" if any(token in text for token in ("定律", "原理", "关系")) else "mechanism"
    if subject == "biology":
        return "process" if any(token in text for token in ("过程", "作用", "循环", "调节")) else "definition"
    return "definition"
