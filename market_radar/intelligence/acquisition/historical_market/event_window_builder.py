"""Event window builder — aligns market bars around macro events.

Builds EventMarketWindowV1 and MarketReactionLabelV1 for each
(event, instrument) pair based on available market data.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .contracts import (
    MarketBarV1,
    EventMarketWindowV1,
    MarketReactionLabelV1,
    DataQuality,
    LabelDirection,
    LabelAvailability,
    Interval,
    make_window_id,
    make_label_id,
    utc_now,
)


# Default window specification
DEFAULT_WINDOW_SPEC = {
    "pre": {
        "24h": 24 * 3600,
        "4h": 4 * 3600,
        "1h": 3600,
        "30m": 1800,
        "15m": 900,
        "5m": 300,
    },
    "post": {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 4 * 3600,
        "24h": 24 * 3600,
    },
}


# Direction epsilon thresholds (version 1.0.0)
DIRECTION_EPSILON = {
    "crypto_1m": 0.0001,
    "crypto_5m": 0.0002,
    "crypto_15m": 0.0003,
    "crypto_30m": 0.0005,
    "crypto_1h": 0.001,
    "crypto_4h": 0.002,
    "crypto_1d": 0.003,
    "daily_cross_asset": 0.001,
}

CALCULATION_VERSION = "1.0.0"


def load_bars_index(bars_path: str | Path) -> dict[str, list[dict]]:
    """Load bars from JSONL file, grouped by instrument_id+interval."""
    bars_path = Path(bars_path)
    index: dict[str, list[dict]] = {}

    if not bars_path.exists():
        return index

    open_func = gzip.open if str(bars_path).endswith(".gz") else open
    with open_func(bars_path, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            key = f"{d.get('instrument_id', '')}|{d.get('interval', '')}"
            if key not in index:
                index[key] = []
            index[key].append(d)

    # Sort each list by open_time_utc
    for key in index:
        index[key].sort(key=lambda x: x.get("open_time_utc", ""))

    return index


def parse_time(time_str: str) -> datetime:
    """Parse ISO-8601 UTC string to datetime."""
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))


def find_bar_at_time(bars: list[dict], target_time: datetime) -> Optional[dict]:
    """Find bar that contains the target time."""
    for bar in bars:
        ot = parse_time(bar["open_time_utc"])
        ct = parse_time(bar.get("close_time_utc", bar["open_time_utc"]))
        if ot <= target_time <= ct:
            return bar
        if ot > target_time:
            break
    return None


def find_last_bar_before(bars: list[dict], target_time: datetime) -> Optional[dict]:
    """Find last bar fully before target_time."""
    last_bar = None
    for bar in bars:
        ct = parse_time(bar.get("close_time_utc", bar["open_time_utc"]))
        if ct < target_time:
            last_bar = bar
        else:
            break
    return last_bar


def find_bars_in_range(
    bars: list[dict],
    start_time: datetime,
    end_time: datetime,
) -> list[dict]:
    """Find all bars within [start_time, end_time] range."""
    result = []
    for bar in bars:
        ot = parse_time(bar["open_time_utc"])
        ct = parse_time(bar.get("close_time_utc", bar["open_time_utc"]))
        if ot >= start_time and ct <= end_time:
            result.append(bar)
        if ot > end_time:
            break
    return result


def compute_return(before_price: float, after_price: float) -> float:
    """Compute return between two prices."""
    if before_price == 0:
        return 0.0
    return (after_price / before_price) - 1.0


def compute_direction(return_val: float, epsilon: float) -> str:
    """Classify direction based on epsilon threshold."""
    if return_val > epsilon:
        return LabelDirection.POSITIVE.value
    elif return_val < -epsilon:
        return LabelDirection.NEGATIVE.value
    return LabelDirection.NEUTRAL.value


def compute_realized_vol(prices: list[float]) -> float:
    """Compute realized volatility (std of log returns)."""
    if len(prices) < 2:
        return 0.0
    import math
    log_returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            log_returns.append(math.log(prices[i] / prices[i - 1]))
    if len(log_returns) < 2:
        return 0.0
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
    return math.sqrt(variance)


def compute_volume_zscore(bars: list[dict], volume_key: str = "volume") -> float:
    """Compute z-score of the event bar volume relative to pre-window."""
    if len(bars) < 2:
        return 0.0
    volumes = [b.get(volume_key, 0) for b in bars[:-1]]
    if not volumes or all(v == 0 for v in volumes):
        return 0.0
    import math
    mean = sum(volumes) / len(volumes)
    if mean == 0:
        return 0.0
    variance = sum((v - mean) ** 2 for v in volumes) / len(volumes)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    event_volume = bars[-1].get(volume_key, 0)
    return (event_volume - mean) / std


def build_event_windows(
    events_path: str | Path,
    bars_index: dict[str, list[dict]],
    instruments: list[str],
    window_spec: Optional[dict] = None,
    output_dir: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Build event windows and reaction labels.

    Args:
        events_path: Path to Lane A macro events JSONL (or temporary sample)
        bars_index: Pre-loaded bars index from load_bars_index()
        instruments: List of instrument_ids to process
        window_spec: Dict with 'pre' and 'post' horizon definitions
        output_dir: Optional output directory for writing results

    Returns:
        Dict with counts of windows and labels built
    """
    if window_spec is None:
        window_spec = DEFAULT_WINDOW_SPEC

    events_path = Path(events_path)
    if not events_path.exists():
        return {"success": False, "error": f"Events file not found: {events_path}"}

    # Load events
    events: list[dict] = []
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    windows: list[EventMarketWindowV1] = []
    labels: list[MarketReactionLabelV1] = []
    matrix_rows: list[dict] = []

    for event in events:
        event_id = event.get("event_id", "")
        event_family = event.get("event_family", event.get("event_type", "unknown"))
        event_time_str = event.get("actual_release_at_utc", event.get("event_time_utc", ""))
        if not event_time_str:
            # Try first_seen_at
            event_time_str = event.get("first_seen_at_utc", "")
        if not event_time_str:
            continue

        try:
            event_time = parse_time(event_time_str)
        except (ValueError, TypeError):
            continue

        for instrument_id in instruments:
            # Determine best interval based on instrument
            if "crypto" in instrument_id:
                bar_intervals = ["5m", "15m", "1h", "1d"]
            else:
                bar_intervals = ["1d"]

            for bar_interval in bar_intervals:
                bars_key = f"{instrument_id}|{bar_interval}"
                bars = bars_index.get(bars_key, [])

                if not bars:
                    continue

                # Find pre-event reference bar (last bar before event)
                ref_bar = find_last_bar_before(bars, event_time)
                event_bar = find_bar_at_time(bars, event_time)

                if not ref_bar:
                    continue

                # Calculate pre and post window bounds
                pre_seconds = 24 * 3600  # default pre-window
                post_seconds = 24 * 3600  # default post-window

                pre_window_start = event_time - timedelta(seconds=pre_seconds)
                post_window_end = event_time + timedelta(seconds=post_seconds)

                # Find bars in range
                pre_bars = find_bars_in_range(bars, pre_window_start, event_time)
                post_bars = find_bars_in_range(bars, event_time, post_window_end)

                bars_expected = (pre_seconds + post_seconds) // _interval_seconds(bar_interval)
                bars_present = len(pre_bars) + len(post_bars)

                pre_ref_price = ref_bar.get("close", 0)

                window_id = make_window_id(
                    event_id, instrument_id, event_time_str, bar_interval
                )

                window = EventMarketWindowV1(
                    window_id=window_id,
                    event_id=event_id,
                    event_family=event_family,
                    event_time_utc=event_time_str,
                    instrument_id=instrument_id,
                    pre_window_start_utc=pre_window_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    post_window_end_utc=post_window_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    bar_interval=bar_interval,
                    bars_expected=bars_expected,
                    bars_present=bars_present,
                    coverage_ratio=bars_present / max(bars_expected, 1),
                    pre_event_reference_price=pre_ref_price,
                    event_bar_open=event_bar.get("open") if event_bar else None,
                    event_bar_close=event_bar.get("close") if event_bar else None,
                    data_quality=DataQuality.EXACT_PUBLIC_API.value
                    if bars_present > 0
                    else DataQuality.MISSING.value,
                )
                windows.append(window)

                label = _build_reaction_label(
                    event_id, instrument_id, event_time_str,
                    pre_ref_price, bars, event_time, bar_interval,
                    pre_bars, post_bars,
                )
                if label:
                    labels.append(label)

    result = {
        "success": True,
        "events_processed": len(events),
        "instruments": instruments,
        "windows_built": len(windows),
        "labels_built": len(labels),
    }

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        windows_path = output_dir / "event_market_windows_v1.jsonl.gz"
        with gzip.open(windows_path, "wt", encoding="utf-8") as f:
            for w in windows:
                f.write(json.dumps(w.to_json(), ensure_ascii=False) + "\n")
        labels_path = output_dir / "market_reaction_labels_v1.jsonl"
        with open(labels_path, "w", encoding="utf-8") as f:
            for l in labels:
                f.write(json.dumps(l.to_json(), ensure_ascii=False) + "\n")
        result["windows_path"] = str(windows_path)
        result["labels_path"] = str(labels_path)

    return result


