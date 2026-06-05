"""
v1.6G: Address Behavior Card Auto-Send Gate.
v1.10-H: Wired pre_send_gate() before send_tg() for sender gate coverage.

Generates HyperInsight 90+ cards, scores them, sends if passing all gates.
"""

import csv, json, hashlib, os, re, sqlite3, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CN_TZ = timezone(timedelta(hours=8))

from scripts.market_radar_pre_send_gate import pre_send_gate  # v1.10-H: sender gate coverage
COOLDOWN_DB = ROOT / "data" / "ab_card_cooldown.sqlite"
SUM_PATH = ROOT / "results" / "hl_address_history_summary.csv"
POS_PATH = ROOT / "data" / "hyperliquid_position_state.csv"

def china_now(): return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
def sf(v):
    try: return float(v or 0)
    except: return 0.0

# ── Card renderer ──
def ns_human(val, asset=""):
    a = abs(val)
    if a >= 1_000_000: return f"{a/1_000_000:.1f}M" + (f" {asset}" if asset else "")
    if a >= 10_000: return f"{a/10_000:.1f} 万枚" + (f" {asset}" if asset else "")
    return f"{a:.0f} {asset}" if asset else f"{a:.0f}"

def usd(v):
    a = abs(v); s = "-" if v < 0 else ""
    if a >= 1_000_000: return f"{s}${a/1_000_000:.1f}M"
    if a >= 1_000: return f"{s}${a/1_000:.0f}K"
    return f"{s}${a:.0f}"

def build_hi_card(s, pos):
    entity = pos.get("entity", s.get("entity", "Unknown"))
    asset = s["asset"]; side_r = str(pos.get("side","?")).lower()
    fc = int(s.get("fills_7d",0)); br = float(s.get("buy_ratio_7d",0))
    tb = s.get("trade_bias_label",""); ns = sf(s.get("net_size_delta","0"))
    lc = int(s.get("ledger_updates",0)); addr_full = str(pos.get("address","")).strip()
    pos_val = sf(pos.get("position_value_usd")); szi = sf(pos.get("szi_abs"))
    entry_px = sf(pos.get("entry_px")); mark_px = sf(pos.get("mark_px"))
    liq_px = sf(pos.get("liquidation_px")); liq_dist = sf(pos.get("liquidation_distance_pct"))
    pnl = sf(pos.get("unrealized_pnl"))
    side_cn = "多单" if side_r == "long" else "空单" if side_r == "short" else ""
    if fc == 0 and lc == 0: return None, "quiet_address"

    action_cn = "连续买入" if "buy" in tb else "连续卖出" if "sell" in tb else "持续交易"
    dir_label = ("几乎全部为买入成交" if br>=0.95 else "买入为主" if br>=0.65 else
                 "几乎全部为卖出成交" if (1-br)>=0.95 else "卖出为主" if (1-br)>=0.65 else "买卖双向")
    ns_str = (f"7 天净买入 {ns_human(ns)}" if ns>0 else f"7 天净卖出 {ns_human(ns)}" if ns<0 else "7 天成交")
    hd = sum(1 for v in [pos_val, szi, entry_px, mark_px, pnl] if abs(v) > 0.01)

    lines = []
    # Title
    lines.append(f"<b>🚀 Market Radar 地址异动｜{asset} {side_cn}{action_cn}</b>"); lines.append("")
    # Identity
    lines.append(f"【{entity}｜{asset} {side_cn}】{ns_str}"); lines.append("")

    # Data section (fixed order, ▫️ markers, only if value exists)
    if pos_val > 0:
        lines.append(f"▫️ 持仓规模：{usd(pos_val)}")
    if szi > 0:
        lines.append(f"▫️ 持仓数量：{ns_human(szi, asset)}")
    lines.append(f"▫️ 成交：7 天 {fc} 笔，{dir_label}")
    if entry_px > 0:
        lines.append(f"▫️ 均价：${entry_px:.2f}")
    if pnl != 0:
        denom = pos_val - pnl; pnl_pct = abs(pnl)/denom*100 if denom > 0 else 0
        sign = "+" if pnl > 0 else ""
        lines.append(f"▫️ 当前盈亏：{usd(pnl)}（{sign}{pnl_pct:.1f}%）")
    if mark_px > 0:
        lines.append(f"▫️ 当前币价：${mark_px:.2f}")
    if liq_px > 0:
        lines.append(f"▫️ 清算价：${liq_px:.2f}")
    if liq_dist > 0:
        lines.append(f"▫️ 强平距离：{liq_dist*100:.1f}%")
    # Flow: human readable
    nf_val = sf(s.get("net_flow_usd_7d", "0"))
    if abs(nf_val) > 100:
        direction = "充值" if nf_val > 0 else "提取"
        lines.append(f"▫️ 资金进出：7 天{direction}约 {usd(nf_val)}")
    elif lc > 0:
        lines.append("▫️ 资金进出：7 天内未见明显充值或提取")
    else:
        lines.append("▫️ 资金进出：7 天内无变动")
    lines.append("▫️ 资金费：影响较弱，暂不判断真实资金成本")
    lines.append("")

    # Address
    if addr_full.startswith("0x"):
        lines.append(f"📌 地址：{addr_full}")
    lines.append("")

    # v1.6H: Entity Profile — temporal-aware annotation
    from resolve_entity_profile import resolve
    profile = resolve(addr_full, asset, entity)

    note_parts = []
    # 1. Profile identity (historical, with temporal qualifier)
    if profile["note_safe_label"]:
        note_parts.append(profile["note_safe_label"])
    # 2. Recent activity
    if fc >= 10:
        bias_label = "买入成交" if br >= 0.95 else "卖出成交" if (1-br) >= 0.95 else "双向成交"
        note_parts.append(f"近期在 {asset} 上成交非常活跃，7 天内几乎全部为{bias_label}")
    # 3. Multi-asset
    if entity and "loraclexyz" in entity.lower():
        note_parts.append("该地址同时持有多个资产仓位，需按单一资产分别观察")
    # 4. Liquidation risk
    if liq_px > 0 and mark_px > 0:
        dist_to_liq = abs(liq_px - mark_px) / mark_px * 100
        if dist_to_liq < 15:
            note_parts.append(f"当前价距清算价较近（约{dist_to_liq:.0f}%），需关注清算风险")
    # 5. Temporal warning
    if profile["temporal_warning"]:
        note_parts.append(profile["temporal_warning"])
    # 6. Fallback
    if not note_parts:
        note_parts.append("暂无可靠公开身份标签，仅按本地监控到的持仓与成交记录归类")

    lines.append(f"🔥 注：{'；'.join(note_parts)}。")
    lines.append("")

    lines.append("🔗 Hyperliquid 查看：https://app.hyperliquid.xyz/")
    lines.append("")
    lines.append("⚠️ 仅做市场结构观察，不构成交易建议。")

    return {"text": "\n".join(lines), "entity": entity, "asset": asset, "action": action_cn,
            "hard_data_count": hd, "card_should_send": True}, ""


