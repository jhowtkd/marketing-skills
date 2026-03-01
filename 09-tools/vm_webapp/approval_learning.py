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
