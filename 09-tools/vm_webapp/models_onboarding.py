"""Onboarding telemetry models for SQLAlchemy."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import String, Text, DateTime, Integer, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class OnboardingBase(DeclarativeBase):
    pass


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class OnboardingEvent(OnboardingBase):
    """Onboarding event tracking."""
    __tablename__ = "onboarding_events"
    
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    brand_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    step: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    template_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_utc, nullable=False, index=True)
    
    @property
    def event_metadata(self) -> dict[str, Any]:
        return json.loads(self.metadata_json) if self.metadata_json else {}
    
    @event_metadata.setter
    def event_metadata(self, value: dict[str, Any]) -> None:
        self.metadata_json = json.dumps(value) if value else "{}"


class OnboardingFrictionPoint(OnboardingBase):
    """Friction points in onboarding flow."""
    __tablename__ = "onboarding_friction_points"
    
    point_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    step_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    dropoff_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dropoff_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now_utc, nullable=False)


class OnboardingState(OnboardingBase):
    """Onboarding state per user."""
    __tablename__ = "onboarding_states"
    
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    has_started: Mapped[bool] = mapped_column(default=False, nullable=False)
    has_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    template_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now_utc, nullable=False)
