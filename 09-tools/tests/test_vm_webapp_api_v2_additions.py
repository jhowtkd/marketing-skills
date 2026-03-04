"""
VM Studio v17 - API v2 Safety Auto-Tuning Endpoints Tests

Testes para endpoints:
- GET /v2/safety-tuning/status
- POST /v2/safety-tuning/run (propose)
- POST /v2/safety-tuning/apply
- POST /v2/safety-tuning/revert
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from vm_webapp.app import create_app
from vm_webapp.settings import Settings


class TestSafetyTuningAPI:
    """Test safety tuning API endpoints."""
    
    def test_get_status_endpoint(self, tmp_path: Path):
        """GET /v2/safety-tuning/status returns current status."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        
        response = client.get("/v2/safety-tuning/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "last_cycle_at" in data
        assert "gates" in data
    
    def test_post_run_propose_endpoint(self, tmp_path: Path):
        """POST /v2/safety-tuning/run executa análise e retorna propostas."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        
        response = client.post(
            "/v2/safety-tuning/run",
            json={"mode": "propose"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cycle_id" in data
        assert "proposals" in data
        assert "proposals_count" in data
    
    def test_post_apply_endpoint(self, tmp_path: Path):
        """POST /v2/safety-tuning/{proposal_id}/apply aplica proposta."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        
        # Primeiro executa um ciclo para ter propostas
        run_response = client.post(
            "/v2/safety-tuning/run",
            json={"mode": "propose"}
        )
        
        # Se houver propostas, tenta aplicar
        proposals = run_response.json().get("proposals", [])
        if proposals:
            proposal_id = proposals[0]["proposal_id"]
            
            apply_response = client.post(
                f"/v2/safety-tuning/{proposal_id}/apply",
                json={"auto": False}
            )
            
            assert apply_response.status_code == 200
            data = apply_response.json()
            assert "applied" in data
            assert "previous_value" in data
            assert "new_value" in data
    
    def test_post_revert_endpoint_not_found(self, tmp_path: Path):
        """POST /v2/safety-tuning/{proposal_id}/revert retorna 404 para proposta inexistente."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        
        # Testa que endpoint existe e valida que precisa de proposta aplicada
        revert_response = client.post(
            "/v2/safety-tuning/nonexistent/revert",
            json={}
        )
        
        # Deve retornar 404 para proposta inexistente
        assert revert_response.status_code == 404
        data = revert_response.json()
        assert "not found" in data["detail"].lower()
    
    def test_post_freeze_endpoint(self, tmp_path: Path):
        """POST /v2/safety-tuning/gates/{gate_name}/freeze congela gate."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        
        response = client.post(
            "/v2/safety-tuning/gates/sample_size/freeze",
            json={"reason": "manual_review"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["frozen"] is True
        assert data["gate_name"] == "sample_size"
    
    def test_post_unfreeze_endpoint(self, tmp_path: Path):
        """POST /v2/safety-tuning/gates/{gate_name}/unfreeze descongela gate."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        
        # Primeiro congela
        client.post(
            "/v2/safety-tuning/gates/sample_size/freeze",
            json={"reason": "manual_review"}
        )
        
        # Depois descongela
        response = client.post(
            "/v2/safety-tuning/gates/sample_size/unfreeze",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["frozen"] is False
        assert data["gate_name"] == "sample_size"
    
    def test_get_audit_trail_endpoint(self, tmp_path: Path):
        """GET /v2/safety-tuning/audit retorna trilha de auditoria."""
        app = create_app(
            settings=Settings(
                vm_workspace_root=tmp_path / "runtime" / "vm",
                vm_db_path=tmp_path / "runtime" / "vm" / "workspace.sqlite3",
            )
        )
        client = TestClient(app)
        
        response = client.get("/v2/safety-tuning/audit")
        
        assert response.status_code == 200
        data = response.json()
        assert "cycles" in data
        assert "total_cycles" in data
        assert "applied_count" in data
        assert "rollback_count" in data
