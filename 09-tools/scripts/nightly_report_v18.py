#!/usr/bin/env python3
"""
Nightly Report v18 - Recovery Orchestration

Gera relatório noturno com:
- Decisões automatizadas
- Bloqueios por gate
- Rollbacks acionados
- Top segmentos em risco
- Recovery Orchestration v28 (NEW)
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import json

UTC = timezone.utc


def generate_nightly_report(
    audit_store=None,
    safety_engine=None,
    recovery_metrics=None,
    date=None
) -> dict[str, Any]:
    """
    Gera relatório noturno de automação de decisões.
    
    Args:
        audit_store: Store de auditoria (opcional)
        safety_engine: Engine de safety gates (opcional)
        recovery_metrics: Métricas de recovery v28 (opcional)
        date: Data do relatório (default: ontem)
        
    Returns:
        Dict com estrutura do relatório
    """
    if date is None:
        date = datetime.now(UTC) - timedelta(days=1)
    
    report_date = date.strftime("%Y-%m-%d")
    
    # Mock data para demonstração
    # Em produção, viria dos stores reais
    report = {
        "report_version": "v18.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "report_date": report_date,
        
        "summary": {
            "total_decisions": 156,
            "automation_rate": 0.78,
            "blocked_by_gates": 34,
            "rollbacks_triggered": 2,
            "avg_decision_time_ms": 45
        },
        
        "automated_decisions": {
            "total": 122,
            "by_type": {
                "expand": 67,
                "hold": 42,
                "rollback": 13
            },
            "by_actor": {
                "auto": 122,
                "manual": 0
            },
            "success_rate": 0.984
        },
        
        "gate_blocks": {
            "total": 34,
            "by_gate": {
                "sample_size": 12,
                "confidence_threshold": 8,
                "regression_guard": 7,
                "cooldown": 4,
                "max_actions_per_day": 3
            },
            "top_blocked_segments": [
                {"segment": "brand3:conversion", "count": 5},
                {"segment": "brand1:awareness", "count": 3},
                {"segment": "brand2:consideration", "count": 2}
            ]
        },
        
        "rollbacks": {
            "total": 2,
            "details": [
                {
                    "execution_id": "exec_abc123",
                    "segment": "brand1:awareness",
                    "triggered_at": f"{report_date}T14:23:00Z",
                    "reason": "Post-execution regression detected: critical",
                    "rollback_time_ms": 3200
                },
                {
                    "execution_id": "exec_def456",
                    "segment": "brand2:conversion",
                    "triggered_at": f"{report_date}T09:15:00Z",
                    "reason": "Success rate dropped to 65.00%",
                    "rollback_time_ms": 2800
                }
            ]
        },
        
        "top_risk_segments": [
            {
                "segment_key": "brand3:conversion",
                "risk_level": "critical",
                "risk_factors": ["insufficient_sample_size", "low_confidence"],
                "recommendation": "collect_more_data"
            },
            {
                "segment_key": "brand1:awareness",
                "risk_level": "high",
                "risk_factors": ["short_window_regression"],
                "recommendation": "investigate_regression"
            },
            {
                "segment_key": "brand2:consideration",
                "risk_level": "medium",
                "risk_factors": ["cooldown_active"],
                "recommendation": "wait_2.5_hours"
            }
        ],
        
        "canary_executions": {
            "total": 18,
            "promoted": 15,
            "aborted": 3,
            "avg_observation_time_min": 28
        },
        
        "alerts": {
            "critical": 2,
            "warning": 8,
            "info": 15
        },
        
        # v19: ROI Optimizer section
        "roi_optimizer": {
            "cycles_run": 1,
            "proposals": {
                "generated": 2,
                "applied": 1,
                "blocked": 0,
                "rejected": 0,
                "pending": 1
            },
            "current_score": {
                "composite": 0.72,
                "business": 0.68,
                "quality": 0.75,
                "efficiency": 0.73
            },
            "score_change_24h": {
                "composite": +0.03,
                "business": +0.02,
                "quality": +0.04,
                "efficiency": +0.01
            },
            "top_roi_gains": [
                {
                    "proposal_id": "prop_001",
                    "pillar": "quality",
                    "expected_delta": 0.05,
                    "applied_at": f"{report_date}T10:30:00Z"
                }
            ],
            "guardrails_triggered": [
                {
                    "type": "incident_hard_stop",
                    "count": 0,
                    "description": "Blocked proposals that would increase incident rate"
                },
                {
                    "type": "adjustment_clamp",
                    "count": 1,
                    "description": "Proposals adjusted to stay within ±10% limit"
                }
            ]
        },
        
        # v28: Recovery Orchestration section (NEW)
        "recovery_orchestration_v28": {
            "runs": {
                "total": 12,
                "successful": 10,
                "failed": 2,
                "auto": 8,
                "manual": 4,
                "active": 1
            },
            "steps": {
                "total": 48,
                "successful": 42,
                "failed": 3,
                "skipped": 3
            },
            "approvals": {
                "requested": 4,
                "granted": 3,
                "rejected": 1,
                "pending": 1
            },
            "incidents": {
                "handoff_timeout": 5,
                "approval_sla_breach": 4,
                "quality_regression": 2,
                "system_failure": 1
            },
            "mttr": {
                "avg_seconds": 285.5,
                "avg_minutes": 4.76,
                "count": 10
            },
            "controls": {
                "frozen": 1,
                "rolled_back": 1
            },
            "recent_executions": [
                {
                    "run_id": "run-001",
                    "incident_type": "handoff_timeout",
                    "severity": "high",
                    "status": "completed",
                    "auto_executed": False,
                    "approved_by": "user-001",
                    "duration_seconds": 245,
                    "started_at": f"{report_date}T08:15:00Z"
                },
                {
                    "run_id": "run-002",
                    "incident_type": "approval_sla_breach",
                    "severity": "medium",
                    "status": "completed",
                    "auto_executed": True,
                    "duration_seconds": 120,
                    "started_at": f"{report_date}T10:30:00Z"
                },
                {
                    "run_id": "run-003",
                    "incident_type": "quality_regression",
                    "severity": "critical",
                    "status": "frozen",
                    "auto_executed": False,
                    "frozen_at": f"{report_date}T14:45:00Z",
                    "freeze_reason": "Investigating side effects"
                }
            ]
        }
    }
    
    return report


def print_report(report: dict[str, Any]) -> None:
    """Imprime relatório formatado."""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  VM Studio Nightly Report - Recovery Orchestration v18          ║
║  {report['report_date']}                                               ║
╚══════════════════════════════════════════════════════════════════╝

📊 SUMMARY
────────────────────────────────────────────────────────────────────
Total Decisions:        {report['summary']['total_decisions']}
Automation Rate:        {report['summary']['automation_rate']:.1%}
Blocked by Gates:       {report['summary']['blocked_by_gates']}
Rollbacks Triggered:    {report['summary']['rollbacks_triggered']}
Avg Decision Time:      {report['summary']['avg_decision_time_ms']}ms

🤖 AUTOMATED DECISIONS
────────────────────────────────────────────────────────────────────
Total:                  {report['automated_decisions']['total']}
Success Rate:           {report['automated_decisions']['success_rate']:.1%}

By Type:
  - Expand:             {report['automated_decisions']['by_type']['expand']}
  - Hold:               {report['automated_decisions']['by_type']['hold']}
  - Rollback:           {report['automated_decisions']['by_type']['rollback']}

🚫 GATE BLOCKS
────────────────────────────────────────────────────────────────────
Total Blocked:          {report['gate_blocks']['total']}

By Gate:
  - Sample Size:        {report['gate_blocks']['by_gate']['sample_size']}
  - Confidence:         {report['gate_blocks']['by_gate']['confidence_threshold']}
  - Regression Guard:   {report['gate_blocks']['by_gate']['regression_guard']}
  - Cooldown:           {report['gate_blocks']['by_gate']['cooldown']}
  - Max Actions/Day:    {report['gate_blocks']['by_gate']['max_actions_per_day']}

Top Blocked Segments:
  - {report['gate_blocks']['top_blocked_segments'][0]['segment']}: {report['gate_blocks']['top_blocked_segments'][0]['count']} blocks
  - {report['gate_blocks']['top_blocked_segments'][1]['segment']}: {report['gate_blocks']['top_blocked_segments'][1]['count']} blocks
  - {report['gate_blocks']['top_blocked_segments'][2]['segment']}: {report['gate_blocks']['top_blocked_segments'][2]['count']} blocks

↩️  ROLLBACKS
────────────────────────────────────────────────────────────────────
Total:                  {report['rollbacks']['total']}

Details:
""")
    for rb in report['rollbacks']['details']:
        print(f"  - {rb['segment']}: {rb['reason']}")
        print(f"    Time: {rb['rollback_time_ms']}ms")
    
    print(f"""
⚠️  TOP RISK SEGMENTS
────────────────────────────────────────────────────────────────────
""")
    for seg in report['top_risk_segments']:
        print(f"  [{seg['risk_level'].upper()}] {seg['segment_key']}")
        print(f"    Factors: {', '.join(seg['risk_factors'])}")
        print(f"    Action:  {seg['recommendation']}")
    
    print(f"""
🐤 CANARY EXECUTIONS
────────────────────────────────────────────────────────────────────
Total:                  {report['canary_executions']['total']}
Promoted:               {report['canary_executions']['promoted']}
Aborted:                {report['canary_executions']['aborted']}
Avg Observation:        {report['canary_executions']['avg_observation_time_min']}min

🔔 ALERTS
────────────────────────────────────────────────────────────────────
Critical:               {report['alerts']['critical']}
Warning:                {report['alerts']['warning']}
Info:                   {report['alerts']['info']}
""")

    # v28 Recovery Orchestration Section
    recovery = report.get('recovery_orchestration_v28', {})
    if recovery:
        print(f"""
🆘 RECOVERY ORCHESTRATION v28
────────────────────────────────────────────────────────────────────
Runs:
  - Total:              {recovery['runs']['total']}
  - Successful:         {recovery['runs']['successful']}
  - Failed:             {recovery['runs']['failed']}
  - Auto-executed:      {recovery['runs']['auto']}
  - Manual:             {recovery['runs']['manual']}
  - Active:             {recovery['runs']['active']}

Steps:
  - Total:              {recovery['steps']['total']}
  - Successful:         {recovery['steps']['successful']}
  - Failed:             {recovery['steps']['failed']}
  - Skipped:            {recovery['steps']['skipped']}

Approvals:
  - Requested:          {recovery['approvals']['requested']}
  - Granted:            {recovery['approvals']['granted']}
  - Rejected:           {recovery['approvals']['rejected']}
  - Pending:            {recovery['approvals']['pending']}

Incidents:
  - Handoff Timeout:    {recovery['incidents']['handoff_timeout']}
  - SLA Breach:         {recovery['incidents']['approval_sla_breach']}
  - Quality Regress:    {recovery['incidents']['quality_regression']}
  - System Failure:     {recovery['incidents']['system_failure']}

MTTR:                   {recovery['mttr']['avg_minutes']:.2f} min ({recovery['mttr']['count']} recoveries)

Controls:
  - Frozen:             {recovery['controls']['frozen']}
  - Rolled Back:        {recovery['controls']['rolled_back']}

Recent Executions:
""")
        for exec in recovery['recent_executions'][:3]:
            auto_str = "[AUTO]" if exec.get('auto_executed') else "[MANUAL]"
            print(f"  - {exec['run_id']}: {exec['incident_type']} [{exec['severity']}] {auto_str} -> {exec['status']}")
    
    print(f"""
Report generated at:    {report['generated_at']}
""")


if __name__ == "__main__":
    report = generate_nightly_report()
    print_report(report)
    
    # Também salva como JSON
    print("\n" + "="*70)
    print("JSON Output:")
    print(json.dumps(report, indent=2))
