from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from kg_rag.env import load_local_env


@dataclass(frozen=True)
class LLMConfig:
    name: str
    provider: str
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 1200
    timeout_seconds: int = 120

    @classmethod
    def from_env(cls) -> "LLMConfig":
        load_local_env()
        provider = os.getenv("LLM_PROVIDER", "deepseek").strip() or "deepseek"
        base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "1200"))
        timeout_seconds = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "120"))

        missing = [
            name
            for name, value in (
                ("DEEPSEEK_BASE_URL", base_url),
                ("DEEPSEEK_API_KEY", api_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required LLM environment variables: {', '.join(missing)}")

        return cls(
            name=provider,
            provider=provider,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def from_env_prefix(cls, prefix: str, *, default_name: str | None = None) -> "LLMConfig":
        load_local_env()
        normalized = prefix.rstrip("_")
        name = os.getenv(f"{normalized}_NAME", default_name or normalized.lower()).strip()
        provider = os.getenv(f"{normalized}_PROVIDER", "openai-compatible").strip()
        base_url = os.getenv(f"{normalized}_BASE_URL", "").strip()
        api_key = os.getenv(f"{normalized}_API_KEY", "").strip()
        api_key_env = os.getenv(f"{normalized}_API_KEY_ENV", "").strip()
        if not api_key and api_key_env:
            api_key = os.getenv(api_key_env, "").strip()
        model = os.getenv(f"{normalized}_MODEL", "").strip()
        temperature = float(os.getenv(f"{normalized}_TEMPERATURE", "0.0"))
        max_tokens = int(os.getenv(f"{normalized}_MAX_TOKENS", "1600"))
        timeout_seconds = int(os.getenv(f"{normalized}_TIMEOUT_SECONDS", "120"))

        missing = [
            name
            for name, value in (
                (f"{normalized}_BASE_URL", base_url),
                (f"{normalized}_API_KEY or {normalized}_API_KEY_ENV", api_key),
                (f"{normalized}_MODEL", model),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required judge environment variables: {', '.join(missing)}")

        return cls(
            name=name,
            provider=provider,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )


def load_eval_judge_configs(prefixes: Iterable[str] | None = None) -> list[LLMConfig]:
    load_local_env()
    raw_prefixes = list(prefixes or ())
    if not raw_prefixes:
        configured = os.getenv("EVAL_JUDGE_PREFIXES", "").strip()
        raw_prefixes = [item.strip() for item in configured.split(",") if item.strip()]
    if not raw_prefixes:
        count = int(os.getenv("EVAL_JUDGE_COUNT", "3"))
        raw_prefixes = [f"EVAL_JUDGE_{index}" for index in range(1, count + 1)]
    return [
        LLMConfig.from_env_prefix(prefix, default_name=f"judge_{index}")
        for index, prefix in enumerate(raw_prefixes, start=1)
    ]
