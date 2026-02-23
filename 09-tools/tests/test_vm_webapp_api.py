import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.memory import Hit
from vm_webapp.repo import create_brand, create_product
from vm_webapp.settings import Settings


def test_api_health_and_list_brands() -> None:
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True

    res = client.get("/api/v1/brands")
    assert res.status_code == 200
    assert res.json()["brands"] == []


def test_list_products_by_brand(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    ws = app.state.workspace
    engine = app.state.engine

    with session_scope(engine) as session:
        create_brand(
            session,
            brand_id="b1",
            name="Acme",
            canonical={},
            ws=ws,
            soul_md="",
        )
        create_product(
            session,
            brand_id="b1",
            product_id="p1",
            name="Widget",
            canonical={},
            ws=ws,
            essence_md="",
        )

    client = TestClient(app)
    res = client.get("/api/v1/products", params={"brand_id": "b1"})
    assert res.status_code == 200
    assert res.json()["products"][0]["product_id"] == "p1"


def test_start_foundation_run_returns_run_id_and_status(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    res = client.post(
        "/api/v1/runs/foundation",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": "t1",
            "user_request": "crm para clinicas",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["run_id"]
    assert body["status"] in {"running", "waiting_approval", "completed"}


def test_list_runs_by_thread(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    start = client.post(
        "/api/v1/runs/foundation",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": "thread-xyz",
            "user_request": "crm para clinicas",
        },
    )
    assert start.status_code == 200

    res = client.get("/api/v1/runs", params={"thread_id": "thread-xyz"})
    assert res.status_code == 200
    assert len(res.json()["runs"]) >= 1


def test_approve_endpoint_continues_waiting_run(tmp_path: Path) -> None:
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    start = client.post(
        "/api/v1/runs/foundation",
        json={
            "brand_id": "b1",
            "product_id": "p1",
            "thread_id": "t1",
            "user_request": "crm",
        },
    )
    assert start.status_code == 200
    run_id = start.json()["run_id"]

    res = client.post(f"/api/v1/runs/{run_id}/approve")
    assert res.status_code == 200
    assert res.json()["run_id"] == run_id


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


def test_vm_webapp_is_importable_without_conftest_path_hack() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [sys.executable, "-c", "import vm_webapp, vm_webapp.__main__"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
