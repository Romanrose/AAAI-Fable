from __future__ import annotations

import json
from typing import Any

from kg_rag.multi_agent.llm import ChatLLM, ensure_object, extract_json
from kg_rag.multi_agent.text import mask_forbidden_terms, unique_strings


SOURCE_DOMAINS = {
    "biology": ["港口检疫站", "园圃值守所", "剧场后台", "邮局分拣房"],
    "chemistry": ["账房仓库", "铸造工坊", "印章局", "城邦交换所"],
    "physics": ["水渠调度站", "滑道试验场", "船队信号台", "秤房"],
    "math": ["规则棋局", "法庭证据室", "地图修补坊", "拼图工坊"],
}


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _domain_for(card: dict[str, Any], candidate_index: int) -> str:
    domains = SOURCE_DOMAINS.get(str(card.get("subject") or ""), ["修补工坊", "档案局", "港口调度站"])
    return domains[(candidate_index - 1) % len(domains)]


def _fallback_plan(
    *,
    card: dict[str, Any],
    mechanism_graph: dict[str, Any],
    candidate_index: int,
) -> dict[str, Any]:
    source_domain = _domain_for(card, candidate_index)
    nodes = mechanism_graph.get("nodes", [])
    event_chain = [
        f"主角在{source_domain}中检查第{index + 1}道隐含规则是否成立。"
        for index, _node in enumerate(nodes[:5])
    ]
    if not event_chain:
        event_chain = [
            f"主角先在{source_domain}中确认起始条件。",
            "随后按顺序观察变化如何发生。",
            "最后用结果反查整条安排是否可靠。",
        ]
    return {
        "source_domain": source_domain,
        "characters": ["记录员", "调度员", "验收员"],
        "objects": ["分段记录册", "封存箱", "通行牌"],
        "conflict": "表面结果似乎已经出现，但关键条件和中间顺序还没有被核对。",
        "event_chain": event_chain,
        "turning_point": "一次验收暴露出顺序错位，主角必须重新按隐含规则安排流程。",
        "resolution_state": "所有环节按条件、过程和结果衔接后，系统恢复稳定。",
        "mapping_plan": [
            {
                "mechanism_node_id": node.get("id"),
                "mechanism_text": node.get("text"),
                "story_role": f"{source_domain}中的第{index + 1}道隐含环节",
            }
            for index, node in enumerate(nodes)
            if isinstance(node, dict)
        ],
        "risk_notes": ["正文不能出现目标概念名、别名或教材式术语。"],
    }


class PlannerAgent:
    def __init__(self, llm: ChatLLM):
        self.llm = llm
        self.last_call: dict[str, Any] = {"status": "not_called"}

    def plan(
        self,
        *,
        card: dict[str, Any],
        retrieval_package: dict[str, Any],
        mechanism_graph: dict[str, Any],
        candidate_index: int,
    ) -> dict[str, Any]:
        preferred_domain = _domain_for(card, candidate_index)
        system_prompt = (
            "你是寓言结构规划 Agent。你只负责把概念机制图映射为中文寓言结构，"
            "不要写故事正文。必须输出严格 JSON。"
        )
        user_prompt = f"""TASK:PLANNER_JSON
请为一个中文概念寓言生成第 {candidate_index} 个结构方案。

硬性要求：
1. 正文后续必须隐含目标概念，不能直接出现目标概念名、别名或禁用术语。
2. 结构必须保留机制节点和机制边的顺序，不要只做角色替换。
3. 避免智者、老人、森林动物、村庄危机、镜子、钟表、河流等常见模板。
4. 优先使用这个故事域：{preferred_domain}

概念卡：
{_dumps(card)}

GraphRAG 检索摘要：
{_dumps(retrieval_package.get("topic_summary", {}))}

机制图：
{_dumps(mechanism_graph)}

输出 JSON schema：
{{
  "source_domain": "...",
  "characters": ["..."],
  "objects": ["..."],
  "conflict": "...",
  "event_chain": ["..."],
  "turning_point": "...",
  "resolution_state": "...",
  "mapping_plan": [
    {{
      "mechanism_node_id": "n1",
      "mechanism_text": "...",
      "story_role": "..."
    }}
  ],
  "risk_notes": ["..."]
}}
"""
        try:
            response = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1800,
                temperature=0.45,
            )
            plan = ensure_object(extract_json(response), context="planner response")
            self.last_call = {"status": "success"}
        except Exception as exc:
            self.last_call = {"status": "fallback", "error": str(exc)}
            plan = _fallback_plan(card=card, mechanism_graph=mechanism_graph, candidate_index=candidate_index)
        return _normalize_plan(plan, card=card, mechanism_graph=mechanism_graph, candidate_index=candidate_index)


