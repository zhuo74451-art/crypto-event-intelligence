"""
Build unified raw_signals.csv from existing data sources.

Sources:
  - watcher_events_raw.csv  (first-hand onchain/liquidation/whale events)
  - hyperliquid_position_state.csv  (monitored position liquidation risk)
  - v15_percentile_alerts.json  (market state: funding/OI/price percentiles)
  - v14_market_state_snapshot.csv  (market: price/volume/OI/funding snapshots)
  - tg_drafts_v09_routed.csv  (news/flash drafts already routed)
  - tg_drafts_v07_watcher_private_pilot.csv  (watcher drafts)

Output: data/raw_signals.csv
"""

import csv
import json
import math
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

CSV_COLUMNS = [
    "signal_id", "source_type", "source_name", "timestamp_utc", "timestamp_china",
    "asset", "signal_category", "signal_type", "direction", "magnitude",
    "confidence", "is_first_hand", "latency_seconds", "entity", "chain",
    "title", "content_text", "raw_data", "created_at",
]

NOW_UTC = datetime.now(timezone.utc).replace(microsecond=0)
NOW_CHINA = (NOW_UTC.astimezone(CN_TZ)).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def safe_float(value: Any) -> float:
    try:
        return float(str(value or "").replace(",", "").strip())
    except Exception:
        return 0.0


def safe_strength(value: Any, scale: float = 1.0, cap: float = 100.0) -> float:
    """Map a numeric value to [0, cap] using smooth log1p scaling.

    Uses log1p over the full range to produce a gradual curve:
    - Small inputs stay low (single-digit anomalies → strength 20-30)
    - Medium inputs grow smoothly (multi-sigma → strength 50-70)
    - Extreme inputs approach cap without sudden saturation
    - Guaranteed output: [0, cap]
    - NaN/Inf/None/empty → 0
    """
    try:
        v = safe_float(value)
    except Exception:
        return 0.0
    if math.isnan(v) or math.isinf(v):
        return 0.0
    if v == 0:
        return 0.0

    raw = abs(v) * scale
    # Reference: log1p(100 * scale) maps to ~85% of cap
    # This gives a smooth curve — no sudden jump at any threshold
    ref = math.log1p(100.0 * scale)
    score = math.log1p(raw) / max(ref, 1.0) * (cap * 0.85)
    return round(min(cap, max(0.0, score)), 1)


def utc_stamp(value: Any) -> str:
    if not value:
        return NOW_UTC.strftime("%Y-%m-%d %H:%M:%S")
    return str(value).strip()


