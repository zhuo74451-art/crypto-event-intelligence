import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract and evaluate shadow-mode source events without sending to TG.")
    parser.add_argument("--registry", default=str(ROOT / "data" / "source_registry.csv"))
    parser.add_argument("--watcher-events", default=str(ROOT / "data" / "watcher_events_raw.csv"))
    parser.add_argument("--decisions", default=str(ROOT / "data" / "tg_radar_decision_log.csv"))
    parser.add_argument("--shadow-output", default=str(ROOT / "data" / "shadow_events_raw.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "shadow_source_evaluation_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "shadow_source_evaluation_report.md"))
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


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def shadow_registry(rows: list[dict]) -> dict[str, dict]:
    output = {}
    for row in rows:
        if not truthy(row.get("shadow_mode", "")):
            continue
        for field in ("source_id", "source_type"):
            value = str(row.get(field) or "").strip()
            if value:
                output[value] = row
    return output


def event_source_keys(row: dict) -> set[str]:
    keys = set()
    for field in ("watcher_source", "event_type"):
        value = str(row.get(field) or "").strip()
        if value:
            keys.add(value)
    source = str(row.get("source") or "").strip()
    if source:
        keys.add(source)
        if source.startswith("first_hand:"):
            keys.add(source.replace("first_hand:", "", 1))
    return keys


def is_shadow_event(row: dict, shadow_sources: dict[str, dict]) -> bool:
    return bool(event_source_keys(row) & set(shadow_sources))


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    registry_rows = read_rows(normalize_path(args.registry))
    shadow_sources = shadow_registry(registry_rows)
    watcher_events = read_rows(normalize_path(args.watcher_events))
    decision_rows = read_rows(normalize_path(args.decisions))

    shadow_events = [row for row in watcher_events if is_shadow_event(row, shadow_sources)]
    fieldnames = list(watcher_events[0].keys()) if watcher_events else []
    if fieldnames:
        write_rows(normalize_path(args.shadow_output), shadow_events, fieldnames)
    else:
        write_rows(normalize_path(args.shadow_output), [], ["event_id"])

    source_counts = Counter()
    route_counts = Counter()
    for row in shadow_events:
        matched = sorted(event_source_keys(row) & set(shadow_sources))
        source_counts[matched[0] if matched else "unknown"] += 1
        route_counts[str(row.get("publish_route") or "unknown").strip() or "unknown"] += 1

    decision_counts = Counter(str(row.get("source_type") or "unknown").strip() or "unknown" for row in decision_rows)
    source_preview = []
    for source_id, count in source_counts.most_common():
        reg = shadow_sources.get(source_id, {})
        source_preview.append(
            {
                "source_id": source_id,
                "source_type": reg.get("source_type", ""),
                "shadow_events": count,
                "tg_default_route": reg.get("tg_default_route", ""),
                "evaluation_status": reg.get("evaluation_status", ""),
            }
        )

    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "registered_shadow_source_keys": len(shadow_sources),
        "watcher_event_rows": len(watcher_events),
        "shadow_event_rows": len(shadow_events),
        "shadow_source_count": len(source_counts),
        "top_shadow_source": source_counts.most_common(1)[0][0] if source_counts else "",
        "top_shadow_route": route_counts.most_common(1)[0][0] if route_counts else "",
        "decision_source_types_seen": len(decision_counts),
        "shadow_output": str(normalize_path(args.shadow_output)),
        "report": str(normalize_path(args.report)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    route_lines = [f"- {route}: {count}" for route, count in route_counts.most_common()] if route_counts else ["- none: 0"]
    lines = [
        "# Shadow Source Evaluation",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- watcher_event_rows: {summary['watcher_event_rows']}",
        f"- shadow_event_rows: {summary['shadow_event_rows']}",
        f"- shadow_source_count: {summary['shadow_source_count']}",
        "",
        "## Shadow Sources With Current Rows",
        "",
        *markdown_table(source_preview, ["source_id", "source_type", "shadow_events", "tg_default_route", "evaluation_status"]),
        "",
        "## Route Distribution",
        "",
        *route_lines,
        "",
        "## Decision",
        "",
        "- Shadow rows are collected for evaluation only and should not be treated as production TG signals.",
        "- Promotion from shadow requires enough outcomes and a non-noisy source effectiveness report.",
        "",
    ]
    normalize_path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"shadow_event_rows={len(shadow_events)}")
    print(f"wrote_shadow_output={normalize_path(args.shadow_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
