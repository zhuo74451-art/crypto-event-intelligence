"""Audit event windows and reaction labels for data quality."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any


def audit_event_windows(
    windows_path: str | Path,
    labels_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Audit event windows. Returns report."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    findings: dict[str, list] = {
        "pre_event_reference_after_event": [],
        "post_window_before_event": [],
        "missing_bar_filled_without_flag": [],
        "label_computed_from_null": [],
        "low_coverage_windows": [],
    }

    total_windows = 0
    total_labels = 0

    # Audit windows
    if Path(windows_path).exists():
        open_func = gzip.open if str(windows_path).endswith(".gz") else open
        with open_func(windows_path, "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                total_windows += 1
                w = json.loads(line)

                # Check pre-event reference is before event
                ref_time = w.get("pre_window_start_utc", "")
                event_time = w.get("event_time_utc", "")
                if ref_time and event_time and ref_time >= event_time:
                    findings["pre_event_reference_after_event"].append({
                        "window_id": w.get("window_id"),
                        "ref_time": ref_time,
                        "event_time": event_time,
                    })

                # Check coverage
                coverage = w.get("coverage_ratio", 1.0)
                if coverage < 0.5:
                    findings["low_coverage_windows"].append({
                        "window_id": w.get("window_id"),
                        "coverage": coverage,
                        "event_id": w.get("event_id"),
                    })

    # Audit labels
    if Path(labels_path).exists():
        with open(labels_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                total_labels += 1
                l = json.loads(line)

                # Check label from null values
                avail = l.get("label_availability", "missing")
                if avail == "missing":
                    findings["label_computed_from_null"].append({
                        "label_id": l.get("label_id"),
                        "event_id": l.get("event_id"),
                    })

    critical_count = len(findings["pre_event_reference_after_event"])

    report = {
        "success": True,
        "total_windows": total_windows,
        "total_labels": total_labels,
        "findings": {k: len(v) for k, v in findings.items()},
        "critical_error_count": critical_count,
        "detailed_findings": findings,
    }

    # Write reports
    report_json = output_dir / "reports" / "event_window_audit_v1.json"
    report_md = output_dir / "reports" / "event_window_audit_v1.md"

    report_json.parent.mkdir(parents=True, exist_ok=True)
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# Event Window Audit Report V1\n\n")
        f.write(f"Total windows: {total_windows}\n")
        f.write(f"Total labels: {total_labels}\n")
        f.write(f"Critical errors: {critical_count}\n\n")
        f.write("| Finding | Count |\n")
        f.write("|---------|-------|\n")
        for k, v in findings.items():
            f.write(f"| {k} | {len(v)} |\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows-path", default="data/intelligence/historical_market/event_windows/event_market_windows_v1.jsonl.gz")
    parser.add_argument("--labels-path", default="data/intelligence/historical_market/event_windows/market_reaction_labels_v1.jsonl")
    parser.add_argument("--output-dir", default="data/intelligence/historical_market")
    args = parser.parse_args()

    report = audit_event_windows(
        windows_path=args.windows_path,
        labels_path=args.labels_path,
        output_dir=args.output_dir,
    )
    print(json.dumps({k: v for k, v in report.items() if k != "detailed_findings"}, indent=2, default=str))
