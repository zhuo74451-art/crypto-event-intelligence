import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
BENCHMARK_ASSETS = {"BTC", "ETH"}
UNCLEAR_SUBTYPES = {"", "other", "needs_taxonomy_review"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build auditable v14 Composer five-stage scores from historical rows.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--group-stats", default=str(ROOT / "results" / "v13_extended_post_hype_removal_group_stats.csv"))
    parser.add_argument("--source-scores", default=str(ROOT / "data" / "source_scores_v14_webhook_split.csv"))
    parser.add_argument("--price-in", default=str(ROOT / "results" / "v13_extended_price_in_report.csv"))
    parser.add_argument("--regime", default=str(ROOT / "results" / "v13_extended_regime_layer_report.csv"))
    parser.add_argument("--prefilter", default=str(ROOT / "data" / "v14_prefilter_results.csv"))
    parser.add_argument("--etf-filtered", default=str(ROOT / "data" / "etf_fund_flow_filtered.csv"))
    parser.add_argument("--exploit-verified", default=str(ROOT / "data" / "active_exploit_verified.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_composer_scores.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_composer_scores_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_composer_scores_report.md"))
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


def index_by(rows: list[dict], field: str) -> dict[str, dict]:
    return {str(row.get(field) or "").strip(): row for row in rows if str(row.get(field) or "").strip()}


def to_stage20(score_100: float) -> float:
    return round(max(0.0, min(20.0, score_100 / 5.0)), 2)


def load_group_stats(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("event_group") or "").strip(): row for row in rows}


def load_source_scores(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("subsource") or "").strip(): row for row in rows}


def source_key(row: dict) -> str:
    source = str(row.get("source") or "").strip()
    if source == "webhook":
        return "webhook_unknown"
    return source


def source_score(row: dict, source_scores: dict[str, dict]) -> tuple[float, str]:
    score_row = source_scores.get(source_key(row), {})
    return safe_float(score_row.get("score")), str(score_row.get("recommended_action") or "missing")


def has_text(row: dict) -> bool:
    return len(str(row.get("title") or "").strip()) >= 8 or len(str(row.get("content") or "").strip()) >= 30


def amount_quality(row: dict, etf_rows: dict[str, dict], exploit_rows: dict[str, dict]) -> tuple[int, str]:
    event_id = str(row.get("event_id") or "").strip()
    subtype = str(row.get("event_subtype") or "").strip()
    if subtype == "etf_or_fund_flow":
        detail = etf_rows.get(event_id, {})
        if str(detail.get("v14_etf_filter_decision") or "") == "keep":
            amount = safe_float(detail.get("parsed_flow_amount_usd"))
            return (20 if amount >= 50_000_000 else 12, "etf_context_verified")
        return 0, "etf_context_failed"
    if subtype == "exploit_or_theft":
        detail = exploit_rows.get(event_id, {})
        if str(detail.get("urgent_eligible") or "").lower() == "true":
            return 20, "exploit_amount_context_verified"
        return 0, "exploit_amount_context_failed"
    return 8, "amount_not_required"


def stage1_relevance(row: dict, source_scores: dict[str, dict], group_stats: dict[str, dict], min_sample_count: int) -> tuple[float, list[str]]:
    score = 100.0
    reasons = []
    asset = str(row.get("asset_symbol") or "").strip().upper()
    subtype = str(row.get("event_subtype") or row.get("event_type") or "").strip()
    src_score, src_action = source_score(row, source_scores)
    sample_count = int(safe_float(group_stats.get(subtype, {}).get("sample_count")))
    if not asset:
        score -= 45
        reasons.append("missing_asset")
    if asset in BENCHMARK_ASSETS:
        score -= 40
        reasons.append("benchmark_asset")
    if subtype in UNCLEAR_SUBTYPES:
        score -= 45
        reasons.append("unclear_taxonomy")
    if src_score < 50 or src_action == "block":
        score -= 35
        reasons.append("low_source_score")
    if sample_count < min_sample_count:
        score -= 25
        reasons.append("low_sample_count")
    if not has_text(row):
        score -= 15
        reasons.append("thin_text")
    return max(0.0, min(100.0, score)), reasons or ["pass"]


