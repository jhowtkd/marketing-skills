import json

import httpx

from vm_webapp.llm import KimiClient


def test_kimi_chat_completions_request_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "kimi-for-coding"
        assert payload["messages"][-1]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            },
        )

    transport = httpx.MockTransport(handler)
    client = KimiClient(
        base_url="https://api.kimi.com/coding/v1",
        api_key="sk-test",
        transport=transport,
    )
    out = client.chat(
        model="kimi-for-coding",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_tokens=128,
    )
    assert out == "ok"
