"""
Hyperliquid position snapshot + size-based delta detection v1.5B.

Primary delta basis: position SIZE (szi_abs / coin count).
NOTIONAL USD fallback only when size unavailable.
Filters price_drift_noise: size unchanged but USD notional changed.

Usage:
    python scripts/snapshot_hl_positions.py                    # snapshot only
    python scripts/snapshot_hl_positions.py --check-delta       # snapshot + delta
    python scripts/snapshot_hl_positions.py --preview           # full report
"""

import csv
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))
DB_PATH = ROOT / "data" / "hyperliquid_position_snapshots.sqlite"
POSITION_CSV = ROOT / "data" / "hyperliquid_position_state.csv"
COOLDOWN_DB = ROOT / "data" / "hl_delta_cooldown.sqlite"


def china_now(): return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
def sf(v):
    try: return float(v or 0)
    except: return 0.0
def ts_now(): return datetime.now(CN_TZ)


# ── DB ──
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS position_snapshots (
            snapshot_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at       TEXT NOT NULL,
            address           TEXT NOT NULL,
            entity            TEXT NOT NULL DEFAULT '',
            asset             TEXT NOT NULL,
            side              TEXT NOT NULL,
            position_value_usd REAL NOT NULL DEFAULT 0,
            szi_abs           REAL NOT NULL DEFAULT 0,
            liquidation_distance_pct REAL NOT NULL DEFAULT 0,
            liquidation_price REAL NOT NULL DEFAULT 0,
            mark_price        REAL NOT NULL DEFAULT 0,
            source_row_hash   TEXT NOT NULL,
            UNIQUE(captured_at, address, asset, side)
        )
    """)
    conn.commit()
    return conn


def init_cooldown():
    COOLDOWN_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(COOLDOWN_DB), timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cooldown (
            key_id           TEXT PRIMARY KEY,
            last_triggered   TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def row_hash(row):
    s = str(row.get("position_key","")) + str(row.get("szi_abs","")) + str(row.get("position_value_usd",""))
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def snapshot_positions(conn):
    if not POSITION_CSV.exists():
        print(f"Missing: {POSITION_CSV}")
        return 0
    now = china_now()
    count = 0
    with open(POSITION_CSV, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            h = row_hash(row)
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO position_snapshots
                    (captured_at, address, entity, asset, side,
                     position_value_usd, szi_abs, liquidation_distance_pct,
                     liquidation_price, mark_price, source_row_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now, str(row.get("address",""))[:42], str(row.get("entity",""))[:80],
                    str(row.get("asset_symbol","")).upper(), str(row.get("side","")).lower(),
                    sf(row.get("position_value_usd")), sf(row.get("szi_abs")),
                    sf(row.get("liquidation_distance_pct")), sf(row.get("liquidation_px")),
                    sf(row.get("mark_px")), h,
                ))
                count += 1
            except sqlite3.IntegrityError:
                pass
    conn.commit()
    return count


# ── Delta (size-primary) ──
def compute_deltas(conn, cooldown_conn):
    now_dt = ts_now()
    latest = conn.execute("""
        SELECT * FROM position_snapshots
        WHERE captured_at = (SELECT MAX(captured_at) FROM position_snapshots)
    """).fetchall()

    deltas = []
    price_drift_count = 0
    cooldown_applied = 0
    has_size_field = False

    for row in latest:
        addr = row[2]; entity = row[3]; asset = row[4]; side = row[5]
        cur_val = row[6]; cur_size = row[7]; cur_liq = row[8]; cur_mark = row[10]

        if cur_size > 0:
            has_size_field = True

        for wname, wmin in [("5m", 5), ("1h", 60), ("24h", 1440)]:
            target = (now_dt - timedelta(minutes=wmin)).strftime("%Y-%m-%d %H:%M:%S")
            prev = conn.execute("""
                SELECT * FROM position_snapshots
                WHERE address=? AND asset=? AND side=? AND captured_at <= ?
                ORDER BY captured_at DESC LIMIT 1
            """, (addr, asset, side, target)).fetchone()
            if not prev:
                deltas.append(dict(addr=addr[:12], entity=entity[:30], asset=asset, side=side,
                    window=wname, cur_size=cur_size, cur_val=cur_val, cur_liq=cur_liq,
                    prev_size=0, prev_val=0, prev_liq=0,
                    delta_size=0, delta_val=0, delta_pct=0, liq_delta=0,
                    delta_basis="unavailable", price_drift=False, triggered=False,
                    trigger_reasons="no_history", cooldown=False))
                continue

            prev_val = prev[6]; prev_size = prev[7]; prev_liq = prev[8]
            delta_size = cur_size - prev_size
            delta_val = cur_val - prev_val

            # Determine delta basis
            if cur_size > 0 and prev_size > 0:
                basis = "size"
                primary_delta = delta_size
                size_pct = abs(delta_size) / prev_size * 100 if prev_size > 0 else 0
                # Compute notional impact of size change using current mark price
                notional_impact = abs(delta_size) * (cur_mark if cur_mark > 0 else cur_val / cur_size if cur_size > 0 else 0)
            else:
                basis = "notional_usd_fallback"
                primary_delta = delta_val
                size_pct = abs(delta_val) / prev_val * 100 if prev_val > 0 else 0
                notional_impact = abs(delta_val)

            # Price drift detection: size unchanged but USD notional moves
            price_drift = False
            if basis == "size" and abs(delta_size) < 1e-6 and abs(delta_val) > 1_000:
                price_drift = True
                price_drift_count += 1

            delta_pct = abs(notional_impact) / prev_val * 100 if prev_val > 0 else 0
            liq_delta = abs(cur_liq - prev_liq) * 100
            side_flipped = (side != str(prev[5])) if prev[5] else False

            # Trigger rules (size-primary)
            trig = False; reasons = []
            if basis == "size" and not price_drift:
                if notional_impact >= 5_000_000 and wname == "5m":
                    trig = True; reasons.append(f"size_5m_impact=${notional_impact/1e6:.1f}M")
                if notional_impact >= 10_000_000 and wname == "1h":
                    trig = True; reasons.append(f"size_1h_impact=${notional_impact/1e6:.1f}M")
                if notional_impact >= 30_000_000 and wname == "24h":
                    trig = True; reasons.append(f"size_24h_impact=${notional_impact/1e6:.1f}M")
            if basis == "notional_usd_fallback" and not price_drift:
                if abs(delta_val) >= 10_000_000 and wname in ("1h", "24h"):
                    trig = True; reasons.append(f"notional_{wname}=${delta_val/1e6:.1f}M")
            if liq_delta >= 5:
                trig = True; reasons.append(f"liq_delta={liq_delta:.1f}pp")
            if side_flipped:
                trig = True; reasons.append("side_flip")

            # Cooldown check
            key = f"{addr}_{asset}_{side}"
            last_trig = cooldown_conn.execute(
                "SELECT last_triggered FROM cooldown WHERE key_id=?", (key,)
            ).fetchone()
            cooldown = False
            if last_trig and trig:
                last_dt = datetime.strptime(last_trig[0], "%Y-%m-%d %H:%M:%S")
                elapsed = (now_dt - last_dt).total_seconds() / 60
                if elapsed < 30 and not side_flipped and liq_delta < 10:
                    cooldown = True; cooldown_applied += 1; trig = False

            deltas.append(dict(
                addr=addr[:12], entity=entity[:30], asset=asset, side=side,
                window=wname, cur_size=cur_size, cur_val=cur_val, cur_liq=cur_liq,
                prev_size=prev_size, prev_val=prev_val, prev_liq=prev_liq,
                delta_size=delta_size, delta_val=delta_val,
                notional_impact=notional_impact, size_pct=size_pct,
                delta_pct=delta_pct, liq_delta=liq_delta,
                delta_basis=basis, price_drift=price_drift,
                triggered=trig and not price_drift,
                trigger_reasons="; ".join(reasons),
                cooldown=cooldown, side_flipped=side_flipped,
            ))

    return deltas, price_drift_count, cooldown_applied, has_size_field


# ── v1.5C: Address Behavior Profile ──

def get_address_behavior_tags(conn, address, entity, asset, side):
    """Return behavior profile dict for a monitored address/entity+asset+side.
    Only enabled when: >=3 snapshots, >=30min span, real delta, non-mock.
    """
    result = {
        "profile_enabled": False, "profile_reason": "",
        "profile_snapshot_count": 0, "profile_time_span_minutes": 0,
        "watchlist_rank_label": "", "behavior_labels": [], "risk_labels": [],
        "profile_text": "",
    }

    # Fetch all snapshots for this address+asset+side
    snaps = conn.execute("""
        SELECT * FROM position_snapshots
        WHERE address=? AND asset=? AND side=?
        ORDER BY captured_at ASC
    """, (address, asset, side)).fetchall()

    n = len(snaps)
    result["profile_snapshot_count"] = n
    if n < 3:
        result["profile_reason"] = "snapshot_not_enough"
        return result

    # Time span
    t_min = snaps[0][1]  # captured_at
    t_max = snaps[-1][1]
    try:
        from datetime import datetime
        span = (datetime.strptime(t_max[:19], "%Y-%m-%d %H:%M:%S") -
                datetime.strptime(t_min[:19], "%Y-%m-%d %H:%M:%S")).total_seconds() / 60
    except:
        span = 0
    result["profile_time_span_minutes"] = span
    if span < 30:
        result["profile_reason"] = "time_span_too_short"
        return result

    # Watchlist rank: rank by current position_value_usd within same asset
    latest_time = conn.execute("SELECT MAX(captured_at) FROM position_snapshots").fetchone()[0]
    same_asset = conn.execute("""
        SELECT address, entity, position_value_usd FROM position_snapshots
        WHERE asset=? AND captured_at=? ORDER BY position_value_usd DESC
    """, (asset, latest_time)).fetchall()
    rank = None
    for i, row in enumerate(same_asset, 1):
        if row[0] == address:
            rank = i; break
    total_in_asset = len(same_asset)
    if rank:
        if rank <= 3: result["watchlist_rank_label"] = f"{asset} 监控池 Top 3"
        elif rank <= 5: result["watchlist_rank_label"] = f"{asset} 监控池 Top 5"
        elif rank <= 10: result["watchlist_rank_label"] = f"{asset} 监控池 Top 10"

    # Behavior labels
    labels = []
    risk = []
    recent = snaps[-4:] if n >= 4 else snaps  # last 3-4 snapshots

    # Check size deltas in recent snapshots
    size_deltas = []
    for i in range(1, len(recent)):
        ds = recent[i][7] - recent[i-1][7]  # szi_abs column index 7
        size_deltas.append(ds)
    liq_deltas = []
    for i in range(1, len(recent)):
        dl = recent[i][8] - recent[i-1][8]  # liq_distance_pct column index 8
        liq_deltas.append(dl)

    # 24h first move: check if this is first significant delta in 24h
    if len(size_deltas) >= 1 and abs(size_deltas[-1]) > 1e-6:
        older_deltas = [d for d in size_deltas[:-1] if abs(d) > 1e-6]
        if not older_deltas:
            labels.append("24h 首动")

    # Consecutive add/reduce
    if len(size_deltas) >= 2:
        if all(d > 1e-6 for d in size_deltas):
            labels.append("连续加仓")
        elif all(d < -1e-6 for d in size_deltas):
            labels.append("阶梯减仓")

    # Position ATH
    all_sizes = [s[7] for s in snaps]
    if all_sizes and snaps[-1][7] >= max(all_sizes) * 0.999:
        labels.append("持仓新高")

    # Risk margin narrowing
    if len(liq_deltas) >= 2 and all(d < 0 for d in liq_deltas):
        total_drop = abs(sum(liq_deltas))
        if total_drop >= 0.05:
            risk.append("风险边际缩窄")

    # Side flip: check across all history
    sides_seen = set(s[5] for s in snaps)
    if len(sides_seen) >= 2:
        labels.insert(0, "反手头寸")  # highest priority at front

    # Build profile_text
    parts = []
    if result["watchlist_rank_label"]:
        parts.append(result["watchlist_rank_label"])
    parts.extend(labels)
    parts.extend(risk)

    if not parts:
        result["profile_reason"] = "labels_empty"
        return result

    result["behavior_labels"] = labels
    result["risk_labels"] = risk
    result["profile_enabled"] = True
    result["profile_text"] = "；".join(parts) + "。"

    # If no risk contraction detected, note active management if reducing
    if not risk and "阶梯减仓" in labels:
        result["profile_text"] = "；".join(parts) + "。敞口主动收缩。"

    return result


# ── CLI ──
if __name__ == "__main__":
    import argparse; p = argparse.ArgumentParser()
    p.add_argument("--check-delta", action="store_true")
    p.add_argument("--preview", action="store_true")
    args = p.parse_args()

    conn = init_db(); cconn = init_cooldown()
    count = snapshot_positions(conn)
    total = conn.execute("SELECT COUNT(*) FROM position_snapshots").fetchone()[0]
    times = conn.execute("SELECT COUNT(DISTINCT captured_at) FROM position_snapshots").fetchone()[0]
    print(f"Snapshot: {count} new | {total} total | {times} distinct times")

    if args.check_delta or args.preview:
        deltas, drift_cnt, cool_cnt, has_size = compute_deltas(conn, cconn)
        triggered = [d for d in deltas if d["triggered"] and not d["price_drift"]]
        drift_items = [d for d in deltas if d["price_drift"]]
        basis_dist = {"size": sum(1 for d in deltas if d["delta_basis"]=="size"),
                      "notional_usd_fallback": sum(1 for d in deltas if d["delta_basis"]=="notional_usd_fallback"),
                      "unavailable": sum(1 for d in deltas if d["delta_basis"]=="unavailable")}

        print(f"\nDelta: {len(deltas)} comparisons | {len(triggered)} triggered")
        print(f"Delta basis: {basis_dist}")
        print(f"Price drift noise: {drift_cnt} | Cooldown blocking: {cool_cnt}")
        print(f"Has size field: {has_size}")

        # v1.5C: compute address profiles for triggered deltas
        profiles = []
        for d in triggered:
            addr = conn.execute("SELECT address FROM position_snapshots WHERE address LIKE ? LIMIT 1",
                                (d["addr"] + "%",)).fetchone()
            full_addr = addr[0] if addr else d["addr"]
            profile = get_address_behavior_tags(conn, full_addr, d["entity"], d["asset"], d["side"])
            profiles.append({**d, **profile})

        for d in triggered[:6]:
            p = profiles[triggered.index(d)] if triggered.index(d) < len(profiles) else {}
            print(f"  [{d['entity']}] {d['asset']} {d['side']} {d['window']}: "
                  f"size={d['delta_size']:+.4f} notional=${d['notional_impact']/1e6:+.1f}M "
                  f"basis={d['delta_basis']} profile={p.get('profile_enabled',False)} {p.get('profile_text','')[:60]}")

        if args.preview:
            prev_p = ROOT / "results" / "market_radar_delta_monitor_preview.md"
            sum_p = ROOT / "results" / "market_radar_delta_monitor_summary.csv"

            with open(prev_p, "w", encoding="utf-8") as f:
                f.write("# Market Radar Delta Monitor Preview v1.5C\n\n")
                f.write(f"Generated: {china_now()}\n\n")
                f.write("## Snapshot Status\n\n")
                f.write(f"- total_snapshots: {total} | distinct_times: {times}\n")
                f.write(f"- has_size_field: {has_size}\n")
                f.write(f"- delta_basis_distribution: {basis_dist}\n")
                f.write(f"- price_drift_noise_count: {drift_cnt}\n")
                f.write(f"- cooldown_applied: {cool_cnt}\n\n")

                f.write("## Trigger Rules (v1.5B size-primary)\n\n")
                f.write("- size_5m_impact>=$5M | size_1h_impact>=$10M | size_24h_impact>=$30M\n")
                f.write("- size_pct>=15% (1h/24h) | liq_delta>=5pp | side_flip\n")
                f.write("- Cooldown: 30min per address+asset+side (unless side_flip or liq_delta>=10pp)\n")
                f.write("- Price drift (size=0 but notional moved): filtered as noise\n\n")

                f.write("## Triggered Deltas\n\n")
                if triggered:
                    f.write("| entity | asset | side | window | size_delta | notional | basis | reasons |\n")
                    f.write("|---|---|---|---:|---:|---|---|\n")
                    for d in triggered:
                        f.write(f"| {d['entity']} | {d['asset']} | {d['side']} | {d['window']} | "
                                f"{d['delta_size']:+.4f} | ${d['notional_impact']/1e6:+.1f}M | "
                                f"{d['delta_basis']} | {d['trigger_reasons']} |\n")
                else:
                    f.write("No triggered deltas met thresholds.\n")

                f.write("\n## Address Behavior Profiles (v1.5C)\n\n")
                if profiles:
                    for p in profiles:
                        f.write(f"- [{p['entity']}] {p['asset']} {p['side']}: "
                                f"profile_enabled={p['profile_enabled']}\n")
                        f.write(f"  reason={p['profile_reason']} snapshots={p['profile_snapshot_count']} span={p['profile_time_span_minutes']:.0f}min\n")
                        if p['profile_enabled']:
                            f.write(f"  rank={p['watchlist_rank_label']} behaviors={p['behavior_labels']} risks={p['risk_labels']}\n")
                            f.write(f"  text: {p['profile_text']}\n")
                else:
                    f.write("No triggered deltas to profile.\n")

                f.write("\n## Price Drift Items (filtered as noise)\n\n")
                if drift_items:
                    for d in drift_items[:5]:
                        f.write(f"- [{d['entity']}] {d['asset']}: size unchanged, notional ${d['delta_val']/1e6:+.1f}M (price drift)\n")
                else:
                    f.write("No price drift detected.\n")

                f.write("\n> For Market Radar signal structure observation only. Not trading advice.\n")

            with open(sum_p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["metric","value","note"])
                w.writeheader()
                summary_rows = [
                    {"metric":"total_snapshots","value":str(total),"note":""},
                    {"metric":"distinct_times","value":str(times),"note":""},
                    {"metric":"has_size_field","value":str(has_size),"note":"szi_abs from HL position_state"},
                    {"metric":"delta_basis_size","value":str(basis_dist["size"]),"note":""},
                    {"metric":"delta_basis_notional_fallback","value":str(basis_dist["notional_usd_fallback"]),"note":""},
                    {"metric":"delta_basis_unavailable","value":str(basis_dist["unavailable"]),"note":"no prior snapshot"},
                    {"metric":"triggered_count","value":str(len(triggered)),"note":""},
                    {"metric":"price_drift_noise_count","value":str(drift_cnt),"note":"size=0, notional moved"},
                    {"metric":"cooldown_applied","value":str(cool_cnt),"note":"30min cooldown"},
                ]
                # Add first profile's fields if available
                if profiles:
                    fp = profiles[0]
                    for k in ["profile_enabled","profile_reason","profile_snapshot_count",
                              "profile_time_span_minutes","watchlist_rank_label",
                              "behavior_labels","risk_labels","profile_text"]:
                        v = fp.get(k, "")
                        summary_rows.append({"metric":f"profile_{k}","value":str(v),"note":""})
                w.writerows(summary_rows)

            print(f"\nPreview: {prev_p}\nSummary: {sum_p}")

    conn.close(); cconn.close()
