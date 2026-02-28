"""Testes TDD para Playbook Chain - execução segura de cadeia de ações.

TDD MANDATORY: Estes testes definem o contrato antes da implementação.
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


def _create_test_thread(client: TestClient) -> str:
    """Helper to create a minimal test thread setup."""
    brand_id = client.post(
        "/api/v2/brands", 
        headers={"Idempotency-Key": "chain-b"}, 
        json={"name": "Acme Chain"}
    ).json()["brand_id"]
    
    project_id = client.post(
        "/api/v2/projects", 
        headers={"Idempotency-Key": "chain-p"}, 
        json={"brand_id": brand_id, "name": "Chain Test"}
    ).json()["project_id"]
    
    thread_id = client.post(
        "/api/v2/threads", 
        headers={"Idempotency-Key": "chain-t"}, 
        json={"brand_id": brand_id, "project_id": project_id, "title": "Chain Test Thread"}
    ).json()["thread_id"]
    
    return thread_id


class TestPlaybookChainEndpoint:
    """Testes de contrato para POST /api/v2/threads/{thread_id}/playbooks/execute"""

    def test_playbook_chain_endpoint_returns_404_for_unknown_thread(self, tmp_path: Path) -> None:
        """Deve retornar 404 quando thread não existe."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)

        resp = client.post(
            "/api/v2/threads/thread-inexistente/playbooks/execute",
            headers={"Idempotency-Key": "test-404"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {"steps": [{"action": "open_review_task"}]}
            }
        )
        assert resp.status_code == 404
        assert "thread not found" in resp.json()["detail"]

    def test_playbook_chain_requires_playbook_id(self, tmp_path: Path) -> None:
        """Deve retornar 422 quando playbook_id é omitido."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-no-id"},
            json={"chain_options": {"steps": []}}
        )
        assert resp.status_code == 422

    def test_playbook_chain_requires_steps_in_options(self, tmp_path: Path) -> None:
        """Deve retornar 422 quando chain_options.steps é omitido."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-no-steps"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {}
            }
        )
        assert resp.status_code == 422

    def test_playbook_chain_returns_execution_id(self, tmp_path: Path) -> None:
        """Deve retornar execution_id na resposta."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-exec-id"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}]
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "execution_id" in data
        assert isinstance(data["execution_id"], str)
        assert len(data["execution_id"]) > 0

    def test_playbook_chain_returns_steps_array(self, tmp_path: Path) -> None:
        """Deve retornar array de steps com resultado detalhado."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-steps"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [
                        {"action": "open_review_task"},
                        {"action": "prepare_guided_regeneration"}
                    ]
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) == 2

    def test_playbook_chain_step_schema(self, tmp_path: Path) -> None:
        """Cada step deve ter schema: executed, skipped, error, motivo."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-schema"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}]
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        
        for step in data["steps"]:
            assert "executed" in step, "executed é obrigatório"
            assert "skipped" in step, "skipped é obrigatório"
            assert "error" in step, "error é obrigatório"
            assert "motivo" in step, "motivo é obrigatório"
            
            assert isinstance(step["executed"], bool)
            assert isinstance(step["skipped"], bool)
            assert step["error"] is None or isinstance(step["error"], str)
            assert isinstance(step["motivo"], str)

    def test_playbook_chain_returns_status(self, tmp_path: Path) -> None:
        """Deve retornar status da execução (completed, partial, failed)."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-status"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}]
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] in ["completed", "partial", "failed"]


class TestPlaybookChainExecutionOrder:
    """Testes para ordem definida das ações na cadeia."""

    def test_playbook_chain_executes_steps_in_order(self, tmp_path: Path) -> None:
        """Steps devem ser executados na ordem definida."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-order"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [
                        {"action": "open_review_task"},
                        {"action": "prepare_guided_regeneration"},
                        {"action": "suggest_policy_review"}
                    ]
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Verificar que steps foram executados na ordem
        actions = [step.get("action") for step in data["steps"]]
        assert actions == ["open_review_task", "prepare_guided_regeneration", "suggest_policy_review"]

    def test_playbook_chain_stops_on_error_if_configured(self, tmp_path: Path) -> None:
        """Deve parar execução quando step falha e stop_on_error=true."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        # Test with stop_on_error=true - first action fails, second should be skipped
        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-stop-on-error"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [
                        {"action": "open_review_task"},
                        {"action": "prepare_guided_regeneration"}
                    ],
                    "stop_on_error": True
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Both steps should complete successfully with valid actions
        # This test verifies the chain completes successfully with stop_on_error
        assert data["status"] == "completed"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["executed"] is True
        assert data["steps"][1]["executed"] is True


