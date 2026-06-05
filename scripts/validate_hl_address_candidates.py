"""v1.7D-4: Validate candidate addresses via clearinghouseState."""
import csv, json, sqlite3, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

def sf(v):
    try: return float(v or 0)
    except: return 0.0

def hl_post(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=data,
                                  method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def china_now(): return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# Load candidates
cand_path = ROOT / "data" / "hl_address_candidates_discovered.csv"
candidates = []
if cand_path.exists():
    with open(cand_path, encoding="utf-8-sig") as f:
        candidates = list(csv.DictReader(f))

# Deduplicate by address
seen = set()
unique = []
for c in candidates:
    a = c.get("address","").strip()[:42]
    if a.startswith("0x") and a not in seen:
        seen.add(a); unique.append(c)
candidates = unique[:20]  # max 20

print(f"Validating {len(candidates)} unique candidates...")
results = []
added_count = 0

for c in candidates:
    addr = c["address"][:42]
    if not addr.startswith("0x"):
        results.append({"address": addr[:20], "source_type": c.get("source_type",""), "query_ok": False,
                        "active_positions_count": 0, "assets_active": "", "has_hype_position": False,
                        "hype_side": "", "hype_position_value_usd": 0, "largest_position_asset": "",
                        "largest_position_value_usd": 0, "should_add": False, "reason": "invalid_address"})
        continue

    state = hl_post({"type": "clearinghouseState", "user": addr})
    if not state or "error" in str(state):
        results.append({"address": addr[:16], "source_type": c.get("source_type",""), "query_ok": False,
                        "active_positions_count": 0, "assets_active": "", "has_hype_position": False,
                        "hype_side": "", "hype_position_value_usd": 0, "largest_position_asset": "",
                        "largest_position_value_usd": 0, "should_add": False, "reason": f"query_failed:{str(state)[:80]}"})
        continue

    positions = state.get("assetPositions", []) if isinstance(state, dict) else []
    if not positions:
        results.append({"address": addr[:16], "source_type": c.get("source_type",""), "query_ok": True,
                        "active_positions_count": 0, "assets_active": "", "has_hype_position": False,
                        "hype_side": "", "hype_position_value_usd": 0, "largest_position_asset": "",
                        "largest_position_value_usd": 0, "should_add": False, "reason": "no_active_positions"})
        continue

    # Parse positions
    parsed = []
    for p in positions:
        pos = p.get("position", {})
        coin = pos.get("coin", "?")
        szi = sf(pos.get("szi", 0))
        side = "多单" if szi > 0 else "空单" if szi < 0 else ""
        val = abs(szi) * sf(state.get("assetCtx",{}).get("markPx",0)) if not sf(pos.get("positionValue")) else sf(pos.get("positionValue"))
        entry_px = sf(pos.get("entryPx"))
        liq_px = sf(pos.get("liquidationPx"))
        pnl = sf(pos.get("unrealizedPnl"))
        parsed.append({"coin": str(coin).upper(), "side": side, "szi_abs": abs(szi), "value_usd": val,
                       "entry_px": entry_px, "liq_px": liq_px, "pnl": pnl})

    active = [p for p in parsed if p["value_usd"] > 0]
    has_hype = any(p["coin"] == "HYPE" for p in active)
    hype_pos = next((p for p in active if p["coin"] == "HYPE"), None)
    largest = max(active, key=lambda p: p["value_usd"]) if active else None
    should_add = any(p["value_usd"] >= 100_000 for p in active)

    reason = []
    if should_add: reason.append("meets_100k_threshold"); added_count += 1
    if has_hype: reason.append("has_hype")

    results.append({
        "address": addr[:16], "source_type": c.get("source_type",""), "query_ok": True,
        "active_positions_count": len(active), "assets_active": ",".join(p["coin"] for p in active),
        "has_hype_position": has_hype, "hype_side": hype_pos["side"] if hype_pos else "",
        "hype_position_value_usd": hype_pos["value_usd"] if hype_pos else 0,
        "largest_position_asset": largest["coin"] if largest else "",
        "largest_position_value_usd": largest["value_usd"] if largest else 0,
        "should_add": should_add, "reason": ";".join(reason),
    })
    print(f"  {addr[:16]}... ok={len(active)}pos add={should_add} hype={has_hype} largest={largest['coin'] if largest else '?'} ${largest['value_usd']/1e6:.1f}M" if largest else f"  {addr[:16]}... empty")

# Write validation
csv_p = ROOT / "results" / "hl_address_candidate_validation_v1.csv"
with open(csv_p, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    w.writeheader(); w.writerows(results)

# Update dynamic universe CSV
existing = set()
au_path = ROOT / "data" / "hl_address_universe.csv"
if au_path.exists():
    with open(au_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f): existing.add(r.get("address","")[:16])

new_entries = [r for r in results if r["should_add"]]
all_universe = []
# Keep existing
if au_path.exists():
    with open(au_path, encoding="utf-8-sig") as f:
        all_universe = list(csv.DictReader(f))
# Add new
for r in new_entries:
    all_universe.append({"address": r["address"], "source_type": f"validated_{r['source_type']}",
                          "confidence": "medium", "assets_active": r["assets_active"],
                          "largest_position_asset": r["largest_position_asset"],
                          "largest_position_value_usd": str(r["largest_position_value_usd"]),
                          "last_validated_at": china_now()})

dyn_path = ROOT / "data" / "hl_dynamic_address_universe.csv"
with open(dyn_path, "w", encoding="utf-8-sig", newline="") as f:
    fields = ["address","source_type","confidence","assets_active","largest_position_asset","largest_position_value_usd","last_validated_at"]
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader(); w.writerows(all_universe)

# Summary
md_p = ROOT / "results" / "hl_address_candidate_validation_v1.md"
with open(md_p, "w", encoding="utf-8") as f:
    f.write("# Candidate Validation Results\n\n")
    f.write(f"Total candidates: {len(results)}\n")
    f.write(f"Query success: {sum(1 for r in results if r['query_ok'])}\n")
    f.write(f"Active positions: {sum(1 for r in results if r['active_positions_count']>0)}\n")
    f.write(f"HYPE active: {sum(1 for r in results if r['has_hype_position'])}\n")
    f.write(f"Added to universe: {len(new_entries)}\n")
    f.write(f"Dynamic universe total: {len(all_universe)}\n")

print(f"\nTotal: {len(results)} | Success: {sum(1 for r in results if r['query_ok'])} | Active: {sum(1 for r in results if r['active_positions_count']>0)} | HYPE: {sum(1 for r in results if r['has_hype_position'])} | Added: {len(new_entries)}")
print(f"Dynamic universe: {len(all_universe)} addresses")
print(f"CSV: {csv_p}\nMD: {md_p}\nUniverse: {dyn_path}")