def _normalize_plan(
    plan: dict[str, Any],
    *,
    card: dict[str, Any],
    mechanism_graph: dict[str, Any],
    candidate_index: int,
) -> dict[str, Any]:
    fallback = _fallback_plan(card=card, mechanism_graph=mechanism_graph, candidate_index=candidate_index)
    normalized = {**fallback, **{key: value for key, value in plan.items() if value}}
    for key in ("characters", "objects", "event_chain", "mapping_plan", "risk_notes"):
        if not isinstance(normalized.get(key), list):
            normalized[key] = fallback[key]
    normalized["candidate_index"] = candidate_index
    normalized["story_language"] = "zh-CN"
    return normalized


class GeneratorAgent:
    def __init__(self, llm: ChatLLM):
        self.llm = llm
        self.last_call: dict[str, Any] = {"status": "not_called"}

    def generate(
        self,
        *,
        card: dict[str, Any],
        mechanism_graph: dict[str, Any],
        plan: dict[str, Any],
    ) -> str:
        forbidden_terms = unique_strings(
            [
                card.get("canonical_name"),
                *card.get("aliases", []),
                *card.get("forbidden_terms_zh", []),
            ]
        )
        system_prompt = (
            "你是中文寓言写作 Agent。你只输出故事正文，不输出标题、解释、列表或 JSON。"
        )
        user_prompt = f"""TASK:GENERATOR_STORY
请根据结构方案写一篇中文寓言正文。

硬性要求：
1. 只输出故事正文，不要标题，不要解释目标概念。
2. 正文不能出现这些禁用词：{_dumps(forbidden_terms)}
3. 不要使用教材式说明句，不要写“这个故事说明了……概念”。
4. 故事应自然、连贯，约 350-700 个中文字符。
5. 必须让事件顺序对应机制图中的节点和边。

机制图：
{_dumps(mechanism_graph)}

结构方案：
{_dumps(plan)}
"""
        try:
            story = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1600,
                temperature=0.7,
            ).strip()
            self.last_call = {"status": "success"}
        except Exception as exc:
            self.last_call = {"status": "fallback", "error": str(exc)}
            story = _fallback_story(plan)
        return mask_forbidden_terms(_strip_story_noise(story), forbidden_terms)


def _strip_story_noise(story: str) -> str:
    text = story.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("text"):
            text = text[4:].strip()
    return text


def _fallback_story(plan: dict[str, Any]) -> str:
    domain = plan.get("source_domain") or "修补工坊"
    sentences = [
        f"{domain}里有一套从不写在门口的规矩。",
        str(plan.get("conflict") or "表面的顺利掩盖了顺序里的漏洞。"),
    ]
    for event in plan.get("event_chain", [])[:5]:
        sentences.append(str(event))
    sentences.extend(
        [
            str(plan.get("turning_point") or "一次核对让主角发现，少掉任何一环都会让结果失真。"),
            str(plan.get("resolution_state") or "众人按隐含顺序重新安排后，所有记录终于能够互相印证。"),
        ]
    )
    return "".join(sentence if sentence.endswith("。") else f"{sentence}。" for sentence in sentences)


