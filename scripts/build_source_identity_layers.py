import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a three-layer source identity table from historical candidates and outcomes.")
    parser.add_argument("--candidates", default=str(ROOT / "data" / "event_candidates_real_2000_older_v12_reclassified.csv"))
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--registry", default=str(ROOT / "data" / "source_registry.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "source_identity_layers.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v13_source_identity_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_source_identity_layers.md"))
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


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def source_channel(source: str) -> str:
    text = str(source or "").strip()
    if text.startswith("tg:"):
        return text
    if text:
        return text
    return "unknown"


def source_family(channel: str, registry: dict[str, dict]) -> str:
    lower = channel.lower()
    for row in registry.values():
        sid = str(row.get("source_id") or "").lower()
        stype = str(row.get("source_type") or "").lower()
        if sid and sid in lower:
            return str(row.get("source_family") or "unknown")
        if stype and stype in lower:
            return str(row.get("source_family") or "unknown")
    if lower.startswith("tg:"):
        if "hyperinsight" in lower:
            return "historical_news"
        return "telegram_news"
    if "webhook" in lower:
        return "webhook_news"
    return "unknown"


def channel_type(channel: str) -> str:
    lower = channel.lower()
    if lower.startswith("tg:"):
        return "telegram_channel"
    if "webhook" in lower:
        return "webhook"
    if "twitter" in lower or lower.startswith("x:"):
        return "x_account"
    return "unknown"


def reliability_status(sample_count: int, avg_24h: float, win_rate: float, uncategorized_ratio: float) -> str:
    if sample_count < 10:
        return "insufficient_data"
    if uncategorized_ratio >= 0.6:
        return "noisy_source"
    if avg_24h >= 0.01 and win_rate >= 0.55:
        return "promising_needs_validation"
    if abs(avg_24h) < 0.003:
        return "weak_or_context_only"
    return "monitor"


def main() -> int:
    args = parse_args()
    candidates = read_rows(normalize_path(args.candidates))
    backfill = read_rows(normalize_path(args.backfill))
    registry_rows = read_rows(normalize_path(args.registry))
    registry = {str(row.get("source_id") or row.get("source_type") or ""): row for row in registry_rows}

    candidate_groups = defaultdict(list)
    for row in candidates:
        candidate_groups[source_channel(row.get("source"))].append(row)

    backfill_groups = defaultdict(list)
    for row in backfill:
        backfill_groups[source_channel(row.get("source") or row.get("source_type"))].append(row)

    channels = sorted(set(candidate_groups) | set(backfill_groups))
    output = []
    for channel in channels:
        cand = candidate_groups.get(channel, [])
        bf = backfill_groups.get(channel, [])
        types = Counter(str(row.get("v12_event_type") or row.get("candidate_event_type") or "unknown") for row in cand)
        subtypes = Counter(str(row.get("v12_event_subtype") or row.get("candidate_event_subtype") or "unknown") for row in cand)
        assets = Counter(str(row.get("candidate_asset_symbol") or "UNKNOWN").upper() for row in cand)
        values = [safe_float(row.get("abnormal_vs_btc_24h")) for row in bf]
        values = [value for value in values if value is not None]
        win_rate = sum(1 for value in values if value > 0) / len(values) if values else 0.0
        uncategorized = sum(1 for row in cand if str(row.get("v12_event_type") or row.get("candidate_event_type")) in {"uncategorized", "other"})
        uncategorized_ratio = uncategorized / len(cand) if cand else 0.0
        row = {
            "generated_at_china": china_stamp(),
            "source_id": channel.lower().replace(":", "_").replace(" ", "_"),
            "source_family": source_family(channel, registry),
            "source_channel": channel,
            "source_channel_type": channel_type(channel),
            "candidate_count": len(cand),
            "backtested_count": len(bf),
            "uncategorized_count": uncategorized,
            "uncategorized_ratio": round(uncategorized_ratio, 4),
            "top_event_type": types.most_common(1)[0][0] if types else "",
            "top_event_type_share": round(types.most_common(1)[0][1] / len(cand), 4) if types and cand else 0.0,
            "top_event_subtype": subtypes.most_common(1)[0][0] if subtypes else "",
            "top_asset": assets.most_common(1)[0][0] if assets else "",
            "top_asset_share": round(assets.most_common(1)[0][1] / len(cand), 4) if assets and cand else 0.0,
            "avg_abnormal_vs_btc_24h": round(avg(values), 6),
            "win_rate_vs_btc_24h": round(win_rate, 4),
            "reliability_status": reliability_status(len(bf), avg(values), win_rate, uncategorized_ratio),
        }
        output.append(row)
    output.sort(key=lambda row: (-row["candidate_count"], row["source_channel"]))
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["source_id"])

    status_counts = Counter(row["reliability_status"] for row in output)
    summary = {
        "generated_at_china": china_stamp(),
        "status": "pass",
        "source_rows": len(output),
        "candidate_rows": len(candidates),
        "backfill_rows": len(backfill),
        "noisy_source_count": status_counts.get("noisy_source", 0),
        "promising_needs_validation_count": status_counts.get("promising_needs_validation", 0),
        "insufficient_data_count": status_counts.get("insufficient_data", 0),
        "output": str(normalize_path(args.output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    lines = [
        "# v13 Source Identity Layers",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- source_rows: {summary['source_rows']}",
        f"- candidate_rows: {summary['candidate_rows']}",
        "",
        "| source | family | candidates | backtested | uncategorized_ratio | top_type | top_asset | avg_24h | win_rate_24h | status |",
        "|---|---|---:|---:|---:|---|---|---:|---:|---|",
    ]
    for row in output[:50]:
        lines.append(
            f"| {row['source_channel']} | {row['source_family']} | {row['candidate_count']} | {row['backtested_count']} | "
            f"{row['uncategorized_ratio']} | {row['top_event_type']} | {row['top_asset']} | "
            f"{row['avg_abnormal_vs_btc_24h']} | {row['win_rate_vs_btc_24h']} | {row['reliability_status']} |"
        )
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"source_rows={len(output)}")
    print(f"wrote_output={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
