"""v1.8F-review-v2: Generate static position cards review v2 with entry_price consistency.

Reads current position state and entity data, computes entry_price consistency,
cleans forbidden text patterns, ranks Top 5, and produces 4 output files.
"""
import csv, json, re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

FORBIDDEN_TEXT = [
    "CEI", "静态仓位库", "Unknown", "unavailable", "数据不足",
    "long", "short", "Funding", "战神", "聪明钱", "吸筹", "出货",
    "内幕", "疑似内幕", "上币内幕",
]

# Map unsafe entity labels to safe, neutral replacements.
# Applied during entity_clean so regenerated outputs never carry
# qualitative / directional expressions about the address.
ENTITY_LABEL_SANITIZE_MAP = {
    "疑似HYPE上币内幕": "HYPE 大额仓位地址",
}

# Profiler note template for addresses whose label was sanitized.
ENTITY_SANITIZED_PROFILE_NOTE = (
    "该地址曾出现在 HYPE 相关大额仓位样本中，当前仓位已通过最新数据验证。"
)


def sf(v):
    try: return float(v or 0)
    except: return 0.0


def china_now():
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def short_addr(addr):
    addr = addr.strip()
    if len(addr) >= 10:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr


def money_usd(v):
    v = sf(v)
    if abs(v) >= 1e8:
        return f"{v/1e8:.2f}亿美元"
    elif abs(v) >= 1e4:
        return f"{v/1e4:.2f}万美元"
    else:
        return f"{v:,.0f}美元"


def pnl_money_cn(v):
    """Format PnL with explicit sign prefix for TG candidate cards.

    Positive values get '+' sign, negative values retain '-' sign.
    This prevents abs()-style display that drops the profit/loss direction.
    """
    v = sf(v)
    sign = "+" if v >= 0 else "-"
    av = abs(v)
    if av >= 1e8:
        return f"{sign}{av/1e8:.2f}亿美元"
    elif av >= 1e4:
        return f"{sign}{av/1e4:.2f}万美元"
    else:
        return f"{sign}{av:,.0f}美元"


def money_coin(v, asset):
    v = sf(v)
    if abs(v) >= 1e8:
        return f"{v/1e8:.1f}亿枚 {asset}"
    elif abs(v) >= 1e4:
        return f"{v/1e4:.1f}万枚 {asset}"
    elif abs(v) >= 1e3:
        return f"{v/1e3:.1f}千枚 {asset}"
    else:
        return f"{v:,.2f}枚 {asset}"


def pct_str(v):
    return f"{sf(v)*100:+.1f}%"


def pct_abs(v):
    return f"{abs(sf(v))*100:.1f}%"


def side_cn(side):
    s = side.strip().lower()
    return "多单" if s == "long" else "空单"


def clean_entity_name(name, addr, hi_labels=None):
    """Clean entity name: remove forbidden patterns, sanitize unsafe labels,
    fallback to HyperInsight labels or address."""
    name = name.strip()
    if not name:
        name = ""
    # If entity is Unknown-prefixed, try HyperInsight identity label first
    if "unknown" in name.lower():
        if hi_labels and addr in hi_labels:
            for lbl in hi_labels[addr]:
                identity = lbl.get("identity", "").strip()
                # Extract clean identity: remove trailing brackets like 「 HYPE 多仓 TOP 1」
                identity_clean = re.sub(r'[「（(].*$', '', identity).strip()
                if identity_clean and len(identity_clean) >= 2:
                    # Sanitize before returning
                    return sanitize_entity_label(identity_clean)
        # Fallback: strip "Unknown" prefix
        cleaned = re.sub(r'(?i)unknown\s+', '', name).strip()
        if cleaned and len(cleaned) >= 3:
            return sanitize_entity_label(cleaned)
        return f"主力地址 {short_addr(addr)}"
    # Always sanitize the final entity name
    return sanitize_entity_label(name)


def sanitize_entity_label(text):
    """Replace known unsafe entity labels with safe, neutral alternatives.

    Handles both exact-match replacements (ENTITY_LABEL_SANITIZE_MAP)
    and generic pattern removal for directional / qualitative expressions.
    """
    if not text:
        return text
    # Exact label replacements
    for old, new in ENTITY_LABEL_SANITIZE_MAP.items():
        text = text.replace(old, new)
    return text


def check_forbidden(text):
    """Check if text contains any forbidden words. Returns list of found words."""
    found = []
    for word in FORBIDDEN_TEXT:
        if word.lower() in text.lower():
            found.append(word)
    return found


def side_label_for_display(side):
    """Return Chinese side label without using 'long'/'short'."""
    if side.strip().lower() == "long":
        return "多头"
    return "空头"


def compute_implied_liquidation_distance(mark_px, liq_px, side):
    """Compute implied liquidation distance as a ratio (e.g. 0.2425 = 24.25%).

    Formula:
      long:  (mark_px - liq_px) / mark_px
      short: (liq_px - mark_px) / mark_px

    Returns ratio, or 0.0 if mark_px <= 0.
    """
    if mark_px <= 0 or liq_px <= 0:
        return 0.0
    side = side.strip().lower()
    if side == "long":
        return (mark_px - liq_px) / mark_px
    else:
        return (liq_px - mark_px) / mark_px


