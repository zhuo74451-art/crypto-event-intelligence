import argparse
import csv
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


EVENT_TYPE_LABELS = {
    "whale_position": "链上巨鲸",
    "institutional_flow": "机构资金",
    "exchange_listing": "交易所动态",
    "hack_security": "安全事件",
    "regulation_macro": "监管宏观",
    "macro": "宏观事件",
    "token_unlock": "代币解锁",
    "network_upgrade": "网络升级",
    "staking_governance": "质押治理",
    "onchain_data": "链上数据",
    "stablecoin_flow": "稳定币流动",
    "project_business": "项目进展",
    "legal_enforcement": "执法合规",
    "other": "事件观察",
    "other_review": "事件观察",
}

EVENT_HEADLINES = {
    "whale_position": "大额仓位信号",
    "institutional_flow": "资金流动信号",
    "exchange_listing": "交易所事件",
    "hack_security": "安全风险信号",
    "regulation_macro": "政策/宏观信号",
    "macro": "宏观信号",
    "token_unlock": "供应变化信号",
    "network_upgrade": "网络升级信号",
    "staking_governance": "治理/质押信号",
    "onchain_data": "链上数据变化",
    "stablecoin_flow": "稳定币流动信号",
    "project_business": "项目进展信号",
    "legal_enforcement": "执法合规信号",
}

ROUTE_LABELS = {
    "alpha_candidate": "重点观察",
    "macro_policy": "宏观/政策观察",
    "research_only": "研究记录",
    "unsupported_research": "研究记录",
    "review_queue": "待复核",
}

SCOPE_LABELS = {
    "single_asset": "单资产",
    "multi_asset": "多资产",
    "market_wide": "全市场",
    "unknown": "待确认",
}

CONFIDENCE_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate local Telegram-style draft messages without sending anything."
    )
    parser.add_argument("--input", default="data/event_candidates_v06_clean_low_risk_preview.csv")
    parser.add_argument("--output", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--markdown-output", default="results/tg_drafts_v06_private_pilot.md")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--mode", default="private_pilot", choices=["private_pilot", "review_queue"])
    return parser.parse_args()


def value(row: dict, *names: str) -> str:
    for name in names:
        item = str(row.get(name, "") or "").strip()
        if item:
            return item
    return ""


def clamp_text(text: str, max_len: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", str(text or "")).strip()


def looks_truncated_title(title: str) -> bool:
    title = " ".join(str(title or "").split()).strip()
    if not title:
        return False
    return title.lower().endswith(
        (
            " with",
            " and",
            " to",
            " for",
            " of",
            " in",
            " at",
            " using",
            "allocating",
            "manag",
            "secto",
        )
    )


def first_content_line(content: str) -> str:
    for line in str(content or "").splitlines():
        line = " ".join(line.split()).strip()
        if line and not line.startswith("http"):
            return line
    return ""


def display_title(row: dict) -> str:
    title = value(row, "title")
    content = value(row, "content")
    if looks_truncated_title(title):
        line = first_content_line(content)
        if len(line) > len(title):
            return line
    return title


def normalized_event_type(row: dict) -> str:
    return value(row, "manual_event_type_l1", "event_type_l1", "candidate_event_type", "event_type") or "other"


def effective_asset(row: dict) -> str:
    return value(
        row,
        "manual_primary_asset_symbol",
        "effective_asset_symbol",
        "primary_asset_symbol",
        "candidate_asset_symbol",
        "asset_symbol",
    )


def confidence_label(row: dict) -> str:
    raw = value(row, "relevance_score_realtime", "auto_label_confidence", "auto_quality_score")
    try:
        score = float(raw)
    except ValueError:
        return "medium"
    if score > 1:
        score = score / 100.0
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


def strength_stars(row: dict) -> str:
    raw = value(row, "candidate_importance", "importance")
    try:
        stars = int(float(raw))
    except ValueError:
        score_raw = value(row, "relevance_score_realtime", "auto_quality_score")
        try:
            score = float(score_raw)
        except ValueError:
            stars = 3
        else:
            if score <= 1:
                score *= 100
            stars = 5 if score >= 85 else 4 if score >= 70 else 3 if score >= 50 else 2
    stars = max(1, min(5, stars))
    return "★" * stars + "☆" * (5 - stars)


def should_include(row: dict) -> bool:
    if value(row, "auto_publish").lower() in {"true", "1", "yes"}:
        return False
    decision = value(row, "manual_decision", "publish_decision", "suggested_review_decision").lower()
    if decision in {"discard", "exclude", "reject"}:
        return False
    if value(row, "quality_status").lower() == "fail":
        return False
    route = value(row, "manual_channel_route", "channel_route")
    if route in {"discard", "trash"}:
        return False
    return bool(effective_asset(row) and value(row, "title"))


def extract_amount_hint(text: str) -> str:
    patterns = [
        r"\$\d[\d,.]*\s?(?:B|M|K|b|m|k|million|billion)?",
        r"\d[\d,.]*\s?(?:BTC|ETH|USDT|USDC|SOL|HYPE|AAVE|ONDO)",
        r"[\d,.]+\s?(?:万美元|亿美元|万枚|枚)",
    ]
    hits = []
    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            cleaned = " ".join(str(match).split())
            if cleaned and cleaned not in hits:
                hits.append(cleaned)
            if len(hits) >= 3:
                break
        if len(hits) >= 3:
            break
    return " / ".join(hits)


def has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))


