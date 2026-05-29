import argparse
import csv
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
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
    "valid_1h_count",
    "avg_abnormal_primary_1h",
    "win_rate_1h",
    "live_policy_status",
    "tg_action",
    "reason_cn",
]


SUMMARY_COLUMNS = [
    "status",
    "generated_at_china",
    "outcome_rows",
    "policy_rows",
    "downrank_count",
    "digest_only_count",
    "monitor_count",
    "output",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build provisional live TG signal policy from post-publish outcomes.")
    parser.add_argument("--outcomes", default=str(ROOT / "data" / "tg_alert_outcomes.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_signal_policy_live.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_signal_policy_live_summary.csv"))
    parser.add_argument("--min-abs-move-1h", type=float, default=0.005)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_stamp() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


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
        raw = str(value or "").strip()
        if not raw:
            return math.nan
        return float(raw)
    except Exception:
        return math.nan


def avg(values: list[float]) -> float:
    values = [value for value in values if not math.isnan(value)]
    return sum(values) / len(values) if values else math.nan


def repeat_group_from_outcome(row: dict) -> str:
    source = str(row.get("source_type") or "")
    subtype = str(row.get("event_subtype") or "")
    if source == "token_unlock" or subtype.startswith("token_unlock"):
        return "token_unlock"
    if subtype == "whale_position_static_large":
        return "static_position"
    if subtype in {"whale_position_size_change", "whale_position_near_liquidation"}:
        return "position_change"
    if source == "long_short":
        return "indicator"
    if source in {"cex_netflow", "stablecoin_flow"}:
        return "flow"
    return source or "unknown"


def scope_values(row: dict) -> list[tuple[str, str]]:
    values = []
    if row.get("event_subtype"):
        values.append(("event_subtype", str(row.get("event_subtype"))))
    if row.get("source_type"):
        values.append(("source_type", str(row.get("source_type"))))
    repeat_group = repeat_group_from_outcome(row)
    if repeat_group and repeat_group != "unknown":
        values.append(("repeat_group", repeat_group))
    return values


def decide(scope: str, name: str, values: list[float], min_abs_move: float) -> tuple[str, str, str]:
    count = len(values)
    mean = avg(values)
    win_rate = sum(1 for value in values if value > 0) / count if count else 0.0
    if count == 0 or math.isnan(mean):
        return "no_signal", "monitor", "暂无成熟 1h 结果。"

    if name in {"token_unlock", "token_unlock_team_large", "token_unlock_investor_large"}:
        return "background_only", "digest_only", "解锁属于静态供给背景，盘中只在临近或异常放大时出现，默认转早晚报。"

    if name in {"static_position", "whale_position_static_large"}:
        if mean <= -min_abs_move:
            return "weak_early_reaction", "downrank", "静态大仓位 1h 初步表现偏弱，先降低盘中重复曝光，等待仓位变化或接近清算再提高。"
        return "static_context", "monitor", "静态大仓位只做背景观察，优先等待仓位变化。"

    if count >= 2 and mean <= -min_abs_move and win_rate <= 0.34:
        return "weak_live_reaction", "downrank", "同类实时样本 1h 后续表现偏弱，临时降权。"
    if count >= 2 and mean >= min_abs_move and win_rate >= 0.50:
        return "promising_live_reaction", "boost", "同类实时样本 1h 后续表现较好，临时提高关注度。"
    return "insufficient_live_sample", "monitor", "实时样本仍少，继续观察，不做强结论。"


def build_policy(rows: list[dict], min_abs_move: float) -> list[dict]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        if str(row.get("quality_status") or "").lower() in {"skipped", "error"}:
            continue
        value = safe_float(row.get("abnormal_primary_1h"))
        if math.isnan(value):
            continue
        for scope, name in scope_values(row):
            grouped[(scope, name)].append(value)

    output = []
    for (scope, name), values in sorted(grouped.items()):
        status, action, reason = decide(scope, name, values, min_abs_move)
        mean = avg(values)
        win_rate = sum(1 for value in values if value > 0) / len(values) if values else 0.0
        output.append(
            {
                "policy_scope": scope,
                "name": name,
                "sample_count": str(len(values)),
                "valid_1h_count": str(len(values)),
                "avg_abnormal_primary_1h": "" if math.isnan(mean) else f"{mean:.8f}",
                "win_rate_1h": f"{win_rate:.4f}",
                "live_policy_status": status,
                "tg_action": action,
                "reason_cn": reason,
            }
        )
    return output


def main() -> int:
    args = parse_args()
    outcome_rows = read_rows(normalize_path(args.outcomes))
    policy_rows = build_policy(outcome_rows, args.min_abs_move_1h)
    write_rows(normalize_path(args.output), policy_rows, POLICY_COLUMNS)
    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "outcome_rows": str(len(outcome_rows)),
        "policy_rows": str(len(policy_rows)),
        "downrank_count": str(sum(1 for row in policy_rows if row["tg_action"] == "downrank")),
        "digest_only_count": str(sum(1 for row in policy_rows if row["tg_action"] == "digest_only")),
        "monitor_count": str(sum(1 for row in policy_rows if row["tg_action"] == "monitor")),
        "output": str(normalize_path(args.output)),
    }
    write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
    print(f"wrote live policy rows={len(policy_rows)} to {normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
