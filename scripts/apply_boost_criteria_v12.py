import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply strict v12 boost/downrank/digest-only criteria to event performance rows.")
    parser.add_argument("--matrix", default=str(ROOT / "results" / "event_type_performance_matrix_non_benchmark_alt.csv"))
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--contamination-summary", default=str(ROOT / "results" / "v12_whale_position_contamination_summary.csv"))
    parser.add_argument("--hack-summary", default=str(ROOT / "results" / "v12_hack_classification_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_signal_policy_v12.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v12_boost_criteria_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v12_boost_criteria_summary.csv"))
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


def safe_float(value, default=0.0) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default


def safe_int(value, default=0) -> int:
    try:
        return int(float(str(value or "").strip()))
    except ValueError:
        return default


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def backfill_diversity(rows: list[dict]) -> dict[str, dict]:
    grouped = defaultdict(list)
    for row in rows:
        keys = {
            str(row.get("event_type") or "").strip(),
            str(row.get("event_subtype") or "").strip(),
        }
        for key in keys:
            if key:
                grouped[key].append(row)
    stats = {}
    for key, items in grouped.items():
        assets = [str(row.get("asset_symbol") or "").strip().upper() for row in items if row.get("asset_symbol")]
        unique_assets = len(set(assets))
        hype_count = sum(1 for asset in assets if asset == "HYPE")
        counts = defaultdict(int)
        for asset in assets:
            counts[asset] += 1
        max_single = max(counts.values()) if counts else 0
        total = len(items)
        stats[key] = {
            "unique_assets": unique_assets,
            "hype_ratio": round(hype_count / total, 4) if total else 0.0,
            "max_single_asset_ratio": round(max_single / total, 4) if total else 0.0,
        }
    return stats


def decide(row: dict, diversity: dict[str, dict], contamination_failed: bool) -> tuple[str, float, float, str]:
    name = str(row.get("event_subtype") or row.get("event_type") or "").strip()
    sample_count = safe_int(row.get("sample_count"))
    count24 = safe_int(row.get("computed_24h_count"))
    avg24 = safe_float(row.get("avg_abnormal_primary_24h"))
    win24 = safe_float(row.get("win_rate_primary_24h"))
    matrix_status = str(row.get("matrix_status") or "").strip()
    d = diversity.get(name) or diversity.get(str(row.get("event_type") or "").strip()) or {}
    unique_assets = int(d.get("unique_assets", 0) or 0)
    hype_ratio = float(d.get("hype_ratio", 0.0) or 0.0)
    single_asset_ratio = float(d.get("max_single_asset_ratio", 0.0) or 0.0)

    if name in {"market_sentiment", "analyst_opinion_or_prediction", "fund_recovery", "old_case_update"}:
        return "digest_only", -25.0, 2.0, "主观观点或旧案追踪，只进摘要，不进盘中雷达。"

    if matrix_status == "weak_or_context_only":
        return "digest_only", -20.0, 1.8, "历史表现更像背景信息，降低盘中曝光。"

    if count24 >= 30 and sample_count >= 50 and avg24 >= 0.05 and win24 >= 0.65:
        checks = []
        if unique_assets < 10:
            checks.append("资产覆盖不足")
        if hype_ratio > 0.15:
            checks.append("HYPE 占比过高")
        if single_asset_ratio > 0.30:
            checks.append("单资产集中度过高")
        if contamination_failed and name in {"whale_wallet_position", "whale_position"}:
            checks.append("鲸鱼仓位污染检查未通过")
        if not checks:
            return "boost", 10.0, 0.8, "满足严格历史样本、表现和污染检查，可提高观察优先级。"
        return "collect_more", -4.0, 1.3, "表现强但未通过污染/多样性检查：" + "、".join(checks)

    if count24 >= 10 and (win24 <= 0.45 or avg24 <= 0):
        return "digest_only", -18.0, 1.8, "24h 历史表现偏弱，盘中降权，保留摘要观察。"

    return "collect_more", -4.0, 1.2, "样本或稳定性不足，继续收集，不做强路由结论。"


