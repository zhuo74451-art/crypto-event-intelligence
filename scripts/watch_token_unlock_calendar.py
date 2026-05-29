import argparse
from datetime import timedelta
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        dt_to_utc_iso,
        is_enabled,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        safe_float,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
    from utils.time_utils import parse_any_time_to_utc_iso
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        dt_to_utc_iso,
        is_enabled,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        safe_float,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
    from scripts.utils.time_utils import parse_any_time_to_utc_iso


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch local token unlock calendar rows and emit structured alerts.")
    parser.add_argument("--calendar", default=str(ROOT / "data" / "token_unlock_calendar.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_token_unlocks.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_token_unlock_watcher_summary.csv"))
    parser.add_argument("--horizon-hours", type=float, default=72)
    parser.add_argument("--min-unlock-pct", type=float, default=2.0)
    parser.add_argument("--min-amount-usd", type=float, default=10_000_000)
    parser.add_argument("--include-samples", default="false")
    return parser.parse_args()


def utc_iso_to_dt(value: str):
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    from datetime import datetime, timezone

    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def alert_row(row: dict, unlock_time_utc: str) -> dict:
    asset = str(row.get("asset_symbol", "") or "").strip().upper()
    unlock_id = str(row.get("unlock_id", "") or "").strip() or make_dedupe_key(asset, unlock_time_utc, row.get("unlock_name", ""))
    amount_usd = safe_float(row.get("unlock_amount_usd"))
    pct = safe_float(row.get("unlock_pct_circulating"))
    observed = dt_to_utc_iso(now_utc())
    item = {column: "" for column in ALERT_COLUMNS}
    item.update(
        {
            "alert_id": make_alert_id("token_unlock_calendar", unlock_id, asset, unlock_time_utc),
            "observed_at_utc": observed,
            "observed_at_china": utc_iso_to_china(observed),
            "source_type": "first_hand",
            "watcher_source": "token_unlock_calendar",
            "blockchain": "calendar",
            "primary_entity": str(row.get("source", "") or "Token Unlock Calendar").strip(),
            "primary_address": unlock_id,
            "counterparty_entity": "scheduled_unlock",
            "counterparty_address": unlock_time_utc,
            "asset_symbol": asset,
            "amount_native": str(pct),
            "amount_usd": f"{amount_usd:.2f}",
            "metric_type": "token_unlock_upcoming",
            "metric_value": f"{pct:.4f}",
            "metric_change_pct": "",
            "event_type_l1": "token_unlock",
            "event_type_l2": "scheduled_token_unlock",
            "risk_category": "supply_event",
            "confidence": "medium",
            "relevance_score": "0.82" if pct >= 2 else "0.65",
            "threshold_rule": "unlock_pct>=min_unlock_pct or amount_usd>=min_amount_usd",
            "dedupe_key": make_dedupe_key("token_unlock_calendar", unlock_id, asset, unlock_time_utc),
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "ok",
            "raw_json": json_dumps({**row, "unlock_time_utc": unlock_time_utc}),
        }
    )
    return item


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def is_sample_row(row: dict) -> bool:
    text = " ".join(
        [
            str(row.get("unlock_id", "") or ""),
            str(row.get("unlock_name", "") or ""),
            str(row.get("source", "") or ""),
            str(row.get("notes", "") or ""),
        ]
    ).lower()
    return "sample" in text or "replace or extend" in text or "template" in text


def main() -> int:
    args = parse_args()
    rows = [row for row in read_csv_rows(normalize_path(args.calendar)) if is_enabled(row)]
    current = now_utc()
    horizon = current + timedelta(hours=args.horizon_hours)
    alerts = []
    skipped = 0
    bad_time = 0
    sample_skipped = 0
    for row in rows:
        if is_sample_row(row) and not truthy(args.include_samples):
            sample_skipped += 1
            continue
        unlock_time_utc = parse_any_time_to_utc_iso(row.get("unlock_time_utc", ""))
        unlock_dt = utc_iso_to_dt(unlock_time_utc)
        if not unlock_dt:
            bad_time += 1
            continue
        if not (current <= unlock_dt <= horizon):
            skipped += 1
            continue
        amount_usd = safe_float(row.get("unlock_amount_usd"))
        pct = safe_float(row.get("unlock_pct_circulating"))
        if amount_usd < args.min_amount_usd and pct < args.min_unlock_pct:
            skipped += 1
            continue
        alerts.append(alert_row(row, unlock_time_utc))

    output_path = normalize_path(args.output)
    write_csv_rows(output_path, alerts, ALERT_COLUMNS)
    summary = {
        "watcher": "token_unlock_calendar",
        "calendar_rows": len(rows),
        "alert_rows": len(alerts),
        "skipped_rows": skipped,
        "sample_skipped_rows": sample_skipped,
        "bad_time_rows": bad_time,
        "horizon_hours": args.horizon_hours,
        "min_unlock_pct": args.min_unlock_pct,
        "min_amount_usd": args.min_amount_usd,
        "status": "pass",
        "output": str(output_path),
    }
    write_summary(normalize_path(args.summary), summary)
    print(f"token_unlock_alert_rows={len(alerts)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
