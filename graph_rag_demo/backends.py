"""Fixture and DeepSeek JSON generation backends."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from .fixtures import generation_fixture, mechanism_fixture
from .retrieval import normalize, serialize_subgraph


class BackendError(RuntimeError):
    """Raised when a generation backend cannot return a valid response."""


RequestFunction = Callable[[urllib.request.Request, float], tuple[int, bytes]]


def _default_request(request: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


class FixtureBackend:
    """Return audited responses while still requiring real graph retrieval."""

    name = "fixture"

    def extract_mechanism(self, subgraph: dict[str, Any]) -> dict[str, Any]:
        if normalize(subgraph["target"]["name"]) != normalize("光合作用"):
            raise BackendError("fixture backend only supports the concept '光合作用'")
        return mechanism_fixture()

    def generate_narrative(
        self, mechanism_bundle: dict[str, Any], repair_errors: list[str] | None = None
    ) -> dict[str, Any]:
        if normalize(mechanism_bundle["concept"]["name"]) != normalize("光合作用"):
            raise BackendError("fixture backend only supports the concept '光合作用'")
        return generation_fixture()


class DeepSeekBackend:
    """Two-stage DeepSeek client using the OpenAI-compatible JSON API."""

    name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        request_fn: RequestFunction | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        self.base_url = (
            base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        ).rstrip("/")
        self.timeout = timeout
        self.request_fn = request_fn or _default_request
        self.sleep_fn = sleep_fn

    def _chat_json(
        self, messages: list[dict[str, str]], max_tokens: int
    ) -> dict[str, Any]:
        if not self.api_key:
            raise BackendError(
                "DEEPSEEK_API_KEY is not configured; use --backend fixture "
                "or export a valid key"
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        last_error = "unknown DeepSeek error"
        for attempt in range(2):
            retryable = False
            try:
                status, body = self.request_fn(request, self.timeout)
                if status == 429 or status >= 500:
                    retryable = True
                    last_error = f"DeepSeek returned HTTP {status}"
                elif status >= 400:
                    detail = body.decode("utf-8", errors="replace")[:500]
                    raise BackendError(f"DeepSeek returned HTTP {status}: {detail}")
                else:
                    envelope = json.loads(body.decode("utf-8"))
                    content = envelope["choices"][0]["message"]["content"]
                    if not content and envelope["choices"][0].get("finish_reason") == "length":
                        raise ValueError(
                            "empty content because model output hit max_tokens"
                        )
                    result = json.loads(content)
                    if not isinstance(result, dict):
                        raise ValueError("JSON response is not an object")
                    return result
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or exc.code >= 500
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                last_error = f"DeepSeek returned HTTP {exc.code}: {detail}"
                if not retryable:
                    raise BackendError(last_error) from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                retryable = True
                last_error = f"DeepSeek request failed: {exc}"
            except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
                retryable = True
                last_error = f"DeepSeek returned invalid JSON: {exc}"

            if retryable and attempt == 0:
                self.sleep_fn(0.25)
                continue
            break
        raise BackendError(last_error)

    def extract_mechanism(self, subgraph: dict[str, Any]) -> dict[str, Any]:
        context = serialize_subgraph(subgraph)
        return self._chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "你是严谨的教育知识图谱分析器。请只根据给定检索证据，"
                        "把课程子图提炼为机制图。课程子图和机制图必须明确区分。"
                        "输入中的 raw_edges 是原始 KG 边，selected_paths 是裁剪后的"
                        "机制路径，topic_summary 是辅助摘要而不是原始事实来源。"
                        "必须输出合法 json 对象，不要输出 Markdown。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"检索证据：\n{context}\n\n"
                        "输出 json，结构为："
                        '{"concept":{"name":"...","aliases":[],"forbidden_terms":[]},'
                        '"mechanism_plan":{"core_question":"...",'
                        '"steps":[{"step_id":"s1","text":"...",'
                        '"kind":"condition"}],"dependencies":[{"source_step_id":"s1",'
                        '"target_step_id":"s2","relation":"..."}],'
                        '"supporting_edge_ids":[],"supporting_path_ids":[],'
                        '"forbidden_terms":[],"coverage_targets":{'
                        '"required_step_count":4,"required_dependency_count":3,'
                        '"must_cover_path_ids":[]}},'
                        '"mechanism_graph":{"nodes":[{"id":"n1","text":"...",'
                        '"weight":1.0}],"edges":[{"id":"e1","source":"n1",'
                        '"target":"n2","relation":"...","weight":1.0}]},'
                        '"grounding":{"note":"模型提炼，不是原始KG事实",'
                        '"source_node_ids":[],"source_edge_ids":[]}}。'
                        "要求 4–6 个节点、3–6 条有向边；禁用词包含概念名之外的"
                        "高泄露学科术语；优先从 selected_paths 提炼机制结构；"
                        "mechanism_plan.steps 的 kind 只能是 condition、process 或 effect；"
                        "mechanism_plan.supporting_path_ids 只能引用 selected_paths 中的 path_id；"
                        "grounding 只能引用 raw_edges 中真实存在的来源 ID，"
                        "不能把 topic_summary 当作原始 KG 事实来源。"
                    ),
                },
            ],
            max_tokens=5000,
        )

    @staticmethod
    def _direction_contract(mechanism_bundle: dict[str, Any]) -> str:
        graph = mechanism_bundle.get("mechanism_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_text_by_id = {
            str(node.get("id")): str(node.get("text", ""))
            for node in nodes
            if isinstance(node, dict)
        }
        lines = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            edge_id = str(edge.get("id", ""))
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            relation = str(edge.get("relation", ""))
            if not edge_id or not source or not target:
                continue
            source_text = node_text_by_id.get(source, "")
            target_text = node_text_by_id.get(target, "")
            lines.append(
                f"- {edge_id}: {source}({source_text}) -> "
                f"{target}({target_text}), relation={relation}"
            )
        return "\n".join(lines) if lines else "- 无有效机制边"

    @staticmethod
    def _alignment_contract(mechanism_bundle: dict[str, Any]) -> str:
        graph = mechanism_bundle.get("mechanism_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_lines = [
            f"- {node.get('id')}: {node.get('text')}"
            for node in nodes
            if isinstance(node, dict)
        ]
        edge_lines = [
            f"- {edge.get('id')}: {edge.get('source')} -> "
            f"{edge.get('target')} ({edge.get('relation')})"
            for edge in edges
            if isinstance(edge, dict)
        ]
        return (
            "必须映射的节点：\n"
            + ("\n".join(node_lines) if node_lines else "- 无")
            + "\n必须映射的边：\n"
            + ("\n".join(edge_lines) if edge_lines else "- 无")
        )

    def generate_narrative(
        self, mechanism_bundle: dict[str, Any], repair_errors: list[str] | None = None
    ) -> dict[str, Any]:
        direction_contract = self._direction_contract(mechanism_bundle)
        alignment_contract = self._alignment_contract(mechanism_bundle)
        repair_instruction = ""
        if repair_errors:
            repair_hint = (
                "如果错误包含 narrative 长度问题，请扩写为至少 4 个中文句子，"
                "围绕角色、困境、行动、结果补足细节，控制在约 160 个汉字；"
                "如果错误包含 narrative_anchor 不在 narrative 中，请先写完整故事，再把"
                " node_alignments 和 edge_alignments 的 narrative_anchor 逐字复制自正文连续片段；"
                "如果错误包含 reverses mechanism direction，请不要依赖 direction_preserved 自报，"
                "必须按下方机制边方向重写正文事件顺序，并把 narrative_source_concept_node_id 与 "
                "narrative_target_concept_node_id 填成机制图原方向；"
                "如果错误包含 must map every mechanism node/edge exactly once，请补齐缺失映射、删除重复映射；"
                "如果错误包含 forbidden_terms 泄露，请把学科术语改写成角色、物件或场景意象。"
            )
            repair_instruction = (
                "\n\n上一次输出未通过校验，错误如下："
                + "; ".join(repair_errors)
                + f"。{repair_hint}\n机制边方向合同：\n{direction_contract}\n"
                "请重新输出完整合法 json。"
            )
        return self._chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "你是 K12 科学微型寓言作者。必须输出合法 json 对象，"
                        "不得输出 Markdown。你的任务是把给定机制结构改写成微型寓言，"
                        "用角色、冲突、行动、变化和结果隐含表达机制，"
                        "同时隐藏目标术语。正文只负责讲故事；"
                        "对齐说明放在 evidence 字段，正文锚点放在 narrative_anchor 字段。"
                        "不要写成定义、讲解、实验说明、步骤答案或结论复述。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "输入机制：\n"
                        f"{json.dumps(mechanism_bundle, ensure_ascii=False)}"
                        f"{repair_instruction}\n\n"
                        f"{alignment_contract}\n\n"
                        "机制边方向合同如下，edge_alignments 必须逐条遵守：\n"
                        f"{direction_contract}\n\n"
                        "输出 json，结构为："
                        '{"narrative":"90到260字中文微型寓言",'
                        '"node_alignments":[{"concept_node_id":"n1",'
                        '"narrative_element":"...","evidence":"机制对齐说明",'
                        '"narrative_anchor":"正文中的连续原文"}],'
                        '"edge_alignments":[{"concept_edge_id":"e1",'
                        '"narrative_relation":"...","evidence":"因果或关系说明",'
                        '"narrative_anchor":"正文中的连续原文",'
                        '"narrative_source_concept_node_id":"n1",'
                        '"narrative_target_concept_node_id":"n2",'
                        '"direction_preserved":true}]}。'
                        "必须同时遵循 mechanism_plan 的步骤顺序和 mechanism_graph 的有向边；"
                        "narrative 必须是完整的微型寓言，至少 4 个中文句子，控制在 90 到 260 个中文字符，"
                        "建议约 160 到 200 个汉字；"
                        "第 1 句交代角色与困境，第 2-3 句推进行动与变化，最后 1 句给出结果或含蓄寓意；"
                        "允许动物、植物、器物或自然现象拟人，但整篇只能使用一套稳定喻体；"
                        "正文要有画面感，优先写角色之间的互动，不要把 mechanism_graph 逐条翻译成教材句子；"
                        "避免使用“实验”“说明了”“表示”“因此”“可见”等说明文口吻；"
                        "每个节点和边恰好映射一次；"
                        "evidence 用来写该节点或边在机制上的对齐说明，不必逐字出现在正文；"
                        "narrative_anchor 必须逐字复制自 narrative 的连续片段，不得改写，"
                        "建议选择 4 到 20 个汉字的具体事件短语；"
                        "edge_alignments 中的 narrative_source_concept_node_id 和 "
                        "narrative_target_concept_node_id 必须等于机制边方向合同中的 source 和 target；"
                        "输出前请自检：所有 anchor 都能在正文中搜索到，所有边方向都与合同一致；"
                        "正文不得出现概念名、aliases 或 forbidden_terms。"
                    ),
                },
            ],
            max_tokens=4000,
        )
