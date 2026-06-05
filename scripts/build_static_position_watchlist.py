"""v1.8A: Static Position Watchlist builder."""
import csv, json, re, sqlite3, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

def sf(v):
    try: return float(v or 0)
    except: return 0.0

def china_now(): return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── Init DB ──
db = ROOT / "data" / "static_position_watchlist.sqlite"
db.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(str(db)); conn.execute("PRAGMA journal_mode=WAL")
conn.execute("""CREATE TABLE IF NOT EXISTS static_entities (
    entity_id TEXT PRIMARY KEY, address TEXT, entity_name TEXT, aliases TEXT,
    first_seen TEXT, last_seen TEXT, source_channels TEXT, confidence TEXT, notes TEXT)""")
conn.execute("""CREATE TABLE IF NOT EXISTS static_entity_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT, asset TEXT, label_text TEXT,
    label_type TEXT, label_time_scope TEXT DEFAULT 'historical',
    source_channel TEXT, source_time TEXT, evidence_text TEXT, confidence TEXT)""")
conn.execute("""CREATE TABLE IF NOT EXISTS static_recent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT, asset TEXT, event_time TEXT,
    action_cn TEXT, side_cn TEXT, value_usd REAL, size_coin REAL,
    pnl_usd REAL, liquidation_price REAL, note_cn TEXT, source_channel TEXT, evidence_text TEXT)""")
conn.commit()

