"""
Approval Cost Optimizer - v23

Otimização de custo de aprovação humana para medium/high risk via:
- Triagem refinada de risco
- Batching inteligente
- Fila priorizada
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4


class RiskLevel:
    """Níveis de risco."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalRequest:
    """Request de aprovação."""

    request_id: str
    run_id: str
    node_id: str
    node_type: str
    risk_level: str
    brand_id: str
    impact_score: float = 0.5
    urgency_hours: Optional[float] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "pending"  # pending, approved, rejected, expired
    params: dict[str, Any] = field(default_factory=dict)


class RiskTriageRefiner:
    """Refinador de risco para requests de aprovação."""

    def __init__(self):
        self._risk_weights = {
            "impact": 0.4,
            "revenue_at_risk": 0.3,
            "node_type_risk": 0.2,
            "historical_failure_rate": 0.1,
        }

    def _get_value(self, request: Any, key: str, default: Any = None) -> Any:
        """Obtém valor de dict ou objeto."""
        if isinstance(request, dict):
            return request.get(key, default)
        return getattr(request, key, default)

    def refine_risk(self, request: Any) -> dict[str, Any]:
        """
        Refina o risco de um request de aprovação.

        Args:
            request: Request com node_type, risk_level, params

        Returns:
            Request enriquecido com refined_risk_score e risk_factors
        """
        base_risk = self._base_risk_from_level(
            self._get_value(request, "risk_level", "medium")
        )

        risk_factors = []
        score_adjustments = []

        params = self._get_value(request, "params", {})
        if not isinstance(params, dict):
            params = {}

        # Factor 1: Impact
        impact = params.get("impact", "medium")
        if impact == "critical":
            score_adjustments.append(0.3)
            risk_factors.append("critical_impact")
        elif impact == "high":
            score_adjustments.append(0.2)
            risk_factors.append("high_impact")
        elif impact == "low":
            score_adjustments.append(-0.1)
            risk_factors.append("low_impact")

        # Factor 2: Revenue at risk
        revenue = params.get("revenue_at_risk", 0)
        if revenue > 50000:
            score_adjustments.append(0.2)
            risk_factors.append("high_revenue_at_risk")
        elif revenue > 10000:
            score_adjustments.append(0.1)
            risk_factors.append("medium_revenue_at_risk")

        # Factor 3: Node type risk
        node_type = self._get_value(request, "node_type", "")
        high_risk_types = {"publish", "deploy", "delete", "sms_send"}
        if node_type in high_risk_types:
            score_adjustments.append(0.15)
            risk_factors.append(f"high_risk_node_type:{node_type}")

        # Calculate final score
        refined_score = base_risk + sum(score_adjustments)
        refined_score = max(0.0, min(1.0, refined_score))  # Clamp to [0, 1]

        # Build result dict
        if isinstance(request, dict):
            result = dict(request)
        else:
            result = {
                "request_id": self._get_value(request, "request_id"),
                "run_id": self._get_value(request, "run_id"),
                "node_id": self._get_value(request, "node_id"),
                "node_type": self._get_value(request, "node_type"),
                "risk_level": self._get_value(request, "risk_level"),
                "brand_id": self._get_value(request, "brand_id"),
                "impact_score": self._get_value(request, "impact_score"),
                "urgency_hours": self._get_value(request, "urgency_hours"),
                "created_at": self._get_value(request, "created_at"),
                "status": self._get_value(request, "status"),
            }

        result.update(
            {
                "original_risk": self._get_value(request, "risk_level", "medium"),
                "refined_risk_score": round(refined_score, 4),
                "risk_factors": risk_factors,
                "factors": {
                    f: True for f in risk_factors
                },  # Para compatibilidade com testes
                "base_risk_score": base_risk,
            }
        )
        return result

    def _base_risk_from_level(self, level: str) -> float:
        """Converte nível de risco para score base."""
        return {
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 0.9,
        }.get(level, 0.5)

    # Alias para compatibilidade com testes
    refine = refine_risk


