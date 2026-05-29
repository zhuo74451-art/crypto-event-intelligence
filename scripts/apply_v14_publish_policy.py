import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
BENCHMARK_ASSETS = {"BTC", "ETH"}
BLOCKED_SUBTYPES = {"other", "needs_taxonomy_review", ""}
INTERRUPT_SUBTYPES = {"listing_delisting", "active_exploit"}
DIGEST_ELIGIBLE_SUBTYPES = {"exploit_or_theft", "etf_or_fund_flow", "stablecoin_supply_or_flow", "upgrade_or_fork"}
PUBLISHABLE_FLOW_SUBTYPES = {"etf_creation_redemption", "cex_netflow"}
BLOCKED_FLOW_SUBTYPES = {"etf_macro_news", "institutional_disclosure", "flow_unclear"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply v14 Claude-directed publishing policy to backtested rows.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--group-stats", default=str(ROOT / "results" / "v13_extended_post_hype_removal_group_stats.csv"))
    parser.add_argument("--source-scores", default=str(ROOT / "data" / "source_scores_v14_webhook_split.csv"))
    parser.add_argument("--composer-scores", default=str(ROOT / "data" / "v14_composer_scores.csv"))
    parser.add_argument("--flow-subtypes", default=str(ROOT / "data" / "v14_flow_event_subtypes.csv"))
    parser.add_argument("--upgrade-events", default=str(ROOT / "data" / "v14_upgrade_events.csv"))
    parser.add_argument("--criteria-eval", default=str(ROOT / "data" / "v14_publishable_criteria_eval.csv"))
    parser.add_argument("--etf-filtered", default=str(ROOT / "data" / "etf_fund_flow_filtered.csv"))
    parser.add_argument("--exploit-verified", default=str(ROOT / "data" / "active_exploit_verified.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_publish_policy_candidates.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_publish_policy_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_publish_policy_report.md"))
    parser.add_argument("--min-source-score", type=float, default=50.0)
    parser.add_argument("--min-sample-count", type=int, default=20)
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


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def load_group_stats(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("event_group") or "").strip(): row for row in rows}


def load_source_scores(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("subsource") or "").strip(): row for row in rows}


def load_composer_scores(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("event_id") or "").strip(): row for row in rows}


def load_flow_subtypes(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("event_id") or "").strip(): row for row in rows}


def load_upgrade_events(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("event_id") or "").strip(): row for row in rows}


def load_criteria(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("event_id") or "").strip(): row for row in rows}


def id_set(rows: list[dict], id_field: str, predicate) -> set[str]:
    return {str(row.get(id_field) or "").strip() for row in rows if predicate(row)}


def source_score_for(row: dict, source_scores: dict[str, dict]) -> tuple[float, str]:
    source = str(row.get("source") or "").strip()
    if source == "webhook":
        source = "webhook_unknown"
    score_row = source_scores.get(source, {})
    return safe_float(score_row.get("score")), str(score_row.get("recommended_action") or "missing")


