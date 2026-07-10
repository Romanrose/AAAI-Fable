from __future__ import annotations

import json
import re
import time
from dataclasses import replace
from typing import Any, Protocol

from kg_rag.llm_client import LLMRequestError, chat_completion
from kg_rag.llm_config import LLMConfig


class ChatLLM(Protocol):
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        ...


class DeepSeekLLM:
    def __init__(
        self,
        config: LLMConfig,
        *,
        max_attempts: int = 3,
        retry_base_seconds: float = 0.5,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.config = config
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        config = self.config
        if max_tokens is not None or temperature is not None:
            config = replace(
                config,
                max_tokens=max_tokens if max_tokens is not None else config.max_tokens,
                temperature=temperature if temperature is not None else config.temperature,
            )
        for attempt in range(1, self.max_attempts + 1):
            try:
                return chat_completion(
                    config=config,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            except LLMRequestError as exc:
                if not exc.retriable or attempt >= self.max_attempts:
                    raise
                time.sleep(self.retry_base_seconds * (2 ** (attempt - 1)))
        raise AssertionError("unreachable retry loop")


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json|JSON)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def extract_json(text: str) -> Any:
    cleaned = strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    starts = [index for index in (cleaned.find("{"), cleaned.find("[")) if index >= 0]
    if not starts:
        raise ValueError(f"LLM response does not contain JSON: {cleaned[:300]}")
    start = min(starts)
    opening = cleaned[start]
    closing = "}" if opening == "{" else "]"
    end = cleaned.rfind(closing)
    if end <= start:
        raise ValueError(f"LLM response contains incomplete JSON: {cleaned[:300]}")
    return json.loads(cleaned[start : end + 1])


def ensure_object(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value


def ensure_list(value: Any, *, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a JSON array")
    return value
