from pathlib import Path

from vm_webapp.stacking import build_context_pack


def test_context_pack_contains_canonical_and_retrieved(tmp_path: Path) -> None:
    ctx = build_context_pack(
        brand_soul_md="# Soul\nAcme: evidence-led.",
        product_essence_md="# Essence\nWidget: simple.",
        retrieved=[{"title": "old run", "text": "We tried X and it failed."}],
        stage_contract="Write output in Markdown.",
        user_request="Create landing copy.",
    )
    assert "Acme: evidence-led." in ctx
    assert "Widget: simple." in ctx
    assert "We tried X and it failed." in ctx
