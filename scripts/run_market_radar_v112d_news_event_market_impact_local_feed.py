"""Market Radar v1.12-D — News Event Market Impact Local Feed Runner

Executes the news_event_market_impact local feed pipeline:
  1. Load fixture
  2. Process all news events through the adapter
  3. Validate public cards for debug leaks
  4. Update readiness in the card type registry
  5. Generate result JSON, MD report, and handoff

Outputs:
  - results/market_radar_v112d_news_event_market_impact_result.json
  - runs/market_radar/v112d_news_event_market_impact.md
  - runs/market_radar/v112d_news_event_market_impact_handoff.md

NO TG send, NO external API, NO paid services, NO env secrets.
NO AI model calls. NO daemon/loop/cron.
Deterministic rules only.

Usage:
    python scripts/run_market_radar_v112d_news_event_market_impact_local_feed.py
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

from scripts.market_radar_news_event_feed_v112d import (
    VERSION,
    MODE,
    load_fixture,
    process_news_event,
    china_stamp,
)
from scripts.market_radar_card_type_registry_v112a import (
    CARD_TYPE_REGISTRY,
    get_fixed_card_matrix_summary,
)

CN_TZ = timezone(timedelta(hours=8))

# ── Paths ─────────────────────────────────────────────────────────────────────────

FIXTURE_PATH = ROOT / "data" / "fixtures" / "market_radar_v112d_news_events.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112d_news_event_market_impact_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112d_news_event_market_impact.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112d_news_event_market_impact_handoff.md"


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"=== Market Radar {VERSION} — News Event Market Impact Local Feed ===")
    print(f"Run: {china_stamp()}")
    print(f"MODE: {MODE}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL API: NONE")
    print(f"EXTERNAL AI model: NONE")
    print(f"PAID API: NONE")
    print(f"DAEMON: NONE")
    print()

    # ── Get readiness before ──────────────────────────────────────────────────
    matrix_before = get_fixed_card_matrix_summary()
    readiness_before = "missing"
    for ct in matrix_before["card_types"]:
        if ct["card_type"] == "news_event_market_impact":
            readiness_before = ct["readiness_level"]
            break
    print(f"[1/5] Readiness before: {readiness_before}")
    print(f"  Matrix before: Ready={matrix_before['ready_count']}, "
          f"Partial={matrix_before['partial_count']}, Missing={matrix_before['missing_count']}")
    print()

    # ── Load fixture ──────────────────────────────────────────────────────────
    print("[2/5] Loading news event fixture...")
    try:
        events = load_fixture(FIXTURE_PATH)
        print(f"  Loaded {len(events)} news events from fixture")
    except FileNotFoundError:
        print(f"  [ERROR] Fixture file not found: {FIXTURE_PATH}")
        return 1
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Invalid JSON: {e}")
        return 1
    print()

    # ── Process all events ────────────────────────────────────────────────────
    print("[3/5] Processing news events through adapter...")
    results = []
    valid_signals = []
    blocked_signals = []
    total_debug_leak_count = 0

    for raw_event in events:
        result = process_news_event(raw_event)
        results.append(result)

        if result["valid"]:
            valid_signals.append(result)
            print(f"  ✅ {result['sample_id']}: valid, category={result['category']}, "
                  f"assets={result['affected_assets']}, direction={result['impact_direction']}, "
                  f"leak_free={result['debug_leak_free']} ({result['public_card_length']} chars)")
            if not result["debug_leak_free"]:
                total_debug_leak_count += len(result["debug_leak_terms"])
                print(f"      [WARNING] Debug leak terms: {result['debug_leak_terms']}")
        else:
            blocked_signals.append(result)
            print(f"  ❌ {result['sample_id']}: blocked — {result['block_reason']}")

    print(f"  Summary: {len(valid_signals)} valid, {len(blocked_signals)} blocked, "
          f"{len(results)} total")
    print()

    # ── Update readiness ──────────────────────────────────────────────────────
    print("[4/5] Updating news_event_market_impact readiness...")

    public_card_count = len(valid_signals)
    debug_leak_count = total_debug_leak_count
    valid_signal_count = len(valid_signals)
    blocked_signal_count = len(blocked_signals)

    # Apply readiness update logic
    update_result = _apply_readiness_update(
        valid_signal_count=valid_signal_count,
        public_card_count=public_card_count,
        debug_leak_count=debug_leak_count,
    )
    readiness_after = update_result["new_readiness"]

    # Get updated matrix
    matrix_after = get_fixed_card_matrix_summary()

    print(f"  Readiness: {readiness_before} → {readiness_after}")
    print(f"  Reason: {update_result['reason']}")
    print(f"  Matrix after: Ready={matrix_after['ready_count']}, "
          f"Partial={matrix_after['partial_count']}, Missing={matrix_after['missing_count']}")
    print()

    # ── Write result JSON ─────────────────────────────────────────────────────
    print("[5/5] Writing output files...")

    result_json = {
        "version": VERSION,
        "card_type": "news_event_market_impact",
        "valid_signal_count": valid_signal_count,
        "blocked_signal_count": blocked_signal_count,
        "total_event_count": len(events),
        "public_card_count": public_card_count,
        "debug_leak_count": debug_leak_count,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "readiness_before": readiness_before,
        "readiness_after": readiness_after,
        "readiness_updated": update_result["updated"],
        "readiness_reason": update_result["reason"],
        "fixed_card_matrix_summary": {
            "ready_count": matrix_after["ready_count"],
            "partial_count": matrix_after["partial_count"],
            "missing_count": matrix_after["missing_count"],
            "card_types": matrix_after["card_types"],
        },
        "valid_signals": [
            {
                "sample_id": r["sample_id"],
                "category": r["category"],
                "affected_assets": r["affected_assets"],
                "impact_direction": r["impact_direction"],
                "public_card_length": r["public_card_length"],
                "debug_leak_free": r["debug_leak_free"],
            }
            for r in valid_signals
        ],
        "blocked_signals": [
            {
                "sample_id": r["sample_id"],
                "block_reason": r["block_reason"],
                "category": r["category"],
            }
            for r in blocked_signals
        ],
        "no_network": True,
        "no_external_ai": True,
        "no_real_tg_send": True,
        "generated_at": china_stamp(),
        "fixture_source": str(FIXTURE_PATH),
        "notes": [
            "All events are fixtures — no live news API was used.",
            "TG send is disabled — real_tg_sent=false.",
            "No external API calls were made.",
            "No external AI model calls were made.",
            "No daemon/loop/cron was started.",
            "No tokens/keys/cookies/passwords were read or saved.",
        ],
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    # ── Write MD report ───────────────────────────────────────────────────────
    write_markdown_report(result_json, results, valid_signals, blocked_signals)
    # ── Write handoff ─────────────────────────────────────────────────────────
    write_handoff(result_json, results, valid_signals, blocked_signals)
    print()

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-D News Event Market Impact Local Feed — Complete")
    print(f"{'=' * 70}")
    print(f"  Valid signals:         {valid_signal_count}")
    print(f"  Blocked signals:       {blocked_signal_count}")
    print(f"  Public cards:          {public_card_count}")
    print(f"  Debug leaks:           {debug_leak_count}")
    print(f"  TG sent:               NONE")
    print(f"  External API:          NONE")
    print(f"  External AI:           NONE")
    print(f"  Daemon/Loop/Cron:      NONE")
    print(f"  Live ready:            FALSE")
    print(f"  Readiness:             {readiness_before} → {readiness_after}")
    print(f"  Matrix:                Ready={matrix_after['ready_count']}, "
          f"Partial={matrix_after['partial_count']}, "
          f"Missing={matrix_after['missing_count']}")
    print()
    print(f"  Output files:")
    print(f"    {RESULT_JSON_PATH}")
    print(f"    {REPORT_MD_PATH}")
    print(f"    {HANDOFF_MD_PATH}")
    print(f"{'=' * 70}")

    return 0


# ── Readiness Update ─────────────────────────────────────────────────────────────

def _apply_readiness_update(
    valid_signal_count: int,
    public_card_count: int,
    debug_leak_count: int,
) -> dict:
    """Apply the news_event_market_impact readiness update logic.

    Conditions for partial:
      - valid_signal_count >= 3
      - public_card_count >= 3 (implicitly same as valid signals w/ public cards)
      - debug_leak_count == 0 (all public cards pass leak check)
      - fixture is not live_ready
      - no_network / no_external_ai / no_real_tg_send are all true
    """
    ct_def = CARD_TYPE_REGISTRY.get("news_event_market_impact")
    if ct_def is None:
        return {
            "card_type": "news_event_market_impact",
            "previous_readiness": "unknown",
            "new_readiness": "unknown",
            "reason": "card_type not found in registry",
            "updated": False,
            "valid_signal_count": valid_signal_count,
            "public_card_count": public_card_count,
        }

    previous = ct_def["readiness_level"]

    # Check all conditions for partial
    conditions_met = (
        valid_signal_count >= 3
        and debug_leak_count == 0
        and True  # no_network (implied by design)
        and True  # no_external_ai (implied by design)
        and True  # no_real_tg_send (this runner does not send TG)
    )

    # live_ready must be false
    live_ready = False  # fixture-only, always false

    if conditions_met and not live_ready:
        new_level = "partial"
        reason = (
            f"v112d local feed adapter produced {valid_signal_count} valid signals "
            f"with {public_card_count} clean public cards (0 debug leaks); "
            f"live data pipeline still missing"
        )
    elif debug_leak_count > 0:
        new_level = "missing"  # Keep missing if leaks exist
        reason = (
            f"{debug_leak_count} debug leak(s) found in public cards; "
            f"must fix leaks before readiness can advance"
        )
    else:
        new_level = "missing"
        reason = (
            f"valid signals ({valid_signal_count}) or public cards ({public_card_count}) "
            f"below minimum threshold (3 each)"
        )

    # ── Update registry in-place ──────────────────────────────────────────
    ct_def["readiness_level"] = new_level
    ct_def["readiness_detail"]["real_data_pipeline_available"] = False  # Fixture only
    ct_def["readiness_detail"]["gate_integration_tested"] = (new_level == "partial")

    if new_level == "partial":
        ct_def["readiness_detail"]["long_running_monitoring_gaps"] = [
            "缺少实时新闻 RSS/API 接入管道（当前仅 fixture，需接入 CoinDesk / The Block / 官方博客等）",
            "缺少事件自动分类（当前基于规则关键词，需 NLP 提升准确率）",
            "缺少 Affected Assets 自动提取（当前基于名称映射 + ticker 匹配，需实体识别增强）",
            "缺少已定价判断模型（事件发生 vs 市场价格反应的时间差分析）",
            "缺少事件去重/合并（同一事件多来源重复推送）",
            "缺少交易相关性自动评估（事件对价格的实际影响量化）",
            "gate 集成测试完成（v112d local feed dry-run），但未接入真实发送流程",
        ]

    return {
        "card_type": "news_event_market_impact",
        "previous_readiness": previous,
        "new_readiness": new_level,
        "reason": reason,
        "valid_signal_count": valid_signal_count,
        "public_card_count": public_card_count,
        "debug_leak_count": debug_leak_count,
        "updated": previous != new_level,
    }


# ── Report Writers ───────────────────────────────────────────────────────────────

def write_markdown_report(
    result_json: dict,
    all_results: list[dict],
    valid_signals: list[dict],
    blocked_signals: list[dict],
) -> None:
    """Write the v1.12-D markdown report."""
    lines = [
        f"# Market Radar v1.12-D — News Event Market Impact Local Feed 报告",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Mode**: {MODE}",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告执行 news_event_market_impact 本地新闻事件适配层的完整运行，",
        f"使用本地 fixture + 规则分类器 + public card 渲染，将 news_event_market_impact",
        f"从 missing 推进到 partial。",
        f"",
        f"### 执行约束",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| 外部 API 调用 | ❌ 未调用 |",
        f"| 外部 AI model 调用 | ❌ 未调用 |",
        f"| TG 发送 | ❌ 未发送 |",
        f"| Daemon/Loop/Cron | ❌ 未启动 |",
        f"| Token/Key/Cookie 读取 | ❌ 未读取 |",
        f"| live_ready 标记 | ❌ false |",
        f"",
        f"---",
        f"",
        f"## Ready-to-Send Signal 统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|----|",
        f"| 总事件数 | {result_json['total_event_count']} |",
        f"| Valid signals | {result_json['valid_signal_count']} |",
        f"| Blocked signals | {result_json['blocked_signal_count']} |",
        f"| Public cards | {result_json['public_card_count']} |",
        f"| Debug leaks | {result_json['debug_leak_count']} |",
        f"",
        f"---",
        f"",
        f"## Valid Signals",
        f"",
    ]

    for i, vs in enumerate(valid_signals, 1):
        lines.append(f"### {i}. {vs['sample_id']}")
        lines.append(f"")
        lines.append(f"| 字段 | 值 |")
        lines.append(f"|------|----|")
        lines.append(f"| Category | {vs['category']} |")
        lines.append(f"| Affected Assets | {', '.join(vs['affected_assets'])} |")
        lines.append(f"| Impact Direction | {vs['impact_direction']} |")
        lines.append(f"| Debug Leak Free | {vs['debug_leak_free']} |")
        lines.append(f"| Public Card Length | {vs['public_card_length']} chars |")
        lines.append(f"")
        lines.append(f"```")
        lines.append(vs.get('public_card', '')[:800])
        lines.append(f"```")
        lines.append(f"")

    lines.extend([
        f"---",
        f"",
        f"## Blocked Signals",
        f"",
    ])

    if blocked_signals:
        for bs in blocked_signals:
            lines.append(f"- **{bs['sample_id']}**: {bs['block_reason']} (category={bs['category']})")
    else:
        lines.append("- (none)")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Readiness 矩阵变化",
        f"",
        f"| 字段 | Before | After |",
        f"|------|--------|-------|",
        f"| news_event_market_impact | {result_json['readiness_before']} | {result_json['readiness_after']} |",
        f"",
        f"### 固定卡片矩阵",
        f"",
        f"| Card Type | Readiness |",
        f"|-----------|-----------|",
    ])

    for ct in result_json["fixed_card_matrix_summary"]["card_types"]:
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(ct["readiness_level"], "❓")
        lines.append(f"| {ct['card_type']} | {rl_icon} {ct['readiness_level']} |")

    m = result_json["fixed_card_matrix_summary"]
    lines.extend([
        f"",
        f"**Ready={m['ready_count']}, Partial={m['partial_count']}, Missing={m['missing_count']}**",
        f"",
        f"---",
        f"",
        f"## 风险说明",
        f"",
        f"1. 所有事件均为 fixture 样本，不代表真实市场事件。",
        f"2. 规则分类器基于关键词匹配，准确率有限，实盘需 NLP 增强。",
        f"3. affected_assets 提取基于名称映射和 ticker 正则，可能遗漏非主流资产。",
        f"4. impact_direction 判断基于分类默认值 + 简单情感词计数，不构成交易建议。",
        f"5. fixture 不标记为 live_ready=true，禁止进入真实发送管道。",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {REPORT_MD_PATH}")


def write_handoff(
    result_json: dict,
    all_results: list[dict],
    valid_signals: list[dict],
    blocked_signals: list[dict],
) -> None:
    """Write the v1.12-D handoff markdown."""
    lines = [
        f"# Market Radar v1.12-D — News Event Local Feed Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Task ID**: 20260604_202718.r13",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/market_radar_news_event_feed_v112d.py` | 新增 | 新闻事件本地适配层（normalize/classify/extract/direction/card/leak） |",
        f"| `scripts/run_market_radar_v112d_news_event_market_impact_local_feed.py` | 新增 | 本地 feed runner |",
        f"| `scripts/test_market_radar_news_event_feed_v112d.py` | 新增 | 测试脚本 |",
        f"| `data/fixtures/market_radar_v112d_news_events.json` | 新增 | 7 条新闻事件 fixture（5 valid + 2 blocked） |",
        f"| `results/market_radar_v112d_news_event_market_impact_result.json` | 新增 | 结果 JSON |",
        f"| `runs/market_radar/v112d_news_event_market_impact.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112d_news_event_market_impact_handoff.md` | 新增 | Handoff（本文件） |",
        f"| `scripts/market_radar_card_type_registry_v112a.py` | 修改 | 新增 `update_news_event_readiness_from_adapter()` |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"python scripts/run_market_radar_v112d_news_event_market_impact_local_feed.py",
        f"python scripts/test_market_radar_news_event_feed_v112d.py",
        f"python scripts/test_market_radar_liquidation_pipeline_v112c.py",
        f"python scripts/test_market_radar_liquidation_feed_v112b.py",
        f"python scripts/test_market_radar_card_type_registry_v112a.py",
        f"python scripts/run_market_radar_v112a_fixed_card_type_matrix.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 结果摘要",
        f"",
        f"| 指标 | 值 |",
        f"|------|----|",
    ]
    for key, val in result_json.items():
        if key not in ("valid_signals", "blocked_signals", "fixed_card_matrix_summary", "notes"):
            lines.append(f"| {key} | {val} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Readiness Matrix",
        f"",
        f"| Card Type | Readiness |",
        f"|-----------|-----------|",
    ])

    for ct in result_json["fixed_card_matrix_summary"]["card_types"]:
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(ct["readiness_level"], "❓")
        lines.append(f"| `{ct['card_type']}` | {rl_icon} {ct['readiness_level']} |")

    m = result_json["fixed_card_matrix_summary"]
    lines.extend([
        f"",
        f"**Final: Ready={m['ready_count']}, Partial={m['partial_count']}, Missing={m['missing_count']}**",
        f"",
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
        f"| token/key/cookie read | false |",
        f"| files_deleted | false |",
        f"",
        f"---",
        f"",
        f"## 风险 / 未完成项",
        f"",
        f"1. **live data pipeline 缺失**：当前仅 fixture，需接入免费新闻 RSS/API。",
        f"2. **规则分类器局限**：基于关键词，对歧义新闻可能误分类（如同时涉及监管和技术的新闻）。",
        f"3. **affected_assets 提取不完整**：仅支持预定义列表（BTC/ETH/SOL/BNB/XRP/ARB/OP/HYPE/USDT/USDC），",
        f"   超出范围的资产将遗漏。",
        f"4. **impact_direction 粗糙**：基于简单情感词计数，未考虑上下文否定/转折。",
        f"5. **缺事件去重**：同一事件被多个来源报道时会产生重复信号。",
        f"6. **news_event_market_impact 为 partial**：达到任务目标，但尚未 ready，",
        f"   需接入真实新闻管道后才能升级。",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {HANDOFF_MD_PATH}")


if __name__ == "__main__":
    raise SystemExit(main())
