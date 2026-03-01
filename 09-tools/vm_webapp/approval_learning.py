"""
Approval Optimizer Learning Loop - v24

Aprendizado contínuo para o Approval Optimizer com:
- Coleta de sinais (observe)
- Geração de sugestões (learn)
- Aplicação com guardrails (apply)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4


@dataclass
class AdjustmentSuggestion:
    """Sugestão de ajuste do optimizer."""
    
    suggestion_id: str
    brand_id: str
    adjustment_type: str  # batch_size, risk_threshold, priority_weight
    current_value: float
    proposed_value: float
    confidence: float  # 0-1
    expected_savings_percent: float
    risk_score: float  # 0-1
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "pending"  # pending, applied, rejected, rolled_back


class LearningCore:
    """Core de aprendizado do approval optimizer."""
    
    def __init__(self):
        self._outcomes: list[dict[str, Any]] = []
        self._suggestions: dict[str, AdjustmentSuggestion] = {}
        self._lock = threading.Lock()
        
        # Configuration
        self._min_samples_for_suggestion = 5
        self._confidence_threshold = 0.6
    
    def record_outcome(self, outcome: dict[str, Any]) -> dict[str, Any]:
        """
        Registra o resultado de uma aprovação.
        
        Args:
            outcome: Dados do resultado (request_id, batch_id, approved, etc)
            
        Returns:
            Confirmação do registro
        """
        record = {
            "record_id": uuid4().hex[:16],
            "request_id": outcome.get("request_id"),
            "batch_id": outcome.get("batch_id"),
            "brand_id": outcome.get("brand_id", "default"),
            "approved": outcome.get("approved", False),
            "risk_level": outcome.get("risk_level", "medium"),
            "predicted_risk": outcome.get("predicted_risk", 0.5),
            "actual_time_minutes": outcome.get("actual_time_minutes", 0.0),
            "batch_size": outcome.get("batch_size", 1),
            "predicted_outcome": outcome.get("predicted_outcome", True),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with self._lock:
            self._outcomes.append(record)
        
        return {
            "recorded": True,
            "request_id": record["request_id"],
            "record_id": record["record_id"],
        }
    
    def calculate_delta(self, brand_id: str, days: int = 7) -> dict[str, Any]:
        """
        Calcula deltas de performance para uma brand.
        
        Args:
            brand_id: ID da brand
            days: Janela de análise em dias
            
        Returns:
            Deltas calculados
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self._lock:
            brand_outcomes = [
                o for o in self._outcomes
                if o["brand_id"] == brand_id and 
                datetime.fromisoformat(o["recorded_at"]) > cutoff
            ]
        
        if len(brand_outcomes) < 2:
            return {
                "time_delta_percent": 0.0,
                "precision_delta_percent": 0.0,
                "sample_size": len(brand_outcomes),
            }
        
        # Split in half for comparison
        mid = len(brand_outcomes) // 2
        first_half = brand_outcomes[:mid]
        second_half = brand_outcomes[mid:]
        
        # Calculate avg times
        first_time = sum(o["actual_time_minutes"] for o in first_half) / len(first_half)
        second_time = sum(o["actual_time_minutes"] for o in second_half) / len(second_half)
        
        time_delta = ((second_time - first_time) / first_time * 100) if first_time > 0 else 0.0
        
        # Calculate precision deltas
        def calc_precision(outcomes):
            if not outcomes:
                return 0.5
            correct = sum(
                1 for o in outcomes 
                if o["approved"] == o["predicted_outcome"]
            )
            return correct / len(outcomes)
        
        first_precision = calc_precision(first_half)
        second_precision = calc_precision(second_half)
        
        precision_delta = (second_precision - first_precision) * 100
        
        return {
            "time_delta_percent": round(time_delta, 2),
            "precision_delta_percent": round(precision_delta, 2),
            "sample_size": len(brand_outcomes),
        }
    
    def generate_suggestions(self, brand_id: str) -> list[dict[str, Any]]:
        """
        Gera sugestões de ajuste para uma brand.
        
        Args:
            brand_id: ID da brand
            
        Returns:
            Lista de sugestões
        """
        with self._lock:
            brand_outcomes = [
                o for o in self._outcomes 
                if o["brand_id"] == brand_id
            ]
        
        if len(brand_outcomes) < self._min_samples_for_suggestion:
            return []
        
        suggestions = []
        
        # Calculate current metrics
        avg_time = sum(o["actual_time_minutes"] for o in brand_outcomes) / len(brand_outcomes)
        
        # Check batch size optimization
        avg_batch_size = sum(o["batch_size"] for o in brand_outcomes) / len(brand_outcomes)
        
        # If avg time is high, suggest increasing batch size
        if avg_time > 5.0 and avg_batch_size < 10:
            confidence = min(0.9, len(brand_outcomes) / 20)
            expected_savings = -10.0  # 10% reduction in time
            
            suggestion = AdjustmentSuggestion(
                suggestion_id=uuid4().hex[:16],
                brand_id=brand_id,
                adjustment_type="batch_size",
                current_value=avg_batch_size,
                proposed_value=min(10, avg_batch_size + 1),
                confidence=confidence,
                expected_savings_percent=expected_savings,
                risk_score=0.3,  # Low risk
            )
            
            with self._lock:
                self._suggestions[suggestion.suggestion_id] = suggestion
            
            suggestions.append({
                "suggestion_id": suggestion.suggestion_id,
                "adjustment_type": suggestion.adjustment_type,
                "current_value": suggestion.current_value,
                "proposed_value": suggestion.proposed_value,
                "confidence": suggestion.confidence,
                "expected_savings_percent": suggestion.expected_savings_percent,
                "risk_score": suggestion.risk_score,
                "status": suggestion.status,
            })
        
        # Suggest risk threshold adjustment based on precision
        precision = self.get_batch_precision(brand_id, days=7)
        if precision < 0.7:
            confidence = min(0.85, len(brand_outcomes) / 20)
            
            suggestion = AdjustmentSuggestion(
                suggestion_id=uuid4().hex[:16],
                brand_id=brand_id,
                adjustment_type="risk_threshold",
                current_value=0.5,
                proposed_value=0.6,
                confidence=confidence,
                expected_savings_percent=5.0,
                risk_score=0.4,
            )
            
            with self._lock:
                self._suggestions[suggestion.suggestion_id] = suggestion
            
            suggestions.append({
                "suggestion_id": suggestion.suggestion_id,
                "adjustment_type": suggestion.adjustment_type,
                "current_value": suggestion.current_value,
                "proposed_value": suggestion.proposed_value,
                "confidence": suggestion.confidence,
                "expected_savings_percent": suggestion.expected_savings_percent,
                "risk_score": suggestion.risk_score,
                "status": suggestion.status,
            })
        
        return suggestions
    
    def get_batch_precision(self, brand_id: str, days: int = 7) -> float:
        """
        Calcula precisão dos batches para uma brand.
        
        Args:
            brand_id: ID da brand
            days: Janela de análise
            
        Returns:
            Precisão 0-1
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self._lock:
            brand_outcomes = [
                o for o in self._outcomes
                if o["brand_id"] == brand_id and 
                datetime.fromisoformat(o["recorded_at"]) > cutoff
            ]
        
        if not brand_outcomes:
            return 0.5
        
        correct = sum(
            1 for o in brand_outcomes 
            if o["approved"] == o["predicted_outcome"]
        )
        
        return correct / len(brand_outcomes)

    def apply_suggestion(
        self, 
        suggestion_id: str, 
        guardrails: LearningGuardrails,
        force: bool = False
    ) -> dict[str, Any]:
        """
        Aplica uma sugestão de ajuste.
        
        Args:
            suggestion_id: ID da sugestão
            guardrails: Guardrails de segurança
            force: Se True, aplica mesmo se for medium/high risk
            
        Returns:
            Resultado da aplicação
        """
        with self._lock:
            suggestion = self._suggestions.get(suggestion_id)
            if not suggestion:
                return {"applied": False, "error": "suggestion_not_found"}
            
            # Check if brand is frozen
            if hasattr(self, '_frozen_brands') and suggestion.brand_id in self._frozen_brands:
                return {"applied": False, "error": "brand_frozen"}
            
            # Apply guardrails - clamp adjustment
            clamped_value = guardrails.clamp_adjustment(
                suggestion.current_value,
                suggestion.proposed_value
            )
            
            # Determine application mode based on risk
            if suggestion.risk_score < guardrails.auto_apply_risk_threshold:
                mode = "auto"
            elif force:
                mode = "approval"
            else:
                # Medium/high risk - requires explicit approval
                return {
                    "applied": False,
                    "mode": "pending_approval",
                    "reason": "high_risk",
                    "risk_score": suggestion.risk_score,
                }
            
            # Apply the suggestion
            suggestion.status = "applied"
            suggestion.proposed_value = clamped_value
            
            # Track applied suggestion
            if not hasattr(self, '_applied_history'):
                self._applied_history = []
            
            self._applied_history.append({
                "suggestion_id": suggestion_id,
                "brand_id": suggestion.brand_id,
                "adjustment_type": suggestion.adjustment_type,
                "previous_value": suggestion.current_value,
                "applied_value": clamped_value,
                "mode": mode,
                "applied_at": datetime.now(timezone.utc).isoformat(),
            })
            
            return {
                "applied": True,
                "mode": mode,
                "suggestion_id": suggestion_id,
                "previous_value": suggestion.current_value,
                "applied_value": clamped_value,
            }
    
    def freeze_brand(self, brand_id: str, reason: str = "manual") -> dict[str, Any]:
        """
        Congela aprendizado para uma brand.
        
        Args:
            brand_id: ID da brand
            reason: Motivo do congelamento
            
        Returns:
            Confirmação do congelamento
        """
        if not hasattr(self, '_frozen_brands'):
            self._frozen_brands = {}
        
        self._frozen_brands[brand_id] = {
            "frozen_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        
        return {
            "frozen": True,
            "brand_id": brand_id,
            "reason": reason,
        }
    
    def unfreeze_brand(self, brand_id: str) -> dict[str, Any]:
        """
        Descongela aprendizado para uma brand.
        
        Args:
            brand_id: ID da brand
            
        Returns:
            Confirmação do descongelamento
        """
        if hasattr(self, '_frozen_brands') and brand_id in self._frozen_brands:
            del self._frozen_brands[brand_id]
        
        return {
            "unfrozen": True,
            "brand_id": brand_id,
        }
    
    def rollback_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        """
        Reverte uma sugestão aplicada.
        
        Args:
            suggestion_id: ID da sugestão
            
        Returns:
            Resultado do rollback
        """
        with self._lock:
            suggestion = self._suggestions.get(suggestion_id)
            if not suggestion:
                return {"rolled_back": False, "error": "suggestion_not_found"}
            
            if suggestion.status != "applied":
                return {"rolled_back": False, "error": "not_applied"}
            
            # Find the applied record
            if not hasattr(self, '_applied_history'):
                return {"rolled_back": False, "error": "no_history"}
            
            applied_record = None
            for record in self._applied_history:
                if record["suggestion_id"] == suggestion_id:
                    applied_record = record
                    break
            
            if not applied_record:
                return {"rolled_back": False, "error": "no_applied_record"}
            
            # Update suggestion status
            suggestion.status = "rolled_back"
            
            return {
                "rolled_back": True,
                "suggestion_id": suggestion_id,
                "previous_value": applied_record["previous_value"],
                "rolled_back_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def get_applied_history(self, brand_id: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Retorna histórico de sugestões aplicadas.
        
        Args:
            brand_id: Filtrar por brand (opcional)
            
        Returns:
            Lista de registros aplicados
        """
        if not hasattr(self, '_applied_history'):
            return []
        
        history = self._applied_history
        
        if brand_id:
            history = [h for h in history if h["brand_id"] == brand_id]
        
        return history


class LearningGuardrails:
    """Guardrails de segurança para o learning loop."""
    
    def __init__(
        self,
        max_adjustment_percent: float = 10.0,
        auto_apply_risk_threshold: float = 0.3,
    ):
        self.max_adjustment_percent = max_adjustment_percent
        self.auto_apply_risk_threshold = auto_apply_risk_threshold
    
    def clamp_adjustment(self, current_value: float, proposed_value: float) -> float:
        """
        Limita o ajuste a ±max_adjustment_percent.
        
        Args:
            current_value: Valor atual
            proposed_value: Valor proposto
            
        Returns:
            Valor limitado
        """
        if current_value == 0:
            return proposed_value
        
        percent_change = (proposed_value - current_value) / current_value * 100
        
        if percent_change > self.max_adjustment_percent:
            # Limit increase
            return current_value * (1 + self.max_adjustment_percent / 100)
        elif percent_change < -self.max_adjustment_percent:
            # Limit decrease
            return current_value * (1 - self.max_adjustment_percent / 100)
        
        return proposed_value