def policy_decision(
    row: dict,
    args,
    group_stats: dict[str, dict],
    source_scores: dict[str, dict],
    composer_scores: dict[str, dict],
    flow_subtypes: dict[str, dict],
    upgrade_events: dict[str, dict],
    criteria_rows: dict[str, dict],
    etf_keep_ids: set[str],
    exploit_urgent_ids: set[str],
) -> dict:
    event_id = str(row.get("event_id") or "").strip()
    asset = str(row.get("asset_symbol") or "").strip().upper()
    subtype = str(row.get("event_subtype") or row.get("event_type") or "").strip()
    source_score, source_action = source_score_for(row, source_scores)
    stats = group_stats.get(subtype, {})
    sample_count = int(safe_float(stats.get("sample_count")))
    win_rate_1h = safe_float(stats.get("win_rate_vs_btc_1h"))
    avg_1h = safe_float(stats.get("avg_abnormal_vs_btc_1h"))
    composer = composer_scores.get(event_id, {})
    composer_route = str(composer.get("composer_route_hint") or "")
    composer_gate_passed = str(composer.get("composer_gate_passed") or "").lower() == "true"
    flow = flow_subtypes.get(event_id, {})
    upgrade = upgrade_events.get(event_id, {})
    criteria = criteria_rows.get(event_id, {})
    refined_flow_subtype = str(flow.get("refined_subtype") or flow.get("v14_flow_subtype") or "")
    upgrade_route = str(upgrade.get("upgrade_route") or "")
    reasons = []

    if subtype in BLOCKED_SUBTYPES:
        reasons.append("blocked_unclear_taxonomy")
    if asset in BENCHMARK_ASSETS:
        reasons.append("blocked_benchmark_asset")
    if sample_count < args.min_sample_count:
        reasons.append("blocked_low_sample_count")
    if source_score < args.min_source_score or source_action == "block":
        reasons.append("blocked_low_source_score")
    if subtype == "etf_or_fund_flow" and event_id not in etf_keep_ids:
        reasons.append("blocked_etf_filter_failed")
    if subtype == "etf_or_fund_flow" and refined_flow_subtype in BLOCKED_FLOW_SUBTYPES:
        reasons.append(f"blocked_flow_subtype_{refined_flow_subtype}")
    if subtype == "etf_or_fund_flow" and refined_flow_subtype and refined_flow_subtype not in PUBLISHABLE_FLOW_SUBTYPES:
        reasons.append(f"blocked_non_publishable_flow_subtype_{refined_flow_subtype}")
    if subtype == "exploit_or_theft" and event_id not in exploit_urgent_ids:
        reasons.append("blocked_exploit_amount_context_failed")
    if subtype == "upgrade_or_fork" and upgrade_route not in {"digest", "background"}:
        reasons.append("blocked_upgrade_quality_failed")
    if not composer_gate_passed or composer_route == "block":
        reasons.append("blocked_by_composer_gate")
    if criteria and str(criteria.get("criteria_passed") or "").lower() != "true":
        reasons.append(f"blocked_publishable_criteria:{criteria.get('criteria_block_reason','')}")

    quality_bonus = 0
    if subtype == "etf_or_fund_flow" and event_id in etf_keep_ids:
        quality_bonus += 25
    if subtype == "exploit_or_theft" and event_id in exploit_urgent_ids:
        quality_bonus += 25
    if source_action == "trust":
        quality_bonus += 5

    publish_score = 0
    publish_score += min(source_score, 80) * 0.35
    publish_score += min(sample_count, 100) * 0.25
    publish_score += max(0, win_rate_1h * 100 - 50) * 0.20
    publish_score += max(0, avg_1h * 1000) * 0.20
    publish_score += quality_bonus

    if reasons:
        route = "block"
    elif composer_route == "interrupt_candidate" and subtype in INTERRUPT_SUBTYPES and sample_count >= 10 and source_score >= 70:
        route = "interrupt"
    elif subtype == "upgrade_or_fork" and composer_route in {"digest_candidate", "interrupt_candidate"} and upgrade_route in {"digest", "background"} and publish_score >= 20:
        route = "digest"
    elif composer_route in {"digest_candidate", "interrupt_candidate"} and subtype in DIGEST_ELIGIBLE_SUBTYPES and publish_score >= 60:
        route = "digest"
    else:
        route = "digest" if publish_score >= 60 else "block"
        if route == "block":
            reasons.append("blocked_publish_score_below_60")

    output = dict(row)
    output.update(
        {
            "v14_policy_route": route,
            "v14_policy_reasons": ",".join(reasons) if reasons else "pass",
            "v14_publish_score": round(publish_score, 2),
            "v14_source_score": round(source_score, 2),
            "v14_source_action": source_action,
            "v14_event_group_sample_count": sample_count,
            "v14_event_group_win_rate_1h": win_rate_1h,
            "v14_event_group_avg_abnormal_vs_btc_1h": avg_1h,
            "v14_quality_bonus": quality_bonus,
            "refined_flow_subtype": refined_flow_subtype,
            "flow_direction": flow.get("flow_direction", ""),
            "flow_data_source": flow.get("data_source", ""),
            "upgrade_type": upgrade.get("upgrade_type", ""),
            "upgrade_route": upgrade_route,
            "upgrade_block_reason": upgrade.get("upgrade_block_reason", ""),
            "criteria_passed": criteria.get("criteria_passed", ""),
            "criteria_block_reason": criteria.get("criteria_block_reason", ""),
            "source_tier": criteria.get("source_tier", ""),
            "price_in_5m": criteria.get("price_in_5m", ""),
            "price_in_15m": criteria.get("price_in_15m", ""),
            "price_in_1h": criteria.get("price_in_1h", ""),
            "composer_gate_passed": composer.get("composer_gate_passed", ""),
            "composer_block_reason": composer.get("composer_block_reason", ""),
            "composer_route_hint": composer.get("composer_route_hint", ""),
            "composer_hard_block_reasons": composer.get("composer_hard_block_reasons", ""),
        }
    )
    return output


