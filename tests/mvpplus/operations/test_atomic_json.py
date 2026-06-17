"""Tests for atomic_json."""

import json
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from market_radar.operations.atomic_json import atomic_write_json, _unique_tmp_path


class TestAtomicJson:
    def test_atomic_write(self, tmp_path: Path):
        target = tmp_path / "test.json"
        path = atomic_write_json({"a": 1}, target)
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == {"a": 1}
        assert path == str(target.resolve())

    def test_backup_created(self, tmp_path: Path):
        target = tmp_path / "backup_test.json"
        atomic_write_json({"v": 1}, target)
        atomic_write_json({"v": 2}, target, backup=True)
        assert target.exists()
        backup = target.with_suffix(".json.backup")
        assert backup.exists()
        data = json.loads(backup.read_text(encoding="utf-8"))
        assert data == {"v": 1}

    def test_tmp_cleaned(self, tmp_path: Path):
        """The unique .tmp file must not linger after the write."""
        target = tmp_path / "clean.json"
        atomic_write_json({"x": 1}, target)
        # Check no *.tmp files remain in the directory
        tmp_files = list(target.parent.glob("*.tmp"))
        assert len(tmp_files) == 0, f"leftover tmp files: {tmp_files}"

    def test_list_data(self, tmp_path: Path):
        target = tmp_path / "list.json"
        atomic_write_json([1, 2, 3], target)
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == [1, 2, 3]

    def test_unique_tmp_per_writer(self, tmp_path: Path):
        """Each call to _unique_tmp_path must produce a distinct path."""
        p1 = _unique_tmp_path(tmp_path / "data.json")
        p2 = _unique_tmp_path(tmp_path / "data.json")
        assert p1 != p2, f"two temp paths must differ: {p1} == {p2}"

    def test_tmp_path_in_same_directory(self, tmp_path: Path):
        """The temp file must be in the same directory as the target."""
        target = tmp_path / "sub" / "data.json"
        tmp = _unique_tmp_path(target)
        assert tmp.parent == target.parent, (
            f"tmp parent {tmp.parent} != target parent {target.parent}"
        )
        assert tmp.name.startswith("data.json")

    def test_concurrent_writers_unique_tmp(self, tmp_path: Path):
        """Concurrent writers must not share a .tmp path."""
        target = tmp_path / "concurrent.json"
        n = 16
        written = []

        def write(i: int) -> str:
            path = atomic_write_json({"worker": i, "data": list(range(i))}, target)
            return path

        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = [pool.submit(write, i) for i in range(n)]
            for f in as_completed(futures):
                written.append(f.result())

        assert len(written) == n
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        # Some worker wrote last
        assert "worker" in data

        # No lingering .tmp files
        tmp_files = list(target.parent.glob("*.tmp"))
        assert len(tmp_files) == 0, f"leftover tmp files: {tmp_files}"