class AlignerAgent:
    def __init__(self, llm: ChatLLM):
        self.llm = llm
        self.last_call: dict[str, Any] = {"status": "not_called"}

    def align(
        self,
        *,
        mechanism_graph: dict[str, Any],
        plan: dict[str, Any],
        story: str,
    ) -> dict[str, Any]:
        system_prompt = (
            "你是故事-机制对齐 Agent。你只判断故事证据如何对应机制图，必须输出严格 JSON。"
        )
        user_prompt = f"""TASK:ALIGNER_JSON
请把故事正文反向对齐到机制图。

硬性要求：
1. evidence 必须从故事正文中逐字复制，长度 4-40 字。
2. 不要编造正文中不存在的证据。
3. edge_alignments 必须判断方向是否保留。

机制图：
{_dumps(mechanism_graph)}

结构方案：
{_dumps(plan)}

故事正文：
{story}

输出 JSON schema：
{{
  "node_alignments": [
    {{
      "concept_node_id": "n1",
      "narrative_element": "...",
      "evidence": "...",
      "narrative_anchor": "...",
      "confidence": 0.0
    }}
  ],
  "edge_alignments": [
    {{
      "concept_edge_id": "e1",
      "narrative_relation": "...",
      "evidence": "...",
      "narrative_anchor": "...",
      "narrative_source_concept_node_id": "n1",
      "narrative_target_concept_node_id": "n2",
      "direction_preserved": true,
      "confidence": 0.0
    }}
  ]
}}
"""
        try:
            response = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1800,
                temperature=0.2,
            )
            alignment = ensure_object(extract_json(response), context="aligner response")
            self.last_call = {"status": "success"}
        except Exception as exc:
            self.last_call = {"status": "fallback", "error": str(exc)}
            alignment = {}
        return normalize_alignment(alignment, mechanism_graph=mechanism_graph, story=story)


def normalize_alignment(
    alignment: dict[str, Any],
    *,
    mechanism_graph: dict[str, Any],
    story: str,
) -> dict[str, Any]:
    node_ids = {node.get("id") for node in mechanism_graph.get("nodes", []) if isinstance(node, dict)}
    edge_ids = {edge.get("id") for edge in mechanism_graph.get("edges", []) if isinstance(edge, dict)}
    normalized_nodes = []
    seen_nodes: set[str] = set()
    for item in alignment.get("node_alignments", []):
        if not isinstance(item, dict) or item.get("concept_node_id") not in node_ids:
            continue
        node_id = item["concept_node_id"]
        if node_id in seen_nodes:
            continue
        anchor = item.get("narrative_anchor") or item.get("evidence")
        if not isinstance(anchor, str) or not anchor.strip() or anchor not in story:
            continue
        anchor = anchor.strip()
        normalized_nodes.append(
            {
                "concept_node_id": node_id,
                "narrative_element": str(item.get("narrative_element") or anchor),
                "evidence": anchor,
                "narrative_anchor": anchor,
                "confidence": _confidence(item.get("confidence"), 0.6),
            }
        )
        seen_nodes.add(node_id)

    normalized_edges = []
    seen_edges: set[str] = set()
    for item in alignment.get("edge_alignments", []):
        if not isinstance(item, dict) or item.get("concept_edge_id") not in edge_ids:
            continue
        edge_id = item["concept_edge_id"]
        if edge_id in seen_edges:
            continue
        anchor = item.get("narrative_anchor") or item.get("evidence")
        if not isinstance(anchor, str) or not anchor.strip() or anchor not in story:
            continue
        anchor = anchor.strip()
        normalized_edges.append(
            {
                "concept_edge_id": edge_id,
                "narrative_relation": str(item.get("narrative_relation") or "事件顺序承接"),
                "evidence": anchor,
                "narrative_anchor": anchor,
                "narrative_source_concept_node_id": item.get("narrative_source_concept_node_id"),
                "narrative_target_concept_node_id": item.get("narrative_target_concept_node_id"),
                "direction_preserved": item.get("direction_preserved") is True,
                "confidence": _confidence(item.get("confidence"), 0.55),
            }
        )
        seen_edges.add(edge_id)

    return {"node_alignments": normalized_nodes, "edge_alignments": normalized_edges}


