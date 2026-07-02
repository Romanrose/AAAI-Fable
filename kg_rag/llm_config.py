from __future__ import annotations

import os
from dataclasses import dataclass

from kg_rag.env import load_local_env


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 1200

    @classmethod
    def from_env(cls) -> "LLMConfig":
        load_local_env()
        provider = os.getenv("LLM_PROVIDER", "deepseek").strip() or "deepseek"
        base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
        temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "1200"))

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
            provider=provider,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
