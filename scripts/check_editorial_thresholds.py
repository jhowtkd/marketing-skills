#!/usr/bin/env python3
"""
Script para verificar thresholds de métricas editoriais.
Usado em CI/CD para alertar sobre anomalias na governança editorial.

Exits with code 0 se todos os thresholds estiverem OK.
Exits with code 1 se houver violações (gera artefatos de diagnóstico).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests


def parse_prometheus_metrics(text: str) -> dict[str, float]:
    """Parse Prometheus exposition format into dict."""
    metrics = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Match metric lines: name value [timestamp]
        # Handle formats like: vm_metric_name 42
        #              or: vm_metric_name{label="value"} 42
        match = re.match(r'^(\w+(?:\{\w+="[^"]+"(?:,\w+="[^"]+")*\})?)\s+([\d.]+)', line)
        if match:
            name = match.group(1)
            value = float(match.group(2))
            metrics[name] = value
    
    return metrics


def check_thresholds(
    metrics: dict[str, float],
    threshold_policy_denied: float,
    threshold_baseline_none: float,
) -> tuple[bool, list[dict]]:
    """
    Check if metrics are within thresholds.
    
    Returns (all_ok, violations_list)
    """
    violations = []
    
    # Check policy denial rate
    policy_denied = metrics.get("vm_editorial_golden_policy_denied_total", 0)
    if policy_denied > threshold_policy_denied:
        violations.append({
            "metric": "vm_editorial_golden_policy_denied_total",
            "value": policy_denied,
            "threshold": threshold_policy_denied,
            "severity": "warning" if policy_denied < threshold_policy_denied * 2 else "critical",
            "message": f"Policy denial count ({policy_denied}) exceeds threshold ({threshold_policy_denied})",
        })
    
    # Check baseline=none count
    baseline_none = metrics.get("vm_editorial_baseline_source_none", 0)
    if baseline_none > threshold_baseline_none:
        violations.append({
            "metric": "vm_editorial_baseline_source_none",
            "value": baseline_none,
            "threshold": threshold_baseline_none,
            "severity": "warning",
            "message": f"Baseline=none count ({baseline_none}) exceeds threshold ({threshold_baseline_none})",
        })
    
    # Check policy denial by role (individual thresholds)
    for role in ["editor", "viewer"]:
        role_denied = metrics.get(f"vm_editorial_golden_policy_denied_role_{role}", 0)
        if role_denied > threshold_policy_denied / 2:  # Lower threshold per role
            violations.append({
                "metric": f"vm_editorial_golden_policy_denied_role_{role}",
                "value": role_denied,
                "threshold": threshold_policy_denied / 2,
                "severity": "info",
                "message": f"Policy denials for role '{role}' ({role_denied}) exceeds threshold",
            })
    
    return len(violations) == 0, violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check editorial governance metrics against thresholds"
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000",
        help="API endpoint base URL",
    )
    parser.add_argument(
        "--threshold-policy-denied",
        type=float,
        default=10.0,
        help="Threshold for policy denials",
    )
    parser.add_argument(
        "--threshold-baseline-none",
        type=float,
        default=50.0,
        help="Threshold for baseline=none count",
    )
    args = parser.parse_args()
    
    # Fetch metrics from Prometheus endpoint
    metrics_url = f"{args.endpoint}/api/v2/metrics/prometheus"
    
    try:
        response = requests.get(metrics_url, timeout=30)
        response.raise_for_status()
        metrics_text = response.text
    except requests.RequestException as e:
        print(f"❌ Failed to fetch metrics from {metrics_url}: {e}", file=sys.stderr)
        return 1
    
    # Parse metrics
    metrics = parse_prometheus_metrics(metrics_text)
    
    # Save raw metrics for diagnostics
    Path("diagnostic_metrics.txt").write_text(metrics_text, encoding="utf-8")
    
    # Check thresholds
    all_ok, violations = check_thresholds(
        metrics,
        args.threshold_policy_denied,
        args.threshold_baseline_none,
    )
    
    # Report results
    print("=" * 60)
    print("EDITORIAL GOVERNANCE METRICS CHECK")
    print("=" * 60)
    print(f"\nEndpoint: {metrics_url}")
    print(f"Threshold Policy Denied: {args.threshold_policy_denied}")
    print(f"Threshold Baseline None: {args.threshold_baseline_none}")
    print()
    
    # Report key metrics
    key_metrics = [
        "vm_editorial_golden_marked_total",
        "vm_editorial_golden_policy_denied_total",
        "vm_editorial_baseline_resolved_total",
        "vm_editorial_baseline_source_none",
    ]
    
    print("Key Metrics:")
    for metric in key_metrics:
        value = metrics.get(metric, 0)
        print(f"  {metric}: {value}")
    
    print()
    
    if all_ok:
        print("✅ All metrics within thresholds")
        return 0
    
    # Report violations
    print(f"⚠️  {len(violations)} threshold violation(s) detected:")
    for v in violations:
        icon = "🔴" if v["severity"] == "critical" else "🟡" if v["severity"] == "warning" else "🔵"
        print(f"  {icon} [{v['severity'].upper()}] {v['message']}")
    
    # Save violations to JSON
    Path("threshold_violations.json").write_text(
        json.dumps({
            "timestamp": str(Path("/proc/uptime").read_text().split()[0]) if Path("/proc/uptime").exists() else "unknown",
            "violations": violations,
            "metrics_sample": {k: metrics.get(k, 0) for k in key_metrics},
        }, indent=2),
        encoding="utf-8"
    )
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
