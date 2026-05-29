import argparse
import subprocess
import sys
from pathlib import Path

try:
    from utils.watcher_utils import normalize_path, read_csv_rows, write_summary
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import normalize_path, read_csv_rows, write_summary


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local v0.7 first-hand watcher MVP.")
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--limit-alerts", type=int, default=100)
    parser.add_argument("--sample-if-no-key", default="true")
    parser.add_argument("--backfill", action="store_true", help="Run price backfill on normalized watcher events.")
    parser.add_argument("--api-key-env", default="ETHERSCAN_API_KEY")
    parser.add_argument("--fetch-token-unlocks", default="true")
    parser.add_argument("--token-unlock-calendar", default=str(ROOT / "data" / "token_unlock_calendar_cmc.csv"))
    parser.add_argument("--token-unlock-fetch-limit", type=int, default=500)
    parser.add_argument("--seed-cex-baseline", default="true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def run_step(name: str, command: list[str], required: bool = True) -> None:
    print(f"\n== {name} ==")
    print(" ".join(command))
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode != 0:
        if not required:
            print(f"optional step failed and will be skipped: {name} exit={result.returncode}")
            return
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")


def count_rows(path: str) -> int:
    return len(read_csv_rows(normalize_path(path)))


def main() -> int:
    args = parse_args()
    py = sys.executable
    sample_flag = str(args.sample_if_no_key).strip().lower()

    address_output = "data/watcher_alerts_address_transfers.csv"
    stable_output = "data/watcher_alerts_stablecoin_mint_burn.csv"
    hyperliquid_output = "data/watcher_alerts_hyperliquid_positions.csv"
    cex_netflow_output = "data/watcher_alerts_cex_netflows.csv"
    funding_output = "data/watcher_alerts_binance_funding.csv"
    liquidation_output = "data/watcher_alerts_lending_liquidations.csv"
    cex_listing_output = "data/watcher_alerts_cex_listings.csv"
    token_unlock_output = "data/watcher_alerts_token_unlocks.csv"
    token_unlock_calendar = str(normalize_path(args.token_unlock_calendar))
    alerts_output = "data/watcher_alerts_raw.csv"
    events_output = "data/watcher_events_raw.csv"
    report_output = "results/v07_watcher_daily_report.md"
    tg_drafts_output = "data/tg_drafts_v07_watcher_private_pilot.csv"
    tg_drafts_markdown = "results/tg_drafts_v07_watcher_private_pilot.md"
    summary_output = "results/v07_first_hand_watcher_run_summary.csv"

    steps = []
    if truthy(args.fetch_token_unlocks):
        steps.append(
            (
                "fetch CoinMarketCap token unlock calendar",
                [
                    py,
                    "scripts/fetch_coinmarketcap_token_unlocks.py",
                    "--output",
                    token_unlock_calendar,
                    "--raw-output",
                    "data/token_unlock_calendar_cmc_raw.json",
                    "--summary",
                    "results/v081_cmc_token_unlock_fetch_summary.csv",
                    "--limit",
                    str(args.token_unlock_fetch_limit),
                    "--include-small-unlocks",
                    "true",
                ],
                not Path(token_unlock_calendar).exists(),
            )
        )

    steps.extend([
        (
            "validate v0.7 watchlists",
            [
                py,
                "scripts/validate_v07_watchlists.py",
            ],
        ),
        (
            "watch Ethereum address transfers",
            [
                py,
                "scripts/watch_eth_address_transfers.py",
                "--hours",
                str(args.hours),
                "--output",
                address_output,
                "--summary",
                "results/v07_address_transfer_watcher_summary.csv",
                "--api-key-env",
                args.api_key_env,
                "--sample-if-no-key",
                sample_flag,
            ],
        ),
        (
            "watch stablecoin mint/burn",
            [
                py,
                "scripts/watch_stablecoin_mint_burn.py",
                "--hours",
                str(args.hours),
                "--output",
                stable_output,
                "--summary",
                "results/v07_stablecoin_watcher_summary.csv",
                "--api-key-env",
                args.api_key_env,
                "--sample-if-no-key",
                sample_flag,
            ],
        ),
        (
            "watch Hyperliquid large positions",
            [
                py,
                "scripts/watch_hyperliquid_positions.py",
                "--output",
                hyperliquid_output,
                "--summary",
                "results/v07_hyperliquid_position_watcher_summary.csv",
                "--alert-first-seen",
                "true",
                "--alert-snapshot",
                "true",
            ],
        ),
        (
            "watch Binance funding rates",
            [
                py,
                "scripts/watch_binance_funding_rates.py",
                "--output",
                funding_output,
                "--summary",
                "results/v08_funding_rate_watcher_summary.csv",
            ],
        ),
    ])

    if truthy(args.seed_cex_baseline):
        steps.append(
            (
                "seed CEX netflow baseline from historical transfers",
                [
                    py,
                    "scripts/seed_cex_netflow_baseline_from_transfers.py",
                    "--hours",
                    str(max(args.hours, 168)),
                    "--bucket-hours",
                    "4",
                    "--summary",
                    "results/v08_cex_netflow_baseline_seed_summary.csv",
                    "--api-key-env",
                    args.api_key_env,
                ],
                False,
            )
        )

    steps.extend([
        (
            "watch CEX wallet netflows",
            [
                py,
                "scripts/watch_cex_netflows.py",
                "--hours",
                str(max(args.hours, 4)),
                "--window-hours",
                "4",
                "--output",
                cex_netflow_output,
                "--summary",
                "results/v08_cex_netflow_watcher_summary.csv",
                "--api-key-env",
                args.api_key_env,
                "--sample-if-no-key",
                sample_flag,
            ],
        ),
        (
            "watch Aave V3 lending liquidations",
            [
                py,
                "scripts/watch_lending_liquidations.py",
                "--hours",
                str(args.hours),
                "--output",
                liquidation_output,
                "--summary",
                "results/v08_lending_liquidation_watcher_summary.csv",
                "--api-key-env",
                args.api_key_env,
                "--sample-if-no-key",
                sample_flag,
            ],
        ),
        (
            "watch CEX listing announcements",
            [
                py,
                "scripts/watch_cex_listing_announcements.py",
                "--output",
                cex_listing_output,
                "--summary",
                "results/v08_cex_listing_watcher_summary.csv",
                "--lookback-hours",
                str(args.hours),
                "--sample-if-empty",
                "false",
            ],
        ),
        (
            "watch token unlock calendar",
            [
                py,
                "scripts/watch_token_unlock_calendar.py",
                "--calendar",
                token_unlock_calendar,
                "--output",
                token_unlock_output,
                "--summary",
                "results/v08_token_unlock_watcher_summary.csv",
            ],
        ),
        (
            "normalize watcher alerts to events",
            [
                py,
                "scripts/normalize_watcher_alerts_to_events.py",
                "--inputs",
                address_output,
                stable_output,
                hyperliquid_output,
                funding_output,
                cex_netflow_output,
                liquidation_output,
                cex_listing_output,
                token_unlock_output,
                "--alerts-output",
                alerts_output,
                "--events-output",
                events_output,
                "--summary",
                "results/v07_watcher_normalization_summary.csv",
                "--markdown-output",
                report_output,
                "--limit",
                str(args.limit_alerts),
            ],
        ),
        (
            "generate watcher TG draft preview",
            [
                py,
                "scripts/generate_watcher_tg_drafts.py",
                "--input",
                events_output,
                "--output",
                tg_drafts_output,
                "--markdown-output",
                tg_drafts_markdown,
                "--limit",
                str(args.limit_alerts),
            ],
        ),
        (
            "validate watcher TG draft preview",
            [
                py,
                "scripts/validate_tg_drafts.py",
                "--input",
                tg_drafts_output,
                "--output",
                "results/tg_drafts_v07_watcher_validation_report.csv",
                "--summary",
                "results/tg_drafts_v07_watcher_validation_summary.csv",
                "--markdown-output",
                "results/tg_drafts_v07_watcher_validation_report.md",
            ],
        ),
    ])

    if args.backfill:
        steps.extend(
            [
                (
                    "backfill watcher event prices",
                    [
                        py,
                        "scripts/backfill_event_prices.py",
                        "--input",
                        events_output,
                        "--output",
                        "results/v07_watcher_event_price_backfill.csv",
                        "--quality-output",
                        "results/v07_watcher_event_quality_report.csv",
                        "--limit",
                        str(args.limit_alerts),
                        "--symbol-map",
                        "data/symbol_map.csv",
                    ],
                ),
                (
                    "validate watcher event backfill",
                    [
                        py,
                        "scripts/validate_backfill_results.py",
                        "--input",
                        "results/v07_watcher_event_price_backfill.csv",
                        "--output",
                        "results/v07_watcher_event_quality_report.csv",
                    ],
                ),
            ]
        )

    try:
        for step in steps:
            if len(step) == 3:
                name, command, required = step
            else:
                name, command = step
                required = True
            run_step(name, command, required=required)
    except Exception as exc:
        write_summary(
            normalize_path(summary_output),
            {
                "status": "fail",
                "error": str(exc),
                "address_alert_rows": count_rows(address_output),
                "stablecoin_alert_rows": count_rows(stable_output),
                "hyperliquid_alert_rows": count_rows(hyperliquid_output),
                "funding_alert_rows": count_rows(funding_output),
                "cex_netflow_alert_rows": count_rows(cex_netflow_output),
                "liquidation_alert_rows": count_rows(liquidation_output),
                "cex_listing_alert_rows": count_rows(cex_listing_output),
                "token_unlock_alert_rows": count_rows(token_unlock_output),
                "deduped_alert_rows": count_rows(alerts_output),
                "event_rows": count_rows(events_output),
                "tg_draft_rows": count_rows(tg_drafts_output),
                "report": report_output,
            },
        )
        print(f"v0.7 watcher run failed: {exc}")
        return 1

    summary = {
        "status": "pass",
        "hours": args.hours,
        "address_alert_rows": count_rows(address_output),
        "stablecoin_alert_rows": count_rows(stable_output),
        "hyperliquid_alert_rows": count_rows(hyperliquid_output),
        "funding_alert_rows": count_rows(funding_output),
        "cex_netflow_alert_rows": count_rows(cex_netflow_output),
        "liquidation_alert_rows": count_rows(liquidation_output),
        "cex_listing_alert_rows": count_rows(cex_listing_output),
        "token_unlock_alert_rows": count_rows(token_unlock_output),
        "deduped_alert_rows": count_rows(alerts_output),
        "event_rows": count_rows(events_output),
        "tg_draft_rows": count_rows(tg_drafts_output),
        "backfill_enabled": str(bool(args.backfill)).lower(),
        "alerts_output": alerts_output,
        "events_output": events_output,
        "tg_drafts_output": tg_drafts_output,
        "report": report_output,
    }
    write_summary(normalize_path(summary_output), summary)
    print("\nv0.7 first-hand watcher run completed")
    for key, value in summary.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
