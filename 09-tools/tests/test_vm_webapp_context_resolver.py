import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vm_webapp.models import Base
from vm_webapp.context_versions import append_context_version
from vm_webapp.context_resolver import resolve_hierarchical_context, ContextPolicyError

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_context_resolver_applies_allowed_overrides_only(session: Session) -> None:
    # 1. Base Brand Context
    append_context_version(session, scope="brand", scope_id="b1", payload={
        "tone": "formal",
        "brand_name": "Acme",
        "objective": "general"
    })
    
    # 2. Campaign Overrides (allowed: objective)
    append_context_version(session, scope="campaign", scope_id="c1", payload={
        "objective": "sell-summer"
    })
    
    # 3. Task Overrides (forbidden: brand_name)
    append_context_version(session, scope="task", scope_id="t1", payload={
        "brand_name": "Globex"
    })
    
    # Resolve brand -> campaign (should pass)
    ctx = resolve_hierarchical_context(session, brand_id="b1", campaign_id="c1")
    assert ctx["tone"] == "formal"
    assert ctx["brand_name"] == "Acme"
    assert ctx["objective"] == "sell-summer"
    
    # Resolve brand -> campaign -> task (should fail)
    with pytest.raises(ContextPolicyError, match="brand_name"):
        resolve_hierarchical_context(session, brand_id="b1", campaign_id="c1", task_id="t1")