class PriorityScorer:
    """Calculador de score de prioridade."""

    def __init__(self):
        self._urgency_weights = {
            "critical": 1.0,
            "high": 0.7,
            "medium": 0.4,
            "low": 0.1,
        }

    def _get_value(self, request: Any, key: str, default: Any = None) -> Any:
        """Obtém valor de dict ou objeto."""
        if isinstance(request, dict):
            return request.get(key, default)
        return getattr(request, key, default)

    def calculate_priority(self, request: Any) -> dict[str, Any]:
        """
        Calcula prioridade baseada em risco, urgência e impacto.

        Args:
            request: Request com refined_risk_score, urgency, etc.

        Returns:
            Request enriquecido com priority_score e priority_level
        """
        # Components
        risk_score = self._get_value(request, "refined_risk_score", 0.5)

        # Use urgency_hours if available, otherwise fall back to urgency level
        urgency_hours = self._get_value(request, "urgency_hours")
        if urgency_hours is not None:
            # Convert hours to urgency weight (less hours = higher urgency)
            if urgency_hours <= 1:
                urgency_weight = 1.0  # critical
            elif urgency_hours <= 4:
                urgency_weight = 0.7  # high
            elif urgency_hours <= 24:
                urgency_weight = 0.4  # medium
            else:
                urgency_weight = 0.1  # low
        else:
            urgency = self._get_value(request, "urgency", "medium")
            urgency_weight = self._urgency_weights.get(urgency, 0.4)

        wait_time = self._get_value(request, "wait_time_seconds", 0)
        wait_bonus = min(wait_time / 3600, 0.2)  # Max 0.2 bonus for waiting >1h

        # Use impact_score directly if available
        impact_value = self._get_value(request, "impact_score", 0)
        business_impact = self._get_value(request, "business_impact", 0)
        if impact_value:
            impact_score = impact_value * 0.6  # Scale to max 0.6
        else:
            impact_score = min(business_impact / 50000, 0.3)  # Max 0.3 for high impact

        # Calculate priority score
        priority_score = (
            risk_score * 0.3
            + urgency_weight * 0.35
            + wait_bonus * 0.05
            + impact_score * 0.3
        )

        priority_score = round(max(0.0, min(1.0, priority_score)), 4)

        # Determine priority level
        if priority_score >= 0.8:
            priority_level = "critical"
        elif priority_score >= 0.6:
            priority_level = "high"
        elif priority_score >= 0.3:
            priority_level = "medium"
        else:
            priority_level = "low"

        # Convert request to dict if needed
        if isinstance(request, dict):
            result = dict(request)
        else:
            result = {
                "request_id": self._get_value(request, "request_id"),
                "run_id": self._get_value(request, "run_id"),
                "node_id": self._get_value(request, "node_id"),
                "node_type": self._get_value(request, "node_type"),
                "risk_level": self._get_value(request, "risk_level"),
                "brand_id": self._get_value(request, "brand_id"),
                "impact_score": self._get_value(request, "impact_score"),
                "urgency_hours": self._get_value(request, "urgency_hours"),
                "created_at": self._get_value(request, "created_at"),
                "status": self._get_value(request, "status"),
            }

        result.update(
            {
                "priority_score": priority_score,
                "priority_level": priority_level,
            }
        )
        return result

    def order_queue(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Ordena fila por prioridade (determinístico).

        Args:
            requests: Lista de requests

        Returns:
            Lista ordenada por prioridade (maior primeiro)
        """
        # Calculate priority for all
        scored = [self.calculate_priority(r) for r in requests]

        # Sort by priority_score DESC, then created_at ASC (FIFO tie-breaker)
        return sorted(
            scored,
            key=lambda r: (-r["priority_score"], r.get("created_at", "")),
        )


@dataclass
class ApprovalBatch:
    """Lote de aprovações."""

    batch_id: str
    brand_id: str
    requests: list[dict[str, Any]]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected, expanded
    total_value: float = 0.0
    risk_score: float = 0.0


@dataclass
class BatchSizeLimits:
    """Limites de tamanho para batches."""

    max_batch_size: int = 10
    max_total_value: float = 100000.0
    default_ttl_seconds: int = 3600


class BatchGuard:
    """Guardas de segurança para batches."""

    def __init__(
        self,
        max_total_value: float = 100000.0,
        auto_approve_threshold: float = 0.3,
    ):
        self.max_total_value = max_total_value
        self.auto_approve_threshold = auto_approve_threshold

    def _get_value(self, request: Any, key: str, default: Any = None) -> Any:
        """Obtém valor de dict ou objeto."""
        if isinstance(request, dict):
            return request.get(key, default)
        return getattr(request, key, default)

    def validate_batch(self, requests: list[Any]) -> bool:
        """
        Valida se batch é seguro.

        Returns:
            True se batch é válido
        """
        if not requests:
            return False

        # Check brand consistency
        brands = set(self._get_value(r, "brand_id") for r in requests)
        if len(brands) > 1:
            return False

        # Check risk level mixing
        risk_levels = set(self._get_value(r, "risk_level") for r in requests)
        high_risk = {"high", "critical"}
        if risk_levels & high_risk and len(risk_levels) > 1:
            # Don't mix high risk with others
            return False

        # Check total value
        total_value = sum(self._get_value(r, "business_value", 0) for r in requests)
        if total_value > self.max_total_value:
            return False

        return True

    # Alias para compatibilidade com testes
    validate_batch_compatibility = validate_batch

    def requires_approval(self, batch: Any) -> bool:
        """Verifica se batch requer aprovação humana."""
        if isinstance(batch, dict):
            risk_score = batch.get("risk_score", 0.5)
        else:
            risk_score = getattr(batch, "risk_score", 0.5)
        return risk_score > self.auto_approve_threshold


class BatchingEngine:
    """Motor de criação de lotes."""

    def __init__(
        self,
        max_batch_size: int = 10,
        batch_ttl_seconds: int = 3600,
    ):
        self.max_batch_size = max_batch_size
        self.batch_ttl_seconds = batch_ttl_seconds
        self._batches: dict[str, ApprovalBatch] = {}
        self._guard = BatchGuard()
        self._lock = threading.Lock()

    def _get_value(self, request: Any, key: str, default: Any = None) -> Any:
        """Obtém valor de dict ou objeto."""
        if isinstance(request, dict):
            return request.get(key, default)
        return getattr(request, key, default)

    def create_batch(
        self,
        requests: list[Any],
        brand_id: Optional[str] = None,
        enforce_single_brand: bool = True,
        limits: Optional[BatchSizeLimits] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Cria um lote compatível.

        Args:
            requests: Lista de requests
            brand_id: Brand ID para o batch
            enforce_single_brand: Se True, rejeita multi-brand
            limits: Limites do batch

        Returns:
            Dados do batch criado ou None
        """
        if not requests:
            return None

        # Apply limits
        if limits and len(requests) > limits.max_batch_size:
            requests = requests[: limits.max_batch_size]

        if enforce_single_brand:
            brands = set(self._get_value(r, "brand_id") for r in requests)
            if len(brands) > 1:
                return None

        # Limit batch size
        batch_requests = requests[: self.max_batch_size]

        # Calculate aggregate metrics
        brand_id_val = brand_id or self._get_value(
            batch_requests[0], "brand_id", "unknown"
        )
        total_value = sum(
            self._get_value(r, "business_value", 0) for r in batch_requests
        )
        avg_risk = sum(
            self._get_value(r, "refined_risk_score", 0.5) for r in batch_requests
        ) / len(batch_requests)

        # Create batch
        batch = ApprovalBatch(
            batch_id=uuid4().hex[:16],
            brand_id=brand_id_val,
            requests=batch_requests,
            total_value=total_value,
            risk_score=avg_risk,
        )

        # Set expiration
        expires = datetime.now(timezone.utc) + timedelta(seconds=self.batch_ttl_seconds)
        batch.expires_at = expires.isoformat()

        with self._lock:
            self._batches[batch.batch_id] = batch

        return {
            "batch_id": batch.batch_id,
            "brand_id": batch.brand_id,
            "requests": batch.requests,
            "created_at": batch.created_at,
            "expires_at": batch.expires_at,
            "total_value": batch.total_value,
            "risk_score": batch.risk_score,
        }

    def is_expired(self, batch_id: str) -> bool:
        """Verifica se batch expirou."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if not batch or not batch.expires_at:
                return False

            expires = datetime.fromisoformat(batch.expires_at)
            return datetime.now(timezone.utc) > expires

    def process_with_fallback(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Processa request com fallback para fila individual.

        Args:
            request: Request único

        Returns:
            Resultado do processamento
        """
        try:
            # Try to create single-item batch
            batch = self.create_batch([request])
            return {
                "mode": "batch",
                "batch_id": batch["batch_id"],
                "status": "created",
            }
        except ValueError:
            # Fallback to individual queue
            return {
                "mode": "individual",
                "request_id": request.get("request_id"),
                "status": "queued",
            }


class ApprovalOptimizer:
    """Otimizador principal de aprovações."""

    def __init__(self):
        self._risk_refiner = RiskTriageRefiner()
        self._priority_scorer = PriorityScorer()
        self._batching_engine = BatchingEngine()
        self._batch_guard = BatchGuard()

        self._queue: list[dict[str, Any]] = []
        self._queue_lock = threading.Lock()

    def _request_to_dict(self, request: Any) -> dict[str, Any]:
        """Converte request para dict."""
        if isinstance(request, dict):
            return request
        if hasattr(request, "__dataclass_fields__"):
            # It's a dataclass
            result = {}
            for field_name in request.__dataclass_fields__:
                result[field_name] = getattr(request, field_name)
            return result
        return dict(request)

    def add_request(self, request: Any) -> dict[str, Any]:
        """
        Adiciona request à fila otimizada.

        Args:
            request: Request de aprovação

        Returns:
            Request enriquecido
        """
        # Convert to dict if needed
        request_dict = self._request_to_dict(request)

        # Add timestamp if not present
        if "created_at" not in request_dict:
            request_dict["created_at"] = datetime.now(timezone.utc).isoformat()

        # Refine risk
        refined = self._risk_refiner.refine_risk(request_dict)

        # Calculate priority
        prioritized = self._priority_scorer.calculate_priority(refined)

        # Add to queue
        with self._queue_lock:
            self._queue.append(prioritized)

        return prioritized

    def get_queue(self) -> list[dict[str, Any]]:
        """Retorna fila ordenada por prioridade."""
        with self._queue_lock:
            return self._priority_scorer.order_queue(self._queue.copy())

    # Alias para compatibilidade com testes
    get_prioritized_queue = get_queue

    def create_batch_from_queue(
        self,
        brand_id: Optional[str] = None,
        max_size: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Cria batch a partir da fila.

        Args:
            brand_id: Filtrar por brand
            max_size: Tamanho máximo do batch

        Returns:
            Batch criado ou None
        """
        queue = self.get_queue()

        # Filter by brand if specified
        if brand_id:
            candidates = [r for r in queue if r.get("brand_id") == brand_id]
        else:
            candidates = queue

        if not candidates:
            return None

        # Limit size
        if max_size:
            candidates = candidates[:max_size]

        # Validate batch
        if not self._batch_guard.validate_batch(candidates):
            return None

        # Create batch
        return self._batching_engine.create_batch(candidates)

    def create_batch(
        self,
        brand_id: Optional[str] = None,
        max_size: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Cria batch a partir da fila (alias para create_batch_from_queue).

        Args:
            brand_id: Filtrar por brand
            max_size: Tamanho máximo do batch

        Returns:
            Batch criado ou None
        """
        return self.create_batch_from_queue(brand_id=brand_id, max_size=max_size)

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do optimizer."""
        with self._queue_lock:
            queue = self._queue.copy()

        if not queue:
            return {
                "queue_length": 0,
                "avg_priority": 0.0,
                "avg_risk": 0.0,
            }

        return {
            "queue_length": len(queue),
            "avg_priority": sum(r.get("priority_score", 0) for r in queue) / len(queue),
            "avg_risk": sum(r.get("refined_risk_score", 0.5) for r in queue)
            / len(queue),
            "by_priority": {
                "critical": len(
                    [r for r in queue if r.get("priority_level") == "critical"]
                ),
                "high": len([r for r in queue if r.get("priority_level") == "high"]),
                "medium": len(
                    [r for r in queue if r.get("priority_level") == "medium"]
                ),
                "low": len([r for r in queue if r.get("priority_level") == "low"]),
            },
        }
