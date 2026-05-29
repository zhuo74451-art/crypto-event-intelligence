import argparse
import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Hyperliquid watched-position state history readiness.")
    parser.add_argument("--input", default=str(ROOT / "data" / "hyperliquid_position_state_history.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v081_hyperliquid_state_history_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v081_hyperliquid_state_history_summary.csv"))
    parser.add_argument("--by-position", default=str(ROOT / "results" / "v081_hyperliquid_state_history_by_position.csv"))
    parser.add_argument("--min-snapshots", type=int, default=12)
    parser.add_argument("--min-change-usd", type=float, default=5_000_000)
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


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    grouped = defaultdict(list)
    for row in rows:
        key = str(row.get("position_key", "") or "").strip()
        if key:
            grouped[key].append(row)

    output_rows = []
    for key, items in grouped.items():
        items = sorted(items, key=lambda r: str(r.get("updated_at_utc", "")))
        values = [safe_float(r.get("position_value_usd")) for r in items]
        sides = [str(r.get("side", "") or "").strip() for r in items]
        near_liq_count = sum(1 for r in items if str(r.get("near_liquidation", "") or "").strip().lower() == "true")
        max_step_change = 0.0
        changed_steps = 0
        for prev, cur in zip(values, values[1:]):
            delta = abs(cur - prev)
            max_step_change = max(max_step_change, delta)
            if delta >= args.min_change_usd:
                changed_steps += 1
        side_changes = sum(1 for prev, cur in zip(sides, sides[1:]) if prev and cur and prev != cur)
        latest = items[-1] if items else {}
        output_rows.append(
            {
                "position_key": key,
                "entity": latest.get("entity", ""),
                "asset_symbol": latest.get("asset_symbol", ""),
                "side": latest.get("side", ""),
                "snapshot_count": len(items),
                "first_updated_china": items[0].get("updated_at_china", "") if items else "",
                "last_updated_china": latest.get("updated_at_china", ""),
                "latest_position_value_usd": round(values[-1], 2) if values else 0,
                "min_position_value_usd": round(min(values), 2) if values else 0,
                "max_position_value_usd": round(max(values), 2) if values else 0,
                "max_step_change_usd": round(max_step_change, 2),
                "large_change_steps": changed_steps,
                "side_change_steps": side_changes,
                "near_liquidation_snapshots": near_liq_count,
                "history_status": "ready" if len(items) >= args.min_snapshots else "needs_more_history",
            }
        )
    output_rows.sort(key=lambda r: (r["history_status"] != "ready", -int(r["snapshot_count"]), -float(r["latest_position_value_usd"])))

    ready_positions = sum(1 for r in output_rows if r["history_status"] == "ready")
    max_snapshots = max([int(r["snapshot_count"]) for r in output_rows], default=0)
    summary = {
        "history_rows": len(rows),
        "position_count": len(output_rows),
        "ready_positions": ready_positions,
        "needs_more_history_positions": len(output_rows) - ready_positions,
        "max_snapshots": max_snapshots,
        "min_snapshots": args.min_snapshots,
        "large_change_steps": sum(int(r["large_change_steps"]) for r in output_rows),
        "side_change_steps": sum(int(r["side_change_steps"]) for r in output_rows),
        "near_liquidation_snapshots": sum(int(r["near_liquidation_snapshots"]) for r in output_rows),
        "status": "ready" if ready_positions else "needs_more_history",
    }
    fields = [
        "position_key",
        "entity",
        "asset_symbol",
        "side",
        "snapshot_count",
        "first_updated_china",
        "last_updated_china",
        "latest_position_value_usd",
        "min_position_value_usd",
        "max_position_value_usd",
        "max_step_change_usd",
        "large_change_steps",
        "side_change_steps",
        "near_liquidation_snapshots",
        "history_status",
    ]
    write_rows(normalize_path(args.by_position), output_rows, fields)
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    lines = [
        "# v0.8.1 Hyperliquid State History Report",
        "",
        f"- status: {summary['status']}",
        f"- history_rows: {len(rows)}",
        f"- position_count: {len(output_rows)}",
        f"- ready_positions: {ready_positions}",
        f"- max_snapshots: {max_snapshots} / {args.min_snapshots}",
        f"- large_change_steps: {summary['large_change_steps']}",
        "",
        "## Positions",
        "",
        "| entity | asset | side | snapshots | latest_value_usd | max_step_change_usd | status |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in output_rows[:30]:
        lines.append(
            f"| {row['entity']} | {row['asset_symbol']} | {row['side']} | {row['snapshot_count']} | {row['latest_position_value_usd']} | {row['max_step_change_usd']} | {row['history_status']} |"
        )
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "Use state history to detect position changes. A single current snapshot is not enough to prove a position-change alert.",
            "",
        ]
    )
    normalize_path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"status={summary['status']}")
    print(f"history_rows={len(rows)}")
    print(f"ready_positions={ready_positions}")
    print(f"wrote_report={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