def _build_reaction_label(
    event_id: str,
    instrument_id: str,
    event_time_str: str,
    pre_ref_price: float,
    all_bars: list[dict],
    event_time: datetime,
    interval: str,
    pre_bars: list[dict],
    post_bars: list[dict],
) -> Optional[MarketReactionLabelV1]:
    if pre_ref_price <= 0:
        return None

    horizon_seconds = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "1d": 86400,
    }

    returns = {}
    for horizon, seconds in horizon_seconds.items():
        target_time = event_time + timedelta(seconds=seconds)
        post_bar = find_bar_at_time(all_bars, target_time)
        if post_bar and post_bar.get("close", 0) > 0:
            returns[horizon] = compute_return(pre_ref_price, post_bar["close"])
        else:
            last_bar = find_last_bar_before(all_bars, target_time)
            if last_bar and last_bar.get("close", 0) > 0:
                returns[horizon] = compute_return(pre_ref_price, last_bar["close"])
            else:
                returns[horizon] = None

    pre_prices = [b.get("close", 0) for b in pre_bars if b.get("close", 0) > 0]
    post_prices = [b.get("close", 0) for b in post_bars if b.get("close", 0) > 0]
    vol_pre = compute_realized_vol(pre_prices) if len(pre_prices) >= 2 else None
    vol_post = compute_realized_vol(post_prices) if len(post_prices) >= 2 else None
    volume_z = compute_volume_zscore(post_bars) if post_bars else None

    def get_direction(horizon, eps_key):
        r = returns.get(horizon)
        if r is None:
            return LabelDirection.NEUTRAL.value
        eps = DIRECTION_EPSILON.get(eps_key, 0.001)
        return compute_direction(r, eps)

    direction_5m = get_direction("5m", "crypto_5m" if "crypto" in instrument_id else "daily_5m")
    direction_1h = get_direction("1h", "crypto_1h" if "crypto" in instrument_id else "daily_1h")
    direction_1d = get_direction("1d", "crypto_1d" if "crypto" in instrument_id else "daily_1d")

    available_returns = [v for v in returns.values() if v is not None]
    total_horizons = len(horizon_seconds)
    availability_ratio = len(available_returns) / total_horizons
    if availability_ratio >= 0.8:
        label_avail = LabelAvailability.FULL.value
    elif availability_ratio >= 0.3:
        label_avail = LabelAvailability.PARTIAL.value
    elif availability_ratio > 0:
        label_avail = LabelAvailability.MINIMAL.value
    else:
        label_avail = LabelAvailability.MISSING.value

    label_id = make_label_id(event_id, instrument_id, event_time_str, CALCULATION_VERSION)

    label = MarketReactionLabelV1(
        label_id=label_id,
        event_id=event_id,
        instrument_id=instrument_id,
        event_time_utc=event_time_str,
        return_1m=returns.get("1m"),
        return_5m=returns.get("5m"),
        return_15m=returns.get("15m"),
        return_30m=returns.get("30m"),
        return_1h=returns.get("1h"),
        return_4h=returns.get("4h"),
        return_1d=returns.get("1d"),
        realized_vol_pre_1h=vol_pre,
        realized_vol_post_1h=vol_post,
        volume_zscore=volume_z,
        direction_5m=direction_5m,
        direction_1h=direction_1h,
        direction_1d=direction_1d,
        label_availability=label_avail,
        data_quality=DataQuality.EXACT_PUBLIC_API.value
        if label_avail != LabelAvailability.MISSING.value
        else DataQuality.MISSING.value,
        calculation_version=CALCULATION_VERSION,
    )
    return label


def _interval_seconds(interval: str) -> int:
    mapping = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800,
    }
    return mapping.get(interval, 3600)
