"""
Tests for Approval Cost Optimizer - v23

Coverage:
- Risk triage refiner
- Priority scorer  
- Batching engine
- Batch guards
"""

import pytest
from datetime import datetime, timedelta, timezone

from vm_webapp.approval_optimizer import (
    ApprovalRequest,
    ApprovalOptimizer,
    PriorityScorer,
    RiskTriageRefiner,
    BatchingEngine,
    BatchGuard,
    BatchSizeLimits,
)


class TestRiskTriageRefiner:
    """Test risk triage refinement"""

    def test_refine_risk_for_approval_request(self):
        """Should refine risk level based on multiple factors"""
        refiner = RiskTriageRefiner()
        request = ApprovalRequest(
            request_id="req-001",
            run_id="run-001",
            node_id="node-1",
            node_type="email_send",
            risk_level="medium",
            brand_id="brand-1",
            impact_score=0.8,
        )

        result = refiner.refine(request)

        assert "original_risk" in result
        assert "refined_risk_score" in result
        assert "factors" in result
        assert 0 <= result["refined_risk_score"] <= 1

    def test_risk_factors_identification(self):
        """Should identify risk factors"""
        refiner = RiskTriageRefiner()
        request = ApprovalRequest(
            request_id="req-002",
            run_id="run-001",
            node_id="node-1",
            node_type="sms_send",
            risk_level="high",
            brand_id="brand-1",
            impact_score=0.9,
        )

        result = refiner.refine(request)
        factors = result.get("factors", {})

        assert isinstance(factors, dict)
        assert len(factors) > 0

    def test_refine_risk_deterministic(self):
        """Same input should produce same output (deterministic)"""
        refiner = RiskTriageRefiner()
        request = ApprovalRequest(
            request_id="req-003",
            run_id="run-001",
            node_id="node-1",
            node_type="email_send",
            risk_level="low",
            brand_id="brand-1",
            impact_score=0.5,
        )

        result1 = refiner.refine(request)
        result2 = refiner.refine(request)

        assert result1["refined_risk_score"] == result2["refined_risk_score"]


class TestPriorityScorer:
    """Test priority scoring"""

    def test_calculate_priority_score(self):
        """Should calculate priority score between 0-1"""
        scorer = PriorityScorer()
        request = ApprovalRequest(
            request_id="req-004",
            run_id="run-001",
            node_id="node-1",
            node_type="email_send",
            risk_level="medium",
            brand_id="brand-1",
            impact_score=0.7,
            urgency_hours=4.0,
        )

        score = scorer.calculate_priority(request)

        assert 0 <= score <= 1
        assert score > 0.5  # medium risk + high impact/urgency

    def test_priority_considers_urgency_and_impact(self):
        """Priority should increase with urgency and impact"""
        scorer = PriorityScorer()

        low_priority = ApprovalRequest(
            request_id="req-005",
            run_id="run-001",
            node_id="node-1",
            node_type="email_send",
            risk_level="low",
            brand_id="brand-1",
            impact_score=0.2,
            urgency_hours=48.0,
        )

        high_priority = ApprovalRequest(
            request_id="req-006",
            run_id="run-001",
            node_id="node-2",
            node_type="email_send",
            risk_level="high",
            brand_id="brand-1",
            impact_score=0.9,
            urgency_hours=1.0,
        )

        low_score = scorer.calculate_priority(low_priority)
        high_score = scorer.calculate_priority(high_priority)

        assert high_score > low_score

    def test_priority_queue_ordering(self):
        """Should produce correctly ordered queue"""
        scorer = PriorityScorer()
        optimizer = ApprovalOptimizer()

        # Add requests in random order
        requests = [
            ApprovalRequest(
                request_id=f"req-{i}",
                run_id="run-001",
                node_id=f"node-{i}",
                node_type="email_send",
                risk_level=["low", "medium", "high"][i % 3],
                brand_id="brand-1",
                impact_score=0.3 + (i * 0.2),
            )
            for i in range(5)
        ]

        for req in requests:
            optimizer.add_request(req)

        queue = optimizer.get_prioritized_queue()

        # Queue should be ordered by priority descending
        for i in range(len(queue) - 1):
            assert queue[i]["priority_score"] >= queue[i + 1]["priority_score"]

    def test_deterministic_ordering_same_priority(self):
        """Same priority items should have deterministic order"""
        scorer = PriorityScorer()

        req1 = ApprovalRequest(
            request_id="req-007",
            run_id="run-001",
            node_id="node-1",
            node_type="email_send",
            risk_level="medium",
            brand_id="brand-1",
            impact_score=0.5,
        )

        req2 = ApprovalRequest(
            request_id="req-008",
            run_id="run-001",
            node_id="node-2",
            node_type="email_send",
            risk_level="medium",
            brand_id="brand-1",
            impact_score=0.5,
        )

        # Multiple runs should give consistent results
        results = []
        for _ in range(3):
            optimizer = ApprovalOptimizer()
            optimizer.add_request(req1)
            optimizer.add_request(req2)
            queue = optimizer.get_prioritized_queue()
            results.append([item["request_id"] for item in queue])

        # All results should be identical
        assert results[0] == results[1] == results[2]


