import argparse
import re
from datetime import datetime, timedelta, timezone
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
        request_json,
        safe_float,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )
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
        request_json,
        safe_float,
        utc_iso_to_china,
        write_csv_rows,
        write_summary,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENDPOINT = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
LISTING_WORDS = re.compile(r"\b(will list|will add|launch|listing|listed|seed tag|futures will launch)\b", re.I)
SYMBOL_PATTERN = re.compile(r"\(([A-Z0-9]{2,12})\)|\b([A-Z0-9]{2,12})USDT\b")
TITLE_DATE_PATTERN = re.compile(r"\((20\d{2}[-/]\d{1,2}[-/]\d{1,2})\)")
NOISE_SYMBOLS = {"USD", "USDT", "USDC", "FDUSD", "NFT", "ETF", "API", "VIP", "USDⓈ"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch CEX public listing announcements and emit structured alerts.")
    parser.add_argument("--sources", default=str(ROOT / "data" / "cex_listing_sources.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_cex_listings.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_cex_listing_watcher_summary.csv"))
    parser.add_argument("--lookback-hours", type=float, default=72)
    parser.add_argument("--page-size", type=int, default=30)
    parser.add_argument("--sample-if-empty", default="true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def release_to_utc_iso(value, title: str = "") -> str:
    try:
        if str(value or "").strip():
            raw = int(float(str(value)))
            if raw > 10_000_000_000:
                raw = raw / 1000
            return dt_to_utc_iso(datetime.fromtimestamp(raw, tz=timezone.utc))
    except Exception:
        pass

    match = TITLE_DATE_PATTERN.search(str(title or ""))
    if match:
        try:
            date_text = match.group(1).replace("/", "-")
            dt = datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt_to_utc_iso(dt)
        except Exception:
            return ""
    return ""


def utc_iso_to_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def extract_assets(title: str) -> list[str]:
    symbols = []
    for left, right in SYMBOL_PATTERN.findall(title):
        symbol = (left or right or "").strip().upper()
        if symbol and symbol not in NOISE_SYMBOLS and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def fetch_binance_articles(endpoint: str, catalog_id: str, page_size: int) -> list[dict]:
    payload = request_json(
        endpoint or DEFAULT_ENDPOINT,
        params={"catalogId": catalog_id or "48", "pageNo": 1, "pageSize": page_size},
        timeout=15,
        retries=3,
    )
    if not isinstance(payload, dict):
        return []
    data = payload.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("articles"), list):
        return data["articles"]
    articles = []
    if isinstance(data, dict) and isinstance(data.get("catalogs"), list):
        for catalog in data["catalogs"]:
            if isinstance(catalog, dict) and isinstance(catalog.get("articles"), list):
                articles.extend(catalog["articles"])
    return articles


def build_alert(exchange: str, article: dict, asset: str) -> dict:
    title = str(article.get("title", "") or "").strip()
    code = str(article.get("code", "") or article.get("id", "") or "").strip()
    release_utc = release_to_utc_iso(article.get("releaseDate") or article.get("publishDate") or "", title)
    item = {column: "" for column in ALERT_COLUMNS}
    item.update(
        {
            "alert_id": make_alert_id("cex_listing_announcement", exchange, code, asset),
            "observed_at_utc": release_utc,
            "observed_at_china": utc_iso_to_china(release_utc),
            "source_type": "first_hand",
            "watcher_source": "cex_listing_announcement",
            "blockchain": "cex_announcement",
            "primary_entity": exchange,
            "primary_address": code,
            "counterparty_entity": "listed_asset",
            "counterparty_address": asset,
            "asset_symbol": asset,
            "amount_native": "0",
            "amount_usd": "0",
            "metric_type": "cex_listing_announcement",
            "metric_value": "1",
            "event_type_l1": "exchange_listing",
            "event_type_l2": "cex_listing_announcement",
            "risk_category": "listing_event",
            "confidence": "high",
            "relevance_score": "0.9",
            "threshold_rule": "public_cex_listing_announcement",
            "dedupe_key": make_dedupe_key("cex_listing_announcement", exchange, code, asset),
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "ok",
            "raw_json": json_dumps({"exchange": exchange, "article": article, "title": title}),
        }
    )
    return item


def sample_alert() -> dict:
    observed = dt_to_utc_iso(now_utc() - timedelta(hours=2))
    item = {column: "" for column in ALERT_COLUMNS}
    item.update(
        {
            "alert_id": make_alert_id("sample_cex_listing", "Binance", observed),
            "observed_at_utc": observed,
            "observed_at_china": utc_iso_to_china(observed),
            "source_type": "first_hand",
            "watcher_source": "cex_listing_announcement",
            "blockchain": "cex_announcement",
            "primary_entity": "Binance",
            "primary_address": "sample_listing_notice",
            "counterparty_entity": "listed_asset",
            "counterparty_address": "SOL",
            "asset_symbol": "SOL",
            "amount_native": "0",
            "amount_usd": "0",
            "metric_type": "cex_listing_announcement",
            "metric_value": "1",
            "event_type_l1": "exchange_listing",
            "event_type_l2": "cex_listing_announcement",
            "risk_category": "listing_event",
            "confidence": "sample",
            "relevance_score": "0.9",
            "threshold_rule": "sample_public_cex_listing_announcement",
            "dedupe_key": make_dedupe_key("sample_cex_listing", "Binance", observed[:13]),
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "sample",
            "raw_json": json_dumps({"sample": True, "title": "Binance Will List Sample Asset (SOL)"}),
        }
    )
    return item


def main() -> int:
    args = parse_args()
    sources = [row for row in read_csv_rows(normalize_path(args.sources)) if is_enabled(row)]
    cutoff = now_utc() - timedelta(hours=args.lookback_hours)
    alerts = []
    fetched_articles = 0
    skipped_not_listing = 0
    skipped_old = 0
    skipped_missing_time = 0
    for source in sources:
        exchange = str(source.get("exchange", "") or source.get("source_name", "") or "CEX").strip()
        try:
            articles = fetch_binance_articles(
                str(source.get("endpoint", "") or DEFAULT_ENDPOINT).strip(),
                str(source.get("catalog_id", "") or "48").strip(),
                args.page_size,
            )
        except Exception:
            articles = []
        fetched_articles += len(articles)
        for article in articles:
            title = str(article.get("title", "") or "").strip()
            if not LISTING_WORDS.search(title):
                skipped_not_listing += 1
                continue
            release_utc = release_to_utc_iso(article.get("releaseDate") or article.get("publishDate") or "", title)
            if not release_utc:
                skipped_missing_time += 1
                continue
            release_dt = utc_iso_to_dt(release_utc)
            if release_dt and release_dt < cutoff:
                skipped_old += 1
                continue
            assets = extract_assets(title)
            if not assets:
                assets = ["BTC"] if "Bitcoin" in title else []
            for asset in assets[:5]:
                alerts.append(build_alert(exchange, article, asset))

    if not alerts and truthy(args.sample_if_empty):
        alerts = [sample_alert()]

    output_path = normalize_path(args.output)
    write_csv_rows(output_path, alerts, ALERT_COLUMNS)
    summary = {
        "watcher": "cex_listing_announcement",
        "source_rows": len(sources),
        "fetched_articles": fetched_articles,
        "alert_rows": len(alerts),
        "skipped_not_listing": skipped_not_listing,
        "skipped_old": skipped_old,
        "skipped_missing_time": skipped_missing_time,
        "lookback_hours": args.lookback_hours,
        "status": "pass",
        "output": str(output_path),
    }
    write_summary(normalize_path(args.summary), summary)
    print(f"cex_listing_alert_rows={len(alerts)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
