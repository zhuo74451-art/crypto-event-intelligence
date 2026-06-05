"""Build HL market structure layer for a given asset."""
import csv, json, sqlite3, sys, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
        print(f"  HL API error: {e}")
        return None

def fetch_meta():
    result = hl_post({"type": "metaAndAssetCtxs"})
    if not result or not isinstance(result, list) or len(result) < 2:
        return {}
    universe = result[0] if isinstance(result[0], list) else []
    ctxs = result[1] if isinstance(result[1], list) else []
    markets = {}
    for i, u in enumerate(universe):
        name = str(u.get("name", "")).upper() if isinstance(u, dict) else str(u).upper()
        ctx = ctxs[i] if i < len(ctxs) and isinstance(ctxs[i], dict) else {}
        markets[name] = {
            "mark_px": sf(ctx.get("markPx")),
            "oracle_px": sf(ctx.get("oraclePx")),
            "funding": sf(ctx.get("funding")),
            "oi_coin": sf(ctx.get("openInterest")),
            "oi_usd": sf(ctx.get("openInterest", 0)) * sf(ctx.get("markPx", 0)),
            "vol_24h": sf(ctx.get("dayNtlVlm")),
        }
    return markets

def main():
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--asset", default="TON")
    args = p.parse_args(); asset = args.asset.upper()

    markets = fetch_meta()
    hl = markets.get(asset, {})
    has_hl = bool(hl)

    # Address universe
    addresses = []
    au_path = ROOT / "data" / "hl_address_universe.csv"
    if au_path.exists():
        with open(au_path, encoding="utf-8-sig") as f:
            addresses = list(csv.DictReader(f))

    # Position sample: from position_state (we already have this)
    positions = []
    with open(ROOT / "data" / "hyperliquid_position_state.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if str(r.get("asset_symbol","")).upper() == asset:
                side = str(r.get("side","")).lower()
                positions.append({
                    "address": str(r.get("address",""))[:42],
                    "entity": str(r.get("entity",""))[:30],
                    "asset": asset,
                    "side_cn": "多单" if side == "long" else "空单",
                    "size_coin_abs": sf(r.get("szi_abs")),
                    "position_value_usd": sf(r.get("position_value_usd")),
                    "entry_price": sf(r.get("entry_px")),
                    "mark_price": sf(r.get("mark_px")),
                    "unrealized_pnl_usd": sf(r.get("unrealized_pnl")),
                    "liquidation_price": sf(r.get("liquidation_px")),
                })

    # Whale / large layers
    pos_sorted = sorted(positions, key=lambda p: -p["position_value_usd"])
    whale_threshold = 1_000_000
    whales = [p for p in pos_sorted if p["position_value_usd"] >= whale_threshold]
    whale_count = min(len(whales), 10)
    whales = whales[:10]
    large = [p for p in pos_sorted if p["position_value_usd"] >= 100_000]
    large_count = len(large)

    wlv = sum(p["position_value_usd"] for p in whales if p["side_cn"] == "多单")
    wsv = sum(p["position_value_usd"] for p in whales if p["side_cn"] == "空单")
    wtotal = wlv + wsv
    wlp = wlv / wtotal * 100 if wtotal > 0 else 0
    wsp = wsv / wtotal * 100 if wtotal > 0 else 0

    llv = sum(p["position_value_usd"] for p in large if p["side_cn"] == "多单")
    lsv = sum(p["position_value_usd"] for p in large if p["side_cn"] == "空单")
    ltotal = llv + lsv
    llp = llv / ltotal * 100 if ltotal > 0 else 0
    lsp = lsv / ltotal * 100 if ltotal > 0 else 0

    # Liquidation clusters
    nearest_long_liq = None; nearest_short_liq = None
    for p in positions:
        lp = p.get("liquidation_price", 0)
        if lp <= 0 or p["mark_price"] <= 0: continue
        dist = abs(p["mark_price"] - lp) / p["mark_price"] * 100
        if p["side_cn"] == "多单":
            if nearest_long_liq is None or lp > (nearest_long_liq.get("price", 0) if nearest_long_liq else 0):
                nearest_long_liq = {"price": lp, "dist": dist, "value": p["position_value_usd"]}
        elif p["side_cn"] == "空单":
            if nearest_short_liq is None or lp < (nearest_short_liq.get("price", 0) if nearest_short_liq else float("inf")):
                nearest_short_liq = {"price": lp, "dist": dist, "value": p["position_value_usd"]}

    # Quality
    if has_hl and whale_count >= 3: quality = "good"
    elif has_hl: quality = "market_only"
    elif len(positions) >= 3: quality = "sample_only"
    elif len(positions) > 0: quality = "partial"
    else: quality = "unavailable"

    # Card lines
    card_lines = []
    fr = hl.get("funding", 0)
    fr_pct = fr * 100
    if has_hl:
        if abs(fr_pct) >= 0.001:
            d = "多头付费" if fr > 0 else "空头付费"
            card_lines.append(f"▫️ 资金费率：{fr_pct:+.4f}% / 小时，{d}")
        else:
            card_lines.append(f"▫️ 资金费率：{fr_pct:+.4f}% / 小时，影响较弱")
        if hl.get("oi_usd", 0) > 0:
            card_lines.append(f"▫️ 全市场持仓：{hl['oi_usd']:,.0f}美元")
    if whale_count >= 3:
        card_lines.append(f"▫️ 主力样本：多单 {wlp:.0f}% / 空单 {wsp:.0f}%（n={whale_count}）")
    elif large_count >= 5:
        card_lines.append(f"▫️ 大户样本：多单 {llp:.0f}% / 空单 {lsp:.0f}%（n={large_count}）")
    if nearest_long_liq:
        card_lines.append(f"▫️ 多单清算线：{nearest_long_liq['price']:.2f}美元（距现价 {nearest_long_liq['dist']:.1f}%）")
    if nearest_short_liq:
        card_lines.append(f"▫️ 空单清算线：{nearest_short_liq['price']:.2f}美元（距现价 {nearest_short_liq['dist']:.1f}%）")

    # Output
    out_csv = ROOT / "results" / "hl_market_structure_latest.csv"
    out_md = ROOT / "results" / "hl_market_structure_latest.md"
    row = {
        "asset": asset, "mark_price": hl.get("mark_px", 0),
        "open_interest_usd": hl.get("oi_usd", 0),
        "funding_rate_hourly": fr, "funding_direction_cn": "多头付费" if fr > 0 else "空头付费" if fr < 0 else "中性",
        "sample_address_count": len(positions), "active_position_count": len(positions),
        "whale_count": whale_count, "whale_long_pct": wlp, "whale_short_pct": wsp,
        "large_count": large_count, "large_long_pct": llp, "large_short_pct": lsp,
        "nearest_long_liq_price": nearest_long_liq["price"] if nearest_long_liq else 0,
        "nearest_long_liq_distance_pct": nearest_long_liq["dist"] if nearest_long_liq else 0,
        "nearest_short_liq_price": nearest_short_liq["price"] if nearest_short_liq else 0,
        "nearest_short_liq_distance_pct": nearest_short_liq["dist"] if nearest_short_liq else 0,
        "market_structure_quality": quality,
        "card_market_structure_lines": " | ".join(card_lines),
        "has_hl": has_hl, "scope_misuse": quality == "partial" and whale_count < 2,
    }

    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        w.writeheader(); w.writerow(row)

    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# HL Market Structure: {asset}\n\n")
        f.write(f"quality: **{quality}**\n\n")
        f.write(f"## Market Layer\n")
        f.write(f"- has_hl_market_data: {has_hl}\n")
        if has_hl:
            f.write(f"- mark_price: {hl.get('mark_px',0):.4f}\n")
            f.write(f"- funding_rate: {fr_pct:+.4f}%/h ({row['funding_direction_cn']})\n")
            f.write(f"- OI: {hl.get('oi_usd',0):,.0f} USD\n")
        f.write(f"\n## Position Sample\n")
        f.write(f"- addresses_with_{asset}: {len(positions)}\n")
        f.write(f"- whale_count: {whale_count}\n")
        f.write(f"- large_count: {large_count}\n")
        if whale_count >= 3:
            f.write(f"- whale: long {wlp:.0f}% / short {wsp:.0f}%\n")
        f.write(f"\n## Card Lines\n")
        for cl in card_lines:
            f.write(f"- {cl}\n")

    print(f"Asset: {asset}")
    print(f"  HL market: {has_hl} | positions: {len(positions)} | whales: {whale_count} | large: {large_count}")
    print(f"  quality: {quality} | scope_misuse: {row['scope_misuse']}")
    print(f"  card_lines: {len(card_lines)}")
    for cl in card_lines:
        print(f"    {cl}")
    print(f"CSV: {out_csv}\nMD: {out_md}")

if __name__ == "__main__":
    main()
