"""Tests for v34 Onboarding Recovery Strategy Engine.

Strategy selection and smart resume path generation.
"""

import pytest
from datetime import datetime, timezone, timedelta

from vm_webapp.onboarding_recovery import (
    DropoffReason,
    RecoveryCaseStatus,
    RecoveryPriority,
    RecoveryCase,
)
from vm_webapp.onboarding_recovery_strategy import (
    ReactivationStrategy,
    StrategyType,
    StrategySelection,
    ResumePath,
    SmartResumePath,
    ReactivationStrategyEngine,
)


class TestReactivationStrategy:
    """Test ReactivationStrategy enum."""

    def test_strategy_values(self):
        """Strategy should have expected values."""
        assert ReactivationStrategy.REMINDER == "reminder"
        assert ReactivationStrategy.FAST_LANE == "fast_lane"
        assert ReactivationStrategy.TEMPLATE_BOOST == "template_boost"
        assert ReactivationStrategy.GUIDED_RESUME == "guided_resume"


class TestStrategyType:
    """Test StrategyType classification."""

    def test_strategy_type_values(self):
        """StrategyType should have expected values."""
        assert StrategyType.LOW_TOUCH == "low_touch"
        assert StrategyType.MEDIUM_TOUCH == "medium_touch"
        assert StrategyType.HIGH_TOUCH == "high_touch"


class TestStrategySelection:
    """Test StrategySelection model."""

    def test_selection_creation(self):
        """Create a strategy selection."""
        selection = StrategySelection(
            strategy=ReactivationStrategy.FAST_LANE,
            strategy_type=StrategyType.MEDIUM_TOUCH,
            reason="Late-stage dropoff with high intent",
            expected_impact=0.35,
        )
        
        assert selection.strategy == ReactivationStrategy.FAST_LANE
        assert selection.strategy_type == StrategyType.MEDIUM_TOUCH
        assert selection.expected_impact == 0.35

    def test_selection_to_dict(self):
        """Convert selection to dict."""
        selection = StrategySelection(
            strategy=ReactivationStrategy.REMINDER,
            strategy_type=StrategyType.LOW_TOUCH,
            reason="Early-stage timeout",
            expected_impact=0.15,
        )
        
        data = selection.to_dict()
        
        assert data["strategy"] == "reminder"
        assert data["strategy_type"] == "low_touch"
        assert data["expected_impact"] == 0.15


class TestResumePath:
    """Test ResumePath model."""

    def test_path_creation(self):
        """Create a resume path."""
        path = ResumePath(
            case_id="case-001",
            entry_point="step_3",
            prefill_data={"company_name": "Acme Inc"},
            skip_steps=["welcome_video"],
            highlight_changes=["new_templates"],
            estimated_completion_minutes=5,
        )
        
        assert path.case_id == "case-001"
        assert path.entry_point == "step_3"
        assert path.estimated_completion_minutes == 5

    def test_path_to_dict(self):
        """Convert path to dict."""
        path = ResumePath(
            case_id="case-001",
            entry_point="step_5",
            prefill_data={"industry": "tech"},
            skip_steps=["onboarding_intro"],
            highlight_changes=["simplified_flow"],
            estimated_completion_minutes=3,
        )
        
        data = path.to_dict()
        
        assert data["entry_point"] == "step_5"
        assert data["skip_steps"] == ["onboarding_intro"]
        assert "friction_score" in data


class TestSmartResumePath:
    """Test SmartResumePath generator."""

    def test_generator_initialization(self):
        """Initialize resume path generator."""
        generator = SmartResumePath()
        assert generator is not None

    def test_generate_for_late_stage(self):
        """Generate path for late-stage dropoff."""
        generator = SmartResumePath()
        
        case = RecoveryCase(
            case_id="case-late",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=6,
            total_steps=7,
            metadata={"company_name": "Acme Inc", "industry": "tech"},
        )
        
        path = generator.generate(case)
        
        assert path.case_id == "case-late"
        assert path.entry_point == "step_6"  # Resume from dropoff step
        assert len(path.skip_steps) > 0  # Should skip some completed steps

    def test_generate_for_early_stage(self):
        """Generate path for early-stage dropoff."""
        generator = SmartResumePath()
        
        case = RecoveryCase(
            case_id="case-early",
            user_id="user-2",
            brand_id="brand-a",
            reason=DropoffReason.TIMEOUT,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.LOW,
            current_step=2,
            total_steps=7,
            metadata={},
        )
        
        path = generator.generate(case)
        
        assert path.case_id == "case-early"
        # Early stage may restart or go to simplified entry
        assert path.entry_point is not None

    def test_prefill_from_metadata(self):
        """Prefill form data from case metadata."""
        generator = SmartResumePath()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.MEDIUM,
            current_step=4,
            total_steps=7,
            metadata={
                "company_name": "Acme Inc",
                "industry": "technology",
                "team_size": "10-50",
            },
        )
        
        path = generator.generate(case)
        
        assert "company_name" in path.prefill_data
        assert path.prefill_data["company_name"] == "Acme Inc"

    def test_friction_score_calculation(self):
        """Calculate friction score for path."""
        generator = SmartResumePath()
        
        # Low friction: late stage, skips available
        case = RecoveryCase(
            case_id="case-low",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=6,
            total_steps=7,
            metadata={},
        )
        
        path = generator.generate(case)
        
        # Late stage should have low friction (high progress = low remaining steps)
        assert path.friction_score < 0.5