def hard_block_reasons(
    row: dict,
    source_scores: dict[str, dict],
    group_stats: dict[str, dict],
    etf_rows: dict[str, dict],
    exploit_rows: dict[str, dict],
    prefilter_rows: dict[str, dict],
    min_sample_count: int,
) -> list[str]:
    event_id = str(row.get("event_id") or "").strip()
    asset = str(row.get("asset_symbol") or "").strip().upper()
    subtype = str(row.get("event_subtype") or row.get("event_type") or "").strip()
    src_score, src_action = source_score(row, source_scores)
    sample_count = int(safe_float(group_stats.get(subtype, {}).get("sample_count")))
    reasons = []
    prefilter = prefilter_rows.get(event_id, {})
    if str(prefilter.get("prefilter_passed") or "true").lower() != "true":
        for reason in str(prefilter.get("prefilter_blocks") or "").split(","):
            if reason and reason != "pass":
                reasons.append(f"prefilter_{reason}")
    if not asset:
        reasons.append("missing_asset")
    if asset in BENCHMARK_ASSETS:
        reasons.append("benchmark_asset")
    if subtype in UNCLEAR_SUBTYPES:
        reasons.append("unclear_taxonomy")
    if src_score < 50 or src_action == "block":
        reasons.append("low_source_score")
    if sample_count < min_sample_count:
        reasons.append("low_sample_count")
    if subtype == "etf_or_fund_flow" and str(etf_rows.get(event_id, {}).get("v14_etf_filter_decision") or "") != "keep":
        reasons.append("etf_context_failed")
    if subtype == "exploit_or_theft" and str(exploit_rows.get(event_id, {}).get("urgent_eligible") or "").lower() != "true":
        reasons.append("exploit_amount_context_failed")
    return reasons


def stage2_structuring(row: dict, etf_rows: dict[str, dict], exploit_rows: dict[str, dict]) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []
    if str(row.get("asset_symbol") or "").strip():
        score += 20
    else:
        reasons.append("missing_asset")
    if str(row.get("event_time_utc") or row.get("event_time") or "").strip():
        score += 20
    else:
        reasons.append("missing_time")
    if str(row.get("source") or "").strip():
        score += 15
    else:
        reasons.append("missing_source")
    if str(row.get("event_subtype") or row.get("event_type") or "").strip() not in UNCLEAR_SUBTYPES:
        score += 20
    else:
        reasons.append("unclear_taxonomy")
    amount_points, amount_reason = amount_quality(row, etf_rows, exploit_rows)
    score += amount_points
    reasons.append(amount_reason)
    if has_text(row):
        score += 5
    else:
        reasons.append("thin_text")
    return max(0.0, min(100.0, score)), reasons


def stage3_attribution(row: dict, price_in_rows: dict[str, dict], regime_rows: dict[str, dict]) -> tuple[float, list[str]]:
    event_id = str(row.get("event_id") or "").strip()
    subtype = str(row.get("event_subtype") or "").strip()
    price_row = price_in_rows.get(event_id, {})
    regime_row = regime_rows.get(subtype, {})
    score = 100.0
    reasons = []
    price_flag = str(price_row.get("price_in_flag") or "")
    if price_flag == "severe_price_in":
        score -= 45
        reasons.append("severe_price_in")
    elif not price_row:
        score -= 15
        reasons.append("missing_price_in_check")
    else:
        ratio = safe_float(price_row.get("price_in_ratio"))
        if ratio > 0.75:
            score -= 25
            reasons.append("high_price_in_ratio")
        elif ratio > 0.5:
            score -= 10
            reasons.append("medium_price_in_ratio")
    if not regime_row:
        score -= 20
        reasons.append("missing_regime_layer")
    elif int(safe_float(regime_row.get("sample_count"))) < 20:
        score -= 10
        reasons.append("thin_regime_sample")
    return max(0.0, min(100.0, score)), reasons or ["pass"]


def magnitude_bucket(value: float) -> str:
    if value <= 0:
        return "unknown"
    if value < 1_000_000:
        return "small"
    if value < 10_000_000:
        return "medium"
    if value < 100_000_000:
        return "large"
    return "xlarge"


def row_magnitude(row: dict, etf_rows: dict[str, dict], exploit_rows: dict[str, dict]) -> float:
    event_id = str(row.get("event_id") or "").strip()
    subtype = str(row.get("event_subtype") or "").strip()
    if subtype == "etf_or_fund_flow":
        return safe_float(etf_rows.get(event_id, {}).get("parsed_flow_amount_usd"))
    if subtype == "exploit_or_theft":
        return safe_float(exploit_rows.get(event_id, {}).get("estimated_amount_usd"))
    return 0.0


