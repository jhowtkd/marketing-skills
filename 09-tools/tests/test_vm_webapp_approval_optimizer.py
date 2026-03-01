"""
Tests for Approval Cost Optimizer - Task 1 & 2 v23
TDD: fail -> implement -> pass -> commit
"""

import pytest
from datetime import datetime, timezone


class TestRiskTriageRefiner:
    """Test Task 1: Risk triage refiner."""

    def test_refine_risk_for_approval_request(self):
        """Testa refino de risco para request de aprovação."""
        from vm_webapp.approval_optimizer import RiskTriageRefiner
        
        refiner = RiskTriageRefiner()
        
        request = {
            "request_id": "req_001",
            "node_type": "publish",
            "risk_level": "medium",
            "params": {"impact": "high", "revenue_at_risk": 10000},
        }
        
        refined = refiner.refine_risk(request)
        
        assert "refined_risk_score" in refined
        assert "risk_factors" in refined
        assert isinstance(refined["refined_risk_score"], float)
        assert 0 <= refined["refined_risk_score"] <= 1

    def test_risk_factors_identification(self):
        """Testa identificação de fatores de risco."""
        from vm_webapp.approval_optimizer import RiskTriageRefiner
        
        refiner = RiskTriageRefiner()
        
        # High impact request
        request_high = {
            "request_id": "req_001",
            "node_type": "publish",
            "risk_level": "high",
            "params": {"impact": "critical", "revenue_at_risk": 50000},
        }
        
        refined_high = refiner.refine_risk(request_high)
        
        # Should have risk factors
        assert len(refined_high["risk_factors"]) > 0
        assert any("critical" in f.lower() or "high" in f.lower() 
                   for f in refined_high["risk_factors"])

    def test_refine_risk_deterministic(self):
        """Testa que refino é determinístico para mesma entrada."""
        from vm_webapp.approval_optimizer import RiskTriageRefiner
        
        refiner = RiskTriageRefiner()
        
        request = {
            "request_id": "req_001",
            "node_type": "publish",
            "risk_level": "medium",
            "params": {"impact": "medium"},
        }
        
        refined1 = refiner.refine_risk(request)
        refined2 = refiner.refine_risk(request)
        
        assert refined1["refined_risk_score"] == refined2["refined_risk_score"]


class TestPriorityScorer:
    """Test Task 1: Priority scorer."""

    def test_calculate_priority_score(self):
        """Testa cálculo de score de prioridade."""
        from vm_webapp.approval_optimizer import PriorityScorer
        
        scorer = PriorityScorer()
        
        request = {
            "request_id": "req_001",
            "refined_risk_score": 0.7,
            "urgency": "high",
            "wait_time_seconds": 300,
            "business_impact": 10000,
        }
        
        score = scorer.calculate_priority(request)
        
        assert "priority_score" in score
        assert "priority_level" in score
        assert isinstance(score["priority_score"], float)
        assert score["priority_level"] in ["critical", "high", "medium", "low"]

    def test_priority_considers_urgency_and_impact(self):
        """Testa que prioridade considera urgência e impacto."""
        from vm_webapp.approval_optimizer import PriorityScorer
        
        scorer = PriorityScorer()
        
        # High urgency, high impact
        urgent = {
            "request_id": "req_001",
            "refined_risk_score": 0.5,
            "urgency": "critical",
            "wait_time_seconds": 600,
            "business_impact": 50000,
        }
        
        # Low urgency, low impact
        normal = {
            "request_id": "req_002",
            "refined_risk_score": 0.5,
            "urgency": "low",
            "wait_time_seconds": 30,
            "business_impact": 100,
        }
        
        urgent_score = scorer.calculate_priority(urgent)
        normal_score = scorer.calculate_priority(normal)
        
        assert urgent_score["priority_score"] > normal_score["priority_score"]

    def test_priority_queue_ordering(self):
        """Testa ordenação determinística da fila."""
        from vm_webapp.approval_optimizer import PriorityScorer
        
        scorer = PriorityScorer()
        
        requests = [
            {"request_id": "req_001", "refined_risk_score": 0.3, "urgency": "low", 
             "wait_time_seconds": 100, "business_impact": 100},
            {"request_id": "req_002", "refined_risk_score": 0.8, "urgency": "high",
             "wait_time_seconds": 500, "business_impact": 10000},
            {"request_id": "req_003", "refined_risk_score": 0.5, "urgency": "medium",
             "wait_time_seconds": 200, "business_impact": 1000},
        ]
        
        ordered = scorer.order_queue(requests)
        
        # Should be ordered by priority (highest first)
        assert ordered[0]["request_id"] == "req_002"  # Highest priority
        assert ordered[-1]["request_id"] == "req_001"  # Lowest priority

    def test_deterministic_ordering_same_priority(self):
        """Testa ordenação determinística para mesma prioridade."""
        from vm_webapp.approval_optimizer import PriorityScorer
        
        scorer = PriorityScorer()
        
        requests = [
            {"request_id": "req_001", "refined_risk_score": 0.5, "urgency": "medium",
             "wait_time_seconds": 100, "business_impact": 1000, "created_at": "2026-03-01T10:00:00"},
            {"request_id": "req_002", "refined_risk_score": 0.5, "urgency": "medium",
             "wait_time_seconds": 200, "business_impact": 1000, "created_at": "2026-03-01T09:00:00"},
        ]
        
        ordered = scorer.order_queue(requests)
        
        # Older request should come first (FIFO tie-breaker)
        assert ordered[0]["request_id"] == "req_002"


