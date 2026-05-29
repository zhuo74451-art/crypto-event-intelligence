import argparse
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

KNOWN_UNSUPPORTED_OR_NONBENCHMARK_ASSETS = {
    "MSTR",
    "AMD",
    "HIVE",
    "USDT",
    "USDC",
}

EQUITY_OR_STOCK_TERMS = {
    "mstr",
    "amd",
    "hive",
    "stock",
    "equity",
    "miner",
    "mining stock",
    "ai super factory",
    "data center",
    "股票",
    "矿企",
}
MARKET_WIDE_TERMS = {
    "market",
    "macro",
    "sec",
    "fed",
    "fomc",
    "cpi",
    "ppi",
    "regulation",
    "bill",
    "稳定币",
    "代币化",
    "监管",
    "市场",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit asset attribution risk in the v0.6 filtered preview sample.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "event_candidates_v06_filtered_mature_review_auto50_preview.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "v06_filtered_preview_asset_attribution_audit.csv"),
    )
    parser.add_argument(
        "--summary",
        default=str(ROOT / "results" / "v06_filtered_preview_asset_attribution_summary.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v06_filtered_preview_asset_attribution_audit.md"),
    )
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def token_present(text_upper: str, token: str) -> bool:
    token = token.upper().lstrip("$")
    return re.search(rf"(?<![A-Z0-9])\$?{re.escape(token)}(?![A-Z0-9])", text_upper) is not None


def contains_equity_or_stock_term(text_lower: str) -> bool:
    if "adshares" in text_lower:
        text_lower = text_lower.replace("adshares", "")
    phrase_terms = [
        "mining stock",
        "ai super factory",
        "data center",
        "股票",
        "矿企",
    ]
    if any(term in text_lower for term in phrase_terms):
        return True
    token_terms = ["mstr", "amd", "hive", "stock", "equity", "miner"]
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text_lower) for term in token_terms)


def split_pipe(value: object) -> list[str]:
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def risk_for_row(row: pd.Series) -> tuple[str, list[str], str]:
    flags: list[str] = []
    title = str(row.get("title", ""))
    content = str(row.get("content", ""))
    text = f"{title} {content[:1200]}"
    text_lower = text.lower()
    text_upper = text.upper()
    candidate_asset = str(row.get("candidate_asset_symbol", "")).strip().upper()
    primary_asset = str(row.get("primary_asset_symbol", "")).strip().upper()
    event_scope = str(row.get("event_scope", "")).strip()
    channel_route = str(row.get("channel_route", "")).strip()
    event_type = str(row.get("v06_stratify_type", "") or row.get("event_type_l1", "")).strip()
    detected_names = split_pipe(row.get("detected_entity_names", ""))

    if primary_asset and candidate_asset and primary_asset != candidate_asset:
        flags.append("candidate_primary_asset_mismatch")
    if event_scope == "market_wide" and channel_route == "alpha_candidate":
        flags.append("market_wide_alpha_candidate")
    if event_scope == "market_wide" and candidate_asset in {"BTC", "ETH"} and event_type not in {"regulation_macro", "institutional_flow"}:
        flags.append("market_wide_forced_major_asset")

    unsupported_hits = sorted([asset for asset in KNOWN_UNSUPPORTED_OR_NONBENCHMARK_ASSETS if token_present(text_upper, asset)])
    unsupported_without_candidate = [asset for asset in unsupported_hits if asset != candidate_asset]
    if unsupported_without_candidate and candidate_asset in {"BTC", "ETH"}:
        flags.append("mentions_other_asset_but_candidate_major")
    if unsupported_hits and candidate_asset not in unsupported_hits and event_type in {"whale_position", "institutional_flow", "project_business"}:
        flags.append("possible_wrong_primary_asset")

    if contains_equity_or_stock_term(text_lower) and channel_route in {"alpha_candidate", "macro_policy"}:
        flags.append("equity_or_infrastructure_not_token_event")
    if event_type in {"legal_enforcement", "project_business", "stablecoin_flow"} and candidate_asset == "BTC" and not token_present(text_upper, "BTC"):
        flags.append("btc_default_without_explicit_btc")
    if event_scope == "market_wide" and not any(term in text_lower for term in MARKET_WIDE_TERMS) and candidate_asset in {"BTC", "ETH"}:
        flags.append("market_wide_without_clear_macro_terms")

    if "candidate_asset_mismatch" in str(row.get("entity_flags", "")):
        flags.append("entity_flag_candidate_asset_mismatch")
    if "multiple_assets_detected" in str(row.get("entity_flags", "")):
        flags.append("multiple_assets_detected")

    flags = list(dict.fromkeys(flags))
    severe_flags = {
        "possible_wrong_primary_asset",
        "mentions_other_asset_but_candidate_major",
        "equity_or_infrastructure_not_token_event",
        "btc_default_without_explicit_btc",
    }
    medium_flags = {
        "candidate_primary_asset_mismatch",
        "market_wide_alpha_candidate",
        "market_wide_forced_major_asset",
        "entity_flag_candidate_asset_mismatch",
        "multiple_assets_detected",
        "market_wide_without_clear_macro_terms",
    }
    if any(flag in severe_flags for flag in flags):
        risk = "high"
    elif any(flag in medium_flags for flag in flags):
        risk = "medium"
    else:
        risk = "low"

    explanation_parts = []
    if unsupported_without_candidate:
        explanation_parts.append(f"mentions={','.join(unsupported_without_candidate)}")
    if detected_names:
        explanation_parts.append("entities=" + ",".join(detected_names[:5]))
    explanation = "; ".join(explanation_parts)
    return risk, flags, explanation


