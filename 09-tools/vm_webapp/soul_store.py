from __future__ import annotations

import hashlib
import os
import re
import tempfile
import threading
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

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


class SoulVersionConflictError(ValueError):
    """Raised when the provided version hash does not match current persisted hash."""


_SOUL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_PATH_LOCK_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.Lock] = {}


def _sha256_markdown(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(path))
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _updated_at_iso(path: Path) -> str:
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return mtime.isoformat()


def _validate_identifier(identifier_name: str, identifier_value: str) -> str:
    if not identifier_value:
        raise ValueError(f"{identifier_name} is required.")
    if (
        "/" in identifier_value
        or "\\" in identifier_value
        or ".." in identifier_value
        or Path(identifier_value).is_absolute()
    ):
        raise ValueError(
            f"Invalid {identifier_name} '{identifier_value}': "
            "path separators, '..' and absolute paths are not allowed."
        )
    if not _SOUL_ID_PATTERN.fullmatch(identifier_value):
        raise ValueError(
            f"Invalid {identifier_name} '{identifier_value}': "
            "use alphanumeric characters plus '-' and '_' only."
        )
    return identifier_value


def _ensure_path_within_base(base_dir: Path, target_path: Path) -> Path:
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve(strict=False)
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError as exc:
        raise ValueError(
            f"Resolved soul path escapes runtime root: '{resolved_target}'."
        ) from exc
    return resolved_target


@contextmanager
def _lock_for_path(path: Path) -> Iterator[None]:
    path_key = str(path.resolve(strict=False))
    with _PATH_LOCK_GUARD:
        lock = _PATH_LOCKS.get(path_key)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[path_key] = lock
    lock.acquire()
    lock_file = None
    try:
        lock_path = path.with_name(f"{path.name}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("a+")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if lock_file is not None:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()
        lock.release()


def resolve_soul_path(
    *,
    runtime_root: Path,
    level: str,
    brand_id: str,
    project_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Path:
    safe_brand_id = _validate_identifier("brand_id", brand_id)
    base_dir = runtime_root.resolve()
    if level == SOUL_LEVEL_BRAND:
        path = base_dir / "brands" / safe_brand_id / "brand.md"
        return _ensure_path_within_base(base_dir, path)
    if level == SOUL_LEVEL_PROJECT:
        if not project_id:
            raise ValueError("project_id is required for level 'project'.")
        safe_project_id = _validate_identifier("project_id", project_id)
        path = (
            base_dir
            / "brands"
            / safe_brand_id
            / "projects"
            / safe_project_id
            / "project.md"
        )
        return _ensure_path_within_base(base_dir, path)
    if level == SOUL_LEVEL_THREAD:
        if not project_id:
            raise ValueError("project_id is required for level 'thread'.")
        if not thread_id:
            raise ValueError("thread_id is required for level 'thread'.")
        safe_project_id = _validate_identifier("project_id", project_id)
        safe_thread_id = _validate_identifier("thread_id", thread_id)
        path = (
            base_dir
            / "brands"
            / safe_brand_id
            / "projects"
            / safe_project_id
            / "threads"
            / safe_thread_id
            / "thread.md"
        )
        return _ensure_path_within_base(base_dir, path)
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
        with _lock_for_path(path):
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
        with _lock_for_path(path):
            if path.exists():
                current_markdown = path.read_text(encoding="utf-8")
            else:
                current_markdown = template_for(level)

            current_hash = _sha256_markdown(current_markdown)
            if version_hash != current_hash:
                raise SoulVersionConflictError(
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
