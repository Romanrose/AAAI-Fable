from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from kg_rag.llm_config import LLMConfig


class LLMRequestError(RuntimeError):
    """Raised when the configured LLM request fails."""


def chat_completion(*, config: LLMConfig, system_prompt: str, user_prompt: str) -> str:
    provider = config.provider.lower().replace("_", "-")
    if provider in {"anthropic", "claude"}:
        return _anthropic_completion(config=config, system_prompt=system_prompt, user_prompt=user_prompt)
    if provider in {"gemini", "google", "google-gemini"}:
        return _gemini_completion(config=config, system_prompt=system_prompt, user_prompt=user_prompt)
    return _openai_compatible_completion(config=config, system_prompt=system_prompt, user_prompt=user_prompt)


def _openai_compatible_completion(*, config: LLMConfig, system_prompt: str, user_prompt: str) -> str:
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
        with request.urlopen(req, timeout=config.timeout_seconds) as resp:
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


def _anthropic_completion(*, config: LLMConfig, system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": config.model,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=f"{config.base_url}/messages",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with request.urlopen(req, timeout=config.timeout_seconds) as resp:
            result: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<unreadable response body>"
        raise LLMRequestError(f"HTTP {exc.code} from {config.base_url}/messages: {body}") from exc
    except error.URLError as exc:
        raise LLMRequestError(f"Network error while calling {config.base_url}/messages: {exc.reason}") from exc
    except TimeoutError as exc:
        raise LLMRequestError(f"Timeout while calling {config.base_url}/messages") from exc

    try:
        content = result["content"]
        if isinstance(content, list):
            return "\n".join(str(block.get("text", "")) for block in content if isinstance(block, dict)).strip()
        return str(content)
    except (KeyError, TypeError) as exc:
        raise LLMRequestError(
            f"Malformed Anthropic response from {config.base_url}: {json.dumps(result, ensure_ascii=False)[:1000]}"
        ) from exc


def _gemini_completion(*, config: LLMConfig, system_prompt: str, user_prompt: str) -> str:
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": config.temperature,
            "maxOutputTokens": config.max_tokens,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    endpoint = f"{config.base_url}/models/{config.model}:generateContent?key={config.api_key}"
    req = request.Request(
        url=endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=config.timeout_seconds) as resp:
            result: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<unreadable response body>"
        raise LLMRequestError(f"HTTP {exc.code} from Gemini endpoint: {body}") from exc
    except error.URLError as exc:
        raise LLMRequestError(f"Network error while calling Gemini endpoint: {exc.reason}") from exc
    except TimeoutError as exc:
        raise LLMRequestError("Timeout while calling Gemini endpoint") from exc

    try:
        parts = result["candidates"][0]["content"]["parts"]
        return "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMRequestError(
            f"Malformed Gemini response from {config.base_url}: {json.dumps(result, ensure_ascii=False)[:1000]}"
        ) from exc
