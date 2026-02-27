#!/usr/bin/env python3
"""Generate consolidated editorial operations report.

This script aggregates editorial governance metrics and recommendations
across threads/brands to produce a markdown report for operational review.
"""

from __future__ import annotations

import argparse
import json
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
    return parser.parse_args()


def load_insights(source: Path | None) -> list[dict[str, Any]]:
    """Load insights data from file or stdin."""
    if source:
        with open(source, "r") as f:
            return json.load(f)
    else:
        return json.load(sys.stdin)


def aggregate_metrics(all_insights: list[dict]) -> dict[str, Any]:
    """Aggregate metrics across all threads."""
    total_threads = len(all_insights)
    total_marked = sum(i.get("totals", {}).get("marked_total", 0) for i in all_insights)
    total_denied = sum(i.get("policy", {}).get("denied_total", 0) for i in all_insights)
    
    by_scope = {"global": 0, "objective": 0}
    by_reason_code: dict[str, int] = {}
    by_source = {
        "objective_golden": 0,
        "global_golden": 0,
        "previous": 0,
        "none": 0,
    }
    
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
    
    # Calculate baseline none rate
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


def generate_markdown_report(
    metrics: dict[str, Any],
    generated_at: datetime,
) -> str:
    """Generate markdown report from aggregated metrics."""
    lines = [
        "# Editorial Operations Report",
        "",
        f"**Generated:** {generated_at.isoformat()}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Threads | {metrics['total_threads']} |",
        f"| Total Golden Marked | {metrics['total_marked']} |",
        f"| Total Policy Denied | {metrics['total_denied']} |",
        f"| Total Baseline Resolved | {metrics['total_resolved']} |",
        f"| Baseline None Rate | {metrics['baseline_none_rate']:.1%} |",
        "",
        "## Golden Marks by Scope",
        "",
        f"| Scope | Count |",
        f"|-------|-------|",
        f"| Global | {metrics['by_scope']['global']} |",
        f"| Objective | {metrics['by_scope']['objective']} |",
        "",
        "## Baseline Sources",
        "",
        f"| Source | Count |",
        f"|--------|-------|",
        f"| Objective Golden | {metrics['by_source']['objective_golden']} |",
        f"| Global Golden | {metrics['by_source']['global_golden']} |",
        f"| Previous | {metrics['by_source']['previous']} |",
        f"| None | {metrics['by_source']['none']} |",
        "",
    ]
    
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
    
    # Alerts section
    alerts = []
    if metrics["baseline_none_rate"] > 0.3:
        alerts.append("⚠️ **High baseline-none rate**: Consider marking more golden versions")
    if metrics["total_denied"] > 5:
        alerts.append("⚠️ **Policy denials detected**: Review editorial policy configuration")
    if metrics["total_marked"] == 0 and metrics["total_threads"] > 0:
        alerts.append("⚠️ **No golden marks**: No editorial decisions recorded yet")
    
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


def main() -> int:
    args = parse_args()
    
    try:
        insights = load_insights(args.insights_file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading insights: {e}", file=sys.stderr)
        return 1
    
    metrics = aggregate_metrics(insights)
    generated_at = datetime.now(timezone.utc)
    
    if args.format == "json":
        output = json.dumps(
            {"generated_at": generated_at.isoformat(), "metrics": metrics},
            indent=2,
        )
    else:
        output = generate_markdown_report(metrics, generated_at)
    
    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