def clean_english_noise(text: str) -> str:
    text = strip_urls(text)
    text = re.sub(r"^[🔥⚡🚨\s]*(BULLISH|UPDATE|JUST IN):\s*", "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()


def display_china_time(value_text: str) -> str:
    raw = str(value_text or "").strip()
    if not raw:
        return "待确认"

    normalized = re.sub(r"\s*(UTC\+8|GMT\+8|CST|北京时间)\s*$", "", raw, flags=re.IGNORECASE).strip()
    iso_text = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    try:
        dt = datetime.fromisoformat(iso_text)
    except ValueError:
        return normalized

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return normalized


def chinese_event_title(row: dict, asset: str, event_type: str, raw_title: str) -> str:
    title = clean_english_noise(raw_title)
    content = clean_english_noise(value(row, "content"))
    text = f"{title}\n{content}"
    if has_chinese(title):
        return title

    lower = text.lower()
    amount_hint = extract_amount_hint(text)

    if event_type == "whale_position":
        name_match = re.search(r"whale\s+([A-Za-z0-9_.@()-]+)", title, flags=re.IGNORECASE)
        name = name_match.group(1) if name_match else "巨鲸地址"
        direction = "空头" if "short" in lower else "多头" if "long" in lower else "仓位"
        leverage_match = re.search(r"\((\d+x)\)", title, flags=re.IGNORECASE)
        leverage = f"{leverage_match.group(1)} " if leverage_match else ""
        return f"巨鲸 {name} 继续增加 {asset} {leverage}{direction}仓位，规模约 {amount_hint or '待确认'}"

    if "white house" in lower and "bitcoin reserve" in lower:
        return "白宫比特币储备相关公告临近"

    if "pro-bitcoin" in lower and "federal reserve chair" in lower:
        return "亲比特币立场的 Kevin Warsh 将宣誓就任美联储主席"

    if "ethereum etf net flow" in lower:
        flow = amount_hint or "待确认"
        return f"以太坊 ETF 出现净流变化，规模约 {flow}"

    if "bitwise" in lower and "hype" in lower and "balance sheet" in lower:
        pct = re.search(r"(\d+(?:\.\d+)?%)", title)
        pct_text = pct.group(1) if pct else "部分"
        return f"Bitwise 将把 {pct_text} Hyperliquid ETF 管理费用于持有 HYPE"

    if "solana" in lower and "rwa" in lower and "crossed" in lower:
        return f"Solana RWA 市场规模突破 {amount_hint or '新高'}"

    if "tokenized stocks" in lower and "ondo" in lower:
        return f"Ondo Finance 代币化股票 TVL 突破 {amount_hint or '新高'}"

    if event_type in {"regulation_macro", "macro"}:
        return f"{asset} 相关宏观/政策事件出现，需结合市场环境观察"
    if event_type == "institutional_flow":
        return f"{asset} 出现机构/资金流相关事件，规模约 {amount_hint or '待确认'}"
    if event_type == "onchain_data":
        return f"{asset} 出现链上数据变化，规模约 {amount_hint or '待确认'}"
    return f"{asset} 出现{EVENT_TYPE_LABELS.get(event_type, '事件')}相关信号，需结合原文复核"


def entity_hint(row: dict, asset: str) -> str:
    flags = value(row, "entity_flags")
    if flags:
        parts = [p for p in re.split(r"[,;|]", flags) if p.strip()]
        if parts:
            return clamp_text(parts[0], 36)
    source = value(row, "source")
    source_lower = source.lower()
    if (
        source
        and source_lower not in {"webhook", "unknown"}
        and not source_lower.startswith(("news:", "feed:", "tg:", "telegram:"))
    ):
        return source
    return asset


def event_interpretation(event_type: str, route: str, title: str) -> str:
    lowered = title.lower()
    if event_type == "whale_position":
        return "大额地址或巨鲸仓位出现变化，属于需要优先观察的链上/合约结构信号；重点看是否持续加仓、减仓或触发清算压力。"
    if event_type == "institutional_flow":
        return "机构、ETF 或资金账户出现流入/流出变化，反映资金侧边际变化；需要结合连续性和后续公告确认。"
    if event_type == "hack_security":
        return "安全事件会直接影响信任、流动性和相关资产风险，需要关注损失规模、资金去向和官方处置。"
    if event_type in {"regulation_macro", "macro"}:
        return "宏观/监管事件通常影响全市场风险偏好，单条消息不宜直接归因到单一资产，需要结合市场环境观察。"
    if event_type == "exchange_listing":
        return "交易所上新/下架会改变资产可交易性和流动性，重点看交易所级别、交易对和生效时间。"
    if event_type == "token_unlock":
        return "代币解锁属于供应侧变化，需要关注释放规模、接收方和是否进入交易所。"
    if event_type == "network_upgrade":
        return "网络升级影响协议能力、生态预期或技术风险，重点看是否按时上线和是否出现异常。"
    if event_type == "staking_governance":
        return "质押/治理变化反映参与度或规则调整，需要结合提案影响范围和资金规模判断。"
    if event_type == "onchain_data":
        return "链上数据变化是结构性观察信号，重点看是否持续、是否伴随资金流或价格波动。"
    if event_type == "stablecoin_flow":
        return "稳定币流动反映链上流动性变化，重点看后续是否进入交易所、DeFi 或出现连续同向流动。"
    if "rwa" in lowered or "tvl" in lowered:
        return "业务指标出现变化，属于项目基本面观察信号；需要看是否有连续增长和真实资金支撑。"
    if route == "research_only":
        return "该事件更适合作为研究线索，暂不直接视为市场异动，需要等待更多事实确认。"
    return "该事件属于加密市场情报观察项，重点看后续是否出现资金流、官方确认或二次传播。"


def review_need(row: dict, route: str, confidence: str) -> tuple[str, str]:
    if route in {"research_only", "unsupported_research"}:
        return "需要", "研究型或价格源受限事件，进入发布前需复核"
    if confidence == "low":
        return "需要", "置信度偏低，需要复核实体、资产和时间"
    if value(row, "asset_attribution_risk") in {"high", "medium"}:
        return "需要", "资产归因存在风险，需要复核主资产"
    return "建议", "发布前建议快速扫一眼事实和措辞"


def build_draft(row: dict, sequence: int, mode: str) -> dict:
    candidate_id = value(row, "candidate_id", "event_id", "raw_id") or f"draft_{sequence:04d}"
    asset = effective_asset(row)
    event_type = normalized_event_type(row)
    event_type_label = EVENT_TYPE_LABELS.get(event_type, "事件观察")
    headline = EVENT_HEADLINES.get(event_type, "重点情报信号")
    route = value(row, "manual_channel_route", "channel_route") or "review_queue"
    route_label = ROUTE_LABELS.get(route, route)
    scope = value(row, "event_scope") or "unknown"
    scope_label = SCOPE_LABELS.get(scope, scope)
    confidence = confidence_label(row)
    confidence_cn = CONFIDENCE_LABELS.get(confidence, "中")
    published_china = display_china_time(value(row, "published_at_china", "backtest_time_china", "event_time_china", "published_at"))
    source = value(row, "source") or "unknown"
    url = value(row, "url")
    raw_title = clamp_text(strip_urls(display_title(row)), 220)
    title = clamp_text(chinese_event_title(row, asset, event_type, raw_title), 180)
    content = strip_urls(value(row, "content"))
    amount_hint = extract_amount_hint(f"{title}\n{content}") or "未提取到明确金额"
    entity = entity_hint(row, asset)
    review, review_reason = review_need(row, route, confidence)
    notes = value(row, "manual_notes", "review_notes", "asset_attribution_explanation")

    lines = [
        f"<b>⚡【{event_type_label}】{asset} {headline}</b>",
        "━━━━━━━━━━━━━━",
        f"📌 事件：{title}",
        f"🕒 北京时间：{published_china}",
        f"🏷️ 主体：{entity}",
        f"🔎 类型：{event_type_label} / {scope_label}",
        f"💰 规模：{amount_hint}",
        f"🔥 强度：{strength_stars(row)}",
        f"✅ 置信：{confidence_cn}",
        f"📍 路由：{route_label}",
        "",
        f"🧠 解读：{event_interpretation(event_type, route, title)}",
        "",
        f"🧾 复核：{review}",
        f"原因：{review_reason}",
    ]
    if notes:
        lines.append(f"备注：{clamp_text(notes, 90)}")
    if url:
        lines.extend(["🔗 来源：", url])
    lines.extend(["", "⚠️ 仅作事件情报与研究观察，不构成任何交易建议。"])

    return {
        "draft_id": f"tg_{sequence:04d}",
        "candidate_id": candidate_id,
        "published_at_china": published_china,
        "asset_symbol": asset,
        "event_type": event_type,
        "event_type_label": event_type_label,
        "event_scope": scope,
        "channel_route": route,
        "confidence_label": confidence,
        "strength_stars": strength_stars(row),
        "source": source,
        "title": title,
        "url": url,
        "draft_text": "\n".join(lines),
        "draft_status": "pending_review",
        "reviewer_decision": "",
        "reviewer_usefulness": "",
        "reviewer_issue_type": "",
        "reviewer_notes": "",
        "approved_text": "",
        "draft_mode": mode,
        "auto_send_enabled": "false",
    }


def write_markdown(path: Path, rows: list[dict]) -> None:
    lines = [
        "# TG Draft Preview",
        "",
        "These are local draft messages only. No Telegram API is called and nothing is sent automatically.",
        "",
        f"- draft_count: {len(rows)}",
        "- auto_send_enabled: false",
        "",
    ]
    for row in rows:
        lines.extend([f"## {row['draft_id']} / {row['candidate_id']}", "", "```text", row["draft_text"], "```", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def read_existing_review_state(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))
    except Exception:
        return {}
    by_candidate = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id", "") or "").strip()
        if candidate_id:
            by_candidate[candidate_id] = row
    return by_candidate


def preserve_review_fields(rows: list[dict], existing: dict[str, dict]) -> list[dict]:
    review_fields = [
        "draft_status",
        "reviewer_decision",
        "reviewer_usefulness",
        "reviewer_issue_type",
        "reviewer_notes",
        "approved_text",
    ]
    for row in rows:
        previous = existing.get(row["candidate_id"])
        if not previous:
            continue
        for field in review_fields:
            old_value = str(previous.get(field, "") or "").strip()
            if old_value:
                row[field] = old_value
    return rows


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    markdown_path = Path(args.markdown_output)

    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8-sig", newline="")))
    selected = []
    for row in rows:
        if should_include(row):
            selected.append(build_draft(row, len(selected) + 1, args.mode))
        if args.limit and len(selected) >= args.limit:
            break

    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected = preserve_review_fields(selected, read_existing_review_state(output_path))
    fieldnames = [
        "draft_id",
        "candidate_id",
        "published_at_china",
        "asset_symbol",
        "event_type",
        "event_type_label",
        "event_scope",
        "channel_route",
        "confidence_label",
        "strength_stars",
        "source",
        "title",
        "url",
        "draft_text",
        "draft_status",
        "reviewer_decision",
        "reviewer_usefulness",
        "reviewer_issue_type",
        "reviewer_notes",
        "approved_text",
        "draft_mode",
        "auto_send_enabled",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)
    write_markdown(markdown_path, selected)
    print(f"input_rows={len(rows)}")
    print(f"draft_count={len(selected)}")
    print(f"wrote_csv={output_path}")
    print(f"wrote_markdown={markdown_path}")


if __name__ == "__main__":
    main()
