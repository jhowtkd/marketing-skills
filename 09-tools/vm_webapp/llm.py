from __future__ import annotations

from typing import Any

import httpx


class KimiClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(transport=transport, timeout=30.0)
        self._api_key = api_key

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        # Build headers with optional HTTP-Referer for OpenRouter compatibility
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # Add HTTP-Referer for OpenRouter (required by their API)
        if "openrouter" in self._base_url.lower():
            headers["HTTP-Referer"] = "https://vm-webapp.local"
            headers["X-Title"] = "VM Web App"
        
        response = self._client.post(
            f"{self._base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"])
