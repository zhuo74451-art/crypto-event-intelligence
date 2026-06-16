"""Fixture Loader — offline-safe deterministic test data.

Loads fixture JSON files from the fixtures/ directory.
All files are credential-free and timestamped for repeatability.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional


_FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

# Catalog of known fixtures with expected decisions
FIXTURE_CATALOG: dict[str, dict[str, Any]] = {
    "event_high_quality": {
        "file": "event_high_quality.json",
        "expected_decision": "观察",
        "description": "高质量市场事件 — SEC BTC ETF 期权",
        "dedup_key": "cei_dedup:btc-etf-options-2026-06-16",
    },
    "event_duplicate": {
        "file": "event_duplicate.json",
        "expected_decision": "丢弃",
        "description": "重复事件（与 high_quality 相同 dedup_key）",
        "dedup_key": "cei_dedup:btc-etf-options-2026-06-16",
    },
    "event_old_news_rehash": {
        "file": "event_old_news_rehash.json",
        "expected_decision": "风险提示",
        "description": "旧消息重炒 — stale news repackaged",
        "dedup_key": "cei_dedup:old-news-rehash-btc-2026-06",
    },
    "event_no_asset": {
        "file": "event_no_asset.json",
        "expected_decision": "观察",
        "description": "无明确资产事件 — 宏观经济新闻",
        "dedup_key": "cei_dedup:no-asset-event-2026-06-16",
    },
    "event_insufficient_source": {
        "file": "event_insufficient_source.json",
        "expected_decision": "丢弃",
        "description": "来源不足事件 — 单一不可验证来源",
        "dedup_key": "cei_dedup:insufficient-source-2026-06-16",
    },
    "event_pump_risk": {
        "file": "event_pump_risk.json",
        "expected_decision": "禁止",
        "description": "高追涨/Pump 风险事件",
        "dedup_key": "cei_dedup:pump-risk-sol-2026-06-16",
    },
    "event_missing_fields": {
        "file": "event_missing_fields.json",
        "expected_decision": "丢弃",
        "description": "数据字段缺失事件",
        "dedup_key": "cei_dedup:missing-fields-2026-06-16",
    },
}


def load_fixture(fixture_id: str) -> Optional[dict[str, Any]]:
    """Load a fixture JSON file by its ID.

    Returns the parsed dict, or None if the file cannot be loaded.
    """
    entry = FIXTURE_CATALOG.get(fixture_id)
    if entry is None:
        return None
    file_path = os.path.join(_FIXTURES_DIR, entry["file"])
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def load_all_fixtures() -> list[dict[str, Any]]:
    """Load all known fixtures.

    Returns list of (fixture_id, data) tuples for loaded fixtures.
    Silently skips fixtures that fail to load.
    """
    results = []
    for fid in FIXTURE_CATALOG:
        data = load_fixture(fid)
        if data is not None:
            results.append({"fixture_id": fid, "data": data})
    return results


def get_dedup_key(data: dict[str, Any]) -> str:
    """Extract the dedup key from a fixture payload.

    Returns empty string if no dedup_key is present.
    """
    return data.get("dedup_key", "")


def load_binance_sample() -> Optional[dict[str, Any]]:
    """Load the real Binance API response sample."""
    file_path = os.path.join(_FIXTURES_DIR, "real_binance_response_sample.json")
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None
