"""Generate coverage report for historical market data."""

from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
from pathlib import Path
from typing import Any


def generate_coverage_report(
    bars_path: str | Path,
    derivatives_path: str | Path,
    windows_path: str | Path,
    labels_path: str | Path,
    index_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Generate comprehensive coverage report."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "rows_by_instrument": {},
        "rows_by_interval": {},
        "rows_by_year": {},
        "rows_by_provider": {},
        "coverage_start_by_instrument": {},
        "coverage_end_by_instrument": {},
        "gap_count_by_instrument": {},
        "proxy_instruments": [],
        "lower_frequency_fallbacks": [],
        "event_windows_by_family": {},
        "labels_by_horizon": {},
        "derivative_coverage": {},
        "quarantine_count": 0,
        "audit_violation_count": 0,
        "provider_failure_count": 0,
    }

    # Market bars analysis
    bars_path = Path(bars_path)
    if bars_path.exists():
        open_func = gzip.open if str(bars_path).endswith(".gz") else open
        bars = []
        with open_func(bars_path, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    bars.append(json.loads(line))

        for bar in bars:
            inst = bar.get("instrument_id", "unknown")
            interval = bar.get("interval", "unknown")
            year = bar.get("open_time_utc", "")[:4]
            provider = bar.get("source_provider", "unknown")
            quality = bar.get("data_quality", "unknown")

            report["rows_by_instrument"][inst] = report["rows_by_instrument"].get(inst, 0) + 1
            report["rows_by_interval"][interval] = report["rows_by_interval"].get(interval, 0) + 1
            report["rows_by_year"][year] = report["rows_by_year"].get(year, 0) + 1
            report["rows_by_provider"][provider] = report["rows_by_provider"].get(provider, 0) + 1

            # Coverage start/end
            if inst not in report["coverage_start_by_instrument"] or bar.get("open_time_utc", "") < report["coverage_start_by_instrument"][inst]:
                report["coverage_start_by_instrument"][inst] = bar.get("open_time_utc", "")
            if inst not in report["coverage_end_by_instrument"] or bar.get("open_time_utc", "") > report["coverage_end_by_instrument"][inst]:
                report["coverage_end_by_instrument"][inst] = bar.get("open_time_utc", "")

            if quality == "explicit_liquid_proxy":
                report["proxy_instruments"].append(inst)
            if quality == "lower_frequency_fallback":
                report["lower_frequency_fallbacks"].append(inst)

    # Derivatives analysis
    derivatives_path = Path(derivatives_path)
    if derivatives_path.exists():
        with gzip.open(derivatives_path, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    inst = d.get("instrument_id", "unknown")
                    report["derivative_coverage"][inst] = report["derivative_coverage"].get(inst, 0) + 1

    # Event windows analysis
    windows_path = Path(windows_path)
    if windows_path.exists():
        open_func = gzip.open if str(windows_path).endswith(".gz") else open
        with open_func(windows_path, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    w = json.loads(line)
                    family = w.get("event_family", "unknown")
                    report["event_windows_by_family"][family] = report["event_windows_by_family"].get(family, 0) + 1

    # Labels analysis
    labels_path = Path(labels_path)
    if labels_path.exists():
        with open(labels_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    l = json.loads(line)
                    for horizon in ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]:
                        key = f"return_{horizon}"
                        if l.get(key) is not None:
                            report["labels_by_horizon"][horizon] = report["labels_by_horizon"].get(horizon, 0) + 1

    # Unique instruments
    report["instruments"] = list(report["rows_by_instrument"].keys())

    # Write report
    report_path = output_dir / "reports" / "coverage_report_v1.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    # Write markdown
    md_path = output_dir / "reports" / "coverage_report_v1.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Historical Market Data Coverage Report V1\n\n")
        f.write("## Rows by Instrument\n\n")
        for k, v in sorted(report["rows_by_instrument"].items()):
            f.write(f"- {k}: {v}\n")
        f.write("\n## Rows by Interval\n\n")
        for k, v in sorted(report["rows_by_interval"].items()):
            f.write(f"- {k}: {v}\n")
        f.write("\n## Rows by Year\n\n")
        for k, v in sorted(report["rows_by_year"].items()):
            f.write(f"- {k}: {v}\n")
        f.write("\n## Derivative Coverage\n\n")
        for k, v in sorted(report["derivative_coverage"].items()):
            f.write(f"- {k}: {v}\n")
        f.write("\n## Event Windows by Family\n\n")
        for k, v in sorted(report["event_windows_by_family"].items()):
            f.write(f"- {k}: {v}\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars-path", default="data/intelligence/historical_market/normalized/market_bars_v1.jsonl.gz")
    parser.add_argument("--derivatives-path", default="data/intelligence/historical_market/normalized/derivative_snapshots_v1.jsonl.gz")
    parser.add_argument("--windows-path", default="data/intelligence/historical_market/event_windows/event_market_windows_v1.jsonl.gz")
    parser.add_argument("--labels-path", default="data/intelligence/historical_market/event_windows/market_reaction_labels_v1.jsonl")
    parser.add_argument("--index-path", default="data/intelligence/historical_market/indexes/historical_market_v1.sqlite")
    parser.add_argument("--output-dir", default="data/intelligence/historical_market")
    args = parser.parse_args()

    report = generate_coverage_report(
        bars_path=args.bars_path,
        derivatives_path=args.derivatives_path,
        windows_path=args.windows_path,
        labels_path=args.labels_path,
        index_path=args.index_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, indent=2, default=str))
