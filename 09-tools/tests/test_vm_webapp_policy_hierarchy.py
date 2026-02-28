"""Tests for hierarchical policy resolver (v18).

Policy resolution precedence: segment > brand > global
"""

import json
import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vm_webapp.models import Base, Policy, PolicyLevel
from vm_webapp.policy_hierarchy import (
    resolve_effective_policy,
    EffectivePolicy,
    PolicySource,
)
from vm_webapp import repo


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestResolveEffectivePolicy:
    """Test policy resolution with precedence segment > brand > global."""

    def test_global_policy_only(self, db_session):
        """When only global policy exists, return global values."""
        # Arrange
        policy = Policy(
            policy_id="policy-global",
            level=PolicyLevel.GLOBAL,
            brand_id=None,
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.5, "mode": "standard"}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add(policy)
        db_session.commit()

        # Act
        result = resolve_effective_policy(db_session, brand_id="brand1")

        # Assert
        assert isinstance(result, EffectivePolicy)
        assert result.threshold == 0.5
        assert result.mode == "standard"
        assert result.source == PolicySource.GLOBAL
        assert result.source_brand_id is None
        assert result.source_segment is None

    def test_brand_overrides_global(self, db_session):
        """Brand policy should override global policy."""
        # Arrange
        global_policy = Policy(
            policy_id="policy-global",
            level=PolicyLevel.GLOBAL,
            brand_id=None,
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.5, "mode": "standard"}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        brand_policy = Policy(
            policy_id="policy-brand1",
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.7, "mode": "strict"}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add_all([global_policy, brand_policy])
        db_session.commit()

        # Act
        result = resolve_effective_policy(db_session, brand_id="brand1")

        # Assert
        assert result.threshold == 0.7
        assert result.mode == "strict"
        assert result.source == PolicySource.BRAND
        assert result.source_brand_id == "brand1"

    def test_segment_overrides_brand(self, db_session):
        """Segment policy should override brand policy."""
        # Arrange
        brand_policy = Policy(
            policy_id="policy-brand1",
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.7, "mode": "strict"}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        segment_policy = Policy(
            policy_id="policy-segment",
            level=PolicyLevel.SEGMENT,
            brand_id="brand1",
            segment="enterprise",
            objective_key=None,
            params_json=json.dumps({"threshold": 0.9, "mode": "enterprise"}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add_all([brand_policy, segment_policy])
        db_session.commit()

        # Act
        result = resolve_effective_policy(
            db_session, brand_id="brand1", segment="enterprise"
        )

        # Assert
        assert result.threshold == 0.9
        assert result.mode == "enterprise"
        assert result.source == PolicySource.SEGMENT
        assert result.source_brand_id == "brand1"
        assert result.source_segment == "enterprise"

    def test_fallback_when_segment_missing(self, db_session):
        """When segment policy doesn't exist, fall back to brand."""
        # Arrange
        brand_policy = Policy(
            policy_id="policy-brand1",
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.7}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add(brand_policy)
        db_session.commit()

        # Act - request segment that doesn't exist
        result = resolve_effective_policy(
            db_session, brand_id="brand1", segment="nonexistent"
        )

        # Assert - should fallback to brand
        assert result.threshold == 0.7
        assert result.source == PolicySource.BRAND

    def test_fallback_when_brand_missing(self, db_session):
        """When brand policy doesn't exist, fall back to global."""
        # Arrange
        global_policy = Policy(
            policy_id="policy-global",
            level=PolicyLevel.GLOBAL,
            brand_id=None,
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.5}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add(global_policy)
        db_session.commit()

        # Act - request brand that doesn't exist
        result = resolve_effective_policy(db_session, brand_id="unknown-brand")

        # Assert - should fallback to global
        assert result.threshold == 0.5
        assert result.source == PolicySource.GLOBAL

    def test_partial_override_at_brand_level(self, db_session):
        """Brand can override only some parameters."""
        # Arrange
        global_policy = Policy(
            policy_id="policy-global",
            level=PolicyLevel.GLOBAL,
            brand_id=None,
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.5, "mode": "standard", "timeout": 30}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        brand_policy = Policy(
            policy_id="policy-brand1",
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            segment=None,
            objective_key=None,
            # Only overrides threshold
            params_json=json.dumps({"threshold": 0.8}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add_all([global_policy, brand_policy])
        db_session.commit()

        # Act
        result = resolve_effective_policy(db_session, brand_id="brand1")

        # Assert - merged policy with brand taking precedence
        assert result.threshold == 0.8  # from brand
        assert result.mode == "standard"  # from global
        assert result.timeout == 30  # from global

    def test_objective_key_specific_policy(self, db_session):
        """Policy can be specific to an objective_key."""
        # Arrange
        brand_policy = Policy(
            policy_id="policy-brand1",
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.5}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        objective_policy = Policy(
            policy_id="policy-brand1-obj",
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            segment=None,
            objective_key="conversion",
            params_json=json.dumps({"threshold": 0.9}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add_all([brand_policy, objective_policy])
        db_session.commit()

        # Act
        result = resolve_effective_policy(
            db_session, brand_id="brand1", objective_key="conversion"
        )

        # Assert
        assert result.threshold == 0.9

    def test_deterministic_snapshot(self, db_session):
        """Effective policy should have a deterministic snapshot representation."""
        # Arrange
        policy = Policy(
            policy_id="policy-global",
            level=PolicyLevel.GLOBAL,
            brand_id=None,
            segment=None,
            objective_key=None,
            params_json=json.dumps({"threshold": 0.5, "mode": "standard"}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add(policy)
        db_session.commit()

        # Act
        result = resolve_effective_policy(db_session, brand_id="brand1")

        # Assert
        snapshot = result.to_snapshot()
        assert isinstance(snapshot, dict)
        assert "threshold" in snapshot
        assert "mode" in snapshot
        assert "_source" in snapshot
        assert snapshot["_source"] == "global"

    def test_empty_params_returns_default_policy(self, db_session):
        """When no policies exist, return default policy."""
        # Act
        result = resolve_effective_policy(db_session, brand_id="brand1")

        # Assert
        assert isinstance(result, EffectivePolicy)
        assert result.source == PolicySource.DEFAULT


class TestPolicyRepository:
    """Test policy repository functions."""

    def test_upsert_policy_creates_new(self, db_session):
        """upsert_policy should create new policy if not exists."""
        # Act
        from vm_webapp.policy_hierarchy import upsert_policy

        policy = upsert_policy(
            db_session,
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            params={"threshold": 0.5},
        )

        # Assert
        assert policy.policy_id is not None
        assert policy.level == PolicyLevel.BRAND
        assert policy.brand_id == "brand1"

    def test_upsert_policy_updates_existing(self, db_session):
        """upsert_policy should update existing policy."""
        # Arrange
        from vm_webapp.policy_hierarchy import upsert_policy

        policy1 = upsert_policy(
            db_session,
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            params={"threshold": 0.5},
        )
        original_id = policy1.policy_id

        # Act
        policy2 = upsert_policy(
            db_session,
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            params={"threshold": 0.8},
        )

        # Assert
        assert policy2.policy_id == original_id
        params = json.loads(policy2.params_json)
        assert params["threshold"] == 0.8

    def test_get_policy_by_level(self, db_session):
        """get_policy should retrieve policy by level."""
        # Arrange
        from vm_webapp.policy_hierarchy import upsert_policy, get_policy

        upsert_policy(
            db_session,
            level=PolicyLevel.BRAND,
            brand_id="brand1",
            params={"threshold": 0.5},
        )

        # Act
        result = get_policy(db_session, level=PolicyLevel.BRAND, brand_id="brand1")

        # Assert
        assert result is not None
        assert result.brand_id == "brand1"