def render_report(rows: list[dict], summary: dict) -> str:
    route_counts = Counter(row["v14_policy_route"] for row in rows)
    reason_counts = Counter(
        reason
        for row in rows
        for reason in str(row.get("v14_policy_reasons") or "").split(",")
        if reason and reason != "pass"
    )
    lines = [
        "# v14 Publish Policy Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- digest_rows: {summary['digest_rows']}",
        f"- interrupt_rows: {summary['interrupt_rows']}",
        f"- block_rows: {summary['block_rows']}",
        "",
        "## Route Counts",
        "",
    ]
    for route, count in route_counts.most_common():
        lines.append(f"- {route}: {count}")
    lines.extend(["", "## Top Block Reasons", ""])
    for reason, count in reason_counts.most_common(12):
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Digest Preview Candidates", "", "| route | score | source_score | samples | asset | subtype | title |", "|---|---:|---:|---:|---|---|---|"])
    for row in [item for item in rows if item["v14_policy_route"] != "block"][:30]:
        title = str(row.get("title") or "").replace("|", "\\|")[:100]
        lines.append(
            f"| {row['v14_policy_route']} | {row['v14_publish_score']} | {row['v14_source_score']} | {row['v14_event_group_sample_count']} | {row.get('asset_symbol','')} | {row.get('event_subtype','')} | {title} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    backfill = read_rows(normalize_path(args.backfill))
    group_stats = load_group_stats(read_rows(normalize_path(args.group_stats)))
    source_scores = load_source_scores(read_rows(normalize_path(args.source_scores)))
    composer_scores = load_composer_scores(read_rows(normalize_path(args.composer_scores)))
    flow_subtypes = load_flow_subtypes(read_rows(normalize_path(args.flow_subtypes)))
    upgrade_events = load_upgrade_events(read_rows(normalize_path(args.upgrade_events)))
    criteria_rows = load_criteria(read_rows(normalize_path(args.criteria_eval)))
    etf_keep_ids = id_set(
        read_rows(normalize_path(args.etf_filtered)),
        "event_id",
        lambda row: str(row.get("v14_etf_filter_decision") or "") == "keep",
    )
    exploit_urgent_ids = id_set(
        read_rows(normalize_path(args.exploit_verified)),
        "event_id",
        lambda row: str(row.get("urgent_eligible") or "").lower() == "true",
    )
    output = [
        policy_decision(row, args, group_stats, source_scores, composer_scores, flow_subtypes, upgrade_events, criteria_rows, etf_keep_ids, exploit_urgent_ids)
        for row in backfill
    ]
    output.sort(key=lambda row: (row["v14_policy_route"] == "block", -safe_float(row["v14_publish_score"])))
    fields = list(output[0].keys()) if output else ["event_id"]
    write_rows(normalize_path(args.output), output, fields)
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(output),
        "digest_rows": sum(1 for row in output if row["v14_policy_route"] == "digest"),
        "interrupt_rows": sum(1 for row in output if row["v14_policy_route"] == "interrupt"),
        "block_rows": sum(1 for row in output if row["v14_policy_route"] == "block"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.markdown_output).write_text(render_report(output, summary), encoding="utf-8")
    print(f"input_rows={len(output)}")
    print(f"digest_rows={summary['digest_rows']}")
    print(f"interrupt_rows={summary['interrupt_rows']}")
    print(f"block_rows={summary['block_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
