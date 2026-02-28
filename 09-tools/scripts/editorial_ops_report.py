#!/usr/bin/env python3
"""Generate consolidated editorial operations report.

This script aggregates editorial governance metrics, recommendations,
and forecast data across threads/brands to produce a markdown report 
for operational review. Includes forecast delta tracking, signal quality metrics,
SLO alerts evidence, and playbook execution status.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate editorial operations consolidated report"
    )
    parser.add_argument(
        "--insights-file",
        type=Path,
        help="Path to JSON file with insights data (or stdin if not provided)",
    )
    parser.add_argument(
        "--forecasts-file",
        type=Path,
        help="Path to JSON file with forecast data (optional)",
    )
    parser.add_argument(
        "--recommendations-file",
        type=Path,
        help="Path to JSON file with recommendations data (optional)",
    )
    parser.add_argument(
        "--previous-report",
        type=Path,
        help="Path to previous report for delta calculation (optional)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output markdown file (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--github-step-summary",
        action="store_true",
        help="Also write summary to GITHUB_STEP_SUMMARY",
    )
    parser.add_argument(
        "--staging-url",
        type=str,
        default="",
        help="Staging URL for testing (if empty, report will be marked as SKIPPED)",
    )
    return parser.parse_args()


def load_insights(source: Path | None) -> list[dict[str, Any]]:
    """Load insights data from file or stdin."""
    if source:
        with open(source, "r") as f:
            return json.load(f)
    else:
        return json.load(sys.stdin)


def load_forecasts(source: Path | None) -> dict[str, dict[str, Any]]:
    """Load forecast data from file."""
    if source and source.exists():
        with open(source, "r") as f:
            forecasts_list = json.load(f)
            return {f["thread_id"]: f for f in forecasts_list if "thread_id" in f}
    return {}


def load_recommendations(source: Path | None) -> dict[str, list[dict[str, Any]]]:
    """Load recommendations data from file."""
    if source and source.exists():
        with open(source, "r") as f:
            recs_list = json.load(f)
            return {r["thread_id"]: r.get("recommendations", []) for r in recs_list if "thread_id" in r}
    return {}


def extract_previous_forecasts(previous_report_path: Path | None) -> dict[str, int]:
    """Extract previous risk scores from report for delta calculation."""
    if not previous_report_path or not previous_report_path.exists():
        return {}
    
    try:
        content = previous_report_path.read_text()
        previous_scores: dict[str, int] = {}
        in_forecast_section = False
        
        for line in content.split("\n"):
            if "## Forecast Summary" in line:
                in_forecast_section = True
                continue
            if in_forecast_section and line.startswith("## "):
                in_forecast_section = False
                continue
            if in_forecast_section and line.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                # Filter out empty parts
                parts = [p for p in parts if p]
                # Skip header row and separator row
                if len(parts) >= 3 and parts[0] not in ("Thread", "--------") and not parts[0].startswith("-"):
                    try:
                        thread_id = parts[0]
                        score = int(parts[1])  # Risk Score is second column
                        previous_scores[thread_id] = score
                    except (ValueError, IndexError):
                        pass
        
        return previous_scores
    except Exception:
        return {}


def aggregate_metrics(all_insights: list[dict]) -> dict[str, Any]:
    """Aggregate metrics across all threads."""
    total_threads = len(all_insights)
    total_marked = sum(i.get("totals", {}).get("marked_total", 0) for i in all_insights)
    total_denied = sum(i.get("policy", {}).get("denied_total", 0) for i in all_insights)
    
    by_scope = {"global": 0, "objective": 0}
    by_reason_code: dict[str, int] = {}
    by_source = {"objective_golden": 0, "global_golden": 0, "previous": 0, "none": 0}
    
    for insight in all_insights:
        totals = insight.get("totals", {})
        scope_data = totals.get("by_scope", {})
        by_scope["global"] += scope_data.get("global", 0)
        by_scope["objective"] += scope_data.get("objective", 0)
        
        for code, count in totals.get("by_reason_code", {}).items():
            by_reason_code[code] = by_reason_code.get(code, 0) + count
        
        baseline = insight.get("baseline", {})
        source_data = baseline.get("by_source", {})
        for source in by_source:
            by_source[source] += source_data.get(source, 0)
    
    total_resolved = sum(by_source.values())
    baseline_none_rate = by_source["none"] / total_resolved if total_resolved > 0 else 0
    
    return {
        "total_threads": total_threads,
        "total_marked": total_marked,
        "total_denied": total_denied,
        "by_scope": by_scope,
        "by_reason_code": by_reason_code,
        "by_source": by_source,
        "baseline_none_rate": baseline_none_rate,
        "total_resolved": total_resolved,
    }


def calculate_signal_quality(
    forecasts: dict[str, dict[str, Any]],
    recommendations: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Calculate signal quality metrics across all threads."""
    if not forecasts:
        return {
            "avg_confidence": 0.0,
            "avg_volatility": 0,
            "suppressed_actions_rate": 0.0,
            "low_confidence_high_volatility_threads": [],
            "total_threads_with_forecast": 0,
        }
    
    total_confidence = 0.0
    total_volatility = 0
    total_recommendations = 0
    total_suppressed = 0
    low_conf_high_vol_threads: list[dict] = []
    
    for thread_id, forecast in forecasts.items():
        confidence = forecast.get("confidence", 0.0)
        volatility = forecast.get("volatility", 0)
        
        total_confidence += confidence
        total_volatility += volatility
        
        if confidence < 0.5 and volatility > 60:
            low_conf_high_vol_threads.append({
                "thread_id": thread_id,
                "confidence": confidence,
                "volatility": volatility,
                "risk_score": forecast.get("risk_score", 0),
            })
        
        thread_recs = recommendations.get(thread_id, [])
        total_recommendations += len(thread_recs)
        total_suppressed += sum(1 for r in thread_recs if r.get("suppressed", False))
    
    total_threads = len(forecasts)
    
    return {
        "avg_confidence": total_confidence / total_threads if total_threads > 0 else 0.0,
        "avg_volatility": total_volatility // total_threads if total_threads > 0 else 0,
        "suppressed_actions_rate": (total_suppressed / total_recommendations * 100) if total_recommendations > 0 else 0.0,
        "low_confidence_high_volatility_threads": low_conf_high_vol_threads,
        "total_threads_with_forecast": total_threads,
    }


