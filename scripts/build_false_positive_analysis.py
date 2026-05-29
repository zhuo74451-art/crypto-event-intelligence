import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze likely false-positive/noisy TG alerts from outcomes and radar decisions.")
    parser.add_argument("--outcomes", default=str(ROOT / "data" / "tg_alert_outcomes.csv"))
    parser.add_argument("--decision-log", default=str(ROOT / "data" / "tg_radar_decision_log.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "false_positive_analysis.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "false_positive_analysis_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "false_positive_analysis.md"))
    parser.add_argument("--flat-threshold", type=float, default=0.005, help="Abs abnormal return below this is treated as flat/no reaction.")
    parser.add_argument("--negative-threshold", type=float, default=-0.01, help="Abnormal return below this is treated as adverse.")
    return parser.parse_args()


def path_value(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if raw == "":
        return None
    try:
        return float(raw)
    except Exception:
        return None


def latest_abnormal(row: dict) -> tuple[str, float | None]:
    for horizon in ("72h", "24h", "4h", "1h"):
        value = safe_float(row.get(f"abnormal_primary_{horizon}"))
        if value is not None:
            return horizon, value
    return "", None


def classify_outcome(row: dict, flat_threshold: float, negative_threshold: float) -> tuple[str, str]:
    horizon, value = latest_abnormal(row)
    quality = str(row.get("quality_status", "") or "").lower()
    pending = str(row.get("horizons_pending", "") or "")
    priced_in = str(row.get("priced_in_flag", "") or "").lower()
    if quality not in {"ok", "partial"}:
        return "unusable_quality", "质量不可用"
    if value is None:
        return "pending_no_outcome", "还没有可计算收益"
    if horizon in {"1h", "4h"} and ("24h" in pending or "72h" in pending):
        maturity_note = "仅短周期"
    else:
        maturity_note = horizon
    if priced_in and priced_in != "none":
        return "priced_in_risk", f"{maturity_note}，发布前已有反应"
    if value <= negative_threshold:
        return "adverse_reaction", f"{maturity_note} abnormal {value:.2%}"
    if abs(value) <= flat_threshold:
        return "flat_no_reaction", f"{maturity_note} abnormal {value:.2%}"
    if value > flat_threshold:
        return "positive_followthrough", f"{maturity_note} abnormal {value:.2%}"
    return "unclear", f"{maturity_note} abnormal {value:.2%}"


def decision_counts(rows: list[dict]) -> dict[tuple[str, str], dict[str, int]]:
    result: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        source = str(row.get("source_type") or "unknown")
        repeat = str(row.get("repeat_group") or "unknown")
        decision = str(row.get("decision") or "unknown")
        result[(source, repeat)][decision] += 1
    return result


def build_report(args: argparse.Namespace) -> tuple[list[dict], dict, str]:
    outcomes = read_rows(path_value(args.outcomes))
    decisions = read_rows(path_value(args.decision_log))
    decision_by_group = decision_counts(decisions)

    grouped: dict[tuple[str, str, str], dict] = {}
    for row in outcomes:
        source = str(row.get("source_type") or "unknown")
        event_type = str(row.get("event_type") or "unknown")
        subtype = str(row.get("event_subtype") or "")
        key = (source, event_type, subtype)
        if key not in grouped:
            grouped[key] = {
                "source_type": source,
                "event_type": event_type,
                "event_subtype": subtype,
                "sample_count": 0,
                "positive_followthrough_count": 0,
                "flat_no_reaction_count": 0,
                "adverse_reaction_count": 0,
                "priced_in_risk_count": 0,
                "pending_no_outcome_count": 0,
                "unusable_quality_count": 0,
                "latest_horizon_sum": 0,
                "abnormal_sum": 0.0,
                "abnormal_n": 0,
                "example_alert_id": "",
                "example_asset": "",
                "example_reason": "",
            }
        bucket = grouped[key]
        status, reason = classify_outcome(row, args.flat_threshold, args.negative_threshold)
        bucket["sample_count"] += 1
        count_key = f"{status}_count"
        if count_key in bucket:
            bucket[count_key] += 1
        horizon, value = latest_abnormal(row)
        if value is not None:
            bucket["abnormal_sum"] += value
            bucket["abnormal_n"] += 1
        if not bucket["example_alert_id"] and status in {"flat_no_reaction", "adverse_reaction", "priced_in_risk"}:
            bucket["example_alert_id"] = row.get("alert_id", "")
            bucket["example_asset"] = row.get("asset_symbol", "")
            bucket["example_reason"] = reason

    rows = []
    for (source, _event_type, _subtype), bucket in grouped.items():
        sample_count = int(bucket["sample_count"])
        noisy_count = int(bucket["flat_no_reaction_count"]) + int(bucket["adverse_reaction_count"]) + int(bucket["priced_in_risk_count"])
        false_positive_like_rate = noisy_count / sample_count if sample_count else 0.0
        avg_abnormal = bucket["abnormal_sum"] / bucket["abnormal_n"] if bucket["abnormal_n"] else ""
        group_decisions = decision_by_group.get((source, bucket["event_subtype"] or "unknown"), {})
        suppress_count = sum(v for k, v in group_decisions.items() if k in {"suppressed_cooldown", "filtered_digest_only", "not_selected_capacity"})
        if sample_count < 10:
            recommendation = "collect_more"
        elif false_positive_like_rate >= 0.6:
            recommendation = "downrank_or_shadow"
        elif false_positive_like_rate >= 0.35:
            recommendation = "tighten_threshold"
        else:
            recommendation = "keep_testing"
        rows.append(
            {
                **{k: v for k, v in bucket.items() if k not in {"abnormal_sum", "abnormal_n"}},
                "avg_latest_abnormal_primary": f"{avg_abnormal:.8f}" if avg_abnormal != "" else "",
                "false_positive_like_count": noisy_count,
                "false_positive_like_rate": f"{false_positive_like_rate:.4f}",
                "suppressed_or_digest_decision_count": suppress_count,
                "recommendation": recommendation,
            }
        )
    rows = sorted(rows, key=lambda r: (r["recommendation"] != "downrank_or_shadow", -float(r["false_positive_like_rate"]), -int(r["sample_count"])))

    summary = {
        "generated_at_china": datetime.now(CN_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
        "outcome_rows": len(outcomes),
        "decision_rows": len(decisions),
        "group_rows": len(rows),
        "collect_more_count": sum(1 for row in rows if row["recommendation"] == "collect_more"),
        "tighten_threshold_count": sum(1 for row in rows if row["recommendation"] == "tighten_threshold"),
        "downrank_or_shadow_count": sum(1 for row in rows if row["recommendation"] == "downrank_or_shadow"),
        "status": "pass",
    }

    lines = [
        "# False Positive / Noise Analysis",
        "",
        f"- 生成时间：{summary['generated_at_china']}",
        f"- outcome rows：{summary['outcome_rows']}",
        f"- decision rows：{summary['decision_rows']}",
        f"- group rows：{summary['group_rows']}",
        "",
        "## 结论",
        "",
        "- 当前 live 样本仍少，绝大多数分组只能标记 collect_more，不能直接判死刑。",
        "- adverse/flat/priced-in 会被记为 false-positive-like，用于后续降权、转影子或提高阈值。",
        "- suppressed/digest 决策用于衡量重复噪音，不依赖用户反馈。",
        "",
        "## Top Groups",
        "",
    ]
    for row in rows[:12]:
        lines.append(
            f"- {row['source_type']} / {row['event_type']} / {row['event_subtype'] or '-'}："
            f"样本 {row['sample_count']}，false-positive-like {row['false_positive_like_rate']}，建议 {row['recommendation']}。"
        )

    return rows, summary, "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows, summary, markdown = build_report(args)
    fieldnames = [
        "source_type",
        "event_type",
        "event_subtype",
        "sample_count",
        "positive_followthrough_count",
        "flat_no_reaction_count",
        "adverse_reaction_count",
        "priced_in_risk_count",
        "pending_no_outcome_count",
        "unusable_quality_count",
        "avg_latest_abnormal_primary",
        "false_positive_like_count",
        "false_positive_like_rate",
        "suppressed_or_digest_decision_count",
        "recommendation",
        "example_alert_id",
        "example_asset",
        "example_reason",
    ]
    write_rows(path_value(args.output), rows, fieldnames)
    write_rows(path_value(args.summary), [summary], list(summary.keys()))
    write_text(path_value(args.markdown_output), markdown)
    print(f"groups={len(rows)}")
    print(f"status={summary['status']}")
    print(f"wrote_output={path_value(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
