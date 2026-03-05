#!/usr/bin/env python3
"""Daily Policy Operations Runner.

Executes daily evaluation of experiment policies and generates reports.
Can be run manually or via cron/job scheduler.

Usage:
    python policy_ops_daily.py [--dry-run] [--experiment-id ID] [--output-format md|json]
    python policy_ops_daily.py --help

Examples:
    # Dry run (no side effects)
    python policy_ops_daily.py --dry-run
    
    # Evaluate specific experiment
    python policy_ops_daily.py --experiment-id exp_001
    
    # Generate JSON report only
    python policy_ops_daily.py --output-format json
    
    # Full daily run with MD report
    python policy_ops_daily.py --output-format md
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vm_webapp.policy_ops_engine import (
    PolicyOpsEngine,
    RecommendationAction,
    RecommendationStatus,
    get_pending_recommendations,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Daily Policy Operations Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run                    # Test run without changes
  %(prog)s --experiment-id exp_001      # Evaluate specific experiment
  %(prog)s --output-format json         # JSON report only
  %(prog)s --output-format md           # Markdown report (default)
        """,
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without persisting any changes",
    )
    
    parser.add_argument(
        "--experiment-id",
        type=str,
        help="Evaluate specific experiment (default: all active)",
    )
    
    parser.add_argument(
        "--output-format",
        choices=["md", "json", "both"],
        default="md",
        help="Report output format (default: md)",
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Output directory for reports (default: reports)",
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    return parser.parse_args()


def generate_markdown_report(
    results: list[Any],
    output_dir: Path,
    dry_run: bool,
) -> Path:
    """Generate Markdown report of evaluation results.
    
    Args:
        results: List of EvaluationResult objects
        output_dir: Directory to save report
        dry_run: Whether this was a dry run
        
    Returns:
        Path to generated report file
    """
    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y-%m-%d")
    datetime_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / f"policy_ops_{date_str}.md"
    
    # Build report content
    lines = []
    lines.append("# Policy Operations Daily Report\n")
    lines.append(f"**Generated:** {datetime_str}\n")
    lines.append(f"**Mode:** {'DRY RUN (no changes)' if dry_run else 'LIVE'}\n")
    lines.append(f"**Experiments Evaluated:** {len(results)}\n")
    lines.append("---\n")
    
    # Executive Summary
    lines.append("## Executive Summary\n")
    
    if not results:
        lines.append("No active experiments found for evaluation.\n")
    else:
        promote_count = sum(1 for r in results if r.recommendation.action == RecommendationAction.PROMOTE)
        hold_count = sum(1 for r in results if r.recommendation.action == RecommendationAction.HOLD)
        rollback_count = sum(1 for r in results if r.recommendation.action == RecommendationAction.ROLLBACK)
        
        lines.append(f"- **Promote:** {promote_count}")
        lines.append(f"- **Hold:** {hold_count}")
        lines.append(f"- **Rollback:** {rollback_count}")
        lines.append(f"- **Pending Approval:** {len([r for r in results if r.recommendation.status == RecommendationStatus.PENDING and r.recommendation.action == RecommendationAction.PROMOTE])}\n")
    
    # Action Items
    lines.append("## Action Items\n")
    
    action_items = []
    for result in results:
        rec = result.recommendation
        if rec.action == RecommendationAction.ROLLBACK:
            action_items.append(("🔴 URGENT", result.experiment_id, "Immediate rollback required", rec.confidence))
        elif rec.action == RecommendationAction.PROMOTE and rec.status == RecommendationStatus.PENDING:
            action_items.append(("🟡 REVIEW", result.experiment_id, "Pending approval for promotion", rec.confidence))
    
    if action_items:
        lines.append("| Priority | Experiment | Action | Confidence |")
        lines.append("|----------|------------|--------|------------|")
        for priority, exp_id, action, confidence in action_items:
            lines.append(f"| {priority} | `{exp_id}` | {action} | {confidence:.1%} |")
        lines.append("")
    else:
        lines.append("No immediate action items.\n")
    
    # Detailed Results
    lines.append("## Detailed Results\n")
    
    for result in results:
        rec = result.recommendation
        
        lines.append(f"### {result.experiment_id}\n")
        lines.append(f"**Recommendation:** {rec.action.value.upper()}")
        lines.append(f"**Confidence:** {rec.confidence:.1%}")
        lines.append(f"**Status:** {rec.status.value}")
        if rec.evaluated_at:
            lines.append(f"**Evaluated At:** {rec.evaluated_at}")
        lines.append("")
        
        lines.append(f"**Rationale:** {rec.rationale}\n")
        
        if result.gates_passed:
            lines.append(f"**Gates Passed:** {', '.join(result.gates_passed)}")
        if result.gates_failed:
            lines.append(f"**Gates Failed:** {', '.join(result.gates_failed)}")
        
        if rec.metrics_snapshot:
            lines.append("\n**Metrics Snapshot:**")
            lines.append(f"```json")
            lines.append(json.dumps(rec.metrics_snapshot, indent=2))
            lines.append(f"```")
        
        lines.append("")
    
    # Pending Approvals Section
    pending = [r for r in results if r.recommendation.status == RecommendationStatus.PENDING and r.recommendation.action == RecommendationAction.PROMOTE]
    if pending:
        lines.append("## Pending Approvals (SUPERVISED Mode)\n")
        lines.append("The following experiments are awaiting manual approval:\n")
        
        for result in pending:
            rec = result.recommendation
            lines.append(f"- `{result.experiment_id}`: {rec.confidence:.1%} confidence - {rec.rationale}")
        
        lines.append("")
        lines.append("Use the Rollout Dashboard to review and approve/reject these recommendations.")
        lines.append("")
    
    # Footer
    lines.append("---\n")
    lines.append("*This report was generated automatically by the Policy Operations Engine.*\n")
    
    # Write file
    content = "\n".join(lines)
    with open(filepath, "w") as f:
        f.write(content)
    
    logger.info(f"Generated Markdown report: {filepath}")
    return filepath


def generate_json_report(
    results: list[Any],
    output_dir: Path,
    dry_run: bool,
) -> Path:
    """Generate JSON report of evaluation results.
    
    Args:
        results: List of EvaluationResult objects
        output_dir: Directory to save report
        dry_run: Whether this was a dry run
        
    Returns:
        Path to generated report file
    """
    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y-%m-%d")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / f"policy_ops_{date_str}.json"
    
    # Build report data
    report_data = {
        "metadata": {
            "schema_version": "1.0.0",
            "generated_at": timestamp.isoformat(),
            "dry_run": dry_run,
            "total_experiments": len(results),
        },
        "summary": {
            "promote": sum(1 for r in results if r.recommendation.action == RecommendationAction.PROMOTE),
            "hold": sum(1 for r in results if r.recommendation.action == RecommendationAction.HOLD),
            "rollback": sum(1 for r in results if r.recommendation.action == RecommendationAction.ROLLBACK),
            "pending_approval": len([r for r in results if r.recommendation.status == RecommendationStatus.PENDING and r.recommendation.action == RecommendationAction.PROMOTE]),
        },
        "results": [
            {
                "experiment_id": r.experiment_id,
                "recommendation": {
                    "action": r.recommendation.action.value,
                    "confidence": r.recommendation.confidence,
                    "rationale": r.recommendation.rationale,
                    "status": r.recommendation.status.value,
                    "created_at": r.recommendation.created_at,
                    "evaluated_at": r.recommendation.evaluated_at,
                    "expires_at": r.recommendation.expires_at,
                },
                "gates_passed": r.gates_passed,
                "gates_failed": r.gates_failed,
                "metrics": r.recommendation.metrics_snapshot,
            }
            for r in results
        ],
        "pending_approvals": [
            {
                "experiment_id": r.experiment_id,
                "confidence": r.recommendation.confidence,
                "rationale": r.recommendation.rationale,
            }
            for r in results
            if r.recommendation.status == RecommendationStatus.PENDING and r.recommendation.action == RecommendationAction.PROMOTE
        ],
    }
    
    # Write file
    with open(filepath, "w") as f:
        json.dump(report_data, f, indent=2)
    
    logger.info(f"Generated JSON report: {filepath}")
    return filepath


def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 60)
    logger.info("Policy Operations Daily Runner")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("⚠️  DRY RUN MODE - No changes will be persisted")
    
    # Initialize engine
    config_path = Path(args.config) if args.config else None
    engine = PolicyOpsEngine(config_path=config_path)
    
    # Run evaluation
    try:
        logger.info(f"Starting evaluation (experiment_id={args.experiment_id or 'ALL'})")
        results = engine.evaluate_daily(
            experiment_id=args.experiment_id,
            dry_run=args.dry_run,
        )
        logger.info(f"Evaluation complete: {len(results)} experiments processed")
        
        # Generate reports
        output_dir = Path(args.output_dir)
        
        if args.output_format in ("md", "both"):
            md_path = generate_markdown_report(results, output_dir, args.dry_run)
            print(f"\n📄 Markdown report: {md_path}")
        
        if args.output_format in ("json", "both"):
            json_path = generate_json_report(results, output_dir, args.dry_run)
            print(f"📄 JSON report: {json_path}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Experiments evaluated: {len(results)}")
        
        promote_count = sum(1 for r in results if r.recommendation.action == RecommendationAction.PROMOTE)
        hold_count = sum(1 for r in results if r.recommendation.action == RecommendationAction.HOLD)
        rollback_count = sum(1 for r in results if r.recommendation.action == RecommendationAction.ROLLBACK)
        pending_count = len([r for r in results if r.recommendation.status == RecommendationStatus.PENDING and r.recommendation.action == RecommendationAction.PROMOTE])
        
        print(f"  Promote:   {promote_count}")
        print(f"  Hold:      {hold_count}")
        print(f"  Rollback:  {rollback_count}")
        print(f"  Pending:   {pending_count}")
        
        if rollback_count > 0:
            print("\n🔴 URGENT: Rollback actions required!")
        
        if pending_count > 0:
            print("\n🟡 Review pending approvals in Rollout Dashboard")
        
        print("\n✅ Daily run completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Daily run failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