class TestApprovalOptimizer:
    """Test integrated approval optimizer."""

    def test_optimizer_initialization(self):
        """Testa inicialização do optimizer."""
        from vm_webapp.approval_optimizer import ApprovalOptimizer
        
        optimizer = ApprovalOptimizer()
        
        assert optimizer is not None

    def test_add_request_to_optimizer(self):
        """Testa adicionar request ao optimizer."""
        from vm_webapp.approval_optimizer import ApprovalOptimizer
        
        optimizer = ApprovalOptimizer()
        
        request = {
            "request_id": "req_001",
            "run_id": "run_001",
            "node_id": "node_a",
            "node_type": "publish",
            "risk_level": "medium",
            "brand_id": "brand_001",
        }
        
        optimizer.add_request(request)
        
        queue = optimizer.get_queue()
        assert len(queue) == 1
        assert queue[0]["request_id"] == "req_001"

    def test_get_prioritized_queue(self):
        """Testa obtenção de fila priorizada."""
        from vm_webapp.approval_optimizer import ApprovalOptimizer
        
        optimizer = ApprovalOptimizer()
        
        # Add multiple requests
        optimizer.add_request({
            "request_id": "req_001",
            "run_id": "run_001",
            "node_id": "node_a",
            "node_type": "research",
            "risk_level": "low",
            "brand_id": "brand_001",
        })
        
        optimizer.add_request({
            "request_id": "req_002",
            "run_id": "run_002",
            "node_id": "node_b",
            "node_type": "publish",
            "risk_level": "high",
            "brand_id": "brand_001",
        })
        
        queue = optimizer.get_queue()
        
        # High risk should be first
        assert queue[0]["request_id"] == "req_002"


# Task 2: Batching engine tests

class TestBatchingEngine:
    """Test Task 2: Batching engine."""

    def test_create_compatible_batch(self):
        """Testa criação de lote compatível."""
        from vm_webapp.approval_optimizer import BatchingEngine
        
        batcher = BatchingEngine(max_batch_size=5)
        
        requests = [
            {"request_id": "req_001", "brand_id": "brand_001", "risk_level": "medium"},
            {"request_id": "req_002", "brand_id": "brand_001", "risk_level": "medium"},
            {"request_id": "req_003", "brand_id": "brand_001", "risk_level": "medium"},
        ]
        
        batch = batcher.create_batch(requests)
        
        assert batch is not None
        assert "batch_id" in batch
        assert len(batch["requests"]) <= 5

    def test_batch_same_brand_only(self):
        """Testa que lote só inclui requests do mesmo brand."""
        from vm_webapp.approval_optimizer import BatchingEngine
        
        batcher = BatchingEngine()
        
        requests = [
            {"request_id": "req_001", "brand_id": "brand_001", "risk_level": "medium"},
            {"request_id": "req_002", "brand_id": "brand_002", "risk_level": "medium"},
        ]
        
        # Should create separate batches or filter
        with pytest.raises(ValueError):
            batcher.create_batch(requests, enforce_single_brand=True)

    def test_batch_size_limit(self):
        """Testa limite de tamanho do lote."""
        from vm_webapp.approval_optimizer import BatchingEngine
        
        batcher = BatchingEngine(max_batch_size=3)
        
        requests = [
            {"request_id": f"req_{i:03d}", "brand_id": "brand_001", "risk_level": "medium"}
            for i in range(10)
        ]
        
        batch = batcher.create_batch(requests)
        
        assert len(batch["requests"]) <= 3

    def test_batch_expiration(self):
        """Testa expiração de lote."""
        from vm_webapp.approval_optimizer import BatchingEngine, ApprovalBatch
        
        batcher = BatchingEngine(batch_ttl_seconds=3600)
        
        batch = batcher.create_batch([
            {"request_id": "req_001", "brand_id": "brand_001"},
        ])
        
        # Check not expired
        assert not batcher.is_expired(batch["batch_id"])
        
        # Simulate expiration by creating an expired batch
        expired_batch = ApprovalBatch(
            batch_id=batch["batch_id"],
            brand_id="brand_001",
            requests=[],
            expires_at="2026-02-01T00:00:00+00:00",  # Past date
        )
        batcher._batches[batch["batch_id"]] = expired_batch
        
        assert batcher.is_expired(batch["batch_id"])

    def test_fallback_to_individual_queue(self):
        """Testa fallback para fila individual."""
        from vm_webapp.approval_optimizer import BatchingEngine
        
        batcher = BatchingEngine()
        
        # Request that cannot be batched
        request = {"request_id": "req_001", "brand_id": "brand_001", "risk_level": "high"}
        
        # Force fallback
        result = batcher.process_with_fallback(request)
        
        assert result["mode"] in ["batch", "individual"]


class TestBatchGuards:
    """Test batch guards and safety."""

    def test_guard_max_batch_value(self):
        """Testa guarda de valor máximo do lote."""
        from vm_webapp.approval_optimizer import BatchGuard
        
        guard = BatchGuard(max_total_value=100000)
        
        requests = [
            {"request_id": "req_001", "business_value": 60000},
            {"request_id": "req_002", "business_value": 60000},  # Would exceed
        ]
        
        assert not guard.validate_batch(requests)

    def test_guard_risk_level_mixing(self):
        """Testa que não mistura risk levels incompatíveis."""
        from vm_webapp.approval_optimizer import BatchGuard
        
        guard = BatchGuard()
        
        # Should not batch high and low risk together
        requests = [
            {"request_id": "req_001", "risk_level": "high"},
            {"request_id": "req_002", "risk_level": "low"},
        ]
        
        assert not guard.validate_batch(requests)

    def test_guard_approval_required(self):
        """Testa que batch requer aprovação quando necessário."""
        from vm_webapp.approval_optimizer import BatchGuard
        
        guard = BatchGuard(auto_approve_threshold=0.3)
        
        # High risk batch should require approval
        batch = {"risk_score": 0.8, "requests": []}
        
        assert guard.requires_approval(batch)
