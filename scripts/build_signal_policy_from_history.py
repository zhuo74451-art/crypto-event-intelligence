import argparse
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


POLICY_COLUMNS = [
    "policy_scope",
    "name",
    "sample_count",
    "valid_24h_count",
    "avg_abnormal_vs_btc_24h",
    "abs_move_24h_hit_rate",
    "benchmark_asset_share",
    "historical_usefulness_status",
    "tg_action",
    "reason_cn",
]


SUMMARY_COLUMNS = [
    "status",
    "source_policy_rows",
    "event_type_policy_rows",
    "boost_count",
    "digest_only_count",
    "review_count",
    "policy_output",
    "report_output",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build machine-readable TG signal policy from historical backtest usefulness.")
    parser.add_argument("--by-event-type", default=str(ROOT / "results" / "v10_historical_signal_quality_by_event_type.csv"))
    parser.add_argument("--by-source", default=str(ROOT / "results" / "v10_historical_signal_quality_by_source.csv"))
    parser.add_argument("--policy-output", default=str(ROOT / "data" / "tg_signal_policy_from_history.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v10_signal_policy_from_history_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v10_signal_policy_from_history_report.md"))
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


def safe_float(value) -> float:
    try:
        return float(str(value or "0").strip())
    except Exception:
        return 0.0


def safe_int(value) -> int:
    try:
        return int(float(str(value or "0").strip()))
    except Exception:
        return 0


def decide_action(row: dict) -> tuple[str, str]:
    status = str(row.get("historical_usefulness_status") or "")
    samples = safe_int(row.get("sample_count"))
    valid_24h = safe_int(row.get("valid_24h_count"))
    hit_24h = safe_float(row.get("abs_move_24h_hit_rate"))
    benchmark_share = safe_float(row.get("benchmark_asset_share"))
    avg_24h = safe_float(row.get("avg_abnormal_vs_btc_24h"))

    if status == "promising_for_expansion":
        return "boost", "历史样本显示有一定后续波动，优先扩样本，但仍需分资产和分市场状态验证。"
    if status == "benchmark_polluted" or benchmark_share >= 0.65:
        return "review_benchmark", "BTC/ETH 占比过高，当前异常收益结论会被 benchmark 污染，不能直接用于雷达加权。"
    if valid_24h >= 20 and hit_24h < 0.15:
        return "digest_only", "样本不少但 24h 有效波动比例偏低，优先放入早晚报，不适合盘中反复推送。"
    if samples < 10:
        return "collect_more", "样本太少，不能下结论；保留但不提高权重。"
    if avg_24h < 0 and hit_24h < 0.2:
        return "downrank", "历史异常收益和有效波动比例都偏弱，盘中降权。"
    return "review", "信号还不能明确加权或降权，需要继续观察。"


def build_policy(rows: list[dict], scope: str, key_name: str) -> list[dict]:
    output = []
    for row in rows:
        action, reason = decide_action(row)
        output.append(
            {
                "policy_scope": scope,
                "name": row.get(key_name, ""),
                "sample_count": row.get("sample_count", ""),
                "valid_24h_count": row.get("valid_24h_count", ""),
                "avg_abnormal_vs_btc_24h": row.get("avg_abnormal_vs_btc_24h", ""),
                "abs_move_24h_hit_rate": row.get("abs_move_24h_hit_rate", ""),
                "benchmark_asset_share": row.get("benchmark_asset_share", ""),
                "historical_usefulness_status": row.get("historical_usefulness_status", ""),
                "tg_action": action,
                "reason_cn": reason,
            }
        )
    return output


def md_table(rows: list[dict]) -> list[str]:
    if not rows:
        return ["暂无数据。"]
    columns = ["policy_scope", "name", "sample_count", "valid_24h_count", "avg_abnormal_vs_btc_24h", "tg_action", "reason_cn"]
    lines = ["| 范围 | 名称 | 样本 | 24h有效 | 24h平均异常收益 | 动作 | 原因 |", "| --- | --- | ---: | ---: | ---: | --- | --- |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", "｜") for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    by_event = read_rows(normalize_path(args.by_event_type))
    by_source = read_rows(normalize_path(args.by_source))
    policies = build_policy(by_source, "source", "source") + build_policy(by_event, "event_type", "event_type")
    write_rows(normalize_path(args.policy_output), policies, POLICY_COLUMNS)

    boost_count = sum(1 for row in policies if row["tg_action"] == "boost")
    digest_count = sum(1 for row in policies if row["tg_action"] == "digest_only")
    review_count = sum(1 for row in policies if row["tg_action"].startswith("review"))
    summary = {
        "status": "pass",
        "source_policy_rows": str(len(by_source)),
        "event_type_policy_rows": str(len(by_event)),
        "boost_count": str(boost_count),
        "digest_only_count": str(digest_count),
        "review_count": str(review_count),
        "policy_output": str(normalize_path(args.policy_output)),
        "report_output": str(normalize_path(args.report)),
    }
    write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)

    lines = [
        "# 历史回测生成的 TG 信号策略建议",
        "",
        "这份文件把历史回测中的来源和事件类型表现转成机器可读的初步动作：提高权重、只进早晚报、继续收集、降权或重新审查 benchmark。",
        "",
        "## 策略表",
        "",
        *md_table(policies),
        "",
        "## 说明",
        "",
        "- `boost` 不是交易方向，只表示这个来源或事件类型值得扩样本、提高雷达关注度。",
        "- `digest_only` 表示适合早报/晚报背景，不适合盘中频繁刷。",
        "- `review_benchmark` 表示 BTC/ETH 污染较重，不能用当前异常收益直接判断有效性。",
        "- `collect_more` 表示样本太少，先不做强结论。",
        "",
    ]
    normalize_path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote policy rows={len(policies)} to {normalize_path(args.policy_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
