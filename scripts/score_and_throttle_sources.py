import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score sources and derive source-level throttling rules.")
    parser.add_argument("--source-layers", default=str(ROOT / "data" / "source_identity_layers.csv"))
    parser.add_argument("--clean-backfill", default=str(ROOT / "data" / "backtest_v08_alt_history_clean.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "source_scores.csv"))
    parser.add_argument("--rules", default=str(ROOT / "results" / "v13_source_throttle_rules.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_source_throttle_report.md"))
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
        return float(str(value or "").strip() or 0)
    except ValueError:
        return 0.0


def safe_int(value) -> int:
    try:
        return int(float(str(value or "").strip() or 0))
    except ValueError:
        return 0


def source_key(value: str) -> str:
    return str(value or "").strip().lower()


def score_source(row: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    valid_event_ratio = 1 - safe_float(row.get("uncategorized_ratio"))
    backtested_count = safe_int(row.get("backtested_count"))
    avg_24h = safe_float(row.get("avg_abnormal_vs_btc_24h"))
    top_asset_share = safe_float(row.get("top_asset_share"))
    if valid_event_ratio > 0.60:
        score += 30
        reasons.append("valid_event_ratio>60")
    if avg_24h > 0.05:
        score += 20
        reasons.append("avg_24h>5pct")
    if backtested_count > 20:
        score += 15
        reasons.append("backtested_count>20")
    if top_asset_share < 0.30:
        score += 15
        reasons.append("asset_diversity_ok")
    if str(row.get("reliability_status")) == "promising_needs_validation":
        score += 20
        reasons.append("promising_needs_validation")
    if top_asset_share >= 0.60:
        score -= 20
        reasons.append("single_asset_penalty")
    if str(row.get("source_channel") or "").lower() == "tg:hyperinsight":
        score -= 20
        reasons.append("known_hype_contamination_penalty")
    return max(0, min(100, score)), reasons


def action_for(score: int) -> tuple[str, int, int]:
    if score < 30:
        return "block", 0, 0
    if score < 50:
        return "throttle", 5, 2
    if score < 70:
        return "validate", 20, 5
    return "trust", 50, 10


def main() -> int:
    args = parse_args()
    layers = read_rows(normalize_path(args.source_layers))
    clean = [row for row in read_rows(normalize_path(args.clean_backfill)) if str(row.get("is_archived") or "") != "true"]
    clean_by_source = {}
    for row in clean:
        key = source_key(row.get("source") or row.get("source_type"))
        item = clean_by_source.setdefault(key, {"count": 0, "returns": []})
        item["count"] += 1
        try:
            item["returns"].append(float(row.get("abnormal_vs_btc_24h")))
        except (TypeError, ValueError):
            pass
    output = []
    for row in layers:
        score, reasons = score_source(row)
        action, quota, burst = action_for(score)
        key = source_key(row.get("source_channel"))
        clean_stats = clean_by_source.get(key, {"count": 0, "returns": []})
        returns = clean_stats["returns"]
        avg_clean_24h = sum(returns) / len(returns) if returns else 0.0
        item = {
            "generated_at_china": china_stamp(),
            "source": row.get("source_channel", ""),
            "source_family": row.get("source_family", ""),
            "total_candidates": row.get("candidate_count", ""),
            "backtested_count": row.get("backtested_count", ""),
            "clean_backtested_count": clean_stats["count"],
            "valid_event_ratio": round(1 - safe_float(row.get("uncategorized_ratio")), 4),
            "avg_abnormal_return_24h": round(avg_clean_24h or safe_float(row.get("avg_abnormal_vs_btc_24h")), 6),
            "top_asset": row.get("top_asset", ""),
            "top_asset_share": row.get("top_asset_share", ""),
            "source_score": score,
            "score_reasons": ",".join(reasons),
            "daily_quota": quota,
            "burst_window_limit": burst,
            "recommended_action": action,
        }
        output.append(item)
    output.sort(key=lambda row: (-row["source_score"], -safe_int(row["backtested_count"]), row["source"]))
    fields = list(output[0].keys()) if output else ["source", "source_score"]
    write_rows(normalize_path(args.output), output, fields)
    write_rows(normalize_path(args.rules), output, fields)

    lines = [
        "# v13 Source Throttle Report",
        "",
        f"- generated_at_china: {china_stamp()}",
        f"- source_rows: {len(output)}",
        f"- trust_count: {sum(1 for row in output if row['recommended_action'] == 'trust')}",
        f"- block_count: {sum(1 for row in output if row['recommended_action'] == 'block')}",
        "",
        "| source | score | action | quota | burst | clean_backtested | avg_24h | top_asset | reasons |",
        "|---|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for row in output:
        lines.append(
            f"| {row['source']} | {row['source_score']} | {row['recommended_action']} | {row['daily_quota']} | "
            f"{row['burst_window_limit']} | {row['clean_backtested_count']} | {row['avg_abnormal_return_24h']} | "
            f"{row['top_asset']} | {row['score_reasons']} |"
        )
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"source_rows={len(output)}")
    print(f"trust_count={sum(1 for row in output if row['recommended_action'] == 'trust')}")
    print(f"block_count={sum(1 for row in output if row['recommended_action'] == 'block')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
