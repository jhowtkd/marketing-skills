from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Brand(Base):
    __tablename__ = "brands"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class Project(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class Thread(Base):
    __tablename__ = "threads"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    last_activity_at: Mapped[str] = mapped_column(
        String(64), nullable=False, default=_now_iso
    )


class Run(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stack_path: Mapped[str] = mapped_column(String(512), nullable=False)
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class Stage(Base):
    __tablename__ = "stages"

    stage_pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    stage_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class EventLog(Base):
    __tablename__ = "event_log"

    event_pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stream_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    stream_version: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    brand_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    occurred_at: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CommandDedup(Base):
    __tablename__ = "command_dedup"

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    command_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class BrandView(Base):
    __tablename__ = "brands_view"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class ProjectView(Base):
    __tablename__ = "projects_view"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    channels_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    due_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class ThreadView(Base):
    __tablename__ = "threads_view"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    modes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    last_activity_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class TimelineItemView(Base):
    __tablename__ = "timeline_items_view"

    timeline_pk: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    occurred_at: Mapped[str] = mapped_column(String(64), nullable=False)


class CampaignView(Base):
    __tablename__ = "campaigns_view"

    campaign_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class TaskView(Base):
    __tablename__ = "tasks_view"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    campaign_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    brand_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class ApprovalView(Base):
    __tablename__ = "approvals_view"

    approval_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    required_role: Mapped[str] = mapped_column(String(64), nullable=False, default="editor")
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class ToolPermission(Base):
    __tablename__ = "tool_permissions"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    max_calls_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    current_day_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_call_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class ToolCredential(Base):
    __tablename__ = "tool_credentials"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    secret_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class ContextVersion(Base):
    __tablename__ = "context_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # brand, campaign, task
    scope_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class EditorialDecisionView(Base):
    __tablename__ = "editorial_decisions_view"

    decision_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    objective_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False, default="")
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class EditorialPolicy(Base):
    __tablename__ = "editorial_policies"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    editor_can_mark_objective: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    editor_can_mark_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class EditorialSLO(Base):
    """SLO (Service Level Objective) configuration for editorial governance per brand."""

    __tablename__ = "editorial_slos"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Maximum allowed baseline_source:none rate (0.0 - 1.0, default 0.5 = 50%)
    max_baseline_none_rate: Mapped[float] = mapped_column(nullable=False, default=0.5)
    # Maximum allowed policy denied rate (0.0 - 1.0, default 0.2 = 20%)
    max_policy_denied_rate: Mapped[float] = mapped_column(nullable=False, default=0.2)
    # Minimum required forecast confidence (0.0 - 1.0, default 0.4)
    min_confidence: Mapped[float] = mapped_column(nullable=False, default=0.4)
    # Enable auto-remediation for this brand
    auto_remediation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class FirstRunOutcomeView(Base):
    """First-run outcome tracking for recommendation engine (v12).
    
    Tracks success of runs within a 24-hour window to determine
    which profile/mode combinations are most effective.
    """

    __tablename__ = "first_run_outcomes_view"

    outcome_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    profile: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    success_24h: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    duration_ms: Mapped[float] = mapped_column(nullable=False, default=0.0)
    completed_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class FirstRunOutcomeAggregate(Base):
    """Aggregated first-run outcomes by brand/project/profile/mode (v12).
    
    Pre-computed aggregates for fast recommendation queries.
    """

    __tablename__ = "first_run_outcome_aggregates"

    aggregate_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    profile: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_24h_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score_sum: Mapped[float] = mapped_column(nullable=False, default=0.0)
    duration_ms_sum: Mapped[float] = mapped_column(nullable=False, default=0.0)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class CopilotSuggestionView(Base):
    """Read-model for editorial copilot suggestions (v13).
    
    Stores generated suggestions with metadata for retrieval and analytics.
    """

    __tablename__ = "copilot_suggestions_view"

    suggestion_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)  # initial, refine, strategy
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    reason_codes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    why: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_impact_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)


class CopilotFeedbackView(Base):
    """Read-model for editorial copilot feedback (v13).
    
    Stores editor feedback on suggestions for continuous improvement.
    """

    __tablename__ = "copilot_feedback_view"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    suggestion_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # accepted, edited, ignored
    edited_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(64), nullable=False, default=_now_iso)
