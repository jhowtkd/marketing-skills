from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from vm_webapp.soul_parser import SoulParseError, parse_and_validate
from vm_webapp.soul_store import OptimisticConcurrencyError, SoulStore
from vm_webapp.soul_templates import required_sections, template_for


def _markdown_with_sections(title: str, sections: list[str]) -> str:
    body = [f"# {title}", ""]
    for section in sections:
        body.extend([f"## {section}", f"Content for {section}.", ""])
    return "\n".join(body).rstrip() + "\n"


def test_load_bootstraps_brand_template_when_missing(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)

    doc = store.load(level="brand", brand_id="brand-001")

    assert doc.path == tmp_path / "brands" / "brand-001" / "brand.md"
    assert doc.path.exists()
    assert doc.recovered is True
    assert doc.level == "brand"
    assert doc.markdown == template_for("brand")
    assert set(required_sections("brand")).issubset(set(doc.sections.keys()))
    assert doc.version_hash == hashlib.sha256(doc.markdown.encode("utf-8")).hexdigest()
    assert isinstance(doc.updated_at, str)


def test_parser_reports_missing_required_sections_with_clear_error() -> None:
    markdown = "# Brand Soul\n\n## Brand Overview\nOnly one section.\n"

    with pytest.raises(SoulParseError) as exc_info:
        parse_and_validate(level="brand", markdown=markdown)

    message = str(exc_info.value)
    assert "Missing required section(s)" in message
    assert "brand" in message
    assert "Brand Voice" in message


def test_save_and_reload_roundtrip_for_project_document(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)
    initial = store.load(level="project", brand_id="brand-001", project_id="proj-001")
    markdown = _markdown_with_sections("Project Soul", required_sections("project"))

    saved = store.save(
        level="project",
        brand_id="brand-001",
        project_id="proj-001",
        markdown=markdown,
        expected_version_hash=initial.version_hash,
    )
    reloaded = store.load(level="project", brand_id="brand-001", project_id="proj-001")

    assert saved.recovered is False
    assert saved.markdown == markdown
    assert reloaded.markdown == markdown
    assert saved.version_hash == reloaded.version_hash
    assert saved.path == tmp_path / "brands" / "brand-001" / "projects" / "proj-001" / "project.md"


def test_save_rejects_version_hash_conflict(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)
    doc = store.load(
        level="thread",
        brand_id="brand-001",
        project_id="proj-001",
        thread_id="thread-001",
    )

    doc.path.write_text(
        _markdown_with_sections("Thread Soul Updated", required_sections("thread")),
        encoding="utf-8",
    )

    with pytest.raises(OptimisticConcurrencyError) as exc_info:
        store.save(
            level="thread",
            brand_id="brand-001",
            project_id="proj-001",
            thread_id="thread-001",
            markdown=_markdown_with_sections("Thread Soul Save", required_sections("thread")),
            expected_version_hash=doc.version_hash,
        )

    message = str(exc_info.value)
    assert "version_hash mismatch" in message
    assert "expected=" in message
    assert "current=" in message


def test_store_paths_are_hierarchical_for_each_level(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)

    brand_doc = store.load(level="brand", brand_id="brand-001")
    project_doc = store.load(level="project", brand_id="brand-001", project_id="proj-001")
    thread_doc = store.load(
        level="thread",
        brand_id="brand-001",
        project_id="proj-001",
        thread_id="thread-001",
    )

    assert brand_doc.path == tmp_path / "brands" / "brand-001" / "brand.md"
    assert project_doc.path == tmp_path / "brands" / "brand-001" / "projects" / "proj-001" / "project.md"
    assert (
        thread_doc.path
        == tmp_path
        / "brands"
        / "brand-001"
        / "projects"
        / "proj-001"
        / "threads"
        / "thread-001"
        / "thread.md"
    )