def stage4_historical(
    row: dict,
    all_rows: list[dict],
    etf_rows: dict[str, dict],
    exploit_rows: dict[str, dict],
    min_exact_matches: int = 3,
) -> tuple[float, list[str], dict]:
    event_id = str(row.get("event_id") or "").strip()
    subtype = str(row.get("event_subtype") or "").strip()
    asset = str(row.get("asset_symbol") or "").strip().upper()
    bucket = magnitude_bucket(row_magnitude(row, etf_rows, exploit_rows))
    matches = []
    for candidate in all_rows:
        candidate_id = str(candidate.get("event_id") or "").strip()
        if candidate_id == event_id:
            continue
        if str(candidate.get("event_subtype") or "").strip() != subtype:
            continue
        if str(candidate.get("asset_symbol") or "").strip().upper() != asset:
            continue
        if magnitude_bucket(row_magnitude(candidate, etf_rows, exploit_rows)) != bucket:
            continue
        value = safe_float(candidate.get("abnormal_vs_btc_1h"))
        matches.append((candidate_id, value))
    if len(matches) < min_exact_matches:
        return 5.0, ["similar_sample_count_below_3"], {
            "historical_match_key": f"{subtype}|{asset}|{bucket}",
            "historical_similar_count": len(matches),
            "historical_avg_abnormal_vs_btc_1h": "",
            "historical_false_positive_rate": "",
            "historical_similar_event_ids": ",".join(item[0] for item in matches[:3]),
        }
    values = [item[1] for item in matches]
    avg_1h = sum(values) / len(values)
    win_rate = sum(1 for value in values if value > 0) / len(values)
    false_positive_rate = sum(1 for value in values if abs(value) < 0.003) / len(values)
    score = 10.0
    if len(matches) >= 8:
        score += 3.0
    if false_positive_rate <= 0.5:
        score += 3.0
    if abs(avg_1h) > 0.003:
        score += 3.0
    if win_rate >= 0.6 or win_rate <= 0.4:
        score += 1.0
    reasons = ["pass"]
    if false_positive_rate > 0.5:
        reasons = ["high_historical_false_positive_rate"]
    return min(20.0, score), reasons, {
        "historical_match_key": f"{subtype}|{asset}|{bucket}",
        "historical_similar_count": len(matches),
        "historical_avg_abnormal_vs_btc_1h": f"{avg_1h:.6f}",
        "historical_false_positive_rate": f"{false_positive_rate:.4f}",
        "historical_similar_event_ids": ",".join(item[0] for item in matches[:3]),
    }


def stage4_group_historical(row: dict, group_stats: dict[str, dict], min_sample_count: int) -> tuple[float, list[str]]:
    subtype = str(row.get("event_subtype") or "").strip()
    stats = group_stats.get(subtype, {})
    sample_count = int(safe_float(stats.get("sample_count")))
    win_1h = safe_float(stats.get("win_rate_vs_btc_1h"))
    avg_1h = safe_float(stats.get("avg_abnormal_vs_btc_1h"))
    win_24h = safe_float(stats.get("win_rate_vs_btc_24h"))
    score = 0.0
    reasons = []
    if sample_count >= 100:
        score += 40
    elif sample_count >= 50:
        score += 30
    elif sample_count >= min_sample_count:
        score += 20
    else:
        reasons.append("low_sample_count")
    score += max(0.0, min(30.0, (win_1h - 0.5) * 100))
    score += max(0.0, min(20.0, avg_1h * 1000))
    score += max(0.0, min(10.0, (win_24h - 0.5) * 50))
    if win_1h < 0.55:
        reasons.append("weak_1h_win_rate")
    if avg_1h < 0.003:
        reasons.append("weak_1h_avg_abnormal")
    return max(0.0, min(100.0, score)), reasons or ["pass"]


def stage5_readability(row: dict) -> tuple[float, list[str]]:
    title = str(row.get("title") or "").strip()
    content = str(row.get("content") or "").strip()
    score = 100.0
    reasons = []
    if len(title) < 12:
        score -= 20
        reasons.append("short_title")
    if len(title) > 110:
        score -= 10
        reasons.append("long_title")
    if len(content) > 2500:
        score -= 15
        reasons.append("noisy_long_content")
    if any(term in content.lower() for term in ["cookie policy", "sign up", "advertise", "all rights reserved"]):
        score -= 15
        reasons.append("webpage_boilerplate")
    return max(0.0, min(100.0, score)), reasons or ["pass"]


def gate_route(stages: dict[str, float], hard_reasons: list[str]) -> tuple[bool, str, str]:
    gate_reasons = list(hard_reasons)
    if stages["trading_relevance_score"] < 15:
        gate_reasons.append("trading_relevance_below_15")
    if stages["attribution_score"] < 12:
        gate_reasons.append("attribution_below_12")
    if stages["historical_confidence_score"] < 10:
        gate_reasons.append("historical_confidence_below_10")
    if gate_reasons:
        return False, ",".join(dict.fromkeys(gate_reasons)), "review" if not hard_reasons else "block"
    if stages["structuring_score"] >= 15 and stages["readability_score"] >= 15:
        return True, "pass", "interrupt_candidate"
    if stages["structuring_score"] >= 10 or stages["readability_score"] >= 10:
        return True, "pass", "digest_candidate"
    return True, "pass", "review"


