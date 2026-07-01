"""Tests for tools.io_utils — atomic write, file locking, YAML round-trip."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from tools import io_utils
from tools.schemas.base import SchemaVersionError


# ---------------------------------------------------------------------------
# atomic_write_bytes / atomic_write_text
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    def test_creates_file_with_content(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        io_utils.atomic_write_text(target, "hello")
        assert target.read_text(encoding="utf-8") == "hello"

    def test_overwrites_existing_file_atomically(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        target.write_text("old", encoding="utf-8")
        io_utils.atomic_write_text(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_creates_parent_dirs(self, tmp_path: Path):
        target = tmp_path / "nested" / "deeper" / "out.txt"
        io_utils.atomic_write_text(target, "x")
        assert target.is_file()

    def test_no_tmp_file_left_on_success(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        io_utils.atomic_write_text(target, "x")
        tmps = list(tmp_path.glob(".out.txt.*.tmp"))
        assert tmps == []

    def test_unicode_content_preserved(self, tmp_path: Path):
        target = tmp_path / "u.txt"
        io_utils.atomic_write_text(target, "你好 🧪")
        assert target.read_text(encoding="utf-8") == "你好 🧪"


# ---------------------------------------------------------------------------
# YAML load/dump
# ---------------------------------------------------------------------------


class TestYamlRoundTrip:
    def test_dump_and_load_roundtrip(self, tmp_path: Path):
        target = tmp_path / "x.yaml"
        payload = {
            "schema_version": "2.0",
            "schema_type": "test",
            "name": "张三",
            "list": [1, 2, 3],
        }
        io_utils.dump_yaml(target, payload)
        loaded = io_utils.load_yaml(target)
        assert loaded == payload

    def test_load_rejects_stale_schema_version(self, tmp_path: Path):
        target = tmp_path / "x.yaml"
        target.write_text("schema_version: '1.0'\nname: X\n", encoding="utf-8")
        with pytest.raises(SchemaVersionError):
            io_utils.load_yaml(target)

    def test_load_can_skip_version_check(self, tmp_path: Path):
        target = tmp_path / "x.yaml"
        target.write_text("schema_version: '1.0'\nname: X\n", encoding="utf-8")
        data = io_utils.load_yaml(target, check_schema_version=False)
        assert data["name"] == "X"

    def test_load_top_level_must_be_mapping(self, tmp_path: Path):
        target = tmp_path / "x.yaml"
        target.write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(ValueError):
            io_utils.load_yaml(target)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


class TestJsonRoundTrip:
    def test_dump_and_load(self, tmp_path: Path):
        target = tmp_path / "state.json"
        payload = {"schema_version": "2.0", "name": "张三", "counts": {"projects": 3}}
        io_utils.dump_json(target, payload)
        assert io_utils.load_json(target) == payload

    def test_top_level_must_be_object(self, tmp_path: Path):
        target = tmp_path / "state.json"
        target.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(ValueError):
            io_utils.load_json(target)


# ---------------------------------------------------------------------------
# file locking
# ---------------------------------------------------------------------------


class TestFileLock:
    def test_lock_serializes_writers(self, tmp_path: Path):
        target = tmp_path / "counter.txt"
        target.write_text("0", encoding="utf-8")

        def increment():
            with io_utils.file_lock(target, timeout=5):
                v = int(target.read_text())
                time.sleep(0.02)
                target.write_text(str(v + 1), encoding="utf-8")

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert int(target.read_text()) == 5

    def test_locked_edit_yaml_persists_changes(self, tmp_path: Path):
        target = tmp_path / "x.yaml"
        io_utils.dump_yaml(target, {"schema_version": "2.0", "counter": 0})
        with io_utils.locked_edit_yaml(target) as data:
            data["counter"] = 42
        assert io_utils.load_yaml(target)["counter"] == 42

    def test_locked_edit_yaml_missing_file_without_create_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            with io_utils.locked_edit_yaml(tmp_path / "nope.yaml"):
                pass

    def test_locked_edit_yaml_can_create(self, tmp_path: Path):
        target = tmp_path / "new.yaml"
        with io_utils.locked_edit_yaml(
            target, create_if_missing=True, default={"schema_version": "2.0", "a": 1}
        ) as data:
            data["a"] = 2
        assert io_utils.load_yaml(target)["a"] == 2

    def test_locked_edit_yaml_does_not_persist_on_exception(self, tmp_path: Path):
        target = tmp_path / "x.yaml"
        io_utils.dump_yaml(target, {"schema_version": "2.0", "a": 1})
        with pytest.raises(RuntimeError):
            with io_utils.locked_edit_yaml(target) as data:
                data["a"] = 99
                raise RuntimeError("boom")
        # File should be unchanged
        assert io_utils.load_yaml(target)["a"] == 1


# ---------------------------------------------------------------------------
# ensure_dir / safe_copy
# ---------------------------------------------------------------------------


class TestFileHelpers:
    def test_ensure_dir_creates_missing(self, tmp_path: Path):
        p = io_utils.ensure_dir(tmp_path / "a" / "b" / "c")
        assert p.is_dir()

    def test_safe_copy_creates_parent(self, tmp_path: Path):
        src = tmp_path / "src.txt"
        src.write_text("data", encoding="utf-8")
        dst = tmp_path / "nested" / "dst.txt"
        io_utils.safe_copy(src, dst)
        assert dst.read_text() == "data"
