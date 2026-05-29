import argparse
import csv
import importlib.util
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def load_criteria_module():
    path = ROOT / "scripts" / "define_publishable_event_criteria.py"
    spec = importlib.util.spec_from_file_location("criteria", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate publishable criteria against golden known events.")
    parser.add_argument("--golden", default=str(ROOT / "data" / "v14_publishable_golden_events.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_publishable_criteria_validation.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_publishable_criteria_validation_summary.csv"))
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


def evaluate(row: dict, criteria) -> dict:
    short = {"short_price_in_flag": "pass", "price_in_1h": row.get("price_in_1h", "")}
    result = criteria.evaluate(row, {row.get("event_id", ""): short})
    expected = str(row.get("expected_publishable") or "").lower() == "true"
    actual = str(result.get("criteria_passed") or "").lower() == "true"
    return {
        **row,
        "actual_publishable": "true" if actual else "false",
        "validation_status": "pass" if actual == expected else "fail",
        "criteria_block_reason": result.get("criteria_block_reason", ""),
        "computed_source_tier": result.get("source_tier", ""),
    }


def main() -> int:
    args = parse_args()
    criteria = load_criteria_module()
    rows = [evaluate(row, criteria) for row in read_rows(normalize_path(args.golden))]
    write_rows(normalize_path(args.output), rows, list(rows[0].keys()) if rows else ["event_id"])
    failed = [row for row in rows if row["validation_status"] != "pass"]
    expected_positive = [row for row in rows if str(row.get("expected_publishable") or "").lower() == "true"]
    expected_negative = [row for row in rows if str(row.get("expected_publishable") or "").lower() != "true"]
    true_positive = [row for row in expected_positive if row["actual_publishable"] == "true"]
    false_negative = [row for row in expected_positive if row["actual_publishable"] != "true"]
    false_positive = [row for row in expected_negative if row["actual_publishable"] == "true"]
    predicted_positive = [row for row in rows if row["actual_publishable"] == "true"]
    rejection_reasons = Counter(
        reason
        for row in rows
        for reason in str(row.get("criteria_block_reason") or "").split(",")
        if reason and reason != "pass"
    )
    recall = len(true_positive) / len(expected_positive) if expected_positive else 0.0
    precision = len(true_positive) / len(predicted_positive) if predicted_positive else 0.0
    summary = {
        "generated_at_china": china_stamp(),
        "golden_rows": len(rows),
        "expected_publishable_rows": sum(1 for row in rows if str(row.get("expected_publishable") or "").lower() == "true"),
        "actual_publishable_rows": sum(1 for row in rows if row["actual_publishable"] == "true"),
        "recall": round(recall, 4),
        "precision_estimate": round(precision, 4),
        "false_positive_rows": len(false_positive),
        "false_negative_rows": len(false_negative),
        "failed_rows": len(failed),
        "top_rejection_reasons": ";".join(f"{k}:{v}" for k, v in rejection_reasons.most_common(8)),
        "status": "pass" if not failed else "fail",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"golden_rows={summary['golden_rows']}")
    print(f"actual_publishable_rows={summary['actual_publishable_rows']}")
    print(f"failed_rows={summary['failed_rows']}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
