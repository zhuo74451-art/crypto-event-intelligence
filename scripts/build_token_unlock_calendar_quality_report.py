import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate local token unlock calendar readiness.")
    parser.add_argument("--input", default=str(ROOT / "data" / "token_unlock_calendar.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v081_token_unlock_calendar_quality_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v081_token_unlock_calendar_quality_summary.csv"))
    parser.add_argument("--min-real-rows", type=int, default=20)
    parser.add_argument("--require-symbol-map", default="false")
    parser.add_argument("--require-amount-usd", default="false")
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_utc(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def safe_float(value) -> float:
    try:
        raw = str(value or "").strip()
        if raw == "":
            return 0.0
        return float(raw)
    except Exception:
        return 0.0


def is_enabled(row: dict) -> bool:
    return str(row.get("enabled", "true") or "true").strip().lower() in {"1", "true", "yes", "y"}


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def is_sample(row: dict) -> bool:
    text = " ".join(
        [
            str(row.get("unlock_id", "")),
            str(row.get("unlock_name", "")),
            str(row.get("source", "")),
            str(row.get("notes", "")),
        ]
    ).lower()
    return "sample" in text or "replace or extend" in text


def symbol_set(rows: list[dict]) -> set[str]:
    return {str(row.get("asset_symbol", "") or "").strip().upper() for row in rows if str(row.get("asset_symbol", "") or "").strip()}


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    symbols = symbol_set(read_rows(normalize_path(args.symbol_map)))
    require_symbol_map = truthy(args.require_symbol_map)
    require_amount_usd = truthy(args.require_amount_usd)
    now = datetime.now(timezone.utc)
    enabled = [row for row in rows if is_enabled(row)]
    real_rows = [row for row in enabled if not is_sample(row)]

    missing_symbol = 0
    unsupported_symbol = 0
    invalid_time = 0
    future_rows = 0
    missing_amount = 0
    missing_source = 0
    large_rows = 0
    upcoming_30d = 0

    detail_rows = []
    for row in enabled:
        symbol = str(row.get("asset_symbol", "") or "").strip().upper()
        dt = parse_utc(str(row.get("unlock_time_utc", "") or ""))
        amount = safe_float(row.get("unlock_amount_usd"))
        flags = []
        if not symbol:
            missing_symbol += 1
            flags.append("missing_symbol")
        elif require_symbol_map and symbol not in symbols:
            unsupported_symbol += 1
            flags.append("unsupported_symbol")
        elif symbol not in symbols:
            flags.append("not_in_symbol_map")
        if not dt:
            invalid_time += 1
            flags.append("invalid_unlock_time")
        else:
            if dt > now:
                future_rows += 1
                if (dt - now).days <= 30:
                    upcoming_30d += 1
            else:
                flags.append("past_unlock_time")
        if amount <= 0:
            missing_amount += 1
            flags.append("missing_amount_usd")
        if amount >= 50_000_000:
            large_rows += 1
        if not str(row.get("source", "") or "").strip():
            missing_source += 1
            flags.append("missing_source")
        if is_sample(row):
            flags.append("sample_row")
        detail_rows.append(
            {
                "unlock_id": row.get("unlock_id", ""),
                "asset_symbol": symbol,
                "unlock_time_utc": row.get("unlock_time_utc", ""),
                "unlock_amount_usd": row.get("unlock_amount_usd", ""),
                "source": row.get("source", ""),
                "quality_flags": ",".join(flags),
            }
        )

    ready = (
        len(real_rows) >= args.min_real_rows
        and invalid_time == 0
        and (unsupported_symbol == 0 or not require_symbol_map)
        and (missing_amount == 0 or not require_amount_usd)
        and missing_source == 0
    )
    status = "ready" if ready else "needs_data"
    summary = {
        "calendar_rows": len(rows),
        "enabled_rows": len(enabled),
        "real_rows": len(real_rows),
        "sample_rows": len(enabled) - len(real_rows),
        "future_rows": future_rows,
        "upcoming_30d_rows": upcoming_30d,
        "large_unlock_rows": large_rows,
        "missing_symbol_rows": missing_symbol,
        "unsupported_symbol_rows": unsupported_symbol,
        "invalid_time_rows": invalid_time,
        "missing_amount_rows": missing_amount,
        "missing_source_rows": missing_source,
        "min_real_rows": args.min_real_rows,
        "require_symbol_map": str(require_symbol_map).lower(),
        "require_amount_usd": str(require_amount_usd).lower(),
        "status": status,
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    preview = detail_rows[:30]
    lines = [
        "# v0.8.1 Token Unlock Calendar Quality Report",
        "",
        f"- status: {status}",
        f"- calendar_rows: {len(rows)}",
        f"- real_rows: {len(real_rows)}",
        f"- sample_rows: {len(enabled) - len(real_rows)}",
        f"- upcoming_30d_rows: {upcoming_30d}",
        f"- large_unlock_rows: {large_rows}",
        "",
        "## Blocking Issues",
        "",
        f"- real_rows below target: {len(real_rows)} / {args.min_real_rows}",
        f"- invalid_time_rows: {invalid_time}",
        f"- unsupported_symbol_rows: {unsupported_symbol}",
        f"- missing_amount_rows: {missing_amount}",
        f"- missing_source_rows: {missing_source}",
        f"- require_symbol_map: {str(require_symbol_map).lower()}",
        f"- require_amount_usd: {str(require_amount_usd).lower()}",
        "",
        "## Preview",
        "",
        "| unlock_id | asset | time | amount_usd | source | flags |",
        "|---|---|---|---:|---|---|",
    ]
    for row in preview:
        lines.append(
            f"| {row['unlock_id']} | {row['asset_symbol']} | {row['unlock_time_utc']} | {row['unlock_amount_usd']} | {row['source']} | {row['quality_flags']} |"
        )
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "Only real, sourced unlock rows should drive Telegram or backtest candidates. Sample rows are allowed for pipeline tests only.",
            "",
        ]
    )
    normalize_path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"status={status}")
    print(f"real_rows={len(real_rows)}")
    print(f"wrote_report={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
