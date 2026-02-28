"""
Task A: Weekly KPI Scoreboard
Governança operacional v15 - Painel semanal de KPI real vs meta
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Optional


class KpiStatus(str, Enum):
    """Status de performance vs target."""
    ON_TRACK = "on_track"
    ATTENTION = "attention"
    OFF_TRACK = "off_track"


class KpiTarget:
    """Targets v15 para métricas de governança."""
    # approval_without_regen_24h: +5 p.p. vs v13
    APPROVAL_WITHOUT_REGEN_24H_DELTA = 0.05
    
    # V1 score avg: +6 pontos em segmentos elegíveis
    V1_SCORE_AVG_DELTA = 6.0
    
    # regenerations/job: -15% em segmentos elegíveis
    REGENERATIONS_PER_JOB_DELTA = -0.15
    
    # Tolerâncias para classificação de status
    TOLERANCE_POSITIVE = 0.02  # ±2 p.p.
    TOLERANCE_SCORE = 2.0      # ±2 pontos
    TOLERANCE_REDUCTION = 0.05  # ±5 p.p.


@dataclass
class KpiWeeklyDelta:
    """Delta semanal de um KPI vs baseline e target."""
    metric_name: str
    current_value: float
    baseline_value: float
    actual_delta: float
    target_delta: float
    gap_to_target: float
    status: KpiStatus
    
    @property
    def is_on_target(self) -> bool:
        """Verifica se está no target considerando tolerância."""
        return self.status == KpiStatus.ON_TRACK


@dataclass
class SegmentKpiSummary:
    """Resumo de KPIs para um segmento específico."""
    segment_key: str
    runs_count: int
    approval_without_regen_24h: KpiWeeklyDelta
    v1_score_avg: KpiWeeklyDelta
    regenerations_per_job: KpiWeeklyDelta
    overall_status: KpiStatus
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GlobalKpiSummary:
    """Resumo global agregado de todos os segmentos."""
    total_runs: int
    total_segments: int
    segments_on_track: int
    segments_attention: int
    segments_off_track: int
    approval_without_regen_24h: KpiWeeklyDelta
    v1_score_avg: KpiWeeklyDelta
    regenerations_per_job: KpiWeeklyDelta
    overall_status: KpiStatus


def calculate_kpi_status(
    current: float,
    baseline: float,
    target_delta: float,
    tolerance: float = 0.02
) -> KpiStatus:
    """
    Calcula o status de um KPI baseado no delta atual vs target.
    
    Args:
        current: Valor atual
        baseline: Valor baseline (v13)
        target_delta: Delta esperado (positivo para aumento, negativo para redução)
        tolerance: Tolerância para considerar "at attention"
    
    Returns:
        Status do KPI
    """
    if baseline == 0:
        # Sem baseline, qualquer valor positivo é considerado on_track
        return KpiStatus.ON_TRACK if current > 0 else KpiStatus.OFF_TRACK
    
    actual_delta = current - baseline
    gap = actual_delta - target_delta
    
    # Para targets positivos (aumento desejado)
    if target_delta > 0:
        if actual_delta >= target_delta:
            return KpiStatus.ON_TRACK
        elif actual_delta >= (target_delta - tolerance):
            return KpiStatus.ATTENTION
        else:
            return KpiStatus.OFF_TRACK
    
    # Para targets negativos (redução desejada)
    else:
        if actual_delta <= target_delta:
            return KpiStatus.ON_TRACK
        elif actual_delta <= (target_delta + tolerance):
            return KpiStatus.ATTENTION
        else:
            return KpiStatus.OFF_TRACK


def calculate_delta_vs_target(
    current: float,
    baseline: float,
    target_delta: float
) -> KpiWeeklyDelta:
    """
    Calcula o delta vs target para um KPI.
    
    Args:
        current: Valor atual
        baseline: Valor baseline
        target_delta: Delta esperado
    
    Returns:
        KpiWeeklyDelta com todos os cálculos
    """
    if baseline == 0:
        actual_delta = current if current > 0 else 0
    else:
        actual_delta = current - baseline
    
    gap_to_target = target_delta - actual_delta
    
    # Define tolerância baseada no tipo de métrica
    if target_delta == KpiTarget.APPROVAL_WITHOUT_REGEN_24H_DELTA:
        tolerance = KpiTarget.TOLERANCE_POSITIVE
    elif target_delta == KpiTarget.V1_SCORE_AVG_DELTA:
        tolerance = KpiTarget.TOLERANCE_SCORE
    else:
        tolerance = KpiTarget.TOLERANCE_REDUCTION
    
    status = calculate_kpi_status(current, baseline, target_delta, tolerance)
    
    # Determina nome da métrica baseado no target
    metric_name = _get_metric_name(target_delta)
    
    return KpiWeeklyDelta(
        metric_name=metric_name,
        current_value=current,
        baseline_value=baseline,
        actual_delta=actual_delta,
        target_delta=target_delta,
        gap_to_target=gap_to_target,
        status=status
    )


def _get_metric_name(target_delta: float) -> str:
    """Mapeia target_delta para nome da métrica."""
    if target_delta == KpiTarget.APPROVAL_WITHOUT_REGEN_24H_DELTA:
        return "approval_without_regen_24h"
    elif target_delta == KpiTarget.V1_SCORE_AVG_DELTA:
        return "v1_score_avg"
    elif target_delta == KpiTarget.REGENERATIONS_PER_JOB_DELTA:
        return "regenerations_per_job"
    return "unknown"


def aggregate_weekly_kpis(
    segment_data_list: list[dict],
    baseline_data: dict[str, dict]
) -> list[SegmentKpiSummary]:
    """
    Agrega KPIs semanais para múltiplos segmentos.
    
    Args:
        segment_data_list: Lista de dados de segmentos
        baseline_data: Dict de baseline por segment_key
    
    Returns:
        Lista de SegmentKpiSummary
    """
    summaries = []
    
    for segment_data in segment_data_list:
        segment_key = segment_data["segment_key"]
        baseline = baseline_data.get(segment_key, {
            "approval_without_regen_24h": 0.50,
            "v1_score_avg": 76.0,
            "regenerations_per_job": 1.00,
        })
        
        # Calcula deltas para cada métrica
        approval_delta = calculate_delta_vs_target(
            current=segment_data.get("approval_without_regen_24h", 0.50),
            baseline=baseline.get("approval_without_regen_24h", 0.50),
            target_delta=KpiTarget.APPROVAL_WITHOUT_REGEN_24H_DELTA
        )
        
        v1_score_delta = calculate_delta_vs_target(
            current=segment_data.get("v1_score_avg", 76.0),
            baseline=baseline.get("v1_score_avg", 76.0),
            target_delta=KpiTarget.V1_SCORE_AVG_DELTA
        )
        
        regen_delta = calculate_delta_vs_target(
            current=segment_data.get("regenerations_per_job", 1.00),
            baseline=baseline.get("regenerations_per_job", 1.00),
            target_delta=KpiTarget.REGENERATIONS_PER_JOB_DELTA
        )
        
        # Calcula status geral (pior dos três)
        statuses = [approval_delta.status, v1_score_delta.status, regen_delta.status]
        if KpiStatus.OFF_TRACK in statuses:
            overall_status = KpiStatus.OFF_TRACK
        elif KpiStatus.ATTENTION in statuses:
            overall_status = KpiStatus.ATTENTION
        else:
            overall_status = KpiStatus.ON_TRACK
        
        summary = SegmentKpiSummary(
            segment_key=segment_key,
            runs_count=segment_data.get("runs_count", 0),
            approval_without_regen_24h=approval_delta,
            v1_score_avg=v1_score_delta,
            regenerations_per_job=regen_delta,
            overall_status=overall_status
        )
        
        summaries.append(summary)
    
    return summaries


def _fetch_segment_metrics(brand_id: Optional[str] = None) -> list[dict]:
    """
    Busca métricas dos segmentos (stub - implementação real consultaria DB).
    
    Args:
        brand_id: Filtro opcional por brand
    
    Returns:
        Lista de métricas por segmento
    """
    # Stub - em produção, consultaria o banco de dados
    return []


def _fetch_baseline_metrics(brand_id: Optional[str] = None) -> dict[str, dict]:
    """
    Busca baseline v13 por segmento (stub - implementação real consultaria DB).
    
    Args:
        brand_id: Filtro opcional por brand
    
    Returns:
        Dict de baseline por segment_key
    """
    # Stub - em produção, consultaria o banco de dados
    return {}


def _calculate_global_summary(
    segment_summaries: list[SegmentKpiSummary]
) -> Optional[GlobalKpiSummary]:
    """
    Calcula resumo global agregado.
    
    Args:
        segment_summaries: Lista de resumos por segmento
    
    Returns:
        GlobalKpiSummary ou None se não houver segmentos
    """
    if not segment_summaries:
        return None
    
    total_runs = sum(s.runs_count for s in segment_summaries)
    total_segments = len(segment_summaries)
    
    if total_runs == 0:
        return None
    
    # Conta status
    segments_on_track = sum(1 for s in segment_summaries if s.overall_status == KpiStatus.ON_TRACK)
    segments_attention = sum(1 for s in segment_summaries if s.overall_status == KpiStatus.ATTENTION)
    segments_off_track = sum(1 for s in segment_summaries if s.overall_status == KpiStatus.OFF_TRACK)
    
    # Calcula médias ponderadas
    weighted_approval = sum(
        s.approval_without_regen_24h.current_value * s.runs_count 
        for s in segment_summaries
    ) / total_runs
    
    weighted_v1_score = sum(
        s.v1_score_avg.current_value * s.runs_count 
        for s in segment_summaries
    ) / total_runs
    
    weighted_regen = sum(
        s.regenerations_per_job.current_value * s.runs_count 
        for s in segment_summaries
    ) / total_runs
    
    # Baseline global (média dos baselines dos segmentos)
    baseline_approval = sum(
        s.approval_without_regen_24h.baseline_value * s.runs_count 
        for s in segment_summaries
    ) / total_runs
    
    baseline_v1_score = sum(
        s.v1_score_avg.baseline_value * s.runs_count 
        for s in segment_summaries
    ) / total_runs
    
    baseline_regen = sum(
        s.regenerations_per_job.baseline_value * s.runs_count 
        for s in segment_summaries
    ) / total_runs
    
    # Calcula deltas globais
    global_approval = calculate_delta_vs_target(
        current=weighted_approval,
        baseline=baseline_approval,
        target_delta=KpiTarget.APPROVAL_WITHOUT_REGEN_24H_DELTA
    )
    
    global_v1_score = calculate_delta_vs_target(
        current=weighted_v1_score,
        baseline=baseline_v1_score,
        target_delta=KpiTarget.V1_SCORE_AVG_DELTA
    )
    
    global_regen = calculate_delta_vs_target(
        current=weighted_regen,
        baseline=baseline_regen,
        target_delta=KpiTarget.REGENERATIONS_PER_JOB_DELTA
    )
    
    # Status geral
    if segments_off_track > 0:
        overall_status = KpiStatus.OFF_TRACK
    elif segments_attention > 0:
        overall_status = KpiStatus.ATTENTION
    else:
        overall_status = KpiStatus.ON_TRACK
    
    return GlobalKpiSummary(
        total_runs=total_runs,
        total_segments=total_segments,
        segments_on_track=segments_on_track,
        segments_attention=segments_attention,
        segments_off_track=segments_off_track,
        approval_without_regen_24h=global_approval,
        v1_score_avg=global_v1_score,
        regenerations_per_job=global_regen,
        overall_status=overall_status
    )


def get_kpi_scoreboard(brand_id: Optional[str] = None) -> dict:
    """
    Retorna o painel semanal de KPIs.
    
    Args:
        brand_id: Filtro opcional por brand
    
    Returns:
        Dict com estrutura:
        {
            "week_ending": str,
            "global": GlobalKpiSummary | None,
            "segments": list[SegmentKpiSummary]
        }
    """
    # Busca dados
    segment_metrics = _fetch_segment_metrics(brand_id)
    baseline_metrics = _fetch_baseline_metrics(brand_id)
    
    # Agrega por segmento
    segment_summaries = aggregate_weekly_kpis(segment_metrics, baseline_metrics)
    
    # Calcula global
    global_summary = _calculate_global_summary(segment_summaries)
    
    # Determina fim da semana (domingo)
    now = datetime.now(UTC)
    days_to_sunday = 6 - now.weekday() if now.weekday() != 6 else 0
    week_ending = (now + __import__('datetime').timedelta(days=days_to_sunday)).strftime("%Y-%m-%d")
    
    return {
        "week_ending": week_ending,
        "global": global_summary,
        "segments": segment_summaries
    }
