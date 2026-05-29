import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://api.coinmarketcap.com/data-api/v3/token-unlock/listing"
SOURCE_URL = "https://coinmarketcap.com/token-unlocks/"
OUTPUT_COLUMNS = [
    "unlock_id",
    "asset_symbol",
    "unlock_time_utc",
    "unlock_name",
    "unlock_amount_usd",
    "unlock_pct_circulating",
    "source",
    "url",
    "enabled",
    "notes",
]


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": SOURCE_URL,
    "Origin": "https://coinmarketcap.com",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch real token unlock calendar rows from CoinMarketCap public page API.")
    parser.add_argument("--output", default=str(ROOT / "data" / "token_unlock_calendar_cmc.csv"))
    parser.add_argument("--raw-output", default=str(ROOT / "data" / "token_unlock_calendar_cmc_raw.json"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v081_cmc_token_unlock_fetch_summary.csv"))
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--min-amount-usd", type=float, default=0.0)
    parser.add_argument("--min-unlock-pct", type=float, default=0.0)
    parser.add_argument("--include-small-unlocks", default="true")
    parser.add_argument("--request-sleep", type=float, default=0.15)
    parser.add_argument("--timeout", type=float, default=15)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def ms_to_utc_iso(value) -> str:
    try:
        ts_ms = int(float(value))
    except Exception:
        return ""
    if ts_ms <= 0:
        return ""
    return datetime.fromtimestamp(ts_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_float(value) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def safe_float_text(value, decimals: int = 6) -> str:
    number = safe_float(value)
    if number == 0:
        return ""
    return f"{number:.{decimals}f}".rstrip("0").rstrip(".")


def make_unlock_id(symbol: str, unlock_time_utc: str, name: str, crypto_id: str) -> str:
    material = "|".join([symbol, unlock_time_utc, name, str(crypto_id or "")])
    digest = hashlib.sha1(material.encode("utf-8", errors="replace")).hexdigest()[:14]
    return f"cmc_unlock_{symbol.lower()}_{digest}"


def fetch_page(start: int, limit: int, include_small_unlocks: bool, timeout: float) -> dict:
    params = {
        "start": start,
        "limit": limit,
        "sort": "next_unlocked_date",
        "direction": "desc",
        "enableSmallUnlocks": str(include_small_unlocks).lower(),
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    status = payload.get("status") or {}
    if str(status.get("error_code")) not in {"0", "None", ""}:
        raise RuntimeError(f"CoinMarketCap API error: {status}")
    return payload


def allocation_summary(details: list[dict]) -> str:
    parts = []
    for detail in details[:6]:
        name = str(detail.get("allocationName", "") or detail.get("vestingType", "") or "").strip()
        amount_usd = safe_float(detail.get("tokenAmountUsd"))
        if name and amount_usd:
            parts.append(f"{name}:${amount_usd:,.0f}")
        elif name:
            parts.append(name)
    return "; ".join(parts)


def convert_item(item: dict) -> dict | None:
    symbol = str(item.get("symbol", "") or "").strip().upper()
    name = str(item.get("name", "") or "").strip()
    slug = str(item.get("slug", "") or "").strip()
    crypto_id = str(item.get("cryptoId", "") or item.get("id", "") or "").strip()
    next_unlocked = item.get("nextUnlocked") or {}
    unlock_time_utc = ms_to_utc_iso(next_unlocked.get("date"))
    amount_usd = safe_float(next_unlocked.get("tokenAmountUsd"))
    pct = safe_float(next_unlocked.get("tokenAmountPercentage"))
    if not symbol or not unlock_time_utc:
        return None
    details = item.get("nextUnlockedDetail") or []
    unlock_name = f"{symbol} next token unlock"
    notes = [
        "provider=coinmarketcap_public_page_api",
        f"crypto_id={crypto_id}",
        f"name={name}",
        f"cmc_rank={item.get('cmcRank', '')}",
        f"total_unlocked_pct={item.get('totalUnlockedPercentage', '')}",
    ]
    alloc = allocation_summary(details)
    if alloc:
        notes.append(f"allocations={alloc}")
    return {
        "unlock_id": make_unlock_id(symbol, unlock_time_utc, name or symbol, crypto_id),
        "asset_symbol": symbol,
        "unlock_time_utc": unlock_time_utc,
        "unlock_name": unlock_name,
        "unlock_amount_usd": safe_float_text(amount_usd, 2),
        "unlock_pct_circulating": safe_float_text(pct, 4),
        "source": "coinmarketcap_token_unlocks",
        "url": f"https://coinmarketcap.com/currencies/{slug}/" if slug else SOURCE_URL,
        "enabled": "true",
        "notes": "; ".join(notes),
    }


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    include_small = truthy(args.include_small_unlocks)
    raw_pages = []
    converted = []
    seen = set()
    total_count = 0

    for page_index in range(args.max_pages):
        if args.limit and len(converted) >= args.limit:
            break
        start = page_index + 1
        payload = fetch_page(start, args.page_size, include_small, args.timeout)
        data = payload.get("data") or {}
        total_count = int(data.get("totalCount") or total_count or 0)
        items = data.get("tokenUnlockList") or []
        raw_pages.append({"start": start, "count": len(items), "payload": payload})
        if not items:
            break
        for item in items:
            row = convert_item(item)
            if not row:
                continue
            if safe_float(row["unlock_amount_usd"]) < args.min_amount_usd:
                continue
            if safe_float(row["unlock_pct_circulating"]) < args.min_unlock_pct:
                continue
            dedupe = (row["asset_symbol"], row["unlock_time_utc"], row["unlock_name"])
            if dedupe in seen:
                continue
            seen.add(dedupe)
            converted.append(row)
            if args.limit and len(converted) >= args.limit:
                break
        time.sleep(max(args.request_sleep, 0))
        if total_count and start * args.page_size >= total_count:
            break

    converted.sort(key=lambda row: (row["unlock_time_utc"], row["asset_symbol"]))
    output_path = normalize_path(args.output)
    raw_output_path = normalize_path(args.raw_output)
    summary_path = normalize_path(args.summary)
    write_csv(output_path, converted, OUTPUT_COLUMNS)
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text(json.dumps({"api_url": API_URL, "pages": raw_pages}, ensure_ascii=False, indent=2), encoding="utf-8")

    now = datetime.now(timezone.utc)
    future_rows = 0
    next_72h_rows = 0
    for row in converted:
        dt = datetime.strptime(row["unlock_time_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if dt >= now:
            future_rows += 1
            if (dt - now).total_seconds() <= 72 * 3600:
                next_72h_rows += 1
    summary = {
        "provider": "coinmarketcap_token_unlocks",
        "api_url": API_URL,
        "api_total_count": total_count,
        "output_rows": len(converted),
        "future_rows": future_rows,
        "next_72h_rows": next_72h_rows,
        "include_small_unlocks": str(include_small).lower(),
        "min_amount_usd": args.min_amount_usd,
        "min_unlock_pct": args.min_unlock_pct,
        "output": str(output_path),
        "raw_output": str(raw_output_path),
        "status": "pass" if converted else "no_rows",
    }
    write_csv(summary_path, [summary], list(summary.keys()))
    print(f"output_rows={len(converted)}")
    print(f"future_rows={future_rows}")
    print(f"next_72h_rows={next_72h_rows}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
