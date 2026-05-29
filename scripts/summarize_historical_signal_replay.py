import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize historical signal replay backtest results.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_signal_replay_200_price_backfill.csv"))
    parser.add_argument("--quality", default=str(ROOT / "results" / "v08_historical_signal_replay_200_quality_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_historical_signal_replay_200_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_historical_signal_replay_200_findings.md"))
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


def safe_float(value) -> float | None:
    try:
        raw = str(value or "").strip()
        if raw == "":
            return None
        return float(raw)
    except Exception:
        return None


def avg(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"


def benchmark_aware_metric(row: dict, horizon: str) -> float | None:
    asset = str(row.get("asset_symbol", "") or "").strip().upper()
    if asset == "BTC":
        return safe_float(row.get(f"abnormal_vs_eth_{horizon}"))
    return safe_float(row.get(f"abnormal_vs_btc_{horizon}"))


def md_count_table(title: str, counter: Counter) -> list[str]:
    lines = [f"## {title}", "", "| value | count |", "|---|---:|"]
    if not counter:
        lines.append("| none | 0 |")
    else:
        for key, count in counter.most_common():
            lines.append(f"| {key or 'blank'} | {count} |")
    lines.append("")
    return lines


def main() -> int:
    args = parse_args()
    backfill = read_rows(normalize_path(args.backfill))
    quality = read_rows(normalize_path(args.quality))
    summary = read_rows(normalize_path(args.summary))

    status_counts = Counter(str(row.get("status", "") or "unknown") for row in backfill)
    quality_counts = Counter(str(row.get("quality_status", "") or "unknown") for row in quality)
    event_counts = Counter(str(row.get("event_type", "") or "unknown") for row in backfill)
    asset_counts = Counter(str(row.get("asset_symbol", "") or "unknown") for row in backfill)

    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in backfill:
        if str(row.get("status", "")).lower() in {"ok", "partial"}:
            by_type[str(row.get("event_type", "") or "unknown")].append(row)

    lines = [
        "# v0.8 Historical Signal Replay Findings",
        "",
        "This report replays older historical event candidates through the same price backfill logic to increase signal sample size. It is research/quality analysis only and is not trading advice.",
        "",
        f"- total_backfill_rows: {len(backfill)}",
        f"- quality_rows: {len(quality)}",
        "",
        *md_count_table("Backfill Status", status_counts),
        *md_count_table("Quality Status", quality_counts),
        *md_count_table("Samples By Event Type", event_counts),
        *md_count_table("Samples By Asset", asset_counts),
        "## Event Type Performance",
        "",
        "| event_type | rows | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h | win_rate_24h | win_rate_72h |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    type_rows = []
    benchmark_aware_type_rows = []
    for event_type, rows in sorted(by_type.items(), key=lambda item: len(item[1]), reverse=True):
        values = {h: [safe_float(row.get(f"abnormal_vs_btc_{h}")) for row in rows] for h in ["1h", "4h", "24h", "72h"]}
        aware_values = {h: [benchmark_aware_metric(row, h) for row in rows] for h in ["1h", "4h", "24h", "72h"]}
        win24 = [value for value in values["24h"] if value is not None]
        win72 = [value for value in values["72h"] if value is not None]
        aware_win24 = [value for value in aware_values["24h"] if value is not None]
        aware_win72 = [value for value in aware_values["72h"] if value is not None]
        type_row = {
            "event_type": event_type,
            "rows": len(rows),
            "avg_1h": avg(values["1h"]),
            "avg_4h": avg(values["4h"]),
            "avg_24h": avg(values["24h"]),
            "avg_72h": avg(values["72h"]),
            "win24": sum(value > 0 for value in win24) / len(win24) if win24 else None,
            "win72": sum(value > 0 for value in win72) / len(win72) if win72 else None,
        }
        aware_type_row = {
            "event_type": event_type,
            "rows": len(rows),
            "avg_1h": avg(aware_values["1h"]),
            "avg_4h": avg(aware_values["4h"]),
            "avg_24h": avg(aware_values["24h"]),
            "avg_72h": avg(aware_values["72h"]),
            "win24": sum(value > 0 for value in aware_win24) / len(aware_win24) if aware_win24 else None,
            "win72": sum(value > 0 for value in aware_win72) / len(aware_win72) if aware_win72 else None,
        }
        type_rows.append(type_row)
        benchmark_aware_type_rows.append(aware_type_row)
        lines.append(
            f"| {event_type} | {len(rows)} | {pct(type_row['avg_1h'])} | {pct(type_row['avg_4h'])} | {pct(type_row['avg_24h'])} | {pct(type_row['avg_72h'])} | {pct(type_row['win24'])} | {pct(type_row['win72'])} |"
        )

    lines.extend(
        [
            "",
            "## Benchmark-Aware Event Type Performance",
            "",
            "BTC rows use `abnormal_vs_eth`; non-BTC rows use `abnormal_vs_btc`. This reduces BTC benchmark self-comparison flattening.",
            "",
            "| event_type | rows | avg_benchmark_aware_1h | avg_benchmark_aware_4h | avg_benchmark_aware_24h | avg_benchmark_aware_72h | win_rate_24h | win_rate_72h |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(benchmark_aware_type_rows, key=lambda item: item["rows"], reverse=True):
        lines.append(
            f"| {row['event_type']} | {row['rows']} | {pct(row['avg_1h'])} | {pct(row['avg_4h'])} | {pct(row['avg_24h'])} | {pct(row['avg_72h'])} | {pct(row['win24'])} | {pct(row['win72'])} |"
        )

    scored24 = [(safe_float(row.get("abnormal_vs_btc_24h")), row) for row in backfill]
    scored24 = [(score, row) for score, row in scored24 if score is not None]
    scored72 = [(safe_float(row.get("abnormal_vs_btc_72h")), row) for row in backfill]
    scored72 = [(score, row) for score, row in scored72 if score is not None]

    def event_section(title: str, items: list[tuple[float, dict]]) -> None:
        lines.extend(["", f"## {title}", "", "| abnormal_vs_btc | event_type | asset | title |", "|---:|---|---|---|"])
        if not items:
            lines.append("| n/a |  |  | no rows |")
            return
        for score, row in items[:10]:
            title_text = str(row.get("title", "") or "").replace("|", "\\|").replace("\n", " ")[:180]
            lines.append(f"| {pct(score)} | {row.get('event_type', '')} | {row.get('asset_symbol', '')} | {title_text} |")

    event_section("Best 24h Events", sorted(scored24, key=lambda item: item[0], reverse=True))
    event_section("Worst 24h Events", sorted(scored24, key=lambda item: item[0]))
    event_section("Best 72h Events", sorted(scored72, key=lambda item: item[0], reverse=True))
    event_section("Worst 72h Events", sorted(scored72, key=lambda item: item[0]))

    mature_types = [row for row in type_rows if row["rows"] >= 10]
    aware_mature_types = [row for row in benchmark_aware_type_rows if row["rows"] >= 10]
    lines.extend(["", "## Practical Read", ""])
    if mature_types:
        best24 = max(mature_types, key=lambda row: row["avg_24h"] if row["avg_24h"] is not None else -999)
        best72 = max(mature_types, key=lambda row: row["avg_72h"] if row["avg_72h"] is not None else -999)
        lines.append(f"- Among event types with at least 10 rows, strongest 24h average: `{best24['event_type']}` at {pct(best24['avg_24h'])}.")
        lines.append(f"- Among event types with at least 10 rows, strongest 72h average: `{best72['event_type']}` at {pct(best72['avg_72h'])}.")
        if aware_mature_types:
            aware_best24 = max(aware_mature_types, key=lambda row: row["avg_24h"] if row["avg_24h"] is not None else -999)
            aware_best72 = max(aware_mature_types, key=lambda row: row["avg_72h"] if row["avg_72h"] is not None else -999)
            lines.append(
                f"- Benchmark-aware strongest 24h average: `{aware_best24['event_type']}` at {pct(aware_best24['avg_24h'])}."
            )
            lines.append(
                f"- Benchmark-aware strongest 72h average: `{aware_best72['event_type']}` at {pct(aware_best72['avg_72h'])}."
            )
    else:
        lines.append("- No event_type has at least 10 rows yet; treat all per-type conclusions as weak.")
    lines.append("- BTC events versus BTC benchmark can flatten abnormal-vs-BTC; use the benchmark-aware table before reading BTC-heavy buckets.")
    lines.append("- This is historical replay for source-quality learning, not a live publishing rule.")

    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"backfill_rows={len(backfill)}")
    print(f"event_type_count={len(event_counts)}")
    print(f"wrote_report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
