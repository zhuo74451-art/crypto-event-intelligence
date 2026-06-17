"""Tests for atomic_json."""

import json
from pathlib import Path

from market_radar.operations.atomic_json import atomic_write_json


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
        target = tmp_path / "clean.json"
        atomic_write_json({"x": 1}, target)
        assert not target.with_suffix(".tmp").exists()

    def test_list_data(self, tmp_path: Path):
        target = tmp_path / "list.json"
        atomic_write_json([1, 2, 3], target)
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == [1, 2, 3]
