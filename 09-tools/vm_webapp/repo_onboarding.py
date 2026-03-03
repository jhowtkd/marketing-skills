"""Repository functions for onboarding telemetry aggregation."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from vm_webapp.models_onboarding import OnboardingEvent, OnboardingFrictionPoint, OnboardingState


def get_onboarding_metrics(
    session: Session,
    brand_id: Optional[str] = None,
    days: int = 30
) -> dict[str, Any]:
    """Get aggregated onboarding metrics.
    
    Args:
        session: Database session
        brand_id: Optional brand filter
        days: Number of days to look back
        
    Returns:
        Dict with total_events, events_by_type, period_start, period_end
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = session.query(OnboardingEvent).filter(OnboardingEvent.created_at >= since)
    if brand_id:
        query = query.filter(OnboardingEvent.brand_id == brand_id)
    
    events = query.all()
    
    events_by_type: dict[str, int] = {}
    for e in events:
        events_by_type[e.event_type] = events_by_type.get(e.event_type, 0) + 1
    
    # Calculate additional metrics
    started = events_by_type.get("onboarding_started", 0)
    completed = events_by_type.get("onboarding_completed", 0)
    completion_rate = completed / started if started > 0 else 0.0
    
    return {
        "total_events": len(events),
        "events_by_type": events_by_type,
        "total_started": started,
        "total_completed": completed,
        "completion_rate": round(completion_rate, 2),
        "period_start": since.isoformat(),
        "period_end": datetime.now(timezone.utc).isoformat(),
    }


def get_funnel_metrics(
    session: Session,
    brand_id: Optional[str] = None,
    days: int = 30
) -> dict[str, Any]:
    """Get funnel metrics for onboarding steps.
    
    Args:
        session: Database session
        brand_id: Optional brand filter
        days: Number of days to look back
        
    Returns:
        Dict with step counts and conversion rates
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = session.query(OnboardingEvent).filter(OnboardingEvent.created_at >= since)
    if brand_id:
        query = query.filter(OnboardingEvent.brand_id == brand_id)
    
    # Group by step
    step_counts = (
        query.filter(OnboardingEvent.step.isnot(None))
        .with_entities(OnboardingEvent.step, func.count(OnboardingEvent.event_id))
        .group_by(OnboardingEvent.step)
        .all()
    )
    
    steps = {step: count for step, count in step_counts}
    
    return {
        "steps": steps,
        "period_days": days,
        "period_start": since.isoformat(),
        "period_end": datetime.now(timezone.utc).isoformat(),
    }


def get_friction_metrics(
    session: Session,
    brand_id: Optional[str] = None
) -> dict[str, Any]:
    """Get friction points with dropoff rates.
    
    Args:
        session: Database session
        brand_id: Optional brand filter
        
    Returns:
        Dict with friction_points and dropoff_rates
    """
    query = session.query(OnboardingFrictionPoint)
    if brand_id:
        query = query.filter(OnboardingFrictionPoint.brand_id == brand_id)
    
    points = query.all()
    
    friction_points = []
    dropoff_rates = {}
    
    for p in points:
        friction_points.append({
            "step_name": p.step_name,
            "dropoff_count": p.dropoff_count,
            "total_count": p.total_count,
            "dropoff_rate": round(p.dropoff_rate, 2),
        })
        if p.total_count > 0:
            dropoff_rates[p.step_name] = round(p.dropoff_count / p.total_count, 2)
    
    return {
        "friction_points": friction_points,
        "dropoff_rates": dropoff_rates,
    }


def get_user_onboarding_state(
    session: Session,
    user_id: str
) -> Optional[dict[str, Any]]:
    """Get onboarding state for a specific user.
    
    Args:
        session: Database session
        user_id: User identifier
        
    Returns:
        Dict with user state or None if not found
    """
    state = session.get(OnboardingState, user_id)
    if not state:
        return None
    
    return {
        "user_id": state.user_id,
        "current_step": state.current_step,
        "has_started": state.has_started,
        "has_completed": state.has_completed,
        "duration_ms": state.duration_ms,
        "template_id": state.template_id,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    }


def update_friction_point(
    session: Session,
    step_name: str,
    brand_id: Optional[str] = None,
    dropoff_increment: int = 0,
    total_increment: int = 0,
) -> OnboardingFrictionPoint:
    """Update or create a friction point record.
    
    Args:
        session: Database session
        step_name: Name of the step
        brand_id: Optional brand identifier
        dropoff_increment: Amount to increment dropoff count
        total_increment: Amount to increment total count
        
    Returns:
        Updated OnboardingFrictionPoint
    """
    # Find existing point
    query = session.query(OnboardingFrictionPoint).filter(
        OnboardingFrictionPoint.step_name == step_name
    )
    if brand_id:
        query = query.filter(OnboardingFrictionPoint.brand_id == brand_id)
    
    point = query.first()
    
    if point:
        point.dropoff_count += dropoff_increment
        point.total_count += total_increment
        if point.total_count > 0:
            point.dropoff_rate = point.dropoff_count / point.total_count
        point.updated_at = datetime.now(timezone.utc)
    else:
        from uuid import uuid4
        point = OnboardingFrictionPoint(
            point_id=str(uuid4()),
            brand_id=brand_id,
            step_name=step_name,
            dropoff_count=dropoff_increment,
            total_count=total_increment,
            dropoff_rate=total_increment / total_increment if total_increment > 0 else 0.0,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(point)
    
    return point


def get_time_to_first_value_stats(
    session: Session,
    brand_id: Optional[str] = None,
    days: int = 30
) -> dict[str, Any]:
    """Get statistics for time to first value.
    
    Args:
        session: Database session
        brand_id: Optional brand filter
        days: Number of days to look back
        
    Returns:
        Dict with avg, min, max TTFV
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = session.query(OnboardingEvent).filter(
        OnboardingEvent.event_type == "time_to_first_value",
        OnboardingEvent.created_at >= since,
        OnboardingEvent.duration_ms.isnot(None)
    )
    
    if brand_id:
        query = query.filter(OnboardingEvent.brand_id == brand_id)
    
    durations = [e.duration_ms for e in query.all() if e.duration_ms]
    
    if not durations:
        return {
            "count": 0,
            "avg_ms": 0,
            "min_ms": 0,
            "max_ms": 0,
        }
    
    return {
        "count": len(durations),
        "avg_ms": round(sum(durations) / len(durations), 2),
        "min_ms": min(durations),
        "max_ms": max(durations),
    }


def get_events_by_template(
    session: Session,
    brand_id: Optional[str] = None,
    days: int = 30
) -> dict[str, int]:
    """Get event counts grouped by template.
    
    Args:
        session: Database session
        brand_id: Optional brand filter
        days: Number of days to look back
        
    Returns:
        Dict mapping template_id to event count
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = session.query(OnboardingEvent).filter(
        OnboardingEvent.created_at >= since,
        OnboardingEvent.template_id.isnot(None)
    )
    
    if brand_id:
        query = query.filter(OnboardingEvent.brand_id == brand_id)
    
    results = (
        query.with_entities(OnboardingEvent.template_id, func.count(OnboardingEvent.event_id))
        .group_by(OnboardingEvent.template_id)
        .all()
    )
    
    return {template_id: count for template_id, count in results}
