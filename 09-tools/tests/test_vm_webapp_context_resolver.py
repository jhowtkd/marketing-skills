from pathlib import Path
import pytest

from vm_webapp.db import build_engine, init_db, session_scope
from vm_webapp.context_versions import append_context_version
from vm_webapp.context_resolver import resolve_hierarchical_context, ContextPolicyError


def test_context_resolver_applies_allowed_overrides_only(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        # 1. Base Brand context
        append_context_version(
            session,
            scope="brand",
            scope_id="b1",
            payload={
                "brand_name": "Acme",
                "tone": "formal",
                "target_audience": "professionals"
            }
        )

        # 2. Campaign overrides 'tone' (allowed)
        append_context_version(
            session,
            scope="campaign",
            scope_id="c1",
            payload={
                "tone": "playful"
            }
        )

        # 3. Task overrides 'target_audience' (allowed)
        append_context_version(
            session,
            scope="task",
            scope_id="t1",
            payload={
                "target_audience": "developers"
            }
        )

        # 4. Resolve
        context = resolve_hierarchical_context(
            session,
            brand_id="b1",
            campaign_id="c1",
            task_id="t1"
        )

        assert context["brand_name"] == "Acme"
        assert context["tone"] == "playful"
        assert context["target_audience"] == "developers"

def test_context_resolver_blocks_forbidden_overrides(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "db.sqlite3")
    init_db(engine)

    with session_scope(engine) as session:
        append_context_version(
            session,
            scope="brand",
            scope_id="b1",
            payload={"brand_name": "Acme"}
        )

        # Campaign tries to override 'brand_name' (forbidden)
        append_context_version(
            session,
            scope="campaign",
            scope_id="c1",
            payload={"brand_name": "Evil Corp"}
        )

        with pytest.raises(ContextPolicyError, match="Override of 'brand_name' is not allowed"):
            resolve_hierarchical_context(
                session,
                brand_id="b1",
                campaign_id="c1"
            )
