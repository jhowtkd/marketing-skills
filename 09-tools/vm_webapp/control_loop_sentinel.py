"""Online Control Loop - Regression Sentinel - v26.

Sentinel de regressão para detecção precoce em loop de controle online.
Implementa detecção em múltiplas janelas de tempo com histerese.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class RegressionSeverity(str, Enum):
    """Níveis de severidade de regressão."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DetectionWindow:
    """Configuração de janelas de detecção."""
    
    short_term_minutes: int = 15    # Detecção rápida
    medium_term_minutes: int = 60   # 1 hora
    long_term_minutes: int = 240    # 4 horas (ciclo)


@dataclass
class HysteresisState:
    """Estado de histerese para evitar flapping."""
    
    is_triggered: bool = False
    triggered_at: Optional[str] = None
    trigger_count: int = 0
    last_signal_id: Optional[str] = None
    cooldown_until: Optional[str] = None
    
    @property
    def is_clear(self) -> bool:
        """Retorna True se estado está limpo (não triggerado)."""
        return not self.is_triggered
    
    def trigger(self) -> None:
        """Transiciona para estado triggerado."""
        self.is_triggered = True
        self.triggered_at = datetime.now(timezone.utc).isoformat()
        self.trigger_count += 1
    
    def clear(self) -> None:
        """Limpa estado triggerado."""
        self.is_triggered = False
        self.triggered_at = None
    
    def set_cooldown(self, minutes: int) -> None:
        """Define período de cooldown."""
        from datetime import timedelta
        cooldown_end = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.cooldown_until = cooldown_end.isoformat()
    
    def is_in_cooldown(self) -> bool:
        """Verifica se está em período de cooldown."""
        if self.cooldown_until is None:
            return False
        cooldown_end = datetime.fromisoformat(self.cooldown_until)
        return datetime.now(timezone.utc) < cooldown_end


@dataclass
class RegressionSignal:
    """Sinal de regressão detectado."""
    
    signal_id: str
    metric_name: str
    severity: str
    detected_at: str
    value: float
    baseline: float
    delta_pct: float
    window_minutes: int
    suppressed: bool = False
    cleared_at: Optional[str] = None


@dataclass
class MetricThresholds:
    """Limites para detecção de regressão por métrica."""
    
    # V1 Score: queda de 5%/10%/15%/20% = low/medium/high/critical
    v1_score_low: float = -5.0
    v1_score_medium: float = -10.0
    v1_score_high: float = -15.0
    v1_score_critical: float = -20.0
    
    # Approval rate: queda similar
    approval_rate_low: float = -5.0
    approval_rate_medium: float = -10.0
    approval_rate_high: float = -15.0
    approval_rate_critical: float = -20.0
    
    # Incident rate: aumento (valores positivos = aumento)
    incident_rate_low: float = 20.0   # +20%
    incident_rate_medium: float = 50.0
    incident_rate_high: float = 100.0
    incident_rate_critical: float = 200.0


