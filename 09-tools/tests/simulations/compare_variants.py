"""v42 Variant Comparison Script - A/B/C Testing Harness.

This script runs simulations across multiple onboarding variants (A/B/C)
and generates comparative reports with weighted scoring.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, '.')

from tests.simulations.onboarding_simulation_runner import (
    OnboardingSimulator,
    OnboardingVariantA,
    OnboardingVariantB,
    OnboardingVariantC,
    JourneyType,
    SimulationConfig,
    JourneyMetrics,
    calculate_statistics,
)


def calculate_variant_score(
    name: str,
    stats: Dict[str, Any],
    complexity_penalty: float = 0.0,
    baseline_ttfv_ms: Optional[float] = None
) -> float:
    """Calculate weighted score for a variant.
    
    Score formula:
    - 60% TTFV efficiency (baseline / actual, can exceed 1.0 if better than baseline)
    - 25% completion rate
    - 15% complexity penalty (simpler is better)
    
    Args:
        name: Variant name
        stats: Statistics dict from calculate_statistics
        complexity_penalty: Penalty for added complexity (0.0 = baseline)
        baseline_ttfv_ms: TTFV of baseline variant for comparison (if None, uses 30s default)
    
    Returns:
        Weighted score (higher is better)
    """
    avg_ttfv_s = stats['avg_ttfv_ms'] / 1000
    
    # TTFV score: menor tempo = maior score (inverted and normalized)
    # Usando baseline real da simulação ou 30s como referência
    baseline_ttfv = (baseline_ttfv_ms / 1000) if baseline_ttfv_ms else 30.0
    ttfv_efficiency = baseline_ttfv / max(avg_ttfv_s, 1.0)
    
    completion = stats['completion_rate']
    
    # Score ponderado
    score = (
        0.60 * ttfv_efficiency +
        0.25 * completion +
        0.15 * (1.0 - complexity_penalty)  # Menor penalidade = melhor
    )
    
    return round(score, 4)


def get_complexity_penalty(name: str) -> float:
    """Get complexity penalty for each variant.
    
    Baseline: 0 (simplest)
    Variant A: 0.05 (step reordering - low complexity)
    Variant B: 0.10 (delayed resume logic - medium complexity)
    Variant C: 0.08 (early fast lane check - low-medium complexity)
    """
    penalties = {
        'baseline': 0.0,
        'variant_a': 0.05,
        'variant_b': 0.10,
        'variant_c': 0.08,
    }
    return penalties.get(name, 0.0)


def compare_variants(n: int = 50) -> Dict[str, Any]:
    """Run A/B/C variant comparison with n simulations each.
    
    Args:
        n: Number of simulations per variant
    
    Returns:
        Dict with results and scores for each variant
    """
    # Configure all variants with fast test mode
    config_base = SimulationConfig(fast_test_mode=True)
    
    variants = {
        'baseline': OnboardingSimulator(SimulationConfig(fast_test_mode=True)),
        'variant_a': OnboardingVariantA(SimulationConfig(fast_test_mode=True)),
        'variant_b': OnboardingVariantB(SimulationConfig(fast_test_mode=True)),
        'variant_c': OnboardingVariantC(SimulationConfig(fast_test_mode=True)),
    }
    
    print(f"🔄 Running {n} simulations per variant...")
    print()
    
    results = {}
    all_metrics: Dict[str, List[JourneyMetrics]] = {}
    
    # First pass: run all simulations and collect stats
    for name, sim in variants.items():
        print(f"  ▶️  {name}: ", end="", flush=True)
        
        # Run happy path simulations
        metrics = sim.run_batch(JourneyType.HAPPY_PATH, count=n)
        all_metrics[name] = metrics
        
        stats = calculate_statistics(metrics)
        complexity = get_complexity_penalty(name)
        
        results[name] = {
            'stats': stats,
            'complexity_penalty': complexity,
            'sample_size': n,
            # Score will be calculated in second pass after we have baseline
        }
        
        print(f"✓ TTFV={stats['avg_ttfv_ms']/1000:.2f}s")
    
    # Get baseline TTFV for relative scoring
    baseline_ttfv_ms = results['baseline']['stats']['avg_ttfv_ms']
    
    # Second pass: calculate scores with baseline reference
    print()
    print(f"📊 Calculating scores (baseline TTFV: {baseline_ttfv_ms/1000:.2f}s)...")
    for name in results:
        stats = results[name]['stats']
        complexity = results[name]['complexity_penalty']
        score = calculate_variant_score(name, stats, complexity, baseline_ttfv_ms)
        results[name]['score'] = score
        print(f"  {name}: Score={score:.4f}")
    
    print()
    return results


def generate_json_report(results: Dict[str, Any]) -> str:
    """Generate JSON report from comparison results.
    
    Returns:
        Path to saved JSON file
    """
    report = {
        'generated_at': datetime.utcnow().isoformat(),
        'version': 'v42',
        'methodology': {
            'simulations_per_variant': results.get('baseline', {}).get('sample_size', 0),
            'score_formula': '0.60*TTFV_efficiency + 0.25*completion + 0.15*simplicity',
            'journey_type': JourneyType.HAPPY_PATH.value,
        },
        'variants': {}
    }
    
    for name, data in results.items():
        report['variants'][name] = {
            'score': data['score'],
            'complexity_penalty': data['complexity_penalty'],
            'metrics': {
                'avg_ttfv_ms': data['stats']['avg_ttfv_ms'],
                'avg_ttfv_s': round(data['stats']['avg_ttfv_ms'] / 1000, 2),
                'min_ttfv_ms': data['stats']['min_ttfv_ms'],
                'max_ttfv_ms': data['stats']['max_ttfv_ms'],
                'completion_rate': round(data['stats']['completion_rate'], 4),
                'prefill_adoption': round(data['stats']['prefill_adoption'], 4),
                'fast_lane_adoption': round(data['stats']['fast_lane_adoption'], 4),
                'resume_adoption': round(data['stats']['resume_adoption'], 4),
            }
        }
    
    # Determine winner
    winner = max(results.items(), key=lambda x: x[1]['score'])
    report['winner'] = {
        'name': winner[0],
        'score': winner[1]['score'],
        'justification': generate_winner_justification(winner[0], winner[1])
    }
    
    # Save to file
    import os
    repo_root = os.environ.get('REPO_ROOT', '../../..')
    report_dir = os.path.join(repo_root, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    
    json_path = os.path.join(report_dir, 'variant_comparison.json')
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return json_path


def generate_winner_justification(name: str, data: Dict[str, Any]) -> str:
    """Generate justification text for why a variant won."""
    stats = data['stats']
    ttfv_s = stats['avg_ttfv_ms'] / 1000
    completion = stats['completion_rate']
    
    justifications = {
        'baseline': f"Baseline mantém o equilíbrio ideal com TTFV de {ttfv_s:.1f}s e {completion*100:.1f}% completion.",
        'variant_a': f"Template First reduziu TTFV para {ttfv_s:.1f}s com reordenação estratégica dos steps.",
        'variant_b': f"Resume Delayed melhorou decisão informada com {completion*100:.1f}% completion e overhead reduzido.",
        'variant_c': f"Fast Lane Early capturou mais usuários qualificados com {stats['fast_lane_adoption']*100:.1f}% adoption.",
    }
    
    return justifications.get(name, "Melhor performance geral nos critérios avaliados.")


def generate_markdown_report(results: Dict[str, Any]) -> str:
    """Generate markdown report from comparison results.
    
    Returns:
        Path to saved markdown file
    """
    import os
    repo_root = os.environ.get('REPO_ROOT', '../../..')
    report_dir = os.path.join(repo_root, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    
    # Find winner
    winner = max(results.items(), key=lambda x: x[1]['score'])
    
    md = f"""# Variant Comparison Report - v42 Onboarding Optimization

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Version:** v42  
**Simulations per variant:** {results.get('baseline', {}).get('sample_size', 0)}

