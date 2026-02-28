"""Editorial Copilot - Deterministic suggestion engine for VM Studio.

Provides suggestions across three phases:
- initial: Profile/mode recommendations based on v12 ranking
- refine: Text refinements based on scorecard gaps
- strategy: Strategic recommendations based on risk signals

Each suggestion includes confidence, explainability (reason_codes, why),
and expected impact for informed editor decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Self

SuggestionPhase = Literal["initial", "refine", "strategy"]
FeedbackAction = Literal["accepted", "edited", "ignored"]


@dataclass
class CopilotSuggestion:
    """A copilot suggestion with explainability and impact forecasting.
    
    Designed for the three-phase workflow: initial, refine, strategy.
    """
    
    suggestion_id: str
    thread_id: str
    phase: SuggestionPhase
    content: str
    confidence: float
    reason_codes: list[str] = field(default_factory=list)
    why: str = ""
    expected_impact: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CopilotFeedback:
    """Editor feedback on a suggestion for continuous improvement.
    
    Tracks acceptance, edits, and ignores to improve future suggestions.
    """
    
    feedback_id: str
    suggestion_id: str
    thread_id: str
    phase: SuggestionPhase
    action: FeedbackAction
    edited_content: str | None = None
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _generate_suggestion_id() -> str:
    """Generate a unique suggestion ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    import uuid
    return f"sugg-{timestamp}-{uuid.uuid4().hex[:8]}"


