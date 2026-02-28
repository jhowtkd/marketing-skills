"""
Task B: Segment Regression Alerts
Governança operacional v15 - Alertas automáticos de regressão por segmento
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from enum import Enum
from typing import Optional
from collections import defaultdict

from prometheus_client import Counter


class RegressionSeverity(str, Enum):
    """Níveis de severidade para alertas de regressão."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class RegressionReasonCode(str, Enum):
    """Códigos padronizados para razões de regressão."""
    APPROVAL_RATE_DROP = "approval_rate_drop"
    V1_SCORE_DECLINE = "v1_score_decline"
    REGEN_RATE_SPIKE = "regen_rate_spike"
    MULTI_METRIC_REGRESSION = "multi_metric_regression"


@dataclass
class RegressionAlert:
    """Alerta de regressão detectado."""
    alert_id: str
    segment_key: str
    severity: RegressionSeverity
    reason_code: RegressionReasonCode
    metric_name: str
    current_value: float
    baseline_value: float
    delta: float
    window_hours: int
    detected_at: datetime
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    false_positive: bool = False
    dismissed_at: Optional[datetime] = None
    dismissed_by: Optional[str] = None


class RegressionDetector:
    """
    Detector de regressão com histerese para evitar flapping.
    
    Thresholds:
    - INFO: 3% regressão
    - WARNING: 5% regressão  
    - CRITICAL: 10% regressão
    
    Histerese: Precisa melhorar 1% para limpar alerta
    """
    
    # Thresholds por tipo de métrica (valores absolutos de regressão)
    # INFO: até 3%, WARNING: 3-5%, CRITICAL: >10%
    THRESHOLDS = {
        "approval_without_regen_24h": {
            "info": 0.03,      # 3% drop = info
            "warning": 0.05,   # 5% drop = warning
            "critical": 0.10,  # 10% drop = critical
        },
        "v1_score_avg": {
            "info": 3.0,
            "warning": 5.0,
            "critical": 10.0,
        },
        "regenerations_per_job": {
            "info": 0.15,  # 15% increase
            "warning": 0.25,
            "critical": 0.40,
        }
    }
    
    # Histerese - quanto precisa melhorar para limpar
    HYSTERESIS = {
        "approval_without_regen_24h": 0.01,
        "v1_score_avg": 1.0,
        "regenerations_per_job": 0.05,
    }
    
    def detect(
        self,
        segment_key: str,
        metric_name: str,
        current: float,
        baseline: float,
        window_hours: int,
        previous_alert: Optional[RegressionAlert] = None
    ) -> Optional[RegressionAlert]:
        """
        Detecta regressão em uma métrica.
        
        Args:
            segment_key: Identificador do segmento
            metric_name: Nome da métrica
            current: Valor atual
            baseline: Valor baseline
            window_hours: Janela de análise em horas
            previous_alert: Alerta anterior (para histerese)
        
        Returns:
            RegressionAlert se regressão detectada, None caso contrário
        """
        if baseline == 0:
            return None
        
        delta = current - baseline
        
        # Para métricas que devem diminuir (regenerations), invertemos
        if metric_name == "regenerations_per_job":
            delta = -delta  # Increase is bad
        
        thresholds = self.THRESHOLDS.get(metric_name, self.THRESHOLDS["approval_without_regen_24h"])
        hysteresis = self.HYSTERESIS.get(metric_name, 0.01)
        
        # Check hysteresis - se estava em alerta
        if previous_alert and previous_alert.severity != RegressionSeverity.INFO:
            # Calcula mudança desde o alerta anterior (usando valores arredondados)
            delta_change = round(abs(round(delta, 4) - round(previous_alert.delta, 4)), 4)
            # Se mudou menos ou igual a histerese, não cria novo alerta
            if delta_change <= hysteresis:
                return None  # Ainda dentro da histerese, não cria novo alerta
        
        # Determina severidade baseado na magnitude da regressão
        # Usa round para evitar problemas de floating point (0.45-0.50 = -0.4999...)
        severity = None
        abs_delta = abs(round(delta, 4))
        if abs_delta >= thresholds["critical"]:
            severity = RegressionSeverity.CRITICAL
        elif abs_delta >= thresholds["warning"]:
            severity = RegressionSeverity.WARNING
        elif abs_delta >= thresholds["info"]:
            severity = RegressionSeverity.INFO
        
        if severity is None:
            return None
        
        # Mapeia para reason code
        reason_code = self._get_reason_code(metric_name)
        
        return RegressionAlert(
            alert_id=self._generate_alert_id(),
            segment_key=segment_key,
            severity=severity,
            reason_code=reason_code,
            metric_name=metric_name,
            current_value=current,
            baseline_value=baseline,
            delta=round(delta, 4),
            window_hours=window_hours,
            detected_at=datetime.now(UTC)
        )
    
    def _get_reason_code(self, metric_name: str) -> RegressionReasonCode:
        """Mapeia nome da métrica para reason code."""
        mapping = {
            "approval_without_regen_24h": RegressionReasonCode.APPROVAL_RATE_DROP,
            "v1_score_avg": RegressionReasonCode.V1_SCORE_DECLINE,
            "regenerations_per_job": RegressionReasonCode.REGEN_RATE_SPIKE,
        }
        return mapping.get(metric_name, RegressionReasonCode.APPROVAL_RATE_DROP)
    
    def _generate_alert_id(self) -> str:
        """Gera ID único para alerta."""
        import uuid
        return f"alert_{uuid.uuid4().hex[:12]}"


