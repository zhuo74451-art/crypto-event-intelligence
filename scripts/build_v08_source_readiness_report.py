import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a readiness report for first-hand source expansion using historical replay data.")
    parser.add_argument("--candidates", default=str(ROOT / "data" / "event_candidates_real_500_older_review_suggested.csv"))
    parser.add_argument("--historical-event-type", default=str(ROOT / "results" / "v08_historical_source_usefulness_by_event_type.csv"))
    parser.add_argument("--historical-source", default=str(ROOT / "results" / "v08_historical_source_usefulness_by_source.csv"))
    parser.add_argument("--token-calendar", default=str(ROOT / "data" / "token_unlock_calendar.csv"))
    parser.add_argument("--cex-sources", default=str(ROOT / "data" / "cex_listing_sources.csv"))
    parser.add_argument("--cex-netflow-baseline", default=str(ROOT / "data" / "cex_netflow_baseline_state.csv"))
    parser.add_argument("--hyperliquid-state", default=str(ROOT / "data" / "hyperliquid_position_state.csv"))
    parser.add_argument("--hyperliquid-history", default=str(ROOT / "data" / "hyperliquid_position_state_history.csv"))
    parser.add_argument("--live-source-usefulness", default=str(ROOT / "results" / "v08_tg_source_usefulness_by_source.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_source_readiness_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_source_readiness_summary.csv"))
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


def enabled_count(rows: list[dict]) -> int:
    return sum(1 for row in rows if str(row.get("enabled", "true")).strip().lower() in {"1", "true", "yes", "y", ""})


def safe_int(value) -> int:
    try:
        return int(float(str(value or "0")))
    except Exception:
        return 0


def find_event_row(rows: list[dict], event_type: str) -> dict:
    for row in rows:
        if str(row.get("event_type", "") or "").strip() == event_type:
            return row
    return {}


def count_candidates(rows: list[dict], event_type: str) -> int:
    return sum(1 for row in rows if str(row.get("candidate_event_type", "") or "").strip() == event_type)


def count_text_matches(rows: list[dict], pattern: str) -> int:
    rx = re.compile(pattern, re.I)
    return sum(1 for row in rows if rx.search(f"{row.get('title','')} {row.get('content','')}"))