class TestApprovalOptimizer:
    """Test main optimizer"""

    def test_optimizer_initialization(self):
        """Optimizer should initialize with empty state"""
        optimizer = ApprovalOptimizer()
        assert optimizer.get_prioritized_queue() == []

    def test_add_request_to_optimizer(self):
        """Should add request to optimizer"""
        optimizer = ApprovalOptimizer()
        request = ApprovalRequest(
            request_id="req-009",
            run_id="run-001",
            node_id="node-1",
            node_type="email_send",
            risk_level="medium",
            brand_id="brand-1",
        )

        optimizer.add_request(request)
        queue = optimizer.get_prioritized_queue()

        assert len(queue) == 1
        assert queue[0]["request_id"] == "req-009"

    def test_get_prioritized_queue(self):
        """Should return queue with priority metadata"""
        optimizer = ApprovalOptimizer()

        for i in range(3):
            optimizer.add_request(
                ApprovalRequest(
                    request_id=f"req-00{i}",
                    run_id="run-001",
                    node_id=f"node-{i}",
                    node_type="email_send",
                    risk_level="medium",
                    brand_id="brand-1",
                    impact_score=0.5 + (i * 0.1),
                )
            )

        queue = optimizer.get_prioritized_queue()

        assert len(queue) == 3
        for item in queue:
            assert "request_id" in item
            assert "priority_score" in item
            assert "priority_level" in item
            assert "refined_risk_score" in item


