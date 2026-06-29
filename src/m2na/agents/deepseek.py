"""DeepSeek LLM 后端（实现 LLMClient 协议）。

用标准库 urllib 直连 DeepSeek 的 OpenAI 兼容接口，不引入 openai 依赖。
注入方式与 MockLLMClient 一致：`M2NAPipeline(DeepSeekClient())` 或
`extract_mechanism_graph(record, DeepSeekClient())`，agent / 抽取器一行不用改。

API key 从环境变量 DEEPSEEK_API_KEY 读取，**不写进源码**。
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

_DEFAULT_BASE_URL = "https://api.deepseek.com"
_DEFAULT_MODEL = "deepseek-chat"
_DEFAULT_TIMEOUT = 60


def _load_dotenv(path: Path | None = None) -> None:
    """Load simple KEY=VALUE lines from .env without adding a runtime dependency."""

    env_path = path or Path(__file__).resolve().parents[3] / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class DeepSeekClient:
    """最小 DeepSeek 后端：complete(prompt) -> str。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEFAULT_BASE_URL,
        temperature: float = 0.7,
        timeout: int = _DEFAULT_TIMEOUT,
        ca_bundle: str | None = None,
    ) -> None:
        _load_dotenv()
        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError(
                "缺少 DeepSeek API key：请在项目根目录 .env 中填写 DEEPSEEK_API_KEY，"
                "设置环境变量 DEEPSEEK_API_KEY，或显式传入 DeepSeekClient(api_key=...)。"
            )
        self._key = key
        self._model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._temperature = temperature
        self._timeout = timeout
        # TLS 拦截代理环境（自签名根证书）下，传入企业 CA bundle 路径，或设
        # 环境变量 DEEPSEEK_CA_BUNDLE / SSL_CERT_FILE。默认走系统证书。
        cafile = ca_bundle or os.environ.get("DEEPSEEK_CA_BUNDLE")
        self._ssl_context = ssl.create_default_context(cafile=cafile)

    def complete(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = json.dumps(
            {
                "model": self._model,
                "messages": messages,
                "temperature": self._temperature,
                "stream": False,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            self._url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout, context=self._ssl_context
            ) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DeepSeek 请求失败: {exc.reason}") from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"DeepSeek 响应结构异常: {body!r}") from exc
