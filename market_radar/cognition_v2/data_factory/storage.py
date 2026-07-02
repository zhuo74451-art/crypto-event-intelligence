"""Canonical artifact storage — JSONL and YAML.

D10: Create versioned text artifacts under data/historical_v1/.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

from market_radar.cognition_v2.data_factory.contracts import (
    CorpusBuildManifest,
    SCHEMA_VERSION,
    _stable_hash,
)


ARTIFACT_DIR = "data/historical_v1"


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _dict_clean(obj: Any) -> Any:
    """Convert dataclass/datetime/enum to serializable form."""
    from dataclasses import is_dataclass, asdict
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {k: _dict_clean(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _dict_clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_dict_clean(v) for v in obj]
    return obj


def write_jsonl(path: str, records: List[Any]) -> str:
    """Write records as sorted-key JSONL. Returns SHA256 of the file."""
    _ensure_dir(path)
    lines = []
    for r in records:
        clean = _dict_clean(r)
        line = json.dumps(clean, sort_keys=True, ensure_ascii=False)
        lines.append(line)
    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def write_yaml(path: str, data: Any) -> str:
    """Write data as YAML. Returns SHA256 of the file."""
    _ensure_dir(path)
    clean = _dict_clean(data)
    content = yaml.dump(clean, default_flow_style=False, sort_keys=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_jsonl(path: str) -> List[dict]:
    """Read JSONL file, return list of parsed dicts."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def read_yaml(path: str) -> dict:
    """Read YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def file_sha256(path: str) -> str:
    """Compute SHA256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest_hash(base_dir: str) -> str:
    """Compute deterministic manifest hash from all artifact file hashes."""
    artifacts = [
        "source_registry.yaml",
        "cases.jsonl",
        "evidence.jsonl",
        "correction_chains.jsonl",
        "market_bars.jsonl",
        "outcome_windows.jsonl",
        "split_manifest.json",
    ]
    hashes = {}
    for art in artifacts:
        path = os.path.join(base_dir, art)
        if os.path.exists(path):
            hashes[art] = file_sha256(path)
    return _stable_hash(hashes)