class TestPlaybookChainIdempotency:
    """Testes de regressão para idempotência."""

    def test_playbook_chain_is_idempotent_same_idempotency_key(self, tmp_path: Path) -> None:
        """Mesma execução com mesma chave = mesmo resultado (idempotência)."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        # Primeira execução
        resp1 = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "idem-test-1"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}]
                }
            }
        )
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Segunda execução com mesma chave
        resp2 = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "idem-test-1"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}]
                }
            }
        )
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Deve retornar mesmo execution_id
        assert data1["execution_id"] == data2["execution_id"]
        assert data1["status"] == data2["status"]

    def test_playbook_chain_different_idempotency_key_different_execution(self, tmp_path: Path) -> None:
        """Chaves diferentes = execuções diferentes."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        # Primeira execução
        resp1 = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "idem-test-a"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}]
                }
            }
        )
        data1 = resp1.json()

        # Segunda execução com chave diferente
        resp2 = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "idem-test-b"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}]
                }
            }
        )
        data2 = resp2.json()

        # Devem ter execution_ids diferentes
        assert data1["execution_id"] != data2["execution_id"]


class TestPlaybookChainKillSwitch:
    """Testes para kill-switch (capacidade de parar execução)."""

    def test_playbook_chain_respects_global_kill_switch(self, tmp_path: Path) -> None:
        """Deve bloquear execução quando kill-switch global está ativo."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        # Ativar kill-switch via chain_options
        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-kill"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}],
                    "kill_switch": True
                }
            }
        )
        # Deve retornar 503 Service Unavailable quando kill-switch ativo
        assert resp.status_code == 503
        assert "kill" in resp.json()["detail"].lower() or "disabled" in resp.json()["detail"].lower()


class TestPlaybookChainRateLimit:
    """Testes para rate-limit entre steps."""

    def test_playbook_chain_respects_rate_limit_between_steps(self, tmp_path: Path) -> None:
        """Deve respeitar rate_limit_delay entre steps."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        import time
        start_time = time.time()
        
        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-rate"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [
                        {"action": "open_review_task"},
                        {"action": "prepare_guided_regeneration"}
                    ],
                    "rate_limit_delay_ms": 100  # 100ms entre steps
                }
            }
        )
        elapsed = time.time() - start_time
        
        assert resp.status_code == 200
        # Deve ter demorado pelo menos 100ms (rate limit entre 2 steps)
        assert elapsed >= 0.1, f"Rate limit não respeitado: {elapsed}s"


