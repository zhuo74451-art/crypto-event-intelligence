import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize CEX netflow rolling baseline readiness.")
    parser.add_argument("--input", default=str(ROOT / "data" / "cex_netflow_baseline_state.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v081_cex_netflow_baseline_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v081_cex_netflow_baseline_summary.csv"))
    parser.add_argument("--by-pair", default=str(ROOT / "results" / "v081_cex_netflow_baseline_by_pair.csv"))
    parser.add_argument("--min-samples", type=int, default=72)
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
        raw = str(value or "").strip()
        if raw == "":
            return 0.0
        return float(raw)
    except Exception:
        return 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    idx = (len(values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return values[lo] * (1 - frac) + values[hi] * frac


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    grouped = defaultdict(list)
    for row in rows:
        entity = str(row.get("entity", "") or "unknown").strip() or "unknown"
        asset = str(row.get("asset_symbol", "") or "unknown").strip().upper() or "unknown"
        grouped[(entity, asset)].append(row)

    pair_rows = []
    for (entity, asset), items in grouped.items():
        net = [safe_float(r.get("net_usd")) for r in items]
        abs_net = [abs(v) for v in net]
        gross = [safe_float(r.get("gross_usd")) for r in items]
        tx_counts = [safe_float(r.get("tx_count")) for r in items]
        pair_rows.append(
            {
                "entity": entity,
                "asset_symbol": asset,
                "sample_count": len(items),
                "first_observed_china": items[0].get("observed_at_china", ""),
                "last_observed_china": items[-1].get("observed_at_china", ""),
                "avg_abs_net_usd": round(avg(abs_net), 2),
                "median_abs_net_usd": round(statistics.median(abs_net), 2) if abs_net else 0,
                "p95_abs_net_usd": round(percentile(abs_net, 0.95), 2),
                "max_abs_net_usd": round(max(abs_net), 2) if abs_net else 0,
                "avg_gross_usd": round(avg(gross), 2),
                "avg_tx_count": round(avg(tx_counts), 2),
                "baseline_status": "ready" if len(items) >= args.min_samples else "needs_more_history",
            }
        )
    pair_rows.sort(key=lambda r: (r["baseline_status"] != "ready", -int(r["sample_count"]), -float(r["p95_abs_net_usd"])))

    ready_pairs = sum(1 for r in pair_rows if r["baseline_status"] == "ready")
    max_samples = max([int(r["sample_count"]) for r in pair_rows], default=0)
    summary = {
        "baseline_rows": len(rows),
        "entity_asset_pairs": len(pair_rows),
        "ready_pairs": ready_pairs,
        "needs_more_history_pairs": len(pair_rows) - ready_pairs,
        "max_pair_samples": max_samples,
        "min_samples": args.min_samples,
        "status": "ready" if ready_pairs else "needs_more_history",
    }
    fields = [
        "entity",
        "asset_symbol",
        "sample_count",
        "first_observed_china",
        "last_observed_china",
        "avg_abs_net_usd",
        "median_abs_net_usd",
        "p95_abs_net_usd",
        "max_abs_net_usd",
        "avg_gross_usd",
        "avg_tx_count",
        "baseline_status",
    ]
    write_rows(normalize_path(args.by_pair), pair_rows, fields)
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    lines = [
        "# v0.8.1 CEX Netflow Baseline Report",
        "",
        f"- status: {summary['status']}",
        f"- baseline_rows: {len(rows)}",
        f"- entity_asset_pairs: {len(pair_rows)}",
        f"- ready_pairs: {ready_pairs}",
        f"- max_pair_samples: {max_samples} / {args.min_samples}",
        "",
        "## Top Pairs",
        "",
        "| entity | asset | samples | p95_abs_net_usd | avg_gross_usd | status |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in pair_rows[:30]:
        lines.append(
            f"| {row['entity']} | {row['asset_symbol']} | {row['sample_count']} | {row['p95_abs_net_usd']} | {row['avg_gross_usd']} | {row['baseline_status']} |"
        )
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "Use this baseline to decide whether a CEX netflow alert is unusual. Do not raise Telegram volume until key entity/asset pairs have enough rolling samples.",
            "",
        ]
    )
    normalize_path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"status={summary['status']}")
    print(f"baseline_rows={len(rows)}")
    print(f"ready_pairs={ready_pairs}")
    print(f"wrote_report={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
