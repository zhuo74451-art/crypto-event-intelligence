"""
All 71 V2 portfolio-level corpus case definitions (C101-C171).

Imported by gen_v2_corpus.py and consumed by test_whale_replay_corpus_v2.py.
Data is loaded from the canonical JSON fixture to avoid duplication.

This file replaces the former _v2_cases.py pattern by re-exporting data
from whale_replay_corpus_v2.json, keeping the generator and test in sync
with a single source of truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_CORPUS_PATH = _THIS_DIR / "whale_replay_corpus_v2.json"

with open(_CORPUS_PATH, "r", encoding="utf-8") as _f:
    _CORPUS_DATA: dict[str, Any] = json.load(_f)

ALL_CASES: list[dict[str, Any]] = _CORPUS_DATA["cases"]

META: dict[str, Any] = _CORPUS_DATA.get("corpus_meta", {})

CASES_BY_ID: dict[str, dict[str, Any]] = {c["case_id"]: c for c in ALL_CASES}

# Re-export for backward compatibility with gen_v2_corpus.py
# (which previously imported from _v2_cases)
__all__ = ["ALL_CASES", "META", "CASES_BY_ID"]
