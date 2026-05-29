import argparse
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        append_csv_rows,
        compact_number,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        safe_float,
        write_csv_rows,
        write_summary,
        dt_to_utc_iso,
        utc_iso_to_china,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        append_csv_rows,
        compact_number,
        json_dumps,
        make_alert_id,
        make_dedupe_key,
        normalize_path,
        now_utc,
        read_csv_rows,
        safe_float,
        write_csv_rows,
        write_summary,
        dt_to_utc_iso,
        utc_iso_to_china,
    )


ROOT = Path(__file__).resolve().parents[1]
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"

STATE_COLUMNS = [
    "position_key",
    "updated_at_utc",
    "updated_at_china",
    "address",
    "entity",
    "asset_symbol",
    "side",
    "szi_abs",
    "position_value_usd",
    "entry_px",
    "liquidation_px",
    "mark_px",
    "liquidation_distance_pct",
    "near_liquidation",
    "unrealized_pnl",
    "return_on_equity",
    "above_threshold",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch curated Hyperliquid accounts for large perp positions.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "hyperliquid_watchlist.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "watcher_alerts_hyperliquid_positions.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v07_hyperliquid_position_watcher_summary.csv"))
    parser.add_argument("--state", default=str(ROOT / "data" / "hyperliquid_position_state.csv"))
    parser.add_argument("--history", default=str(ROOT / "data" / "hyperliquid_position_state_history.csv"))
    parser.add_argument("--limit-addresses", type=int, default=25)
    parser.add_argument("--min-change-pct", type=float, default=0.15)
    parser.add_argument("--min-change-usd", type=float, default=5_000_000)
    parser.add_argument("--near-liquidation-pct", type=float, default=0.08)
    parser.add_argument("--alert-closed", default="true")
    parser.add_argument("--alert-first-seen", default="false")
    parser.add_argument("--alert-snapshot", default="false", help="Emit one current-position snapshot alert for large unchanged positions.")
    parser.add_argument("--sample-if-empty", default="true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def is_enabled(row: dict) -> bool:
    return str(row.get("enabled", "")).strip().lower() in {"1", "true", "yes", "y"}


def address(value: str) -> str:
    return str(value or "").strip().lower()


def post_hyperliquid_state(user: str) -> dict:
    import requests

    last_error = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                HYPERLIQUID_INFO_URL,
                json={"type": "clearinghouseState", "user": user},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            raise RuntimeError(f"unexpected Hyperliquid response: {str(payload)[:200]}")
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                import time

                time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"Hyperliquid request failed: {last_error}")


def sample_alerts() -> list[dict]:
    observed = dt_to_utc_iso(now_utc())
    china = utc_iso_to_china(observed)
    sample = {
        "alert_id": make_alert_id("sample_hyperliquid_position", "0xsample", "BTC", "short"),
        "observed_at_utc": observed,
        "observed_at_china": china,
        "source_type": "first_hand",
        "watcher_source": "sample_hyperliquid_clearinghouse_state",
        "blockchain": "hyperliquid",
        "block_number": "",
        "tx_hash": "",
        "log_index": "",
        "primary_entity": "Loracle",
        "primary_address": "0x0000000000000000000000000000000000000000",
        "counterparty_entity": "Hyperliquid",
        "counterparty_address": "",
        "asset_symbol": "BTC",
        "token_address": "",
        "amount_native": "476.4",
        "amount_usd": "36900000.00",
        "metric_type": "hyperliquid_position_short",
        "metric_value": "36900000.00",
        "metric_change_pct": "",
        "event_type_l1": "whale_position",
        "event_type_l2": "hyperliquid_perp_position",
        "risk_category": "perp_position",
        "confidence": "sample",
        "relevance_score": "0.86",
        "threshold_rule": "sample_position_value>=10000000",
        "dedupe_key": make_dedupe_key("sample_hyperliquid_position", "BTC", "short"),
        "needs_model_review": "true",
        "model_review_reason": "large_hyperliquid_position",
        "publish_route": "review",
        "status": "sample",
        "skip_reason": "",
        "raw_json": json_dumps({"sample": True}),
    }
    row = {column: "" for column in ALERT_COLUMNS}
    row.update(sample)
    return [row]


def position_key(user: str, coin: str) -> str:
    return f"{address(user)}:{str(coin or '').strip().upper()}"


def liquidation_distance(position: dict, szi_abs: float, position_value: float) -> tuple[float, float]:
    if szi_abs <= 0 or position_value <= 0:
        return 0.0, 0.0
    mark_px = position_value / szi_abs
    liquidation_px = safe_float(position.get("liquidationPx"))
    if mark_px <= 0 or liquidation_px <= 0:
        return mark_px, 0.0
    return mark_px, abs(mark_px - liquidation_px) / mark_px


def load_state(path: Path) -> dict[str, dict]:
    output = {}
    for row in read_csv_rows(path):
        key = str(row.get("position_key", "")).strip()
        if key:
            output[key] = row
    return output


def state_row(position_row: dict, account: dict, observed_iso: str, threshold: float, near_liquidation_pct: float) -> dict | None:
    position = position_row.get("position", {}) if isinstance(position_row, dict) else {}
    if not isinstance(position, dict):
        return None
    coin = str(position.get("coin", "")).strip().upper()
    szi = safe_float(position.get("szi"))
    if not coin or not szi:
        return None
    side = "long" if szi > 0 else "short"
    value_usd = abs(safe_float(position.get("positionValue")))
    mark_px, liq_distance = liquidation_distance(position, abs(szi), value_usd)
    user = address(account.get("address"))
    return {
        "position_key": position_key(user, coin),
        "updated_at_utc": observed_iso,
        "updated_at_china": utc_iso_to_china(observed_iso),
        "address": account.get("address", ""),
        "entity": account.get("entity") or account.get("label", ""),
        "asset_symbol": coin,
        "side": side,
        "szi_abs": f"{abs(szi):.12g}",
        "position_value_usd": f"{value_usd:.2f}",
        "entry_px": str(position.get("entryPx", "") or ""),
        "liquidation_px": str(position.get("liquidationPx", "") or ""),
        "mark_px": f"{mark_px:.8f}" if mark_px else "",
        "liquidation_distance_pct": f"{liq_distance:.6f}" if liq_distance else "",
        "near_liquidation": str(bool(liq_distance and liq_distance <= near_liquidation_pct)).lower(),
        "unrealized_pnl": str(position.get("unrealizedPnl", "") or ""),
        "return_on_equity": str(position.get("returnOnEquity", "") or ""),
        "above_threshold": str(value_usd >= threshold).lower(),
    }


def classify_change(
    current: dict,
    previous: dict | None,
    threshold: float,
    min_change_pct: float,
    min_change_usd: float,
    alert_first_seen: bool,
) -> tuple[str, float, float, bool]:
    current_value = safe_float(current.get("position_value_usd"))
    previous_value = safe_float(previous.get("position_value_usd")) if previous else 0.0
    delta = current_value - previous_value
    change_pct = delta / previous_value if previous_value > 0 else 0.0
    current_side = str(current.get("side", "")).strip()
    previous_side = str(previous.get("side", "")).strip() if previous else ""
    previous_above = str(previous.get("above_threshold", "")).strip().lower() == "true" if previous else False
    current_near_liq = str(current.get("near_liquidation", "")).strip().lower() == "true"
    previous_near_liq = str(previous.get("near_liquidation", "")).strip().lower() == "true" if previous else False
    current_above = current_value >= threshold

    if not current_above:
        return "below_threshold", delta, change_pct, False
    if previous is None:
        return "first_seen", delta, change_pct, alert_first_seen
    if current_near_liq and not previous_near_liq:
        return "near_liquidation", delta, change_pct, True
    if previous_side and previous_side != current_side:
        return "direction_changed", delta, change_pct, True
    if not previous_above and current_above:
        return "crossed_threshold", delta, change_pct, True
    if abs(delta) >= min_change_usd and abs(change_pct) >= min_change_pct:
        return "position_increased" if delta > 0 else "position_decreased", delta, change_pct, True
    return "unchanged_position", delta, change_pct, False


def build_alert(
    position_row: dict,
    account: dict,
    observed_iso: str,
    change_type: str,
    delta_usd: float,
    change_pct: float,
) -> tuple[dict | None, str]:
    position = position_row.get("position", {}) if isinstance(position_row, dict) else {}
    if not isinstance(position, dict):
        return None, "missing_position"

    coin = str(position.get("coin", "")).strip().upper()
    szi = safe_float(position.get("szi"))
    position_value = abs(safe_float(position.get("positionValue")))
    threshold = safe_float(account.get("alert_threshold_usd"), 10_000_000)
    if not coin or not szi:
        return None, "empty_position"
    if position_value < threshold:
        return None, "below_threshold"

    side = "long" if szi > 0 else "short"
    user = address(account.get("address"))
    change_bucket = int(abs(delta_usd) // 1_000_000)
    dedupe_key = make_dedupe_key("hyperliquid_position", user, coin, side, change_type, change_bucket)
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("hyperliquid_position", user, coin, side, change_type, change_bucket),
            "observed_at_utc": observed_iso,
            "observed_at_china": utc_iso_to_china(observed_iso),
            "source_type": "first_hand",
            "watcher_source": "hyperliquid_clearinghouse_state",
            "blockchain": "hyperliquid",
            "block_number": "",
            "tx_hash": "",
            "log_index": "",
            "primary_entity": account.get("entity") or account.get("label", ""),
            "primary_address": account.get("address", ""),
            "counterparty_entity": "Hyperliquid",
            "counterparty_address": "",
            "asset_symbol": coin,
            "token_address": "",
            "amount_native": f"{abs(szi):.12g}",
            "amount_usd": f"{position_value:.2f}",
            "metric_type": f"hyperliquid_position_{side}",
            "metric_value": f"{position_value:.2f}",
            "metric_change_pct": f"{change_pct:.6f}",
            "event_type_l1": "whale_position",
            "event_type_l2": f"hyperliquid_perp_{change_type}",
            "risk_category": "perp_position",
            "confidence": account.get("label_confidence", "medium"),
            "relevance_score": "0.88" if position_value >= 50_000_000 else "0.78",
            "threshold_rule": f"position_value_usd>={threshold:.0f};change_type={change_type};delta_usd={delta_usd:.2f};change_pct={change_pct:.6f}",
            "dedupe_key": dedupe_key,
            "needs_model_review": "true",
            "model_review_reason": "large_hyperliquid_position",
            "publish_route": "review",
            "status": "ok",
            "skip_reason": "",
            "raw_json": json_dumps({"change_type": change_type, "delta_usd": delta_usd, "change_pct": change_pct, "current": position_row}),
        }
    )
    return alert, ""