class AlertDeduplicator:
    """
    Deduplica alertas para evitar spam.
    
    Alertas do mesmo segmento/métrica dentro da janela de dedup
    são considerados o mesmo alerta.
    """
    
    def __init__(self, dedup_window_hours: int = 4):
        self.dedup_window = timedelta(hours=dedup_window_hours)
        self._recent_alerts: dict[str, datetime] = {}
    
    def _get_dedup_key(self, alert: RegressionAlert) -> str:
        """Gera chave de deduplicação."""
        return f"{alert.segment_key}:{alert.reason_code.value}:{alert.metric_name}"
    
    def should_alert(self, alert: RegressionAlert) -> bool:
        """
        Verifica se alerta deve ser emitido (não está deduplicado).
        
        Args:
            alert: Alerta candidato
        
        Returns:
            True se deve alertar, False se deduplicado
        """
        key = self._get_dedup_key(alert)
        now = datetime.now(UTC)
        
        if key in self._recent_alerts:
            last_alert_time = self._recent_alerts[key]
            if now - last_alert_time < self.dedup_window:
                return False  # Ainda dentro da janela
        
        return True
    
    def record_alert(self, alert: RegressionAlert):
        """Registra alerta para deduplicação futura."""
        key = self._get_dedup_key(alert)
        self._recent_alerts[key] = alert.detected_at
        
        # Cleanup de alertas antigos
        self._cleanup_old_alerts()
    
    def _cleanup_old_alerts(self):
        """Remove alertas expirados."""
        now = datetime.now(UTC)
        expired = [
            key for key, timestamp in self._recent_alerts.items()
            if now - timestamp > self.dedup_window
        ]
        for key in expired:
            del self._recent_alerts[key]


