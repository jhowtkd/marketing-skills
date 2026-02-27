"""Testes para policy editorial multi-tenant por brand.

TDD estrito: fail -> mínimo -> pass -> commit
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.db import session_scope
from vm_webapp.editorial_policy import (
    BrandPolicy,
    PolicyDecision,
    PolicyEvaluator,
    Role,
    Scope,
    create_evaluator_from_session,
)
from vm_webapp.settings import Settings


# =============================================================================
# Testes Unitários do Módulo editorial_policy
# =============================================================================

def test_policy_evaluator_admin_can_global():
    """Admin pode marcar golden global."""
    evaluator = PolicyEvaluator()
    result = evaluator.evaluate(role=Role.ADMIN, scope=Scope.GLOBAL)
    assert result.allowed is True
    assert "admin" in result.reason.lower()


def test_policy_evaluator_admin_can_objective():
    """Admin pode marcar golden objective."""
    evaluator = PolicyEvaluator()
    result = evaluator.evaluate(role=Role.ADMIN, scope=Scope.OBJECTIVE)
    assert result.allowed is True


def test_policy_evaluator_viewer_cannot_any_scope():
    """Viewer não pode marcar golden em nenhum escopo."""
    evaluator = PolicyEvaluator()
    
    result_global = evaluator.evaluate(role=Role.VIEWER, scope=Scope.GLOBAL)
    assert result_global.allowed is False
    assert "viewer" in result_global.reason.lower()
    
    result_obj = evaluator.evaluate(role=Role.VIEWER, scope=Scope.OBJECTIVE)
    assert result_obj.allowed is False


def test_policy_evaluator_editor_can_objective_with_default_policy():
    """Editor pode marcar objective com policy padrão."""
    evaluator = PolicyEvaluator()
    result = evaluator.evaluate(role=Role.EDITOR, scope=Scope.OBJECTIVE)
    assert result.allowed is True
    assert "objective" in result.reason.lower()


def test_policy_evaluator_editor_cannot_global_with_default_policy():
    """Editor não pode marcar global com policy padrão (editor_can_mark_global=False)."""
    evaluator = PolicyEvaluator()
    result = evaluator.evaluate(role=Role.EDITOR, scope=Scope.GLOBAL)
    assert result.allowed is False
    assert "global" in result.reason.lower()


def test_policy_evaluator_editor_can_global_when_policy_allows():
    """Editor pode marcar global quando policy permite."""
    policy = BrandPolicy(editor_can_mark_global=True)
    
    class MockStore:
        def get_policy(self, brand_id: str):
            return policy
    
    evaluator = PolicyEvaluator(store=MockStore())
    result = evaluator.evaluate(
        role=Role.EDITOR, 
        scope=Scope.GLOBAL, 
        brand_id="test-brand"
    )
    assert result.allowed is True


def test_policy_evaluator_editor_cannot_objective_when_policy_denies():
    """Editor não pode marcar objective quando policy nega."""
    policy = BrandPolicy(editor_can_mark_objective=False)
    
    class MockStore:
        def get_policy(self, brand_id: str):
            return policy
    
    evaluator = PolicyEvaluator(store=MockStore())
    result = evaluator.evaluate(
        role=Role.EDITOR, 
        scope=Scope.OBJECTIVE, 
        brand_id="test-brand"
    )
    assert result.allowed is False
    assert "policy denies" in result.reason.lower()


def test_policy_evaluator_fallback_to_default_when_store_none():
    """Fallback para policy default quando store é None."""
    evaluator = PolicyEvaluator(store=None)
    result = evaluator.evaluate(role=Role.EDITOR, scope=Scope.OBJECTIVE)
    assert result.allowed is True  # Default allows objective


def test_policy_evaluator_fallback_to_default_when_brand_id_none():
    """Fallback para policy default quando brand_id é None."""
    evaluator = PolicyEvaluator()
    result = evaluator.evaluate(role=Role.EDITOR, scope=Scope.OBJECTIVE, brand_id=None)
    assert result.allowed is True  # Default allows objective


def test_policy_evaluator_fallback_to_default_when_policy_not_found():
    """Fallback para policy default quando policy não existe no store."""
    class EmptyStore:
        def get_policy(self, brand_id: str):
            return None
    
    evaluator = PolicyEvaluator(store=EmptyStore())
    result = evaluator.evaluate(
        role=Role.EDITOR, 
        scope=Scope.OBJECTIVE, 
        brand_id="nonexistent-brand"
    )
    assert result.allowed is True  # Default allows objective


def test_policy_evaluator_handles_string_inputs():
    """Evaluator deve aceitar strings em vez de enums."""
    evaluator = PolicyEvaluator()
    
    result = evaluator.evaluate(role="admin", scope="global")
    assert result.allowed is True
    
    result = evaluator.evaluate(role="editor", scope="objective")
    assert result.allowed is True


def test_policy_evaluator_unknown_role_denied():
    """Roles desconhecidas são negadas."""
    evaluator = PolicyEvaluator()
    result = evaluator.evaluate(role="unknown", scope="objective")
    assert result.allowed is False
    assert "unknown role" in result.reason.lower()


def test_policy_evaluator_unknown_scope_denied():
    """Scopes desconhecidos são negados para editor."""
    evaluator = PolicyEvaluator()
    result = evaluator.evaluate(role="editor", scope="unknown")
    assert result.allowed is False
    assert "unknown scope" in result.reason.lower()


# =============================================================================
# Policy Matrix Completa (documentação por código)
# =============================================================================

def test_policy_matrix_all_combinations():
    """Matrix completa de role x scope x policy.
    
    Documentação executável de todas as combinações suportadas.
    """
    # (role, scope, editor_obj_flag, editor_global_flag, expected_allowed)
    test_cases = [
        # Admin: sempre pode tudo
        ("admin", "global", False, False, True),
        ("admin", "objective", False, False, True),
        ("admin", "global", True, True, True),
        
        # Viewer: nunca pode nada
        ("viewer", "global", True, True, False),
        ("viewer", "objective", True, True, False),
        
        # Editor: depende da policy
        ("editor", "objective", True, False, True),   # default
        ("editor", "objective", False, False, False), # policy denies
        ("editor", "global", False, False, False),    # default
        ("editor", "global", False, True, True),      # policy allows
    ]
    
    for role, scope, obj_flag, global_flag, expected in test_cases:
        policy = BrandPolicy(
            editor_can_mark_objective=obj_flag,
            editor_can_mark_global=global_flag,
        )
        
        class MockStore:
            def get_policy(self, brand_id: str):
                return policy
        
        evaluator = PolicyEvaluator(store=MockStore())
        result = evaluator.evaluate(role=role, scope=scope, brand_id="test")
        
        assert result.allowed == expected, (
            f"Failed for role={role}, scope={scope}, "
            f"obj_flag={obj_flag}, global_flag={global_flag}"
        )


# =============================================================================
# Integração com API e Database
# =============================================================================

def test_create_evaluator_from_session(tmp_path: Path) -> None:
    """Factory function deve criar evaluator com policy do banco."""
    app = create_app(
        settings=Settings(
            vm_workspace_root=tmp_path / "runtime" / "vm",
            vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
        )
    )
    
    with session_scope(app.state.engine) as session:
        # Criar brand e policy
        from vm_webapp.repo import upsert_editorial_policy
        upsert_editorial_policy(
            session,
            brand_id="test-brand-eval",
            editor_can_mark_objective=False,
            editor_can_mark_global=False,
        )
        
        # Criar evaluator
        evaluator = create_evaluator_from_session(session, "test-brand-eval")
        
        # Verificar que usa policy do banco
        result = evaluator.evaluate(
            role=Role.EDITOR, 
            scope=Scope.OBJECTIVE, 
            brand_id="test-brand-eval"
        )
        assert result.allowed is False  # Policy denies


def test_evaluator_with_real_database_policy(tmp_path: Path) -> None:
    """Evaluator deve funcionar com policy real do banco."""
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
        headers={"Idempotency-Key": "eval-b"}, 
        json={"name": "Acme"}
    ).json()["brand_id"]

    # Configurar policy: editor pode tudo
    client.put(
        f"/api/v2/brands/{brand_id}/editorial-policy",
        headers={
            "Idempotency-Key": "eval-policy",
            "Authorization": "Bearer admin:admin"
        },
        json={
            "editor_can_mark_objective": True,
            "editor_can_mark_global": True,
        }
    )

    # Criar evaluator e verificar
    with session_scope(app.state.engine) as session:
        evaluator = create_evaluator_from_session(session, brand_id)
        
        result_global = evaluator.evaluate(
            role=Role.EDITOR, scope=Scope.GLOBAL, brand_id=brand_id
        )
        assert result_global.allowed is True


# =============================================================================
# Testes de API Endpoints (mantidos da Task A)
# =============================================================================

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