---

## 🏆 Winner

**{winner[0].upper().replace('_', ' ')}**

- **Score:** {winner[1]['score']:.4f}
- **Justification:** {generate_winner_justification(winner[0], winner[1])}

---

## 📊 Comparative Results

| Variant | Score | Avg TTFV | Completion | Prefill | Fast Lane | Complexity |
|---------|-------|----------|------------|---------|-----------|------------|
"""
    
    # Sort by score descending
    sorted_results = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
    
    for name, data in sorted_results:
        stats = data['stats']
        is_winner = "🏆" if name == winner[0] else ""
        md += f"| {name.replace('_', ' ').title()} {is_winner} | "
        md += f"{data['score']:.3f} | "
        md += f"{stats['avg_ttfv_ms']/1000:.2f}s | "
        md += f"{stats['completion_rate']*100:.1f}% | "
        md += f"{stats['prefill_adoption']*100:.1f}% | "
        md += f"{stats['fast_lane_adoption']*100:.1f}% | "
        md += f"{data['complexity_penalty']*100:.0f}% |\n"
    
    md += f"""

## 🔬 Variant Descriptions

### Baseline
- Ordem padrão dos steps: welcome → workspace_setup → template_selection → customization → completion
- Comportamento de resume no início
- Fast lane check no step de workspace_setup

