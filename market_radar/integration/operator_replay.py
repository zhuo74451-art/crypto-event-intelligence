"""Failure Replay Pack — generate sanitised replay fixtures from structured errors.

Each replay pack contains only configuration and expected status,
not full content or real API responses.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional


def generate_replay_pack(
    diagnosis_code: str,
    profile_name: str = "fixture-smoke",
    context: Optional[dict] = None,
) -> dict:
    """Generate a replay fixture for a specific failure diagnosis.

    Args:
        diagnosis_code: Machine code from operator_diagnosis.
        profile_name: Operator profile to use for replay.
        context: Optional context dict with additional parameters.

    Returns:
        Replay fixture dict (no real content, no credentials).
    """
    fixture: dict[str, Any] = {
        "replay_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "diagnosis_code": diagnosis_code,
        "profile": profile_name,
        "description": _get_description(diagnosis_code),
        "expected_status": _get_expected_status(diagnosis_code),
        "context": context or {},
        "fixture_hash": "",
    }
    raw = json.dumps(fixture, sort_keys=True, default=str)
    fixture["fixture_hash"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return fixture


def _get_description(code: str) -> str:
    descriptions = {
        "CURATED_API_UNAVAILABLE": "Curated API is unreachable — provider returns unavailable",
        "NORMAL_EMPTY_FEED": "Normal empty batch — API responds with zero new items",
        "CURSOR_CORRUPT": "Feed cursor state file is corrupted or unparseable",
        "CURSOR_ROLLBACK": "New cursor is older than persisted cursor — rollback rejected",
        "HYPERLIQUID_UNAVAILABLE": "Hyperliquid public adapter cannot reach API",
        "CCXT_UNAVAILABLE": "CCXT exchange adapter cannot initialize or fetch",
        "DB_LOCKED": "Run history database is locked by another process",
        "STOP_MARKER_SET": "STOP file exists in state directory — run blocked",
        "SCHEMA_MISMATCH": "Database schema version does not match expected",
        "REPORT_MISSING": "Expected run report JSON file not found",
        "PARENT_CHILD_MISMATCH": "Shadow parent/child run-history relationship inconsistent",
        "STALE_MARKET_SNAPSHOT": "Market data timestamp is older than expected",
        "WHALE_EMPTY_POSITIONS": "Whale address returned zero positions",
        "RUNTIME_ARTIFACT_INCOMPLETE": "Expected output artifacts are missing",
    }
    return descriptions.get(code, f"Unknown diagnosis code: {code}")


def _get_expected_status(code: str) -> str:
    expected = {
        "CURATED_API_UNAVAILABLE": "degraded",
        "NORMAL_EMPTY_FEED": "completed",
        "CURSOR_CORRUPT": "degraded",
        "CURSOR_ROLLBACK": "degraded",
        "HYPERLIQUID_UNAVAILABLE": "degraded",
        "CCXT_UNAVAILABLE": "degraded",
        "DB_LOCKED": "failed",
        "STOP_MARKER_SET": "failed",
        "SCHEMA_MISMATCH": "failed",
        "REPORT_MISSING": "failed",
        "PARENT_CHILD_MISMATCH": "failed",
        "STALE_MARKET_SNAPSHOT": "completed",
        "WHALE_EMPTY_POSITIONS": "completed",
        "RUNTIME_ARTIFACT_INCOMPLETE": "degraded",
    }
    return expected.get(code, "failed")
