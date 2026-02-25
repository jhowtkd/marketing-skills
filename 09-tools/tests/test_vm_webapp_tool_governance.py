import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vm_webapp.models import Base
from vm_webapp.tooling.governance import ToolGovernance, ToolPermissionError

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_tool_execution_requires_permission_and_respects_rate_limit(session: Session) -> None:
    governance = ToolGovernance(session)
    
    # Should fail if no permission
    with pytest.raises(ToolPermissionError):
        governance.authorize_call(brand_id="b1", tool_id="search_google")

    # Add permission
    governance.grant_permission(brand_id="b1", tool_id="search_google", max_calls_per_day=2)
    
    # Should pass now
    governance.authorize_call(brand_id="b1", tool_id="search_google")
    governance.record_call(brand_id="b1", tool_id="search_google")
    
    governance.authorize_call(brand_id="b1", tool_id="search_google")
    governance.record_call(brand_id="b1", tool_id="search_google")
    
    # Should fail due to rate limit
    with pytest.raises(ToolPermissionError, match="rate limit exceeded"):
        governance.authorize_call(brand_id="b1", tool_id="search_google")

def test_tool_credential_resolution(session: Session) -> None:
    governance = ToolGovernance(session)
    governance.set_credential_ref(brand_id="b1", tool_id="search_google", secret_ref="env:GOOGLE_API_KEY")
    
    ref = governance.get_credential_ref(brand_id="b1", tool_id="search_google")
    assert ref == "env:GOOGLE_API_KEY"