def aggregate_matrix(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        name = str(row.get("event_subtype") or row.get("event_type") or "").strip()
        if name:
            grouped[name].append(row)
    output = []
    for name, items in grouped.items():
        sample_count = sum(safe_int(row.get("sample_count")) for row in items)
        computed_24h = sum(safe_int(row.get("computed_24h_count")) for row in items)
        computed_1h = sum(safe_int(row.get("computed_1h_count")) for row in items)
        computed_4h = sum(safe_int(row.get("computed_4h_count")) for row in items)
        computed_72h = sum(safe_int(row.get("computed_72h_count")) for row in items)

        def weighted_avg(field: str, weight_field: str) -> float:
            numerator = 0.0
            denominator = 0
            for row in items:
                weight = safe_int(row.get(weight_field))
                numerator += safe_float(row.get(field)) * weight
                denominator += weight
            return round(numerator / denominator, 6) if denominator else 0.0

        statuses = {str(row.get("matrix_status") or "") for row in items}
        matrix_status = "insufficient_sample"
        if computed_24h >= 10:
            avg24 = weighted_avg("avg_abnormal_primary_24h", "computed_24h_count")
            matrix_status = "promising_needs_validation" if abs(avg24) >= 0.01 else "weak_or_context_only"
        if computed_24h < 10 and max(computed_1h, computed_4h, computed_72h) >= 10:
            matrix_status = "short_horizon_only"

        event_types = [str(row.get("event_type") or "").strip() for row in items if row.get("event_type")]
        output.append(
            {
                "event_type": Counter(event_types).most_common(1)[0][0] if event_types else "unknown",
                "event_subtype": name,
                "sample_count": sample_count,
                "computed_1h_count": computed_1h,
                "computed_4h_count": computed_4h,
                "computed_24h_count": computed_24h,
                "computed_72h_count": computed_72h,
                "avg_abnormal_primary_1h": weighted_avg("avg_abnormal_primary_1h", "computed_1h_count"),
                "avg_abnormal_primary_4h": weighted_avg("avg_abnormal_primary_4h", "computed_4h_count"),
                "avg_abnormal_primary_24h": weighted_avg("avg_abnormal_primary_24h", "computed_24h_count"),
                "avg_abnormal_primary_72h": weighted_avg("avg_abnormal_primary_72h", "computed_72h_count"),
                "win_rate_primary_24h": weighted_avg("win_rate_primary_24h", "computed_24h_count"),
                "matrix_status": matrix_status,
                "source_row_count": len(items),
                "source_statuses": ",".join(sorted(status for status in statuses if status)),
            }
        )
    output.sort(key=lambda row: (-safe_int(row.get("computed_24h_count")), row["event_subtype"]))
    return output


def main() -> int:
    args = parse_args()
    matrix = aggregate_matrix(read_rows(normalize_path(args.matrix)))
    backfill = read_rows(normalize_path(args.backfill))
    contamination = read_rows(normalize_path(args.contamination_summary))
    contamination_failed = bool(contamination and contamination[0].get("status") == "fail")
    diversity = backfill_diversity(backfill)

    policy_rows = []
    report_rows = []
    for row in matrix:
        name = str(row.get("event_subtype") or row.get("event_type") or "").strip()
        if not name:
            continue
        action, priority_delta, cooldown_multiplier, reason = decide(row, diversity, contamination_failed)
        d = diversity.get(name, {})
        policy_rows.append(
            {
                "policy_scope": "event_subtype",
                "name": name,
                "sample_count": row.get("sample_count", ""),
                "valid_24h_count": row.get("computed_24h_count", ""),
                "avg_abnormal_primary_24h": row.get("avg_abnormal_primary_24h", ""),
                "win_rate_primary_24h": row.get("win_rate_primary_24h", ""),
                "false_positive_like_rate": "",
                "matrix_status": row.get("matrix_status", ""),
                "tg_action": action,
                "priority_delta": priority_delta,
                "cooldown_multiplier": cooldown_multiplier,
                "reason_cn": reason,
            }
        )
        report_rows.append(
            {
                "event_type": row.get("event_type", ""),
                "event_subtype": name,
                "sample_count": row.get("sample_count", ""),
                "computed_24h_count": row.get("computed_24h_count", ""),
                "avg_abnormal_primary_24h": row.get("avg_abnormal_primary_24h", ""),
                "win_rate_primary_24h": row.get("win_rate_primary_24h", ""),
                "unique_assets": d.get("unique_assets", 0),
                "hype_ratio": d.get("hype_ratio", 0),
                "max_single_asset_ratio": d.get("max_single_asset_ratio", 0),
                "tg_action": action,
                "reason_cn": reason,
            }
        )
    fields = ["policy_scope", "name", "sample_count", "valid_24h_count", "avg_abnormal_primary_24h", "win_rate_primary_24h", "false_positive_like_rate", "matrix_status", "tg_action", "priority_delta", "cooldown_multiplier", "reason_cn"]
    write_rows(normalize_path(args.output), policy_rows, fields)
    write_rows(normalize_path(args.report), report_rows, list(report_rows[0].keys()) if report_rows else ["event_subtype"])
    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "policy_rows": len(policy_rows),
        "boost_count": sum(1 for row in policy_rows if row["tg_action"] == "boost"),
        "digest_only_count": sum(1 for row in policy_rows if row["tg_action"] == "digest_only"),
        "collect_more_count": sum(1 for row in policy_rows if row["tg_action"] == "collect_more"),
        "contamination_failed": str(contamination_failed).lower(),
        "output": str(normalize_path(args.output)),
        "report": str(normalize_path(args.report)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"policy_rows={len(policy_rows)}")
    print(f"boost_count={summary['boost_count']}")
    print(f"digest_only_count={summary['digest_only_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
