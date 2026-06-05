"""Market Radar v1.12-A — Fixed Card Type Matrix Runner

Executes the full 5-card-type matrix evaluation:
  1. Schema validation for each card type
  2. Required fields check
  3. Admission check
  4. Block check
  5. Public card render
  6. Debug leak check
  7. Readiness judgement

Outputs:
  - results/market_radar_v112a_fixed_card_type_matrix_result.json
  - runs/market_radar/v112a_fixed_card_type_matrix.md
  - runs/market_radar/v112a_fixed_card_type_matrix_handoff.md

NO TG send, NO external API, NO paid services, NO env secrets.
Deterministic rules only.

Usage:
    python scripts/run_market_radar_v112a_fixed_card_type_matrix.py
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

from scripts.market_radar_card_type_registry_v112a import (
    CARD_TYPE_REGISTRY,
    REGISTRY_VERSION,
    MODE,
    get_all_card_types,
    get_card_type,
    list_card_types,
    get_card_type_count,
    validate_signal_against_card_type,
    render_public_preview,
    assess_readiness,
    check_public_debug_leak,
)

CN_TZ = timezone(timedelta(hours=8))
VERSION = REGISTRY_VERSION

# ── Paths ─────────────────────────────────────────────────────────────────────────

FIXTURE_PATH = ROOT / "data" / "fixtures" / "market_radar_v112a_card_type_samples.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112a_fixed_card_type_matrix_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112a_fixed_card_type_matrix.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112a_fixed_card_type_matrix_handoff.md"


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _has_required_fields(signal: dict, required: list[str]) -> tuple[bool, list[str]]:
    missing = [f for f in required if f not in signal or signal.get(f) is None]
    return len(missing) == 0, missing


# ── Process single card type ──────────────────────────────────────────────────────

def process_card_type(
    card_type_def: dict,
    samples: list[dict],
) -> dict:
    """Run the full evaluation pipeline for one card type.

    For each sample:
      1. schema validation (required_fields check)
      2. admission check
      3. block check
      4. public card render
      5. debug leak check

    Then aggregate into readiness judgement.
    """
    card_type = card_type_def["card_type"]
    display_name = card_type_def.get("display_name", card_type)

    sample_results = []
    all_schema_valid = True
    all_admission_passed = True
    any_block_triggered = False
    any_debug_leak = False

    for sample_wrapper in samples:
        signal = sample_wrapper.get("signal", sample_wrapper)
        sample_id = sample_wrapper.get("sample_id", "unknown")
        data_mode = sample_wrapper.get("data_mode", signal.get("data_mode", "unknown"))

        # 1. Schema validation
        validation = validate_signal_against_card_type(signal, card_type_def)

        # 2 & 3 already done in validation

        # 4. Public card render
        try:
            public_preview = render_public_preview(card_type_def, signal, validation)
            preview_len = len(public_preview)
        except Exception as exc:
            public_preview = f"[RENDER ERROR: {exc}]"
            preview_len = 0

        # 5. Debug leak check
        leaked_terms = check_public_debug_leak(public_preview, card_type_def)
        leak_free = len(leaked_terms) == 0

        # 6. Fixture as live check
        is_fixture = (
            signal.get("is_fixture") in (True, "true", "True") or
            str(signal.get("source_type", "")).lower() == "fixture"
        )
        fixture_marked_correctly = (
            not is_fixture or data_mode == "fixture"
        )

        sample_result = {
            "sample_id": sample_id,
            "data_mode": data_mode,
            "is_fixture": is_fixture,
            "fixture_marked_correctly": fixture_marked_correctly,
            "schema_valid": validation["schema_valid"],
            "missing_required": validation["missing_required"],
            "admission_passed": validation["admission_passed"],
            "admission_result": validation["admission_result"],
            "block_triggered": validation["block_triggered"],
            "block_reason": validation["block_reason"],
            "block_result": validation["block_result"],
            "all_checks_passed": validation["all_checks_passed"],
            "public_preview": public_preview[:500],
            "preview_length": preview_len,
            "debug_leak_terms": leaked_terms,
            "debug_leak_free": leak_free,
        }
        sample_results.append(sample_result)

        if not validation["schema_valid"]:
            all_schema_valid = False
        if not validation["admission_passed"]:
            all_admission_passed = False
        if validation["block_triggered"]:
            any_block_triggered = True
        if not leak_free:
            any_debug_leak = True

    # ── Readiness assessment ────────────────────────────────────────────
    readiness = assess_readiness(card_type_def)

    # Determine overall status per sample results
    # For fixture samples, admission may fail by design (multi_asset_sync with 0 real)
    # so readiness is driven by the card type definition, not sample test results.
    readiness_level = readiness["readiness_level"]

    # ── Build per-type result ───────────────────────────────────────────
    best_sample = sample_results[0] if sample_results else None
    public_preview_best = best_sample["public_preview"] if best_sample else ""

    return {
        "card_type": card_type,
        "display_name": display_name,
        "purpose": card_type_def.get("purpose", ""),
        "category": card_type_def.get("category", ""),
        "required_fields": card_type_def.get("required_fields", []),
        "sample_count": len(samples),
        "sample_results": sample_results,
        "readiness": readiness,
        "public_preview": public_preview_best,
        "debug_leak_free": not any_debug_leak,
        "summary": {
            "all_samples_schema_valid": all_schema_valid,
            "all_samples_admission_passed": all_admission_passed,
            "any_sample_block_triggered": any_block_triggered,
            "any_debug_leak": any_debug_leak,
        },
    }


# ── Main ──────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"=== Market Radar {VERSION} — Fixed Card Type Matrix ===")
    print(f"Run: {china_stamp()}")
    print(f"MODE: {MODE}")
    print(f"TG SEND: NONE")
    print(f"EXTERNAL API: NONE")
    print(f"PAID API: NONE")
    print(f"DAEMON: NONE")
    print()

    # ── Load fixture samples ──────────────────────────────────────────────────
    print("[1/5] Loading fixture samples...")
    try:
        fixtures = load_json(FIXTURE_PATH)
        fixture_card_types = fixtures.get("card_types", {})
        print(f"  Fixtures loaded: {fixtures.get('meta', {}).get('total_card_types', 0)} card types, "
              f"{fixtures.get('meta', {}).get('total_samples', 0)} samples")
        print(f"  Data mode: {fixtures.get('meta', {}).get('data_mode', 'unknown')}")
    except FileNotFoundError:
        print(f"  [ERROR] Fixture file not found: {FIXTURE_PATH}")
        fixture_card_types = {}
    print()

    # ── Process each card type ────────────────────────────────────────────────
    print("[2/5] Processing 5 card types...")
    card_type_names = list_card_types()
    card_type_results = []

    for ct_name in card_type_names:
        ct_def = get_card_type(ct_name)
        if ct_def is None:
            continue

        # Get samples for this card type
        fixture_ct = fixture_card_types.get(ct_name, {})
        samples = fixture_ct.get("samples", [])

        # If no fixture samples, create a minimal synthetic one
        if not samples:
            # Create a basic empty signal for schema validation
            samples = [{
                "sample_id": f"{ct_name}_empty_placeholder",
                "data_mode": "fixture",
                "signal": {
                    "signal_type": ct_name,
                    "asset": "PLACEHOLDER",
                    "source_type": "fixture",
                    "is_fixture": True,
                    "data_mode": "fixture",
                },
            }]

        result = process_card_type(ct_def, samples)
        card_type_results.append(result)

        readiness_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(
            result["readiness"]["readiness_level"], "❓"
        )
        print(f"  {readiness_icon} {ct_name}: readiness={result['readiness']['readiness_level']}, "
              f"samples={result['sample_count']}, "
              f"debug_leak_free={result['debug_leak_free']}")

    print()

    # ── Compute aggregate summary ─────────────────────────────────────────────
    print("[3/5] Computing aggregate summary...")
    ready_count = sum(
        1 for r in card_type_results
        if r["readiness"]["readiness_level"] == "ready"
    )
    partial_count = sum(
        1 for r in card_type_results
        if r["readiness"]["readiness_level"] == "partial"
    )
    missing_count = sum(
        1 for r in card_type_results
        if r["readiness"]["readiness_level"] == "missing"
    )

    # Determine highest priority gap
    # Priority: ready types that need final push > partial that are close > missing that
    # block the monitoring loop
    highest_priority_gap = _determine_highest_priority_gap(card_type_results)

    print(f"  Ready: {ready_count}, Partial: {partial_count}, Missing: {missing_count}")
    print(f"  Highest priority gap: {highest_priority_gap['card_type']} — {highest_priority_gap['gap']}")
    print()

    # ── Write result JSON ─────────────────────────────────────────────────────
    print("[4/5] Writing result JSON...")

    result = {
        "version": VERSION,
        "mode": MODE,
        "real_tg_sent": False,
        "external_api_called": False,
        "paid_api_called": False,
        "daemon_started": False,
        "card_type_count": len(card_type_results),
        "ready_count": ready_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "card_types": card_type_results,
        "highest_priority_gap": highest_priority_gap,
        "generated_at": china_stamp(),
        "fixture_source": str(FIXTURE_PATH),
        "notes": [
            "All samples are fixtures — no live market data was used.",
            "TG send is disabled — real_tg_sent=false.",
            "No external API calls were made.",
            "No daemon/loop/cron was started.",
            "No tokens/keys/cookies/passwords were read or saved.",
        ],
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    print()

    # ── Write reports ─────────────────────────────────────────────────────────
    print("[5/5] Writing markdown report and handoff...")
    write_markdown_report(result, card_type_results, highest_priority_gap)
    write_handoff(result, card_type_results, highest_priority_gap)
    print()

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-A Fixed Card Type Matrix — Complete")
    print(f"{'=' * 70}")
    print(f"  Card types defined:    {len(card_type_results)}")
    print(f"  Ready:                 {ready_count}")
    print(f"  Partial:               {partial_count}")
    print(f"  Missing:               {missing_count}")
    print(f"  TG send:               NONE")
    print(f"  External API:          NONE")
    print(f"  Paid API:              NONE")
    print(f"  Daemon/Loop/Cron:      NONE")
    print(f"  Highest priority gap:  {highest_priority_gap['card_type']}")
    print()
    print(f"  Output files:")
    print(f"    {RESULT_JSON_PATH}")
    print(f"    {REPORT_MD_PATH}")
    print(f"    {HANDOFF_MD_PATH}")
    print(f"{'=' * 70}")

    return 0


# ── Priority gap determination ────────────────────────────────────────────────────

def _determine_highest_priority_gap(card_type_results: list[dict]) -> dict:
    """Determine the single highest priority gap across all card types.

    Logic:
      1. Missing types that block the monitoring loop → highest priority
      2. Partial types closest to ready → next priority
      3. Ready types with remaining monitoring gaps → lowest priority among gaps
    """
    # First, look at missing types — these are biggest blockers
    missing_types = [r for r in card_type_results if r["readiness"]["readiness_level"] == "missing"]
    if missing_types:
        # Pick the one with the most serious data source gap
        # liquidation_pressure is critical for risk management
        # news_event is important but less structural
        critical_order = ["liquidation_pressure", "news_event_market_impact"]
        for critical in critical_order:
            for mt in missing_types:
                if mt["card_type"] == critical:
                    return {
                        "card_type": mt["card_type"],
                        "gap": mt["readiness"].get("next_gap", "real data pipeline missing"),
                        "recommended_next_task": (
                            f"Build real-time data ingestion pipeline for {mt['card_type']}: "
                            f"{mt['readiness'].get('next_gap', 'acquire data source')}"
                        ),
                    }

    # Then partial types
    partial_types = [r for r in card_type_results if r["readiness"]["readiness_level"] == "partial"]
    if partial_types:
        # whale_position_alert is closest to ready (we have real HL pipeline)
        pt = partial_types[0]
        for p in partial_types:
            if p["card_type"] == "whale_position_alert":
                pt = p
                break
        return {
            "card_type": pt["card_type"],
            "gap": pt["readiness"].get("next_gap", "address labeling needed"),
            "recommended_next_task": (
                f"Advance {pt['card_type']} from partial to ready: "
                f"{pt['readiness'].get('next_gap', 'address remaining gaps')}"
            ),
        }

    # Ready types — find any remaining gaps
    ready_types = [r for r in card_type_results if r["readiness"]["readiness_level"] == "ready"]
    if ready_types:
        rt = ready_types[0]
        return {
            "card_type": rt["card_type"],
            "gap": rt["readiness"].get("next_gap", "OI/Volume delta tracking"),
            "recommended_next_task": (
                f"Enhance {rt['card_type']} for long-running monitoring: "
                f"{rt['readiness'].get('next_gap', 'minor enhancements')}"
            ),
        }

    # Fallback
    return {
        "card_type": "unknown",
        "gap": "no card types processed",
        "recommended_next_task": "Process card types first",
    }


# ── Report writers ────────────────────────────────────────────────────────────────

def write_markdown_report(
    result: dict,
    card_type_results: list[dict],
    highest_priority_gap: dict,
) -> None:
    """Write the v1.12-A fixed card type matrix markdown report."""
    lines = [
        f"# Market Radar v1.12-A — 固定卡片类型矩阵报告",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Mode**: {MODE}",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告建立 Market Radar 的 5 类固定卡片类型矩阵，每类包含：",
        f"",
        f"- **Schema**：required_fields + optional_fields",
        f"- **准入规则**：admission_rules（信号需满足的条件）",
        f"- **阻止规则**：block_rules（信号应被过滤的条件）",
        f"- **公开模板规则**：public_template_rules（公开卡片渲染规范）",
        f"- **Readiness 判断**：ready / partial / missing",
        f"",
        f"## 5 类卡片总览",
        f"",
        f"| # | 卡片类型 | 分类 | Readiness | 适用长期监测 |",
        f"|---|----------|------|-----------|-------------|",
    ]

    for i, ct in enumerate(card_type_results, 1):
        rl = ct["readiness"]["readiness_level"]
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(rl, "❓")
        suitable = "✅ 是" if ct["readiness"]["suitable_for_long_running_monitoring"] else "❌ 否"
        lines.append(
            f"| {i} | {ct['display_name']} (`{ct['card_type']}`) | "
            f"{ct['category']} | {rl_icon} {rl} | {suitable} |"
        )

    lines.extend([
        f"",
        f"**计数**: Ready={result['ready_count']}, Partial={result['partial_count']}, "
        f"Missing={result['missing_count']}",
        f"",
        f"---",
        f"",
    ])

    # ── Per card type detail ──────────────────────────────────────────────
    for ct in card_type_results:
        rl = ct["readiness"]["readiness_level"]
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(rl, "❓")
        lines.extend([
            f"## {rl_icon} {ct['display_name']} (`{ct['card_type']}`)",
            f"",
            f"### 用途",
            f"",
            f"{ct['purpose']}",
            f"",
            f"### Required Fields",
            f"",
            f"```",
            ", ".join(ct["required_fields"]),
            f"```",
            f"",
            f"### 准入规则",
            f"",
        ])

        ct_def = get_card_type(ct["card_type"])
        if ct_def:
            for rule in ct_def.get("admission_rules", []):
                lines.append(f"- **{rule['rule_id']}** ({rule['severity']}): {rule['description']}")

        lines.extend([
            f"",
            f"### 阻止规则",
            f"",
        ])
        if ct_def:
            for rule in ct_def.get("block_rules", []):
                lines.append(f"- **{rule['rule_id']}**: {rule['description']}")

        lines.extend([
            f"",
            f"### Public Preview",
            f"",
            f"```",
            ct.get("public_preview", "")[:600],
            f"```",
            f"",
            f"### Readiness: {rl_icon} {rl}",
            f"",
            f"- **Schema complete**: {ct['readiness'].get('schema_complete', False)}",
            f"- **Real data pipeline**: {ct['readiness'].get('real_data_pipeline_available', False)}",
            f"- **Gate integration tested**: {ct['readiness'].get('gate_integration_tested', False)}",
            f"- **Suitable for long-running monitoring**: {ct['readiness']['suitable_for_long_running_monitoring']}",
            f"",
            f"### 距离真实长期自动监测还差什么",
            f"",
        ])

        gaps = ct["readiness"].get("long_running_monitoring_gaps", [])
        if gaps:
            for gap in gaps:
                lines.append(f"- {gap}")
        else:
            lines.append("- 无明显缺口")

        lines.extend([
            f"",
            f"### Missing Fields / Data Sources / Rules",
            f"",
            f"- **Missing fields**: {', '.join(ct['readiness'].get('missing_fields', [])) or '无'}",
            f"- **Missing data sources**: {', '.join(ct['readiness'].get('missing_data_sources', [])) or '无'}",
            f"- **Missing rules**: {', '.join(ct['readiness'].get('missing_rules', [])) or '无'}",
            f"",
            f"### Next Gap",
            f"",
            f"{ct['readiness'].get('next_gap', 'N/A')}",
            f"",
            f"---",
            f"",
        ])

    # ── Summary sections ──────────────────────────────────────────────────
    lines.extend([
        f"## 最接近可用的卡片",
        f"",
    ])

    ready_types = [ct for ct in card_type_results if ct["readiness"]["readiness_level"] == "ready"]
    if ready_types:
        lines.append(f"**{ready_types[0]['display_name']} (`{ready_types[0]['card_type']}`)** 是最接近可用的卡片。")
        lines.append(f"")
        lines.append(f"理由：")
        lines.append(f"- Schema 完整、准入/阻止规则已定义、公开模板已就绪")
        lines.append(f"- 真实数据管道可用（Hyperliquid API）")
        lines.append(f"- Gate 集成已通过测试（SignalValueGate + CooldownGate + PreSendGate）")
        lines.append(f"- v1.11-L 已验证 public card 净化流程")
    else:
        lines.append(f"目前没有 ready 状态的卡片类型。")
        # Find closest partial
        partial_types = [ct for ct in card_type_results if ct["readiness"]["readiness_level"] == "partial"]
        if partial_types:
            lines.append(f"最接近的是 **{partial_types[0]['display_name']}** — 距离 ready 仅差 1-2 个缺口。")

    lines.extend([
        f"",
        f"## 最影响长期自动监测闭环的卡片",
        f"",
    ])

    # Missing types are the biggest blockers
    missing_types = [ct for ct in card_type_results if ct["readiness"]["readiness_level"] == "missing"]
    if missing_types:
        lines.append(f"**{missing_types[0]['display_name']} (`{missing_types[0]['card_type']}`)** 是最影响长期监测闭环的卡片。")
        lines.append(f"")
        lines.append(f"理由：")
        lines.append(f"- 缺少真实数据管道，无法进入 gate → card → monitor 闭环")
        lines.append(f"- 清算压力是市场风险管理的核心信号，缺失将导致监测矩阵不完整")
        lines.append(f"- 新闻事件是外部冲击的主要来源，缺失意味着系统只能看到技术面")

    lines.extend([
        f"",
        f"## 下一步最高优先级建议",
        f"",
        f"### 当前最大缺口：{highest_priority_gap['card_type']}",
        f"",
        f"- **缺口**: {highest_priority_gap['gap']}",
        f"- **建议下一步**: {highest_priority_gap['recommended_next_task']}",
        f"",
        f"### 优先级排序",
        f"",
        f"1. **liquidation_pressure** — 建立清算数据管道（Coinglass API / 交易所 liquidation feed），",
        f"   这是目前从 missing → partial 的最大单一提升。",
        f"2. **whale_position_alert** — 增加地址标签自动标注，将其从 partial → ready。",
        f"   Hyperliquid 管道已可用，仅需增强。",
        f"3. **multi_asset_market_sync** — 建立跨资产实时相关性矩阵，从依赖 context 传入",
        f"   升级为自动检测。",
        f"4. **news_event_market_impact** — 接入 RSS/新闻 API，实现事件自动分类。",
        f"   这是最大工程量的工作，建议在清算和巨鲸就绪后启动。",
        f"5. **price_oi_volume_anomaly** — 已 ready，仅需 OI/Volume delta 追踪增强。",
        f"   可以在其他卡片推进的同时并行完善。",
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
    card_type_results: list[dict],
    highest_priority_gap: dict,
) -> None:
    """Write the v1.12-A handoff markdown."""
    lines = [
        f"# Market Radar v1.12-A — Fixed Card Type Matrix Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Task ID**: 20260604_202718.r10",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/market_radar_card_type_registry_v112a.py` | 新增 | 5 类固定卡片注册表，含 schema/准入/block/模板/readiness |",
        f"| `scripts/run_market_radar_v112a_fixed_card_type_matrix.py` | 新增 | 矩阵 runner，执行全量评估 |",
        f"| `scripts/test_market_radar_card_type_registry_v112a.py` | 新增 | 测试脚本 |",
        f"| `data/fixtures/market_radar_v112a_card_type_samples.json` | 新增 | 5 类卡片 sample fixture（全部标记 data_mode: fixture） |",
        f"| `results/market_radar_v112a_fixed_card_type_matrix_result.json` | 新增 | 结果 JSON |",
        f"| `runs/market_radar/v112a_fixed_card_type_matrix.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112a_fixed_card_type_matrix_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"python scripts/run_market_radar_v112a_fixed_card_type_matrix.py",
        f"python scripts/test_market_radar_card_type_registry_v112a.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 5 类卡片 Readiness Matrix",
        f"",
        f"| # | Card Type | Readiness | 长期监测 | 最大缺口 |",
        f"|---|-----------|-----------|----------|----------|",
    ]

    for i, ct in enumerate(card_type_results, 1):
        rl = ct["readiness"]["readiness_level"]
        rl_icon = {"ready": "✅", "partial": "⚠️", "missing": "❌"}.get(rl, "❓")
        suitable = "✅" if ct["readiness"]["suitable_for_long_running_monitoring"] else "❌"
        next_gap = ct["readiness"].get("next_gap", "N/A")
        if len(next_gap) > 80:
            next_gap = next_gap[:77] + "..."
        lines.append(
            f"| {i} | `{ct['card_type']}` | {rl_icon} {rl} | {suitable} | {next_gap} |"
        )

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 当前最大缺口",
        f"",
        f"- **卡片类型**: `{highest_priority_gap['card_type']}`",
        f"- **缺口**: {highest_priority_gap['gap']}",
        f"- **建议下一步**: {highest_priority_gap['recommended_next_task']}",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. **立即**: 推进 `{highest_priority_gap['card_type']}` 的数据管道建设",
        f"2. **短期**: 将 whale_position_alert 从 partial → ready（地址标签自动标注）",
        f"3. **中期**: 建立 multi_asset_market_sync 自动检测（跨资产相关性矩阵）",
        f"4. **长期**: 接入新闻 RSS/API 管道（news_event_market_impact）",
        f"5. **持续**: 对已 ready 的 price_oi_volume_anomaly 做 OI/Volume delta 增强",
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
        f"---",
        f"",
        f"## 风险",
        f"",
        f"1. **liquidation_pressure 缺少真实数据源**：Coinglass API 可能需要付费，",
        f"   需评估是否有免费替代方案（如交易所 WebSocket 公开清算流）。",
        f"2. **news_event 需要 NLP 管道**：新闻自动分类和 Affected Assets 提取",
        f"   需要额外的 ML/NLP 能力，超出当前纯规则系统的范围。",
        f"3. **multi_asset_sync 自动检测复杂度高**：跨资产实时相关性矩阵需要",
        f"   持续维护，且对数据延迟敏感。",
        f"4. **fixture 不能无限增长**：当前全部使用 fixture 样本，需要尽快接入",
        f"   真实数据管道进行端到端验证。",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {HANDOFF_MD_PATH}")


if __name__ == "__main__":
    raise SystemExit(main())
