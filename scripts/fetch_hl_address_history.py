"""
Hyperliquid Address History Fetcher v1.6 MVP.

Fetches last 7 days of fills, ledger updates, funding for monitored addresses.
Uses public Hyperliquid info API (no API key required).

Usage:
    python scripts/fetch_hl_address_history.py                    # all addresses
    python scripts/fetch_hl_address_history.py --limit 3          # first 3 only
"""

import csv
import json
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))
INFO_URL = "https://api.hyperliquid.xyz/info"
DB_PATH = ROOT / "data" / "hyperliquid_address_history.sqlite"
POSITION_CSV = ROOT / "data" / "hyperliquid_position_state.csv"


def china_now(): return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
def sf(v):
    try: return float(v or 0)
    except: return 0.0


def hl_post(payload: dict, timeout: int = 20) -> dict | None:
    """POST to Hyperliquid info API. Returns parsed JSON or None on failure."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(INFO_URL, data=data, method="POST",
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  HL API error: {str(e)[:120]}")
        return None


# ── DB ──
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fetches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL, asset TEXT, fetched_at TEXT NOT NULL,
            window_start_ts INTEGER, window_end_ts INTEGER,
            fills_count INTEGER DEFAULT 0, ledger_count INTEGER DEFAULT 0,
            funding_count INTEGER DEFAULT 0, state_status TEXT DEFAULT '',
            error TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL, asset TEXT, fetched_at TEXT NOT NULL,
            fill_time_ts INTEGER, side TEXT, px REAL, sz REAL,
            hash_id TEXT, raw_json TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ledger_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL, fetched_at TEXT NOT NULL,
            update_time_ts INTEGER, delta_type TEXT, usdc REAL,
            tx_hash TEXT, raw_json TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS funding_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL, fetched_at TEXT NOT NULL,
            event_time_ts INTEGER, asset TEXT, funding_rate REAL,
            premium REAL, raw_json TEXT
        )
    """)
    conn.commit()
    return conn


# ── Fetch functions ──
def fetch_fills(address: str, since_ms: int, until_ms: int):
    return hl_post({"type": "userFillsByTime", "user": address,
                     "startTime": since_ms, "endTime": until_ms, "aggregateByTime": True})

def fetch_ledger(address: str, since_ms: int, until_ms: int):
    return hl_post({"type": "userNonFundingLedgerUpdates", "user": address,
                     "startTime": since_ms, "endTime": until_ms})

def fetch_funding(address: str, since_ms: int, until_ms: int):
    return hl_post({"type": "userFunding", "user": address,
                     "startTime": since_ms, "endTime": until_ms})

def fetch_state(address: str):
    return hl_post({"type": "clearinghouseState", "user": address})


