from __future__ import annotations

from onboard_web import create_app


def test_health_endpoint() -> None:
    app = create_app()
    client = app.test_client()
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_defaults_endpoint_returns_supported_ides(monkeypatch) -> None:
    monkeypatch.setattr(
        "onboard_web.build_defaults",
        lambda shell_file: {"supported_ides": ["codex"], "shell_file": "/tmp/.zshrc"},
    )
    app = create_app()
    client = app.test_client()
    response = client.get("/api/v1/defaults")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["defaults"]["supported_ides"] == ["codex"]


def test_preview_endpoint_returns_report(monkeypatch) -> None:
    monkeypatch.setattr(
        "onboard_web.run_preview",
        lambda **kwargs: {"ides": {"codex": {"status": "preview"}}, "keys": {}, "dry_run": True},
    )
    app = create_app()
    client = app.test_client()
    response = client.post(
        "/api/v1/onboard/preview",
        json={"ides": ["codex"], "applyKeys": False, "keys": {}, "shellFile": ""},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["report"]["dry_run"] is True


def test_apply_endpoint_returns_report(monkeypatch) -> None:
    monkeypatch.setattr(
        "onboard_web.run_apply",
        lambda **kwargs: {"ides": {"codex": {"status": "applied"}}, "keys": {}, "dry_run": False},
    )
    app = create_app()
    client = app.test_client()
    response = client.post(
        "/api/v1/onboard/apply",
        json={
            "ides": ["codex"],
            "decisions": {"codex": "apply"},
            "applyKeys": False,
            "keys": {},
            "shellFile": "",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["report"]["dry_run"] is False


def test_apply_endpoint_requires_decisions() -> None:
    app = create_app()
    client = app.test_client()
    response = client.post(
        "/api/v1/onboard/apply",
        json={"ides": ["codex"], "applyKeys": False, "keys": {}, "shellFile": ""},
    )
    assert response.status_code == 400
