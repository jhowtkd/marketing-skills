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


class RiskTriageRefiner:
    """Refinador de risco para requests de aprovação."""
    
    def __init__(self):
        self._risk_weights = {
            "impact": 0.4,
            "revenue_at_risk": 0.3,
            "node_type_risk": 0.2,
            "historical_failure_rate": 0.1,
        }
    
    def refine_risk(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Refina o risco de um request de aprovação.
        
        Args:
            request: Request com node_type, risk_level, params
            
        Returns:
            Request enriquecido com refined_risk_score e risk_factors
        """
        base_risk = self._base_risk_from_level(request.get("risk_level", "medium"))
        
        risk_factors = []
        score_adjustments = []
        
        params = request.get("params", {})
        
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
        node_type = request.get("node_type", "")
        high_risk_types = {"publish", "deploy", "delete"}
        if node_type in high_risk_types:
            score_adjustments.append(0.15)
            risk_factors.append(f"high_risk_node_type:{node_type}")
        
        # Calculate final score
        refined_score = base_risk + sum(score_adjustments)
        refined_score = max(0.0, min(1.0, refined_score))  # Clamp to [0, 1]
        
        return {
            **request,
            "refined_risk_score": round(refined_score, 4),
            "risk_factors": risk_factors,
            "base_risk_score": base_risk,
        }
    
    def _base_risk_from_level(self, level: str) -> float:
        """Converte nível de risco para score base."""
        return {
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 0.9,
        }.get(level, 0.5)


class PriorityScorer:
    """Calculador de score de prioridade."""
    
    def __init__(self):
        self._urgency_weights = {
            "critical": 1.0,
            "high": 0.7,
            "medium": 0.4,
            "low": 0.1,
        }
    
    def calculate_priority(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Calcula prioridade baseada em risco, urgência e impacto.
        
        Args:
            request: Request com refined_risk_score, urgency, etc.
            
        Returns:
            Request enriquecido com priority_score e priority_level
        """
        # Components
        risk_score = request.get("refined_risk_score", 0.5)
        urgency = request.get("urgency", "medium")
        urgency_weight = self._urgency_weights.get(urgency, 0.4)
        
        wait_time = request.get("wait_time_seconds", 0)
        wait_bonus = min(wait_time / 3600, 0.2)  # Max 0.2 bonus for waiting >1h
        
        business_impact = request.get("business_impact", 0)
        impact_score = min(business_impact / 50000, 0.3)  # Max 0.3 for high impact
        
        # Calculate priority score
        priority_score = (
            risk_score * 0.4 +
            urgency_weight * 0.3 +
            wait_bonus * 0.2 +
            impact_score * 0.1
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
        
        return {
            **request,
            "priority_score": priority_score,
            "priority_level": priority_level,
        }
    
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
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected, expanded
    total_value: float = 0.0
    risk_score: float = 0.0


class BatchGuard:
    """Guardas de segurança para batches."""
    
    def __init__(
        self,
        max_total_value: float = 100000.0,
        auto_approve_threshold: float = 0.3,
    ):
        self.max_total_value = max_total_value
        self.auto_approve_threshold = auto_approve_threshold
    
    def validate_batch(self, requests: list[dict[str, Any]]) -> bool:
        """
        Valida se batch é seguro.
        
        Returns:
            True se batch é válido
        """
        if not requests:
            return False
        
        # Check brand consistency
        brands = set(r.get("brand_id") for r in requests)
        if len(brands) > 1:
            return False
        
        # Check risk level mixing
        risk_levels = set(r.get("risk_level") for r in requests)
        high_risk = {"high", "critical"}
        if risk_levels & high_risk and len(risk_levels) > 1:
            # Don't mix high risk with others
            return False
        
        # Check total value
        total_value = sum(r.get("business_value", 0) for r in requests)
        if total_value > self.max_total_value:
            return False
        
        return True
    
    def requires_approval(self, batch: dict[str, Any]) -> bool:
        """Verifica se batch requer aprovação humana."""
        risk_score = batch.get("risk_score", 0.5)
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
    
    def create_batch(
        self,
        requests: list[dict[str, Any]],
        enforce_single_brand: bool = True,
    ) -> dict[str, Any]:
        """
        Cria um lote compatível.
        
        Args:
            requests: Lista de requests
            enforce_single_brand: Se True, rejeita multi-brand
            
        Returns:
            Dados do batch criado
        """
        if not requests:
            raise ValueError("Cannot create empty batch")
        
        if enforce_single_brand:
            brands = set(r.get("brand_id") for r in requests)
            if len(brands) > 1:
                raise ValueError("Batch cannot contain multiple brands")
        
        # Limit batch size
        batch_requests = requests[:self.max_batch_size]
        
        # Calculate aggregate metrics
        brand_id = batch_requests[0].get("brand_id", "unknown")
        total_value = sum(r.get("business_value", 0) for r in batch_requests)
        avg_risk = sum(r.get("refined_risk_score", 0.5) for r in batch_requests) / len(batch_requests)
        
        # Create batch
        batch = ApprovalBatch(
            batch_id=uuid4().hex[:16],
            brand_id=brand_id,
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
    
    def add_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Adiciona request à fila otimizada.
        
        Args:
            request: Request de aprovação
            
        Returns:
            Request enriquecido
        """
        # Add timestamp if not present
        if "created_at" not in request:
            request["created_at"] = datetime.now(timezone.utc).isoformat()
        
        # Refine risk
        refined = self._risk_refiner.refine_risk(request)
        
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
            "avg_risk": sum(r.get("refined_risk_score", 0.5) for r in queue) / len(queue),
            "by_priority": {
                "critical": len([r for r in queue if r.get("priority_level") == "critical"]),
                "high": len([r for r in queue if r.get("priority_level") == "high"]),
                "medium": len([r for r in queue if r.get("priority_level") == "medium"]),
                "low": len([r for r in queue if r.get("priority_level") == "low"]),
            },
        }
