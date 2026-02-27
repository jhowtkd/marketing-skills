"""Testes para policy editorial multi-tenant por brand.

TDD estrito: fail -> mínimo -> pass -> commit
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.settings import Settings


def test_editorial_policy_model_exists():
    """Modelo EditorialPolicy deve existir com campos corretos."""
    from vm_webapp.models import EditorialPolicy
    
    # Verificar que o modelo existe e tem os campos esperados
    assert hasattr(EditorialPolicy, 'brand_id')
    assert hasattr(EditorialPolicy, 'editor_can_mark_objective')
    assert hasattr(EditorialPolicy, 'editor_can_mark_global')
    assert hasattr(EditorialPolicy, 'updated_at')


def test_get_editorial_policy_endpoint_returns_defaults(tmp_path: Path) -> None:
    """GET /api/v2/brands/{brand_id}/editorial-policy deve retornar defaults quando não existe."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Criar brand
    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "policy-b"}, 
        json={"name": "Acme"}
    ).json()["brand_id"]

    # GET policy - deve retornar defaults
    resp = client.get(f"/api/v2/brands/{brand_id}/editorial-policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["brand_id"] == brand_id
    assert data["editor_can_mark_objective"] is True  # default
    assert data["editor_can_mark_global"] is False    # default
    assert "updated_at" in data


def test_put_editorial_policy_requires_admin_role(tmp_path: Path) -> None:
    """PUT /api/v2/brands/{brand_id}/editorial-policy deve exigir role admin."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "policy-b2"}, 
        json={"name": "Acme"}
    ).json()["brand_id"]

    # Editor tentando atualizar policy - deve falhar
    resp_editor = client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={
            "Idempotency-Key": "policy-update-editor",
            "Authorization": "Bearer editor:editor"
        },
        json={
            "editor_can_mark_objective": True,
            "editor_can_mark_global": True,
        }
    )
    assert resp_editor.status_code == 403

    # Admin pode atualizar
    resp_admin = client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={
            "Idempotency-Key": "policy-update-admin",
            "Authorization": "Bearer admin:admin"
        },
        json={
            "editor_can_mark_objective": True,
            "editor_can_mark_global": True,
        }
    )
    assert resp_admin.status_code == 200


def test_put_editorial_policy_requires_idempotency_key(tmp_path: Path) -> None:
    """PUT deve exigir Idempotency-Key header."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "policy-b3"}, 
        json={"name": "Acme"}
    ).json()["brand_id"]

    # Sem Idempotency-Key
    resp = client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={"Authorization": "Bearer admin:admin"},
        json={"editor_can_mark_objective": True}
    )
    assert resp.status_code == 400


def test_put_editorial_policy_persists_changes(tmp_path: Path) -> None:
    """PUT deve persistir alterações e GET deve retornar valores atualizados."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "policy-b4"}, 
        json={"name": "Acme"}
    ).json()["brand_id"]

    # Atualizar policy
    resp_put = client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={
            "Idempotency-Key": "policy-update-1",
            "Authorization": "Bearer admin:admin"
        },
        json={
            "editor_can_mark_objective": False,
            "editor_can_mark_global": True,
        }
    )
    assert resp_put.status_code == 200
    data_put = resp_put.json()
    assert data_put["editor_can_mark_objective"] is False
    assert data_put["editor_can_mark_global"] is True

    # GET deve retornar valores atualizados
    resp_get = client.get(f"/api/v2/brands/{brand_id}/editorial-policy")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["editor_can_mark_objective"] is False
    assert data_get["editor_can_mark_global"] is True


def test_editorial_policy_is_idempotent(tmp_path: Path) -> None:
    """PUT com mesmo Idempotency-Key deve ser idempotente."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "policy-b5"}, 
        json={"name": "Acme"}
    ).json()["brand_id"]

    # Primeira chamada
    resp1 = client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={
            "Idempotency-Key": "idem-same",
            "Authorization": "Bearer admin:admin"
        },
        json={"editor_can_mark_objective": False}
    )
    assert resp1.status_code == 200
    updated_at_1 = resp1.json()["updated_at"]

    # Segunda chamada com mesmo Idempotency-Key - deve retornar mesmo resultado
    resp2 = client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={
            "Idempotency-Key": "idem-same",
            "Authorization": "Bearer admin:admin"
        },
        json={"editor_can_mark_objective": True}  # Valor diferente, mas deve ignorar
    )
    assert resp2.status_code == 200
    # Deve retornar os valores da primeira chamada (idempotência)
    assert resp2.json()["editor_can_mark_objective"] is False


def test_mark_golden_uses_brand_policy(tmp_path: Path) -> None:
    """Endpoint mark golden deve respeitar policy da brand (não hardcode)."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    client = TestClient(app)

    # Criar estrutura
    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "policy-b6"}, 
        json={"name": "Acme"}
    ).json()["brand_id"]
    
    project_id = client.post(
        "/api/v2/projects", 
        headers={"Idempotency-Key": "policy-p6"}, 
        json={"brand_id": brand_id, "name": "Launch"}
    ).json()["project_id"]
    
    thread_id = client.post(
        "/api/v2/threads", 
        headers={"Idempotency-Key": "policy-t6"}, 
        json={"brand_id": brand_id, "project_id": project_id, "title": "Planning"}
    ).json()["thread_id"]
    
    run_id = client.post(
        f"/api/v2/threads/{thread_id}/workflow-runs", 
        headers={"Idempotency-Key": "policy-run6"}, 
        json={"request_text": "Campanha", "mode": "content_calendar"}
    ).json()["run_id"]

    # Desabilitar editor_can_mark_objective na policy
    client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={
            "Idempotency-Key": "policy-update-6",
            "Authorization": "Bearer admin:admin"
        },
        json={"editor_can_mark_objective": False}
    )

    # Editor tentando marcar objective - deve falhar devido à policy
    resp = client.post(
        f"/api/v2/threads/{thread_id}/editorial-decisions/golden",
        headers={
            "Idempotency-Key": "policy-mark-6",
            "Authorization": "Bearer editor:editor"
        },
        json={
            "run_id": run_id, 
            "scope": "objective", 
            "objective_key": "obj-123",
            "justification": "test policy"
        }
    )
    # Se a policy for respeitada, editor não pode marcar objective quando editor_can_mark_objective=False
    assert resp.status_code == 403
