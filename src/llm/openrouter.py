"""OpenRouter client — OpenAI-compatible chat completions over httpx.

We talk to OpenRouter directly (no vendor SDK) so the dependency surface stays
small. The client tracks token usage and supports a simple fallback: if the
requested model errors, it retries once on the fast model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from src.config import get_settings
from src.core.logging import logger

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class LLMError(RuntimeError):
    """Raised when OpenRouter cannot fulfil a completion after fallback."""


@dataclass
class Usage:
    """Running token/cost counter for a process lifetime."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    requests: int = 0

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.requests += 1

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class OpenRouterClient:
    usage: Usage = field(default_factory=Usage)

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResult:
        settings = get_settings()
        if not settings.openrouter_configured:
            raise LLMError("OPENROUTER_API_KEY is not configured")

        target = model or settings.openrouter_model_fast
        try:
            return await self._call(target, prompt, system, temperature, max_tokens)
        except (httpx.HTTPError, LLMError) as exc:
            fast = settings.openrouter_model_fast
            if target == fast:
                raise LLMError(f"OpenRouter failed for {target}: {exc}") from exc
            logger.warning("model {} failed ({}); falling back to {}", target, exc, fast)
            return await self._call(fast, prompt, system, temperature, max_tokens)

    async def _call(
        self,
        model: str,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> LLMResult:
        settings = get_settings()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": settings.openrouter_app_url,
            "X-Title": settings.openrouter_app_name,
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(_ENDPOINT, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise LLMError(f"{resp.status_code}: {resp.text[:200]}")
            data = resp.json()

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"unexpected response shape: {data}") from exc

        usage = data.get("usage", {})
        pt = int(usage.get("prompt_tokens", 0))
        ct = int(usage.get("completion_tokens", 0))
        self.usage.add(pt, ct)
        return LLMResult(text=text.strip(), model=model, prompt_tokens=pt, completion_tokens=ct)


# Shared client so token usage accumulates across the process.
llm_client = OpenRouterClient()
