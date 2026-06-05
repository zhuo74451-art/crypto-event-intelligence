"""Market Radar v1.12-F — Whale Position Local Enrichment Runner

Main runner for whale_position_alert local enrichment pipeline.
Loads fixtures, processes all position events through the v112f adapter,
and produces result JSON, Markdown report, and handoff documents.

Pipeline:
  1. Load address labels fixture
  2. Load whale position sequence fixture
  3. Process each position through normalize → enrich → classify → validate → render
  4. Aggregate results: valid signals, blocked signals, public cards
  5. Run unified debug/secret leak check across all public cards
  6. Write result JSON, Markdown report, handoff

Constraints (all verified):
  - NO real TG send
  - NO external API calls
  - NO external AI calls
  - NO daemon / loop / cron
  - NO token / key / password read or saved
  - NO file deletion
  - NO full wallet addresses in public cards

Outputs:
  - results/market_radar_v112f_whale_position_local_enrichment_result.json
  - runs/market_radar/v112f_whale_position_local_enrichment.md
  - runs/market_radar/v112f_whale_position_local_enrichment_handoff.md

Usage:
    python scripts/run_market_radar_v112f_whale_position_local_enrichment.py
"""

from __future__ import annotations

import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_whale_position_feed_v112f import (
    VERSION,
    MODE,
    load_address_labels,
    load_whale_positions,
    normalize_whale_position,
    enrich_wallet_label,
    calculate_position_delta,
    classify_alert_type,
    decide_valid_blocked,
    render_whale_public_card,
    check_secrets_and_debug,
    process_whale_position,
    WhalePositionEvent,
    WhaleAddressLabel,
    VALID_ALERT_TYPES,
    VALID_ENTITY_TYPES,
    WHALE_POSITION_SIZE_THRESHOLD,
    WHALE_POSITION_DELTA_THRESHOLD,
    WHALE_LEVERAGE_THRESHOLD,
    WHALE_UNREALIZED_LOSS_THRESHOLD,
)

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = "20260604_202718"

# ── Paths ─────────────────────────────────────────────────────────────────────────

LABELS_PATH = ROOT / "data" / "fixtures" / "market_radar_v112f_whale_address_labels.json"
POSITIONS_PATH = ROOT / "data" / "fixtures" / "market_radar_v112f_whale_positions.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112f_whale_position_local_enrichment_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112f_whale_position_local_enrichment.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112f_whale_position_local_enrichment_handoff.md"


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _safe_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "").replace(",", "").replace("+", "").strip()
        if not s:
            return default
        try:
            return float(s)
        except (ValueError, TypeError):
            return default
    return default


def _fmt_money(value):
    v = abs(value)
    sign = "-" if value < 0 else ""
    if v >= 1_000_000_000:
        return f"{sign}${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{sign}${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}${v/1_000:.2f}K"
    if v < 0.01 and v > 0:
        return f"{sign}${v:.6f}"
    return f"{sign}${v:,.2f}"


# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"=== Market Radar {VERSION} — Whale Position Local Enrichment Runner ===")
    print(f"Mode: {MODE}")
    print(f"Run: {china_stamp()}")
    print(f"Run ID: {RUN_ID}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL API: NONE")
    print(f"EXTERNAL AI: NONE")
    print(f"PAID API: NONE")
    print(f"DAEMON: NONE")
    print()

    # ── Step 1: Load address labels ────────────────────────────────────────────
    print("[1/5] Loading whale address labels...")
    if LABELS_PATH.exists():
        labels = load_address_labels(str(LABELS_PATH))
        print(f"  Loaded {len(labels)} address labels from {LABELS_PATH.name}")
    else:
        labels = []
        print(f"  [WARN] No address labels fixture found at {LABELS_PATH}")
    print()

    # ── Step 2: Load whale position sequence ───────────────────────────────────
    print("[2/5] Loading whale position sequence...")
    if POSITIONS_PATH.exists():
        raw_positions = load_whale_positions(str(POSITIONS_PATH))
        print(f"  Loaded {len(raw_positions)} whale positions from {POSITIONS_PATH.name}")
    else:
        raw_positions = []
        print(f"  [WARN] No whale positions fixture found at {POSITIONS_PATH}")
    print()

    # ── Step 3: Process all positions ──────────────────────────────────────────
    print("[3/5] Processing whale positions through v112f enrichment pipeline...")

    position_results: list[dict] = []
    valid_signals: list[dict] = []
    blocked_signals: list[dict] = []
    public_cards: list[str] = []
    all_debug_leaks: list[str] = []
    all_secret_leaks: list[str] = []

    for i, raw in enumerate(raw_positions):
        result = process_whale_position(raw, labels)
        position_results.append(result)

        status = "VALID" if result["valid"] else "BLOCKED"
        print(f"  [{i+1}/{len(raw_positions)}] {result['event_id']}: {status} "
              f"({result['alert_type']}, {_fmt_money(result['position_size_usd'])}, "
              f"label={result['label'][:25] if result['label'] else 'N/A'})")

        if result["valid"]:
            valid_signals.append(result)

        if result["blocked"]:
            blocked_signals.append(result)

        if result["public_card"]:
            public_cards.append(result["public_card"])

        all_debug_leaks.extend(result["debug_leak_terms"])
        all_secret_leaks.extend(result["secret_leak_terms"])

    print()
    print(f"  Summary: {len(valid_signals)} valid, {len(blocked_signals)} blocked, "
          f"{len(public_cards)} public cards")
    print()

    # ── Step 4: Aggregate results ──────────────────────────────────────────────
    print("[4/5] Aggregating results and checking leaks...")

    total_debug_leaks = len(set(all_debug_leaks))
    total_secret_leaks = len(set(all_secret_leaks))

    # Check for full wallet addresses in any public card
    full_wallet_in_public = False
    for card in public_cards:
        matches = re.findall(r'0x[a-fA-F0-9]{40}', card)
        if matches:
            full_wallet_in_public = True
            total_secret_leaks += 1
            print(f"  [WARN] Full wallet address found in public card!")

    print(f"  Debug leaks: {total_debug_leaks}")
    print(f"  Secret leaks: {total_secret_leaks}")
    print(f"  Full wallet in public: {full_wallet_in_public}")
    print()

    # ── Step 5: Write outputs ──────────────────────────────────────────────────
    print("[5/5] Writing result JSON, report, and handoff...")

    # Build result
    result = {
        "version": VERSION,
        "mode": MODE,
        "run_id": RUN_ID,
        "task_id": "market_radar_v112f_whale_position_local_enrichment",
        "generated_at": china_stamp(),
        "address_labels_loaded": len(labels),
        "positions_loaded": len(raw_positions),
        "positions_processed": len(position_results),
        "valid_signal_count": len(valid_signals),
        "blocked_signal_count": len(blocked_signals),
        "public_card_count": len(public_cards),
        "debug_leak_count": total_debug_leaks,
        "secret_leak_count": total_secret_leaks,
        "full_wallet_in_public_card": full_wallet_in_public,
        "fallback_preview": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "alert_types_found": list(set(r["alert_type"] for r in position_results)),
        "entity_types_found": list(set(r["entity_type"] for r in position_results if r["entity_type"])),
        "position_results": position_results,
        "public_cards": public_cards,
        "validation_thresholds": {
            "position_size_usd_min": WHALE_POSITION_SIZE_THRESHOLD,
            "position_delta_usd_min": WHALE_POSITION_DELTA_THRESHOLD,
            "leverage_min": WHALE_LEVERAGE_THRESHOLD,
            "unrealized_loss_max": WHALE_UNREALIZED_LOSS_THRESHOLD,
        },
        "wallet_short_form_used": True,
        "notes": [
            "All data is from local fixtures — no live chain data used.",
            "All wallet addresses are synthetic — no real private keys.",
            "Public cards use short wallet form (0x7a9f...b8c) — no full addresses.",
            "TG send disabled — real_tg_sent=false.",
            "No external API calls made.",
            "No external AI calls made.",
            "No daemon/loop/cron started.",
            "No tokens/keys/cookies/passwords read or saved.",
            "No files deleted.",
            f"Whale position alert now has {len(public_cards)} real public previews from local enrichment.",
            "fallback_preview=false — whale position alert no longer depends on fallback preview.",
        ],
    }

    # Write result JSON
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    # Write Markdown report
    write_markdown_report(result, position_results, valid_signals, blocked_signals, public_cards)
    print(f"  [OK] {REPORT_MD_PATH}")

    # Write handoff
    write_handoff(result, position_results, valid_signals, blocked_signals)
    print(f"  [OK] {HANDOFF_MD_PATH}")

    print()
    print(f"{'=' * 70}")
    print(f"v1.12-F Whale Position Local Enrichment — Complete")
    print(f"{'=' * 70}")
    print(f"  Valid signals:    {len(valid_signals)}")
    print(f"  Blocked signals:  {len(blocked_signals)}")
    print(f"  Public cards:     {len(public_cards)}")
    print(f"  Debug leaks:      {total_debug_leaks}")
    print(f"  Secret leaks:     {total_secret_leaks}")
    print(f"  TG send:          NONE")
    print(f"  External API:     NONE")
    print(f"  External AI:      NONE")
    print(f"  Daemon/Loop:      NONE")
    print(f"  Live ready:       FALSE")
    print(f"  Fallback preview: FALSE")
    print(f"{'=' * 70}")

    return 0


