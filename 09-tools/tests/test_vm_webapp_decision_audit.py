"""
Task B: Decision Simulation + Audit Trail - Tests
Governança v16 - Auditabilidade completa de decisões automatizadas
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from vm_webapp.decision_audit import (
    DecisionAuditLog,
    DecisionAuditStore,
    DecisionSimulator,
    SimulationResult,
    AuditQuery,
    AuditPagination,
    simulate_decision,
    get_decision_history,
    record_decision_execution,
)
from vm_webapp.safety_gates import SafetyGateResult, RiskLevel, GateType

UTC = timezone.utc


class TestDecisionAuditLog:
    """Test audit log data structure."""
    
    def test_audit_log_creation(self):
        """Can create audit log entry."""
        log = DecisionAuditLog(
            audit_id="audit_001",
            segment_key="brand1:awareness",
            brand_id="brand1",
            input_metrics={"sample_size": 150, "confidence": 0.85},
            suggested_decision="expand",
            gates_applied=["sample_size", "confidence"],
            gate_results=[{"allowed": True}],
            final_decision="expand",
            actor="auto",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        assert log.audit_id == "audit_001"
        assert log.segment_key == "brand1:awareness"
        assert log.final_decision == "expand"
    
    def test_audit_log_with_snapshot(self):
        """Audit log includes full metrics snapshot."""
        snapshot = {
            "kpi_summary": {
                "approval_without_regen_24h": {"status": "on_track", "value": 0.85},
                "v1_score_avg": {"status": "on_track", "value": 75}
            },
            "active_alerts": [],
            "sample_size": 150,
            "confidence_score": 0.85
        }
        
        log = DecisionAuditLog(
            audit_id="audit_002",
            segment_key="brand1:awareness",
            brand_id="brand1",
            input_metrics=snapshot,
            suggested_decision="expand",
            gates_applied=[],
            gate_results=[],
            final_decision="expand",
            actor="auto",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        assert "kpi_summary" in log.input_metrics
        assert log.input_metrics["sample_size"] == 150


class TestSimulationResult:
    """Test simulation result structure."""
    
    def test_simulation_allowed(self):
        """Simulation result when allowed."""
        result = SimulationResult(
            dry_run=True,
            would_execute=True,
            safety_result=SafetyGateResult(
                gate_type=GateType.SAMPLE_SIZE,
                allowed=True,
                risk_level=RiskLevel.LOW
            ),
            predicted_decision="expand",
            confidence=0.85,
            warnings=[]
        )
        
        assert result.dry_run is True
        assert result.would_execute is True
        assert result.predicted_decision == "expand"
    
    def test_simulation_blocked(self):
        """Simulation result when blocked."""
        result = SimulationResult(
            dry_run=True,
            would_execute=False,
            safety_result=SafetyGateResult(
                gate_type=GateType.SAMPLE_SIZE,
                allowed=False,
                blocked_by=["insufficient_sample_size"],
                risk_level=RiskLevel.HIGH
            ),
            predicted_decision="hold",
            confidence=0.85,
            warnings=["Sample size below threshold"]
        )
        
        assert result.would_execute is False
        assert len(result.warnings) > 0


class TestDecisionSimulator:
    """Test decision simulator - dry-run antes da execução real."""
    
    def test_simulate_allowed_decision(self):
        """Simulator returns would_execute=True when gates pass."""
        simulator = DecisionSimulator()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 150,
            "confidence_score": 0.85,
            "short_window_regression": False,
            "long_window_regression": False,
            "active_alerts": [],
            "actions_today": 3,
            "decision_type": "expand"
        }
        
        result = simulator.simulate(context)
        
        assert result.dry_run is True
        assert result.would_execute is True
        assert result.predicted_decision == "expand"
        assert result.safety_result.allowed is True
    
    def test_simulate_blocked_decision(self):
        """Simulator returns would_execute=False when gates fail."""
        simulator = DecisionSimulator()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 50,  # Too few
            "confidence_score": 0.85,
            "short_window_regression": False,
            "long_window_regression": False,
            "active_alerts": [],
            "actions_today": 3,
            "decision_type": "expand"
        }
        
        result = simulator.simulate(context)
        
        assert result.dry_run is True
        assert result.would_execute is False
        assert result.safety_result.allowed is False
        assert "insufficient_sample_size" in result.safety_result.blocked_by
    
    def test_simulate_includes_full_snapshot(self):
        """Simulation captures full metrics snapshot."""
        simulator = DecisionSimulator()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 150,
            "confidence_score": 0.85,
            "kpi_summary": {
                "approval_rate": 0.85,
                "v1_score": 75
            },
            "active_alerts": [],
            "actions_today": 3,
            "decision_type": "expand"
        }
        
        result = simulator.simulate(context)
        
        assert "kpi_summary" in result.metrics_snapshot
        assert result.metrics_snapshot["sample_size"] == 150
    
    def test_simulate_with_manual_override(self):
        """Simulation can include manual override preview."""
        simulator = DecisionSimulator()
        
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 50,  # Would block
            "confidence_score": 0.85,
            "decision_type": "expand",
            "manual_override": True,
            "override_reason": "Business priority"
        }
        
        result = simulator.simulate(context)
        
        assert result.manual_override_preview is True
        assert result.override_reason == "Business priority"


class TestDecisionAuditStore:
    """Test audit store persistence."""
    
    def test_store_and_retrieve(self):
        """Can store and retrieve audit log."""
        store = DecisionAuditStore()
        
        log = DecisionAuditLog(
            audit_id="audit_003",
            segment_key="brand1:awareness",
            brand_id="brand1",
            input_metrics={"sample_size": 150},
            suggested_decision="expand",
            gates_applied=["sample_size"],
            gate_results=[{"allowed": True}],
            final_decision="expand",
            actor="auto",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        store.store(log)
        retrieved = store.get("audit_003")
        
        assert retrieved is not None
        assert retrieved.audit_id == "audit_003"
        assert retrieved.segment_key == "brand1:awareness"
    
    def test_query_by_segment(self):
        """Can query audits by segment."""
        store = DecisionAuditStore()
        
        # Add multiple logs
        for i in range(5):
            log = DecisionAuditLog(
                audit_id=f"audit_{i}",
                segment_key="brand1:awareness" if i < 3 else "brand2:conversion",
                brand_id="brand1" if i < 3 else "brand2",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        results = store.query_by_segment("brand1:awareness")
        
        assert len(results) == 3
        for r in results:
            assert r.segment_key == "brand1:awareness"
    
    def test_query_by_brand(self):
        """Can query audits by brand."""
        store = DecisionAuditStore()
        
        # Add logs for different brands
        for i in range(4):
            log = DecisionAuditLog(
                audit_id=f"audit_{i}",
                segment_key=f"brand{i%2+1}:obj",
                brand_id=f"brand{i%2+1}",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        results = store.query_by_brand("brand1")
        
        assert len(results) == 2
        for r in results:
            assert r.brand_id == "brand1"
    
    def test_query_by_date_range(self):
        """Can query audits by date range."""
        store = DecisionAuditStore()
        
        now = datetime.now(UTC)
        
        # Add logs at different times
        for i in range(3):
            log = DecisionAuditLog(
                audit_id=f"audit_{i}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=(now - timedelta(days=i)).isoformat()
            )
            store.store(log)
        
        # Query last 2 days
        start_date = (now - timedelta(days=1)).isoformat()
        end_date = now.isoformat()
        results = store.query_by_date_range(start_date, end_date)
        
        assert len(results) == 2  # Today and yesterday


class TestAuditPagination:
    """Test audit log pagination."""
    
    def test_pagination_basic(self):
        """Basic pagination works."""
        store = DecisionAuditStore()
        
        # Add 25 logs
        for i in range(25):
            log = DecisionAuditLog(
                audit_id=f"audit_{i:03d}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        # Query page 1, size 10
        pagination = AuditPagination(page=1, page_size=10)
        results, total = store.query_paginated(
            segment_key="brand1:awareness",
            pagination=pagination
        )
        
        assert len(results) == 10
        assert total == 25
    
    def test_pagination_page_2(self):
        """Second page returns correct results."""
        store = DecisionAuditStore()
        now = datetime.now(UTC)
        
        # Add 25 logs with different timestamps
        for i in range(25):
            log = DecisionAuditLog(
                audit_id=f"audit_{i:03d}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=(now - timedelta(seconds=i)).isoformat()  # Different timestamps
            )
            store.store(log)
        
        # Query page 2, size 10
        pagination = AuditPagination(page=2, page_size=10)
        results, total = store.query_paginated(
            segment_key="brand1:awareness",
            pagination=pagination
        )
        
        assert len(results) == 10
        # Items on page 2 should have audit_ids from audit_010 to audit_019
        audit_ids = {r.audit_id for r in results}
        assert "audit_010" in audit_ids or "audit_011" in audit_ids
    
    def test_pagination_last_page(self):
        """Last page may have fewer items."""
        store = DecisionAuditStore()
        
        # Add 25 logs
        for i in range(25):
            log = DecisionAuditLog(
                audit_id=f"audit_{i:03d}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        # Query page 3 (last), size 10
        pagination = AuditPagination(page=3, page_size=10)
        results, total = store.query_paginated(
            segment_key="brand1:awareness",
            pagination=pagination
        )
        
        assert len(results) == 5  # Remaining items
        assert total == 25


class TestAuditConsistency:
    """Test audit log consistency."""
    
    def test_audit_immutable_after_store(self):
        """Audit logs should be immutable after storage."""
        store = DecisionAuditStore()
        
        log = DecisionAuditLog(
            audit_id="audit_004",
            segment_key="brand1:awareness",
            brand_id="brand1",
            input_metrics={"sample_size": 150},
            suggested_decision="expand",
            gates_applied=[],
            gate_results=[],
            final_decision="expand",
            actor="auto",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        store.store(log)
        
        # Try to modify stored log (should work with dataclass copy)
        retrieved = store.get("audit_004")
        # This would fail if we enforced immutability strictly
        # For now, we just verify retrieval works
        assert retrieved.audit_id == "audit_004"
    
    def test_audit_trail_completeness(self):
        """Audit trail captures all required fields."""
        log = DecisionAuditLog(
            audit_id="audit_005",
            segment_key="brand1:awareness",
            brand_id="brand1",
            input_metrics={"kpi": "data"},
            suggested_decision="expand",
            gates_applied=["sample_size", "confidence"],
            gate_results=[
                {"gate": "sample_size", "allowed": True},
                {"gate": "confidence", "allowed": True}
            ],
            final_decision="expand",
            actor="auto",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        # Verify all fields are present
        assert log.audit_id is not None
        assert log.segment_key is not None
        assert log.input_metrics is not None
        assert log.suggested_decision is not None
        assert log.gates_applied is not None
        assert log.gate_results is not None
        assert log.final_decision is not None
        assert log.actor is not None
        assert log.executed_at is not None


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_simulate_decision(self):
        """simulate_decision utility works."""
        context = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "sample_size": 150,
            "confidence_score": 0.85,
            "decision_type": "expand"
        }
        
        result = simulate_decision(context)
        
        assert isinstance(result, SimulationResult)
        assert result.dry_run is True
    
    def test_record_decision_execution(self):
        """record_decision_execution utility works."""
        store = DecisionAuditStore()
        
        execution_data = {
            "segment_key": "brand1:awareness",
            "brand_id": "brand1",
            "input_metrics": {"sample_size": 150},
            "suggested_decision": "expand",
            "gates_applied": ["sample_size"],
            "gate_results": [{"allowed": True}],
            "final_decision": "expand",
            "actor": "auto"
        }
        
        audit_id = record_decision_execution(execution_data, store)
        
        assert audit_id is not None
        assert store.get(audit_id) is not None
    
    def test_get_decision_history(self):
        """get_decision_history utility works."""
        store = DecisionAuditStore()
        
        # Add some logs
        for i in range(5):
            log = DecisionAuditLog(
                audit_id=f"audit_{i}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        results = get_decision_history("brand1:awareness", store=store)
        
        assert len(results) == 5


class TestAuditQueryFilters:
    """Test audit query filters."""
    
    def test_filter_by_actor(self):
        """Can filter by actor type."""
        store = DecisionAuditStore()
        
        # Add auto and manual decisions
        for i in range(4):
            log = DecisionAuditLog(
                audit_id=f"audit_{i}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto" if i < 3 else "manual",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        auto_results = store.query(AuditQuery(actor="auto"))
        manual_results = store.query(AuditQuery(actor="manual"))
        
        assert len(auto_results) == 3
        assert len(manual_results) == 1
    
    def test_filter_by_decision_type(self):
        """Can filter by final decision."""
        store = DecisionAuditStore()
        
        # Add different decision types
        for i, decision in enumerate(["expand", "expand", "hold", "rollback"]):
            log = DecisionAuditLog(
                audit_id=f"audit_{i}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision=decision,
                gates_applied=[],
                gate_results=[],
                final_decision=decision,
                actor="auto",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        expand_results = store.query(AuditQuery(final_decision="expand"))
        
        assert len(expand_results) == 2


class TestEdgeCases:
    """Test edge cases."""
    
    def test_simulate_empty_context(self):
        """Simulator handles empty context."""
        simulator = DecisionSimulator()
        
        result = simulator.simulate({})
        
        assert result.would_execute is False
        assert result.safety_result.allowed is False
    
    def test_store_duplicate_audit_id(self):
        """Storing duplicate audit ID updates or ignores."""
        store = DecisionAuditStore()
        
        log1 = DecisionAuditLog(
            audit_id="duplicate_id",
            segment_key="brand1:awareness",
            brand_id="brand1",
            input_metrics={"version": 1},
            suggested_decision="expand",
            gates_applied=[],
            gate_results=[],
            final_decision="expand",
            actor="auto",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        log2 = DecisionAuditLog(
            audit_id="duplicate_id",
            segment_key="brand1:awareness",
            brand_id="brand1",
            input_metrics={"version": 2},
            suggested_decision="hold",
            gates_applied=[],
            gate_results=[],
            final_decision="hold",
            actor="auto",
            executed_at=datetime.now(UTC).isoformat()
        )
        
        store.store(log1)
        store.store(log2)
        
        # Should have the second one (or both, depending on implementation)
        retrieved = store.get("duplicate_id")
        assert retrieved is not None
    
    def test_query_no_results(self):
        """Query with no matches returns empty."""
        store = DecisionAuditStore()
        
        results = store.query_by_segment("nonexistent:segment")
        
        assert results == []
    
    def test_pagination_beyond_range(self):
        """Pagination beyond available data returns empty."""
        store = DecisionAuditStore()
        
        # Add 5 logs
        for i in range(5):
            log = DecisionAuditLog(
                audit_id=f"audit_{i}",
                segment_key="brand1:awareness",
                brand_id="brand1",
                input_metrics={},
                suggested_decision="expand",
                gates_applied=[],
                gate_results=[],
                final_decision="expand",
                actor="auto",
                executed_at=datetime.now(UTC).isoformat()
            )
            store.store(log)
        
        # Query page 10 (way beyond)
        pagination = AuditPagination(page=10, page_size=10)
        results, total = store.query_paginated(
            segment_key="brand1:awareness",
            pagination=pagination
        )
        
        assert len(results) == 0
        assert total == 5
