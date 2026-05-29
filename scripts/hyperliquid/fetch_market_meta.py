import argparse
import csv
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
INFO_URL = "https://api.hyperliquid.xyz/info"
CN_TZ = timezone(timedelta(hours=8))


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


COLUMNS = [
    "observed_at_utc",
    "observed_at_china",
    "asset_symbol",
    "mark_price",
    "mid_price",
    "prev_day_price",
    "price_change_pct_24h",
    "funding_rate",
    "open_interest_native",
    "open_interest_usd",
    "day_volume_usd",
    "premium",
    "oracle_price",
    "quality_status",
    "skip_reason",
    "raw_json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Hyperliquid public perp market metadata via official info API.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "funding_watchlist.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "hyperliquid" / "market_meta_snapshot.csv"))
    parser.add_argument("--history", default=str(ROOT / "data" / "hyperliquid" / "market_meta_history.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v15_hyperliquid_market_meta_summary.csv"))
    parser.add_argument("--all-assets", action="store_true")
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def china_time(dt: datetime) -> str:
    return dt.astimezone(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], columns: list[str], append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if not append or not exists:
            writer.writeheader()
        writer.writerows(rows)


def enabled_assets(path: Path) -> set[str]:
    assets = set()
    for row in read_rows(path):
        if str(row.get("enabled") or "").strip().lower() in {"1", "true", "yes", "y"}:
            asset = str(row.get("asset_symbol") or "").strip().upper()
            if asset:
                assets.add(asset)
    return assets


def request_meta(retries: int = 3) -> tuple[dict, list]:
    last_error = None
    session = requests.Session()
    session.trust_env = False
    for attempt in range(1, retries + 1):
        try:
            response = session.post(INFO_URL, json={"type": "metaAndAssetCtxs"}, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[0], dict) and isinstance(payload[1], list):
                return payload[0], payload[1]
            raise RuntimeError(f"unexpected_response:{str(payload)[:200]}")
        except Exception as exc:
            last_error = exc
            time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"hyperliquid_meta_failed:{last_error}")


def build_rows(meta: dict, ctxs: list, observed: datetime, assets: set[str], all_assets: bool) -> list[dict]:
    universe = meta.get("universe", []) if isinstance(meta, dict) else []
    rows = []
    for index, ctx in enumerate(ctxs):
        asset_meta = universe[index] if index < len(universe) and isinstance(universe[index], dict) else {}
        asset = str(asset_meta.get("name") or ctx.get("coin") or "").strip().upper()
        if not asset:
            continue
        if assets and not all_assets and asset not in assets:
            continue
        mark = safe_float(ctx.get("markPx"))
        mid = safe_float(ctx.get("midPx"))
        prev = safe_float(ctx.get("prevDayPx"))
        oi_native = safe_float(ctx.get("openInterest"))
        price_change = (mark / prev - 1.0) * 100 if mark > 0 and prev > 0 else 0.0
        row = {column: "" for column in COLUMNS}
        row.update(
            {
                "observed_at_utc": utc_iso(observed),
                "observed_at_china": china_time(observed),
                "asset_symbol": asset,
                "mark_price": f"{mark:.10g}" if mark else "",
                "mid_price": f"{mid:.10g}" if mid else "",
                "prev_day_price": f"{prev:.10g}" if prev else "",
                "price_change_pct_24h": f"{price_change:.4f}",
                "funding_rate": str(ctx.get("funding") or ""),
                "open_interest_native": str(ctx.get("openInterest") or ""),
                "open_interest_usd": f"{oi_native * mark:.2f}" if oi_native and mark else "",
                "day_volume_usd": str(ctx.get("dayNtlVlm") or ""),
                "premium": str(ctx.get("premium") or ""),
                "oracle_price": str(ctx.get("oraclePx") or ""),
                "quality_status": "ok" if mark else "partial",
                "raw_json": json.dumps({"asset_meta": asset_meta, "ctx": ctx}, ensure_ascii=False, separators=(",", ":")),
            }
        )
        rows.append(row)
    return rows


def main() -> int:
    args = parse_args()
    observed = datetime.now(timezone.utc).replace(microsecond=0)
    assets = enabled_assets(normalize_path(args.watchlist))
    try:
        meta, ctxs = request_meta()
        rows = build_rows(meta, ctxs, observed, assets, args.all_assets)
        status = "pass" if rows else "warning"
        message = "ok" if rows else "no_rows"
    except Exception as exc:
        rows = []
        status = "fail"
        message = str(exc)[:200]

    write_rows(normalize_path(args.output), rows, COLUMNS)
    if rows:
        write_rows(normalize_path(args.history), rows, COLUMNS, append=True)
    ok_rows = sum(1 for row in rows if row.get("quality_status") == "ok")
    summary = {
        "observed_at_china": china_time(observed),
        "watchlist_assets": ";".join(sorted(assets)),
        "rows": len(rows),
        "ok_rows": ok_rows,
        "partial_rows": sum(1 for row in rows if row.get("quality_status") == "partial"),
        "history_output": str(normalize_path(args.history).relative_to(ROOT)),
        "status": status,
        "message": message,
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"hyperliquid_market_meta rows={len(rows)} ok={ok_rows} status={status}")
    if status == "fail":
        print(message)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