class TestReactivationStrategyEngine:
    """Test ReactivationStrategyEngine."""

    def test_engine_initialization(self):
        """Initialize strategy engine."""
        engine = ReactivationStrategyEngine()
        assert engine._resume_generator is not None

    def test_select_strategy_for_high_priority_late_stage(self):
        """Select appropriate strategy for high-priority late-stage case."""
        engine = ReactivationStrategyEngine()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=6,
            total_steps=7,
            metadata={},
        )
        
        selection = engine.select_strategy(case)
        
        assert selection.strategy in [ReactivationStrategy.FAST_LANE, ReactivationStrategy.GUIDED_RESUME]
        assert selection.strategy_type in [StrategyType.MEDIUM_TOUCH, StrategyType.HIGH_TOUCH]

    def test_select_strategy_for_error_dropoff(self):
        """Select strategy for error-induced dropoff."""
        engine = ReactivationStrategyEngine()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ERROR,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=3,
            total_steps=7,
            metadata={"error_code": "TEMPLATE_RENDER_FAILED"},
        )
        
        selection = engine.select_strategy(case)
        
        # Error cases should get guided resume to rebuild confidence
        assert selection.strategy == ReactivationStrategy.GUIDED_RESUME

    def test_select_strategy_for_timeout(self):
        """Select strategy for timeout dropoff."""
        engine = ReactivationStrategyEngine()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.TIMEOUT,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.LOW,
            current_step=2,
            total_steps=7,
            metadata={},
        )
        
        selection = engine.select_strategy(case)
        
        # Timeout cases get reminder or fast-lane
        assert selection.strategy in [ReactivationStrategy.REMINDER, ReactivationStrategy.FAST_LANE]

    def test_select_strategy_for_low_priority(self):
        """Select low-touch strategy for low-priority cases."""
        engine = ReactivationStrategyEngine()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.USER_INITIATED_EXIT,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.LOW,
            current_step=1,
            total_steps=7,
            metadata={},
        )
        
        selection = engine.select_strategy(case)
        
        assert selection.strategy_type == StrategyType.LOW_TOUCH
        assert selection.strategy == ReactivationStrategy.REMINDER

    def test_generate_proposal(self):
        """Generate complete recovery proposal."""
        engine = ReactivationStrategyEngine()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=5,
            total_steps=7,
            metadata={"company_name": "Acme"},
        )
        
        proposal = engine.generate_proposal(case)
        
        assert proposal["case_id"] == "case-001"
        assert "strategy" in proposal
        assert "strategy_type" in proposal["strategy"]  # Nested under strategy
        assert "resume_path" in proposal
        assert "requires_approval" in proposal

    def test_high_touch_requires_approval(self):
        """High-touch strategies require human approval."""
        engine = ReactivationStrategyEngine()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ERROR,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.HIGH,
            current_step=4,
            total_steps=7,
            metadata={},
        )
        
        proposal = engine.generate_proposal(case)
        
        assert proposal["requires_approval"] is True

    def test_low_touch_auto_apply(self):
        """Low-touch strategies can be auto-applied."""
        engine = ReactivationStrategyEngine()
        
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.TIMEOUT,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.LOW,
            current_step=2,
            total_steps=7,
            metadata={},
        )
        
        proposal = engine.generate_proposal(case)
        
        assert proposal["requires_approval"] is False

    def test_batch_generate_proposals(self):
        """Generate proposals for multiple cases."""
        engine = ReactivationStrategyEngine()
        
        cases = [
            RecoveryCase(
                case_id="case-1",
                user_id="user-1",
                brand_id="brand-a",
                reason=DropoffReason.TIMEOUT,
                status=RecoveryCaseStatus.RECOVERABLE,
                priority=RecoveryPriority.LOW,
                current_step=2,
                total_steps=7,
                metadata={},
            ),
            RecoveryCase(
                case_id="case-2",
                user_id="user-2",
                brand_id="brand-a",
                reason=DropoffReason.ABANDONED_STEP,
                status=RecoveryCaseStatus.RECOVERABLE,
                priority=RecoveryPriority.HIGH,
                current_step=6,
                total_steps=7,
                metadata={},
            ),
        ]
        
        proposals = engine.batch_generate_proposals(cases)
        
        assert len(proposals) == 2
        assert proposals[0]["case_id"] == "case-1"
        assert proposals[1]["case_id"] == "case-2"

    def test_get_strategy_metrics(self):
        """Get strategy generation metrics."""
        engine = ReactivationStrategyEngine()
        
        # Generate some proposals first
        case = RecoveryCase(
            case_id="case-001",
            user_id="user-1",
            brand_id="brand-a",
            reason=DropoffReason.ABANDONED_STEP,
            status=RecoveryCaseStatus.RECOVERABLE,
            priority=RecoveryPriority.MEDIUM,
            current_step=4,
            total_steps=7,
            metadata={},
        )
        engine.generate_proposal(case)
        
        metrics = engine.get_strategy_metrics()
        
        assert metrics["proposals_generated"] >= 1
        assert "auto_apply_count" in metrics
        assert "needs_approval_count" in metrics
