import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


REGISTRY_FIELDS = [
    "source_id",
    "source_type",
    "source_family",
    "adapter_script",
    "primary_output",
    "enabled",
    "shadow_mode",
    "latency_target_seconds",
    "cost_level",
    "confidence_level",
    "tg_default_route",
    "evaluation_status",
    "last_eval_date",
    "owner",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and summarize source_registry.csv.")
    parser.add_argument("--registry", default=str(ROOT / "data" / "source_registry.csv"))
    parser.add_argument("--watcher-events", default=str(ROOT / "data" / "watcher_events_raw.csv"))
    parser.add_argument("--alert-ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--decision-log", default=str(ROOT / "data" / "tg_radar_decision_log.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "source_registry_report.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "source_registry_report.md"))
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


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def source_type_from_watcher(row: dict) -> str:
    source = str(row.get("watcher_source") or row.get("source") or "").lower()
    event_type = str(row.get("event_type") or "").lower()
    raw_signal = str(row.get("raw_signal_type") or "").lower()
    if "hyperliquid" in source or "hyperliquid" in raw_signal:
        return "hyperliquid"
    if "token_unlock" in source or event_type == "token_unlock":
        return "token_unlock"
    if "cex_netflow" in source or event_type == "cex_netflow":
        return "cex_netflow"
    if "stablecoin" in source or event_type == "stablecoin_flow":
        return "stablecoin_flow"
    if "funding" in source or event_type == "funding_rate":
        return "funding_rate"
    if "listing" in source or event_type == "exchange_listing":
        return "exchange_listing"
    if "liquidation" in source or event_type == "lending_liquidation":
        return "lending_liquidation"
    if "address" in source or "transfer" in raw_signal:
        return "address_transfer"
    return event_type or "unknown"


def counter_by(rows: list[dict], field: str) -> Counter:
    return Counter(str(row.get(field) or "unknown").strip() or "unknown" for row in rows)


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    registry_path = normalize_path(args.registry)
    registry = read_rows(registry_path)
    watcher_rows = read_rows(normalize_path(args.watcher_events))
    ledger_rows = read_rows(normalize_path(args.alert_ledger))
    decision_rows = read_rows(normalize_path(args.decision_log))

    registry_source_types = {str(row.get("source_type") or "").strip() for row in registry if row.get("source_type")}
    source_ids = [str(row.get("source_id") or "").strip() for row in registry]
    duplicate_ids = [source for source, count in Counter(source_ids).items() if source and count > 1]
    missing_required = []
    missing_files = []
    missing_scripts = []
    invalid_routes = []
    for row in registry:
        sid = str(row.get("source_id") or "").strip() or "unknown"
        for field in REGISTRY_FIELDS:
            if field in {"last_eval_date", "notes"}:
                continue
            if not str(row.get(field) or "").strip():
                missing_required.append(f"{sid}:{field}")
        route = str(row.get("tg_default_route") or "").strip()
        if route not in {"interrupt", "board", "digest", "archive", "discard"}:
            invalid_routes.append(f"{sid}:{route}")
        script = normalize_path(row.get("adapter_script") or "")
        output = normalize_path(row.get("primary_output") or "")
        if str(row.get("adapter_script") or "").strip() and not script.exists():
            missing_scripts.append(str(row.get("source_id") or "unknown"))
        if str(row.get("primary_output") or "").strip() and not output.exists():
            missing_files.append(str(row.get("source_id") or "unknown"))

    watcher_counter = Counter(source_type_from_watcher(row) for row in watcher_rows)
    ledger_counter = counter_by(ledger_rows, "source_type")
    decision_counter = counter_by(decision_rows, "source_type")
    unregistered_seen = sorted(
        {
            key
            for key in set(watcher_counter) | set(ledger_counter) | set(decision_counter)
            if key and key != "unknown" and key not in registry_source_types
        }
    )

    enabled_count = sum(1 for row in registry if truthy(row.get("enabled", "")))
    shadow_count = sum(1 for row in registry if truthy(row.get("shadow_mode", "")))
    live_count = enabled_count - shadow_count
    status = "pass"
    flags = []
    if duplicate_ids:
        status = "fail"
        flags.append("duplicate_source_id")
    if missing_required:
        status = "fail"
        flags.append("missing_required_fields")
    if invalid_routes:
        status = "fail"
        flags.append("invalid_route")
    if missing_scripts:
        flags.append("missing_adapter_script")
        if status == "pass":
            status = "warning"
    if missing_files:
        flags.append("missing_primary_output")
        if status == "pass":
            status = "warning"
    if unregistered_seen:
        flags.append("unregistered_observed_source_type")
        if status == "pass":
            status = "warning"

    rows = [
        {
            "status": status,
            "generated_at_china": china_stamp(),
            "registry_rows": len(registry),
            "enabled_count": enabled_count,
            "shadow_count": shadow_count,
            "live_count": live_count,
            "watcher_rows": len(watcher_rows),
            "ledger_rows": len(ledger_rows),
            "decision_rows": len(decision_rows),
            "duplicate_source_ids": ",".join(duplicate_ids),
            "missing_required_count": len(missing_required),
            "missing_adapter_scripts": ",".join(missing_scripts),
            "missing_primary_outputs": ",".join(missing_files),
            "unregistered_seen": ",".join(unregistered_seen),
            "quality_flags": ",".join(flags),
        }
    ]
    write_rows(normalize_path(args.summary), rows, list(rows[0].keys()))

    preview = []
    for row in registry:
        stype = str(row.get("source_type") or "")
        preview.append(
            {
                "source_id": row.get("source_id", ""),
                "type": stype,
                "enabled": row.get("enabled", ""),
                "shadow": row.get("shadow_mode", ""),
                "route": row.get("tg_default_route", ""),
                "watcher_rows": watcher_counter.get(stype, 0),
                "sent_rows": ledger_counter.get(stype, 0),
                "decision_rows": decision_counter.get(stype, 0),
                "status": row.get("evaluation_status", ""),
            }
        )

    lines = [
        "# Source Registry Report",
        "",
        f"- generated_at_china: {rows[0]['generated_at_china']}",
        f"- status: {status}",
        f"- registry_rows: {len(registry)}",
        f"- enabled_count: {enabled_count}",
        f"- shadow_count: {shadow_count}",
        f"- live_count: {live_count}",
        f"- unregistered_seen: {', '.join(unregistered_seen) if unregistered_seen else 'none'}",
        "",
        "## Registered Sources",
        "",
        *markdown_table(preview, ["source_id", "type", "enabled", "shadow", "route", "watcher_rows", "sent_rows", "decision_rows", "status"]),
        "",
        "## Validation Flags",
        "",
        f"- duplicate_source_ids: {', '.join(duplicate_ids) if duplicate_ids else 'none'}",
        f"- missing_required_count: {len(missing_required)}",
        f"- missing_adapter_scripts: {', '.join(missing_scripts) if missing_scripts else 'none'}",
        f"- missing_primary_outputs: {', '.join(missing_files) if missing_files else 'none'}",
        "",
        "This report is source governance only. It does not provide trading advice.",
        "",
    ]
    normalize_path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"status={status}")
    print(f"registry_rows={len(registry)}")
    print(f"wrote_summary={normalize_path(args.summary)}")
    print(f"wrote_report={normalize_path(args.output)}")
    return 0 if status in {"pass", "warning"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
