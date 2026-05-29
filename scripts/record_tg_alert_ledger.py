import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


LEDGER_COLUMNS = [
    "alert_id",
    "created_at_china",
    "published_at_china",
    "published_at_utc",
    "board_id",
    "board_label",
    "telegram_chat_id",
    "telegram_message_id",
    "send_status",
    "alert_status",
    "source_type",
    "event_type",
    "event_subtype",
    "asset_symbol",
    "repeat_group",
    "item_key",
    "direction_observation",
    "confidence_bucket",
    "magnitude_usd",
    "alert_text",
    "raw_payload_json",
]


SUMMARY_COLUMNS = [
    "status",
    "created_at_china",
    "board_id",
    "telegram_message_id",
    "send_status",
    "ledger_rows_added",
    "ledger_output",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record structured TG radar items into an alert outcome ledger.")
    parser.add_argument("--board-id", default="")
    parser.add_argument("--board-label", default="")
    parser.add_argument("--telegram-chat-id", default="")
    parser.add_argument("--telegram-message-id", default="")
    parser.add_argument("--send-status", default="sent")
    parser.add_argument("--published-at-china", default="")
    parser.add_argument("--item-state", default=str(ROOT / "data" / "tg_radar_item_state.csv"))
    parser.add_argument("--ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_alert_ledger_record_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)


def china_stamp(dt: datetime | None = None) -> str:
    return (dt or china_now()).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def parse_china_stamp(value: str) -> datetime | None:
    raw = str(value or "").replace("UTC+8", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone(timedelta(hours=8)))
        except ValueError:
            continue
    return None


def to_utc_iso(china_value: str) -> str:
    dt = parse_china_stamp(china_value)
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def infer_subtype(source_type: str, repeat_group: str, text: str) -> str:
    source = str(source_type or "").strip()
    group = str(repeat_group or "").strip()
    raw = str(text or "")
    if source == "hyperliquid":
        if group == "position_change":
            return "whale_position_size_change"
        if "清算" in raw or "爆仓" in raw:
            return "whale_position_near_liquidation"
        return "whale_position_static_large"
    if source == "token_unlock":
        if "团队" in raw or "贡献" in raw:
            return "token_unlock_team_large"
        if "投资" in raw:
            return "token_unlock_investor_large"
        return "token_unlock_large"
    if source == "cex_netflow":
        if "流入" in raw:
            return "cex_netflow_inflow_spike"
        if "流出" in raw:
            return "cex_netflow_outflow_spike"
        return "cex_netflow_spike"
    if source == "stablecoin_flow":
        if "增发" in raw:
            return "stablecoin_mint"
        if "流入" in raw or "转入" in raw:
            return "stablecoin_cex_inflow"
        return "stablecoin_large_flow"
    if source == "long_short":
        return "long_short_crowding_extreme"
    return source or "unknown"


def infer_event_type(source_type: str) -> str:
    mapping = {
        "hyperliquid": "whale_position",
        "token_unlock": "token_unlock",
        "cex_netflow": "cex_netflow",
        "stablecoin_flow": "stablecoin_flow",
        "long_short": "market_structure",
    }
    return mapping.get(str(source_type or "").strip(), str(source_type or "other").strip() or "other")


def infer_direction(source_type: str, repeat_group: str, text: str) -> str:
    raw = str(text or "")
    source = str(source_type or "")
    if source == "token_unlock":
        return "risk_observation"
    if "空头" in raw:
        return "short_position_observation"
    if "多头" in raw:
        return "long_position_observation"
    if "流入" in raw or "转入" in raw:
        return "inflow_observation"
    if "流出" in raw or "转出" in raw:
        return "outflow_observation"
    if repeat_group == "indicator":
        return "crowding_observation"
    return "observe"


def alert_id_for(board_id: str, item_key: str, text: str) -> str:
    raw = f"{board_id}|{item_key}|{text}"
    return "tg_" + hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


def main() -> int:
    args = parse_args()
    now = china_stamp()
    summary_path = normalize_path(args.summary)
    try:
        item_rows = read_rows(normalize_path(args.item_state))
        ledger_path = normalize_path(args.ledger)
        ledger_rows = read_rows(ledger_path)
        existing_ids = {str(row.get("alert_id") or "") for row in ledger_rows}
        board_id = str(args.board_id or "").strip()
        if not board_id:
            raise RuntimeError("board_id is required")

        published_at_china = args.published_at_china or now
        rows_for_board = [row for row in item_rows if str(row.get("board_id") or "").strip() == board_id]
        new_rows = []
        for item in rows_for_board:
            text = str(item.get("text") or "").strip()
            item_key = str(item.get("item_key") or "").strip()
            alert_id = alert_id_for(board_id, item_key, text)
            if alert_id in existing_ids:
                continue
            source_type = str(item.get("source_type") or "").strip()
            repeat_group = str(item.get("repeat_group") or "").strip()
            row = {
                "alert_id": alert_id,
                "created_at_china": now,
                "published_at_china": published_at_china,
                "published_at_utc": to_utc_iso(published_at_china),
                "board_id": board_id,
                "board_label": args.board_label,
                "telegram_chat_id": args.telegram_chat_id,
                "telegram_message_id": args.telegram_message_id,
                "send_status": args.send_status,
                "alert_status": "published" if args.send_status == "sent" else args.send_status,
                "source_type": source_type,
                "event_type": infer_event_type(source_type),
                "event_subtype": infer_subtype(source_type, repeat_group, text),
                "asset_symbol": str(item.get("asset") or "").upper(),
                "repeat_group": repeat_group,
                "item_key": item_key,
                "direction_observation": infer_direction(source_type, repeat_group, text),
                "confidence_bucket": "medium",
                "magnitude_usd": "",
                "alert_text": text,
                "raw_payload_json": json.dumps(item, ensure_ascii=False),
            }
            new_rows.append(row)
            existing_ids.add(alert_id)

        ledger_rows.extend(new_rows)
        write_rows(ledger_path, ledger_rows, LEDGER_COLUMNS)
        summary = {
            "status": "pass",
            "created_at_china": now,
            "board_id": board_id,
            "telegram_message_id": args.telegram_message_id,
            "send_status": args.send_status,
            "ledger_rows_added": str(len(new_rows)),
            "ledger_output": str(ledger_path),
            "error": "",
        }
        write_rows(summary_path, [summary], SUMMARY_COLUMNS)
        print(f"recorded {len(new_rows)} TG alert ledger rows")
        return 0
    except Exception as exc:
        summary = {
            "status": "fail",
            "created_at_china": now,
            "board_id": args.board_id,
            "telegram_message_id": args.telegram_message_id,
            "send_status": args.send_status,
            "ledger_rows_added": "0",
            "ledger_output": str(normalize_path(args.ledger)),
            "error": str(exc)[:300],
        }
        write_rows(summary_path, [summary], SUMMARY_COLUMNS)
        print(f"failed to record TG alert ledger: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
