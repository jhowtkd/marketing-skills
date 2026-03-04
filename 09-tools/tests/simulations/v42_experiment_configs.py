"""v42 Onboarding Optimization Loop - Experiment Configurations.

Configurações de simulação para as variações A/B/C de fluxo onboarding.
Importar e usar com OnboardingSimulator do harness v41.
"""

from tests.simulations.onboarding_simulation_runner import SimulationConfig


# =============================================================================
# BASELINE (Controle)
# =============================================================================

BASELINE_CONFIG = SimulationConfig(
    steps=[
        "welcome",
        "workspace_setup",
        "template_selection",
        "customization",
        "completion"
    ],
    step_duration_base_ms=5000,
    step_duration_variance_ms=2000,
    prefill_time_saved_ms=3000,
    fast_lane_time_saved_per_step_ms=4000,
    resume_overhead_ms=500,
    fast_test_mode=False,
    prefill_probability=0.4,
    fast_lane_eligible_probability=0.3,
    fast_lane_accept_probability=0.7,
    interrupt_probability=0.3,
    abandon_probability=0.15,
    fast_lane_skippable=["customization"],
)


# =============================================================================
# VARIAÇÃO A: Template First (Reordenar Steps)
# =============================================================================
# Hipótese: Selecionar template antes reduz fricção inicial ao dar contexto
# imediato ao usuário sobre o que ele vai criar.
# 
# Fluxo: welcome → template_selection → workspace_setup → customization → completion
# =============================================================================

VARIATION_A_CONFIG = SimulationConfig(
    steps=[
        "welcome",
        "template_selection",   # Movido para antes do workspace_setup
        "workspace_setup",      # Agora vem depois do template
        "customization",
        "completion"
    ],
    step_duration_base_ms=5000,
    step_duration_variance_ms=2000,
    prefill_time_saved_ms=3500,  # +17% pois tem mais contexto do template
    fast_lane_time_saved_per_step_ms=4000,
    resume_overhead_ms=500,
    fast_test_mode=False,
    prefill_probability=0.50,   # Aumentado de 0.4 devido ao contexto do template
    fast_lane_eligible_probability=0.30,
    fast_lane_accept_probability=0.70,
    interrupt_probability=0.30,
    abandon_probability=0.12,   # Reduzido de 0.15 (menor abandono early)
    fast_lane_skippable=["customization"],
)


# =============================================================================
# VARIAÇÃO B: Progressive Disclosure (Dividir Workspace Setup)
# =============================================================================
# Hipótese: Dividir workspace_setup em múltiplos steps menores reduz carga
# cognitiva e cria momentum de progresso.
#
# Fluxo: welcome → workspace_basic → template_selection → workspace_advanced 
#        → customization → completion
# =============================================================================

VARIATION_B_CONFIG = SimulationConfig(
    steps=[
        "welcome",
        "workspace_basic",      # Novo: apenas configurações essenciais
        "template_selection",
        "workspace_advanced",   # Novo: configurações adicionais
        "customization",
        "completion"
    ],
    step_duration_base_ms=3500,  # Reduzido de 5000 (steps menores = mais rápidos)
    step_duration_variance_ms=1500,
    prefill_time_saved_ms=3000,
    fast_lane_time_saved_per_step_ms=4000,
    resume_overhead_ms=400,     # Reduzido (steps menores = menos contexto para recuperar)
    fast_test_mode=False,
    prefill_probability=0.40,
    fast_lane_eligible_probability=0.40,  # +33% (pode pular workspace_advanced)
    fast_lane_accept_probability=0.75,    # +7% (usuários mais engajados)
    interrupt_probability=0.25,           # -17% (menos intimidante)
    abandon_probability=0.10,             # -33% (steps menores = menos abandono)
    fast_lane_skippable=[
        "workspace_advanced",   # Pode pular configurações avançadas
        "customization"
    ],
)


# =============================================================================
# VARIAÇÃO C: Quick Start First (Gamificação do Progresso)
# =============================================================================
# Hipótese: Começar com um "quick win" antes de configurações complexas
# aumenta engagement através do investment loop.
#
# Fluxo: welcome → quick_start_template → template_selection → workspace_setup
#        → full_customization → completion
# =============================================================================

VARIATION_C_CONFIG = SimulationConfig(
    steps=[
        "welcome",
        "quick_start_template",  # Novo: quick win inicial (template pré-selecionado)
        "template_selection",
        "workspace_setup",
        "full_customization",    # Renomeado: customization completo
        "completion"
    ],
    step_duration_base_ms=5000,
    step_duration_variance_ms=2000,
    prefill_time_saved_ms=3000,
    fast_lane_time_saved_per_step_ms=4000,
    resume_overhead_ms=500,
    fast_test_mode=False,
    prefill_probability=0.80,   # +100% (quick start sempre tem prefill forte)
    fast_lane_eligible_probability=0.30,
    fast_lane_accept_probability=0.70,
    interrupt_probability=0.20,  # -33% (engajamento inicial maior)
    abandon_probability=0.08,    # -47% (investment loop reduz abandono)
    fast_lane_skippable=["full_customization"],
)


# =============================================================================
# CONFIGURAÇÕES DE TESTE RÁPIDO (fast_test_mode=True)
# =============================================================================

BASELINE_CONFIG_FAST = SimulationConfig(
    **{**BASELINE_CONFIG.__dict__, "fast_test_mode": True}
)