# ── Scoring ──
def score_card(text):
    s = {}
    s["title"] = 15 if re.search(r"(HYPE|BTC|ETH|SOL|BNB|DOGE|XRP|TON|AVAX|LINK)", text) and re.search(r"(买入|卖出|加仓|减仓|爆仓|平仓|减持|增持|连续买入|连续卖出|反手)", text) else 8
    s["id"] = 15 if re.search(r"(0x[a-fA-F0-9]{8,}|loraclexyz|Abras|Loracle)", text, re.I) else 5
    s["action"] = min(20, sum(1 for a in ["加仓","减仓","爆仓","平仓","连续买入","连续卖出","减持","增持","净买入","净卖出"] if a in text) * 7)
    s["num"] = min(20, len(re.findall(r"[\d,.]+[万枚KMB%]|\$\d+", text)) * 4)
    s["note"] = 15 if "🔥 注" in text else 0
    bad = sum(1 for kw in ["long\n","short\n","buy_ratio","current_side","profile_enabled","看多","看空"] if kw in text)
    s["clean"] = max(0, 15 - bad * 3)
    return sum(s.values()), s


# ── Cooldown ──
def init_cooldown():
    COOLDOWN_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(COOLDOWN_DB)); conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS cooldown (key_id TEXT PRIMARY KEY, last_sent TEXT NOT NULL)")
    conn.commit(); return conn

def check_cooldown(conn, key_id):
    row = conn.execute("SELECT last_sent FROM cooldown WHERE key_id=?", (key_id,)).fetchone()
    if not row: return False
    dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=CN_TZ)
    return (datetime.now(CN_TZ) - dt).total_seconds() < 1800  # 30 min

def set_cooldown(conn, key_id):
    conn.execute("INSERT OR REPLACE INTO cooldown (key_id, last_sent) VALUES (?,?)",
                 (key_id, china_now())); conn.commit()


# ── Send ──
def send_tg(text, token, chat_id):
    if not token or not chat_id: return "", "missing_token_or_chat_id"
    # Legacy block
    for kw in ["📌 事件", "📝 详情", "🧠 解读", "🔥 强度", "★★★"]:
        if kw in text: return "", f"blocked_legacy:{kw}"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode("utf-8"))
        if result.get("ok"): return str(result["result"]["message_id"]), ""
        return "", f"API:{json.dumps(result)[:200]}"
    except Exception as e: return "", str(e)[:200]


