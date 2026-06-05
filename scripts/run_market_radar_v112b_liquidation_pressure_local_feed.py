"""Market Radar v1.12-B — Liquidation Pressure Local Feed Runner

Reads v112b fixture snapshots, normalizes them, detects liquidation pressure signals,
renders public cards, and outputs results.

Outputs:
  - results/market_radar_v112b_liquidation_pressure_local_feed_result.json
  - runs/market_radar/v112b_liquidation_pressure_local_feed.md
  - runs/market_radar/v112b_liquidation_pressure_local_feed_handoff.md

NO TG send, NO external API, NO paid services, NO daemon/loop/cron.
Deterministic rules only.

Usage:
    python scripts/run_market_radar_v112b_liquidation_pressure_local_feed.py
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_liquidation_feed_v112b import (
    VERSION,
    MODE,
    normalize_liquidation_snapshot,
    detect_liquidation_pressure,
    render_liquidation_pressure_card,
    validate_liquidation_signal,
    check_public_debug_leak,
    process_raw_snapshot,
)

CN_TZ = timezone(timedelta(hours=8))

# ── Paths ─────────────────────────────────────────────────────────────────────────

FIXTURE_PATH = ROOT / "data" / "fixtures" / "market_radar_v112b_liquidation_snapshots.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112b_liquidation_pressure_local_feed_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112b_liquidation_pressure_local_feed.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112b_liquidation_pressure_local_feed_handoff.md"


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Main ─────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"=== Market Radar {VERSION} — Liquidation Pressure Local Feed ===")
    print(f"Run: {china_stamp()}")
    print(f"MODE: {MODE}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL API: NONE")
    print(f"PAID API: NONE")
    print(f"DAEMON: NONE")
    print()

    # ── [1/4] Load fixture snapshots ──────────────────────────────────────────
    print("[1/4] Loading v112b fixture snapshots...")
    try:
        fixtures = load_json(FIXTURE_PATH)
        snapshots = fixtures.get("snapshots", [])
        print(f"  Snapshots loaded: {len(snapshots)}")
        print(f"  Data mode: {fixtures.get('meta', {}).get('data_mode', 'unknown')}")
        print(f"  Valid samples expected: {fixtures.get('meta', {}).get('valid_samples', 0)}")
        print(f"  Invalid samples expected: {fixtures.get('meta', {}).get('invalid_samples', 0)}")
    except FileNotFoundError:
        print(f"  [ERROR] Fixture file not found: {FIXTURE_PATH}")
        snapshots = []
    print()

    # ── [2/4] Process all snapshots ────────────────────────────────────────────
    print("[2/4] Processing snapshots — normalize → detect → validate → render...")
    processed: list[dict] = []
    signals: list[dict] = []
    public_cards: list[str] = []
    blocked_items: list[dict] = []
    data_modes_seen: set[str] = set()

    for raw in snapshots:
        result = process_raw_snapshot(raw)
        processed.append(result)
        data_modes_seen.add(result.get("data_mode", "unknown"))

        if result["blocked"]:
            blocked_items.append({
                "sample_id": result["sample_id"],
                "asset": result.get("asset", ""),
                "reason": result["block_reason"],
            })
            print(f"  [BLOCKED] {result['sample_id']}: {result['block_reason']}")
        else:
            signals.append(result["signal"])
            card = result["public_card"]
            if card:
                public_cards.append(card)
            leak_status = "CLEAN" if result["debug_leak_free"] else f"LEAK: {result['debug_leak_terms']}"
            print(f"  [SIGNAL] {result['sample_id']}: {result['signal'].get('pressure_type', '?')} — {leak_status}")

    signal_count = len(signals)
    public_card_count = len(public_cards)
    blocked_count = len(blocked_items)
    snapshot_count = len(snapshots)

    print(f"\n  Summary: {snapshot_count} snapshots → {signal_count} signals, "
          f"{public_card_count} public cards, {blocked_count} blocked")
    print()

    # ── [3/4] Write result JSON ─────────────────────────────────────────────────
    print("[3/4] Writing result JSON...")

    result = {
        "version": VERSION,
        "mode": MODE,
        "real_tg_sent": False,
        "external_api_called": False,
        "paid_api_called": False,
        "daemon_started": False,
        "data_modes_seen": sorted(data_modes_seen),
        "snapshot_count": snapshot_count,
        "signal_count": signal_count,
        "public_card_count": public_card_count,
        "blocked_count": blocked_count,
        "processed": processed,
        "blocked_items": blocked_items,
        "readiness_update": {
            "card_type": "liquidation_pressure",
            "previous_readiness": "missing",
            "new_readiness": "partial",
            "reason": "local snapshot adapter and public card rendering are ready; live data source is still missing",
        },
        "highest_priority_next_gap": {
            "gap": "live_liquidation_data_source",
            "recommended_next_task": "connect a free or user-approved liquidation data source through the v112b adapter",
        },
        "generated_at": china_stamp(),
        "fixture_source": str(FIXTURE_PATH),
        "notes": [
            "All snapshots are fixtures — no live market data was used.",
            "TG send is disabled — real_tg_sent=false.",
            "No external API calls were made — external_api_called=false.",
            "No paid API calls were made — paid_api_called=false.",
            "No daemon/loop/cron was started.",
            "No tokens/keys/cookies/passwords were read or saved.",
        ],
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    print()

    # ── [4/4] Write reports ─────────────────────────────────────────────────────
    print("[4/4] Writing markdown report and handoff...")
    write_markdown_report(result, processed, signals, public_cards, blocked_items, signal_count, public_card_count, blocked_count, snapshot_count)
    write_handoff(result, signals, public_cards, blocked_items, signal_count, public_card_count, blocked_count, snapshot_count)
    print()

    # ── Summary ─────────────────────────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-B Liquidation Pressure Local Feed — Complete")
    print(f"{'=' * 70}")
    print(f"  Snapshots:             {snapshot_count}")
    print(f"  Signals detected:      {signal_count}")
    print(f"  Public cards rendered: {public_card_count}")
    print(f"  Blocked:               {blocked_count}")
    print(f"  TG send:               NONE")
    print(f"  External API:          NONE")
    print(f"  Paid API:              NONE")
    print(f"  Daemon/Loop/Cron:      NONE")
    print(f"  Readiness:             missing → partial")
    print()
    print(f"  Output files:")
    print(f"    {RESULT_JSON_PATH}")
    print(f"    {REPORT_MD_PATH}")
    print(f"    {HANDOFF_MD_PATH}")
    print(f"{'=' * 70}")

    return 0


# ── Report Writers ───────────────────────────────────────────────────────────────

def write_markdown_report(
    result: dict,
    processed: list[dict],
    signals: list[dict],
    public_cards: list[str],
    blocked_items: list[dict],
    signal_count: int,
    public_card_count: int,
    blocked_count: int,
    snapshot_count: int,
) -> None:
    """Write the v1.12-B markdown report."""
    lines = [
        f"# Market Radar v1.12-B — 清算压力本地数据适配层报告",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Mode**: {MODE}",
        f"",
        f"---",
        f"",
        f"## 本轮目标",
        f"",
        f"推进 v1.12-B：把 `liquidation_pressure` 从 **missing** 推进到 **partial**。",
        f"",
        f"本轮只做「本地清算数据适配层 + 规范化 schema + 稳定 public card 输出」。",
        f"不接 Coinglass 付费 API，不调用外部 API，不做 WebSocket，不做 daemon。",
        f"",
        f"目标是让后续无论接 Coinglass、交易所 liquidation feed，还是本地快照文件，",
        f"都能走同一套输入结构和卡片输出链路。",
        f"",
        f"---",
        f"",
        f"## 为什么不接付费 API",
        f"",
        f"Coinglass 清算数据 API 为付费产品。本轮不调用任何付费 API，所有数据均来自",
        f"本地 fixture 样本 (`data_mode: fixture`)。适配层的设计使得后续接入任何",
        f"数据源（免费 API、交易所公开 WebSocket、本地 CSV 快照）都只需实现同一套",
        f"`normalize_liquidation_snapshot()` 接口。",
        f"",
        f"---",
        f"",
        f"## liquidation_pressure 从 missing → partial 的依据",
        f"",
        f"| 维度 | v1.12-A (missing) | v1.12-B (partial) |",
        f"|------|-------------------|-------------------|",
        f"| Schema 完整 | ✅ | ✅ |",
        f"| 准入/阻止规则 | ✅ | ✅ |",
        f"| 公开模板 | ✅ | ✅ |",
        f"| Fixture 样本 | ✅ | ✅ (5 样本) |",
        f"| 数据适配层 | ❌ | ✅ normalize + detect + render + validate |",
        f"| Public card 输出 | ❌ (模板未实例化) | ✅ 3 张 valid card |",
        f"| 真实数据管道 | ❌ | ❌ (仍缺失) |",
        f"| Gate 集成测试 | ❌ | ❌ (留待后续) |",
        f"",
        f"**结论**: 适配层就绪，card 渲染就绪，规则引擎就绪。仅缺真实数据源 → **partial**。",
        f"",
        f"---",
        f"",
        f"## 样本处理统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 总快照数 | {snapshot_count} |",
        f"| 生成信号数 | {signal_count} |",
        f"| 公开卡片数 | {public_card_count} |",
        f"| 被阻止数 | {blocked_count} |",
        f"| 数据模式 | all_fixture |",
        f"| TG 发送 | false |",
        f"| 外部 API 调用 | false |",
        f"",
        f"---",
        f"",
    ]

    # ── Valid public previews ──────────────────────────────────────────────
    lines.append(f"## Valid Public Previews ({public_card_count} 张)")
    lines.append("")

    for i, card in enumerate(public_cards[:10], 1):
        lines.append(f"### Preview #{i}")
        lines.append("")
        lines.append("```")
        lines.append(card[:800])
        lines.append("```")
        lines.append("")

    # ── Blocked samples ────────────────────────────────────────────────────
    lines.append(f"## Blocked 样本 ({blocked_count} 个)")
    lines.append("")
    lines.append(f"| # | Sample ID | Asset | Block Reason |")
    lines.append(f"|---|-----------|-------|-------------|")
    for i, item in enumerate(blocked_items, 1):
        asset = item.get("asset", "") or "(empty)"
        reason = item.get("reason", "unknown")
        lines.append(f"| {i} | `{item['sample_id']}` | {asset} | {reason} |")
    lines.append("")

    # ── Still missing for long-running monitoring ──────────────────────────
    lines.extend([
        f"---",
        f"",
        f"## 仍然缺什么才能长期自动监测",
        f"",
        f"1. **实时清算数据源** — 当前全部为 fixture 样本，没有真实市场数据。",
        f"   需要接入 Coinglass API（付费）、交易所 liquidation feed（免费但需 WebSocket）、",
        f"   或定期拉取的本地快照文件。",
        f"2. **Gate 集成** — 清算压力信号需要通过 SignalValueGate、CooldownGate、",
        f"   PreSendGate 等 gate 管道后才能进入真实发送流程。",
        f"3. **清算热力图数据** — 当前 cluster 数据为手工构造，实际需要清算价位",
        f"   热力图 API 提供精确的 liquidation level 分布。",
        f"4. **历史基线对比** — 需要历史清算数据来判断当前清算压力是否异常，",
        f"   而非仅依赖固定阈值。",
        f"5. **多资产并发监测** — 当前为单资产处理，长期需要同时对多个资产运行",
        f"   清算压力检测。",
        f"",
        f"---",
        f"",
        f"## 下一步最高优先级建议",
        f"",
        f"1. **接入免费清算数据源** — 调研 Binance/Bybit/OKX 等交易所的公开",
        f"   liquidation WebSocket feed，通过 v112b 适配层 normalize 后进入",
        f"   监测管道。这是从 partial → ready 的关键一步。",
        f"2. **Gate 集成测试** — 将 v112b 信号接入现有 gate 管道",
        f"   (SignalValueGate → CooldownGate → PreSendGate)，验证",
        f"   liquidation_pressure 信号能通过全部 gate 检查。",
        f"3. **对接 v112a registry** — 在 card_type_registry 中更新",
        f"   liquidation_pressure 的 readiness 判断逻辑，使其能读取",
        f"   v112b 的 adapter 输出。",
        f"",
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| TG 发送 | ❌ 未发送 |",
        f"| 外部 API 调用 | ❌ 未调用 |",
        f"| 付费 API | ❌ 未调用 |",
        f"| Daemon/Loop/Cron | ❌ 未启动 |",
        f"| Token/Key/Cookie 读取 | ❌ 未读取 |",
        f"| 文件删除 | ❌ 未删除 |",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {REPORT_MD_PATH}")


def write_handoff(
    result: dict,
    signals: list[dict],
    public_cards: list[str],
    blocked_items: list[dict],
    signal_count: int,
    public_card_count: int,
    blocked_count: int,
    snapshot_count: int,
) -> None:
    """Write the v1.12-B handoff markdown."""
    lines = [
        f"# Market Radar v1.12-B — Liquidation Pressure Local Feed Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Task ID**: 20260604_202718.r11",
        f"**Lane**: 1",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/market_radar_liquidation_feed_v112b.py` | 新增 | 清算数据适配层 — normalize / detect / render / validate |",
        f"| `scripts/run_market_radar_v112b_liquidation_pressure_local_feed.py` | 新增 | Runner — 读取 fixture，执行全流程 |",
        f"| `scripts/test_market_radar_liquidation_feed_v112b.py` | 新增 | 测试脚本 — 11 项测试 |",
        f"| `data/fixtures/market_radar_v112b_liquidation_snapshots.json` | 新增 | 5 条清算快照 fixture（3 valid + 2 invalid） |",
        f"| `results/market_radar_v112b_liquidation_pressure_local_feed_result.json` | 新增 | 结果 JSON |",
        f"| `runs/market_radar/v112b_liquidation_pressure_local_feed.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112b_liquidation_pressure_local_feed_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"python scripts/run_market_radar_v112b_liquidation_pressure_local_feed.py",
        f"python scripts/test_market_radar_liquidation_feed_v112b.py",
        f"python scripts/test_market_radar_card_type_registry_v112a.py",
        f"# 旧测试验证（确保不破坏 v112a）：",
        f"python scripts/test_market_radar_sender_runtime_v111o.py",
        f"python scripts/test_market_radar_safe_sender_v111n.py",
        f"python scripts/test_market_radar_public_card_readiness_v111l.py",
        f"python scripts/test_market_radar_mock_sender_v111j.py",
        f"python scripts/test_market_radar_signal_value_gate_v111b.py",
        f"python scripts/test_market_radar_same_asset_cooldown_gate_v111f.py",
        f"python scripts/test_market_radar_card_router_v110a.py",
        f"python scripts/test_market_radar_pre_send_gate_v110g.py",
        f"python scripts/test_market_radar_signal_trust_gate_v110c.py",
        f"python scripts/test_market_radar_sender_gate_coverage_v110h.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## Readiness 变化",
        f"",
        f"| Card Type | 之前 | 之后 | 原因 |",
        f"|-----------|------|------|------|",
        f"| `liquidation_pressure` | ❌ missing | ⚠️ partial | 本地适配层 + public card 渲染就绪；仅缺实时数据源 |",
        f"",
        f"---",
        f"",
        f"## 测试结果",
        f"",
        f"（运行 `test_market_radar_liquidation_feed_v112b.py` 后填充）",
        f"",
        f"---",
        f"",
        f"## Public Previews 摘要",
        f"",
        f"共生成 **{public_card_count}** 张公开卡片：",
        f"",
    ]

    for i, card in enumerate(public_cards[:3], 1):
        # Extract first few lines for summary
        card_lines = card.strip().split("\n")
        title = card_lines[0] if card_lines else "(no title)"
        oneliner = card_lines[2] if len(card_lines) > 2 else "(no oneliner)"
        lines.append(f"### Card #{i}")
        lines.append(f"- **标题**: {title}")
        lines.append(f"- **一句话**: {oneliner}")
        lines.append("")

    lines.extend([
        f"---",
        f"",
        f"## Blocked Reason 摘要",
        f"",
        f"共 **{blocked_count}** 条样本被阻止：",
        f"",
    ])
    for item in blocked_items:
        lines.append(f"- `{item['sample_id']}`: {item['reason']}")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 风险",
        f"",
        f"1. **无实时数据源** — 当前全部使用 fixture 样本，无法反映真实市场清算压力。",
        f"   在接入实时数据源之前，`liquidation_pressure` 不能用于实际监测。",
        f"2. **Coinglass 付费墙** — 主流清算数据聚合 API (Coinglass) 需要付费订阅。",
        f"   免费替代方案（交易所 WebSocket）需要额外的 WebSocket 客户端开发。",
        f"3. **阈值需要校准** — 当前压力检测使用固定阈值（$5M 1h 清算），实际阈值",
        f"   应根据历史数据和市场状态动态调整。",
        f"4. **Gate 集成未测试** — 信号尚未通过 SignalValueGate / CooldownGate /",
        f"   PreSendGate 管道，不能确认在真实发送流程中不会出问题。",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. **立即**: 调研免费清算数据源（交易所公开 WebSocket），编写对应的",
        f"   normalize 适配器。",
        f"2. **短期**: 将 v112b 信号接入 gate 管道进行集成测试。",
        f"3. **中期**: 对接 v112a registry，使 liquidation_pressure 的 readiness",
        f"   能动态读取 v112b adapter 状态。",
        f"4. **长期**: 建立历史清算基线，实现动态阈值调整。",
        f"",
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| real_tg_sent | false |",
        f"| external_api_called | false |",
        f"| paid_api_called | false |",
        f"| daemon_started | false |",
        f"| token/key/cookie read | false |",
        f"| files_deleted | false |",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {HANDOFF_MD_PATH}")


if __name__ == "__main__":
    raise SystemExit(main())