def calculate_forecast_deltas(
    forecasts: dict[str, dict[str, Any]],
    previous_scores: dict[str, int]
) -> dict[str, str]:
    """Calculate risk score deltas between current and previous forecasts."""
    deltas: dict[str, str] = {}
    
    for thread_id, forecast in forecasts.items():
        current_score = forecast.get("risk_score", 0)
        previous_score = previous_scores.get(thread_id)
        
        if previous_score is not None:
            diff = current_score - previous_score
            if diff > 5:
                deltas[thread_id] = f"📈 +{diff}"
            elif diff < -5:
                deltas[thread_id] = f"📉 {diff}"
            else:
                deltas[thread_id] = "stable"
        else:
            deltas[thread_id] = "new"
    
    return deltas


def get_top_risk_threads(
    forecasts: dict[str, dict[str, Any]],
    limit: int = 3
) -> list[tuple[str, int, str, str]]:
    """Get top N threads by risk score."""
    threads_with_risk: list[tuple[str, int, str, str]] = []
    
    for thread_id, forecast in forecasts.items():
        risk_score = forecast.get("risk_score", 0)
        trend = forecast.get("trend", "stable")
        focus = forecast.get("recommended_focus", "")
        threads_with_risk.append((thread_id, risk_score, trend, focus))
    
    threads_with_risk.sort(key=lambda x: x[1], reverse=True)
    
    return threads_with_risk[:limit]


def generate_slo_alerts_section(forecasts: dict[str, dict[str, Any]]) -> list[str]:
    """Generate SLO Alerts Evidence section."""
    lines = ["## SLO Alerts Evidence", ""]
    
    all_alerts: list[dict[str, Any]] = []
    for thread_id, forecast in forecasts.items():
        slo_alerts = forecast.get("slo_alerts", [])
        for alert in slo_alerts:
            alert_copy = dict(alert)
            alert_copy["thread_id"] = thread_id
            all_alerts.append(alert_copy)
    
    if all_alerts:
        lines.extend([
            "| Thread | Alert ID | Severity | Message | Threshold | Current |",
            "|--------|----------|----------|---------|-----------|---------|",
        ])
        for alert in all_alerts:
            thread_id = alert.get("thread_id", "")
            alert_id = alert.get("alert_id", "")
            severity = alert.get("severity", "")
            message = alert.get("message", "")[:40] + "..." if len(alert.get("message", "")) > 40 else alert.get("message", "")
            threshold = alert.get("threshold", "")
            current = alert.get("current_value", "")
            lines.append(f"| {thread_id} | {alert_id} | {severity} | {message} | {threshold} | {current} |")
        lines.append("")
    else:
        lines.append("✅ No SLO alerts at this time.")
        lines.append("")
    
    return lines