# ── Summary builder ──
def build_summary(conn, address, asset):
    now = china_now()
    f_count = conn.execute("SELECT COUNT(*) FROM fills WHERE address=? AND asset=?",
                           (address, asset)).fetchone()[0]
    l_count = conn.execute("SELECT COUNT(*) FROM ledger_updates WHERE address=?",
                           (address,)).fetchone()[0]
    fund_count = conn.execute("SELECT COUNT(*) FROM funding_events WHERE address=?",
                              (address,)).fetchone()[0]

    # Net size delta
    fills = conn.execute("SELECT side, sz FROM fills WHERE address=? AND asset=?",
                         (address, asset)).fetchall()
    net_delta = sum(f[1] if f[0] == "B" else -f[1] for f in fills) if fills else 0
    buy_sz = sum(f[1] for f in fills if f[0] == "B")
    sell_sz = sum(f[1] for f in fills if f[0] == "A")

    # Ledger breakdown
    withdraw_count = conn.execute(
        "SELECT COUNT(*) FROM ledger_updates WHERE address=? AND delta_type LIKE '%withdraw%'",
        (address,)).fetchone()[0]
    deposit_count = conn.execute(
        "SELECT COUNT(*) FROM ledger_updates WHERE address=? AND delta_type LIKE '%deposit%'",
        (address,)).fetchone()[0]

    # ── v1.6: 7d Net Flow (from ledger) ──
    ledger_rows = conn.execute(
        "SELECT delta_type, usdc FROM ledger_updates WHERE address=?", (address,)).fetchall()
    deposit_usd = sum(abs(r[1]) for r in ledger_rows if r[0] and "deposit" in str(r[0]).lower())
    withdraw_usd = sum(abs(r[1]) for r in ledger_rows if r[0] and "withdraw" in str(r[0]).lower())
    net_flow = deposit_usd - withdraw_usd
    if l_count > 0:
        if net_flow > 100: nf_label = "capital_inflow"
        elif net_flow < -100: nf_label = "capital_outflow"
        else: nf_label = "neutral_flow"
    else:
        nf_label = "unavailable"

    # ── v1.6: 7d Trade Bias ──
    buy_ratio = buy_sz / (buy_sz + sell_sz) if (buy_sz + sell_sz) > 0 else 0
    sell_ratio = 1 - buy_ratio
    if f_count >= 10:
        if buy_ratio >= 0.65: tb_label = "buy_execution_pressure"
        elif sell_ratio >= 0.65: tb_label = "sell_execution_pressure"
        else: tb_label = "balanced_execution"
    else:
        tb_label = "low_activity"

    # ── v1.6: 7d Funding Net ──
    fund_rows = conn.execute(
        "SELECT funding_rate FROM funding_events WHERE address=?", (address,)).fetchall()
    funding_net = sum(sf(r[0]) for r in fund_rows) if fund_rows else 0
    if fund_count >= 10:
        if funding_net > 0.001: fl_label = "funding_earned"
        elif funding_net < -0.001: fl_label = "funding_paid"
        else: fl_label = "funding_neutral"
    else:
        fl_label = "unavailable"

    # ── Quality ──
    if f_count + l_count > 0:
        quality = "good" if f_count >= 5 else "partial"
    else:
        quality = "unavailable"

    # ── Labels ──
    labels = []
    if f_count >= 10: labels.append("recent_active_trader")
    current_side_val = None
    if POSITION_CSV.exists():
        with open(POSITION_CSV, encoding="utf-8-sig", newline="") as pf:
            for pr in csv.DictReader(pf):
                if str(pr.get("address","")).strip()[:16] == address[:16]:
                    current_side_val = str(pr.get("side","")).lower()
                    break
    if current_side_val:
        cs = current_side_val
        if cs == "long" and net_delta > 0: labels.append("recent_size_building")
        elif cs == "short" and net_delta < 0: labels.append("recent_size_building")
        elif net_delta != 0: labels.append("recent_size_reducing")
    if withdraw_count > 0: labels.append("recent_withdrawal_activity")
    if f_count == 0 and l_count == 0: labels.append("quiet_address")

    # ── v1.6: Card history lines (max 3 for TG) ──
    card_lines = []
    if nf_label != "unavailable" and abs(net_flow) > 100:
        direction = "资本流入" if net_flow > 0 else "资本流出"
        card_lines.append(f"资金动向：净流入 ${net_flow/1e6:+.1f}M，{direction}")
    if tb_label not in ("unavailable", "low_activity") and f_count >= 10:
        bias_text = "买方执行压力较强" if tb_label == "buy_execution_pressure" else \
                    "卖方执行压力较强" if tb_label == "sell_execution_pressure" else "成交买卖均衡"
        card_lines.append(f"成交偏好：买方占比 {buy_ratio:.0%}，{bias_text}")
    if fl_label == "funding_paid":
        card_lines.append("Funding：过去 7d 持续支付资金费")
    elif fl_label == "funding_earned":
        card_lines.append("Funding：过去 7d 持续获得资金费")
    elif fl_label == "funding_neutral" and fund_count >= 10:
        card_lines.append("Funding：影响较弱")

    return {
        "address": address[:16], "asset": asset,
        "fills_7d": f_count, "net_size_delta": f"{net_delta:+.4f}",
        "buy_size": f"{buy_sz:.4f}", "sell_size": f"{sell_sz:.4f}",
        "buy_ratio_7d": f"{buy_ratio:.3f}", "trade_bias_label": tb_label,
        "ledger_updates": l_count,
        "deposit_usd_7d": f"{deposit_usd:.0f}",
        "withdrawal_usd_7d": f"{withdraw_usd:.0f}",
        "net_flow_usd_7d": f"{net_flow:.0f}",
        "net_flow_label": nf_label,
        "funding_events": fund_count,
        "funding_net_7d": f"{funding_net:.6f}",
        "funding_label": fl_label,
        "history_quality": quality, "labels": "; ".join(labels),
        "card_history_lines": " || ".join(card_lines[:3]),
        "fetched_at": now,
    }


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--days", type=int, default=7)
    args = p.parse_args()

    if not POSITION_CSV.exists():
        print(f"Missing: {POSITION_CSV}"); return 1

    addresses = []
    with open(POSITION_CSV, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            addr = str(row.get("address", "")).strip()
            if addr.startswith("0x"):
                addresses.append((addr, row.get("asset_symbol", "?").upper(),
                                  row.get("entity", "")[:30]))
    addresses = addresses[:args.limit]

    conn = init_db()
    until_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    since_ms = until_ms - args.days * 86400 * 1000

    print(f"Fetching history for {len(addresses)} addresses ({args.days}d window)...")

    summaries = []
    for addr, asset, entity in addresses:
        print(f"\n[{entity}] {addr[:12]}... {asset}")
        err = ""

        # Fills
        fills = fetch_fills(addr, since_ms, until_ms)
        f_count = 0
        if fills is None:
            err += "fills_api_error; "
        elif isinstance(fills, list):
            for fill in fills:
                try:
                    ft = fill.get("time", 0)
                    side = "B" if str(fill.get("side","")).upper() == "B" else "A"
                    conn.execute("INSERT OR IGNORE INTO fills (address,asset,fetched_at,fill_time_ts,side,px,sz,hash_id,raw_json) VALUES (?,?,?,?,?,?,?,?,?)",
                                 (addr, asset, china_now(), ft, side,
                                  sf(fill.get("px")), sf(fill.get("sz")),
                                  str(fill.get("hash",""))[:66], json.dumps(fill)))
                    f_count += 1
                except: pass
            conn.commit()
            print(f"  fills: {f_count}")
        else:
            err += "fills_failed; "

        # Ledger
        ledger = fetch_ledger(addr, since_ms, until_ms)
        l_count = 0
        if ledger is None:
            err += "ledger_api_error; "
        elif isinstance(ledger, list):
            for lr in ledger:
                try:
                    conn.execute("INSERT OR IGNORE INTO ledger_updates (address,fetched_at,update_time_ts,delta_type,usdc,tx_hash,raw_json) VALUES (?,?,?,?,?,?,?)",
                                 (addr, china_now(), lr.get("time", 0),
                                  str(lr.get("delta",""))[:40],
                                  sf(lr.get("usdc")),
                                  str(lr.get("hash",""))[:66], json.dumps(lr)))
                    l_count += 1
                except: pass
            conn.commit()
            print(f"  ledger: {l_count}")
        else:
            err += "ledger_failed; "

        # Funding
        funding = fetch_funding(addr, since_ms, until_ms)
        fund_c = 0
        if funding is None:
            err += "funding_api_error; "
        elif isinstance(funding, list):
            for fr in funding:
                try:
                    conn.execute("INSERT OR IGNORE INTO funding_events (address,fetched_at,event_time_ts,asset,funding_rate,premium,raw_json) VALUES (?,?,?,?,?,?,?)",
                                 (addr, china_now(), fr.get("time", 0), fr.get("coin", asset),
                                  sf(fr.get("fundingRate")), sf(fr.get("premium")), json.dumps(fr)))
                    fund_c += 1
                except: pass
            conn.commit()
            print(f"  funding: {fund_c}")
        else:
            err += "funding_failed; "

        conn.execute("INSERT INTO fetches (address,asset,fetched_at,window_start_ts,window_end_ts,fills_count,ledger_count,funding_count,error) VALUES (?,?,?,?,?,?,?,?,?)",
                     (addr, asset, china_now(), since_ms, until_ms, f_count, l_count, fund_c, err))
        conn.commit()

        summaries.append(build_summary(conn, addr, asset))
        time.sleep(0.3)  # rate limit

    conn.close()

    # Write summaries
    sum_csv = ROOT / "results" / "hl_address_history_summary.csv"
    sum_md = ROOT / "results" / "hl_address_history_preview.md"

    if summaries:
        with open(sum_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
            w.writeheader(); w.writerows(summaries)

    with open(sum_md, "w", encoding="utf-8") as f:
        f.write("# Hyperliquid Address History Preview v1.6\n\n")
        f.write(f"Generated: {china_now()} | Window: {args.days}d | Addresses: {len(addresses)}\n\n")
        f.write("| address | asset | fills | net_delta | net_flow | flow_label | buy_ratio | trade_bias | funding_label | quality |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---|---|\n")
        for s in summaries:
            f.write(f"| {s['address']} | {s['asset']} | {s['fills_7d']} | {s['net_size_delta']} | "
                    f"{s['net_flow_usd_7d']} | {s['net_flow_label']} | "
                    f"{s['buy_ratio_7d']} | {s['trade_bias_label']} | "
                    f"{s['funding_label']} | {s['history_quality']} |\n")
        f.write("\n### Card History Lines (max 3 for TG)\n\n")
        for s in summaries:
            if s.get("card_history_lines"):
                f.write(f"- **{s['address']} {s['asset']}**: {s['card_history_lines']}\n")
        f.write("\n> For Market Radar signal structure observation only. Not trading advice.\n")

    print(f"\nSummary CSV: {sum_csv}")
    print(f"Preview MD:  {sum_md}")
    for s in summaries:
        print(f"  {s['address']} {s['asset']}: fills={s['fills_7d']} "
              f"net={s['net_size_delta']} quality={s['history_quality']} [{s['labels']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
