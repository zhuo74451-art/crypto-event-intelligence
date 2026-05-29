import argparse
import csv
import io
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest first-party or security-provider alert feeds into local CSV.")
    parser.add_argument("--source", choices=["etherscan-labels"], default="etherscan-labels")
    parser.add_argument("--label", default="phish-hack")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--raw-output", default=str(ROOT / "data" / "security_events" / "etherscan_phish_hack_labels.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "security_events" / "security_events_normalized.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_security_alert_ingest_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def utc_iso_from_timestamp(value: str) -> str:
    try:
        ts = int(float(str(value or "").strip()))
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""


def fetch_etherscan_labels(label: str) -> list[dict]:
    api_key = os.environ.get("ETHERSCAN_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ETHERSCAN_API_KEY missing")
    resp = requests.get(
        "https://api-metadata.etherscan.io/v1/api.ashx",
        params={
            "module": "nametag",
            "action": "exportaddresstags",
            "label": label,
            "format": "csv",
            "apikey": api_key,
        },
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"etherscan_http_{resp.status_code}")
    text = resp.text.lstrip("\ufeff")
    if "NOTOK" in text[:200].upper() or "ERROR" in text[:200].upper():
        raise RuntimeError(text[:180].replace("\n", " "))
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    return list(reader)


def normalize_etherscan(rows: list[dict], limit: int) -> list[dict]:
    normalized = []
    sorted_rows = sorted(rows, key=lambda row: int(float(row.get("lastupdatedtimestamp") or 0)), reverse=True)
    for idx, row in enumerate(sorted_rows[:limit], 1):
        address = str(row.get("address") or "").strip()
        label_slug = str(row.get("labels_slug") or "").strip()
        event_time = utc_iso_from_timestamp(str(row.get("lastupdatedtimestamp") or ""))
        normalized.append(
            {
                "security_event_id": f"etherscan_{label_slug}_{idx:05d}",
                "event_time_utc": event_time,
                "source": "etherscan_metadata",
                "source_tier": "onchain_verified",
                "alert_type": "address_label",
                "exploit_type": label_slug or "phish-hack",
                "affected_protocol": "",
                "loss_amount_usd": "",
                "attacker_address": address,
                "tx_hash": "",
                "verification_url": f"https://etherscan.io/address/{address}" if address else "",
                "raw_label": row.get("labels", ""),
                "nametag": row.get("nametag", ""),
                "notes": " ".join(str(row.get(key) or "").strip() for key in ["shortdescription", "notes_1", "notes_2"] if row.get(key)),
                "publishable_now": "false",
                "publish_block_reason": "address_risk_label_not_active_exploit",
            }
        )
    return normalized


def main() -> int:
    args = parse_args()
    status = "pass"
    error = ""
    raw_rows: list[dict] = []
    normalized: list[dict] = []
    try:
        if args.source == "etherscan-labels":
            raw_rows = fetch_etherscan_labels(args.label)
            normalized = normalize_etherscan(raw_rows, args.limit)
            if raw_rows:
                write_rows(normalize_path(args.raw_output), raw_rows[: args.limit], list(raw_rows[0].keys()))
            write_rows(normalize_path(args.output), normalized, list(normalized[0].keys()) if normalized else ["security_event_id"])
    except Exception as exc:
        status = "warning"
        error = str(exc)
        write_rows(normalize_path(args.output), [], ["security_event_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "source": args.source,
        "label": args.label,
        "raw_rows": len(raw_rows),
        "normalized_rows": len(normalized),
        "publishable_now_rows": sum(1 for row in normalized if row.get("publishable_now") == "true"),
        "status": status,
        "error": error,
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"source={args.source}")
    print(f"normalized_rows={len(normalized)}")
    print(f"status={status}")
    if error:
        print(f"error={error[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
