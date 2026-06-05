"""v1.7D-3: Dynamic Address Universe builder — position leaders, movers, liquidation risk."""
import csv, json, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

def sf(v):
    try: return float(v or 0)
    except: return 0.0

def china_now(): return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── Init dynamic DB ──
db_path = ROOT / "data" / "hl_dynamic_universe.sqlite"
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(str(db_path))
conn.execute("PRAGMA journal_mode=WAL")

for tbl, cols in [
    ("position_leaderboard", "run_time TEXT, asset TEXT, side_cn TEXT, rank INTEGER, address TEXT, entity_name TEXT, position_value_usd REAL, size_coin REAL, liquidation_price REAL, liquidation_distance_pct REAL"),
    ("movers_leaderboard", "run_time TEXT, asset TEXT, address TEXT, entity_name TEXT, side_cn TEXT, delta_window TEXT, position_delta_usd REAL, size_delta_coin REAL, action_label TEXT, rank INTEGER"),
    ("liquidation_risk_leaderboard", "run_time TEXT, asset TEXT, side_cn TEXT, rank INTEGER, address TEXT, entity_name TEXT, position_value_usd REAL, liquidation_price REAL, liquidation_distance_pct REAL, risk_label TEXT"),
]:
    conn.execute(f"CREATE TABLE IF NOT EXISTS {tbl} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
conn.commit()

# ── Load position data ──
positions = []
with open(ROOT / "data" / "hyperliquid_position_state.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        s = str(r.get("side","")).lower()
        positions.append({
            "address": str(r.get("address",""))[:42],
            "entity": str(r.get("entity",""))[:30],
            "asset": str(r.get("asset_symbol","")).upper(),
            "side_cn": "多单" if s == "long" else "空单",
            "size_coin": sf(r.get("szi_abs")),
            "value_usd": sf(r.get("position_value_usd")),
            "entry_px": sf(r.get("entry_px")),
            "mark_px": sf(r.get("mark_px")),
            "pnl": sf(r.get("unrealized_pnl")),
            "liq_px": sf(r.get("liquidation_px")),
            "liq_dist": sf(r.get("liquidation_distance_pct", 0)),
        })

print(f"Positions loaded: {len(positions)}")

# ── 1. Position Leaders (by asset, by side) ──
now = china_now()
by_asset_side = {}
for p in positions:
    key = (p["asset"], p["side_cn"])
    if key not in by_asset_side: by_asset_side[key] = []
    by_asset_side[key].append(p)

for (asset, side), pos_list in by_asset_side.items():
    pos_list.sort(key=lambda p: -p["value_usd"])
    for i, p in enumerate(pos_list, 1):
        ld = p["liq_dist"] * 100 if p["liq_dist"] > 0 and p["liq_dist"] < 1 else p["liq_dist"]
        conn.execute("""INSERT INTO position_leaderboard
        (run_time, asset, side_cn, rank, address, entity_name, position_value_usd, size_coin, liquidation_price, liquidation_distance_pct)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (now, asset, side, i, p["address"][:16], str(p["entity"])[:30], p["value_usd"], p["size_coin"], p["liq_px"], ld))
    print(f"  {asset} {side}: {len(pos_list)} positions (Top: {pos_list[0]['entity'][:20]} ${pos_list[0]['value_usd']/1e6:.1f}M)")

# ── 2. Movers (from snapshots) ──
snap_db = ROOT / "data" / "hyperliquid_position_snapshots.sqlite"
if snap_db.exists():
    sc = sqlite3.connect(str(snap_db))
    times = sc.execute("SELECT DISTINCT captured_at FROM position_snapshots ORDER BY captured_at DESC LIMIT 2").fetchall()
    if len(times) >= 2:
        latest_t = times[0][0]; prev_t = times[1][0]
        latest = {r[2]+":"+r[4]: r for r in sc.execute("SELECT * FROM position_snapshots WHERE captured_at=?", (latest_t,)).fetchall()}
        prev = {r[2]+":"+r[4]: r for r in sc.execute("SELECT * FROM position_snapshots WHERE captured_at=?", (prev_t,)).fetchall()}
        movers = []
        for key, cur in latest.items():
            if key not in prev: continue
            old = prev[key]
            val_delta = cur[6] - old[6]; size_delta = cur[7] - old[7]
            entity = cur[3]; asset = cur[4]; side = cur[5]
            if abs(val_delta) < 100: continue
            action = "增仓" if size_delta > 1e-6 else "减仓" if size_delta < -1e-6 else "变动"
            addr_short = cur[2][:16] if len(str(cur[2])) > 16 else str(cur[2])
        movers.append((abs(val_delta), entity, asset, side, val_delta, size_delta, action, addr_short))
        movers.sort(key=lambda m: -m[0])
        for i, m in enumerate(movers[:10], 1):
            conn.execute("""INSERT INTO movers_leaderboard
                (run_time, asset, address, entity_name, side_cn, delta_window, position_delta_usd, size_delta_coin, action_label, rank)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (now, m[2], m[7], str(m[1])[:30], m[3], "delta", m[4], m[5], m[6], i))
        print(f"\nMovers: {len(movers)} detected")
        for m in movers[:3]:
            print(f"  {m[1][:20]} {m[2]} {m[3]}: ${m[4]/1e6:+.1f}M size={m[5]:+.4f} ({m[6]})")
    else:
        print("\nMovers: need >=2 snapshots")
    sc.close()

# ── 3. Liquidation Risk Leaders ──
liq_risks = [(p["liq_dist"], p) for p in positions if p["liq_dist"] > 0]
liq_risks.sort(key=lambda x: x[0])  # closest to liquidation first
for i, (dist, p) in enumerate(liq_risks[:10], 1):
    dist_display = dist * 100 if dist < 1 else dist
    risk = "critical" if dist_display < 5 else "high" if dist_display < 10 else "medium" if dist_display < 20 else "low"
    risk_cn = "危急" if dist_display < 5 else "高风险" if dist_display < 10 else "中等" if dist_display < 20 else "低"
    conn.execute("""INSERT INTO liquidation_risk_leaderboard
        (run_time, asset, side_cn, rank, address, entity_name, position_value_usd, liquidation_price, liquidation_distance_pct, risk_label)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (now, p["asset"], p["side_cn"], i, p["address"][:16], str(p["entity"])[:30], p["value_usd"], p["liq_px"], dist_display, risk_cn))
    print(f"  Liq risk: {p['asset']} {p['side_cn']} {p['entity'][:20]} dist={dist_display:.1f}% {risk_cn}")

# ── 4. Discover new addresses from HyperInsight ──
discovered = []
hi_path = ROOT / "data" / "benchmark" / "hyperinsight_entity_mentions.csv"
if hi_path.exists():
    with open(hi_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            addr = r.get("address","").strip()
            if addr.startswith("0x") and addr not in [d["address"] for d in discovered]:
                discovered.append({"address": addr[:42], "source_type": "hyperinsight", "source_ref": "HI_channel",
                                   "entity_name": r.get("entity_name",""), "asset_hint": r.get("asset",""),
                                   "confidence": r.get("confidence","medium"), "can_query": True if addr.startswith("0x") else False})

# Also check entity_profiles
try:
    ep = sqlite3.connect(str(ROOT / "data" / "entity_profiles.sqlite"))
    for row in ep.execute("SELECT address, entity_name FROM entity_profiles"):
        a = row[0][:42] if row[0] and row[0].startswith("0x") else ""
        if a and a not in [d["address"] for d in discovered]:
            discovered.append({"address": a, "source_type": "entity_profiles", "source_ref": "manual",
                               "entity_name": row[1], "asset_hint": "", "confidence": "medium", "can_query": True})
    ep.close()
except: pass

disc_csv = ROOT / "data" / "hl_address_candidates_discovered.csv"
with open(disc_csv, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["address","source_type","source_ref","entity_name","asset_hint","confidence","can_query"])
    w.writeheader(); w.writerows(discovered)
print(f"\nDiscovered candidates: {len(discovered)}")
for d in discovered[:5]:
    print(f"  {d['address'][:16]}... {d['entity_name'][:25]} ({d['source_type']})")

# ── 5. Export leaders ──
for tbl, out_name in [("position_leaderboard", "dynamic_position_leaders_latest"),
                       ("movers_leaderboard", "dynamic_movers_latest"),
                       ("liquidation_risk_leaderboard", "dynamic_liquidation_risk_latest")]:
    rows = conn.execute(f"SELECT * FROM {tbl} WHERE run_time=?", (now,)).fetchall()
    if rows:
        desc = conn.execute(f"PRAGMA table_info({tbl})").fetchall()
        cols = [d[1] for d in desc if d[1] != "id"]
        csv_p = ROOT / "results" / f"{out_name}.csv"
        with open(csv_p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for row in rows:
                w.writerow({cols[i]: row[i+1] for i in range(len(cols))})
        print(f"  {out_name}: {len(rows)} rows")

# ── 6. Summary MD ──
sum_p = ROOT / "results" / "dynamic_universe_summary.md"
with open(sum_p, "w", encoding="utf-8") as f:
    f.write("# Dynamic Address Universe Summary\n\n")
    f.write(f"Generated: {now}\n\n")
    f.write(f"## Position Leaders\n")
    for (asset, side), pl in sorted(by_asset_side.items()):
        f.write(f"- {asset} {side}: {len(pl)} positions\n")
    f.write(f"\n## Movers\n")
    mc = conn.execute("SELECT COUNT(*) FROM movers_leaderboard WHERE run_time=?", (now,)).fetchone()[0]
    f.write(f"- detected: {mc}\n")
    f.write(f"\n## Liquidation Risk\n")
    lc = conn.execute("SELECT COUNT(*) FROM liquidation_risk_leaderboard WHERE run_time=?", (now,)).fetchone()[0]
    f.write(f"- positions with liq data: {lc}\n")
    f.write(f"\n## Address Candidates\n")
    f.write(f"- discovered: {len(discovered)}\n")
    f.write(f"- can_query: {sum(1 for d in discovered if d['can_query'])}\n")
    f.write(f"\n## Limitations\n")
    f.write(f"- Current sample: {len(positions)} positions across {len(set(p['asset'] for p in positions))} assets\n")
    f.write(f"- This is a **sample-based leaderboard**, not a full-market ranking.\n")
    f.write(f"- All rankings are relative to our monitored address pool only.\n")

conn.commit(); conn.close()
print(f"\nDB: {db_path}")
print(f"Summary: {sum_p}")