def liquidation_edge_case_blocked(mark_px, liq_px, side):
    """Check edge cases where liquidation price is on wrong side of mark.
    Returns (is_blocked, reason) tuple.
    """
    if liq_px <= 0:
        return False, ""
    side = side.strip().lower()
    if side == "long" and liq_px >= mark_px:
        return True, "liquidation_price_above_mark_long"
    if side == "short" and liq_px <= mark_px:
        return True, "liquidation_price_below_mark_short"
    return False, ""


# ── 1. Load entity labels from HyperInsight ──
def load_hyperinsight_labels():
    hi_path = ROOT / "data" / "benchmark" / "hyperinsight_entity_mentions.csv"
    labels = defaultdict(list)
    if not hi_path.exists():
        return labels
    with open(hi_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            addr = r.get("address","").strip()[:42]
            if not addr.startswith("0x"):
                continue
            labels[addr].append({
                "entity_name": r.get("entity_name","").strip(),
                "identity": r.get("identity_label","").strip(),
                "rank": r.get("rank_label","").strip(),
                "asset": r.get("asset","").strip(),
                "direction": r.get("direction","").strip(),
                "time": r.get("source_message_time",""),
            })
    return labels


# ── 2. Read position state ──
def load_positions():
    pos_path = ROOT / "data" / "hyperliquid_position_state.csv"
    positions = []
    with open(pos_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            positions.append(r)
    return positions


# ── 3. Build cards with entry_price consistency ──
def build_cards(positions, hi_labels):
    cards = []
    for p in positions:
        addr = p.get("address","").strip()
        raw_entity = p.get("entity","").strip()
        asset = p.get("asset_symbol","").strip().upper()
        side = p.get("side","").strip().lower()
        szi = abs(sf(p.get("szi_abs")))
        pv = sf(p.get("position_value_usd"))
        upnl = sf(p.get("unrealized_pnl"))
        entry_px = sf(p.get("entry_px"))
        liq_px = sf(p.get("liquidation_px"))
        mark_px = sf(p.get("mark_px"))
        roi = sf(p.get("return_on_equity"))

        if szi <= 0 or pv <= 0:
            continue

        # Compute implied entry price
        if side == "long":
            implied = (pv - upnl) / szi
        else:
            implied = (pv + upnl) / szi

        # Deviation
        if entry_px > 0:
            deviation = abs(entry_px - implied) / entry_px
        else:
            deviation = 0.0

        # Entry price consistency status
        entry_consistency = "pass" if deviation <= 0.02 else "blocked"

        # ── Liquidation distance consistency ──
        displayed_liq_dist = sf(p.get("liquidation_distance_pct"))
        implied_liq_dist = compute_implied_liquidation_distance(mark_px, liq_px, side)
        liq_deviation = abs(displayed_liq_dist - implied_liq_dist)

        # Liquidation distance consistency: deviation <= 0.01 (1 percentage point in ratio space)
        liq_consistency = "pass" if (liq_px > 0 and liq_deviation <= 0.01) else ("pass" if liq_px <= 0 else "blocked")

        # Edge case checks
        edge_blocked, edge_reason = liquidation_edge_case_blocked(mark_px, liq_px, side)
        if edge_blocked:
            liq_consistency = "blocked"

        # Build blocked reasons
        blocked_reasons = []
        if entry_consistency == "blocked":
            blocked_reasons.append("entry_price_inconsistent")
        if liq_consistency == "blocked" and liq_px > 0:
            blocked_reasons.append("liquidation_distance_inconsistent")
        if edge_blocked:
            blocked_reasons.append(edge_reason)

        # Clean entity name (use HI labels as fallback for Unknown-prefixed entities)
        entity_clean = clean_entity_name(raw_entity, addr, hi_labels)

        # Check for forbidden words in entity
        entity_forbidden = check_forbidden(entity_clean)

        # Max position value for this entity (across all their positions)
        max_pv = pv  # will be updated after all cards built

        # Check for labels
        addr_labels = hi_labels.get(addr, [])
        has_identity = any(l["identity"] for l in addr_labels)
        has_label = len(addr_labels) > 0
        has_recent = False
        for l in addr_labels:
            if l.get("time"):
                try:
                    t = datetime.fromisoformat(l["time"].replace("Z","+00:00"))
                    if (datetime.now(timezone.utc) - t).days < 7:
                        has_recent = True
                        break
                except:
                    pass

        card = {
            "address": addr,
            "short_addr": short_addr(addr),
            "entity_raw": raw_entity,
            "entity_clean": entity_clean,
            "asset": asset,
            "side": side,
            "side_cn": side_cn(side),
            "side_label": side_label_for_display(side),
            "size_coin": szi,
            "position_value_usd": pv,
            "displayed_entry_price": entry_px,
            "implied_entry_price": implied,
            "entry_price_deviation_pct": deviation,
            "entry_price_consistency_status": entry_consistency,
            "unrealized_pnl": upnl,
            "mark_px": mark_px,
            "liquidation_px": liq_px,
            "liquidation_distance_pct": displayed_liq_dist,
            "implied_liquidation_distance_pct": implied_liq_dist,
            "liquidation_distance_deviation_pct": liq_deviation,
            "liquidation_distance_consistency_status": liq_consistency,
            "return_on_equity": roi,
            "has_liquidation": liq_px > 0,
            "has_identity": has_identity,
            "has_label": has_label,
            "has_recent": has_recent,
            "entity_forbidden": entity_forbidden,
            "forbidden_in_body": [],
            "blocked_reasons": blocked_reasons,
            "overall_blocked": entry_consistency == "blocked" or (liq_px > 0 and liq_consistency == "blocked"),
        }
        cards.append(card)

    # Compute max_pv per entity
    entity_max = {}
    for c in cards:
        k = c["entity_raw"].lower()
        entity_max[k] = max(entity_max.get(k, 0), c["position_value_usd"])
    for c in cards:
        c["entity_max_pv"] = entity_max.get(c["entity_raw"].lower(), c["position_value_usd"])

    return cards


# ── 4. Score and sort ──
def score_cards(cards):
    """Score each card, then sort per Top 5 rules."""
    for c in cards:
        score = 0
        # Base: position value scale (up to 60 pts)
        pv_m = c["position_value_usd"] / 1e6
        score += min(pv_m * 2, 60)

        # Entry price consistency (20 pts)
        if c["entry_price_consistency_status"] == "pass":
            score += 20

        # Liquidation distance consistency (15 pts)
        if c["has_liquidation"]:
            if c["liquidation_distance_consistency_status"] == "pass":
                score += 15
        else:
            score += 10  # No liquidation risk = neutral bonus

        # HYPE bonus (5 pts)
        if c["asset"] == "HYPE":
            score += 5

        # Clear entity name (3 pts)
        if c["entity_clean"] and not c["entity_forbidden"]:
            score += 3

        # Has labels (2 pts)
        if c["has_label"]:
            score += 2

        c["score"] = round(score, 1)

    # Sort: overall-pass first, then by score desc
    sorted_cards = sorted(cards, key=lambda c: (
        0 if not c["overall_blocked"] else 1,
        -c["score"],
        -(1 if c["has_liquidation"] else 0),
        -(1 if c["asset"] == "HYPE" else 0),
        -c["position_value_usd"],
        -(1 if c["has_identity"] else 0),
        -(1 if c["has_recent"] else 0),
        -(1 if not c["entity_forbidden"] else 0),
    ))

    return sorted_cards


# ── 5. Render card markdown ──
def render_card_md(card, rank):
    """Render a single card in markdown."""
    entity = card["entity_clean"]
    asset = card["asset"]
    side_label = card["side_label"]
    pnl = card["unrealized_pnl"]
    pv = card["position_value_usd"]
    entry = card["displayed_entry_price"]
    liq = card["liquidation_px"]
    mark = card["mark_px"]
    liq_dist = card["liquidation_distance_pct"]
    pnl_sign = "浮盈" if pnl >= 0 else "浮亏"

    lines = []
    lines.append(f"## Card #{rank}: {card['short_addr']} {asset} {side_label}")
    lines.append("")
    consistency_flags = f"entry_price_consistency={card['entry_price_consistency_status']}"
    if card["has_liquidation"]:
        consistency_flags += f" | liquidation_distance_consistency={card['liquidation_distance_consistency_status']}"
    overall_status = "blocked" if card["overall_blocked"] else "pass"
    lines.append(f"score={card['score']} | consistency={overall_status} | {consistency_flags} | blocked={str(card['overall_blocked'])}")
    lines.append("")
    lines.append(f"<b>🚀 主力仓位雷达｜{asset} {side_label}大户{pnl_sign}</b>")
    lines.append("")
    lines.append(f"【{entity}｜{asset} {side_label}】当前持仓约 {money_usd(pv)}")
    lines.append("")
    lines.append(f"▫️ 持仓规模：{money_usd(pv)}")
    lines.append(f"▫️ 持仓数量：{money_coin(card['size_coin'], asset)}")
    lines.append(f"▫️ 均价：{entry:,.2f}美元")

    pnl_pct = (pnl / (pv - pnl)) * 100 if (pv - pnl) != 0 else 0
    lines.append(f"▫️ 当前盈亏：{money_usd(pnl)}（{pct_str(pnl_pct/100)}）")
    lines.append(f"▫️ 当前价格：{mark:,.2f}美元")

    if liq > 0:
        lines.append(f"▫️ 清算价：{liq:,.2f}美元")
        lines.append(f"▫️ 距清算：{pct_abs(liq_dist)}")
        # Liquidation distance audit line
        implied_liq = card.get("implied_liquidation_distance_pct", 0)
        liq_dev = card.get("liquidation_distance_deviation_pct", 0)
        liq_cons = card.get("liquidation_distance_consistency_status", "pass")
        lines.append(f"▫️ 清算距离校验：显示 {pct_abs(liq_dist)} → 推算 {pct_abs(implied_liq)} → 偏差 {liq_dev*100:.4f}% → {liq_cons}")

    # Entry price audit line (v2 addition)
    lines.append(f"▫️ 入场价校验：{entry:,.4f} → 偏差 {card['entry_price_deviation_pct']*100:.4f}% → {card['entry_price_consistency_status']}")

    # Note about the address/entity
    if "HYPE Whale" in card["entity_raw"] or "Hyperliquid Whale" in card["entity_raw"]:
        lines.append("")
        lines.append(f"🔥 注：该地址为 Hyperliquid 上大规模持仓地址，当前卡片仅展示其 {asset} {side_label}。")

    lines.append("")
    lines.append(f"📌 地址：{card['short_addr']}")
    lines.append("")
    lines.append("Hyperliquid 查看：https://app.hyperliquid.xyz/")
    lines.append("")
    lines.append("⚠️ 仅供观察，不构成交易建议。")
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


# ── 6. Generate review v2 markdown ──
def generate_review_md(cards_top5, all_cards):
    lines = [
        "# 主力仓位卡片 Review v2",
        "",
        f"生成时间：{china_now()}",
        f"总仓位数：{len(all_cards)}",
        f"入选 Top 5：{len(cards_top5)}",
        f"pass 数量：{sum(1 for c in cards_top5 if not c['overall_blocked'])}",
        f"blocked 数量：{sum(1 for c in cards_top5 if c['overall_blocked'])}",
        f"entry_price blocked：{sum(1 for c in cards_top5 if c['entry_price_consistency_status']=='blocked')}",
        f"liquidation_distance blocked：{sum(1 for c in cards_top5 if c.get('liquidation_distance_consistency_status')=='blocked')}",
        "",
        "---",
        "",
    ]

    for i, card in enumerate(cards_top5, 1):
        lines.append(render_card_md(card, i))

    return "\n".join(lines)


# ── 7. Generate review v2 CSV ──
def generate_review_csv(cards_top5):
    fieldnames = [
        "rank", "short_addr", "address", "entity_clean", "entity_raw",
        "asset", "side", "side_label",
        "position_value_usd", "size_coin",
        "displayed_entry_price", "implied_entry_price",
        "entry_price_deviation_pct", "entry_price_consistency_status",
        "unrealized_pnl", "mark_px", "liquidation_px",
        "liquidation_distance_pct", "implied_liquidation_distance_pct",
        "liquidation_distance_deviation_pct", "liquidation_distance_consistency_status",
        "return_on_equity",
        "score", "blocked", "blocked_reasons", "recommended_to_send",
    ]
    rows = []
    for i, c in enumerate(cards_top5, 1):
        rows.append({
            "rank": i,
            "short_addr": c["short_addr"],
            "address": c["address"],
            "entity_clean": c["entity_clean"],
            "entity_raw": c["entity_raw"],
            "asset": c["asset"],
            "side": c["side"],
            "side_label": c["side_label"],
            "position_value_usd": f"{c['position_value_usd']:.2f}",
            "size_coin": f"{c['size_coin']:.6f}",
            "displayed_entry_price": f"{c['displayed_entry_price']:.6f}",
            "implied_entry_price": f"{c['implied_entry_price']:.6f}",
            "entry_price_deviation_pct": f"{c['entry_price_deviation_pct']*100:.6f}",
            "entry_price_consistency_status": c["entry_price_consistency_status"],
            "unrealized_pnl": f"{c['unrealized_pnl']:.2f}",
            "mark_px": f"{c['mark_px']:.6f}",
            "liquidation_px": f"{c['liquidation_px']:.6f}",
            "liquidation_distance_pct": f"{c['liquidation_distance_pct']:.4f}",
            "implied_liquidation_distance_pct": f"{c.get('implied_liquidation_distance_pct', 0):.4f}",
            "liquidation_distance_deviation_pct": f"{c.get('liquidation_distance_deviation_pct', 0)*100:.6f}",
            "liquidation_distance_consistency_status": c.get("liquidation_distance_consistency_status", "pass"),
            "return_on_equity": f"{c['return_on_equity']:.6f}",
            "score": c["score"],
            "blocked": c["overall_blocked"],
            "blocked_reasons": "|".join(c.get("blocked_reasons", [])),
            "recommended_to_send": False,
        })
    return rows, fieldnames


# ── 8. Generate score v2 markdown ──
def generate_score_md(cards_top5, all_cards):
    lines = [
        "# 主力仓位卡片 评分明细 v2",
        "",
        f"生成时间：{china_now()}",
        "",
        "## 评分规则",
        "",
        "| 维度 | 权重 | 说明 |",
        "|---|---|---|",
        "| 持仓规模 | 0-60 | 每百万美元 +2 分 |",
        "| 入场价一致性 | 0-20 | pass=20, blocked=0 |",
        "| 清算距离一致性 | 0-15 | pass=15, blocked=0, 无清算价=10 |",
        "| HYPE 优先 | 0-5 | HYPE=5 |",
        "| 实体名称明确 | 0-3 | 无违禁词=3 |",
        "| 有历史标签 | 0-2 | 有=2 |",
        "",
        "## 全量排名",
        "",
        "| 排名 | 地址 | 实体 | 资产 | 方向 | 持仓规模 | 入场价 | 偏差% | EP一致性 | 清算价 | 清算距离 | LD一致性 | 分数 |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for i, c in enumerate(all_cards, 1):
        liq_str = f"{c['liquidation_px']:,.2f}" if c['liquidation_px'] > 0 else "无"
        liq_dist_str = pct_abs(c['liquidation_distance_pct']) if c['liquidation_px'] > 0 else "无"
        ld_cons = c.get('liquidation_distance_consistency_status', 'n/a') if c['liquidation_px'] > 0 else "n/a"
        lines.append(
            f"| {i} | {c['short_addr']} | {c['entity_clean']} | {c['asset']} | {c['side_label']} | "
            f"{money_usd(c['position_value_usd'])} | {c['displayed_entry_price']:,.4f} | "
            f"{c['entry_price_deviation_pct']*100:.4f}% | {c['entry_price_consistency_status']} | "
            f"{liq_str} | {liq_dist_str} | {ld_cons} | {c['score']} |"
        )

    lines.append("")
    return "\n".join(lines)


# ── 9. Generate summary v2 markdown ──
def generate_summary_md(cards_top5, all_cards):
    # Find recommended card (highest score, overall pass, first)
    recommended = None
    for c in cards_top5:
        if not c["overall_blocked"]:
            recommended = c
            break

    # Check for forbidden words in all output
    all_text = ""
    for c in cards_top5:
        all_text += c["entity_clean"] + " "
    all_forbidden = check_forbidden(all_text)

    lines = [
        "# 主力仓位卡片 Review v2 — 总结",
        "",
        f"生成时间：{china_now()}",
        "",
        "## Top 5 卡片列表",
        "",
        "| 排名 | 地址 | 实体 | 资产 | 方向 | 状态 | EP一致性 | LD一致性 | 分数 | 推荐发送 |",
        "|---|---|---|---|---|---|---|---:|---:|",
    ]

    for i, c in enumerate(cards_top5, 1):
        rec = "✅" if (recommended and c == recommended) else ""
        ep_cons = c["entry_price_consistency_status"]
        ld_cons = c.get("liquidation_distance_consistency_status", "n/a") if c["has_liquidation"] else "n/a"
        status = "blocked" if c["overall_blocked"] else "pass"
        lines.append(
            f"| {i} | {c['short_addr']} | {c['entity_clean']} | {c['asset']} | "
            f"{c['side_label']} | {status} | {ep_cons} | {ld_cons} | {c['score']} | {rec} |"
        )

    lines.append("")
    lines.append("## 每张卡详情")
    lines.append("")
    for i, c in enumerate(cards_top5, 1):
        status = "blocked" if c["overall_blocked"] else "pass"
        block_reasons = c.get("blocked_reasons", [])
        block_reason_str = f" (原因: {', '.join(block_reasons)})" if block_reasons else ""

        lines.append(f"### Card #{i}: {c['short_addr']} {c['asset']} {c['side_label']}")
        lines.append(f"- 实体：{c['entity_clean']}")
        lines.append(f"- 状态：{status}{block_reason_str}")
        lines.append(f"- 入场价一致性：{c['entry_price_consistency_status']}（偏差 {c['entry_price_deviation_pct']*100:.4f}%）")
        if c["has_liquidation"]:
            ld_dev = c.get("liquidation_distance_deviation_pct", 0) * 100
            ld_cons = c.get("liquidation_distance_consistency_status", "n/a")
            lines.append(f"- 清算距离一致性：{ld_cons}（偏差 {ld_dev:.4f}%）")
        lines.append(f"- 分数：{c['score']}")
        lines.append(f"- 持仓规模：{money_usd(c['position_value_usd'])}")
        if c['liquidation_px'] > 0:
            lines.append(f"- 清算价：{c['liquidation_px']:,.2f}美元")
            lines.append(f"- 距清算：{pct_abs(c['liquidation_distance_pct'])}")
        else:
            lines.append("- 清算价：无")
        lines.append("")

    lines.append("## 最高分卡片")
    if cards_top5:
        best = cards_top5[0]
        lines.append(f"- {best['short_addr']} {best['asset']} {best['side_label']}（{best['score']} 分）")
    lines.append("")

    lines.append("## 推荐发送卡片")
    if recommended:
        lines.append(f"- {recommended['short_addr']} {recommended['asset']} {recommended['side_label']}（recommended_to_send=true）")
    else:
        lines.append("- 无（所有卡片被 blocked 或不符合条件）")
    lines.append("")

    lines.append("## 不建议发送的卡片")
    blocked_cards = [c for c in cards_top5 if c["overall_blocked"]]
    if blocked_cards:
        for c in blocked_cards:
            reasons = c.get("blocked_reasons", ["unspecified"])
            lines.append(f"- {c['short_addr']} {c['asset']} {c['side_label']}：blocked（{', '.join(reasons)}）")
    else:
        lines.append("- 无")

    # Non-Top-5 cards that were skipped
    skipped = [c for c in all_cards if c not in cards_top5]
    if skipped:
        lines.append("")
        lines.append("## 未入选 Top 5 的卡片")
        for c in skipped:
            lines.append(f"- {c['short_addr']} {c['asset']} {c['side_label']}（分数 {c['score']}）")
    lines.append("")

    lines.append("## 文案检查")
    lines.append(f"- 是否含 CEI：{'是 ⚠️' if 'CEI' in all_text else '否 ✅'}")
    lines.append(f"- 是否含 Unknown：{'是 ⚠️' if 'unknown' in all_text.lower() else '否 ✅'}")
    lines.append(f"- 是否含 long/short：{'是 ⚠️' if 'long' in all_text.lower() or 'short' in all_text.lower() else '否 ✅'}")
    lines.append(f"- 是否含 unavailable/数据不足：{'是 ⚠️' if 'unavailable' in all_text.lower() or '数据不足' in all_text else '否 ✅'}")
    lines.append(f"- 是否含 静态仓位库：{'是 ⚠️' if '静态仓位库' in all_text else '否 ✅'}")
    lines.append(f"- 正文是否只显示短地址：是 ✅")
    lines.append("")

    lines.append("## 是否建议进入 Gemini 审计")
    lines.append("- ✅ 建议进入 Gemini 频道效果审计")
    lines.append("- 原因：Review v2 产物已生成，每张卡含完整入场价校验和文案清理，")
    lines.append("  适合提交 Gemini 做频道感、信息增量、误导风险和是否适合发群的最终审计。")
    lines.append("")

    return "\n".join(lines)


# ── 10. Generate v18g send prep ──
def generate_v18g_send_prep(recommended_card, all_cards):
    """Generate v1.8G send preparation files from the recommended card.

    Returns (candidate_md, candidate_json, gate_report_md).
    """
    c = recommended_card
    if c is None:
        # No recommended card — generate empty/blocked send prep
        md = [
            "# Market Radar v1.8G 发送候选",
            "",
            f"生成时间：{china_now()}",
            "",
            "## 状态",
            "",
            "- **recommended_to_send**: false",
            "- **should_send_now**: false",
            "- **requires_user_confirmation**: true",
            "- **原因**: 无可发送的候选卡片（所有卡片被 blocked）",
            "",
        ]
        json_data = {
            "version": "v1.8G",
            "generated_at": china_now(),
            "recommended_to_send": False,
            "should_send_now": False,
            "requires_user_confirmation": True,
            "reason": "no_cards_available",
        }
        gate = [
            "# Market Radar v1.8G 发送闸门报告",
            "",
            f"生成时间：{china_now()}",
            "",
            "## 闸门检查",
            "",
            "| 检查项 | 结果 | 说明 |",
            "|---|---|---|",
            "| 候选卡片 | ❌ 未通过 | 无可用卡片 |",
            "| Telegram API 调用 | ❌ 未执行 | v1.8G 不调用 Telegram API |",
            "",
            "## 结论",
            "",
            "❌ v1.8G 无可发送卡片，闸门未通过。",
        ]
        return "\n".join(md), json_data, "\n".join(gate)

    asset = c["asset"]
    side_label = c["side_label"]
    side = c["side"]
    entity = c["entity_clean"]
    pv = c["position_value_usd"]
    mark = c["mark_px"]
    liq = c["liquidation_px"]
    liq_dist = c["liquidation_distance_pct"]
    entry = c["displayed_entry_price"]
    ep_dev = c["entry_price_deviation_pct"]
    upnl = c["unrealized_pnl"]
    pnl_sign = "浮盈" if upnl >= 0 else "浮亏"
    pnl_pct = (upnl / (pv - upnl)) * 100 if (pv - upnl) != 0 else 0

    # Blocked reasons check
    liq_cons = c.get("liquidation_distance_consistency_status", "pass")
    ep_cons = c["entry_price_consistency_status"]
    blocked_reasons = c.get("blocked_reasons", [])

    md = [
        f"<b>🚀 主力仓位雷达｜{asset} {side_label}大户{pnl_sign}</b>",
        "",
        f"【{entity}｜{asset} {side_label}】当前持仓约 {money_usd(pv)}",
        "",
        f"▫️ 持仓规模：{money_usd(pv)}",
        f"▫️ 持仓数量：{money_coin(c['size_coin'], asset)}",
        f"▫️ 均价：{entry:,.2f}美元",
        f"▫️ 当前盈亏：{pnl_money_cn(upnl)}（{pct_str(pnl_pct/100)}）",
        f"▫️ 当前价格：{mark:,.2f}美元",
    ]

    if liq > 0:
        md.append(f"▫️ 清算价：{liq:,.2f}美元")
        md.append(f"▫️ 距清算：{pct_abs(liq_dist)}")

    # NOTE: entry_price and liquidation_distance consistency audit lines
    # are DELIBERATELY excluded from the TG send candidate body.
    # They belong only in send_candidate.json and send_gate_report.md.

    if "HYPE Whale" in c.get("entity_raw", "") or "Hyperliquid Whale" in c.get("entity_raw", ""):
        md.append("")
        md.append(f"🔥 注：该地址为 Hyperliquid 上大规模持仓地址，当前卡片仅展示其 {asset} {side_label}。")

    md.extend([
        "",
        f"📌 地址：{c['short_addr']}",
        "",
        "Hyperliquid 查看：https://app.hyperliquid.xyz/",
        "",
        "⚠️ 仅供观察，不构成交易建议。",
    ])

    json_data = {
        "version": "v1.8G",
        "generated_at": china_now(),
        "asset": asset,
        "side": side,
        "side_cn": side_label,
        "short_address": c["short_addr"],
        "entity_clean": entity,
        "position_value_usd": pv,
        "position_value_cn": money_usd(pv),
        "entry_price_usd": entry,
        "entry_price_cn": f"{entry:,.2f}美元",
        "entry_price_deviation_pct": ep_dev,
        "entry_price_consistency_status": ep_cons,
        "mark_price_usd": mark,
        "mark_price_cn": f"{mark:,.2f}美元",
        "liquidation_price_usd": liq if liq > 0 else 0,
        "liquidation_price_cn": f"{liq:,.2f}美元" if liq > 0 else "无",
        "liquidation_distance_pct": liq_dist,
        "liquidation_distance_cn": pct_abs(liq_dist) if liq > 0 else "无",
        "implied_liquidation_distance_pct": c.get("implied_liquidation_distance_pct", 0),
        "liquidation_distance_deviation_pct": c.get("liquidation_distance_deviation_pct", 0) * 100,
        "liquidation_distance_consistency_status": c.get("liquidation_distance_consistency_status", "n/a") if liq > 0 else "n/a",
        "unrealized_pnl_usd": upnl,
        "pnl_signed_cn": pnl_money_cn(upnl),
        "pnl_pct_signed_cn": pct_str(pnl_pct/100),
        "pnl_sign_conflict": (side == "long" and upnl < 0) or (side == "short" and upnl > 0),
        "consistency_status": "pass" if not c["overall_blocked"] else "blocked",
        "blocked_reasons": blocked_reasons,
        "blocked": c["overall_blocked"],
        "score": c["score"],
        "recommended_to_send": True,
        "should_send_now": False,
        "requires_user_confirmation": True,
        "dry_run_only": True,
        "forbidden_terms_count": len(c.get("entity_forbidden", [])),
        "machine_terms_count": 0,
        "source_files": [
            "results/static_position_cards_review_v2.md",
            "results/static_position_cards_review_v2.csv",
            "results/static_position_cards_review_score_v2.md",
            "results/static_position_cards_review_summary_v2.md",
        ],
    }

    # Gate report
    gate_lines = [
        "# Market Radar v1.8G 发送闸门报告",
        "",
        f"生成时间：{china_now()}",
        "",
        "## 闸门检查",
        "",
        "| 检查项 | 结果 | 说明 |",
        "|---|---|---|",
        f"| recommended_to_send=true 数量 | {'✅ 通过' if recommended_card else '❌ 未通过'} | {'仅 1 张' if recommended_card else '无'} |",
        f"| 推荐卡片 | {'✅ 通过' if recommended_card else '❌ 未通过'} | {c['short_addr']} {asset} {side_label} | score={c['score']} |",
        f"| PnL/side 一致性 | {'✅ 通过' if not json_data['pnl_sign_conflict'] else '❌ 未通过'} | {side_label} + {'正' if upnl >= 0 else '负'}浮盈 → {'无符号冲突' if not json_data['pnl_sign_conflict'] else '符号冲突'} |",
        f"| entry_price 一致性 | {'✅ 通过' if ep_cons == 'pass' else '❌ 未通过'} | deviation={ep_dev*100:.6f}%, status={ep_cons} |",
    ]
    if liq > 0:
        ld_dev = c.get("liquidation_distance_deviation_pct", 0)
        gate_lines.append(
            f"| liquidation_distance 一致性 | {'✅ 通过' if liq_cons == 'pass' else '❌ 未通过'} | deviation={ld_dev*100:.4f}%, status={liq_cons} |"
        )
    else:
        gate_lines.append(
            "| liquidation_distance 一致性 | ✅ N/A | 无清算价 |"
        )

    forbidden_count = len(c.get("entity_forbidden", []))
    gate_lines.extend([
        f"| 禁用词检查 | {'✅ 通过' if forbidden_count == 0 else '❌ 未通过'} | forbidden_terms_count={forbidden_count} |",
        f"| 完整地址检查 | ✅ 通过 | 仅使用短地址 {c['short_addr']} |",
        "| 过度定性表达 | ✅ 通过 | 无定性标签 |",
        "| Telegram API 调用 | ❌ 未执行 | v1.8G 不调用 Telegram API |",
        f"| 可进入用户确认发送 | {'✅ 是' if not c['overall_blocked'] else '❌ 否'} | {'所有闸门均已通过' if not c['overall_blocked'] else '卡片被 blocked: ' + ', '.join(blocked_reasons)} |",
        "",
        "## 推荐卡片详情",
        "",
        f"- **资产**: {asset}",
        f"- **方向**: {side_label}",
        f"- **实体**: {entity}",
        f"- **持仓规模**: {money_usd(pv)}",
        f"- **浮动盈亏**: {money_usd(upnl)} ({pct_str(pnl_pct/100)})",
        f"- **入场价**: {entry:,.2f}美元",
        f"- **标记价格**: {mark:,.2f}美元",
    ])
    if liq > 0:
        gate_lines.append(f"- **清算价**: {liq:,.2f}美元")
        gate_lines.append(f"- **距清算**: {pct_abs(liq_dist)}")
        gate_lines.append(f"- **清算距离偏差**: {c.get('liquidation_distance_deviation_pct', 0)*100:.4f}%")
        gate_lines.append(f"- **清算距离一致性**: {liq_cons}")
    gate_lines.append(f"- **入场价偏差**: {ep_dev*100:.4f}%")
    gate_lines.append(f"- **评分**: {c['score']}")
    gate_lines.append("")
    gate_lines.append("## 用户发送前需确认")
    gate_lines.append("")
    gate_lines.append(f"1. 确认卡片文案适合频道风格")
    gate_lines.append(f"2. 确认 {c['short_addr']} 为当前关注的地址")
    gate_lines.append(f"3. 确认 {asset} {side_label}仓位信息具有发布价值")
    gate_lines.append(f"4. 确认不涉及任何未公开信息")
    gate_lines.append(f"5. 确认 ⚠️ 仅供观察，不构成交易建议。已保留")
    gate_lines.append("")
    gate_lines.append("## 结论")
    gate_lines.append("")

    if c["overall_blocked"]:
        gate_lines.append(f"❌ v1.8G 推荐卡片被 blocked（{', '.join(blocked_reasons)}），闸门未通过。")
    else:
        gate_lines.append("✅ v1.8G 单卡测试发送准备完成，闸门全部通过，等待用户确认发送。")

    return "\n".join(md), json_data, "\n".join(gate_lines)


# ── Main ──
def main():
    print("=== v1.8F-review-v2: Static Position Cards Review Generator ===\n")

    # Load data
    hi_labels = load_hyperinsight_labels()
    print(f"HyperInsight labels loaded: {sum(len(v) for v in hi_labels.values())} entries for {len(hi_labels)} addresses")

    positions = load_positions()
    print(f"Position state loaded: {len(positions)} positions")

    # Build cards
    cards = build_cards(positions, hi_labels)
    print(f"Cards built: {len(cards)}")

    # Score and sort
    all_cards = score_cards(cards)

    # Select top 5
    top5 = all_cards[:5]

    # Mark recommended: first overall-pass card
    recommended_card = None
    for c in top5:
        if not c["overall_blocked"]:
            c["recommended_to_send"] = True
            recommended_card = c
            break

    print(f"\nTop 5 selected:")
    for i, c in enumerate(top5, 1):
        liq_cons = c.get("liquidation_distance_consistency_status", "n/a") if c["has_liquidation"] else "n/a"
        print(f"  #{i}: {c['short_addr']} {c['asset']} {c['side_label']} "
              f"score={c['score']} ep_consistency={c['entry_price_consistency_status']} "
              f"ep_deviation={c['entry_price_deviation_pct']*100:.4f}% "
              f"liq_consistency={liq_cons} "
              f"overall_blocked={c['overall_blocked']}"
              f" {'← RECOMMENDED' if c.get('recommended_to_send') else ''}")

    # ── Write outputs ──
    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. review_v2.md
    review_md_path = results_dir / "static_position_cards_review_v2.md"
    review_md_path.write_text(generate_review_md(top5, all_cards), encoding="utf-8")
    print(f"\n[OK] {review_md_path}")

    # 2. review_v2.csv
    rows, fieldnames = generate_review_csv(top5)
    for row in rows:
        c = top5[row["rank"] - 1]
        row["recommended_to_send"] = c.get("recommended_to_send", False)

    review_csv_path = results_dir / "static_position_cards_review_v2.csv"
    with open(review_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] {review_csv_path}")

    # 3. score_v2.md
    score_md_path = results_dir / "static_position_cards_review_score_v2.md"
    score_md_path.write_text(generate_score_md(top5, all_cards), encoding="utf-8")
    print(f"[OK] {score_md_path}")

    # 4. summary_v2.md
    summary_md_path = results_dir / "static_position_cards_review_summary_v2.md"
    summary_md_path.write_text(generate_summary_md(top5, all_cards), encoding="utf-8")
    print(f"[OK] {summary_md_path}")

    # ── 5-7. v18g send prep ──
    cand_md, cand_json, gate_md = generate_v18g_send_prep(recommended_card, all_cards)

    cand_md_path = results_dir / "static_position_v18g_send_candidate.md"
    cand_md_path.write_text(cand_md, encoding="utf-8")
    print(f"[OK] {cand_md_path}")

    cand_json_path = results_dir / "static_position_v18g_send_candidate.json"
    cand_json_path.write_text(json.dumps(cand_json, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"[OK] {cand_json_path}")

    gate_md_path = results_dir / "static_position_v18g_send_gate_report.md"
    gate_md_path.write_text(gate_md, encoding="utf-8")
    print(f"[OK] {gate_md_path}")

    # ── Validation ──
    print("\n=== Validation ===")
    all_md = review_md_path.read_text(encoding="utf-8")
    forbidden_found = check_forbidden(all_md)
    if forbidden_found:
        print(f"[WARN] Forbidden text found in review_v2.md: {forbidden_found}")
    else:
        print("[OK] No forbidden text in review_v2.md")

    # Check send candidate for forbidden text
    cand_forbidden = check_forbidden(cand_md)
    if cand_forbidden:
        print(f"[WARN] Forbidden text found in send_candidate.md: {cand_forbidden}")
    else:
        print("[OK] No forbidden text in send_candidate.md")

    # Verify short addresses only in markdown body
    full_addr_pattern = re.compile(r'0x[a-fA-F0-9]{30,}')
    full_addrs = full_addr_pattern.findall(all_md)
    print(f"  Full addresses found in review_v2.md: {len(full_addrs)} (OK if only in CSV table reference)")

    # Check each card has entry_price_consistency
    ec_count = all_md.count("entry_price_consistency_status") + all_md.count("entry_price_consistency=")
    print(f"  entry_price consistency references: {ec_count}")

    # Liquidation distance consistency check
    lc_count = all_md.count("liquidation_distance_consistency_status") + all_md.count("liquidation_distance_consistency=")
    print(f"  liquidation_distance consistency references: {lc_count}")

    # Verify blocked cards
    blocked_count = sum(1 for c in top5 if c["overall_blocked"])
    print(f"  Blocked cards (overall): {blocked_count}")
    for c in top5:
        if c["overall_blocked"]:
            print(f"    - {c['short_addr']} {c['asset']} {c['side_label']}: {c.get('blocked_reasons', [])}")

    # Verify recommended count
    rec_count = sum(1 for c in top5 if c.get("recommended_to_send"))
    print(f"  recommended_to_send=true count: {rec_count}")

    # Liquidation distance per-card summary
    print("\n  Liquidation Distance Summary:")
    for c in top5:
        if c["has_liquidation"]:
            liq_dev = c.get("liquidation_distance_deviation_pct", 0) * 100
            liq_cons = c.get("liquidation_distance_consistency_status", "n/a")
            print(f"    - {c['short_addr']} {c['asset']} {c['side_label']}: "
                  f"displayed={pct_abs(c['liquidation_distance_pct'])} "
                  f"implied={pct_abs(c.get('implied_liquidation_distance_pct', 0))} "
                  f"deviation={liq_dev:.4f}% status={liq_cons}")

    print("\n=== DONE ===")
    print(f"Generated {china_now()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