def render_report(audit: pd.DataFrame, summary: pd.DataFrame) -> str:
    first = summary.iloc[0].to_dict() if not summary.empty else {}
    lines = [
        "# v0.6 Filtered Preview Asset Attribution Audit",
        "",
        f"total_rows: {first.get('total_rows', 0)}",
        f"high_risk_rows: {first.get('high_risk_rows', 0)}",
        f"medium_risk_rows: {first.get('medium_risk_rows', 0)}",
        f"low_risk_rows: {first.get('low_risk_rows', 0)}",
        "",
        "## Interpretation",
        "",
        "- This audit checks whether the preview sample's asset attribution is safe enough for backtest planning.",
        "- High-risk rows should not enter a clean v0.6 backtest without correction or explicit policy approval.",
        "- The audit does not modify source candidates or historical v043 outputs.",
        "",
        "## High-Risk Rows",
        "",
        "| candidate_id | event_type | asset | route | flags | title |",
        "|---|---|---|---|---|---|",
    ]
    high = audit[audit["asset_attribution_risk"].eq("high")].copy()
    if high.empty:
        lines.append("| none |  |  |  |  |  |")
    else:
        for _, row in high.head(40).iterrows():
            title = str(row.get("title", "")).replace("|", "/").replace("\n", " ")[:120]
            lines.append(
                f"| {row.get('candidate_id', '')} | {row.get('v06_stratify_type', '')} | {row.get('candidate_asset_symbol', '')} | {row.get('channel_route', '')} | {row.get('asset_attribution_flags', '')} | {title} |"
            )

    lines.extend(
        [
            "",
            "## Recommended Use",
            "",
            "- Use `asset_attribution_risk=low` rows as the safest preview subset.",
            "- Treat `medium` rows as review candidates.",
            "- Exclude or fix `high` rows before any clean backtest branch.",
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
    if df.empty:
        print(f"input empty: {input_path}")
        return 1

    risks = [risk_for_row(row) for _, row in df.iterrows()]
    df["asset_attribution_risk"] = [risk for risk, _flags, _explanation in risks]
    df["asset_attribution_flags"] = [",".join(flags) for _risk, flags, _explanation in risks]
    df["asset_attribution_explanation"] = [explanation for _risk, _flags, explanation in risks]

    summary = pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "high_risk_rows": int(df["asset_attribution_risk"].eq("high").sum()),
                "medium_risk_rows": int(df["asset_attribution_risk"].eq("medium").sum()),
                "low_risk_rows": int(df["asset_attribution_risk"].eq("low").sum()),
                "safe_low_risk_rate": round(float(df["asset_attribution_risk"].eq("low").mean()), 4),
            }
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    summary.to_csv(summary_path, index=False)
    report_path.write_text(render_report(df, summary), encoding="utf-8")
    print(f"wrote audit to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
