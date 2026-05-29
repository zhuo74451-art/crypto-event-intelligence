"""
Aggregate raw_signals into aggregated_events based on:
  - Same asset
  - 30-minute time window
  - Similar signal_category / signal_type
  - Multiple signals merged into one event
  - First-hand signals weighted higher than news
  - Duplicate news only adds supplementary evidence

Input:  data/raw_signals.csv
Output: data/aggregated_events.csv
"""

import csv
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))
WINDOW_MINUTES = 30

EVENT_COLUMNS = [
    "event_id", "asset", "event_start_time", "event_end_time", "signal_ids",
    "signal_count", "first_hand_count", "overall_strength", "overall_confidence",
    "novelty_score", "event_type", "urgency", "card_type",
    "sent_to_telegram", "title", "summary", "observation_points", "created_at",
]

NOW_UTC = datetime.now(timezone.utc).replace(microsecond=0)
NOW_CHINA = (NOW_UTC.astimezone(CN_TZ)).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def safe_float(value: Any) -> float:
    try:
        return float(str(value or "").replace(",", "").strip())
    except Exception:
        return 0.0


def parse_ts(ts_str: str) -> datetime | None:
    """Try to parse a timestamp string into a datetime (UTC)."""
    if not ts_str:
        return None
    s = str(ts_str).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S+00:00",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%SZ",
    ):
        try:
            dt = datetime.strptime(s.replace(" UTC+8", "").replace("+08:00", "").replace("Z", "").replace(" UTC", ""), fmt)
            if "UTC+8" in ts_str or "+08:00" in ts_str:
                return dt.replace(tzinfo=CN_TZ).astimezone(timezone.utc)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def uid() -> str:
    return uuid.uuid4().hex[:12]


def hash_ids(ids: list[str]) -> str:
    return uuid.uuid5(uuid.NAMESPACE_DNS, ",".join(sorted(ids))).hex[:12]


def category_compatible(c1: str, c2: str) -> bool:
    """Check if two signal categories can be merged."""
    same = {
        "news_flash-news_flash": True,
        "monitored_liquidation_risk-monitored_liquidation_risk": True,
        "market_state-funding": True,
        "market_state-open_interest": True,
        "market_state-price": True,
        "market_state-volume": True,
        "funding-open_interest": True,
        "funding-price": True,
        "price-volume": True,
        "price-open_interest": True,
        "volume-open_interest": True,
        "onchain_flow-news_flash": True,
        "whale_position-monitored_liquidation_risk": True,
        "whale_position-open_interest": True,
        "whale_position-volume": True,
    }
    if c1 == c2:
        return True
    key = f"{c1}-{c2}" if c1 < c2 else f"{c2}-{c1}"
    return same.get(key, False)


def derive_event_type(signals: list[dict]) -> str:
    cats = set(s["signal_category"] for s in signals)
    if "monitored_liquidation_risk" in cats:
        return "monitored_liquidation_risk"
    if "whale_position" in cats:
        return "whale_position_change"
    if "onchain_flow" in cats and len(cats) >= 2:
        return "onchain_flow"
    if cats.intersection({"market_state", "funding", "open_interest", "price", "volume"}):
        return "market_state_change"
    if "news_flash" in cats and len(cats) >= 2:
        return "asset_multi_signal"
    if "news_flash" in cats:
        return "news_context"
    return "asset_multi_signal"


def derive_card_type(event_type: str, urgency: str, first_hand: int) -> str:
    if urgency == "high":
        return "intraday_radar"
    if event_type == "monitored_liquidation_risk":
        return "evening_digest"
    if event_type in ("market_state_change", "asset_multi_signal") and first_hand >= 2:
        return "evening_digest"
    if event_type in ("whale_position_change", "onchain_flow"):
        return "evening_digest"
    return "review_only"


def derive_urgency(event_type: str, strength: float, first_hand: int, signal_count: int) -> str:
    if event_type == "monitored_liquidation_risk" and strength > 70:
        return "high"
    if signal_count >= 3 and first_hand >= 2:
        return "high"
    if signal_count >= 2 and first_hand >= 1 and strength > 50:
        return "medium"
    if strength > 30:
        return "medium"
    return "review"


def build_observation_points(signals: list[dict], event_type: str) -> list[str]:
    points = []
    cats = set(s["signal_category"] for s in signals)
    assets = set(s["asset"] for s in signals)

    if "monitored_liquidation_risk" in cats:
        points.append("是否继续接近监控地址清算风险区")
    if cats.intersection({"funding", "open_interest"}):
        points.append("是否出现成交量放大或持仓量快速回落")
    if "whale_position" in cats:
        points.append("是否有新的链上或快讯信号确认")
    if "news_flash" in cats:
        points.append("是否有新的信息源交叉验证")
    if "price" in cats:
        points.append("价格是否持续朝同一方向运动")
    if event_type == "market_state_change" and len(cats) >= 3:
        points.append("多信号共振是否持续或反转")

    return points if points else ["需要继续确认"]