class TestBatchingEngine:
    """Test batching engine"""

    def test_create_compatible_batch(self):
        """Should create batch from compatible requests"""
        engine = BatchingEngine()
        requests = [
            ApprovalRequest(
                request_id=f"req-00{i}",
                run_id="run-001",
                node_id=f"node-{i}",
                node_type="email_send",
                risk_level="medium",
                brand_id="brand-1",
            )
            for i in range(3)
        ]

        batch = engine.create_batch(requests, brand_id="brand-1")

        assert batch is not None
        assert batch.brand_id == "brand-1"
        assert len(batch.requests) == 3

    def test_batch_same_brand_only(self):
        """Batch should only contain same brand requests"""
        engine = BatchingEngine()
        requests = [
            ApprovalRequest(
                request_id="req-001",
                run_id="run-001",
                node_id="node-1",
                node_type="email_send",
                risk_level="medium",
                brand_id="brand-1",
            ),
            ApprovalRequest(
                request_id="req-002",
                run_id="run-001",
                node_id="node-2",
                node_type="email_send",
                risk_level="medium",
                brand_id="brand-2",  # Different brand
            ),
        ]

        # Should not create batch with mixed brands
        batch = engine.create_batch(requests, brand_id="brand-1")
        assert batch is None or len(batch.requests) == 1

    def test_batch_size_limit(self):
        """Batch should respect size limits"""
        engine = BatchingEngine()
        limits = BatchSizeLimits(max_batch_size=5)

        # Create more requests than limit
        requests = [
            ApprovalRequest(
                request_id=f"req-00{i}",
                run_id="run-001",
                node_id=f"node-{i}",
                node_type="email_send",
                risk_level="medium",
                brand_id="brand-1",
            )
            for i in range(10)
        ]

        batch = engine.create_batch(requests, brand_id="brand-1", limits=limits)

        assert batch is not None
        assert len(batch.requests) <= limits.max_batch_size

    def test_batch_expiration(self):
        """Batch should have expiration time"""
        engine = BatchingEngine()
        requests = [
            ApprovalRequest(
                request_id="req-001",
                run_id="run-001",
                node_id="node-1",
                node_type="email_send",
                risk_level="medium",
                brand_id="brand-1",
            )
        ]

        batch = engine.create_batch(requests, brand_id="brand-1")

        assert batch is not None
        assert batch.expires_at is not None

        # Check expiration is in the future
        now = datetime.now(timezone.utc)
        if isinstance(batch.expires_at, str):
            expires = datetime.fromisoformat(batch.expires_at)
        else:
            expires = batch.expires_at
        assert expires > now

    def test_fallback_to_individual_queue(self):
        """Should fallback to individual queue when batching fails"""
        optimizer = ApprovalOptimizer()

        # Add requests
        for i in range(3):
            optimizer.add_request(
                ApprovalRequest(
                    request_id=f"req-00{i}",
                    run_id="run-001",
                    node_id=f"node-{i}",
                    node_type="email_send",
                    risk_level="medium",
                    brand_id="brand-1",
                )
            )

        # Simulate batching failure by calling with invalid brand
        batch = optimizer.create_batch(brand_id="non-existent-brand")

        # Should return None but not crash
        assert batch is None

        # Queue should still be accessible
        queue = optimizer.get_prioritized_queue()
        assert len(queue) == 3


class TestBatchGuards:
    """Test batch safety guards"""

    def test_guard_max_batch_value(self):
        """Should enforce max batch value limit"""
        guard = BatchGuard()
        requests = [
            ApprovalRequest(
                request_id="req-001",
                run_id="run-001",
                node_id="node-1",
                node_type="high_value_campaign",
                risk_level="high",
                brand_id="brand-1",
                impact_score=1.0,
            )
        ]

        # Single high-value item should be ok
        assert guard.validate_batch_compatibility(requests)

    def test_guard_risk_level_mixing(self):
        """Should prevent mixing incompatible risk levels"""
        guard = BatchGuard()

        compatible = [
            ApprovalRequest(
                request_id="req-001",
                run_id="run-001",
                node_id="node-1",
                node_type="email_send",
                risk_level="medium",
                brand_id="brand-1",
            ),
            ApprovalRequest(
                request_id="req-002",
                run_id="run-001",
                node_id="node-2",
                node_type="email_send",
                risk_level="medium",
                brand_id="brand-1",
            ),
        ]

        assert guard.validate_batch_compatibility(compatible)

    def test_guard_approval_required(self):
        """Should identify batches requiring approval"""
        guard = BatchGuard()
        batch = type(
            "Batch",
            (),
            {"total_value": 15000, "risk_score": 0.7, "requests": []},
        )()

        assert guard.requires_approval(batch)


class TestMetrics:
    """Test Prometheus metrics integration"""

    def test_metrics_include_expected_keys(self):
        """Metrics should include expected Prometheus keys"""
        from vm_webapp.agent_dag_audit import metrics

        # Record some operations
        metrics.record_batch_created(5)
        metrics.record_batch_approved()
        metrics.record_queue_length(10)

        snapshot = metrics.get_snapshot()

        # Verify expected keys exist
        assert "batches_created_total" in snapshot
        assert "batches_approved_total" in snapshot
        assert "human_minutes_saved" in snapshot
        assert "approval_queue_p95" in snapshot

        # Verify types
        assert isinstance(snapshot["batches_created_total"], int)
        assert isinstance(snapshot["human_minutes_saved"], (int, float))
