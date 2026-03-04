#!/bin/bash
# v41 Onboarding TTFV Report Generator
# Generates comparative report of onboarding journey simulations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPORT_DIR="${REPO_ROOT}/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "=========================================="
echo "  Onboarding TTFV Simulation Report"
echo "  Generated: $(date)"
echo "=========================================="
echo ""

# Create reports directory if not exists
mkdir -p "${REPORT_DIR}"

# Run simulations via Python
cd "${REPO_ROOT}/09-tools"

echo "Running onboarding simulations..."
echo ""

export REPO_ROOT="${REPO_ROOT}"
python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '.')

import json
from datetime import datetime
from tests.simulations.onboarding_simulation_runner import (
    OnboardingSimulator,
    JourneyType,
    SimulationConfig,
    calculate_statistics,
)

# Run simulations with more samples for better statistics
RUNS_PER_TYPE = 20

print(f"Running {RUNS_PER_TYPE} simulations per journey type...")
print()

config = SimulationConfig(fast_test_mode=True)
sim = OnboardingSimulator(config)
results = sim.compare_journeys(runs_per_type=RUNS_PER_TYPE)

# Calculate statistics for each journey type
report = {
    "generated_at": datetime.utcnow().isoformat(),
    "runs_per_type": RUNS_PER_TYPE,
    "journeys": {}
}

print("=" * 60)
print("SIMULATION RESULTS")
print("=" * 60)
print()

for journey_type in JourneyType:
    journey_key = journey_type.value
    metrics_list = results[journey_key]
    stats = calculate_statistics(metrics_list)
    
    report["journeys"][journey_key] = {
        "statistics": stats,
        "sample_runs": [m.to_dict() for m in metrics_list[:3]]  # First 3 runs
    }
    
    # Print summary
    print(f"📊 {journey_key.replace('_', ' ').upper()}")
    print(f"   Sample size: {stats['sample_size']}")
    print(f"   Avg TTFV: {stats['avg_ttfv_ms']/1000:.2f}s")
    print(f"   Min/Max TTFV: {stats['min_ttfv_ms']/1000:.2f}s / {stats['max_ttfv_ms']/1000:.2f}s")
    print(f"   Completion rate: {stats['completion_rate']*100:.1f}%")
    print(f"   Prefill adoption: {stats['prefill_adoption']*100:.1f}%")
    print(f"   Fast lane adoption: {stats['fast_lane_adoption']*100:.1f}%")
    print(f"   Resume adoption: {stats['resume_adoption']*100:.1f}%")
    print()

# Save JSON report (path relative to repo root via SCRIPT_DIR)
import os
report_dir = os.path.join(os.environ.get('REPO_ROOT', '../../'), 'reports')
os.makedirs(report_dir, exist_ok=True)
report_path = os.path.join(report_dir, 'onboarding_ttfv_report.json')
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"📁 JSON report saved: {report_path}")
print()

# Generate markdown report
md_report = f"""# Onboarding TTFV Simulation Report

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Runs per journey type:** {RUNS_PER_TYPE}

## Summary Table

| Journey Type | Avg TTFV (s) | Min TTFV (s) | Max TTFV (s) | Completion Rate | Prefill | Fast Lane | Resume |
|-------------|-------------|-------------|-------------|-----------------|---------|-----------|--------|
"""

for journey_type in JourneyType:
    journey_key = journey_type.value
    stats = report["journeys"][journey_key]["statistics"]
    
    md_report += f"| {journey_key.replace('_', ' ').title()} | "
    md_report += f"{stats['avg_ttfv_ms']/1000:.2f} | "
    md_report += f"{stats['min_ttfv_ms']/1000:.2f} | "
    md_report += f"{stats['max_ttfv_ms']/1000:.2f} | "
    md_report += f"{stats['completion_rate']*100:.1f}% | "
    md_report += f"{stats['prefill_adoption']*100:.1f}% | "
    md_report += f"{stats['fast_lane_adoption']*100:.1f}% | "
    md_report += f"{stats['resume_adoption']*100:.1f}% |\n"

md_report += f"""

## Analysis

### Happy Path
- Baseline scenario with no interruptions
- TTFV ranges based on feature adoption (prefill, fast lane)

### Interrupted Resume (v40 Feature)
- User returns and continues from saved progress
- Overhead: ~{sim.config.resume_overhead_ms}ms for resume decision
- Benefit: Faster completion vs restart

### Interrupted Restart
- User chooses to start over despite saved progress
- Full TTFV penalty (same as fresh start + overhead)

### Abandon Early
- Users leaving before completion
- No TTFV recorded (first value never reached)

## Feature Impact Analysis

### v38: Smart Prefill
- Estimated time savings: ~{sim.config.prefill_time_saved_ms/1000:.1f}s on template selection
- Adoption rate varies by journey type

### v39: Fast Lane
- Steps skipped: {', '.join(sim.config.fast_lane_skippable)}
- Time saved per skipped step: ~{sim.config.fast_lane_time_saved_per_step_ms/1000:.1f}s

### v40: Save/Resume
- Auto-save on every step completion
- Resume overhead: ~{sim.config.resume_overhead_ms}ms
- Prevents full restart penalty

## Files Generated
- `reports/onboarding_ttfv_report.json` - Full data in JSON format
- `reports/onboarding_ttfv_report.md` - This report

---
*Generated by v41 Onboarding Simulation Harness*
"""

md_path = os.path.join(report_dir, 'onboarding_ttfv_report.md')
with open(md_path, 'w') as f:
    f.write(md_report)

print(f"📄 Markdown report saved: {md_path}")
print()

PYTHON_SCRIPT

echo ""
echo "=========================================="
echo "  Report Generation Complete!"
echo "=========================================="
echo ""
echo "Files generated:"
echo "  - reports/onboarding_ttfv_report.json"
echo "  - reports/onboarding_ttfv_report.md"
echo ""
echo "View markdown report:"
echo "  cat reports/onboarding_ttfv_report.md"
echo ""
