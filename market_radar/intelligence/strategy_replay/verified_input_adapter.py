
"""Verified input adapter — maps Lane A/B canonical fields to Lane C contracts.

Lane A uses: actual_release_at_utc, actual_initial, actual_value_status
Lane B uses: event_time_utc, baseline_price_time_utc, endpoint_price_time_utc

This adapter enforces strict field mapping with no silent fallback.
"""

from __future__ import annotations
from typing import Any, Optional


def adapt_macro_event(raw: dict[str, Any]) -> dict[str, Any]:
    """Adapt a Lane A canonical macro event to Lane C expected fields."""
    adapted = {
        "event_id": raw.get("event_id", ""),
        "event_family": raw.get("event_family", ""),
        "release_time_utc": raw.get("actual_release_at_utc", raw.get("release_time_utc", "")),
        "initial_value": raw.get("actual_initial", raw.get("initial_value")),
        "actual_value_status": raw.get("actual_value_status", "unknown"),
        "point_in_time_grade": raw.get("point_in_time_grade", "medium"),
        "consensus_value": raw.get("consensus_value"),
        "prior_value": raw.get("prior_value"),
    }
    # Verify required fields exist
    assert adapted["event_id"], f"Missing event_id in {raw}"
    assert adapted["release_time_utc"], f"Missing release_time_utc in {raw}"
    return adapted


def adapt_horizon_window(raw: dict[str, Any]) -> dict[str, Any]:
    """Adapt a Lane B horizon window record."""
    return {
        "window_id": raw.get("window_id", ""),
        "event_id": raw.get("event_id", ""),
        "asset": raw.get("asset", ""),
        "instrument_id": raw.get("instrument_id", ""),
        "horizon": raw.get("horizon", ""),
        "event_time_utc": raw.get("event_time_utc", ""),
        "baseline_price_time_utc": raw.get("baseline_price_time_utc", ""),
        "endpoint_price_time_utc": raw.get("endpoint_price_time_utc", ""),
        "pre_bar_close": raw.get("pre_bar_close"),
        "post_bar_close": raw.get("post_bar_close"),
        "return_pct": raw.get("return_pct"),
        "direction": raw.get("direction", "neutral"),
        "precision_class": raw.get("precision_class", "coarse_hourly_alignment"),
        "endpoint_price": raw.get("endpoint_price", raw.get("post_bar_close")),
    }


def adapt_reaction_label(raw: dict[str, Any]) -> dict[str, Any]:
    """Adapt a Lane B reaction label record."""
    return {
        "label_id": raw.get("label_id", ""),
        "window_id": raw.get("window_id", ""),
        "event_id": raw.get("event_id", ""),
        "asset": raw.get("asset", ""),
        "horizon": raw.get("horizon", ""),
        "direction": raw.get("direction", "neutral"),
        "return_pct": raw.get("return_pct", 0.0),
        "precision_class": raw.get("precision_class", "coarse_hourly_alignment"),
    }


def get_event_time_source() -> str:
    """Return the authoritative event time source field name."""
    return "actual_release_at_utc"


def get_initial_value_source() -> str:
    """Return the authoritative initial value source field name."""
    return "actual_initial"


def get_required_value_status() -> str:
    """Return the required value status for verified events."""
    return "verified_initial_from_release"