### Variant A: Template First
- **Mudança:** Reordena steps para template_selection antes de workspace_setup
- **Hipótese:** Escolher template primeiro dá contexto e reduz decisão no setup
- **Ajuste:** Redução de 5% no tempo base de step

### Variant B: Resume Prompt Delayed
- **Mudança:** Resume prompt aparece após 1 step (não no welcome)
- **Hipótese:** Evita sobrecarga cognitiva inicial, decisão mais informada
- **Ajuste:** Redução de 30% no overhead de resume

### Variant C: Fast Lane Early
- **Mudança:** Verificação de elegibilidade fast lane antes do welcome
- **Hipótese:** Usuários qualificados veem a opção no contexto ideal
- **Ajuste:** +20% na probabilidade de aceitação do fast lane

## 📈 Score Calculation

```
Score = 0.60 × TTFV_efficiency + 0.25 × completion_rate + 0.15 × simplicity

Where:
- TTFV_efficiency = baseline_TTFV / actual_TTFV (capped at 1.0)
- simplicity = 1 - complexity_penalty
```

### Complexity Penalties
| Variant | Penalty | Reason |
|---------|---------|--------|
| Baseline | 0% | Implementação existente |
| Variant A | 5% | Reordenação de steps (baixa complexidade) |
| Variant B | 10% | Lógica de delay (complexidade média) |
| Variant C | 8% | Check antecipado (complexidade baixa-média) |

## 📁 Files Generated
- `reports/variant_comparison.json` - Full data in JSON format
- `reports/variant_comparison.md` - This report

---
*Generated by v42 Onboarding Variant Comparison Harness*
"""
    
    md_path = os.path.join(report_dir, 'variant_comparison.md')
    with open(md_path, 'w') as f:
        f.write(md)
    
    return md_path


def print_comparison_table(results: Dict[str, Any]):
    """Print formatted comparison table to console."""
    print("=" * 80)
    print("VARIANT COMPARISON RESULTS")
    print("=" * 80)
    print()
    
    # Header
    print(f"{'Variant':<15} {'Score':>8} {'TTFV(s)':>10} {'Complete%':>10} {'FastLane%':>10}")
    print("-" * 80)
    
    # Sort by score
    sorted_results = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
    
    for name, data in sorted_results:
        stats = data['stats']
        marker = "🏆" if name == max(results.items(), key=lambda x: x[1]['score'])[0] else "  "
        print(f"{marker} {name:<13} {data['score']:>8.3f} "
              f"{stats['avg_ttfv_ms']/1000:>10.2f} {stats['completion_rate']*100:>10.1f} "
              f"{stats['fast_lane_adoption']*100:>10.1f}")
    
    print()


def main():
    """Main entry point for variant comparison."""
    print("=" * 80)
    print("v42 Onboarding Variant A/B/C Comparison")
    print("=" * 80)
    print()
    
    # Run comparison
    n_simulations = 50
    results = compare_variants(n=n_simulations)
    
    # Generate reports
    json_path = generate_json_report(results)
    md_path = generate_markdown_report(results)
    
    # Print results
    print_comparison_table(results)
    
    # Winner announcement
    winner = max(results.items(), key=lambda x: x[1]['score'])
    print("🏆 WINNER:")
    print(f"   Variant: {winner[0]}")
    print(f"   Score: {winner[1]['score']:.4f}")
    print(f"   TTFV: {winner[1]['stats']['avg_ttfv_ms']/1000:.2f}s")
    print(f"   Completion: {winner[1]['stats']['completion_rate']*100:.1f}%")
    print()
    
    # Files
    print("📁 Reports generated:")
    print(f"   - {json_path}")
    print(f"   - {md_path}")
    print()
    
    return results


if __name__ == "__main__":
    main()
