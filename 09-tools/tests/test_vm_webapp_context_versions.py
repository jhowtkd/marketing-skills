import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from vm_webapp.models import Base, ContextVersion
from vm_webapp.context_versions import append_context_version

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_context_versions_are_append_only(session: Session) -> None:
    # 1. Append first version
    payload1 = {"soul": "classic"}
    v1_id = append_context_version(session, scope="brand", scope_id="b1", payload=payload1)
    
    # 2. Append second version
    payload2 = {"soul": "modern"}
    v2_id = append_context_version(session, scope="brand", scope_id="b1", payload=payload2)
    
    assert v1_id != v2_id
    
    # Verify both exist and are correct
    v1 = session.get(ContextVersion, v1_id)
    v2 = session.get(ContextVersion, v2_id)
    
    assert json.loads(v1.payload_json) == payload1
    assert json.loads(v2.payload_json) == payload2
    assert v1.scope == "brand"
    assert v1.scope_id == "b1"