# ── Main ──
def main():
    import argparse; p = argparse.ArgumentParser()
    p.add_argument("--send", action="store_true", help="Actually send to TG")
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    args = p.parse_args()

    if not SUM_PATH.exists(): print("No history summary"); return 1
    if not POS_PATH.exists(): print("No position state"); return 1

    summaries = {}; positions = {}
    with open(SUM_PATH, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f): summaries[r["address"]] = r
    with open(POS_PATH, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            key = str(r.get("address","")).strip()[:16] + ":" + str(r.get("asset_symbol","")).upper()
            positions[key] = r

    cconn = init_cooldown()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_PUBLISH_CHAT_IDS", ""))
    if chat_id and "," in chat_id: chat_id = chat_id.split(",")[0].strip()

    gate_rows = []
    for addr, s in summaries.items():
        asset = s["asset"]; pos_key = addr[:16] + ":" + asset
        pos = positions.get(pos_key, {})
        card, reason = build_hi_card(s, pos)
        if card is None:
            gate_rows.append({"address":addr[:16],"asset":asset,"action":"","benchmark_score":0,
                "hard_data_count":0,"card_should_send":"False","gate_passed":"False",
                "blocked_reason":reason,"cooldown_applied":"","sent":"False","message_id":""})
            continue

        text = card["text"]; score_val, breakdown = score_card(text)
        hd = card["hard_data_count"]; entity = card["entity"]; action = card["action"]
        passed = True; reasons = []

        if score_val < 90: passed = False; reasons.append(f"score_{score_val}_lt_90")
        if hd < 5: passed = False; reasons.append(f"hard_data_{hd}_lt_5")
        machine_hits = sum(1 for kw in ["buy_ratio","current_side","trade_bias_label","profile_enabled","size-based"] if kw in text)
        forbidden = sum(1 for kw in ["看多","看空","利好","利空","吸筹","出货","跑路","止盈","割肉","恐慌","战神","聪明钱"] if kw in text)
        if machine_hits > 0: passed = False; reasons.append(f"machine_terms={machine_hits}")
        if forbidden > 0: passed = False; reasons.append(f"forbidden_terms={forbidden}")

        cooldown_key = f"{entity}:{asset}:{action}"; cd = check_cooldown(cconn, cooldown_key)
        if cd: passed = False; reasons.append("cooldown_30min")

        # ── v1.10-H: pre_send_gate() universal check ──
        if passed:
            signal = {
                "signal_type": "address_behavior",
                "source_type": "hyperliquid_onchain",
                "asset": asset,
                "core_entity": entity,
                "source": "hyperliquid_address_history",
                "source_url": "https://app.hyperliquid.xyz/",
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            payload = {"text": text, "parse_mode": "HTML"}
            precheck = pre_send_gate(signal, payload, target_env="test")
            if not precheck["allowed"]:
                passed = False
                reasons.append(f"pre_send_gate_blocked:{precheck['blocked_reason']}")

        sent = False; msg_id = ""
        if passed and args.send:
            msg_id, err = send_tg(text, token, chat_id)
            if msg_id:
                sent = True; set_cooldown(cconn, cooldown_key)
            else:
                reasons.append(f"send_failed:{err}")

        if args.dry_run and not args.send:
            print(f"\n=== {entity} {asset} ===\n{text}")
            print(f"Score: {score_val}/100 | HD: {hd} | Pass: {passed} | Reasons: {reasons}")

        gate_rows.append({"address":addr[:16],"asset":asset,"action":action,
            "benchmark_score":score_val,"hard_data_count":hd,
            "card_should_send":str(card["card_should_send"]),
            "gate_passed":str(passed),"blocked_reason":"; ".join(reasons),
            "cooldown_applied":str(cd),"sent":str(sent),"message_id":msg_id})

    # Write outputs
    for path, fields in [
        ("results/hyperinsight_style_card_preview_latest.csv", ["address","asset","entity","action","benchmark_score","hard_data_count"]),
        ("results/address_behavior_send_gate_summary.csv", ["address","asset","action","benchmark_score","hard_data_count","card_should_send","gate_passed","blocked_reason","cooldown_applied","sent","message_id"]),
    ]:
        with open(ROOT/path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(gate_rows)

    with open(ROOT/"results"/"card_benchmark_score_latest.md", "w", encoding="utf-8") as f:
        f.write("# Card Benchmark Scores (Latest)\n\n| address | asset | score | hd | gate |\n|---|---:|---:|---|\n")
        for r in gate_rows:
            f.write(f"| {r['address']} | {r['asset']} | {r['benchmark_score']} | {r['hard_data_count']} | {r['gate_passed']} |\n")

    sent_count = sum(1 for r in gate_rows if r["sent"] == "True")
    print(f"\nGate summary: {len(gate_rows)} cards, {sent_count} sent")
    for r in gate_rows:
        tag = "SENT" if r["sent"]=="True" else "PASS" if r["gate_passed"]=="True" else "BLOCKED"
        print(f"  [{tag}] {r['asset']} score={r['benchmark_score']} {r['blocked_reason']}")
    cconn.close(); return 0

if __name__ == "__main__":
    raise SystemExit(main())