def generate_playbook_execution_section(forecasts: dict[str, dict[str, Any]]) -> list[str]:
    """Generate Playbook Execution Status section."""
    lines = ["## Playbook Execution Status", ""]
    
    has_executions = False
    for forecast in forecasts.values():
        if forecast.get("playbook_executions"):
            has_executions = True
            break
    
    if has_executions:
        lines.extend([
            "| Thread | Playbook ID | Status | Executed At | Actions |",
            "|--------|-------------|--------|-------------|---------|",
        ])
        for thread_id, forecast in forecasts.items():
            executions = forecast.get("playbook_executions", [])
            for execution in executions:
                playbook_id = execution.get("playbook_id", "")
                status = execution.get("status", "")
                executed_at = execution.get("executed_at", execution.get("scheduled_at", ""))
                actions = execution.get("actions_taken", execution.get("actions_pending", []))
                actions_str = ", ".join(actions) if actions else "-"
                lines.append(f"| {thread_id} | {playbook_id} | {status} | {executed_at} | {actions_str} |")
        lines.append("")
    else:
        lines.append("ℹ️ No playbook executions recorded.")
        lines.append("")
    
    return lines


def generate_actions_section(forecasts: dict[str, dict[str, Any]]) -> list[str]:
    """Generate Ações Executadas e Pendentes section."""
    lines = ["## Ações Executadas e Pendentes", ""]
    
    has_actions = False
    for forecast in forecasts.values():
        if forecast.get("executed_actions") or forecast.get("pending_actions"):
            has_actions = True
            break
    
    if has_actions:
        for thread_id, forecast in forecasts.items():
            executed = forecast.get("executed_actions", [])
            pending = forecast.get("pending_actions", [])
            
            if executed or pending:
                lines.append(f"### {thread_id}")
                lines.append("")
                
                if executed:
                    lines.append("**✅ Executadas:**")
                    for action in executed:
                        lines.append(f"- {action}")
                    lines.append("")
                
                if pending:
                    lines.append("**⏳ Pendentes:**")
                    for action in pending:
                        lines.append(f"- {action}")
                    lines.append("")
                
                has_actions = True
    else:
        lines.append("ℹ️ No actions recorded.")
        lines.append("")
    
    return lines


def generate_skipped_notice(has_staging_url: bool, has_real_data: bool) -> list[str]:
    """Generate SKIPPED notice when appropriate."""
    lines = []
    
    if not has_staging_url:
        lines.extend([
            "",
            "## ⚠️ SKIPPED",
            "",
            "**Status:** SKIPPED - No staging URL available",
            "",
            "This report was generated without a staging URL. "
            "Operational data could not be collected.",
            "",
            "**Ações recomendadas:**",
            "- Verificar configuração de staging URL",
            "- Executar workflow com staging URL configurado",
            "",
        ])
    elif not has_real_data:
        lines.extend([
            "",
            "## ℹ️ PASS Estrutural",
            "",
            "**Status:** PASS (Structural) - Running with sample/demo data",
            "",
            "Este relatório foi gerado com dados de demonstração. "
            "Para dados reais, configure uma staging URL.",
            "",
        ])
    
    return lines