# ══════════════════════════════════════════════════════════════════════════════════════
# Report Writers
# ══════════════════════════════════════════════════════════════════════════════════════

def write_markdown_report(
    result: dict,
    position_results: list[dict],
    valid_signals: list[dict],
    blocked_signals: list[dict],
    public_cards: list[str],
) -> None:
    """Write the v1.12-F Markdown report."""
    lines = [
        f"# Market Radar v1.12-F — Whale Position Local Enrichment Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Mode**: {MODE}",
        f"**Run ID**: {RUN_ID}",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告证明 `whale_position_alert` 已从 fallback preview 推进到真实 local public preview。",
        f"通过 v112f 本地适配层，实现了地址标签富集、历史仓位序列追踪、仓位变化计算、",
        f"警报类型分类、valid/blocked 判定和公共卡片渲染。",
        f"",
        f"所有数据来自本地 fixture，未调用外部 API、未发送 TG、未启动 daemon。",
        f"",
        f"## 核心指标",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 地址标签数量 | {result['address_labels_loaded']} |",
        f"| 仓位样本数量 | {result['positions_loaded']} |",
        f"| 有效信号数 | {result['valid_signal_count']} |",
        f"| 阻止信号数 | {result['blocked_signal_count']} |",
        f"| 公共卡片数 | {result['public_card_count']} |",
        f"| Debug 泄露数 | {result['debug_leak_count']} |",
        f"| Secret 泄露数 | {result['secret_leak_count']} |",
        f"| Fallback Preview | {result['fallback_preview']} |",
        f"| Live Ready | {result['live_ready']} |",
        f"",
        f"---",
        f"",
        f"## 地址标签覆盖",
        f"",
        f"| 钱包短码 | 标签 | 实体类型 | 置信度 |",
        f"|----------|------|----------|--------|",
    ]

    for r in position_results:
        label = r.get("label", "")[:30]
        entity = r.get("entity_type", "")
        conf = r.get("label_confidence", "")
        wallet_short = r.get("wallet_short", "--")
        if wallet_short:
            lines.append(f"| `{wallet_short}` | {label} | {entity} | {conf} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 有效信号 ({len(valid_signals)})",
        f"",
        f"| # | Event ID | Asset | Side | Size | Leverage | Alert Type | Delta |",
        f"|---|----------|-------|------|------|----------|------------|-------|",
    ])

    for i, v in enumerate(valid_signals, 1):
        side_cn = "多" if v["side"] == "long" else "空" if v["side"] == "short" else v["side"]
        at_display = {
            "position_opened": "新开", "position_increased": "加仓",
            "position_reduced": "减仓", "high_leverage_risk": "高杠杆风险",
            "large_unrealized_loss": "大额浮亏", "unknown": "未知",
        }.get(v["alert_type"], v["alert_type"])
        delta_str = f"+{_fmt_money(v['position_delta_usd'])}" if v['position_delta_usd'] > 0 else _fmt_money(v['position_delta_usd'])
        lines.append(
            f"| {i} | {v['event_id'][:35]} | {v['asset']} | {side_cn} | "
            f"{_fmt_money(v['position_size_usd'])} | {v['leverage']:.0f}x | {at_display} | {delta_str} |"
        )

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 阻止信号 ({len(blocked_signals)})",
        f"",
        f"| # | Event ID | Block Reason |",
        f"|---|----------|-------------|",
    ])

    for i, b in enumerate(blocked_signals, 1):
        reason_cn = {
            "missing_wallet": "缺少钱包地址",
            "missing_asset": "缺少资产",
            "position_size_too_small": "仓位金额太小",
            "below_whale_threshold": "未达巨鲸阈值",
        }.get(b["block_reason"], b["block_reason"])
        lines.append(f"| {i} | {b['event_id'][:40]} | {reason_cn} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 公共卡片预览",
        f"",
    ])

    for i, card in enumerate(public_cards, 1):
        lines.extend([
            f"### 卡片 {i}",
            f"",
            f"```",
            card[:600],
            f"```",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| fallback_preview | {result['fallback_preview']} |",
        f"| real_tg_sent | {result['real_tg_sent']} |",
        f"| external_api_called | {result['external_api_called']} |",
        f"| external_ai_called | {result['external_ai_called']} |",
        f"| daemon_started | {result['daemon_started']} |",
        f"| live_ready | {result['live_ready']} |",
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| full_wallet_in_public | {result['full_wallet_in_public_card']} |",
        f"| token/key/cookie read | false |",
        f"| files_deleted | false |",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_handoff(
    result: dict,
    position_results: list[dict],
    valid_signals: list[dict],
    blocked_signals: list[dict],
) -> None:
    """Write the v1.12-F handoff markdown."""
    lines = [
        f"# Market Radar v1.12-F — Whale Position Local Enrichment Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Mode**: {MODE}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: market_radar_v112f_whale_position_local_enrichment",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `data/fixtures/market_radar_v112f_whale_address_labels.json` | 新增 | 6 个地址标签 fixture |",
        f"| `data/fixtures/market_radar_v112f_whale_positions.json` | 新增 | 8 条仓位序列 fixture（4 valid + 2 blocked + 2 control） |",
        f"| `scripts/market_radar_whale_position_feed_v112f.py` | 新增 | v112f 本地适配层 |",
        f"| `scripts/run_market_radar_v112f_whale_position_local_enrichment.py` | 新增 | v112f runner |",
        f"| `scripts/test_market_radar_whale_position_feed_v112f.py` | 新增 | v112f 单元测试 |",
        f"| `results/market_radar_v112f_whale_position_local_enrichment_result.json` | 新增 | v112f 结果 JSON |",
        f"| `runs/market_radar/v112f_whale_position_local_enrichment.md` | 新增 | v112f Markdown 报告 |",
        f"| `runs/market_radar/v112f_whale_position_local_enrichment_handoff.md` | 新增 | v112f Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统",
        f"python scripts/run_market_radar_v112f_whale_position_local_enrichment.py",
        f"python scripts/test_market_radar_whale_position_feed_v112f.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 核心结果",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 有效信号 | {len(valid_signals)} |",
        f"| 阻止信号 | {len(blocked_signals)} |",
        f"| 公共卡片 | {result['public_card_count']} |",
        f"| Debug 泄露 | {result['debug_leak_count']} |",
        f"| Secret 泄露 | {result['secret_leak_count']} |",
        f"| Fallback Preview | {result['fallback_preview']} |",
        f"",
        f"### 警报类型分布",
        f"",
    ]

    alert_counts: dict[str, int] = {}
    for r in position_results:
        at = r["alert_type"]
        alert_counts[at] = alert_counts.get(at, 0) + 1

    for at, count in sorted(alert_counts.items()):
        at_display = {
            "position_opened": "新开仓位",
            "position_increased": "加仓",
            "position_reduced": "减仓",
            "high_leverage_risk": "高杠杆风险",
            "large_unrealized_loss": "大额浮亏",
            "unknown": "未知",
        }.get(at, at)
        lines.append(f"- **{at_display}** (`{at}`): {count}")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| fallback_preview | {result['fallback_preview']} |",
        f"| real_tg_sent | {result['real_tg_sent']} |",
        f"| external_api_called | {result['external_api_called']} |",
        f"| external_ai_called | {result['external_ai_called']} |",
        f"| daemon_started | {result['daemon_started']} |",
        f"| live_ready | {result['live_ready']} |",
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| token/key/cookie read | false |",
        f"| files_deleted | false |",
        f"",
        f"---",
        f"",
        f"## whale_position_alert 状态",
        f"",
        f"- **Readiness**: partial（不变 — 仍缺 live data source）",
        f"- **Fallback Preview**: false（现已由 v112f 本地 enrichment 产出真实 public preview）",
        f"- **Public Preview**: {result['public_card_count']} 张",
        f"- **Address Labels**: {result['address_labels_loaded']} 个地址已标注",
        f"- **Historical Sequence**: {result['positions_loaded']} 条仓位序列可用",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. v112f 本地 enrichment 已验证可行，下一步可接入 v112e unified pipeline",
        f"2. 补齐更多地址标签类型（market_maker, mev_bot, arbitrageur 等）",
        f"3. 增加历史仓位序列深度（同一地址跨月/跨季度追踪）",
        f"4. 接入 Hyperliquid live API 后可直接替换 fixture data source",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