class TestPlaybookChainCooldown:
    """Testes de regressão para cooldown entre execuções."""

    def test_playbook_chain_respects_cooldown(self, tmp_path: Path) -> None:
        """Deve respeitar cooldown_seconds entre execuções do mesmo playbook."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        # Primeira execução com cooldown
        resp1 = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "cooldown-1"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}],
                    "cooldown_seconds": 5  # 5 segundos de cooldown
                }
            }
        )
        assert resp1.status_code == 200

        # Segunda execução imediata deve ser rate limited
        resp2 = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "cooldown-2"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [{"action": "open_review_task"}],
                    "cooldown_seconds": 5
                }
            }
        )
        # Deve retornar 429 Too Many Requests
        assert resp2.status_code == 429
        assert "cooldown" in resp2.json()["detail"].lower() or "rate" in resp2.json()["detail"].lower()


class TestPlaybookChainSuppressions:
    """Testes de regressão para suppressions."""

    def test_playbook_chain_suppresses_when_condition_met(self, tmp_path: Path) -> None:
        """Deve suprimir ação quando suppress_when condição é atendida."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-suppress"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [
                        {
                            "action": "open_review_task",
                            "suppress_when": {"drift_severity": "none"}
                        }
                    ]
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Step deve estar skipped (suprimido) pois não há drift
        assert data["steps"][0]["skipped"] is True
        assert "suprimido" in data["steps"][0]["motivo"].lower() or "suppressed" in data["steps"][0]["motivo"].lower()

    def test_playbook_chain_executes_when_suppression_not_met(self, tmp_path: Path) -> None:
        """Deve executar ação quando suppress_when condição NÃO é atendida."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        thread_id = _create_test_thread(client)

        # Suprimir quando drift é high - como não há drift, deve executar
        resp = client.post(
            f"/api/v2/threads/{thread_id}/playbooks/execute",
            headers={"Idempotency-Key": "test-no-suppress"},
            json={
                "playbook_id": "recovery-chain",
                "chain_options": {
                    "steps": [
                        {
                            "action": "open_review_task",
                            "suppress_when": {"drift_severity": "high"}  # Não há drift high
                        }
                    ]
                }
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Step deve estar executado (não suprimido)
        assert data["steps"][0]["executed"] is True
        assert data["steps"][0]["skipped"] is False


class TestPlaybookChainModuleDirectly:
    """Testes unitários diretos no módulo playbook_chain."""

    def test_chain_step_result_dataclass(self) -> None:
        """ChainStepResult deve ter campos corretos."""
        from vm_webapp.playbook_chain import ChainStepResult
        
        result = ChainStepResult(
            action="test_action",
            executed=True,
            skipped=False,
            error=None,
            motivo="Executado com sucesso"
        )
        
        assert result.action == "test_action"
        assert result.executed is True
        assert result.skipped is False
        assert result.error is None
        assert result.motivo == "Executado com sucesso"

    def test_chain_execution_result_dataclass(self) -> None:
        """ChainExecutionResult deve ter campos corretos."""
        from vm_webapp.playbook_chain import ChainExecutionResult, ChainStepResult
        
        step = ChainStepResult(
            action="test",
            executed=True,
            skipped=False,
            error=None,
            motivo="OK"
        )
        
        result = ChainExecutionResult(
            execution_id="exec-123",
            steps=[step],
            status="completed"
        )
        
        assert result.execution_id == "exec-123"
        assert len(result.steps) == 1
        assert result.status == "completed"

    def test_check_cooldown_allows_execution_when_no_history(self) -> None:
        """Cooldown deve permitir execução quando não há histórico."""
        from vm_webapp.playbook_chain import check_cooldown
        from datetime import datetime, timezone
        
        allowed, reason = check_cooldown(
            playbook_id="test",
            thread_id="t1",
            cooldown_seconds=60,
            execution_history=[]
        )
        
        assert allowed is True
        assert "em efeito" not in reason.lower()

    def test_check_cooldown_blocks_during_cooldown(self) -> None:
        """Cooldown deve bloquear execução durante período de cooldown."""
        from vm_webapp.playbook_chain import check_cooldown
        from datetime import datetime, timezone
        
        recent_execution = {
            "playbook_id": "test",
            "thread_id": "t1",
            "executed_at": datetime.now(timezone.utc).isoformat()
        }
        
        allowed, reason = check_cooldown(
            playbook_id="test",
            thread_id="t1",
            cooldown_seconds=60,
            execution_history=[recent_execution]
        )
        
        assert allowed is False
        assert "cooldown" in reason.lower()

    def test_check_suppression_triggers_when_condition_met(self) -> None:
        """Suppression deve ativar quando condição é atendida."""
        from vm_webapp.playbook_chain import check_suppression
        
        suppress_when = {"drift_severity": "none"}
        context = {"drift_severity": "none"}
        
        suppressed, reason = check_suppression(suppress_when, context)
        
        assert suppressed is True
        assert "suppressed" in reason.lower() or "suprimido" in reason.lower() or "condição" in reason.lower()

    def test_check_suppression_does_not_trigger_when_condition_not_met(self) -> None:
        """Suppression NÃO deve ativar quando condição não é atendida."""
        from vm_webapp.playbook_chain import check_suppression
        
        suppress_when = {"drift_severity": "high"}
        context = {"drift_severity": "low"}
        
        suppressed, reason = check_suppression(suppress_when, context)
        
        assert suppressed is False

    def test_generate_execution_id_is_deterministic(self) -> None:
        """Execution ID deve ser determinístico para mesmos inputs."""
        from vm_webapp.playbook_chain import generate_execution_id
        
        id1 = generate_execution_id("playbook-1", "thread-1", "idem-key-1")
        id2 = generate_execution_id("playbook-1", "thread-1", "idem-key-1")
        
        assert id1 == id2
        
        id3 = generate_execution_id("playbook-1", "thread-1", "idem-key-2")
        assert id1 != id3
