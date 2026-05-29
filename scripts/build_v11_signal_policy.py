import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))


POLICY_COLUMNS = [
    "policy_scope",
    "name",
    "sample_count",
    "valid_24h_count",
    "avg_abnormal_primary_24h",
    "win_rate_primary_24h",
    "false_positive_like_rate",
    "matrix_status",
    "tg_action",
    "priority_delta",
    "cooldown_multiplier",
    "reason_cn",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build v11 route policy from historical matrix and passive false-positive analysis.")
    parser.add_argument("--event-matrix", default=str(ROOT / "results" / "event_type_performance_matrix.csv"))
    parser.add_argument("--non-benchmark-event-matrix", default=str(ROOT / "results" / "event_type_performance_matrix_non_benchmark_alt.csv"))
    parser.add_argument("--source-effectiveness", default=str(ROOT / "results" / "source_effectiveness_report.csv"))
    parser.add_argument("--false-positive", default=str(ROOT / "results" / "false_positive_analysis.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_signal_policy_v11.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v11_signal_policy_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v11_signal_policy_report.md"))
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


def safe_float(value, default: float = 0.0) -> float:
    try:
        raw = str(value or "").strip()
        return float(raw) if raw else default
    except Exception:
        return default


def safe_int(value) -> int:
    try:
        return int(float(str(value or "0").strip()))
    except Exception:
        return 0


def fp_lookup(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    out = {}
    for row in rows:
        out[(row.get("source_type", ""), row.get("event_type", ""), row.get("event_subtype", ""))] = row
    return out


def decide_matrix(row: dict, fp: dict | None) -> tuple[str, float, float, str]:
    sample = safe_int(row.get("sample_count"))
    valid_24h = safe_int(row.get("computed_24h_count"))
    avg_24h = safe_float(row.get("avg_abnormal_primary_24h"))
    win_24h = safe_float(row.get("win_rate_primary_24h"))
    status = str(row.get("matrix_status") or "")
    asset_tier = str(row.get("asset_tier") or "")
    fp_rate = safe_float((fp or {}).get("false_positive_like_rate"), 0.0)

    if asset_tier == "benchmark_asset":
        return "review_benchmark", -8, 1.5, "历史样本以 BTC/ETH 基准资产为主，异常收益容易被压扁；先降低盘中权重，等待非基准资产样本。"
    if sample < 10 or status == "insufficient_sample":
        cooldown = 1.5 if fp_rate >= 0.5 else 1.2
        return "collect_more", -4, cooldown, "历史样本不足，先收集更多，不做强结论；盘中降低重复曝光。"
    if status == "weak_or_context_only" or (valid_24h >= 20 and abs(avg_24h) < 0.003 and win_24h < 0.35):
        return "digest_only", -25, 2.0, "历史回测显示同类事件更像背景信息，优先进入早午晚报，不适合盘中反复刷。"
    if fp_rate >= 0.6 and sample >= 10:
        return "downrank", -18, 2.0, "被动回看中无反应/反向反应比例偏高，先降权并延长冷却。"
    if valid_24h >= 20 and avg_24h > 0.008 and win_24h >= 0.55:
        return "boost", 10, 0.8, "历史同类事件 24h 后续表现较好，允许提高观察优先级，但仍不代表方向建议。"
    return "monitor", 0, 1.0, "历史证据中性，保留观察，不提高权重。"


def build_event_policies(matrix_rows: list[dict], fp_rows: list[dict]) -> list[dict]:
    fps = fp_lookup(fp_rows)
    policies = []
    seen = set()
    for row in matrix_rows:
        event_type = str(row.get("event_type") or "")
        subtype = str(row.get("event_subtype") or "")
        source = str(row.get("source_type") or "")
        if not event_type:
            continue
        fp = fps.get((source, event_type, subtype))
        action, priority_delta, cooldown, reason = decide_matrix(row, fp)
        for scope, name in [("event_subtype", subtype), ("event_type", event_type), ("source_type", source)]:
            if not name:
                continue
            key = (scope, name)
            if key in seen:
                continue
            seen.add(key)
            policies.append(
                {
                    "policy_scope": scope,
                    "name": name,
                    "sample_count": row.get("sample_count", ""),
                    "valid_24h_count": row.get("computed_24h_count", ""),
                    "avg_abnormal_primary_24h": row.get("avg_abnormal_primary_24h", ""),
                    "win_rate_primary_24h": row.get("win_rate_primary_24h", ""),
                    "false_positive_like_rate": (fp or {}).get("false_positive_like_rate", ""),
                    "matrix_status": row.get("matrix_status", ""),
                    "tg_action": action,
                    "priority_delta": f"{priority_delta:.2f}",
                    "cooldown_multiplier": f"{cooldown:.2f}",
                    "reason_cn": reason,
                }
            )
    return policies


def build_source_effectiveness_policies(rows: list[dict]) -> list[dict]:
    policies = []
    for row in rows:
        source = str(row.get("source_type") or "")
        if not source:
            continue
        status = str(row.get("live_effectiveness_status") or "")
        recommended = str(row.get("recommended_route") or "")
        if status == "shadow_or_no_live_data" or recommended == "shadow":
            action, delta, cooldown, reason = "collect_more", -8, 1.8, "该来源缺少 live outcome 或仍在影子模式，先收集证据，不进入高频盘中曝光。"
        elif status == "insufficient_live_outcomes":
            action, delta, cooldown, reason = "collect_more", -4, 1.3, "live outcome 样本不足，继续观察并降低重复曝光。"
        elif safe_float(row.get("false_positive_like_rate")) >= 0.6 and safe_int(row.get("outcome_rows")) >= 10:
            action, delta, cooldown, reason = "downrank", -15, 2.0, "该来源 false-positive-like 比例偏高，先降权并延长冷却。"
        else:
            action, delta, cooldown, reason = "monitor", 0, 1.0, "来源证据中性，保留观察。"
        policies.append(
            {
                "policy_scope": "source_type",
                "name": source,
                "sample_count": row.get("outcome_rows", ""),
                "valid_24h_count": row.get("computed_24h_count", ""),
                "avg_abnormal_primary_24h": row.get("avg_abnormal_primary_24h", ""),
                "win_rate_primary_24h": row.get("win_rate_primary_24h", ""),
                "false_positive_like_rate": row.get("false_positive_like_rate", ""),
                "matrix_status": status,
                "tg_action": action,
                "priority_delta": f"{delta:.2f}",
                "cooldown_multiplier": f"{cooldown:.2f}",
                "reason_cn": reason,
            }
        )
    return policies


def dedupe_policies(rows: list[dict]) -> list[dict]:
    priority = {"event_subtype": 0, "repeat_group": 1, "source_type": 2, "event_type": 3}
    action_rank = {"downrank": 0, "digest_only": 1, "review_benchmark": 2, "collect_more": 3, "monitor": 4, "boost": 5}
    rows = sorted(rows, key=lambda r: (priority.get(r["policy_scope"], 9), action_rank.get(r["tg_action"], 9)))
    out = {}
    for row in rows:
        key = (row["policy_scope"], row["name"])
        out.setdefault(key, row)
    return list(out.values())


def write_report(path: Path, rows: list[dict], summary: dict) -> None:
    lines = [
        "# v11 历史优先雷达路由策略",
        "",
        f"- 生成时间：{summary['generated_at_china']}",
        f"- 策略行数：{summary['policy_rows']}",
        f"- boost：{summary['boost_count']}，downrank：{summary['downrank_count']}，digest_only：{summary['digest_only_count']}，collect_more：{summary['collect_more_count']}",
        "",
        "## 策略说明",
        "",
        "- 这张表只决定 TG 雷达展示优先级、是否转早午晚报、是否延长冷却；不产生任何交易方向。",
        "- 历史样本不足或 benchmark 污染时，默认 collect_more/review_benchmark，而不是强行下结论。",
        "- false-positive-like 只来自价格回看和雷达决策日志，不依赖用户反馈。",
        "",
        "## 预览",
        "",
        "| scope | name | action | cooldown | reason |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in rows[:30]:
        lines.append(
            f"| {row['policy_scope']} | {row['name']} | {row['tg_action']} | {row['cooldown_multiplier']} | {row['reason_cn']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    matrix = read_rows(path_value(args.event_matrix))
    non_benchmark_matrix = read_rows(path_value(args.non_benchmark_event_matrix))
    source_effectiveness = read_rows(path_value(args.source_effectiveness))
    false_positive = read_rows(path_value(args.false_positive))
    policies = dedupe_policies(
        build_event_policies(non_benchmark_matrix, false_positive)
        + build_event_policies(matrix, false_positive)
        + build_source_effectiveness_policies(source_effectiveness)
    )
    generated_at = datetime.now(CN_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    summary = {
        "status": "pass",
        "generated_at_china": generated_at,
        "matrix_rows": len(matrix),
        "non_benchmark_matrix_rows": len(non_benchmark_matrix),
        "source_effectiveness_rows": len(source_effectiveness),
        "false_positive_rows": len(false_positive),
        "policy_rows": len(policies),
        "boost_count": sum(1 for row in policies if row["tg_action"] == "boost"),
        "downrank_count": sum(1 for row in policies if row["tg_action"] == "downrank"),
        "digest_only_count": sum(1 for row in policies if row["tg_action"] == "digest_only"),
        "collect_more_count": sum(1 for row in policies if row["tg_action"] == "collect_more"),
        "output": str(path_value(args.output)),
    }
    write_rows(path_value(args.output), policies, POLICY_COLUMNS)
    write_rows(path_value(args.summary), [summary], list(summary.keys()))
    write_report(path_value(args.report), policies, summary)
    print(f"policy_rows={len(policies)}")
    print(f"status={summary['status']}")
    print(f"wrote_output={path_value(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