def main() -> None:
    input_path = ROOT / "data" / "raw_signals.csv"
    output_path = ROOT / "data" / "aggregated_events.csv"

    rows = read_rows(input_path)
    print(f"Loaded {len(rows)} raw signals")

    if not rows:
        print("No raw signals found, creating empty aggregated_events.csv")
        write_rows(output_path, [], EVENT_COLUMNS)
        return

    # Group signals by bucket (asset + 30-min window)
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    asset_index: dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        asset = str(row.get("asset", "")).upper()
        if not asset:
            asset = "UNKNOWN"
        asset_index[asset].append(row)
        ts = parse_ts(row.get("timestamp_utc", "")) or NOW_UTC
        window_key = ts.replace(minute=(ts.minute // WINDOW_MINUTES) * WINDOW_MINUTES, second=0, microsecond=0)
        cat = str(row.get("signal_category", ""))
        buckets[(asset, window_key, cat)].append(row)

    # Merge compatible categories within the same asset+window
    # Step 1: Start with category-based buckets
    # Step 2: Merge adjacent categories
    events: list[dict] = []
    merged_keys: set[str] = set()

    # Simplified approach: group all signals for same asset in same 30-min window
    asset_window: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        asset = str(row.get("asset", "")).upper() or "UNKNOWN"
        ts = parse_ts(row.get("timestamp_utc", "")) or NOW_UTC
        window_key = ts.replace(minute=(ts.minute // WINDOW_MINUTES) * WINDOW_MINUTES, second=0, microsecond=0)
        asset_window[(asset, window_key)].append(row)

    print(f"  Asset-window buckets: {len(asset_window)}")

    for (asset, window_start), sigs in asset_window.items():
        window_end = window_start + timedelta(minutes=WINDOW_MINUTES)

        # Split by signal_category compatibility
        clusters: list[list[dict]] = []
        remaining = list(sigs)
        while remaining:
            base = remaining.pop(0)
            cluster = [base]
            base_cat = str(base.get("signal_category", ""))
            compat_remaining = []
            for other in remaining:
                other_cat = str(other.get("signal_category", ""))
                if category_compatible(base_cat, other_cat):
                    cluster.append(other)
                else:
                    compat_remaining.append(other)
            remaining = compat_remaining
            clusters.append(cluster)

        for cluster in clusters:
            if len(cluster) < 1:
                continue

            sig_ids = [s["signal_id"] for s in cluster]
            fh_count = sum(1 for s in cluster if s.get("is_first_hand") in (True, "True", "true", "1"))
            mags = [safe_float(s["magnitude"]) for s in cluster]
            confs = [safe_float(s["confidence"]) for s in cluster]

            avg_mag = sum(mags) / len(mags)
            # First-hand bonus: +15 per first-hand signal
            fh_bonus = min(30, fh_count * 15)
            strength = min(100, avg_mag + fh_bonus)
            avg_conf = sum(confs) / len(confs)

            event_type = derive_event_type(cluster)
            urgency = derive_urgency(event_type, strength, fh_count, len(cluster))
            card_type = derive_card_type(event_type, urgency, fh_count)
            obs_points = build_observation_points(cluster, event_type)

            title_parts = []
            for s in cluster[:3]:
                t = str(s.get("title", ""))
                if t and t not in title_parts:
                    title_parts.append(t[:80])
            title = " | ".join(title_parts[:3]) if title_parts else f"{asset} 多信号事件"

            summary_cats = {s["signal_category"] for s in cluster}
            summary = f"{asset} 在 {window_start.strftime('%H:%M')}-{window_end.strftime('%H:%M')} UTC 内 "
            summary += f"共收到 {len(cluster)} 条信号（一手 {fh_count} 条）"
            summary += f"，涉及类型：{', '.join(sorted(summary_cats))}"

            event = {
                "event_id": hash_ids(sig_ids),
                "asset": asset,
                "event_start_time": window_start.strftime("%Y-%m-%d %H:%M:%S"),
                "event_end_time": window_end.strftime("%Y-%m-%d %H:%M:%S"),
                "signal_ids": ";".join(sig_ids),
                "signal_count": len(cluster),
                "first_hand_count": fh_count,
                "overall_strength": round(strength, 1),
                "overall_confidence": round(avg_conf, 3),
                "novelty_score": round(min(1.0, fh_count * 0.3 + 0.2), 2),
                "event_type": event_type,
                "urgency": urgency,
                "card_type": card_type,
                "sent_to_telegram": "",
                "title": title,
                "summary": summary,
                "observation_points": "；".join(obs_points),
                "created_at": NOW_CHINA,
            }
            events.append(event)

    # Sort: priority assets first, then by strength descending
    priority = {"BTC": 0, "ETH": 1, "HYPE": 2, "SOL": 3, "BNB": 4}
    events.sort(key=lambda e: (
        priority.get(e["asset"], 99),
        -e["overall_strength"],
    ))

    write_rows(output_path, events, EVENT_COLUMNS)

    from collections import Counter
    type_counts = Counter(e["event_type"] for e in events)
    urgency_counts = Counter(e["urgency"] for e in events)
    review_only = sum(1 for e in events if e["card_type"] == "review_only")
    card_ready = sum(1 for e in events if e["card_type"] != "review_only")
    asset_count = len(set(e["asset"] for e in events))

    print(f"\n--- aggregation summary ---")
    print(f"  Aggregated events: {len(events)}")
    print(f"  Assets covered: {asset_count}")
    print(f"  Events ready for cards: {card_ready}")
    print(f"  Review-only events: {review_only}")
    print(f"  By event_type: {dict(type_counts)}")
    print(f"  By urgency: {dict(urgency_counts)}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
