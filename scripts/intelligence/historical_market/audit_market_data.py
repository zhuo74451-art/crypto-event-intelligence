"""Audit market data for quality violations."""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from market_radar.intelligence.acquisition.historical_market.contracts import validate_ohlc


def audit_market_data(
    bars_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Audit market bar data. Returns audit report."""
    bars_path = Path(bars_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    findings: dict[str, list[dict]] = {
        "duplicate_bar_ids": [],
        "duplicate_instrument_timestamp": [],
        "invalid_ohlc": [],
        "negative_price": [],
        "negative_volume": [],
        "interval_gap": [],
        "future_bar_used": [],
        "retrieval_time_before_bar_close": [],
        "source_hash_missing": [],
    }

    total_bars = 0
    seen_ids: dict[str, list[str]] = {}  # bar_id -> [lines]
    seen_ts: dict[str, dict[str, str]] = {}  # instrument_interval -> {timestamp: bar_id}

    now = datetime.now(timezone.utc)

    if not bars_path.exists():
        return {"success": False, "error": f"File not found: {bars_path}", "findings": findings}

    open_func = gzip.open if str(bars_path).endswith(".gz") else open
    with open_func(bars_path, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total_bars += 1
            d = json.loads(line)
            bar_id = d.get("bar_id", "")
            instrument = d.get("instrument_id", "")
            interval = d.get("interval", "")
            ts_key = d.get("open_time_utc", "")

            # Duplicate bar IDs
            if bar_id in seen_ids:
                findings["duplicate_bar_ids"].append({
                    "bar_id": bar_id,
                    "instrument": instrument,
                    "timestamp": ts_key,
                })
            seen_ids[bar_id] = seen_ids.get(bar_id, []) + [line]

            # Duplicate (instrument, timestamp)
            ts_check_key = f"{instrument}|{interval}"
            if ts_check_key not in seen_ts:
                seen_ts[ts_check_key] = {}
            if ts_key in seen_ts[ts_check_key]:
                findings["duplicate_instrument_timestamp"].append({
                    "bar_id": bar_id,
                    "instrument": instrument,
                    "interval": interval,
                    "timestamp": ts_key,
                    "existing_bar_id": seen_ts[ts_check_key][ts_key],
                })
            seen_ts[ts_check_key][ts_key] = bar_id

            # OHLC validation
            bar_for_check = type("Bar", (), {})()
            for field in ["open", "high", "low", "close", "volume"]:
                setattr(bar_for_check, field, d.get(field, 0))
            flags = validate_ohlc(bar_for_check)  # simplified check without full class
            # Manual OHLC check
            o, h, l_, c, v = d.get("open", 0), d.get("high", 0), d.get("low", 0), d.get("close", 0), d.get("volume", 0)
            ohlc_flags = []
            if o < 0: ohlc_flags.append("negative_open")
            if h < 0: ohlc_flags.append("negative_high")
            if l_ < 0: ohlc_flags.append("negative_low")
            if c < 0: ohlc_flags.append("negative_close")
            if v < 0: ohlc_flags.append("negative_volume")
            if h < l_ and h > 0 and l_ > 0: ohlc_flags.append("high_below_low")
            if h < o and h > 0: ohlc_flags.append("high_below_open")
            if h < c and h > 0: ohlc_flags.append("high_below_close")
            if l_ > o and l_ > 0: ohlc_flags.append("low_above_open")
            if l_ > c and l_ > 0: ohlc_flags.append("low_above_close")
            if o == 0 and h == 0 and l_ == 0 and c == 0: ohlc_flags.append("all_zero_price")

            for flag in ohlc_flags:
                if "negative" in flag:
                    findings["negative_price" if "open" in flag or "high" in flag or "low" in flag or "close" in flag else "negative_volume"].append({
                        "bar_id": bar_id,
                        "instrument": instrument,
                        "field": flag,
                    })

            if ohlc_flags:
                findings["invalid_ohlc"].append({
                    "bar_id": bar_id,
                    "instrument": instrument,
                    "flags": ohlc_flags,
                })

    # Interval gap detection (check consecutive bars)
    for key, bars_dict in seen_ts.items():
        sorted_ts = sorted(bars_dict.keys())
        if len(sorted_ts) < 2:
            continue
        parts = key.split("|")
        inst, interval = parts[0], parts[1] if len(parts) > 1 else "1h"
        interval_sec = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400}.get(interval, 3600)

        for i in range(1, len(sorted_ts)):
            try:
                t1 = datetime.fromisoformat(sorted_ts[i - 1].replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(sorted_ts[i].replace("Z", "+00:00"))
                diff = (t2 - t1).total_seconds()
                if diff > interval_sec * 2:  # More than 2x interval = gap
                    findings["interval_gap"].append({
                        "instrument": inst,
                        "interval": interval,
                        "from": sorted_ts[i - 1],
                        "to": sorted_ts[i],
                        "gap_seconds": diff,
                    })
            except (ValueError, TypeError):
                pass

    # Summary
    critical_count = (
        len(findings["duplicate_bar_ids"])
        + len(findings["duplicate_instrument_timestamp"])
        + len(findings["invalid_ohlc"])
    )

    report = {
        "success": True,
        "total_bars_audited": total_bars,
        "findings": {k: len(v) for k, v in findings.items()},
        "critical_error_count": critical_count,
        "detailed_findings": findings,
    }

    # Write reports
    report_json_path = output_dir / "reports" / "market_data_audit_v1.json"
    report_md_path = output_dir / "reports" / "market_data_audit_v1.md"

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Market Data Audit Report V1\n\n")
        f.write(f"Total bars audited: {total_bars}\n")
        f.write(f"Critical errors: {critical_count}\n\n")
        f.write("| Finding | Count |\n")
        f.write("|---------|-------|\n")
        for k, v in findings.items():
            f.write(f"| {k} | {len(v)} |\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars-path", default="data/intelligence/historical_market/normalized/market_bars_v1.jsonl.gz")
    parser.add_argument("--output-dir", default="data/intelligence/historical_market")
    args = parser.parse_args()

    report = audit_market_data(
        bars_path=args.bars_path,
        output_dir=args.output_dir,
    )
    print(json.dumps({k: v for k, v in report.items() if k != "detailed_findings"}, indent=2, default=str))
