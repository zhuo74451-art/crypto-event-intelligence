"""Market Radar v1.12-G — Multi-Asset Sync Local Correlation Runner

Unified entry point that:
  1. Loads v112g multi-asset snapshot fixture
  2. Processes all snapshots through the feed pipeline
  3. Aggregates results (valid/blocked, public cards, debug/secret leaks)
  4. Writes result JSON, Markdown report, and handoff document

Outputs:
  - results/market_radar_v112g_multi_asset_sync_local_correlation_result.json
  - runs/market_radar/v112g_multi_asset_sync_local_correlation.md
  - runs/market_radar/v112g_multi_asset_sync_local_correlation_handoff.md

Security:
  - NO real TG send
  - NO external API calls
  - NO external AI calls
  - NO daemon / loop / cron
  - NO token / key / password read or saved
  - NO file deletion

Usage:
    python scripts/run_market_radar_v112g_multi_asset_sync_local_correlation.py
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_multi_asset_sync_feed_v112g import (
    VERSION,
    MODE,
    load_snapshots,
    process_snapshot,
)

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = "20260604_202718"

# ── Paths ─────────────────────────────────────────────────────────────────────────

FIXTURE_PATH = ROOT / "data" / "fixtures" / "market_radar_v112g_multi_asset_snapshots.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112g_multi_asset_sync_local_correlation_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112g_multi_asset_sync_local_correlation.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112g_multi_asset_sync_local_correlation_handoff.md"


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def main() -> int:
    print(f"=== Market Radar {VERSION} — Multi-Asset Sync Local Correlation Runner ===")
    print(f"Run: {china_stamp()}")
    print(f"Run ID: {RUN_ID}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL API: NONE")
    print(f"EXTERNAL AI: NONE")
    print(f"PAID API: NONE")
    print(f"DAEMON: NONE")
    print()

    # ── Step 1: Load snapshots ─────────────────────────────────────────────────
    print("[1/6] Loading multi-asset snapshots...")
    snapshots = load_snapshots(FIXTURE_PATH)
    print(f"  Loaded: {len(snapshots)} snapshots from {FIXTURE_PATH}")
    if not snapshots:
        print("  [WARN] No snapshots found — aborting.")
        return 1
    print()

    # ── Step 2: Process each snapshot ──────────────────────────────────────────
    print("[2/6] Processing snapshots through v112g pipeline...")
    results = []
    for raw in snapshots:
        result = process_snapshot(raw)
        results.append(result)
        eid = result["event_id"]
        valid_str = "VALID" if result["valid"] else f"BLOCKED ({result['block_reason']})"
        print(f"  {eid}: {valid_str}, sync_type={result['sync_type']}, "
              f"dir_agreement={result['direction_agreement']:.2f}, "
              f"sync_score={result['sync_score']:.1f}")
    print()

    # ── Step 3: Aggregate ──────────────────────────────────────────────────────
    print("[3/6] Aggregating results...")

    valid_results = [r for r in results if r["valid"]]
    blocked_results = [r for r in results if r["blocked"]]
    public_cards = [r["public_card"] for r in valid_results if r["public_card"]]

    total_debug_leaks = sum(r["debug_leak_count"] for r in results)
    total_secret_leaks = sum(r["secret_leak_count"] for r in results)

    sync_types_found = sorted(set(r["sync_type"] for r in results))
    sectors_found = sorted(set(r.get("sector", "") for r in results))

    valid_count = len(valid_results)
    blocked_count = len(blocked_results)
    card_count = len(public_cards)
    fallback_preview = card_count < 3

    print(f"  Valid signals:   {valid_count}")
    print(f"  Blocked signals: {blocked_count}")
    print(f"  Public cards:    {card_count}")
    print(f"  Fallback preview: {fallback_preview}")
    print(f"  Debug leaks:     {total_debug_leaks}")
    print(f"  Secret leaks:    {total_secret_leaks}")
    print(f"  Sync types:      {sync_types_found}")
    print(f"  Sectors:         {sectors_found}")
    print()

    # ── Step 4: Write result JSON ──────────────────────────────────────────────
    print("[4/6] Writing result JSON...")

    v112g_result = {
        "version": VERSION,
        "mode": MODE,
        "run_id": RUN_ID,
        "task_id": "market_radar_v112g_multi_asset_sync_local_correlation",
        "generated_at": china_stamp(),
        "snapshots_loaded": len(snapshots),
        "snapshots_processed": len(results),
        "valid_signal_count": valid_count,
        "blocked_signal_count": blocked_count,
        "public_card_count": card_count,
        "fallback_preview": fallback_preview,
        "debug_leak_count": total_debug_leaks,
        "secret_leak_count": total_secret_leaks,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "sync_types_found": sync_types_found,
        "sectors_found": sectors_found,
        "results": results,
        "public_cards": public_cards,
        "multi_asset_market_sync_readiness": "partial",
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(v112g_result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    print()

    # ── Step 5: Write Markdown report ──────────────────────────────────────────
    print("[5/6] Writing Markdown report and handoff...")
    write_markdown_report(v112g_result, results, valid_results, blocked_results, public_cards)
    write_handoff(v112g_result, results)
    print()

    # ── Step 6: Print final summary ────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-G Multi-Asset Sync Local Correlation — Complete")
    print(f"{'=' * 70}")
    print(f"  Snapshots loaded:   {len(snapshots)}")
    print(f"  Valid signals:      {valid_count}")
    print(f"  Blocked signals:    {blocked_count}")
    print(f"  Public cards:       {card_count}")
    print(f"  Fallback preview:   {fallback_preview}")
    print(f"  Debug leaks:        {total_debug_leaks}")
    print(f"  Secret leaks:       {total_secret_leaks}")
    print(f"  Sync types found:   {sync_types_found}")
    print(f"  TG send:            NONE")
    print(f"  External API:       NONE")
    print(f"  External AI:        NONE")
    print(f"  Daemon/Loop/Cron:   NONE")
    print(f"  Live ready:         FALSE")
    print()
    print(f"  Output files:")
    print(f"    {RESULT_JSON_PATH}")
    print(f"    {REPORT_MD_PATH}")
    print(f"    {HANDOFF_MD_PATH}")
    print(f"{'=' * 70}")

    return 0


def write_markdown_report(
    result: dict,
    all_results: list[dict],
    valid_results: list[dict],
    blocked_results: list[dict],
    public_cards: list[str],
) -> None:
    """Write the v1.12-G Markdown report."""
    lines = [
        f"# Market Radar v1.12-G — Multi-Asset Sync Local Correlation Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告验证 v1.12-G multi-asset market sync 本地相关性适配层可：",
        f"1. 稳定读取本地 fixture 快照",
        f"2. 计算 synchronize move score（同步异动得分）",
        f"3. 计算 direction agreement（方向一致性）",
        f"4. 检测 sector / basket 类型",
        f"5. 分类 sync type（5 种已知类型 + unknown）",
        f"6. 判定 valid / blocked",
        f"7. 渲染干净的 public card（无 debug/secret 泄露）",
        f"",
        f"---",
        f"",
        f"## 执行摘要",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 加载快照数 | {result['snapshots_loaded']} |",
        f"| 处理快照数 | {result['snapshots_processed']} |",
        f"| Valid signals | {result['valid_signal_count']} |",
        f"| Blocked signals | {result['blocked_signal_count']} |",
        f"| Public cards | {result['public_card_count']} |",
        f"| Fallback preview | {result['fallback_preview']} |",
        f"| Debug leaks | {result['debug_leak_count']} |",
        f"| Secret leaks | {result['secret_leak_count']} |",
        f"| Sync types found | {', '.join(result['sync_types_found'])} |",
        f"| Sectors found | {', '.join(result['sectors_found'])} |",
        f"",
        f"---",
        f"",
        f"## Sync Types Found",
        f"",
    ]

    for st in result["sync_types_found"]:
        count = sum(1 for r in all_results if r["sync_type"] == st)
        lines.append(f"- **{st}**: {count} snapshot(s)")
    lines.append("")

    lines.extend([
        f"---",
        f"",
        f"## Valid Signals ({len(valid_results)})",
        f"",
    ])

    for r in valid_results:
        lines.extend([
            f"### {r['event_id']}",
            f"",
            f"| 字段 | 值 |",
            f"|------|-----|",
            f"| Sync Type | {r['sync_type']} |",
            f"| Direction | {r['direction']} |",
            f"| Direction Agreement | {r['direction_agreement']:.2f} |",
            f"| Sync Score | {r['sync_score']:.1f} |",
            f"| Sector | {r.get('sector', 'N/A')} |",
            f"| Primary Assets | {', '.join(r.get('primary_assets', []))} |",
            f"| Window | {r['window_minutes']} min |",
            f"| Avg Price Change | {r['avg_price_change']:+.2f}% |",
            f"| Avg Volume Change | {r['avg_volume_change']:+.1f}% |",
            f"| Avg OI Change | {r['avg_oi_change']:+.2f}% |",
            f"",
            f"**Public Card**:",
            f"```",
            r["public_card"][:600],
            f"```",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## Blocked Signals ({len(blocked_results)})",
        f"",
    ])

    for r in blocked_results:
        lines.extend([
            f"### {r['event_id']}",
            f"",
            f"- **Block Reason**: {r['block_reason']}",
            f"- **Sync Type**: {r['sync_type']}",
            f"- **Direction**: {r['direction']}",
            f"- **Direction Agreement**: {r['direction_agreement']:.2f}",
            f"- **Asset Count**: {r['asset_count']}",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| real_tg_sent | false |",
        f"| external_api_called | false |",
        f"| external_ai_called | false |",
        f"| daemon_started | false |",
        f"| live_ready | false |",
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| token/key/cookie read | false |",
        f"| files_deleted | false |",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {REPORT_MD_PATH}")


def write_handoff(result: dict, all_results: list[dict]) -> None:
    """Write the v1.12-G handoff document."""
    lines = [
        f"# Market Radar v1.12-G — Multi-Asset Sync Local Correlation Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: market_radar_v112g_multi_asset_sync_local_correlation",
        f"",
        f"---",
        f"",
        f"## 修改/新增文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/market_radar_multi_asset_sync_feed_v112g.py` | 新增 | v112g 多资产共振本地适配层 |",
        f"| `scripts/run_market_radar_v112g_multi_asset_sync_local_correlation.py` | 新增 | v112g runner |",
        f"| `scripts/test_market_radar_multi_asset_sync_feed_v112g.py` | 新增 | v112g 测试 |",
        f"| `data/fixtures/market_radar_v112g_multi_asset_snapshots.json` | 新增 | 8 组多资产快照 fixture |",
        f"| `results/market_radar_v112g_multi_asset_sync_local_correlation_result.json` | 新增 | 结果 JSON |",
        f"| `runs/market_radar/v112g_multi_asset_sync_local_correlation.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112g_multi_asset_sync_local_correlation_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统",
        f"python scripts/run_market_radar_v112g_multi_asset_sync_local_correlation.py",
        f"python scripts/test_market_radar_multi_asset_sync_feed_v112g.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 验收结果",
        f"",
        f"| 验收条件 | 结果 |",
        f"|---------|------|",
        f"| valid_signal_count >= 5 | {result['valid_signal_count']} ✅ |" if result['valid_signal_count'] >= 5 else f"| valid_signal_count >= 5 | {result['valid_signal_count']} ❌ |",
        f"| blocked_signal_count >= 3 | {result['blocked_signal_count']} ✅ |" if result['blocked_signal_count'] >= 3 else f"| blocked_signal_count >= 3 | {result['blocked_signal_count']} ❌ |",
        f"| public_card_count >= 3 | {result['public_card_count']} ✅ |" if result['public_card_count'] >= 3 else f"| public_card_count >= 3 | {result['public_card_count']} ❌ |",
        f"| fallback_preview = false | {'✅' if not result['fallback_preview'] else '❌'} |",
        f"| debug_leak_count = 0 | {'✅' if result['debug_leak_count'] == 0 else '❌ '+str(result['debug_leak_count'])} |",
        f"| secret_leak_count = 0 | {'✅' if result['secret_leak_count'] == 0 else '❌ '+str(result['secret_leak_count'])} |",
        f"| real_tg_sent = false | ✅ |",
        f"| external_api_called = false | ✅ |",
        f"| external_ai_called = false | ✅ |",
        f"| daemon_started = false | ✅ |",
        f"| live_ready = false | ✅ |",
        f"| multi_asset_market_sync readiness | partial |",
        f"",
        f"---",
        f"",
        f"## 5 种 Sync Type 覆盖",
        f"",
    ]

    for st in ["market_wide_risk_on", "market_wide_risk_off", "l2_beta_sync",
               "exchange_token_sync", "stablecoin_liquidity_stress", "unknown"]:
        count = sum(1 for r in all_results if r["sync_type"] == st)
        icon = "✅" if count > 0 else "❌"
        lines.append(f"- {icon} **{st}**: {count} snapshot(s)")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. v112g result 存在时，v112e unified pipeline 应优先读取 v112g real preview",
        f"   （不再使用 fallback preview）",
        f"2. 当前所有数据均为 fixture——接入实时行情数据源后，sync type 分类会更准确",
        f"3. 增加更多 sector/basket 模板（DeFi、Meme、AI、RWA 等）",
        f"4. 增加日内多次快照对比（区分日内噪音 vs 趋势共振）",
        f"5. 增加共振强度衰减追踪（信号发出后的持续性验证）",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {HANDOFF_MD_PATH}")


if __name__ == "__main__":
    raise SystemExit(main())
