import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a focused packet for entity-rule review rows.")
    parser.add_argument(
        "--fix-plan",
        default=str(ROOT / "results" / "v06_asset_attribution_fix_plan.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "v06_entity_rule_review_packet.csv"),
    )
    parser.add_argument(
        "--summary",
        default=str(ROOT / "results" / "v06_entity_rule_review_packet_summary.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v06_entity_rule_review_packet.md"),
    )
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def text(row: pd.Series) -> str:
    return f"{row.get('title', '')} {str(row.get('content', ''))[:1200]}".lower()


def classify_review(row: pd.Series) -> tuple[str, str, str, str]:
    value = text(row)
    candidate_asset = str(row.get("candidate_asset_symbol", "")).strip().upper()
    effective_asset = str(row.get("effective_asset_symbol", "") or candidate_asset).strip().upper()
    effective_spot = str(row.get("effective_binance_spot_symbol", "")).strip().upper()
    effective_futures = str(row.get("effective_binance_futures_symbol", "")).strip().upper()
    event_type = str(row.get("v06_stratify_type", "")).strip()
    route = str(row.get("channel_route", "")).strip()

    if "hyperliquid" in value or "hyperliquid" in str(row.get("title", "")).lower():
        if effective_asset == "HYPE" and (effective_spot or effective_futures):
            return (
                "hyperliquid_primary_asset_supported",
                "HYPE",
                route,
                "Hyperliquid/HYPE appears to be primary and now has a validated Binance market symbol; review route, not symbol support.",
            )
        return (
            "unsupported_primary_asset",
            "HYPE",
            "unsupported_research",
            "Hyperliquid/HYPE appears to be the primary subject; do not force SOL/BTC for Binance backtest.",
        )

    if "nobitex" in value and ("tron" in value or "bnb chain" in value):
        return (
            "multi_chain_regulatory_flow",
            "",
            "macro_policy",
            "Regulatory/sanctions flow across Tron and BNB Chain; avoid single-asset attribution.",
        )

    if "echo" in value or "monad" in value or "ebtc" in value:
        return (
            "protocol_exploit_primary_asset_policy",
            effective_asset or candidate_asset,
            route,
            "Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stolen asset, or proxy benchmark.",
        )

    if event_type == "hack_security":
        return (
            "hack_security_multi_asset_policy",
            effective_asset or candidate_asset,
            route,
            "Hack/security row has multiple assets; needs explicit primary-asset policy before clean backtest.",
        )

    return (
        "generic_entity_mismatch",
        effective_asset or candidate_asset,
        route,
        "Entity mismatch requires dictionary or rule review.",
    )


def render_report(packet: pd.DataFrame, summary: pd.DataFrame) -> str:
    lines = [
        "# v0.6 Entity Rule Review Packet",
        "",
        "This packet isolates rows where entity detection or primary-asset selection is ambiguous.",
        "It is non-destructive and does not edit candidate files.",
        "",
        "## Summary",
        "",
        "| review_type | count |",
        "|---|---:|",
    ]
    if summary.empty:
        lines.append("| none | 0 |")
    else:
        for _, row in summary.iterrows():
            lines.append(f"| {row['entity_review_type']} | {row['count']} |")

    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| candidate_id | review_type | current_asset | suggested_asset | suggested_route | note | title |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    if packet.empty:
        lines.append("| none |  |  |  |  |  |  |")
    else:
        for _, row in packet.iterrows():
            title = str(row.get("title", "")).replace("|", "/").replace("\n", " ")[:110]
            note = str(row.get("entity_review_note", "")).replace("|", "/")[:120]
            lines.append(
                f"| {row.get('candidate_id', '')} | {row.get('entity_review_type', '')} | {row.get('candidate_asset_symbol', '')} | {row.get('suggested_asset_symbol', '')} | {row.get('suggested_channel_route', '')} | {note} | {title} |"
            )

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            "- Do not apply these as automatic fixes yet.",
            "- First decide primary-asset policy for protocol exploits and multi-chain regulatory events.",
            "- Add dictionary/rule changes only when the same pattern repeats.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    fix_plan_path = normalize_path(args.fix_plan)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    report_path = normalize_path(args.report)

    if not fix_plan_path.exists():
        print(f"fix plan not found: {fix_plan_path}")
        return 1

    plan = pd.read_csv(fix_plan_path, dtype=str).fillna("")
    packet = plan[plan["recommended_action"].eq("needs_entity_rule_review")].copy()
    if not packet.empty:
        classifications = [classify_review(row) for _, row in packet.iterrows()]
        packet["entity_review_type"] = [item[0] for item in classifications]
        packet["suggested_asset_symbol"] = [item[1] for item in classifications]
        packet["suggested_channel_route"] = [item[2] for item in classifications]
        packet["entity_review_note"] = [item[3] for item in classifications]
    else:
        packet["entity_review_type"] = []
        packet["suggested_asset_symbol"] = []
        packet["suggested_channel_route"] = []
        packet["entity_review_note"] = []

    summary = (
        packet["entity_review_type"]
        .value_counts()
        .rename_axis("entity_review_type")
        .reset_index(name="count")
        if not packet.empty
        else pd.DataFrame(columns=["entity_review_type", "count"])
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    packet.to_csv(output_path, index=False)
    summary.to_csv(summary_path, index=False)
    report_path.write_text(render_report(packet, summary), encoding="utf-8")
    print(f"wrote entity review packet to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
