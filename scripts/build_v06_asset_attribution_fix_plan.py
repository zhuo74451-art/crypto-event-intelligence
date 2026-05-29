import argparse
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

KNOWN_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "XRP",
    "DOGE",
    "ADA",
    "LINK",
    "AVAX",
    "HYPE",
    "ONDO",
    "WLD",
    "SHIB",
    "TRX",
    "USDT",
    "USDC",
]
QUOTE_OR_STABLE_ASSETS = {"USDT", "USDC"}

NON_TOKEN_TICKERS = ["MSTR", "AMD", "HIVE"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a fix plan for v0.6 preview asset attribution risks.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "results" / "v06_filtered_preview_asset_attribution_audit.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "v06_asset_attribution_fix_plan.csv"),
    )
    parser.add_argument(
        "--summary",
        default=str(ROOT / "results" / "v06_asset_attribution_fix_plan_summary.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v06_asset_attribution_fix_plan.md"),
    )
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def token_present(text_upper: str, token: str) -> bool:
    return re.search(rf"(?<![A-Z0-9])\$?{re.escape(token)}(?![A-Z0-9])", text_upper) is not None


def mentioned_assets(row: pd.Series) -> list[str]:
    text = f"{row.get('title', '')} {str(row.get('content', ''))[:1200]}".upper()
    return [asset for asset in KNOWN_ASSETS if token_present(text, asset)]


def mentioned_non_token(row: pd.Series) -> list[str]:
    text = f"{row.get('title', '')} {str(row.get('content', ''))[:1200]}".upper()
    return [asset for asset in NON_TOKEN_TICKERS if token_present(text, asset)]


def has_flag(row: pd.Series, flag: str) -> bool:
    return flag in {part.strip() for part in str(row.get("asset_attribution_flags", "")).split(",") if part.strip()}


def choose_action(row: pd.Series) -> tuple[str, str, str, str]:
    risk = str(row.get("asset_attribution_risk", "")).strip()
    candidate_asset = str(row.get("candidate_asset_symbol", "")).strip().upper()
    event_scope = str(row.get("event_scope", "")).strip()
    event_type = str(row.get("v06_stratify_type", "")).strip()
    route = str(row.get("channel_route", "")).strip()
    assets = mentioned_assets(row)
    non_token = mentioned_non_token(row)
    value = f"{row.get('title', '')} {str(row.get('content', ''))[:1200]}".lower()

    if risk == "low":
        return "keep_for_clean_preview", candidate_asset, route, "low risk asset attribution"

    if non_token:
        return (
            "exclude_from_clean_backtest",
            "",
            "research_only",
            f"non-token/equity/infrastructure reference: {','.join(non_token)}",
        )

    if event_type == "hack_security" and any(term in value for term in ["echo", "monad", "ebtc", "wbtc", "curvance"]):
        return (
            "needs_entity_rule_review",
            candidate_asset,
            route,
            "protocol exploit proxy assets require primary-asset policy review",
        )

    alternate_assets = [asset for asset in assets if asset != candidate_asset and asset not in QUOTE_OR_STABLE_ASSETS]
    if alternate_assets and candidate_asset in {"BTC", "ETH"}:
        alt = alternate_assets[0]
        if alt in {"HYPE", "ONDO", "WLD", "SHIB"}:
            return (
                "route_unsupported_research",
                alt,
                "unsupported_research",
                f"primary mentioned asset appears to be unsupported/non-Binance: {alt}",
            )
        return (
            "fix_primary_asset",
            alt,
            route,
            f"candidate uses {candidate_asset}, but title/content mentions {alt}",
        )

    if has_flag(row, "btc_default_without_explicit_btc"):
        return (
            "exclude_from_clean_backtest",
            "",
            "research_only",
            "BTC default without explicit BTC reference",
        )

    if event_scope == "market_wide" and route == "alpha_candidate":
        return (
            "route_macro_or_research_holdout",
            candidate_asset,
            "macro_policy" if event_type in {"regulation_macro", "stablecoin_flow"} else "research_only",
            "market-wide row should not be alpha_candidate without explicit primary asset",
        )

    if has_flag(row, "multiple_assets_detected") or has_flag(row, "entity_flag_candidate_asset_mismatch"):
        return (
            "needs_entity_rule_review",
            candidate_asset,
            route,
            "multiple assets or entity mismatch requires dictionary/rule review",
        )

    if risk == "medium":
        return "keep_for_manual_review", candidate_asset, route, "medium risk; review before clean backtest"

    return "exclude_from_clean_backtest", "", "research_only", "unresolved high risk attribution"


def render_report(plan: pd.DataFrame, summary: pd.DataFrame) -> str:
    lines = [
        "# v0.6 Asset Attribution Fix Plan",
        "",
        "This is a non-destructive plan. It does not edit candidates or run backtests.",
        "",
        "## Summary",
        "",
        "| action | count |",
        "|---|---:|",
    ]
    if summary.empty:
        lines.append("| none | 0 |")
    else:
        for _, row in summary.iterrows():
            lines.append(f"| {row['recommended_action']} | {row['count']} |")

    lines.extend(
        [
            "",
            "## High/Medium Risk Actions",
            "",
            "| candidate_id | risk | action | asset | route | reason | title |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    risky = plan[plan["asset_attribution_risk"].isin(["high", "medium"])].copy()
    if risky.empty:
        lines.append("| none |  |  |  |  |  |  |")
    else:
        for _, row in risky.iterrows():
            title = str(row.get("title", "")).replace("|", "/").replace("\n", " ")[:100]
            reason = str(row.get("fix_reason", "")).replace("|", "/")[:100]
            lines.append(
                f"| {row.get('candidate_id', '')} | {row.get('asset_attribution_risk', '')} | {row.get('recommended_action', '')} | {row.get('recommended_asset_symbol', '')} | {row.get('recommended_channel_route', '')} | {reason} | {title} |"
            )

    lines.extend(
        [
            "",
            "## Use",
            "",
            "- Apply this plan only after reviewing the recommended action categories.",
            "- Do not force unsupported assets into BTC/ETH just to make Binance backtests work.",
            "- Keep non-token equity/infrastructure rows out of clean token-price backtests.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    report_path = normalize_path(args.report)
    if not input_path.exists():
        print(f"input not found: {input_path}")
        return 1
    df = pd.read_csv(input_path, dtype=str).fillna("")
    rows = []
    for _, row in df.iterrows():
        action, asset, route, reason = choose_action(row)
        item = row.to_dict()
        item.update(
            {
                "recommended_action": action,
                "recommended_asset_symbol": asset,
                "recommended_channel_route": route,
                "fix_reason": reason,
                "mentioned_assets": ",".join(mentioned_assets(row)),
                "mentioned_non_token_tickers": ",".join(mentioned_non_token(row)),
            }
        )
        rows.append(item)
    plan = pd.DataFrame(rows)
    summary = (
        plan["recommended_action"]
        .value_counts()
        .rename_axis("recommended_action")
        .reset_index(name="count")
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(output_path, index=False)
    summary.to_csv(summary_path, index=False)
    report_path.write_text(render_report(plan, summary), encoding="utf-8")
    print(f"wrote fix plan to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
