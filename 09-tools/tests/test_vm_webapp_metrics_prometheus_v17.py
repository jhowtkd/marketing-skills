"""
VM Studio v17 - Safety Auto-Tuning Metrics Tests

Testes para métricas Prometheus:
- Counters de cycles/applied/blocked/rollback
- Deltas FP/incidents no report
"""

import pytest
from datetime import datetime, timezone

from vm_webapp.safety_tuning_metrics import (
    SafetyTuningMetricsCollector,
    render_tuning_prometheus,
)

UTC = timezone.utc


class TestSafetyTuningMetricsCollector:
    """Test safety tuning metrics collector."""
    
    def test_record_cycle_completed(self):
        """Registra ciclo completado."""
        collector = SafetyTuningMetricsCollector()
        
        collector.record_cycle_completed(
            cycle_id="cycle-001",
            proposals_count=3,
            adjustments_count=2
        )
        
        snapshot = collector.snapshot()
        assert snapshot["cycles_completed"] == 1
        assert snapshot["proposals_generated"] == 3
    
    def test_record_adjustment_applied(self):
        """Registra ajuste aplicado."""
        collector = SafetyTuningMetricsCollector()
        
        collector.record_adjustment_applied(
            gate_name="sample_size",
            adjustment_percent=-10.0,
            risk_level="low"
        )
        
        snapshot = collector.snapshot()
        assert snapshot["adjustments_applied"] == 1
        assert snapshot["adjustments_applied_by_risk"]["adjustments_applied_low_risk"] == 1
    
    def test_record_adjustment_blocked(self):
        """Registra ajuste bloqueado."""
        collector = SafetyTuningMetricsCollector()
        
        collector.record_adjustment_blocked(
            gate_name="sample_size",
            reason="high_risk"
        )
        
        snapshot = collector.snapshot()
        assert snapshot["adjustments_blocked"] == 1
    
    def test_record_rollback_triggered(self):
        """Registra rollback acionado."""
        collector = SafetyTuningMetricsCollector()
        
        collector.record_rollback_triggered(
            gate_name="sample_size",
            trigger="fp_rate_spike"
        )
        
        snapshot = collector.snapshot()
        assert snapshot["rollbacks_triggered"] == 1
    
    def test_record_gate_frozen(self):
        """Registra gate congelado."""
        collector = SafetyTuningMetricsCollector()
        
        collector.record_gate_frozen(gate_name="sample_size")
        
        snapshot = collector.snapshot()
        assert "sample_size" in snapshot["frozen_gates"]
    
    def test_record_fp_rate_delta(self):
        """Registra delta de FP rate."""
        collector = SafetyTuningMetricsCollector()
        
        collector.record_fp_rate_delta(
            gate_name="sample_size",
            previous_rate=0.20,
            current_rate=0.15
        )
        
        snapshot = collector.snapshot()
        assert abs(snapshot["fp_rate_deltas"]["sample_size"] - (-0.05)) < 0.001
    
    def test_record_incidents_delta(self):
        """Registra delta de incidentes."""
        collector = SafetyTuningMetricsCollector()
        
        collector.record_incidents_delta(
            gate_name="sample_size",
            previous_rate=0.02,
            current_rate=0.01
        )
        
        snapshot = collector.snapshot()
        assert snapshot["incidents_deltas"]["sample_size"] == -0.01


class TestRenderTuningPrometheus:
    """Test rendering de métricas Prometheus."""
    
    def test_render_cycles_completed(self):
        """Renderiza contador de ciclos."""
        collector = SafetyTuningMetricsCollector()
        collector.record_cycle_completed("cycle-001", 3, 2)
        
        snapshot = collector.snapshot()
        output = render_tuning_prometheus(snapshot)
        
        assert "vm_safety_tuning_cycles_completed" in output
        assert "1" in output
    
    def test_render_proposals_generated(self):
        """Renderiza contador de propostas."""
        collector = SafetyTuningMetricsCollector()
        collector.record_cycle_completed("cycle-001", 5, 2)
        
        snapshot = collector.snapshot()
        output = render_tuning_prometheus(snapshot)
        
        assert "vm_safety_tuning_proposals_generated" in output
        assert "5" in output
    
    def test_render_adjustments_applied(self):
        """Renderiza contador de ajustes aplicados."""
        collector = SafetyTuningMetricsCollector()
        collector.record_adjustment_applied("sample_size", -10.0, "low")
        
        snapshot = collector.snapshot()
        output = render_tuning_prometheus(snapshot)
        
        assert "vm_safety_tuning_adjustments_applied" in output
    
    def test_render_rollbacks_triggered(self):
        """Renderiza contador de rollbacks."""
        collector = SafetyTuningMetricsCollector()
        collector.record_rollback_triggered("sample_size", "fp_rate_spike")
        
        snapshot = collector.snapshot()
        output = render_tuning_prometheus(snapshot)
        
        assert "vm_safety_tuning_rollbacks_triggered" in output
    
    def test_render_frozen_gates(self):
        """Renderiza gates congelados."""
        collector = SafetyTuningMetricsCollector()
        collector.record_gate_frozen("sample_size")
        collector.record_gate_frozen("confidence_threshold")
        
        snapshot = collector.snapshot()
        output = render_tuning_prometheus(snapshot)
        
        assert "vm_safety_tuning_frozen_gates" in output
    
    def test_render_fp_rate_deltas(self):
        """Renderiza deltas de FP rate."""
        collector = SafetyTuningMetricsCollector()
        collector.record_fp_rate_delta("sample_size", 0.20, 0.15)
        
        snapshot = collector.snapshot()
        output = render_tuning_prometheus(snapshot)
        
        assert "vm_safety_tuning_fp_rate_delta" in output
    
    def test_render_empty_metrics(self):
        """Renderiza métricas vazias."""
        collector = SafetyTuningMetricsCollector()
        snapshot = collector.snapshot()
        output = render_tuning_prometheus(snapshot)
        
        assert "vm_safety_tuning_cycles_completed" in output  # Sempre renderiza métricas base