def generate_markdown_report(
    metrics: dict[str, Any],
    forecasts: dict[str, dict[str, Any]],
    signal_quality: dict[str, Any],
    deltas: dict[str, str],
    top_risks: list[tuple[str, int, str, str]],
    generated_at: datetime,
    has_staging_url: bool = True,
) -> str:
    """Generate markdown report from aggregated metrics."""
    has_real_data = metrics["total_threads"] > 0 and not all(
        t.get("thread_id") == "sample" for t in [{}]  # Placeholder check
    )
    
    lines = [
        "# Editorial Operations Report",
        "",
        f"**Generated:** {generated_at.isoformat()}",
    ]
    
    # Add SKIPPED or PASS Estrutural notice if applicable
    lines.extend(generate_skipped_notice(has_staging_url, has_staging_url and metrics["total_threads"] > 0))
    
    lines.extend([
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Threads | {metrics['total_threads']} |",
        f"| Total Golden Marked | {metrics['total_marked']} |",
        f"| Total Policy Denied | {metrics['total_denied']} |",
        f"| Total Baseline Resolved | {metrics['total_resolved']} |",
        f"| Baseline None Rate | {metrics['baseline_none_rate']:.1%} |",
        "",
        "## Signal Quality",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Avg Confidence | {signal_quality['avg_confidence']:.0%} |",
        f"| Avg Volatility | {signal_quality['avg_volatility']}/100 |",
        f"| Suppressed Actions Rate | {signal_quality['suppressed_actions_rate']:.1f}% |",
        f"| Threads with Forecast | {signal_quality['total_threads_with_forecast']} |",
        "",
    ])
    
    quality_alerts = []
    if signal_quality['avg_confidence'] < 0.5:
        quality_alerts.append("**Low average confidence**: Consider gathering more data")
    if signal_quality['avg_volatility'] > 60:
        quality_alerts.append("**High average volatility**: Signals are unstable")
    if signal_quality['suppressed_actions_rate'] > 30:
        quality_alerts.append("**High suppression rate**: Many actions are being rate-limited")
    
    if quality_alerts:
        lines.extend([
            "### Signal Quality Alerts",
            "",
        ] + [f"- {alert}" for alert in quality_alerts] + [""])
    
    noisy_threads = signal_quality.get('low_confidence_high_volatility_threads', [])
    if noisy_threads:
        lines.extend([
            "### Noisy Signals (Low Confidence + High Volatility)",
            "",
            "| Thread | Confidence | Volatility | Risk Score |",
            "|--------|-----------|------------|-----------|",
        ])
        for thread in noisy_threads:
            lines.append(
                f"| {thread['thread_id']} | {thread['confidence']:.0%} | "
                f"{thread['volatility']}/100 | {thread['risk_score']}/100 |"
            )
        lines.append("")
    
    lines.extend([
        "## Golden Marks by Scope",
        "",
        "| Scope | Count |",
        "|-------|-------|",
        f"| Global | {metrics['by_scope']['global']} |",
        f"| Objective | {metrics['by_scope']['objective']} |",
        "",
        "## Baseline Sources",
        "",
        "| Source | Count |",
        "|--------|-------|",
        f"| Objective Golden | {metrics['by_source']['objective_golden']} |",
        f"| Global Golden | {metrics['by_source']['global_golden']} |",
        f"| Previous | {metrics['by_source']['previous']} |",
        f"| None | {metrics['by_source']['none']} |",
        "",
    ])
    
    if forecasts:
        lines.extend([
            "## Forecast Summary",
            "",
            "| Thread | Risk Score | Delta | Trend | Focus |",
            "|--------|-----------|-------|-------|-------|",
        ])
        
        for thread_id, forecast in sorted(forecasts.items()):
            risk_score = forecast.get("risk_score", 0)
            delta = deltas.get(thread_id, "-")
            trend = forecast.get("trend", "stable")
            focus = forecast.get("recommended_focus", "")[:30] + "..." if len(forecast.get("recommended_focus", "")) > 30 else forecast.get("recommended_focus", "")
            lines.append(f"| {thread_id} | {risk_score} | {delta} | {trend} | {focus} |")
        
        lines.append("")
    
    # Add SLO Alerts Evidence section
    lines.extend(generate_slo_alerts_section(forecasts))
    
    # Add Playbook Execution Status section
    lines.extend(generate_playbook_execution_section(forecasts))
    
    # Add Ações Executadas e Pendentes section
    lines.extend(generate_actions_section(forecasts))
    
    if top_risks:
        lines.extend([
            "## Top 3 Threads by Risk",
            "",
        ])
        
        for i, (thread_id, risk_score, trend, focus) in enumerate(top_risks, 1):
            trend_indicator = {"improving": "📈", "stable": "➡️", "degrading": "📉"}.get(trend, "➡️")
            lines.extend([
                f"### {i}. {thread_id}",
                "",
                f"- **Risk Score:** {risk_score}/100",
                f"- **Trend:** {trend_indicator} {trend}",
                f"- **Recommended Focus:** {focus}",
                "",
            ])
    
    if metrics["by_reason_code"]:
        lines.extend([
            "## Reason Code Distribution",
            "",
            "| Reason Code | Count |",
            "|-------------|-------|",
        ])
        for code, count in sorted(
            metrics["by_reason_code"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"| {code} | {count} |")
        lines.append("")
    
    alerts = []
    if metrics["baseline_none_rate"] > 0.3:
        alerts.append("**High baseline-none rate**: Consider marking more golden versions")
    if metrics["total_denied"] > 5:
        alerts.append("**Policy denials detected**: Review editorial policy configuration")
    if metrics["total_marked"] == 0 and metrics["total_threads"] > 0:
        alerts.append("**No golden marks**: No editorial decisions recorded yet")
    
    if top_risks and top_risks[0][1] > 70:
        alerts.append(f"**Critical risk detected**: Thread '{top_risks[0][0]}' has risk score {top_risks[0][1]}/100")
    
    if alerts:
        lines.extend([
            "## Alerts",
            "",
        ] + [f"- {alert}" for alert in alerts] + [""])
    
    lines.extend([
        "---",
        "",
        "_This report is auto-generated by the editorial operations workflow._",
    ])
    
    return "\n".join(lines)


def generate_github_step_summary(
    signal_quality: dict[str, Any],
    metrics: dict[str, Any],
    top_risks: list[tuple[str, int, str, str]],
    has_staging_url: bool = True,
) -> str:
    """Generate a concise summary for GITHUB_STEP_SUMMARY."""
    lines = [
        "## Editorial Operations Summary",
        "",
    ]
    
    if not has_staging_url:
        lines.extend([
            "⚠️ **SKIPPED** - No staging URL available",
            "",
        ])
    
    lines.extend([
        "### Signal Quality",
        "",
        f"- **Average Confidence:** {signal_quality['avg_confidence']:.0%}",
        f"- **Average Volatility:** {signal_quality['avg_volatility']}/100",
        f"- **Suppressed Actions:** {signal_quality['suppressed_actions_rate']:.1f}%",
        f"- **Total Threads:** {metrics['total_threads']}",
        "",
    ])
    
    noisy_threads = signal_quality.get('low_confidence_high_volatility_threads', [])
    if noisy_threads:
        lines.extend([
            "### Noisy Signal Threads",
            "",
        ])
        for thread in noisy_threads:
            lines.append(
                f"- `{thread['thread_id']}`: "
                f"confidence {thread['confidence']:.0%}, "
                f"volatility {thread['volatility']}/100"
            )
        lines.append("")
    
    if top_risks:
        lines.extend([
            "### Top 3 Risks",
            "",
        ])
        for i, (thread_id, risk_score, trend, focus) in enumerate(top_risks, 1):
            lines.append(f"{i}. `{thread_id}`: **{risk_score}/100** ({trend})")
        lines.append("")
    
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    
    # Check if we have a staging URL
    has_staging_url = bool(args.staging_url) or bool(os.environ.get("STAGING_URL"))
    staging_url = args.staging_url or os.environ.get("STAGING_URL", "")
    
    try:
        insights = load_insights(args.insights_file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading insights: {e}", file=sys.stderr)
        return 1
    
    forecasts = load_forecasts(args.forecasts_file)
    recommendations = load_recommendations(args.recommendations_file)
    signal_quality = calculate_signal_quality(forecasts, recommendations)
    previous_scores = extract_previous_forecasts(args.previous_report)
    deltas = calculate_forecast_deltas(forecasts, previous_scores)
    top_risks = get_top_risk_threads(forecasts)
    metrics = aggregate_metrics(insights)
    generated_at = datetime.now(timezone.utc)
    
    if args.format == "json":
        output = json.dumps(
            {
                "generated_at": generated_at.isoformat(),
                "metrics": metrics,
                "signal_quality": signal_quality,
                "forecasts": forecasts,
                "deltas": deltas,
                "top_risks": [
                    {"thread_id": t[0], "risk_score": t[1], "trend": t[2], "focus": t[3]}
                    for t in top_risks
                ],
                "staging_url": staging_url,
                "has_staging_url": has_staging_url,
            },
            indent=2,
        )
    else:
        output = generate_markdown_report(
            metrics, forecasts, signal_quality, deltas, top_risks, generated_at, has_staging_url
        )
    
    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    if args.github_step_summary:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            summary = generate_github_step_summary(signal_quality, metrics, top_risks, has_staging_url)
            with open(summary_path, "a") as f:
                f.write("\n" + summary + "\n")
            print("Summary written to GITHUB_STEP_SUMMARY", file=sys.stderr)
        else:
            print("Warning: GITHUB_STEP_SUMMARY not set", file=sys.stderr)
    
    # Always return 0 (PASS) for structural pass - this is a reporting tool
    # The actual status (SKIPPED/SUCCESS) is indicated in the report content
    return 0


if __name__ == "__main__":
    sys.exit(main())