class RegressionSentinel:
    """Sentinel de regressão para loop de controle online."""
    
    version: str = "v26"
    
    def __init__(self):
        self._metric_history: dict[str, list[dict]] = {}
        self._signals: dict[str, list[RegressionSignal]] = {}
        self._hysteresis: dict[str, dict[str, HysteresisState]] = {}
        self._windows = DetectionWindow()
        self._thresholds = MetricThresholds()
        self._cooldown_minutes = 15  # Cooldown entre sinais do mesmo tipo
    
    def add_metric_point(self, run_id: str, metrics: dict) -> None:
        """Adiciona ponto de métrica ao histórico.
        
        Args:
            run_id: ID do run
            metrics: Dict com métricas (v1_score, approval_rate, etc.)
        """
        if run_id not in self._metric_history:
            self._metric_history[run_id] = []
        
        # Adicionar timestamp se não presente
        metrics_copy = dict(metrics)
        if "timestamp" not in metrics_copy:
            metrics_copy["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        self._metric_history[run_id].append(metrics_copy)
        
        # Limitar histórico a 48h (720 pontos de 4 min)
        max_points = 720
        if len(self._metric_history[run_id]) > max_points:
            self._metric_history[run_id] = self._metric_history[run_id][-max_points:]
    
    def get_metric_history(self, run_id: str) -> list[dict]:
        """Retorna histórico de métricas para um run."""
        return list(self._metric_history.get(run_id, []))
    
    def detect_regression(
        self,
        run_id: str,
        current_metrics: dict,
        window: str = "short",
    ) -> list[RegressionSignal]:
        """Detecta regressões comparando métricas atuais com baseline.
        
        Args:
            run_id: ID do run
            current_metrics: Métricas atuais
            window: Janela de detecção ("short", "medium", "long")
        
        Returns:
            Lista de sinais de regressão detectados
        """
        signals = []
        
        # Adicionar métrica atual ao histórico
        self.add_metric_point(run_id, current_metrics)
        
        # Obter baseline (média das últimas N medições estáveis)
        baseline = self._calculate_baseline(run_id, window)
        if baseline is None:
            return signals
        
        # Inicializar histerese para este run
        if run_id not in self._hysteresis:
            self._hysteresis[run_id] = {}
        
        # Verificar cada métrica
        metrics_to_check = [
            ("v1_score", self._thresholds.v1_score_low, self._thresholds.v1_score_critical, False),
            ("approval_rate", self._thresholds.approval_rate_low, self._thresholds.approval_rate_critical, False),
            ("incident_rate", self._thresholds.incident_rate_low, self._thresholds.incident_rate_critical, True),
        ]
        
        window_minutes = {
            "short": self._windows.short_term_minutes,
            "medium": self._windows.medium_term_minutes,
            "long": self._windows.long_term_minutes,
        }.get(window, self._windows.short_term_minutes)
        
        for metric_name, low_thresh, critical_thresh, is_spike in metrics_to_check:
            if metric_name not in current_metrics or metric_name not in baseline:
                continue
            
            current_val = current_metrics[metric_name]
            baseline_val = baseline[metric_name]
            
            if baseline_val == 0:
                continue
            
            # Calcular delta percentual
            delta_pct = ((current_val - baseline_val) / baseline_val) * 100
            
            # Para incidentes, aumento é negativo
            if is_spike and delta_pct > 0:
                severity = self._classify_severity_incident(delta_pct)
            elif not is_spike and delta_pct < 0:
                severity = self._classify_severity_v1(delta_pct)
            else:
                continue  # Sem regressão
            
            if severity is None:
                continue
            
            # Verificar histerese
            if metric_name not in self._hysteresis[run_id]:
                self._hysteresis[run_id][metric_name] = HysteresisState()
            
            hysteresis = self._hysteresis[run_id][metric_name]
            
            # Se já está triggerado ou em cooldown, suprimir novo sinal
            if hysteresis.is_triggered or hysteresis.is_in_cooldown():
                # Criar sinal suprimido para log/debug
                suppressed_signal = RegressionSignal(
                    signal_id=str(uuid4()),
                    metric_name=metric_name,
                    severity=severity.value,
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    value=current_val,
                    baseline=baseline_val,
                    delta_pct=delta_pct,
                    window_minutes=window_minutes,
                    suppressed=True,
                )
                if run_id not in self._signals:
                    self._signals[run_id] = []
                self._signals[run_id].append(suppressed_signal)
                continue
            
            # Criar sinal
            signal = RegressionSignal(
                signal_id=str(uuid4()),
                metric_name=metric_name,
                severity=severity.value,
                detected_at=datetime.now(timezone.utc).isoformat(),
                value=current_val,
                baseline=baseline_val,
                delta_pct=delta_pct,
                window_minutes=window_minutes,
            )
            
            # Atualizar histerese
            hysteresis.trigger()
            hysteresis.last_signal_id = signal.signal_id
            hysteresis.set_cooldown(self._cooldown_minutes)
            
            # Adicionar à lista de sinais
            if run_id not in self._signals:
                self._signals[run_id] = []
            self._signals[run_id].append(signal)
            
            signals.append(signal)
        
        return signals
    
    def _calculate_baseline(self, run_id: str, window: str) -> Optional[dict]:
        """Calcula baseline a partir do histórico.
        
        Retorna média das últimas N medições estáveis (excluindo última).
        """
        history = self._metric_history.get(run_id, [])
        if len(history) < 2:
            return None
        
        # Usar primeira medição como baseline (ponto de referência estável)
        # ou média das primeiras medições
        if len(history) == 2:
            # Com apenas 2 pontos, usar o primeiro como baseline
            baseline_points = [history[0]]
        else:
            # Com 3+ pontos, usar média dos primeiros (excluindo o atual)
            baseline_points = history[:-1]  # Tudo exceto o último (atual)
            if len(baseline_points) > 5:
                baseline_points = baseline_points[-5:]  # Últimos 5 estáveis
        
        # Calcular média para cada métrica
        baseline = {}
        for metric in ["v1_score", "approval_rate", "incident_rate", "cost_per_job", "mttc"]:
            values = [p.get(metric) for p in baseline_points if p.get(metric) is not None]
            if values:
                baseline[metric] = sum(values) / len(values)
        
        return baseline if baseline else None
    
    def _classify_severity_v1(self, delta_pct: float) -> Optional[RegressionSeverity]:
        """Classifica severidade para métricas V1/approval (queda negativa)."""
        if delta_pct <= self._thresholds.v1_score_critical:
            return RegressionSeverity.CRITICAL
        elif delta_pct <= self._thresholds.v1_score_high:
            return RegressionSeverity.HIGH
        elif delta_pct <= self._thresholds.v1_score_medium:
            return RegressionSeverity.MEDIUM
        elif delta_pct <= self._thresholds.v1_score_low:
            return RegressionSeverity.LOW
        return None
    
    def _classify_severity_incident(self, delta_pct: float) -> Optional[RegressionSeverity]:
        """Classifica severidade para incidentes (aumento positivo)."""
        if delta_pct >= self._thresholds.incident_rate_critical:
            return RegressionSeverity.CRITICAL
        elif delta_pct >= self._thresholds.incident_rate_high:
            return RegressionSeverity.HIGH
        elif delta_pct >= self._thresholds.incident_rate_medium:
            return RegressionSeverity.MEDIUM
        elif delta_pct >= self._thresholds.incident_rate_low:
            return RegressionSeverity.LOW
        return None
    
    def get_active_signals(self, run_id: str) -> list[RegressionSignal]:
        """Retorna sinais ativos (não limpos) para um run."""
        signals = self._signals.get(run_id, [])
        return [s for s in signals if s.cleared_at is None]
    
    def clear_signal(self, run_id: str, signal_id: str) -> bool:
        """Limpa um sinal específico.
        
        Args:
            run_id: ID do run
            signal_id: ID do sinal
        
        Returns:
            True se sinal foi encontrado e limpo
        """
        signals = self._signals.get(run_id, [])
        for signal in signals:
            if signal.signal_id == signal_id:
                signal.cleared_at = datetime.now(timezone.utc).isoformat()
                
                # Limpar histerese correspondente
                if run_id in self._hysteresis and signal.metric_name in self._hysteresis[run_id]:
                    self._hysteresis[run_id][signal.metric_name].clear()
                
                return True
        return False
    
    def clear_all_signals(self, run_id: str) -> int:
        """Limpa todos os sinais para um run.
        
        Returns:
            Número de sinais limpos
        """
        signals = self._signals.get(run_id, [])
        cleared = 0
        for signal in signals:
            if signal.cleared_at is None:
                signal.cleared_at = datetime.now(timezone.utc).isoformat()
                cleared += 1
        
        # Limpar todas as histereses
        if run_id in self._hysteresis:
            for state in self._hysteresis[run_id].values():
                state.clear()
        
        return cleared
    
    def get_status(self) -> dict:
        """Retorna status do sentinel."""
        total_signals = sum(len(signals) for signals in self._signals.values())
        active_signals = sum(
            len([s for s in signals if s.cleared_at is None])
            for signals in self._signals.values()
        )
        
        return {
            "version": self.version,
            "monitored_runs": len(self._metric_history),
            "total_signals_generated": total_signals,
            "active_signals": active_signals,
            "window_config": {
                "short_minutes": self._windows.short_term_minutes,
                "medium_minutes": self._windows.medium_term_minutes,
                "long_minutes": self._windows.long_term_minutes,
            },
        }
