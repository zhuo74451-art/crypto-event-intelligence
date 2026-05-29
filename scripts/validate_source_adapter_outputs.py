import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


REQUIRED_FIELDS = [
    "event_id",
    "event_time",
    "title",
    "content",
    "source",
    "asset_symbol",
    "event_type",
    "direction_hint",
    "importance",
]

V11_REQUIRED_FIELDS = [
    "watcher_source",
    "raw_signal_type",
    "event_time_china",
    "event_type_l2",
    "publish_route",
    "threshold_rule",
    "metric_value",
    "raw_json",
]

RECOMMENDED_FIELDS = [
    "entity_label",
    "address",
    "tx_hash",
    "amount_native",
    "amount_usd",
    "confidence",
    "risk_category",
    "needs_model_review",
    "model_review_reason",
]

VALID_ROUTES = {"interrupt", "board", "review", "archive", "discard", "digest", ""}
VALID_DIRECTION = {"observe", "risk", "positive", "negative", "neutral", "discard", ""}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate normalized source adapter outputs.")
    parser.add_argument("--input", default=str(ROOT / "data" / "watcher_events_raw.csv"))
    parser.add_argument("--registry", default=str(ROOT / "data" / "source_registry.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "source_adapter_validation_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "source_adapter_validation_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "source_adapter_validation_report.md"))
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


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def registered_source_ids(rows: list[dict]) -> set[str]:
    ids = set()
    for row in rows:
        for field in ("source_id", "source_type"):
            value = str(row.get(field) or "").strip()
            if value:
                ids.add(value)
    return ids


def source_registered(row: dict, registry_ids: set[str]) -> bool:
    values = [
        str(row.get("watcher_source") or "").strip(),
        str(row.get("source") or "").replace("first_hand:", "").strip(),
        str(row.get("event_type") or "").strip(),
    ]
    return any(value in registry_ids for value in values if value)


def parse_time_ok(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.endswith("Z") and "T" in text:
        try:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    for fmt in ("%Y-%m-%d %H:%M:%S UTC+8", "%Y-%m-%d %H:%M:%S"):
        try:
            datetime.strptime(text, fmt.replace(" UTC+8", ""))
            return True
        except ValueError:
            pass
    return False


def validate_row(row: dict, registry_ids: set[str]) -> tuple[str, list[str]]:
    flags = []
    for field in REQUIRED_FIELDS:
        if not str(row.get(field) or "").strip():
            flags.append(f"missing_required:{field}")
    for field in V11_REQUIRED_FIELDS:
        if not str(row.get(field) or "").strip():
            flags.append(f"missing_v11_required:{field}")
    if not parse_time_ok(row.get("event_time", "")):
        flags.append("bad_event_time")
    if row.get("event_time_china") and "UTC+8" not in str(row.get("event_time_china")):
        flags.append("non_china_time_display")
    if str(row.get("publish_route") or "").strip() not in VALID_ROUTES:
        flags.append("invalid_publish_route")
    if str(row.get("direction_hint") or "").strip() not in VALID_DIRECTION:
        flags.append("invalid_direction_hint")
    if not source_registered(row, registry_ids):
        flags.append("unregistered_source")
    if not str(row.get("asset_symbol") or "").strip() and str(row.get("publish_route") or "") not in {"discard", "archive"}:
        flags.append("missing_asset_non_archive")
    status = "pass"
    if any(flag.startswith("missing_required") or flag in {"bad_event_time", "invalid_publish_route"} for flag in flags):
        status = "fail"
    elif flags:
        status = "warning"
    return status, flags


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    registry_ids = registered_source_ids(read_rows(normalize_path(args.registry)))
    report = []
    for idx, row in enumerate(rows, start=1):
        status, flags = validate_row(row, registry_ids)
        report.append(
            {
                "row_number": idx,
                "event_id": row.get("event_id", ""),
                "source": row.get("source", ""),
                "watcher_source": row.get("watcher_source", ""),
                "event_type": row.get("event_type", ""),
                "asset_symbol": row.get("asset_symbol", ""),
                "publish_route": row.get("publish_route", ""),
                "validation_status": status,
                "validation_flags": ",".join(flags),
            }
        )

    fail_count = sum(1 for row in report if row["validation_status"] == "fail")
    warning_count = sum(1 for row in report if row["validation_status"] == "warning")
    pass_count = sum(1 for row in report if row["validation_status"] == "pass")
    overall = "fail" if fail_count else "warning" if warning_count else "pass"
    write_rows(normalize_path(args.output), report, list(report[0].keys()) if report else ["validation_status"])
    summary = {
        "status": overall,
        "generated_at_china": china_stamp(),
        "input": str(normalize_path(args.input)),
        "row_count": len(rows),
        "pass_count": pass_count,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "output": str(normalize_path(args.output)),
        "markdown_output": str(normalize_path(args.markdown_output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# Source Adapter Validation Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- status: {overall}",
        f"- row_count: {len(rows)}",
        f"- pass_count: {pass_count}",
        f"- warning_count: {warning_count}",
        f"- fail_count: {fail_count}",
        "",
        "## Non-Pass Rows",
        "",
        *markdown_table(
            [row for row in report if row["validation_status"] != "pass"][:40],
            ["row_number", "event_id", "watcher_source", "event_type", "asset_symbol", "publish_route", "validation_status", "validation_flags"],
        ),
        "",
        "This validation checks source schema quality only. It does not provide trading advice.",
        "",
    ]
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"status={overall}")
    print(f"row_count={len(rows)}")
    print(f"fail_count={fail_count}")
    return 0 if overall in {"pass", "warning"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