def build_closed_alert(previous: dict, observed_iso: str) -> dict:
    user = address(previous.get("address"))
    coin = str(previous.get("asset_symbol", "")).strip().upper()
    entity = str(previous.get("entity", "") or "").strip()
    previous_value = safe_float(previous.get("position_value_usd"))
    side = str(previous.get("side", "") or "").strip()
    alert = {column: "" for column in ALERT_COLUMNS}
    alert.update(
        {
            "alert_id": make_alert_id("hyperliquid_position_closed", user, coin, side, int(previous_value // 1_000_000)),
            "observed_at_utc": observed_iso,
            "observed_at_china": utc_iso_to_china(observed_iso),
            "source_type": "first_hand",
            "watcher_source": "hyperliquid_clearinghouse_state",
            "blockchain": "hyperliquid",
            "primary_entity": entity,
            "primary_address": previous.get("address", ""),
            "counterparty_entity": "Hyperliquid",
            "asset_symbol": coin,
            "amount_native": previous.get("szi_abs", ""),
            "amount_usd": f"{previous_value:.2f}",
            "metric_type": f"hyperliquid_position_{side}",
            "metric_value": "0.00",
            "metric_change_pct": "-1.000000",
            "event_type_l1": "whale_position",
            "event_type_l2": "hyperliquid_perp_position_closed",
            "risk_category": "perp_position",
            "confidence": "medium",
            "relevance_score": "0.78",
            "threshold_rule": f"previous_position_value_usd={previous_value:.2f};change_type=position_closed",
            "dedupe_key": make_dedupe_key("hyperliquid_position_closed", user, coin, side, observed_iso[:13]),
            "needs_model_review": "true",
            "model_review_reason": "large_hyperliquid_position_closed",
            "publish_route": "review",
            "status": "ok",
            "raw_json": json_dumps({"change_type": "position_closed", "previous": previous}),
        }
    )
    return alert


def main() -> int:
    args = parse_args()
    watchlist_path = normalize_path(args.watchlist)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    state_path = normalize_path(args.state)
    history_path = normalize_path(args.history)
    watch_rows = [row for row in read_csv_rows(watchlist_path) if is_enabled(row)][: args.limit_addresses]

    if not watch_rows and truthy(args.sample_if_empty):
        rows = sample_alerts()
        write_csv_rows(output_path, rows, ALERT_COLUMNS)
        write_summary(
            summary_path,
            {
                "watcher": "hyperliquid_positions",
                "mode": "sample_empty_watchlist",
                "watchlist_rows": 0,
                "queried_accounts": 0,
                "raw_position_rows": 0,
                "alert_rows": len(rows),
                "skipped_rows": 0,
                "status": "sample",
                "message": "empty watchlist; wrote sample alerts for pipeline validation",
            },
        )
        print(f"empty watchlist; wrote sample alerts to {output_path}")
        return 0

    observed_iso = dt_to_utc_iso(now_utc())
    alerts = []
    previous_state = load_state(state_path)
    next_state = dict(previous_state)
    seen_keys = set()
    raw_count = 0
    skipped_count = 0
    unchanged_count = 0
    changed_count = 0
    skip_reasons: dict[str, int] = {}
    queried_users: set[str] = set()

    for index, account in enumerate(watch_rows, start=1):
        user = address(account.get("address"))
        print(f"[{index}/{len(watch_rows)}] query hyperliquid={account.get('label')} address={user}")
        try:
            state = post_hyperliquid_state(user)
        except Exception as exc:
            skipped_count += 1
            skip_reasons["request_failed"] = skip_reasons.get("request_failed", 0) + 1
            print(f"  request_failed={exc}")
            continue
        queried_users.add(user)

        positions = state.get("assetPositions", [])
        if not isinstance(positions, list):
            positions = []
        for position_row in positions:
            raw_count += 1
            threshold = safe_float(account.get("alert_threshold_usd"), 10_000_000)
            current_state = state_row(position_row, account, observed_iso, threshold, args.near_liquidation_pct)
            if not current_state:
                skipped_count += 1
                skip_reasons["empty_position"] = skip_reasons.get("empty_position", 0) + 1
                continue
            key = current_state["position_key"]
            seen_keys.add(key)
            previous = previous_state.get(key)
            change_type, delta_usd, change_pct, should_alert = classify_change(
                current_state,
                previous,
                threshold,
                args.min_change_pct,
                args.min_change_usd,
                truthy(args.alert_first_seen),
            )
            next_state[key] = current_state
            if not should_alert and truthy(args.alert_snapshot) and safe_float(current_state.get("position_value_usd")) >= threshold:
                change_type = "position_snapshot"
                delta_usd = 0.0
                change_pct = 0.0
                should_alert = True
            if not should_alert:
                unchanged_count += 1
                skipped_count += 1
                skip_reasons[change_type] = skip_reasons.get(change_type, 0) + 1
                continue
            changed_count += 1
            alert, reason = build_alert(position_row, account, observed_iso, change_type, delta_usd, change_pct)
            if reason:
                skipped_count += 1
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                continue
            if alert:
                alerts.append(alert)
                print(
                    f"  alert {alert['asset_symbol']} {alert['metric_type']} "
                    f"{compact_number(safe_float(alert['amount_usd']))}"
                )

    if truthy(args.alert_closed):
        for key, previous in previous_state.items():
            if key in seen_keys:
                continue
            if address(previous.get("address")) not in queried_users:
                continue
            if str(previous.get("above_threshold", "")).strip().lower() != "true":
                continue
            alert = build_closed_alert(previous, observed_iso)
            alerts.append(alert)
            changed_count += 1
            if key in next_state:
                del next_state[key]

    if not args.dry_run:
        write_csv_rows(output_path, alerts, ALERT_COLUMNS)
        write_csv_rows(state_path, list(next_state.values()), STATE_COLUMNS)
        append_csv_rows(history_path, list(next_state.values()), STATE_COLUMNS)
    top_skip_reason = max(skip_reasons, key=skip_reasons.get) if skip_reasons else ""
    write_summary(
        summary_path,
        {
            "watcher": "hyperliquid_positions",
            "mode": "live",
            "watchlist_rows": len(watch_rows),
            "queried_accounts": len(watch_rows),
            "raw_position_rows": raw_count,
            "alert_rows": len(alerts),
            "skipped_rows": skipped_count,
            "changed_position_rows": changed_count,
            "unchanged_position_rows": unchanged_count,
            "state_rows": len(next_state),
            "min_change_pct": args.min_change_pct,
            "min_change_usd": args.min_change_usd,
            "alert_first_seen": str(truthy(args.alert_first_seen)).lower(),
            "top_skip_reason": top_skip_reason,
            "top_skip_count": skip_reasons.get(top_skip_reason, 0) if top_skip_reason else 0,
            "status": "pass",
            "message": "ok",
        },
    )
    print(f"alert_rows={len(alerts)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
