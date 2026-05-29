import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso


ROOT = Path(__file__).resolve().parents[1]
HORIZONS = ["t0", "1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit event, source, backtest, and price kline time provenance.")
    parser.add_argument("--candidates", default="")
    parser.add_argument("--backfill", default="")
    parser.add_argument("--output", default=str(ROOT / "results" / "event_time_provenance_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "event_time_provenance_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def is_blank(value) -> bool:
    return pd.isna(value) or str(value).strip() == ""


def has_explicit_timezone(value: str) -> bool:
    raw = str(value).strip()
    if not raw:
        return False
    if raw.endswith("Z") or "UTC" in raw.upper() or "GMT" in raw.upper():
        return True
    tail = raw[-6:]
    return len(tail) == 6 and tail[0] in {"+", "-"} and tail[3] == ":"


def iso_to_dt(value: str):
    value = str(value).strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def seconds_between(left_iso: str, right_iso: str):
    left = iso_to_dt(left_iso)
    right = iso_to_dt(right_iso)
    if left is None or right is None:
        return ""
    return round((left - right).total_seconds(), 3)


def add_flag(flags: list[str], flag: str) -> None:
    if flag and flag not in flags:
        flags.append(flag)


def audit_candidates(path: Path) -> list[dict]:
    if not path or not path.exists():
        return []
    df = pd.read_csv(path, dtype=str).fillna("")
    rows = []
    now = datetime.now(timezone.utc)
    for _, row in df.iterrows():
        flags: list[str] = []
        raw_published = str(row.get("raw_published_at", "") or row.get("published_at", "")).strip()
        published_utc = str(row.get("published_at_utc", "")).strip() or parse_any_time_to_utc_iso(raw_published)
        published_china = str(row.get("published_at_china", "")).strip() or utc_iso_to_china_iso(published_utc)
        backtest_utc = str(row.get("backtest_time_utc", "")).strip() or parse_any_time_to_utc_iso(row.get("backtest_time", ""))
        backtest_china = str(row.get("backtest_time_china", "")).strip() or utc_iso_to_china_iso(backtest_utc)
        source_utc = str(row.get("source_published_at_utc", "")).strip()
        source_china = str(row.get("source_published_at_china", "")).strip() or utc_iso_to_china_iso(source_utc)
        source_timezone = str(row.get("source_timezone", "")).strip()
        source_timezone_assumption = str(row.get("source_timezone_assumption", "")).strip()

        if raw_published and not has_explicit_timezone(raw_published):
            add_flag(flags, "published_at_timezone_assumed_china")
        if str(row.get("raw_source_published_at", "")).strip() and not has_explicit_timezone(row.get("raw_source_published_at", "")):
            add_flag(flags, "source_published_at_timezone_assumed")
        if not published_utc:
            add_flag(flags, "published_at_parse_failed")
        if not backtest_utc:
            add_flag(flags, "backtest_time_parse_failed")
        published_dt = iso_to_dt(published_utc)
        if published_dt and published_dt > now:
            add_flag(flags, "future_published_at")
        backtest_dt = iso_to_dt(backtest_utc)
        if backtest_dt and backtest_dt > now:
            add_flag(flags, "future_backtest_time")

        source_lag_minutes = ""
        if source_utc and published_utc:
            lag_seconds = seconds_between(published_utc, source_utc)
            if lag_seconds != "":
                source_lag_minutes = round(float(lag_seconds) / 60.0, 2)
                if abs(source_lag_minutes) > 30:
                    add_flag(flags, "source_lag_over_30m")
                if abs(source_lag_minutes) > 360:
                    add_flag(flags, "source_lag_over_6h")

        status = "fail" if any("failed" in flag or flag.startswith("future_") for flag in flags) else ("warning" if flags else "pass")
        rows.append(
            {
                "record_type": "candidate",
                "record_id": row.get("candidate_id", "") or row.get("raw_id", ""),
                "title": row.get("title", ""),
                "raw_published_at": raw_published,
                "published_at_utc": published_utc,
                "published_at_china": published_china,
                "raw_source_published_at": row.get("raw_source_published_at", ""),
                "source_published_at_utc": source_utc,
                "source_published_at_china": source_china,
                "source_timezone": source_timezone,
                "source_timezone_assumption": source_timezone_assumption,
                "source_lag_minutes": source_lag_minutes,
                "backtest_time_basis": row.get("backtest_time_basis", ""),
                "backtest_time_utc": backtest_utc,
                "backtest_time_china": backtest_china,
                "price_target_utc": "",
                "price_target_china": "",
                "price_kline_time_utc": "",
                "price_kline_time_china": "",
                "price_time_lag_seconds": "",
                "time_audit_status": status,
                "time_audit_flags": ",".join(flags),
            }
        )
    return rows


def audit_backfill(path: Path) -> list[dict]:
    if not path or not path.exists():
        return []
    df = pd.read_csv(path, dtype=str).fillna("")
    rows = []
    for _, row in df.iterrows():
        event_utc = str(row.get("event_time_utc", "")).strip() or parse_any_time_to_utc_iso(row.get("event_time", ""))
        event_china = str(row.get("event_time_china", "")).strip() or utc_iso_to_china_iso(event_utc)
        for asset_prefix in ["asset", "btc", "eth"]:
            for horizon in HORIZONS:
                target_utc = str(row.get(f"price_target_{horizon}_utc", "")).strip()
                target_china = str(row.get(f"price_target_{horizon}_china", "")).strip()
                kline_utc = str(row.get(f"{asset_prefix}_price_{horizon}_kline_time_utc", "")).strip()
                kline_china = str(row.get(f"{asset_prefix}_price_{horizon}_kline_time_china", "")).strip()
                if not target_utc and horizon == "t0":
                    target_utc = event_utc
                    target_china = event_china
                flags: list[str] = []
                lag_seconds = seconds_between(kline_utc, target_utc) if kline_utc and target_utc else ""
                if not target_utc:
                    add_flag(flags, "missing_price_target_time")
                if not kline_utc and not is_blank(row.get(f"{asset_prefix}_price_{horizon}", "")):
                    add_flag(flags, "missing_kline_time")
                if lag_seconds != "" and (float(lag_seconds) < 0 or float(lag_seconds) > 60):
                    add_flag(flags, "price_kline_lag_out_of_range")
                status = "warning" if flags else "pass"
                rows.append(
                    {
                        "record_type": f"backfill_{asset_prefix}_{horizon}",
                        "record_id": row.get("event_id", ""),
                        "title": row.get("title", ""),
                        "raw_published_at": row.get("event_time", ""),
                        "published_at_utc": event_utc,
                        "published_at_china": event_china,
                        "raw_source_published_at": "",
                        "source_published_at_utc": "",
                        "source_published_at_china": "",
                        "source_timezone": "",
                        "source_timezone_assumption": "",
                        "source_lag_minutes": "",
                        "backtest_time_basis": row.get("raw_backtest_mode", ""),
                        "backtest_time_utc": event_utc,
                        "backtest_time_china": event_china,
                        "price_target_utc": target_utc,
                        "price_target_china": target_china,
                        "price_kline_time_utc": kline_utc,
                        "price_kline_time_china": kline_china,
                        "price_time_lag_seconds": lag_seconds,
                        "time_audit_status": status,
                        "time_audit_flags": ",".join(flags),
                    }
                )
    return rows


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame([{"total_rows": 0}])
    status = df["time_audit_status"].value_counts().to_dict()
    flags = df["time_audit_flags"].fillna("").astype(str)
    return pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "pass_count": int(status.get("pass", 0)),
                "warning_count": int(status.get("warning", 0)),
                "fail_count": int(status.get("fail", 0)),
                "timezone_assumed_china_count": int(flags.str.contains("timezone_assumed_china").sum()),
                "source_lag_over_30m_count": int(flags.str.contains("source_lag_over_30m").sum()),
                "source_lag_over_6h_count": int(flags.str.contains("source_lag_over_6h").sum()),
                "source_timezone_assumed_count": int(flags.str.contains("source_published_at_timezone_assumed").sum()),
                "price_kline_lag_out_of_range_count": int(flags.str.contains("price_kline_lag_out_of_range").sum()),
            }
        ]
    )


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    rows: list[dict] = []
    if args.candidates:
        rows.extend(audit_candidates(normalize_path(args.candidates)))
    if args.backfill:
        rows.extend(audit_backfill(normalize_path(args.backfill)))
    if not rows:
        logging.error("no input rows audited; pass --candidates and/or --backfill")
        return 1

    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report = pd.DataFrame(rows)
    report.to_csv(output_path, index=False)
    build_summary(report).to_csv(summary_path, index=False)
    logging.info("wrote time provenance report to %s", output_path)
    logging.info("wrote time provenance summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
