from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from kg_rag.llm_config import LLMConfig


class LLMRequestError(RuntimeError):
    """Raised when the configured LLM request fails."""


def chat_completion(*, config: LLMConfig, system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=f"{config.base_url}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            result: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<unreadable response body>"
        raise LLMRequestError(
            f"HTTP {exc.code} from {config.base_url}/chat/completions: {body}"
        ) from exc
    except error.URLError as exc:
        raise LLMRequestError(
            f"Network error while calling {config.base_url}/chat/completions: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise LLMRequestError(
            f"Timeout while calling {config.base_url}/chat/completions"
        ) from exc

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMRequestError(
            f"Malformed completion response from {config.base_url}: {json.dumps(result, ensure_ascii=False)[:1000]}"
        ) from exc