# ── 1. Extract from HyperInsight ──
hi_path = ROOT / "data" / "benchmark" / "hyperinsight_entity_mentions.csv"
entities = defaultdict(lambda: {"aliases": set(), "channels": set(), "labels": [], "events": [], "first": "", "last": ""})
if hi_path.exists():
    with open(hi_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            addr = r.get("address","").strip()[:42]
            if not addr.startswith("0x"): continue
            en = r.get("entity_name","").strip()
            if not en: en = "Unknown Hyperliquid Whale"
            eid = en.lower().replace(" ","_")
            entities[eid]["aliases"].add(en)
            entities[eid]["address"] = addr
            entities[eid]["channels"].add("HyperInsight")
            ts = r.get("source_message_time","") or china_now()
            if not entities[eid]["first"] or ts < entities[eid]["first"]: entities[eid]["first"] = ts
            if ts > entities[eid]["last"]: entities[eid]["last"] = ts
            rank = r.get("rank_label",""); identity = r.get("identity_label","")
            asset = r.get("asset",""); direction = r.get("direction","")
            if rank or identity:
                entities[eid]["labels"].append({
                    "address": addr, "asset": asset,
                    "label_text": f"{rank} {identity}".strip(),
                    "label_type": "rank_label" if rank else "identity_label",
                    "source_channel": "HyperInsight", "source_time": ts,
                    "evidence_text": r.get("source_text","")[:300],
                    "confidence": r.get("confidence","medium"),
                })

# ── 2. Extract from position_state ──
pos_path = ROOT / "data" / "hyperliquid_position_state.csv"
if pos_path.exists():
    with open(pos_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            addr = r.get("address","").strip()[:42]
            if not addr.startswith("0x"): continue
            en = r.get("entity","").strip()
            if not en or "unknown" in en.lower(): en = "Unknown"
            eid = en.lower().replace(" ","_")
            entities[eid]["aliases"].add(en)
            entities[eid]["address"] = addr
            entities[eid]["channels"].add("position_state")
            now = china_now()
            if not entities[eid]["first"]: entities[eid]["first"] = now
            entities[eid]["last"] = now
            entities[eid]["labels"].append({
                "address": addr, "asset": r.get("asset_symbol","").upper(),
                "label_text": f"{r.get('asset_symbol','').upper()} {('多单' if r.get('side','').lower()=='long' else '空单')}",
                "label_type": "current_claim", "source_channel": "position_state",
                "source_time": now, "evidence_text": f"Position ${sf(r.get('position_value_usd'))/1e6:.1f}M",
                "confidence": "high",
            })
            entities[eid]["events"].append({
                "address": addr, "asset": r.get("asset_symbol","").upper(),
                "event_time": r.get("updated_at_china",now)[:19],
                "action_cn": "持仓中", "side_cn": "多单" if r.get("side","").lower()=="long" else "空单",
                "value_usd": sf(r.get("position_value_usd")),
                "size_coin": sf(r.get("szi_abs")),
                "pnl_usd": sf(r.get("unrealized_pnl")),
                "liquidation_price": sf(r.get("liquidation_px")),
                "source_channel": "position_state",
            })

# ── 3. Write to DB ──
for eid, e in entities.items():
    addr = e.get("address","")
    if not addr.startswith("0x"): continue
    en = max(e["aliases"], key=len) if e["aliases"] else eid
    conn.execute("INSERT OR REPLACE INTO static_entities VALUES (?,?,?,?,?,?,?,?,?)",
        (eid, addr, en, json.dumps(list(e["aliases"])), e["first"], e["last"],
         ",".join(e["channels"]), "high" if len(e["channels"])>=2 else "medium", ""))
    for lbl in e.get("labels", []):
        lt = lbl["label_type"]; lts = "current" if lt == "current_claim" else "historical"
        conn.execute("INSERT INTO static_entity_labels (address,asset,label_text,label_type,label_time_scope,source_channel,source_time,evidence_text,confidence) VALUES (?,?,?,?,?,?,?,?,?)",
            (addr, lbl.get("asset",""), lbl["label_text"], lt, lts, lbl["source_channel"], lbl["source_time"], lbl["evidence_text"][:500], lbl.get("confidence","medium")))
    for ev in e.get("events", []):
        conn.execute("INSERT INTO static_recent_events (address,asset,event_time,action_cn,side_cn,value_usd,size_coin,pnl_usd,liquidation_price,note_cn,source_channel,evidence_text) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (addr, ev["asset"], ev["event_time"], ev["action_cn"], ev["side_cn"], ev["value_usd"], ev["size_coin"], ev["pnl_usd"], ev["liquidation_price"], "", ev["source_channel"], ""))
conn.commit()

# Summary
ec = conn.execute("SELECT COUNT(*) FROM static_entities").fetchone()[0]
lc = conn.execute("SELECT COUNT(*) FROM static_entity_labels").fetchone()[0]
rc = conn.execute("SELECT COUNT(*) FROM static_recent_events").fetchone()[0]
print(f"Static watchlist: {ec} entities, {lc} labels, {rc} events")

# Export CSV
with open(ROOT / "data" / "static_position_watchlist.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["entity_id","address","entity_name","aliases","source_channels","confidence","first_seen","last_seen"])
    w.writeheader()
    for row in conn.execute("SELECT * FROM static_entities").fetchall():
        w.writerow(dict(zip(["entity_id","address","entity_name","aliases","first_seen","last_seen","source_channels","confidence","notes"], row)))

# Summary MD
cnt_by_source = conn.execute("SELECT source_channel, COUNT(*) FROM static_entity_labels GROUP BY source_channel").fetchall()
with open(ROOT / "results" / "static_position_watchlist_summary.md", "w", encoding="utf-8") as f:
    f.write("# Static Position Watchlist Summary\n\n")
    f.write(f"Generated: {china_now()}\n\n")
    f.write(f"- entities: {ec}\n")
    f.write(f"- labels: {lc}\n")
    f.write(f"- events: {rc}\n\n")
    f.write("## By Source\n\n")
    for src, cnt in cnt_by_source:
        f.write(f"- {src}: {cnt}\n")

print(f"Watchlist CSV: {ROOT / 'data' / 'static_position_watchlist.csv'}")
print(f"Summary MD: {ROOT / 'results' / 'static_position_watchlist_summary.md'}")
conn.close()