def china_from_utc(utc_str: str) -> str:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S+00:00", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(utc_str.replace("Z", ""), fmt)
            return dt.replace(tzinfo=timezone.utc).astimezone(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
        except ValueError:
            continue
    return utc_str


def is_china_ts(value: str) -> bool:
    return "UTC+8" in str(value) or "+08:00" in str(value)


def to_utc(value: str) -> str:
    """Normalize a timestamp string to UTC."""
    if not value:
        return NOW_UTC.strftime("%Y-%m-%d %H:%M:%S")
    s = str(value).strip()
    if "UTC+8" in s or "+08:00" in s:
        try:
            base = s.replace(" UTC+8", "").replace("+08:00", "")
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(base, fmt).replace(tzinfo=CN_TZ)
                    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
        except Exception:
            pass
    return s


def shorten(value: str, max_len: int = 300) -> str:
    if not value:
        return ""
    return str(value)[:max_len]


def uid() -> str:
    return uuid.uuid4().hex[:16]


def build_from_watcher_events(signals: list[dict]) -> list[dict]:
    """Convert watcher_events_raw.csv into raw signals."""
    path = ROOT / "data" / "watcher_events_raw.csv"
    rows = read_rows(path)
    added = 0
    for row in rows:
        ts_china = row.get("event_time_china") or row.get("event_time", "")
        ts_utc = to_utc(ts_china) if is_china_ts(ts_china) else ts_china

        source_type = "news"
        raw_type = str(row.get("raw_signal_type", "")).lower()
        watcher_src = str(row.get("watcher_source", "")).lower()

        if "hyperliquid" in raw_type or "hyperliquid" in watcher_src:
            source_type = "hyperliquid"
        elif "onchain" in raw_type or "transfer" in raw_type or "address" in watcher_src:
            source_type = "onchain_flow"
        elif "funding" in raw_type:
            source_type = "market"
        elif "whale" in raw_type:
            source_type = "whale_position"

        category = str(row.get("event_type_l2", row.get("event_type", ""))).strip()
        direction_map = {"long": "up", "short": "down", "inflow": "crowded", "outflow": "crowded"}
        direction = direction_map.get(str(row.get("direction_hint", "")).lower(), "neutral")

        sig = {
            "signal_id": f"watcher_{row.get('event_id', uid())}",
            "source_type": source_type,
            "source_name": str(row.get("watcher_source", row.get("source", "")))[:80],
            "timestamp_utc": ts_utc,
            "timestamp_china": ts_china,
            "asset": str(row.get("asset_symbol", row.get("signal_asset_symbol", ""))).upper()[:20],
            "signal_category": category if category else "news_flash",
            "signal_type": str(row.get("raw_signal_type", row.get("event_type", "")))[:80],
            "direction": direction,
            "magnitude": safe_strength(row.get("importance", 50), scale=1.0),
            "confidence": min(1.0, max(0, safe_float(row.get("confidence", 0.5)))),
            "is_first_hand": str(row.get("source", "")).startswith("first_hand") or source_type in ("whale_position", "onchain_flow", "hyperliquid"),
            "latency_seconds": 0,
            "entity": str(row.get("entity_label", ""))[:80],
            "chain": str(row.get("blockchain", ""))[:40] if row.get("blockchain") else "",
            "title": shorten(row.get("title", ""), 200),
            "content_text": shorten(row.get("content", row.get("draft_text", "")), 500),
            "raw_data": shorten(row.get("raw_json", ""), 500),
            "created_at": NOW_CHINA,
        }
        signals.append(sig)
        added += 1
    print(f"  watcher_events: {added} signals")
    return signals


def build_from_hyperliquid_positions(signals: list[dict]) -> list[dict]:
    """Convert hyperliquid_position_state.csv into monitored_liquidation_risk signals."""
    path = ROOT / "data" / "hyperliquid_position_state.csv"
    rows = read_rows(path)
    added = 0
    for row in rows:
        asset = str(row.get("asset_symbol", "")).upper()
        if not asset:
            continue
        entity = str(row.get("entity", row.get("address", "")))[:80]
        side = str(row.get("side", "")).lower()
        distance_pct = safe_float(row.get("liquidation_distance_pct")) * 100
        value_usd = safe_float(row.get("position_value_usd"))
        near = str(row.get("near_liquidation", "")).strip().lower()

        if distance_pct <= 5:
            urgency_label = "high"
            mag = 90
        elif distance_pct <= 10:
            urgency_label = "medium"
            mag = 60
        elif distance_pct <= 15:
            urgency_label = "low"
            mag = 30
        else:
            urgency_label = "review"
            mag = 10

        sig = {
            "signal_id": f"hl_pos_{row.get('position_key', uid())}",
            "source_type": "hyperliquid",
            "source_name": "hyperliquid_monitored_position",
            "timestamp_utc": utc_stamp(row.get("updated_at_utc", "")),
            "timestamp_china": row.get("updated_at_china", ""),
            "asset": asset,
            "signal_category": "monitored_liquidation_risk",
            "signal_type": f"monitored_position_{side}_{urgency_label}_risk",
            "direction": "risk_down" if side == "long" else "risk_up",
            "magnitude": mag,
            "confidence": 0.85,
            "is_first_hand": True,
            "latency_seconds": 0,
            "entity": entity,
            "chain": "",
            "title": f"监控地址清算风险 | {entity} {asset} {side} 仓位 {value_usd:,.0f}USD 距清算{distance_pct:.1f}%",
            "content_text": f"当前数据仅代表 watchlist 监控地址的清算风险，不代表全市场清算密集区。{entity} {asset} {side} 仓位价值 {value_usd:,.0f} USD，距清算价 {distance_pct:.1f}%。",
            "raw_data": shorten(str(row), 500),
            "created_at": NOW_CHINA,
        }
        signals.append(sig)
        added += 1
    print(f"  hyperliquid_positions: {added} signals")
    return signals


def build_from_percentile_alerts(signals: list[dict]) -> list[dict]:
    """Convert v15_percentile_alerts.json into market_state signals."""
    path = ROOT / "results" / "v15_percentile_alerts.json"
    if not path.exists():
        print("  percentile_alerts: file not found, skipping")
        return signals

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  percentile_alerts: JSON parse error: {e}")
        return signals

    added = 0
    for bucket in ("frontpage_alerts", "watchlist_alerts", "radar_triggers", "digest_context"):
        for item in data.get(bucket, []):
            asset = str(item.get("asset_symbol", "")).upper()
            if not asset:
                continue
            alert_type = str(item.get("alert_type", ""))
            percentile = safe_float(item.get("percentile", 0))
            cat = "market_state"
            if "funding" in alert_type:
                cat = "funding"
            elif "oi" in alert_type.lower() or "open_interest" in alert_type.lower():
                cat = "open_interest"

            if percentile > 90:
                direction = "crowded"
                mag = safe_strength(percentile, scale=1.0)
            elif percentile > 70:
                direction = "neutral"
                mag = 50
            else:
                direction = "neutral"
                mag = safe_strength(percentile, scale=0.5)

            sig = {
                "signal_id": f"pctl_{bucket}_{asset}_{alert_type}_{uid()}",
                "source_type": "market",
                "source_name": "binance_derivatives_percentiles",
                "timestamp_utc": NOW_UTC.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp_china": NOW_CHINA,
                "asset": asset,
                "signal_category": cat,
                "signal_type": alert_type,
                "direction": direction,
                "magnitude": mag,
                "confidence": 0.7 if bucket in ("frontpage_alerts", "radar_triggers") else 0.5,
                "is_first_hand": False,
                "latency_seconds": 0,
                "entity": "",
                "chain": "",
                "title": f"{asset} {alert_type} 分位 {percentile:.1f}% | {item.get('interpretation', '')}",
                "content_text": shorten(item.get("reason", item.get("interpretation", "")), 500),
                "raw_data": shorten(json.dumps(item, ensure_ascii=False), 500),
                "created_at": NOW_CHINA,
            }
            signals.append(sig)
            added += 1
    print(f"  percentile_alerts: {added} signals")
    return signals


def build_from_market_state_snapshot(signals: list[dict]) -> list[dict]:
    """Convert v14_market_state_snapshot.csv into market/price/oi/volume signals."""
    path = ROOT / "results" / "v14_market_state_snapshot.csv"
    rows = read_rows(path)
    added = 0
    for row in rows:
        asset = str(row.get("asset_symbol", "")).upper()
        if not asset:
            continue
        ts_utc = utc_stamp(row.get("observed_at_utc", ""))
        ts_china = row.get("observed_at_china", "")

        # Volume field source: use 1h percentage change (matching price/OI pct-based metrics).
        # Fallback priority:
        #   1. quote_volume_change_pct_1h (percentage, preferred — avoids raw-USD scale mismatch)
        #   2. volume_change_pct_24h (alternative pct column, if available)
        #   3. Falls back to 0 if neither exists (volume signal is skipped at abs(val) < 0.01)
        # Verified 2026-05-29 snapshot: quote_volume_change_pct_1h has real values for all 7 assets.
        volume_val = safe_float(row.get("quote_volume_change_pct_1h",
                            row.get("volume_change_pct_24h", 0)))

        metrics: list[tuple[str, str, float, float]] = [
            # (category, signal_type, raw_value, scale)
            ("price", "price_change_pct_24h", safe_float(row.get("price_change_pct_24h", 0)), 5.0),
            ("volume", "volume_change_pct_1h", volume_val, 5.0),
            ("open_interest", "open_interest_change_pct_24h", safe_float(row.get("open_interest_change_pct_24h", 0)), 5.0),
        ]

        for cat, stype, val, scale in metrics:
            if abs(val) < 0.01:
                continue
            direction = "neutral"
            if cat == "price" and val > 2:
                direction = "up"
            elif cat == "price" and val < -2:
                direction = "down"
            elif cat == "open_interest" and val > 5:
                direction = "crowded"
            mag = safe_strength(val, scale=scale)
            sig = {
                "signal_id": f"market_{asset}_{cat}_{uid()}",
                "source_type": "market",
                "source_name": "binance_spot_futures",
                "timestamp_utc": ts_utc,
                "timestamp_china": ts_china,
                "asset": asset,
                "signal_category": cat,
                "signal_type": stype,
                "direction": direction,
                "magnitude": mag,
                "confidence": 0.6,
                "is_first_hand": False,
                "latency_seconds": 0,
                "entity": "",
                "chain": "",
                "title": f"{asset} {cat} 24h变化 {val:+.2f}%",
                "content_text": shorten(str(row.get("market_state_reason", "")), 500),
                "raw_data": "",
                "created_at": NOW_CHINA,
            }
            signals.append(sig)
            added += 1
    print(f"  market_state_snapshot: {added} signals")
    return signals


def build_from_news_drafts(signals: list[dict]) -> list[dict]:
    """Convert tg_drafts_v09_routed.csv into news_flash signals."""
    for fname in ("tg_drafts_v09_routed.csv", "tg_drafts_v07_watcher_private_pilot.csv"):
        path = ROOT / "data" / fname
        if not path.exists():
            print(f"  {fname}: not found, skipping")
            continue
        rows = read_rows(path)
        added = 0
        for row in rows:
            asset = str(row.get("asset_symbol", "")).upper()
            if not asset:
                continue
            conf = {"高": 0.85, "中": 0.6, "低": 0.3}.get(
                str(row.get("confidence_label", "")).strip(), 0.5
            )
            sig = {
                "signal_id": f"news_{row.get('draft_id', uid())}",
                "source_type": "news",
                "source_name": str(row.get("source", "unknown"))[:80],
                "timestamp_utc": utc_stamp(row.get("published_at_china", "")),
                "timestamp_china": str(row.get("published_at_china", "")),
                "asset": asset,
                "signal_category": "news_flash",
                "signal_type": str(row.get("event_type", row.get("raw_signal_type", "")))[:80],
                "direction": "unknown",
                "magnitude": safe_strength(row.get("alert_priority_score", 50), scale=1.0),
                "confidence": conf,
                "is_first_hand": str(row.get("source", "")).startswith("first_hand"),
                "latency_seconds": 0,
                "entity": "",
                "chain": "",
                "title": shorten(row.get("title", ""), 200),
                "content_text": shorten(row.get("draft_text", row.get("content_summary", "")), 500),
                "raw_data": "",
                "created_at": NOW_CHINA,
            }
            signals.append(sig)
            added += 1
        print(f"  {fname}: {added} signals")
    return signals


def main(limit: int | None = None, output: str | None = None) -> None:
    # Determine output path
    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
    elif limit is not None and limit > 0:
        # --limit without --output → use smoke test file, protect production
        output_path = ROOT / "data" / "raw_signals_smoke_test.csv"
        print(f"  --limit mode: output will go to {output_path}")
        print(f"  (use --output data/raw_signals.csv to override)")
    else:
        output_path = ROOT / "data" / "raw_signals.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    signals: list[dict] = []
    print("[1/5] Extracting watcher events...")
    build_from_watcher_events(signals)
    print("[2/5] Extracting hyperliquid positions (monitored liquidation risk)...")
    build_from_hyperliquid_positions(signals)
    print("[3/5] Extracting percentile alerts...")
    build_from_percentile_alerts(signals)
    print("[4/5] Extracting market state snapshots...")
    build_from_market_state_snapshot(signals)
    print("[5/5] Extracting news drafts...")
    build_from_news_drafts(signals)

    # Apply --limit before writing
    if limit is not None and limit > 0:
        signals = signals[:limit]
        print(f"\n  --limit {limit}: using first {len(signals)} signals only")

    with output_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(signals)

    # Summary
    from collections import Counter
    src_counts = Counter(s["source_type"] for s in signals)
    cat_counts = Counter(s["signal_category"] for s in signals)
    first_hand = sum(1 for s in signals if s["is_first_hand"])

    print(f"\n--- raw_signals build summary ---")
    print(f"  Total signals: {len(signals)}")
    print(f"  First-hand signals: {first_hand}")
    print(f"  By source_type: {dict(src_counts)}")
    print(f"  By signal_category: {dict(cat_counts)}")
    print(f"  Output: {output_path}")

    # --- Smoke test output: first 5 rows with key fields ---
    print(f"\n--- SMOKE TEST: first {min(5, len(signals))} signals ---")
    print(f"{'asset':<8} {'category':<30} {'strength':>8} {'conf':>6} {'ts_china':<24} {'first_hand':>10}")
    print("-" * 96)
    for s in signals[:5]:
        print(f"{s['asset']:<8} {s['signal_category']:<30} {s['magnitude']:>8} {s['confidence']:>6} {s['timestamp_china']:<24} {str(s['is_first_hand']):>10}")

    # Verify all strength values are in [0, 100]
    bad_strengths = [s for s in signals if safe_float(s["magnitude"]) < 0 or safe_float(s["magnitude"]) > 100]
    if bad_strengths:
        print(f"\n  *** WARNING: {len(bad_strengths)} signals with strength outside [0,100]!")
        for bs in bad_strengths[:5]:
            print(f"    signal_id={bs['signal_id']} magnitude={bs['magnitude']}")
    else:
        print(f"\n  All {len(signals)} signals: strength in [0, 100] OK")

    # Extreme value test: verify safe_strength handles absurd inputs
    print(f"\n--- EXTREME VALUE TEST ---")
    extreme_tests = [0, 1, 50, 100, 1000, 1e6, 1e9, -999, None, "abc", float('nan'), float('inf')]
    for tv in extreme_tests:
        result = safe_strength(tv, scale=5.0)
        status = "OK" if 0 <= result <= 100 else "FAIL"
        print(f"  safe_strength({tv!r}, scale=5.0) = {result}  {status}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build raw_signals.csv from existing data sources.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit output to first N signals (smoke test mode). "
                             "When used without --output, writes to data/raw_signals_smoke_test.csv")
    parser.add_argument("--output", type=str, default=None,
                        help="Custom output path (default: data/raw_signals.csv; "
                             "with --limit without --output: data/raw_signals_smoke_test.csv)")
    args = parser.parse_args()
    main(limit=args.limit, output=args.output)