def token_unlock_false_positive_count(rows: list[dict]) -> int:
    negative = re.compile(r"解锁gpt|实时语音|释放被冻结资金|解除制裁|战略石油储备|释放储备|释放人质|释放压力|frozen funds|sanctions relief|strategic petroleum reserve", re.I)
    return sum(
        1
        for row in rows
        if str(row.get("candidate_event_type", "") or "").strip() == "token_unlock"
        and negative.search(f"{row.get('title','')} {row.get('content','')}")
    )


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    candidates = read_rows(normalize_path(args.candidates))
    historical_event_rows = read_rows(normalize_path(args.historical_event_type))
    historical_source_rows = read_rows(normalize_path(args.historical_source))
    token_calendar = read_rows(normalize_path(args.token_calendar))
    cex_sources = read_rows(normalize_path(args.cex_sources))
    cex_baseline = read_rows(normalize_path(args.cex_netflow_baseline))
    hyper_state = read_rows(normalize_path(args.hyperliquid_state))
    hyper_history = read_rows(normalize_path(args.hyperliquid_history))
    live_source_rows = read_rows(normalize_path(args.live_source_usefulness))

    token_event = find_event_row(historical_event_rows, "token_unlock")
    listing_event = find_event_row(historical_event_rows, "exchange_listing")
    whale_event = find_event_row(historical_event_rows, "whale_position")
    macro_event = find_event_row(historical_event_rows, "macro")

    token_calendar_real_rows = [
        r
        for r in token_calendar
        if str(r.get("status", "") or "active").strip().lower() not in {"sample", "disabled"}
        and not str(r.get("unlock_id", "") or "").lower().startswith("sample_")
        and "sample" not in str(r.get("notes", "") or "").lower()
    ]
    token_false_positive = token_unlock_false_positive_count(candidates)
    cex_enabled = enabled_count(cex_sources)
    okx_bybit_enabled = sum(
        1
        for row in cex_sources
        if str(row.get("enabled", "true")).strip().lower() in {"1", "true", "yes", "y", ""}
        and str(row.get("exchange", "") or row.get("source_name", "")).strip().lower() in {"okx", "bybit"}
    )
    hyper_historical_mentions = count_text_matches(candidates, r"hyperliquid|loracle|hl\b")
    cex_transfer_mentions = count_text_matches(candidates, r"coinbase|binance|okx|bybit|kraken|bitfinex")

    live_sent_count = sum(safe_int(r.get("sent_count")) for r in live_source_rows)
    live_followup_4h = sum(safe_int(r.get("followup_4h_rows")) for r in live_source_rows)

    rows = [
        {
            "area": "token_unlock_calendar",
            "historical_evidence": f"candidate_token_unlock={count_candidates(candidates, 'token_unlock')}; backtest_samples={token_event.get('sample_count', 0)}; false_positive_like_rows={token_false_positive}; calendar_rows={len(token_calendar)}; real_calendar_rows={len(token_calendar_real_rows)}",
            "status": "needs_data" if len(token_calendar_real_rows) < 20 or token_false_positive else "usable",
            "next_action": "Add real unlock rows from a token-unlock calendar source and keep stricter keyword rules; do not treat generic 'release/unlock' text as token unlock.",
        },
        {
            "area": "cex_listing_sources",
            "historical_evidence": f"candidate_exchange_listing={count_candidates(candidates, 'exchange_listing')}; backtest_samples={listing_event.get('sample_count', 0)}; enabled_sources={cex_enabled}; okx_bybit_enabled={okx_bybit_enabled}",
            "status": "binance_only" if okx_bybit_enabled == 0 else "multi_cex_ready",
            "next_action": "Keep Binance parser strict on publish time; add OKX/Bybit only after each source has parse-time validation and historical replay counts.",
        },
        {
            "area": "cex_netflow_baseline",
            "historical_evidence": f"baseline_rows={len(cex_baseline)}; historical_cex_mentions={cex_transfer_mentions}; source_rows={len(historical_source_rows)}",
            "status": "needs_more_baseline" if len(cex_baseline) < 72 else "baseline_ready",
            "next_action": "Continue collecting rolling baseline; use baseline_multiple gate before increasing TG volume. Historical news can identify CEX-transfer narratives, but baseline must come from watcher snapshots.",
        },
        {
            "area": "hyperliquid_state_changes",
            "historical_evidence": f"state_rows={len(hyper_state)}; history_rows={len(hyper_history)}; historical_hyperliquid_mentions={hyper_historical_mentions}; whale_backtest_samples={whale_event.get('sample_count', 0)}",
            "status": "state_history_ready" if len(hyper_history) >= 20 else "state_tracking_ready" if len(hyper_state) > 0 else "needs_state_history",
            "next_action": "Keep state and state-history files as source of truth for position-change alerts; historical news replay can test message relevance, but true change detection needs watcher state snapshots.",
        },
        {
            "area": "source_usefulness_from_history",
            "historical_evidence": f"historical_event_rows={len(historical_event_rows)}; historical_source_rows={len(historical_source_rows)}; live_sent_count={live_sent_count}; live_followup_4h={live_followup_4h}; macro_samples={macro_event.get('sample_count', 0)}",
            "status": "usable_for_triage" if historical_event_rows else "missing_historical_usefulness",
            "next_action": "Use historical usefulness report to decide expand/digest/holdout; do not wait 7 days for obvious low-quality historical buckets.",
        },
    ]

    fieldnames = ["area", "historical_evidence", "status", "next_action"]
    write_rows(normalize_path(args.summary), rows, fieldnames)

    lines = [
        "# v0.8 Source Readiness Report",
        "",
        "This report turns the current open issues into historical-data checks. It is for source QA and product operations only.",
        "",
        *markdown_table(rows, fieldnames),
        "",
        "## Practical Decision",
        "",
        "- Do not expand random news volume. Expand only sources with source-specific validation.",
        "- Token unlock needs real calendar rows plus stricter event typing.",
        "- CEX listing can expand to OKX/Bybit after parser-level time validation, not before.",
        "- CEX netflow and Hyperliquid require watcher state/baseline history; historical news backtest is only a relevance proxy.",
        "- Historical usefulness reports can replace part of the 7-day waiting period for obvious bad buckets, but live follow-up is still needed for first-hand watcher-only signals.",
        "",
    ]
    normalize_path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"readiness_rows={len(rows)}")
    print(f"wrote_report={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