def _confidence(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _edge_by_id(mechanism_graph: dict[str, Any], edge_id: str) -> dict[str, Any]:
    for edge in mechanism_graph.get("edges", []):
        if isinstance(edge, dict) and edge.get("id") == edge_id:
            return edge
    return {}


class ReviserAgent:
    def __init__(self, llm: ChatLLM):
        self.llm = llm
        self.last_call: dict[str, Any] = {"status": "not_called"}

    def revise(
        self,
        *,
        card: dict[str, Any],
        mechanism_graph: dict[str, Any],
        plan: dict[str, Any],
        story: str,
        failure_reason: str,
    ) -> str:
        forbidden_terms = unique_strings(
            [
                card.get("canonical_name"),
                *card.get("aliases", []),
                *card.get("forbidden_terms_zh", []),
            ]
        )
        system_prompt = "你是中文寓言修订 Agent。你只输出修订后的故事正文。"
        user_prompt = f"""TASK:REVISER_STORY
请根据失败原因修订故事。

失败原因：
{failure_reason}

硬性要求：
1. 只输出故事正文。
2. 不得出现禁用词：{_dumps(forbidden_terms)}
3. 保留机制图的条件、过程、结果和方向。
4. 不要输出概念解释。

机制图：
{_dumps(mechanism_graph)}

结构方案：
{_dumps(plan)}

原故事：
{story}
"""
        try:
            revised = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1600,
                temperature=0.55,
            ).strip()
            self.last_call = {"status": "success"}
        except Exception as exc:
            self.last_call = {"status": "fallback", "error": str(exc)}
            revised = story
        return mask_forbidden_terms(_strip_story_noise(revised), forbidden_terms)


class ArbiterAgent:
    def __init__(self, llm: ChatLLM):
        self.llm = llm
        self.last_call: dict[str, Any] = {"status": "not_called"}

    def choose(
        self,
        *,
        candidates: list[dict[str, Any]],
        deterministic_winner: str,
    ) -> dict[str, Any]:
        compact_candidates = [
            {
                "candidate_id": candidate["candidate_id"],
                "metrics": candidate["automatic_metrics"],
                "six_dim": candidate["six_dim_eval"]["scores"],
                "story_excerpt": candidate["story"][:260],
            }
            for candidate in candidates
        ]
        system_prompt = (
            "你是多候选寓言决策 Agent。你只能在候选 id 中选择一个，必须输出严格 JSON。"
        )
        user_prompt = f"""TASK:ARBITER_JSON
请在候选故事中选择最终版本。优先保证：
1. 不泄露目标概念。
2. 覆盖机制节点和机制边。
3. 对齐证据可信。
4. 中文故事自然且不模板化。

确定性指标当前推荐：{deterministic_winner}

候选：
{_dumps(compact_candidates)}

输出 JSON schema：
{{
  "winner_candidate_id": "...",
  "rationale": "中文理由",
  "risk_notes": ["..."]
}}
"""
        try:
            response = self.llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=800,
                temperature=0.2,
            )
            decision = ensure_object(extract_json(response), context="arbiter response")
            self.last_call = {"status": "success"}
        except Exception as exc:
            self.last_call = {"status": "fallback", "error": str(exc)}
            decision = {}
        winner = decision.get("winner_candidate_id")
        candidate_ids = {candidate["candidate_id"] for candidate in candidates}
        if winner not in candidate_ids:
            winner = deterministic_winner
        return {
            "winner_candidate_id": winner,
            "rationale": decision.get("rationale") or "使用确定性指标排序结果作为最终选择。",
            "risk_notes": decision.get("risk_notes") if isinstance(decision.get("risk_notes"), list) else [],
        }
