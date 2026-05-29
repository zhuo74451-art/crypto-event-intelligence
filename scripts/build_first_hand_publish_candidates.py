import argparse
import csv
import hashlib
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route first-hand watcher alerts into interrupt/digest/archive candidates.")
    parser.add_argument("--input", default=str(ROOT / "data" / "watcher_alerts_raw.csv"))
    parser.add_argument("--rules", default=str(ROOT / "config" / "routing_rules.yaml"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_first_hand_publish_candidates.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_first_hand_publish_candidates_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_first_hand_publish_candidates.md"))
    parser.add_argument("--min-token-unlock-usd", type=float, default=10_000_000)
    parser.add_argument("--min-token-unlock-pct", type=float, default=5.0)
    parser.add_argument("--min-hyperliquid-delta-usd", type=float, default=5_000_000)
    parser.add_argument("--min-hyperliquid-delta-pct", type=float, default=10.0)
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


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def parse_rule_value(rule: str, key: str) -> float:
    for part in str(rule or "").split(";"):
        if part.startswith(f"{key}="):
            return safe_float(part.split("=", 1)[1])
    return 0.0


def load_simple_yaml(path: Path) -> dict:
    data: dict[str, dict] = {}
    current = None
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1].strip()
            data[current] = {}
        elif current and ":" in line:
            key, value = line.strip().split(":", 1)
            data[current][key.strip()] = value.strip()
    return data


def cfg_float(config: dict, section: str, key: str, default: float) -> float:
    return safe_float(config.get(section, {}).get(key)) or default


def event_hash(row: dict) -> str:
    basis = "|".join(
        str(row.get(key) or "").strip().lower()
        for key in ["watcher_source", "event_type_l1", "event_type_l2", "asset_symbol", "primary_address", "counterparty_address"]
    )
    return hashlib.sha256(basis.encode("utf-8", errors="replace")).hexdigest()[:16]


def route(row: dict, args: argparse.Namespace, config: dict) -> dict:
    source = str(row.get("watcher_source") or "")
    event_l2 = str(row.get("event_type_l2") or "")
    amount = safe_float(row.get("amount_usd"))
    metric_change_pct = abs(safe_float(row.get("metric_change_pct")))
    threshold_rule = str(row.get("threshold_rule") or "")
    delta_usd = abs(parse_rule_value(threshold_rule, "delta_usd"))
    route_value = "archive"
    reason = []
    source_tier = "first_hand_local_watcher"
    publish_window = "none"

    if source == "hyperliquid_clearinghouse_state":
        min_delta_usd = cfg_float(config, "intraday_alert", "hyperliquid_min_delta_usd", args.min_hyperliquid_delta_usd)
        min_delta_pct = cfg_float(config, "intraday_alert", "hyperliquid_min_delta_pct", args.min_hyperliquid_delta_pct)
        if event_l2 == "hyperliquid_perp_position_state_change" or delta_usd >= min_delta_usd or metric_change_pct >= min_delta_pct:
            route_value = "intraday_candidate"
            publish_window = "intraday"
            reason.append("large_position_state_change")
        else:
            reason.append("static_position_snapshot")
    elif source == "token_unlock_calendar":
        unlock_pct = safe_float(row.get("metric_value"))
        min_unlock_usd = cfg_float(config, "daily_digest", "token_unlock_min_usd", args.min_token_unlock_usd)
        min_unlock_pct = cfg_float(config, "daily_digest", "token_unlock_min_pct", args.min_token_unlock_pct)
        if amount >= min_unlock_usd and unlock_pct >= min_unlock_pct:
            route_value = "daily_digest_candidate"
            publish_window = "morning_or_evening_digest"
            reason.append("large_scheduled_unlock")
        else:
            reason.append("small_or_low_pct_unlock")
    elif source == "cex_listing_announcement":
        if event_l2 == "cex_listing_announcement":
            route_value = "digest_candidate"
            publish_window = "digest"
            reason.append("public_cex_listing_announcement")
        else:
            reason.append("unknown_cex_listing_shape")
    elif source in {"stablecoin_mint_burn", "cex_netflow"}:
        min_flow = cfg_float(config, "intraday_alert", "stablecoin_min_flow_usd", 50_000_000)
        if amount >= min_flow:
            route_value = "intraday_candidate"
            publish_window = "intraday"
            reason.append("large_flow_amount")
        else:
            reason.append("flow_below_threshold")
    else:
        reason.append("unsupported_first_hand_source")

    item = dict(row)
    item.update(
        {
            "v14_first_hand_route": route_value,
            "v14_first_hand_reason": ",".join(reason),
            "source_tier": source_tier,
            "publish_window": publish_window,
            "verification_basis": "local_watcher_structured_output",
            "event_content_hash": event_hash(row),
            "event_severity": severity(route_value, source, amount),
        }
    )
    return item


def severity(route_value: str, source: str, amount: float) -> int:
    if route_value == "intraday_candidate":
        return 90
    if source == "cex_listing_announcement":
        return 70
    if source == "token_unlock_calendar" and amount >= 10_000_000:
        return 60
    if route_value != "archive":
        return 50
    return 0


def money(value) -> str:
    number = safe_float(value)
    if number >= 100_000_000:
        return f"{number / 100_000_000:.2f} 亿美元"
    if number >= 10_000:
        return f"{number / 10_000:.2f} 万美元"
    return f"{number:.2f} 美元"


def render_report(rows: list[dict], summary: dict) -> str:
    counts = Counter(row["v14_first_hand_route"] for row in rows)
    lines = [
        "# v14 First-Hand Publish Candidates",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- intraday_candidate_rows: {summary['intraday_candidate_rows']}",
        f"- digest_candidate_rows: {summary['digest_candidate_rows']}",
        f"- daily_digest_candidate_rows: {summary['daily_digest_candidate_rows']}",
        f"- archived_rows: {summary['archived_rows']}",
        "",
        "## Route Counts",
        "",
    ]
    for name, count in counts.most_common():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Candidate Samples", "", "| route | source | asset | amount | reason |", "|---|---|---|---:|---|"])
    for row in [item for item in rows if item["v14_first_hand_route"] != "archive"][:30]:
        lines.append(
            f"| {row['v14_first_hand_route']} | {row.get('watcher_source','')} | {row.get('asset_symbol','')} | {money(row.get('amount_usd'))} | {row['v14_first_hand_reason']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    config = load_simple_yaml(normalize_path(args.rules))
    raw_rows = read_rows(normalize_path(args.input))
    routed = [route(row, args, config) for row in raw_rows]
    seen = set()
    rows = []
    duplicate_count = 0
    for row in sorted(routed, key=lambda item: (-safe_float(item.get("event_severity")), str(item.get("observed_at_utc") or ""))):
        h = str(row.get("event_content_hash") or "")
        if h in seen:
            duplicate_count += 1
            continue
        seen.add(h)
        rows.append(row)
    write_rows(normalize_path(args.output), rows, list(rows[0].keys()) if rows else ["alert_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(rows),
        "intraday_candidate_rows": sum(1 for row in rows if row["v14_first_hand_route"] == "intraday_candidate"),
        "digest_candidate_rows": sum(1 for row in rows if row["v14_first_hand_route"] == "digest_candidate"),
        "daily_digest_candidate_rows": sum(1 for row in rows if row["v14_first_hand_route"] == "daily_digest_candidate"),
        "archived_rows": sum(1 for row in rows if row["v14_first_hand_route"] == "archive"),
        "duplicate_rows": duplicate_count,
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.markdown_output).write_text(render_report(rows, summary), encoding="utf-8")
    print(f"input_rows={summary['input_rows']}")
    print(f"intraday_candidate_rows={summary['intraday_candidate_rows']}")
    print(f"digest_candidate_rows={summary['digest_candidate_rows']}")
    print(f"daily_digest_candidate_rows={summary['daily_digest_candidate_rows']}")
    print(f"archived_rows={summary['archived_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