class RegressionMetrics:
    """Métricas Prometheus para alertas de regressão.
    
    Usa registry separado para evitar conflitos em testes.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if RegressionMetrics._initialized:
            return
            
        from prometheus_client import REGISTRY
        
        # Tenta criar métricas, ou reusa se já existirem
        try:
            self.alerts_detected_total = Counter(
                "vm_copilot_regression_alerts_detected_total",
                "Total de alertas de regressão detectados",
                ["segment_key", "severity"]
            )
        except ValueError:
            # Métrica já existe, pega do registry
            self.alerts_detected_total = REGISTRY._names_to_collectors[
                "vm_copilot_regression_alerts_detected_total"
            ]
        
        try:
            self.alerts_confirmed_total = Counter(
                "vm_copilot_regression_alerts_confirmed_total",
                "Total de alertas confirmados como regressão real",
                ["segment_key"]
            )
        except ValueError:
            self.alerts_confirmed_total = REGISTRY._names_to_collectors[
                "vm_copilot_regression_alerts_confirmed_total"
            ]
        
        try:
            self.alerts_false_positive_total = Counter(
                "vm_copilot_regression_alerts_false_positive_total",
                "Total de alertas descartados como falso positivo",
                ["segment_key"]
            )
        except ValueError:
            self.alerts_false_positive_total = REGISTRY._names_to_collectors[
                "vm_copilot_regression_alerts_false_positive_total"
            ]
        
        RegressionMetrics._initialized = True
    
    def record_detected(self, segment_key: str, severity: str):
        """Registra alerta detectado."""
        self.alerts_detected_total.labels(
            segment_key=segment_key,
            severity=severity
        ).inc()
    
    def record_confirmed(self, segment_key: str):
        """Registra alerta confirmado."""
        self.alerts_confirmed_total.labels(
            segment_key=segment_key
        ).inc()
    
    def record_false_positive(self, segment_key: str):
        """Registra falso positivo."""
        self.alerts_false_positive_total.labels(
            segment_key=segment_key
        ).inc()


# Instância global de métricas
_metrics = RegressionMetrics()


def _fetch_segment_metrics(segment_key: str) -> dict:
    """
    Busca métricas de um segmento (stub - implementação real consultaria DB).
    
    Returns:
        Dict com métricas no formato:
        {
            "metric_name": {"current": float, "baseline": float},
            ...
        }
    """
    # Stub - em produção, consultaria o banco de dados
    return {}


def _store_alert(alert: RegressionAlert):
    """Armazena alerta no banco (stub)."""
    pass


def _load_alerts(segment_key: Optional[str] = None) -> list[RegressionAlert]:
    """Carrega alertas do banco (stub)."""
    return []


def _update_alert(alert: RegressionAlert):
    """Atualiza alerta no banco (stub)."""
    pass


def detect_segment_regression(
    segment_key: str,
    window_hours: int = 24
) -> list[RegressionAlert]:
    """
    Detecta regressões em todas as métricas de um segmento.
    
    Args:
        segment_key: Identificador do segmento
        window_hours: Janela de análise
    
    Returns:
        Lista de alertas detectados
    """
    detector = RegressionDetector()
    deduplicator = AlertDeduplicator()
    
    metrics = _fetch_segment_metrics(segment_key)
    alerts = []
    
    for metric_name, values in metrics.items():
        current = values.get("current", 0)
        baseline = values.get("baseline", 0)
        
        alert = detector.detect(
            segment_key=segment_key,
            metric_name=metric_name,
            current=current,
            baseline=baseline,
            window_hours=window_hours
        )
        
        if alert and deduplicator.should_alert(alert):
            deduplicator.record_alert(alert)
            _store_alert(alert)
            _metrics.record_detected(segment_key, alert.severity.value)
            alerts.append(alert)
    
    # Consolida múltiplos alertas em um se necessário
    if len(alerts) >= 2:
        # Cria alerta consolidado de multi-métrica
        multi_alert = RegressionAlert(
            alert_id=detector._generate_alert_id(),
            segment_key=segment_key,
            severity=RegressionSeverity.CRITICAL,
            reason_code=RegressionReasonCode.MULTI_METRIC_REGRESSION,
            metric_name="multiple",
            current_value=0.0,
            baseline_value=0.0,
            delta=0.0,
            window_hours=window_hours,
            detected_at=datetime.now(UTC)
        )
        alerts.append(multi_alert)
    
    return alerts


def get_active_alerts(segment_key: Optional[str] = None) -> list[RegressionAlert]:
    """
    Retorna alertas ativos (não confirmados, não descartados).
    
    Args:
        segment_key: Filtro opcional por segmento
    
    Returns:
        Lista de alertas ativos
    """
    alerts = _load_alerts(segment_key)
    
    return [
        alert for alert in alerts
        if not alert.confirmed and not alert.false_positive
    ]


def confirm_alert(alert_id: str, confirmed_by: Optional[str] = None) -> Optional[RegressionAlert]:
    """
    Confirma um alerta como regressão real.
    
    Args:
        alert_id: ID do alerta
        confirmed_by: Quem confirmou
    
    Returns:
        Alerta atualizado ou None
    """
    alerts = _load_alerts()
    alert = next((a for a in alerts if a.alert_id == alert_id), None)
    
    if alert:
        alert.confirmed = True
        alert.confirmed_at = datetime.now(UTC)
        _update_alert(alert)
        _metrics.record_confirmed(alert.segment_key)
    
    return alert


def dismiss_false_positive(
    alert_id: str,
    dismissed_by: Optional[str] = None,
    reason: Optional[str] = None
) -> Optional[RegressionAlert]:
    """
    Descarta um alerta como falso positivo.
    
    Args:
        alert_id: ID do alerta
        dismissed_by: Quem descartou
        reason: Razão do descarte
    
    Returns:
        Alerta atualizado ou None
    """
    alerts = _load_alerts()
    alert = next((a for a in alerts if a.alert_id == alert_id), None)
    
    if alert:
        alert.false_positive = True
        alert.dismissed_at = datetime.now(UTC)
        alert.dismissed_by = dismissed_by
        _update_alert(alert)
        _metrics.record_false_positive(alert.segment_key)
    
    return alert
