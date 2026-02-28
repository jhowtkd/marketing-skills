#!/usr/bin/env python3
"""
Nightly Report v16 - Decision Automation

Gera relatório noturno com:
- Decisões automatizadas
- Bloqueios por gate
- Rollbacks acionados
- Top segmentos em risco
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import json

UTC = timezone.utc


def generate_nightly_report(
    audit_store=None,
    safety_engine=None,
    date=None
) -> dict[str, Any]:
    """
    Gera relatório noturno de automação de decisões.
    
    Args:
        audit_store: Store de auditoria (opcional)
        safety_engine: Engine de safety gates (opcional)
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
        "report_version": "v16.0.0",
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
        }
    }
    
    return report


def print_report(report: dict[str, Any]) -> None:
    """Imprime relatório formatado."""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  VM Studio Nightly Report - Decision Automation v16             ║
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

Report generated at:    {report['generated_at']}
""")


if __name__ == "__main__":
    report = generate_nightly_report()
    print_report(report)
    
    # Também salva como JSON
    print("\n" + "="*70)
    print("JSON Output:")
    print(json.dumps(report, indent=2))
