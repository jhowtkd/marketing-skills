from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.memory import Hit


def test_api_health_and_list_brands() -> None:
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True

    res = client.get("/api/v1/brands")
    assert res.status_code == 200
    assert res.json()["brands"] == []


def test_root_serves_ui() -> None:
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "VM Web App" in res.text


def test_chat_uses_retrieved_context_in_prompt() -> None:
    class FakeMemory:
        def search(self, query: str, *, filters: dict, top_k: int) -> list[Hit]:
            assert query == "Create landing copy."
            assert filters == {"brand_id": "b1"}
            assert top_k == 3
            return [
                Hit(
                    doc_id="run:1",
                    text="We tried X and it failed.",
                    meta={"brand_id": "b1"},
                    score=1.0,
                )
            ]

        def upsert_doc(self, doc_id: str, text: str, meta: dict) -> None:
            return None

    class FakeLLM:
        def __init__(self) -> None:
            self.last_messages: list[dict] = []

        def chat(
            self,
            *,
            model: str,
            messages: list[dict],
            temperature: float,
            max_tokens: int,
        ) -> str:
            self.last_messages = messages
            return "assistant reply"

    fake_llm = FakeLLM()
    app = create_app(memory=FakeMemory(), llm=fake_llm)
    client = TestClient(app)

    res = client.post(
        "/api/v1/chat",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": "t1",
            "message": "Create landing copy.",
        },
    )
    assert res.status_code == 200
    assert res.json()["assistant_message"] == "assistant reply"

    prompt_text = "\n".join(str(item.get("content", "")) for item in fake_llm.last_messages)
    assert "We tried X and it failed." in prompt_text


def test_cli_module_imports() -> None:
    import vm_webapp.__main__  # noqa: F401
