"""Filesystem I/O helpers: atomic writes, cross-process locking, YAML/JSON round-trip.

All KB reads / writes MUST go through this module. Direct ``open(...)`` is
forbidden by convention because we want:

1. Atomic writes (``.tmp`` then ``os.replace``) so a crash never leaves a
   half-written file.
2. Cross-process file locks so two agents (Claude Code + MCP) editing the
   same project cannot corrupt each other's writes.
3. Consistent YAML dumper flags (``allow_unicode`` on, ``sort_keys`` off).
4. Schema-version awareness — a stale ``schema_version`` triggers a
   ``SchemaVersionError`` rather than silently loading a stale file.

None of the functions here depend on Pydantic; the schemas layer builds on
top of them.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional, Union

import yaml
from filelock import FileLock, Timeout

from .schemas.base import SCHEMA_VERSION, SchemaVersionError


PathLike = Union[str, os.PathLike[str]]
DEFAULT_LOCK_TIMEOUT_SEC = 10.0


# ---------------------------------------------------------------------------
# Low-level atomic write
# ---------------------------------------------------------------------------


def atomic_write_bytes(path: PathLike, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically.

    Implementation: write into a sibling ``NamedTemporaryFile`` in the same
    directory (so ``os.replace`` is atomic across filesystems), fsync, then
    rename over the target. Works on POSIX and Windows.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
    try:
        os.replace(tmp_path, target)
    except OSError:
        # Cleanup then re-raise so caller sees the real error
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def atomic_write_text(path: PathLike, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


# ---------------------------------------------------------------------------
# File locking
# ---------------------------------------------------------------------------


def _lock_path_for(target: PathLike) -> Path:
    p = Path(target)
    return p.parent / f".{p.name}.lock"


@contextmanager
def file_lock(
    target: PathLike,
    *,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SEC,
) -> Iterator[None]:
    """Acquire a cross-process advisory lock associated with ``target``.

    Raises ``TimeoutError`` if the lock cannot be acquired within ``timeout``
    seconds — we do NOT let ``filelock.Timeout`` leak because callers should
    not need to import filelock.
    """
    lock_path = _lock_path_for(target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path), timeout=timeout)
    try:
        lock.acquire()
    except Timeout as e:
        raise TimeoutError(
            f"could not acquire lock on {target} within {timeout}s "
            f"(is another process editing it?)"
        ) from e
    try:
        yield
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# YAML I/O
# ---------------------------------------------------------------------------


def _yaml_dump(data: Any) -> str:
    """Consistent YAML dump formatting."""
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        indent=2,
        width=100,
    )


def load_yaml(path: PathLike, *, check_schema_version: bool = True) -> dict:
    """Load a YAML file into a plain dict.

    If ``check_schema_version`` is True (default) and the file has a
    ``schema_version`` key that differs from the current ``SCHEMA_VERSION``,
    raises ``SchemaVersionError`` so the caller can route to migrate.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected a mapping at top-level of {p}, got {type(data).__name__}")
    if check_schema_version:
        v = data.get("schema_version")
        if v is not None and v != SCHEMA_VERSION:
            raise SchemaVersionError(str(v), SCHEMA_VERSION, path=str(p))
    return data


def dump_yaml(
    path: PathLike,
    data: dict,
    *,
    with_lock: bool = True,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SEC,
) -> None:
    """Atomically write ``data`` as YAML.

    If ``with_lock`` is True (default), takes a filesystem lock on ``path``
    for the duration of the write. Callers who already hold the lock (e.g.
    read-modify-write inside ``locked_edit_yaml``) should pass ``False``.
    """
    text = _yaml_dump(data)
    if with_lock:
        with file_lock(path, timeout=timeout):
            atomic_write_text(path, text)
    else:
        atomic_write_text(path, text)


@contextmanager
def locked_edit_yaml(
    path: PathLike,
    *,
    create_if_missing: bool = False,
    default: Optional[dict] = None,
    check_schema_version: bool = True,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SEC,
) -> Iterator[dict]:
    """Read-modify-write a YAML file under a lock.

    Usage::

        with locked_edit_yaml("outcomes.yaml") as data:
            data["events"].append(new_event)

    On exit, the mutated dict is written back atomically. If the ``with``
    body raises, no write is performed.
    """
    p = Path(path)
    with file_lock(p, timeout=timeout):
        if p.exists():
            data = load_yaml(p, check_schema_version=check_schema_version)
        elif create_if_missing:
            data = dict(default or {})
        else:
            raise FileNotFoundError(f"{p} does not exist and create_if_missing=False")
        yield data
        dump_yaml(p, data, with_lock=False)


# ---------------------------------------------------------------------------
# JSON I/O (mainly for the derived state file)
# ---------------------------------------------------------------------------


def load_json(path: PathLike) -> dict:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object at top-level of {p}")
    return data


def dump_json(
    path: PathLike,
    data: dict,
    *,
    with_lock: bool = True,
    indent: int = 2,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SEC,
) -> None:
    text = json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=False) + "\n"
    if with_lock:
        with file_lock(path, timeout=timeout):
            atomic_write_text(path, text)
    else:
        atomic_write_text(path, text)


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_copy(src: PathLike, dst: PathLike) -> None:
    """Copy a file, creating parents as needed. Preserves mtime."""
    dst_p = Path(dst)
    ensure_dir(dst_p.parent)
    shutil.copy2(src, dst_p)


# ---------------------------------------------------------------------------
# Test hook: expose the yaml dumper for golden-file tests
# ---------------------------------------------------------------------------

_yaml_dump_stream = io.StringIO  # re-exported for tests


__all__ = [
    "PathLike",
    "atomic_write_bytes",
    "atomic_write_text",
    "file_lock",
    "load_yaml",
    "dump_yaml",
    "locked_edit_yaml",
    "load_json",
    "dump_json",
    "ensure_dir",
    "safe_copy",
]
