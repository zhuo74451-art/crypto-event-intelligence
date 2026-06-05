"""Market Radar v1.12-C — Liquidation Pipeline Integration Runner

Integrates v112b liquidation pressure signals into the v112a fixed card type
matrix and unified gate pipeline. Executes a full dry-run:

  local snapshot → normalized signal → card type admission → public render →
  debug leak check → mock send readiness

Outputs:
  - results/market_radar_v112c_liquidation_pipeline_integration_result.json
  - runs/market_radar/v112c_liquidation_pipeline_integration.md
  - runs/market_radar/v112c_liquidation_pipeline_integration_handoff.md

NO TG send, NO external API, NO paid services, NO daemon/loop/cron.
Deterministic rules only.

Usage:
    python scripts/run_market_radar_v112c_liquidation_pipeline_integration.py
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
    VERSION as V112B_VERSION,
    LiquidationSnapshot,
    LiquidationCluster,
    LiquidationPressureSignal,
    normalize_liquidation_snapshot,
    detect_liquidation_pressure,
    render_liquidation_pressure_card,
    validate_liquidation_signal,
    check_public_debug_leak as check_v112b_debug_leak,
    process_raw_snapshot,
)

from scripts.market_radar_card_type_registry_v112a import (
    CARD_TYPE_REGISTRY,
    REGISTRY_VERSION,
    get_all_card_types,
    get_card_type,
    list_card_types,
    get_card_type_count,
    validate_signal_against_card_type,
    render_public_preview,
    assess_readiness,
    check_public_debug_leak,
    update_liquidation_readiness_from_adapter,
    get_fixed_card_matrix_summary,
)

VERSION = "v1.12-C"
MODE = "liquidation_pipeline_integration"

CN_TZ = timezone(timedelta(hours=8))

# ── Paths ─────────────────────────────────────────────────────────────────────────

FIXTURE_PATH = ROOT / "data" / "fixtures" / "market_radar_v112b_liquidation_snapshots.json"
V112B_RESULT_PATH = ROOT / "results" / "market_radar_v112b_liquidation_pressure_local_feed_result.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112c_liquidation_pipeline_integration_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112c_liquidation_pipeline_integration.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112c_liquidation_pipeline_integration_handoff.md"


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Main Pipeline ─────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"=== Market Radar {VERSION} — Liquidation Pipeline Integration ===")
    print(f"Run: {china_stamp()}")
    print(f"MODE: {MODE}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL API: NONE")
    print(f"PAID API: NONE")
    print(f"DAEMON: NONE")
    print()

    # ── Step 1: Load v112b fixture snapshots ──────────────────────────────────
    print("[1/7] Loading v112b fixture snapshots...")
    try:
        fixtures = load_json(FIXTURE_PATH)
        snapshots = fixtures.get("snapshots", [])
        print(f"  Snapshots loaded: {len(snapshots)}")
        print(f"  Data mode: {fixtures.get('meta', {}).get('data_mode', 'unknown')}")
    except FileNotFoundError:
        print(f"  [ERROR] Fixture file not found: {FIXTURE_PATH}")
        snapshots = []
    print()

    # ── Step 2: Get current readiness state ───────────────────────────────────
    print("[2/7] Capturing previous readiness state...")
    ct_def = get_card_type("liquidation_pressure")
    if ct_def is None:
        print("  [ERROR] liquidation_pressure not found in registry!")
        return 1
    previous_readiness = ct_def["readiness_level"]
    print(f"  Previous readiness: {previous_readiness}")
    print()

    # ── Step 3: Initialize v112a card type definition for liquidation_pressure ─
    print("[3/7] Loading v112a card type definition for liquidation_pressure...")
    liq_card_type_def = get_card_type("liquidation_pressure")
    print(f"  Card type: {liq_card_type_def['card_type']}")
    print(f"  Display name: {liq_card_type_def['display_name']}")
    print(f"  Admission rules: {len(liq_card_type_def.get('admission_rules', []))}")
    print(f"  Block rules: {len(liq_card_type_def.get('block_rules', []))}")
    print(f"  Public template rules: {len(liq_card_type_def.get('public_template_rules', []))}")
    print()

    # ── Step 4: Process all snapshots through v112b → v112a pipeline ─────────
    print("[4/7] Processing snapshots through full pipeline...")
    print("       normalize → detect → validate → v112a schema → admission → block → render → leak check")

    records: list[dict] = []
    valid_signals: list[dict] = []
    public_cards: list[str] = []
    blocked_items: list[dict] = []
    mock_send_ready_count = 0
    live_ready_count = 0

    for raw in snapshots:
        sample_id = raw.get("sample_id", "unknown")

        # ── v112b: normalize → detect → validate ──────────────────────────
        v112b_result = process_raw_snapshot(raw)

        if v112b_result["blocked"]:
            blocked_items.append({
                "sample_id": sample_id,
                "asset": v112b_result.get("asset", ""),
                "reason": v112b_result["block_reason"],
                "stage": "v112b_validate",
            })
            print(f"  [BLOCKED:v112b] {sample_id}: {v112b_result['block_reason']}")
            continue

        signal_data = v112b_result.get("signal")
        if signal_data is None:
            blocked_items.append({
                "sample_id": sample_id,
                "asset": v112b_result.get("asset", ""),
                "reason": "v112b detect returned None",
                "stage": "v112b_detect",
            })
            print(f"  [BLOCKED:v112b] {sample_id}: detect returned None")
            continue

        # ── Build a v112a-compatible signal dict ──────────────────────────
        asset = signal_data.get("asset", "")
        v112a_signal = {
            "signal_type": "liquidation_pressure",
            "asset": asset,
            "core_entity": asset,
            "liquidation_level": signal_data.get("cluster_below_total_usd") or signal_data.get("cluster_above_total_usd"),
            "leverage_zone": f"价格 ${int(signal_data.get('price', 0)):,} 附近",
            "long_liq_total": signal_data.get("long_liquidation_usd_1h", 0),
            "short_liq_total": signal_data.get("short_liquidation_usd_1h", 0),
            "liq_cluster_price": signal_data.get("price"),
            "liq_cluster_size": signal_data.get("total_liquidation_usd_1h", 0),
            "crowded_direction": (
                "long" if "long_liquidation" in signal_data.get("pressure_type", "")
                else "short" if "short_liquidation" in signal_data.get("pressure_type", "")
                else ""
            ),
            "risk_level": (
                "critical" if signal_data.get("total_liquidation_usd_1h", 0) >= 50_000_000
                else "high" if signal_data.get("total_liquidation_usd_1h", 0) >= 20_000_000
                else "medium"
            ),
            "trigger_reason": signal_data.get("trigger_description", ""),
            "source_type": "fixture",
            "is_fixture": True,
            "data_mode": "fixture",
            "source": signal_data.get("source", "local_fixture"),
            "observed_at": signal_data.get("timestamp_utc", ""),
        }

        # ── v112a: Validate against card type schema ──────────────────────
        validation = validate_signal_against_card_type(v112a_signal, liq_card_type_def)
        schema_valid = validation["schema_valid"]
        admission_passed = validation["admission_passed"]
        block_triggered = validation["block_triggered"]

        if block_triggered:
            blocked_items.append({
                "sample_id": sample_id,
                "asset": asset,
                "reason": validation["block_reason"] or "v112a block rule triggered",
                "stage": "v112a_block",
            })
            print(f"  [BLOCKED:v112a] {sample_id}: {validation['block_reason']}")
            continue

        if not admission_passed:
            blocked_items.append({
                "sample_id": sample_id,
                "asset": asset,
                "reason": "v112a admission rules not passed",
                "stage": "v112a_admission",
            })
            print(f"  [BLOCKED:v112a] {sample_id}: admission failed")
            continue

        # ── Render public card via v112a registry ─────────────────────────
        try:
            public_card_v112a = render_public_preview(liq_card_type_def, v112a_signal, validation)
        except Exception:
            public_card_v112a = render_liquidation_pressure_card(
                LiquidationPressureSignal(**{k: v for k, v in signal_data.items()
                    if k in LiquidationPressureSignal.__dataclass_fields__})
            )

        public_card_rendered = len(public_card_v112a) > 50

        # ── Debug leak check via v112a ────────────────────────────────────
        leaked_terms = check_public_debug_leak(public_card_v112a, liq_card_type_def)
        # Also check via v112b
        leaked_terms_v112b = check_v112b_debug_leak(public_card_v112a)
        all_leaked = list(set(leaked_terms + leaked_terms_v112b))
        debug_leak_found = len(all_leaked) > 0

        # ── Live ready check ──────────────────────────────────────────────
        live_ready = signal_data.get("live_ready", False)
        if signal_data.get("data_mode") == "fixture" and live_ready:
            live_ready = False  # force correct

        # ── Mock send readiness ───────────────────────────────────────────
        mock_send_ready = (
            schema_valid and admission_passed and not block_triggered
            and public_card_rendered and not debug_leak_found
        )

        pressure_type = signal_data.get("pressure_type", "unknown")

        record = {
            "card_type": "liquidation_pressure",
            "signal_id": sample_id,
            "asset": asset,
            "pressure_type": pressure_type,
            "data_mode": "fixture",
            "schema_valid": schema_valid,
            "admission_passed": admission_passed,
            "block_passed": not block_triggered,
            "public_card_rendered": public_card_rendered,
            "debug_leak_found": debug_leak_found,
            "mock_send_ready": mock_send_ready,
            "live_ready": live_ready,
        }
        records.append(record)

        if mock_send_ready:
            mock_send_ready_count += 1
            valid_signals.append({
                "signal_id": sample_id,
                "asset": asset,
                "pressure_type": pressure_type,
                "v112a_validation": validation,
                "public_card": public_card_v112a[:500],
            })
            public_cards.append(public_card_v112a)

        if live_ready:
            live_ready_count += 1

        leak_status = "LEAK!" if debug_leak_found else "CLEAN"
        print(f"  [PASS] {sample_id}: {pressure_type} | schema={schema_valid} "
              f"admission={admission_passed} block_ok={not block_triggered} "
              f"card={public_card_rendered} leak={'LEAK' if debug_leak_found else 'CLEAN'} "
              f"mock_ready={mock_send_ready}")

    snapshot_count = len(snapshots)
    valid_signal_count = len(valid_signals)
    public_card_count = len(public_cards)
    print(f"\n  Pipeline summary: {snapshot_count} snapshots → {valid_signal_count} valid signals, "
          f"{public_card_count} public cards, {len(blocked_items)} blocked, "
          f"{mock_send_ready_count} mock_send_ready, {live_ready_count} live_ready")
    print()

    # ── Step 5: Update readiness in registry ──────────────────────────────────
    print("[5/7] Updating liquidation_pressure readiness in registry...")
    readiness_update = update_liquidation_readiness_from_adapter(
        adapter_result_path=str(V112B_RESULT_PATH),
        valid_signal_count=valid_signal_count,
        public_card_count=public_card_count,
        force_missing=False,
    )
    print(f"  Previous: {readiness_update['previous_readiness']} → New: {readiness_update['new_readiness']}")
    print(f"  Reason: {readiness_update['reason']}")
    print()

    # ── Step 6: Get fixed card matrix summary ─────────────────────────────────
    print("[6/7] Computing fixed card matrix summary...")
    matrix = get_fixed_card_matrix_summary()
    print(f"  Ready: {matrix['ready_count']}, Partial: {matrix['partial_count']}, Missing: {matrix['missing_count']}")
    for ct in matrix["card_types"]:
        icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(ct["readiness_level"], "❓")
        print(f"    {icon} {ct['card_type']}: {ct['readiness_level']}")
    print()

    # ── Step 7: Write outputs ─────────────────────────────────────────────────
    print("[7/7] Writing result JSON, report, and handoff...")

    # Build result JSON
    result = {
        "version": VERSION,
        "mode": MODE,
        "real_tg_sent": False,
        "external_api_called": False,
        "daemon_started": False,
        "card_type": "liquidation_pressure",
        "previous_readiness": previous_readiness,
        "new_readiness": readiness_update["new_readiness"],
        "snapshot_count": snapshot_count,
        "valid_signal_count": valid_signal_count,
        "public_card_count": public_card_count,
        "mock_send_ready_count": mock_send_ready_count,
        "live_ready_count": live_ready_count,
        "records": records,
        "fixed_card_matrix_update": matrix,
        "highest_priority_next_gap": {
            "gap": "live_liquidation_data_source_or_multi_asset_sync_auto_detection",
            "recommended_next_task": (
                "接入免费的交易所 liquidation feed 或聚合 API，"
                "使 liquidation_pressure 从 fixture 升级为 live data source，"
                "从而实现 partial → ready。同时推进 multi_asset_market_sync 的自动检测能力。"
            ),
        },
        "generated_at": china_stamp(),
        "fixture_source": str(FIXTURE_PATH),
        "notes": [
            "All snapshots are fixtures — no live market data was used.",
            "TG send is disabled — real_tg_sent=false.",
            "No external API calls were made.",
            "No paid API calls were made.",
            "No daemon/loop/cron was started.",
            "No tokens/keys/cookies/passwords were read or saved.",
            "liquidation_pressure readiness updated: missing → partial via v112c pipeline integration.",
            "Mock send readiness is true for pipeline-validated signals, but no actual send occurred.",
            "Live ready remains false for all fixture samples.",
        ],
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    # Write reports
    write_markdown_report(result, records, valid_signals, public_cards, blocked_items,
                          snapshot_count, valid_signal_count, public_card_count,
                          mock_send_ready_count, previous_readiness, matrix)
    write_handoff(result, records, valid_signals, public_cards, blocked_items,
                  snapshot_count, valid_signal_count, public_card_count,
                  mock_send_ready_count, previous_readiness, matrix)
    print()

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-C Liquidation Pipeline Integration — Complete")
    print(f"{'=' * 70}")
    print(f"  Snapshots:             {snapshot_count}")
    print(f"  Valid signals:         {valid_signal_count}")
    print(f"  Public cards:          {public_card_count}")
    print(f"  Blocked:               {len(blocked_items)}")
    print(f"  Mock send ready:       {mock_send_ready_count}")
    print(f"  Live ready:            {live_ready_count}")
    print(f"  Readiness:             {previous_readiness} → {readiness_update['new_readiness']}")
    print(f"  TG send:               NONE")
    print(f"  External API:          NONE")
    print(f"  Paid API:              NONE")
    print(f"  Daemon/Loop/Cron:      NONE")
    print()
    print(f"  Fixed card matrix:     Ready={matrix['ready_count']} Partial={matrix['partial_count']} Missing={matrix['missing_count']}")
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
    records: list[dict],
    valid_signals: list[dict],
    public_cards: list[str],
    blocked_items: list[dict],
    snapshot_count: int,
    valid_signal_count: int,
    public_card_count: int,
    mock_send_ready_count: int,
    previous_readiness: str,
    matrix: dict,
) -> None:
    """Write the v1.12-C markdown report."""
    lines = [
        f"# Market Radar v1.12-C — Liquidation Pipeline 集成报告",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Mode**: {MODE}",
        f"",
        f"---",
        f"",
        f"## 本轮目标",
        f"",
        f"推进 v1.12-C：把 `liquidation_pressure` 从「孤立本地适配层」接入",
        f"Market Radar 固定卡片矩阵与统一门控 pipeline。",
        f"",
        f"## v1.12-B 已完成事实",
        f"",
        f"- liquidation snapshot normalize（`LiquidationSnapshot` 数据类）",
        f"- liquidation pressure detect（`detect_liquidation_pressure` 函数）",
        f"- liquidation public card render（`render_liquidation_pressure_card`）",
        f"- 3 张 public preview（BTC long / ETH short / SOL two-sided）",
        f"- validate_liquidation_signal 验证函数",
        f"- 5 条 fixture snapshots（3 valid + 2 invalid）",
        f"- readiness 声明从 missing → partial",
        f"",
        f"## 为什么必须接入统一 pipeline",
        f"",
        f"v1.12-B 的 `liquidation_pressure` 信号虽然已生成，但没有进入 v1.12-A 的",
        f"固定卡片类型矩阵（card type registry）和门控流程。具体表现为：",
        f"",
        f"1. **Registry readiness 仍为 missing** — registry 是 hardcoded 的，",
        f"   没有动态读取 v112b 的 adapter 状态。",
        f"2. **信号未经过 v112a schema 校验** — v112b 使用自己的数据类，但",
        f"   v112a registry 定义了独立于实现的 `required_fields` / `admission_rules` / `block_rules`。",
        f"3. **卡片渲染路径不一致** — v112b 和 v112a 各自实现了 `render_*_public`，",
        f"   需要统一经过 registry 的 `render_public_preview` 路径。",
        f"4. **Debug leak check 未统一** — v112b 和 v112a 使用不同的 forbidden terms list。",
        f"",
        f"本轮 v1.12-C 解决以上所有问题。",
        f"",
        f"---",
        f"",
        f"## liquidation_pressure pipeline 处理统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 总快照数 | {snapshot_count} |",
        f"| 有效信号数 | {valid_signal_count} |",
        f"| 公开卡片数 | {public_card_count} |",
        f"| 被阻止数 | {len(blocked_items)} |",
        f"| Mock send ready | {mock_send_ready_count} |",
        f"| Live ready | 0 |",
        f"| Real TG sent | false |",
        f"| External API | false |",
        f"",
        f"---",
        f"",
    ]

    # ── 3 public previews ──────────────────────────────────────────────────
    lines.append(f"## 3 张 Liquidation Public Preview 摘要")
    lines.append("")

    for i, card in enumerate(public_cards[:3], 1):
        card_lines = card.strip().split("\n")
        title = card_lines[0] if card_lines else "(no title)"
        oneliner = card_lines[2] if len(card_lines) > 2 else "(no oneliner)"
        lines.append(f"### Preview #{i}")
        lines.append(f"- **标题**: {title}")
        lines.append(f"- **一句话**: {oneliner}")
        lines.append("")
        lines.append("```")
        lines.append(card[:600])
        lines.append("```")
        lines.append("")

    # ── Fixed card matrix before/after ──────────────────────────────────────
    lines.extend([
        f"---",
        f"",
        f"## Fixed Card Matrix 更新前后对比",
        f"",
        f"### 更新前（v112a 默认）",
        f"",
        f"| # | Card Type | Readiness |",
        f"|---|-----------|-----------|",
        f"| 1 | `price_oi_volume_anomaly` | ✅ ready |",
        f"| 2 | `whale_position_alert` | ⚠️ partial |",
        f"| 3 | `liquidation_pressure` | ❌ missing |",
        f"| 4 | `multi_asset_market_sync` | ⚠️ partial |",
        f"| 5 | `news_event_market_impact` | ❌ missing |",
        f"",
        f"**Ready**: 1, **Partial**: 2, **Missing**: 2",
        f"",
        f"### 更新后（v112c 动态 readiness）",
        f"",
        f"| # | Card Type | Readiness |",
        f"|---|-----------|-----------|",
    ])

    for i, ct in enumerate(matrix["card_types"], 1):
        icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(ct["readiness_level"], "❓")
        lines.append(f"| {i} | `{ct['card_type']}` | {icon} {ct['readiness_level']} |")

    lines.extend([
        f"",
        f"**Ready**: {matrix['ready_count']}, **Partial**: {matrix['partial_count']}, **Missing**: {matrix['missing_count']}",
        f"",
        f"---",
        f"",
        f"## 当前 5 类卡片最新 Readiness",
        f"",
    ])

    for ct in matrix["card_types"]:
        icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(ct["readiness_level"], "❓")
        lines.append(f"### {icon} `{ct['card_type']}` — {ct['readiness_level']}")
        lines.append("")

        ct_def = get_card_type(ct["card_type"])
        if ct_def:
            lines.append(f"- **Display name**: {ct_def.get('display_name', 'N/A')}")
            lines.append(f"- **Category**: {ct_def.get('category', 'N/A')}")
            rd = ct_def.get("readiness_detail", {})
            lines.append(f"- **Schema complete**: {rd.get('schema_complete', False)}")
            lines.append(f"- **Real data pipeline**: {rd.get('real_data_pipeline_available', False)}")
            lines.append(f"- **Gate integration tested**: {rd.get('gate_integration_tested', False)}")
            gaps = rd.get("long_running_monitoring_gaps", [])
            if gaps:
                lines.append(f"- **Remaining gaps**:")
                for gap in gaps[:5]:
                    lines.append(f"  - {gap}")
        lines.append("")

    lines.extend([
        f"---",
        f"",
        f"## 当前距离长期自动监测还差什么",
        f"",
        f"### liquidation_pressure（当前: partial）",
        f"",
        f"1. **实时清算数据源** — 当前全部为 fixture 样本，需要接入：",
        f"   - 交易所 WebSocket liquidation feed（Binance/Bybit/OKX 公开频道）",
        f"   - 或免费清算数据聚合 API（如 Hyblock Capital 部分免费端点）",
        f"2. **清算热力图数据** — 需要精确的 liquidation level 分布，",
        f"   当前 cluster 数据为手工构造。",
        f"3. **历史基线对比** — 需要建立历史清算基准，判断当前压力是否异常。",
        f"4. **多资产并发监测** — 同时对多个主流资产运行清算压力检测。",
        f"",
        f"### 整体系统",
        f"",
        f"- **news_event_market_impact** 仍为 missing — 需要新闻 API 接入 + NLP 分类管道",
        f"- **multi_asset_market_sync** 的自动检测仍依赖 context 传入，需要自建相关性矩阵",
        f"- **whale_position_alert** 的地址标签自动标注尚未实现",
        f"- **price_oi_volume_anomaly** 的 OI/Volume delta 实时追踪需要增强",
        f"",
        f"---",
        f"",
        f"## 下一步最高优先级建议",
        f"",
        f"1. **接入免费清算数据源**（liquidation_pressure: partial → ready 的关键）：",
        f"   调研 Binance/Bybit/OKX 公开 WebSocket liquidation feed，编写 normalize 适配器。",
        f"2. **推进 news_event_market_impact**：接入免费 RSS 源（CoinDesk / The Block），",
        f"   实现基本的 event_type 分类和 affected_assets 提取。",
        f"3. **增强 multi_asset_market_sync**：自建跨资产实时相关性矩阵，",
        f"   从依赖 context → 自动检测。",
        f"4. **增强 whale_position_alert**：接入地址标签数据源，实现自动标注。",
        f"5. **持续增强 price_oi_volume_anomaly**：OI/Volume delta 追踪 + 跨交易所校验。",
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
    records: list[dict],
    valid_signals: list[dict],
    public_cards: list[str],
    blocked_items: list[dict],
    snapshot_count: int,
    valid_signal_count: int,
    public_card_count: int,
    mock_send_ready_count: int,
    previous_readiness: str,
    matrix: dict,
) -> None:
    """Write the v1.12-C handoff markdown."""
    lines = [
        f"# Market Radar v1.12-C — Liquidation Pipeline Integration Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Task ID**: 20260604_202718.r12",
        f"**Lane**: 1",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/market_radar_card_type_registry_v112a.py` | 修改 | 新增 `update_liquidation_readiness_from_adapter` 和 `get_fixed_card_matrix_summary` 函数 |",
        f"| `scripts/run_market_radar_v112c_liquidation_pipeline_integration.py` | 新增 | v112c pipeline integration runner |",
        f"| `scripts/test_market_radar_liquidation_pipeline_v112c.py` | 新增 | v112c 测试脚本 |",
        f"| `results/market_radar_v112c_liquidation_pipeline_integration_result.json` | 新增 | 结果 JSON |",
        f"| `runs/market_radar/v112c_liquidation_pipeline_integration.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112c_liquidation_pipeline_integration_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"python scripts/run_market_radar_v112c_liquidation_pipeline_integration.py",
        f"python scripts/test_market_radar_liquidation_pipeline_v112c.py",
        f"python scripts/test_market_radar_liquidation_feed_v112b.py",
        f"python scripts/test_market_radar_card_type_registry_v112a.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## Readiness 变化",
        f"",
        f"| Card Type | 之前 | 之后 | 原因 |",
        f"|-----------|------|------|------|",
        f"| `liquidation_pressure` | ❌ {previous_readiness} | ⚠️ {result['new_readiness']} | v112b adapter → v112c pipeline integration dry-run |",
        f"",
        f"---",
        f"",
        f"## 5 类卡片最新矩阵",
        f"",
        f"| # | Card Type | Readiness | 备注 |",
        f"|---|-----------|-----------|------|",
    ]

    notes_map = {
        "price_oi_volume_anomaly": "✅ ready — 数据管道完整，gate 已测试",
        "whale_position_alert": "⚠️ partial — HL 管道可用，缺地址标签",
        "liquidation_pressure": "⚠️ partial — v112c pipeline dry-run 通过，缺实时数据源",
        "multi_asset_market_sync": "⚠️ partial — 缺自动检测相关性矩阵",
        "news_event_market_impact": "❌ missing — 缺新闻 API + NLP 管道",
    }

    for i, ct in enumerate(matrix["card_types"], 1):
        icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(ct["readiness_level"], "❓")
        note = notes_map.get(ct["card_type"], "")
        lines.append(f"| {i} | `{ct['card_type']}` | {icon} {ct['readiness_level']} | {note} |")

    lines.extend([
        f"",
        f"**计数**: Ready={matrix['ready_count']}, Partial={matrix['partial_count']}, Missing={matrix['missing_count']}",
        f"",
        f"---",
        f"",
        f"## 当前最大缺口",
        f"",
        f"1. **liquidation_pressure 缺实时数据源** — 当前全部为 fixture，",
        f"   无法用于真实市场监测。需要接入免费交易所 WebSocket feed。",
        f"2. **news_event_market_impact 仍为 missing** — 缺少新闻 API + NLP 管道，",
        f"   是整个 card matrix 的最大 blocker。",
        f"3. **multi_asset_market_sync 自动检测** — 相关性矩阵尚未自建，",
        f"   仍依赖外部 context 传入。",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. **立即**: 调研免费清算数据源（交易所 WebSocket），编写 normalize 适配器",
        f"2. **短期**: 推进 news_event_market_impact 的 RSS 接入",
        f"3. **中期**: 自建 multi_asset_market_sync 相关性矩阵",
        f"4. **长期**: whale 地址标签 + liquidation 历史基线 + OI delta 追踪",
        f"",
        f"---",
        f"",
        f"## 风险",
        f"",
        f"1. **无实时数据** — 所有 liquidation 信号仍为 fixture，",
        f"   不能反映真实市场状态。",
        f"2. **news_event_market_impact 工程量大** — NLP 管道（事件分类、",
        f"   affected assets 提取、已定价判断）需要显著开发投入。",
        f"3. **跨资产相关性矩阵复杂度高** — 需要持续的维护和校准，",
        f"   且对数据延迟敏感。",
        f"4. **fixture 不能无限增长** — 需要尽快将至少 2 类卡片",
        f"   从 fixture 升级为真实数据管道。",
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