def _generate_feedback_id() -> str:
    """Generate a unique feedback ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    import uuid
    return f"feedback-{timestamp}-{uuid.uuid4().hex[:8]}"


class SuggestionEngine:
    """Deterministic engine for generating editorial suggestions by phase.
    
    Implements guardrails: low confidence returns passive suggestions.
    """
    
    # Confidence threshold for active suggestions
    CONFIDENCE_THRESHOLD: float = 0.4
    
    def __init__(self) -> None:
        self._ranker = None  # Will be initialized when first_run_recommendation is imported
    
    def generate_initial(
        self,
        context: dict,
        outcomes: list[dict] | None = None,
    ) -> CopilotSuggestion:
        """Generate initial phase suggestion using v12 ranking.
        
        Returns profile/mode recommendation with confidence and reasoning.
        """
        from vm_webapp.first_run_recommendation import RecommendationRanker, ProfileModeOutcome
        
        # Default content for empty outcomes
        if not outcomes:
            return CopilotSuggestion(
                suggestion_id=_generate_suggestion_id(),
                thread_id=context.get("thread_id", ""),
                phase="initial",
                content="",
                confidence=0.3,
                reason_codes=["fallback_default", "low_sample_size"],
                why="Sem dados históricos suficientes. Considere usar profile 'engagement' e mode 'balanced' como ponto de partida.",
                expected_impact={"quality_delta": 0, "approval_lift": 0},
            )
        
        # Convert outcomes to ProfileModeOutcome objects
        pm_outcomes = [
            ProfileModeOutcome(
                profile=o["profile"],
                mode=o["mode"],
                total_runs=o.get("total_runs", 0),
                success_24h_count=o.get("success_24h_count", 0),
                success_rate=o.get("success_rate", 0.0),
                avg_quality_score=o.get("avg_quality_score", 0.0),
                avg_duration_ms=o.get("avg_duration_ms", 0.0),
            )
            for o in outcomes
        ]
        
        # Rank using v12 engine
        ranker = RecommendationRanker()
        ranked = ranker.rank(pm_outcomes, top_n=1)
        
        if not ranked:
            return CopilotSuggestion(
                suggestion_id=_generate_suggestion_id(),
                thread_id=context.get("thread_id", ""),
                phase="initial",
                content="",
                confidence=0.3,
                reason_codes=["fallback_default"],
                why="Não foi possível gerar recomendação. Use profile 'engagement' e mode 'balanced'.",
                expected_impact={"quality_delta": 0, "approval_lift": 0},
            )
        
        top = ranked[0]
        
        # Build suggestion content
        content = f"Profile: {top.profile}, Mode: {top.mode}"
        
        # Calculate expected impact
        quality_delta = int(top.score * 10)  # 0-10 points
        approval_lift = int(top.confidence * 8)  # percentage points
        
        return CopilotSuggestion(
            suggestion_id=_generate_suggestion_id(),
            thread_id=context.get("thread_id", ""),
            phase="initial",
            content=content,
            confidence=top.confidence,
            reason_codes=top.reason_codes,
            why=f"Baseado em {sum(o.total_runs for o in pm_outcomes)} execuções. Taxa de sucesso 24h: {top.score:.0%}.",
            expected_impact={
                "quality_delta": quality_delta,
                "approval_lift": approval_lift,
            },
        )
    
    def generate_refine(
        self,
        context: dict,
        scorecard_gaps: list[dict] | None = None,
    ) -> CopilotSuggestion:
        """Generate refine phase suggestion based on scorecard gaps.
        
        Returns text refinement suggestions for identified gaps.
        """
        thread_id = context.get("thread_id", "")
        
        if not scorecard_gaps:
            return CopilotSuggestion(
                suggestion_id=_generate_suggestion_id(),
                thread_id=thread_id,
                phase="refine",
                content="",
                confidence=0.3,
                reason_codes=["no_gaps_identified"],
                why="Nenhuma lacuna identificada no scorecard. O conteúdo atende aos critérios atuais.",
                expected_impact={"quality_delta": 0, "approval_lift": 0},
            )
        
        # Build refinement suggestion from gaps
        gap_descriptions = []
        for gap in scorecard_gaps[:3]:  # Top 3 gaps
            dim = gap.get("dimension", "geral")
            score = gap.get("score", 0)
            suggestion = gap.get("suggestion", f"Melhorar {dim}")
            gap_descriptions.append(f"- {suggestion} (dimensão: {dim}, score: {score})")
        
        content = "\n".join(gap_descriptions)
        confidence = min(0.9, 0.5 + (0.1 * len(scorecard_gaps)))
        
        return CopilotSuggestion(
            suggestion_id=_generate_suggestion_id(),
            thread_id=thread_id,
            phase="refine",
            content=content,
            confidence=confidence,
            reason_codes=["scorecard_gaps"],
            why=f"Identificadas {len(scorecard_gaps)} lacunas no scorecard de qualidade.",
            expected_impact={
                "quality_delta": 5 * len(scorecard_gaps),
                "approval_lift": 3 * len(scorecard_gaps),
            },
        )
    
    def generate_strategy(
        self,
        context: dict,
        risk_signals: list[dict] | None = None,
    ) -> CopilotSuggestion:
        """Generate strategy phase suggestion based on high-risk signals.
        
        Returns strategic recommendations when risk is detected.
        """
        thread_id = context.get("thread_id", "")
        
        if not risk_signals:
            return CopilotSuggestion(
                suggestion_id=_generate_suggestion_id(),
                thread_id=thread_id,
                phase="strategy",
                content="",
                confidence=0.3,
                reason_codes=["no_risk_signals"],
                why="Nenhum sinal de risco identificado. Estratégia atual é adequada.",
                expected_impact={"quality_delta": 0, "approval_lift": 0},
            )
        
        # Build strategy suggestion from risk signals
        signal_descriptions = []
        max_risk = 0
        for signal in risk_signals[:3]:
            risk_type = signal.get("type", "unknown")
            severity = signal.get("severity", "low")
            risk_score = signal.get("risk_score", 0)
            max_risk = max(max_risk, risk_score)
            recommendation = signal.get("recommendation", f"Mitigar risco de {risk_type}")
            signal_descriptions.append(f"- [{severity.upper()}] {recommendation}")
        
        content = "\n".join(signal_descriptions)
        confidence = min(0.95, 0.4 + (max_risk / 100))
        
        return CopilotSuggestion(
            suggestion_id=_generate_suggestion_id(),
            thread_id=thread_id,
            phase="strategy",
            content=content,
            confidence=confidence,
            reason_codes=["high_risk_detected"] if max_risk > 70 else ["risk_detected"],
            why=f"Detectados {len(risk_signals)} sinais de risco (máx: {max_risk}/100).",
            expected_impact={
                "quality_delta": 8 if max_risk > 70 else 5,
                "approval_lift": 5 if max_risk > 70 else 3,
            },
        )


def generate_suggestions(
    phase: SuggestionPhase,
    context: dict,
    **kwargs,
) -> CopilotSuggestion:
    """Generate a suggestion for the specified phase.
    
    Args:
        phase: One of 'initial', 'refine', 'strategy'
        context: Dictionary with thread_id, brand_id, project_id, user_request
        **kwargs: Phase-specific data (outcomes, scorecard_gaps, risk_signals)
    
    Returns:
        CopilotSuggestion with confidence, reason_codes, why, and expected_impact
    """
    engine = SuggestionEngine()
    
    if phase == "initial":
        return engine.generate_initial(context, kwargs.get("outcomes"))
    elif phase == "refine":
        return engine.generate_refine(context, kwargs.get("scorecard_gaps"))
    elif phase == "strategy":
        return engine.generate_strategy(context, kwargs.get("risk_signals"))
    else:
        raise ValueError(f"Unknown phase: {phase}")


def build_initial_suggestion(context: dict) -> CopilotSuggestion:
    """Convenience function to build an initial phase suggestion.
    
    Uses default/outcome data if available, otherwise returns passive suggestion.
    """
    return generate_suggestions("initial", context)


# Feedback tracking for continuous improvement

def record_feedback(
    suggestion_id: str,
    thread_id: str,
    phase: SuggestionPhase,
    action: FeedbackAction,
    edited_content: str | None = None,
    metadata: dict | None = None,
) -> CopilotFeedback:
    """Record editor feedback on a suggestion.
    
    Args:
        suggestion_id: ID of the suggestion being rated
        thread_id: Thread context
        phase: Phase of the suggestion
        action: One of 'accepted', 'edited', 'ignored'
        edited_content: Modified content if action is 'edited'
        metadata: Additional context (user_id, timestamp, etc.)
    
    Returns:
        CopilotFeedback record
    """
    return CopilotFeedback(
        feedback_id=_generate_feedback_id(),
        suggestion_id=suggestion_id,
        thread_id=thread_id,
        phase=phase,
        action=action,
        edited_content=edited_content,
        metadata=metadata or {},
    )
