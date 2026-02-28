"""Tests for first-run recommendation read model and ranking engine."""

import pytest

from vm_webapp.first_run_recommendation import (
    FirstRunOutcomeAggregate,
    ProfileModeOutcome,
    RecommendationRanker,
    RankedRecommendation,
)


class TestOutcomeAggregate:
    """Tests for FirstRunOutcomeAggregate."""

    def test_outcome_aggregate_initializes_with_zeroes(self) -> None:
        """Aggregate should initialize with zero counts."""
        aggregate = FirstRunOutcomeAggregate(
            profile="test_profile",
            mode="test_mode",
        )
        
        assert aggregate.profile == "test_profile"
        assert aggregate.mode == "test_mode"
        assert aggregate.total_runs == 0
        assert aggregate.success_24h_count == 0
        assert aggregate.approved_count == 0
        assert aggregate.avg_quality_score == 0.0
        assert aggregate.avg_duration_ms == 0.0

    def test_outcome_aggregate_updates_success_and_totals(self) -> None:
        """Aggregate should update correctly with successful outcome."""
        aggregate = FirstRunOutcomeAggregate(
            profile="test_profile",
            mode="test_mode",
        )
        
        # First successful run
        aggregate.update(
            approved=True,
            success_24h=True,
            quality_score=0.85,
            duration_ms=5000,
        )
        
        assert aggregate.total_runs == 1
        assert aggregate.success_24h_count == 1
        assert aggregate.approved_count == 1
        assert aggregate.avg_quality_score == 0.85
        assert aggregate.avg_duration_ms == 5000.0
        
        # Second run (not successful 24h)
        aggregate.update(
            approved=True,
            success_24h=False,
            quality_score=0.75,
            duration_ms=3000,
        )
        
        assert aggregate.total_runs == 2
        assert aggregate.success_24h_count == 1
        assert aggregate.approved_count == 2
        # Avg quality: (0.85 + 0.75) / 2 = 0.8
        assert aggregate.avg_quality_score == 0.8
        # Avg duration: (5000 + 3000) / 2 = 4000
        assert aggregate.avg_duration_ms == 4000.0

    def test_outcome_aggregate_calculates_success_rate(self) -> None:
        """Aggregate should calculate success rate correctly."""
        aggregate = FirstRunOutcomeAggregate(
            profile="test_profile",
            mode="test_mode",
        )
        
        # No runs yet
        assert aggregate.success_rate == 0.0
        
        # Add runs
        aggregate.update(approved=True, success_24h=True, quality_score=0.8, duration_ms=1000)
        aggregate.update(approved=True, success_24h=True, quality_score=0.8, duration_ms=1000)
        aggregate.update(approved=True, success_24h=False, quality_score=0.8, duration_ms=1000)
        
        # 2 out of 3 successful
        assert aggregate.success_rate == pytest.approx(2/3)


class TestProfileModeOutcome:
    """Tests for ProfileModeOutcome dataclass."""

    def test_profile_mode_outcome_creation(self) -> None:
        """Should create outcome with all fields."""
        outcome = ProfileModeOutcome(
            profile="engagement",
            mode="fast",
            total_runs=10,
            success_24h_count=7,
            success_rate=0.7,
            avg_quality_score=0.82,
            avg_duration_ms=4500.0,
        )
        
        assert outcome.profile == "engagement"
        assert outcome.mode == "fast"
        assert outcome.total_runs == 10
        assert outcome.success_24h_count == 7
        assert outcome.success_rate == 0.7


class TestRecommendationRanker:
    """Tests for RecommendationRanker."""

    def test_ranker_prefers_high_success_rate_with_quality_and_speed_weights(self) -> None:
        """Ranker should prefer options with higher success rate, quality, and speed."""
        ranker = RecommendationRanker()
        
        outcomes = [
            ProfileModeOutcome(
                profile="engagement",
                mode="fast",
                total_runs=100,
                success_24h_count=80,
                success_rate=0.8,
                avg_quality_score=0.85,
                avg_duration_ms=3000.0,
            ),
            ProfileModeOutcome(
                profile="awareness",
                mode="balanced",
                total_runs=50,
                success_24h_count=25,
                success_rate=0.5,
                avg_quality_score=0.75,
                avg_duration_ms=5000.0,
            ),
            ProfileModeOutcome(
                profile="conversion",
                mode="quality",
                total_runs=100,
                success_24h_count=90,
                success_rate=0.9,
                avg_quality_score=0.92,
                avg_duration_ms=4000.0,
            ),
        ]
        
        recommendations = ranker.rank(outcomes, top_n=3)
        
        # Highest success rate should be first
        assert recommendations[0].profile == "conversion"
        assert recommendations[0].mode == "quality"
        assert recommendations[0].confidence > 0.5

    def test_ranker_penalizes_low_sample_size(self) -> None:
        """Ranker should penalize options with low sample size."""
        ranker = RecommendationRanker()
        
        outcomes = [
            ProfileModeOutcome(
                profile="high_sample",
                mode="fast",
                total_runs=100,
                success_24h_count=70,
                success_rate=0.7,
                avg_quality_score=0.8,
                avg_duration_ms=3000.0,
            ),
            ProfileModeOutcome(
                profile="low_sample",
                mode="fast",
                total_runs=5,
                success_24h_count=5,
                success_rate=1.0,
                avg_quality_score=0.95,
                avg_duration_ms=2000.0,
            ),
        ]
        
        recommendations = ranker.rank(outcomes, top_n=2)
        
        # High sample with 70% success should rank higher than low sample with 100%
        assert recommendations[0].profile == "high_sample"
        assert recommendations[1].profile == "low_sample"
        # Low sample should have lower confidence
        assert recommendations[1].confidence < recommendations[0].confidence

    def test_ranker_returns_top_n_only(self) -> None:
        """Ranker should return only top N recommendations."""
        ranker = RecommendationRanker()
        
        outcomes = [
            ProfileModeOutcome(
                profile=f"profile_{i}",
                mode="fast",
                total_runs=10 + i * 10,
                success_24h_count=5 + i * 5,
                success_rate=0.5,
                avg_quality_score=0.8,
                avg_duration_ms=3000.0,
            )
            for i in range(10)
        ]
        
        recommendations = ranker.rank(outcomes, top_n=3)
        
        assert len(recommendations) == 3

    def test_ranker_includes_reason_codes(self) -> None:
        """Ranker should include reason codes for recommendations."""
        ranker = RecommendationRanker()
        
        outcomes = [
            ProfileModeOutcome(
                profile="engagement",
                mode="fast",
                total_runs=100,
                success_24h_count=80,
                success_rate=0.8,
                avg_quality_score=0.85,
                avg_duration_ms=3000.0,
            ),
        ]
        
        recommendations = ranker.rank(outcomes, top_n=1)
        
        assert len(recommendations) == 1
        assert len(recommendations[0].reason_codes) > 0
        assert "high_success_rate" in recommendations[0].reason_codes


class TestRankedRecommendation:
    """Tests for RankedRecommendation dataclass."""

    def test_ranked_recommendation_creation(self) -> None:
        """Should create ranked recommendation with all fields."""
        rec = RankedRecommendation(
            profile="engagement",
            mode="fast",
            score=0.85,
            confidence=0.75,
            reason_codes=["success_rate", "quality"],
        )
        
        assert rec.profile == "engagement"
        assert rec.mode == "fast"
        assert rec.score == 0.85
        assert rec.confidence == 0.75
        assert rec.reason_codes == ["success_rate", "quality"]