VARIATION_A_CONFIG_FAST = SimulationConfig(
    **{**VARIATION_A_CONFIG.__dict__, "fast_test_mode": True}
)

VARIATION_B_CONFIG_FAST = SimulationConfig(
    **{**VARIATION_B_CONFIG.__dict__, "fast_test_mode": True}
)

VARIATION_C_CONFIG_FAST = SimulationConfig(
    **{**VARIATION_C_CONFIG.__dict__, "fast_test_mode": True}
)


# =============================================================================
# MÉTRICAS E GUARDRAILS
# =============================================================================

PRIMARY_METRICS = [
    "time_to_first_value_ms",
    "completion_rate",
    "steps_completed",
    "prefill_adoption",
    "fast_lane_adoption",
    "resume_adoption",
]

SECONDARY_METRICS = [
    "avg_step_duration_ms",
    "dropoff_by_step",
    "feature_usage_combinations",
]

# Guardrails para validação de resultados
GUARDRAILS = {
    "min_completion_rate": 0.75,        # Mínimo 75% completion
    "max_ttfv_increase_percent": 20,    # TTFV não pode aumentar > 20%
    "min_prefill_adoption": 0.30,       # Prefill mínimo 30%
    "min_fast_lane_eligible": 0.25,     # Fast lane elegível mínimo 25%
}

# Thresholds de sucesso para cada variação
SUCCESS_THRESHOLDS = {
    "variation_a": {
        "min_ttfv_improvement_percent": 10,
        "min_completion_improvement_pp": 5,
    },
    "variation_b": {
        "min_ttfv_improvement_percent": 5,
        "min_completion_improvement_pp": 8,
    },
    "variation_c": {
        "max_ttfv_increase_acceptable_percent": 5,
        "min_completion_improvement_pp": 12,
        "min_activation_improvement_percent": 15,
    },
}


# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================

def get_config_by_name(name: str, fast_mode: bool = False) -> SimulationConfig:
    """Get simulation config by variation name.
    
    Args:
        name: One of 'baseline', 'variation_a', 'variation_b', 'variation_c'
        fast_mode: If True, return config with fast_test_mode=True
    
    Returns:
        SimulationConfig for the specified variation
    """
    suffix = "_FAST" if fast_mode else ""
    config_map = {
        "baseline": BASELINE_CONFIG,
        "variation_a": VARIATION_A_CONFIG,
        "variation_b": VARIATION_B_CONFIG,
        "variation_c": VARIATION_C_CONFIG,
        "baseline_fast": BASELINE_CONFIG_FAST,
        "variation_a_fast": VARIATION_A_CONFIG_FAST,
        "variation_b_fast": VARIATION_B_CONFIG_FAST,
        "variation_c_fast": VARIATION_C_CONFIG_FAST,
    }
    
    key = f"{name.lower()}{suffix}"
    if key not in config_map:
        raise ValueError(f"Unknown config name: {name}. Available: {list(config_map.keys())}")
    
    return config_map[key]


def get_all_configs(fast_mode: bool = False) -> dict:
    """Get all configurations as a dictionary.
    
    Returns:
        Dict mapping config names to SimulationConfig objects
    """
    return {
        "baseline": get_config_by_name("baseline", fast_mode),
        "variation_a": get_config_by_name("variation_a", fast_mode),
        "variation_b": get_config_by_name("variation_b", fast_mode),
        "variation_c": get_config_by_name("variation_c", fast_mode),
    }


def validate_guardrails(stats: dict) -> dict:
    """Validate simulation results against guardrails.
    
    Args:
        stats: Statistics dict from calculate_statistics()
    
    Returns:
        Dict with validation results
    """
    violations = []
    
    if stats.get("completion_rate", 1.0) < GUARDRAILS["min_completion_rate"]:
        violations.append(f"completion_rate below minimum ({GUARDRAILS['min_completion_rate']})")
    
    if stats.get("prefill_adoption", 1.0) < GUARDRAILS["min_prefill_adoption"]:
        violations.append(f"prefill_adoption below minimum ({GUARDRAILS['min_prefill_adoption']})")
    
    if stats.get("fast_lane_adoption", 1.0) < GUARDRAILS["min_fast_lane_eligible"]:
        violations.append(f"fast_lane_adoption below minimum ({GUARDRAILS['min_fast_lane_eligible']})")
    
    return {
        "valid": len(violations) == 0,
        "violations": violations,
    }


# =============================================================================
# EXEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    from tests.simulations.onboarding_simulation_runner import (
        OnboardingSimulator, JourneyType, calculate_statistics
    )
    
    print("v42 Onboarding Experiment Configurations")
    print("=" * 50)
    
    # Test each configuration
    for name, config in get_all_configs(fast_mode=True).items():
        print(f"\n{name.upper()}:")
        print(f"  Steps: {config.steps}")
        print(f"  Fast test mode: {config.fast_test_mode}")
        
        # Quick simulation
        sim = OnboardingSimulator(config)
        results = sim.run_batch(JourneyType.HAPPY_PATH, count=10)
        stats = calculate_statistics(results)
        
        print(f"  Avg TTFV: {stats['avg_ttfv_ms']:.0f}ms")
        print(f"  Completion rate: {stats['completion_rate']:.1%}")
        print(f"  Prefill adoption: {stats['prefill_adoption']:.1%}")
