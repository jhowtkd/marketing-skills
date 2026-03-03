from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from vm_webapp.soul_parser import parse_and_validate
from vm_webapp.soul_templates import (
    SOUL_LEVEL_BRAND,
    SOUL_LEVEL_PROJECT,
    SOUL_LEVEL_THREAD,
    template_for,
)


@dataclass(frozen=True)
class SoulDocument:
    level: str
    markdown: str
    sections: dict[str, str]
    version_hash: str
    path: Path
    updated_at: str
    recovered: bool


def _sha256_markdown(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _updated_at_iso(path: Path) -> str:
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime.isoformat()


def resolve_soul_path(
    *,
    runtime_root: Path,
    level: str,
    brand_id: str,
    project_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Path:
    if level == SOUL_LEVEL_BRAND:
        return runtime_root / "brands" / brand_id / "brand.md"
    if level == SOUL_LEVEL_PROJECT:
        if not project_id:
            raise ValueError("project_id is required for level 'project'.")
        return runtime_root / "brands" / brand_id / "projects" / project_id / "project.md"
    if level == SOUL_LEVEL_THREAD:
        if not project_id:
            raise ValueError("project_id is required for level 'thread'.")
        if not thread_id:
            raise ValueError("thread_id is required for level 'thread'.")
        return (
            runtime_root
            / "brands"
            / brand_id
            / "projects"
            / project_id
            / "threads"
            / thread_id
            / "thread.md"
        )
    raise ValueError(
        f"Unsupported soul level '{level}'. Expected one of: "
        f"{SOUL_LEVEL_BRAND}, {SOUL_LEVEL_PROJECT}, {SOUL_LEVEL_THREAD}"
    )


def _build_document(level: str, path: Path, markdown: str, recovered: bool) -> SoulDocument:
    sections = parse_and_validate(level=level, markdown=markdown)
    return SoulDocument(
        level=level,
        markdown=markdown,
        sections=sections,
        version_hash=_sha256_markdown(markdown),
        path=path,
        updated_at=_updated_at_iso(path),
        recovered=recovered,
    )


class SoulStore:
    def __init__(self, runtime_root: Path) -> None:
        self.runtime_root = runtime_root

    def _path_for(
        self,
        *,
        level: str,
        brand_id: str,
        project_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Path:
        return resolve_soul_path(
            runtime_root=self.runtime_root,
            level=level,
            brand_id=brand_id,
            project_id=project_id,
            thread_id=thread_id,
        )

    def _load(
        self,
        *,
        level: str,
        brand_id: str,
        project_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> SoulDocument:
        path = self._path_for(
            level=level,
            brand_id=brand_id,
            project_id=project_id,
            thread_id=thread_id,
        )
        recovered = False
        if not path.exists():
            recovered = True
            _write_text_atomic(path, template_for(level))
        markdown = path.read_text(encoding="utf-8")
        return _build_document(level=level, path=path, markdown=markdown, recovered=recovered)

    def _save(
        self,
        *,
        level: str,
        brand_id: str,
        markdown: str,
        version_hash: str,
        project_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> SoulDocument:
        path = self._path_for(
            level=level,
            brand_id=brand_id,
            project_id=project_id,
            thread_id=thread_id,
        )

        if path.exists():
            current_markdown = path.read_text(encoding="utf-8")
        else:
            current_markdown = template_for(level)
            _write_text_atomic(path, current_markdown)

        current_hash = _sha256_markdown(current_markdown)
        if version_hash != current_hash:
            raise ValueError(
                "version_hash mismatch: "
                f"expected={version_hash} current={current_hash}"
            )

        parse_and_validate(level=level, markdown=markdown)
        _write_text_atomic(path, markdown)
        return _build_document(level=level, path=path, markdown=markdown, recovered=False)

    def get_brand_soul(self, brand_id: str) -> SoulDocument:
        return self._load(level=SOUL_LEVEL_BRAND, brand_id=brand_id)

    def get_project_soul(self, brand_id: str, project_id: str) -> SoulDocument:
        return self._load(
            level=SOUL_LEVEL_PROJECT,
            brand_id=brand_id,
            project_id=project_id,
        )

    def get_thread_soul(self, brand_id: str, project_id: str, thread_id: str) -> SoulDocument:
        return self._load(
            level=SOUL_LEVEL_THREAD,
            brand_id=brand_id,
            project_id=project_id,
            thread_id=thread_id,
        )

    def save_brand_soul(self, brand_id: str, markdown: str, version_hash: str) -> SoulDocument:
        return self._save(
            level=SOUL_LEVEL_BRAND,
            brand_id=brand_id,
            markdown=markdown,
            version_hash=version_hash,
        )

    def save_project_soul(
        self,
        brand_id: str,
        project_id: str,
        markdown: str,
        version_hash: str,
    ) -> SoulDocument:
        return self._save(
            level=SOUL_LEVEL_PROJECT,
            brand_id=brand_id,
            project_id=project_id,
            markdown=markdown,
            version_hash=version_hash,
        )

    def save_thread_soul(
        self,
        brand_id: str,
        project_id: str,
        thread_id: str,
        markdown: str,
        version_hash: str,
    ) -> SoulDocument:
        return self._save(
            level=SOUL_LEVEL_THREAD,
            brand_id=brand_id,
            project_id=project_id,
            thread_id=thread_id,
            markdown=markdown,
            version_hash=version_hash,
        )


def load_soul_document(
    *,
    runtime_root: Path,
    level: str,
    brand_id: str,
    project_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> SoulDocument:
    return SoulStore(runtime_root=runtime_root)._load(
        level=level,
        brand_id=brand_id,
        project_id=project_id,
        thread_id=thread_id,
    )


def save_soul_document(
    *,
    runtime_root: Path,
    level: str,
    brand_id: str,
    markdown: str,
    version_hash: str,
    project_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> SoulDocument:
    return SoulStore(runtime_root=runtime_root)._save(
        level=level,
        brand_id=brand_id,
        project_id=project_id,
        thread_id=thread_id,
        markdown=markdown,
        version_hash=version_hash,
    )