def render_report(rows: list[dict], summary: dict) -> str:
    route_counts = Counter(row["composer_route_hint"] for row in rows)
    lines = [
        "# v14 Composer Scores Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- gate_passed_count: {summary['gate_passed_count']}",
        f"- pass_digest_count: {summary['pass_digest_count']}",
        f"- review_count: {summary['review_count']}",
        f"- block_count: {summary['block_count']}",
        "",
        "## Route Hints",
        "",
    ]
    for route, count in route_counts.most_common():
        lines.append(f"- {route}: {count}")
    lines.extend(["", "## Top Composer Rows", "", "| gate | route | relevance | structure | attribution | history | readability | asset | subtype | title |", "|---|---|---:|---:|---:|---:|---:|---|---|---|"])
    for row in rows[:30]:
        title = str(row.get("title") or "").replace("|", "\\|")[:100]
        lines.append(
            f"| {row['composer_gate_passed']} | {row['composer_route_hint']} | {row['trading_relevance_score']} | {row['structuring_score']} | {row['attribution_score']} | {row['historical_confidence_score']} | {row['readability_score']} | {row.get('asset_symbol','')} | {row.get('event_subtype','')} | {title} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    backfill = read_rows(normalize_path(args.backfill))
    group_stats = load_group_stats(read_rows(normalize_path(args.group_stats)))
    source_scores = load_source_scores(read_rows(normalize_path(args.source_scores)))
    price_in_rows = index_by(read_rows(normalize_path(args.price_in)), "event_id")
    regime_rows = load_group_stats(read_rows(normalize_path(args.regime)))
    prefilter_rows = index_by(read_rows(normalize_path(args.prefilter)), "event_id")
    etf_rows = index_by(read_rows(normalize_path(args.etf_filtered)), "event_id")
    exploit_rows = index_by(read_rows(normalize_path(args.exploit_verified)), "event_id")

    output = []
    for row in backfill:
        s1, r1 = stage1_relevance(row, source_scores, group_stats, args.min_sample_count)
        s2, r2 = stage2_structuring(row, etf_rows, exploit_rows)
        s3, r3 = stage3_attribution(row, price_in_rows, regime_rows)
        s4, r4, historical_meta = stage4_historical(row, backfill, etf_rows, exploit_rows)
        s5, r5 = stage5_readability(row)
        stages = {
            "trading_relevance_score": to_stage20(s1),
            "structuring_score": to_stage20(s2),
            "attribution_score": to_stage20(s3),
            "historical_confidence_score": round(s4, 2),
            "readability_score": to_stage20(s5),
        }
        hard_reasons = hard_block_reasons(row, source_scores, group_stats, etf_rows, exploit_rows, prefilter_rows, args.min_sample_count)
        gate_passed, block_reason, route = gate_route(stages, hard_reasons)
        item = dict(row)
        item.update(stages)
        item["composer_gate_passed"] = "true" if gate_passed else "false"
        item["composer_block_reason"] = block_reason
        item["composer_route_hint"] = route
        item["stage1_reasons"] = ",".join(r1)
        item["stage2_reasons"] = ",".join(r2)
        item["stage3_reasons"] = ",".join(r3)
        item["stage4_reasons"] = ",".join(r4)
        item["stage5_reasons"] = ",".join(r5)
        item["composer_hard_block_reasons"] = ",".join(hard_reasons) if hard_reasons else "pass"
        item.update(historical_meta)
        output.append(item)
    output.sort(key=lambda row: (row["composer_gate_passed"] != "true", row["composer_route_hint"] == "block", -safe_float(row["historical_confidence_score"]), -safe_float(row["trading_relevance_score"])))
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(output),
        "gate_passed_count": sum(1 for row in output if row["composer_gate_passed"] == "true"),
        "pass_digest_count": sum(1 for row in output if row["composer_route_hint"] in {"digest_candidate", "interrupt_candidate"}),
        "interrupt_candidate_count": sum(1 for row in output if row["composer_route_hint"] == "interrupt_candidate"),
        "review_count": sum(1 for row in output if row["composer_route_hint"] == "review"),
        "block_count": sum(1 for row in output if row["composer_route_hint"] == "block"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.markdown_output).write_text(render_report(output, summary), encoding="utf-8")
    print(f"input_rows={len(output)}")
    print(f"pass_digest_count={summary['pass_digest_count']}")
    print(f"interrupt_candidate_count={summary['interrupt_candidate_count']}")
    print(f"review_count={summary['review_count']}")
    print(f"block_count={summary['block_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
