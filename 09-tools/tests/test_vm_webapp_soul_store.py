from __future__ import annotations

import hashlib
import multiprocessing
import threading
from pathlib import Path

import pytest

from vm_webapp.soul_parser import SoulParseError, parse_and_validate
from vm_webapp.soul_store import SoulStore
from vm_webapp.soul_templates import required_sections, template_for


def _markdown_with_sections(title: str, sections: list[str]) -> str:
    body = [f"# {title}", ""]
    for section in sections:
        body.extend([f"## {section}", f"Content for {section}.", ""])
    return "\n".join(body).rstrip() + "\n"


def _save_brand_in_process(
    runtime_root: str,
    markdown: str,
    version_hash: str,
    result_queue: multiprocessing.Queue,
) -> None:
    store = SoulStore(runtime_root=Path(runtime_root))
    try:
        store.save_brand_soul(
            brand_id="brand-001",
            markdown=markdown,
            version_hash=version_hash,
        )
        result_queue.put(("ok", ""))
    except ValueError as exc:
        result_queue.put(("conflict", str(exc)))
    except Exception as exc:  # noqa: BLE001
        result_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def test_load_bootstraps_brand_template_when_missing(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)

    doc = store.get_brand_soul("brand-001")

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
    initial = store.get_project_soul("brand-001", "proj-001")
    markdown = _markdown_with_sections("Project Soul", required_sections("project"))

    saved = store.save_project_soul(
        brand_id="brand-001",
        project_id="proj-001",
        markdown=markdown,
        version_hash=initial.version_hash,
    )
    reloaded = store.get_project_soul("brand-001", "proj-001")

    assert saved.recovered is False
    assert saved.markdown == markdown
    assert reloaded.markdown == markdown
    assert saved.version_hash == reloaded.version_hash
    assert saved.path == tmp_path / "brands" / "brand-001" / "projects" / "proj-001" / "project.md"


def test_save_rejects_version_hash_conflict(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)
    doc = store.get_thread_soul("brand-001", "proj-001", "thread-001")

    doc.path.write_text(
        _markdown_with_sections("Thread Soul Updated", required_sections("thread")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        store.save_thread_soul(
            brand_id="brand-001",
            project_id="proj-001",
            thread_id="thread-001",
            markdown=_markdown_with_sections("Thread Soul Save", required_sections("thread")),
            version_hash=doc.version_hash,
        )

    message = str(exc_info.value)
    assert "version_hash mismatch" in message
    assert "expected=" in message
    assert "current=" in message


def test_store_paths_are_hierarchical_for_each_level(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)

    brand_doc = store.get_brand_soul("brand-001")
    project_doc = store.get_project_soul("brand-001", "proj-001")
    thread_doc = store.get_thread_soul("brand-001", "proj-001", "thread-001")

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


def test_save_api_requires_version_hash_argument(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)
    markdown = _markdown_with_sections("Brand Soul", required_sections("brand"))

    with pytest.raises(TypeError):
        store.save_brand_soul("brand-001", markdown)  # type: ignore[misc]


@pytest.mark.parametrize(
    "invalid_id",
    [
        "../escape",
        "folder/name",
        "folder\\name",
        "/absolute",
        "..",
        "name with spaces",
        "name.ext",
    ],
)
def test_rejects_invalid_ids_and_path_traversal(tmp_path: Path, invalid_id: str) -> None:
    store = SoulStore(runtime_root=tmp_path)

    with pytest.raises(ValueError):
        store.get_brand_soul(invalid_id)
    with pytest.raises(ValueError):
        store.get_project_soul("brand-001", invalid_id)
    with pytest.raises(ValueError):
        store.get_thread_soul("brand-001", "proj-001", invalid_id)


def test_save_does_not_create_file_when_hash_precondition_fails(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)
    target_path = tmp_path / "brands" / "brand-001" / "brand.md"
    markdown = _markdown_with_sections("Brand Soul", required_sections("brand"))

    with pytest.raises(ValueError):
        store.save_brand_soul(
            brand_id="brand-001",
            markdown=markdown,
            version_hash="invalid-version-hash",
        )

    assert target_path.exists() is False


def test_concurrent_save_is_locked_and_keeps_single_winner(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)
    initial = store.get_brand_soul("brand-001")
    markdown_a = _markdown_with_sections("Brand Soul A", required_sections("brand"))
    markdown_b = _markdown_with_sections("Brand Soul B", required_sections("brand"))
    barrier = threading.Barrier(3)
    results: list[str] = []
    errors: list[Exception] = []

    def _writer(markdown: str) -> None:
        barrier.wait()
        try:
            doc = store.save_brand_soul(
                brand_id="brand-001",
                markdown=markdown,
                version_hash=initial.version_hash,
            )
            results.append(doc.markdown)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    thread_a = threading.Thread(target=_writer, args=(markdown_a,))
    thread_b = threading.Thread(target=_writer, args=(markdown_b,))
    thread_a.start()
    thread_b.start()
    barrier.wait()
    thread_a.join()
    thread_b.join()

    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)

    latest = store.get_brand_soul("brand-001")
    assert latest.markdown in (markdown_a, markdown_b)
    assert list(latest.path.parent.glob("brand.md.*.tmp")) == []


def test_cross_process_save_is_optimistically_locked(tmp_path: Path) -> None:
    store = SoulStore(runtime_root=tmp_path)
    initial = store.get_brand_soul("brand-001")
    markdown_a = _markdown_with_sections("Brand Soul Process A", required_sections("brand"))
    markdown_b = _markdown_with_sections("Brand Soul Process B", required_sections("brand"))

    ctx = multiprocessing.get_context("fork")
    result_queue = ctx.Queue()
    proc_a = ctx.Process(
        target=_save_brand_in_process,
        args=(str(tmp_path), markdown_a, initial.version_hash, result_queue),
    )
    proc_b = ctx.Process(
        target=_save_brand_in_process,
        args=(str(tmp_path), markdown_b, initial.version_hash, result_queue),
    )

    proc_a.start()
    proc_b.start()
    proc_a.join(timeout=5)
    proc_b.join(timeout=5)

    assert proc_a.exitcode == 0
    assert proc_b.exitcode == 0

    results = [result_queue.get(timeout=2), result_queue.get(timeout=2)]
    statuses = [status for status, _ in results]
    assert statuses.count("ok") == 1
    assert statuses.count("conflict") == 1

    for status, message in results:
        if status == "conflict":
            assert "version_hash mismatch" in message

    latest = store.get_brand_soul("brand-001")
    assert latest.markdown in (markdown_a, markdown_b)
