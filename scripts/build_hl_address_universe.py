"""Build HL address universe from existing data sources."""
import csv, sqlite3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

addresses = {}
with open(ROOT / "data" / "hyperliquid_position_state.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        a = r.get("address","").strip()
        if a.startswith("0x"): addresses[a[:42]] = {"entity": r.get("entity",""), "source": "position_state"}

try:
    c = sqlite3.connect(str(ROOT / "data" / "entity_profiles.sqlite"))
    for row in c.execute("SELECT address, entity_name, profile_confidence FROM entity_profiles"):
        a = row[0][:42] if row[0] and row[0].startswith("0x") else ""
        if a and a not in addresses: addresses[a] = {"entity": row[1], "source": "entity_profiles"}
    c.close()
except: pass

out = ROOT / "data" / "hl_address_universe.csv"
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["address","entity_name","source_type"])
    w.writeheader()
    for a, info in addresses.items():
        w.writerow({"address": a, "entity_name": info["entity"], "source_type": info["source"]})

print(f"Address universe: {len(addresses)} addresses")
for a, info in list(addresses.items())[:8]:
    print(f"  {a[:16]}... {info['entity'][:30]} ({info['source']})")
print(f"Wrote: {out}")
