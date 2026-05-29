import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


ADDED_COLUMNS = [
    "delivery_bucket",
    "routing_score",
    "routing_reason",
    "interrupt_eligible",
    "board_eligible",
    "archive_eligible",
]


SUMMARY_COLUMNS = [
    "status",
    "input_rows",
    "output_rows",
    "interrupt_count",
    "board_count",
    "archive_count",
    "discard_count",
    "top_event_type",
    "top_asset",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route TG items into interrupt / board / archive / discard buckets.")
    parser.add_argument("--input", default=str(ROOT / "data" / "tg_drafts_v07_watcher_private_pilot.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_drafts_v09_routed.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v09_tg_delivery_routing_summary.csv"))
    parser.add_argument("--min-board-usd", type=float, default=10_000_000)
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
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def has_known_entity(row: dict) -> bool:
    text = " ".join(
        str(row.get(name, "") or "")
        for name in ["title", "draft_text", "context_summary", "source"]
    ).lower()
    if "某地址" in text or "链上大户" in text or "unknown" in text:
        return False
    return any(name in text for name in ["loraclexyz", "matrixport", "machi", "黄立成"])


def route_row(row: dict, min_board_usd: float) -> dict:
    event_type = str(row.get("event_type", "") or "").strip()
    asset = str(row.get("asset_symbol", "") or "").strip().upper()
    amount = safe_float(row.get("amount_usd"))
    severity = str(row.get("severity_tier", "") or "").strip().lower()
    needs_review = truthy(row.get("needs_model_review"))
    score = safe_float(row.get("alert_priority_score"))
    reasons = []

    if not asset:
        return route("discard", 0, "missing_asset")
    if event_type in {"other", ""}:
        return route("discard", 0, "unsupported_event_type")
    if needs_review:
        score -= 10
        reasons.append("needs_review_penalty")

    if event_type == "token_unlock":
        if amount < 10_000_000:
            return route("archive", max(score, 35), "small_unlock_archive_only")
        if amount >= 100_000_000:
            return route("interrupt", max(score, 90), "major_unlock_over_100m")
        return route("board", max(score, 70), "unlock_board")

    if event_type == "whale_position":
        draft_text = str(row.get("draft_text", "") or "")
        if "静态大仓位快照" in draft_text:
            if has_known_entity(row) and amount >= 75_000_000 and asset not in {"BTC", "ETH"}:
                return route("board", max(score, 72), "known_entity_static_unusual_position_board")
            return route("archive", max(score, 45), "static_position_snapshot_archive")
        if amount >= 100_000_000:
            return route("interrupt", max(score, 92), "hyperliquid_position_over_100m")
        if amount >= 30_000_000:
            return route("board", max(score, 75), "large_position_board")
        if amount >= min_board_usd:
            return route("board", max(score, 65), "position_board")
        return route("archive", max(score, 40), "small_position_archive")

    if event_type == "stablecoin_flow":
        if amount >= 100_000_000:
            return route("interrupt", max(score, 90), "stablecoin_flow_over_100m")
        if amount >= 50_000_000:
            return route("board", max(score, 72), "stablecoin_flow_board")
        return route("archive", max(score, 45), "small_stablecoin_flow_archive")

    if event_type == "cex_netflow":
        if amount >= 500_000_000:
            return route("interrupt", max(score, 95), "cex_netflow_over_500m")
        if amount >= 100_000_000:
            return route("board", max(score, 75), "cex_netflow_board")
        return route("archive", max(score, 45), "small_cex_netflow_archive")

    if event_type == "exchange_listing":
        return route("interrupt" if severity == "critical" else "board", max(score, 80), "exchange_listing")

    if event_type in {"funding_rate", "liquidation"}:
        if severity in {"critical", "high"} or amount >= min_board_usd:
            return route("board", max(score, 68), f"{event_type}_board")
        return route("archive", max(score, 40), f"{event_type}_archive")

    if amount >= 50_000_000:
        return route("board", max(score, 70), "large_amount_generic_board")
    if amount >= min_board_usd:
        return route("archive", max(score, 45), "generic_archive")
    return route("archive", max(score, 35), "low_magnitude_archive")


def route(bucket: str, score: float, reason: str) -> dict:
    return {
        "delivery_bucket": bucket,
        "routing_score": f"{score:.1f}",
        "routing_reason": reason,
        "interrupt_eligible": str(bucket == "interrupt").lower(),
        "board_eligible": str(bucket in {"interrupt", "board"}).lower(),
        "archive_eligible": str(bucket in {"interrupt", "board", "archive"}).lower(),
    }


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    rows = read_rows(input_path)
    output_rows = []
    for row in rows:
        routed = dict(row)
        routed.update(route_row(row, args.min_board_usd))
        output_rows.append(routed)

    existing_fields = list(rows[0].keys()) if rows else []
    fieldnames = [*existing_fields, *[name for name in ADDED_COLUMNS if name not in existing_fields]]
    write_rows(normalize_path(args.output), output_rows, fieldnames)

    buckets = Counter(row.get("delivery_bucket", "") for row in output_rows)
    event_types = Counter(row.get("event_type", "") or "unknown" for row in output_rows)
    assets = Counter(row.get("asset_symbol", "") or "unknown" for row in output_rows)
    summary = {
        "status": "pass",
        "input_rows": str(len(rows)),
        "output_rows": str(len(output_rows)),
        "interrupt_count": str(buckets.get("interrupt", 0)),
        "board_count": str(buckets.get("board", 0)),
        "archive_count": str(buckets.get("archive", 0)),
        "discard_count": str(buckets.get("discard", 0)),
        "top_event_type": event_types.most_common(1)[0][0] if event_types else "",
        "top_asset": assets.most_common(1)[0][0] if assets else "",
    }
    write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
    print(f"wrote routed items to {normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
