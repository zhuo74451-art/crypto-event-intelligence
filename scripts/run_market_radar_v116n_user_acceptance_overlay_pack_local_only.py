"""Market Radar v1.16-N — User Acceptance Overlay Pack (Local Only)

Reads v116L milestone pack outputs (manifest, acceptance matrix, TG evidence index)
and produces v116N user-acceptance-facing overlay documents.

This is a PRESENTATION-ONLY overlay — no external API calls, no TG sends, no AI calls,
no production writes, no file deletions, no modification of v116L or older artifacts.

v116N wraps v116L's "internal milestone pack" into a "deliverable acceptance pack" by:
  - Adding a one-pager acceptance summary with clear red lines
  - Explaining normal blockages (liquidation gate, whale evidence) as design, not failure
  - Providing a user decision tree with A/B/C next-step options
  - Creating a 10-minute demo sequence
  - Building a production readiness checklist (0/5)
  - Creating a whale manual evidence workbook template
  - Providing a user-facing operator review pack

Outputs (8 files):
  runs/market_radar/v116n_one_pager_acceptance_summary.md
  runs/market_radar/v116n_operator_review_pack_user_facing.md
  runs/market_radar/v116n_user_decision_tree.md
  runs/market_radar/v116n_demo_sequence_10min.md
  runs/market_radar/v116n_production_readiness_checklist.md
  runs/market_radar/v116n_whale_manual_evidence_checklist.md
  runs/market_radar/v116n_local_only_handoff.md
  results/market_radar_v116n_user_acceptance_overlay_manifest.json

Constraints:
  - NO external API calls
  - NO TG sends
  - NO AI/model calls
  - NO production writes
  - NO daemon/cron/loop
  - NO file deletion
  - NO modification of v116A-L historical artifacts
  - NO reading of API keys/tokens/cookies/passwords

Usage:
    python scripts/run_market_radar_v116n_user_acceptance_overlay_pack_local_only.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


# ── UTF-8 fix for Windows ─────────────────────────────────────────────────
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

TASK_ID = "20260605_v116n_market_radar_user_acceptance_overlay_pack_local_only"
RUN_ID = "20260605_124925.r07"
OVERLAY_VERSION = "v116N"
SOURCE_MILESTONE_VERSION = "v116L"
AUDIT_SOURCE = "v116M"

CARD_FAMILIES = [
    "whale_position_alert",
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "liquidation_pressure",
    "news_event_market_impact",
]

CARD_DISPLAY = {
    "whale_position_alert": "Whale Position Alert",
    "multi_asset_market_sync": "Multi-Asset Market Sync",
    "price_oi_volume_anomaly": "Price/OI/Volume Anomaly",
    "liquidation_pressure": "Liquidation Pressure",
    "news_event_market_impact": "News Event Market Impact",
}

VERSION_QUICK_REF = {
    "v116E": "Multi-Asset Market Sync — real E2E TG test sent",
    "v116G": "Price/OI/Volume Anomaly — real E2E TG test sent",
    "v116I": "Liquidation Pressure — real API attempt, gate blocked (calm market)",
    "v116J": "News Event Market Impact — real E2E TG test sent (public RSS + REST)",
    "v116K": "Five-card real E2E coverage audit",
    "v116L": "Real E2E milestone delivery pack aggregation",
    "v116M": "Gemini audit of v116L operator pack",
    "v116N": "User acceptance overlay pack (this version)",
}


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def china_stamp_iso() -> str:
    return datetime.now(CN_TZ).isoformat()


# ═══════════════════════════════════════════════════════════════════════════
# Source readers (v116L read-only)
# ═══════════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def read_v116l_manifest() -> dict:
    p = ROOT / "results" / "market_radar_v116l_milestone_pack_manifest.json"
    return load_json(p)


def read_v116l_acceptance_matrix() -> dict:
    p = ROOT / "results" / "market_radar_v116l_real_e2e_acceptance_matrix.json"
    return load_json(p)


def read_v116l_tg_evidence_index() -> list[dict]:
    p = ROOT / "results" / "market_radar_v116l_tg_evidence_index.jsonl"
    return load_jsonl(p)


# ═══════════════════════════════════════════════════════════════════════════
# Overlay Manifest
# ═══════════════════════════════════════════════════════════════════════════

def build_overlay_manifest(source_manifest: dict, source_acceptance: dict,
                           source_evidence: list[dict], files_created: list[str],
                           source_files_read: list[str]) -> dict:
    """Build the v116N overlay manifest."""

    return {
        "overlay_version": OVERLAY_VERSION,
        "source_milestone_version": SOURCE_MILESTONE_VERSION,
        "audit_source": AUDIT_SOURCE,
        "local_only": True,
        "external_api_called_this_run": False,
        "tg_sent_this_run": False,
        "production_send_ready_count": 0,
        "generated_at": china_stamp_iso(),
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "user_acceptance_ready_after_overlay": True,
        "overlay_type": "user_acceptance_presentation",
        "summary": source_manifest.get("summary", {}),
        "card_family_status_summary": {
            family: {
                "display_name": info.get("display_name", CARD_DISPLAY.get(family, family)),
                "real_e2e_status": info.get("real_e2e_status", "unknown"),
            }
            for family, info in source_manifest.get("card_family_status", {}).items()
        },
        "created_files": files_created,
        "source_files_read": source_files_read,
        "remaining_blockers": [
            {
                "blocker": "liquidation_pressure",
                "status": "gate_blocked_calm_market",
                "explanation": "Gate correctly blocked during calm market. NOT a bug. Rerun during high volatility.",
                "not_a_failure": True,
            },
            {
                "blocker": "whale_position_alert",
                "status": "manual_evidence_required",
                "explanation": "Requires human on-chain address attribution. Cannot be automated via free APIs. NOT a bug.",
                "not_a_failure": True,
            },
            {
                "blocker": "production_send",
                "status": "0/5 ready",
                "explanation": "No card family is production send ready. Requires explicit user approval, production target, secret preflight, and dry-run audit.",
                "not_a_failure": True,
            },
        ],
        "user_next_step_options": ["A", "B", "C"],
        "safety_constraints_verified": {
            "external_api_called_this_run": False,
            "public_source_called_this_run": False,
            "tg_sent_this_run": False,
            "prod_state_write": False,
            "ai_model_called": False,
            "daemon_or_loop_started": False,
            "files_deleted": False,
            "historical_artifacts_modified": False,
            "credentials_read": False,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# Output: One-Pager Acceptance Summary
# ═══════════════════════════════════════════════════════════════════════════

def write_one_pager(manifest: dict, acceptance: dict, evidence: list[dict]):
    path = ROOT / "runs" / "market_radar" / "v116n_one_pager_acceptance_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    s = manifest.get("summary", {})
    status = manifest.get("card_family_status", {})

    lines = []
    # ── Title ──
    lines.append("# Market Radar v116N One-Pager Acceptance Summary")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Overlay Version**: {OVERLAY_VERSION}")
    lines.append(f"**Source Milestone**: {SOURCE_MILESTONE_VERSION}")
    lines.append(f"**Audit Source**: {AUDIT_SOURCE}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── CRITICAL Red-Line Block ──
    lines.append("## CRITICAL: Production Status & Risk Warnings")
    lines.append("")
    lines.append("| Warning | Detail |")
    lines.append("|---------|--------|")
    lines.append("| **Production Readiness** | **0/5 — NOT FOR LIVE USE** |")
    lines.append("| TG test group sends | Are NOT production sends |")
    lines.append("| No daemon / cron / loop | Is enabled |")
    lines.append("| No automatic production publishing | Is enabled |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Status Matrix ──
    lines.append("## Status Matrix")
    lines.append("")
    lines.append("| Dimension | Score | Detail |")
    lines.append("|-----------|-------|--------|")
    lines.append(f"| Fixture E2E | **{s.get('fixture_e2e_passed', 'N/A')}** | All five card families pass fixture pipeline |")
    lines.append(f"| Real API / public source + TG test sent | **{s.get('real_api_public_source_tg_test_sent', 'N/A')}** | 3 families verified with real data |")
    lines.append(f"| Real API attempted but gate blocked | **{s.get('real_api_attempted_but_gate_blocked', 'N/A')}** | liquidation_pressure — gate correct, not a failure |")
    lines.append(f"| Manual evidence blocked | **{s.get('manual_evidence_blocked', 'N/A')}** | whale_position_alert — needs human evidence, not a failure |")
    lines.append(f"| Production send ready | **{s.get('production_send_ready', 'N/A')}** | No card family ready for production |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Three-Sentence Conclusion ──
    lines.append("## Three-Sentence Conclusion（三句话结论）")
    lines.append("")
    lines.append("1. **Market Radar 已完成五类卡片 fixture 覆盖。**")
    lines.append("2. **三类卡片已完成真实数据/公开来源 + TG test group one-shot 验证。**")
    lines.append("3. **当前仍不是 production ready，下一步应先由用户验收和确定优先级。**")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Two Normal Blockage Explanations ──
    lines.append("## 两个正常阻断解释")
    lines.append("")
    lines.append("### 1. Liquidation Pressure — Normal Gate Blockage")
    lines.append("")
    lines.append("- **Status**: `blocked_gate_not_passed`")
    lines.append("- **What happened**: v116I called Binance public REST, fetched BTC/ETH/SOL data successfully. Signals were generated for all 3 assets. The quality gate correctly blocked 0/3 signals due to calm market conditions.")
    lines.append("- **Why this is NOT a failure**:")
    lines.append("  - Gate paused / calm market — 正常阻断，不是程序故障")
    lines.append("  - The data pipeline (3/3 assets fetched) is verified")
    lines.append("  - The signal pipeline (3/3 signals generated) is verified")
    lines.append("  - The gate mechanism is verified (correctly blocks in calm market)")
    lines.append("- **Do NOT lower the gate**: Liquidation pressure is an event-triggered card. Lowering the threshold to force card generation would undermine the entire quality gate design.")
    lines.append("- **Right action**: Wait for high-volatility window, then one-shot rerun.")
    lines.append("")
    lines.append("### 2. Whale Position Alert — Normal Manual Evidence Blockage")
    lines.append("")
    lines.append("- **Status**: `blocked_manual_evidence`")
    lines.append("- **What happened**: Fixture E2E passed. Real E2E blocked because the operator workbook has empty fields for all 4 addresses. No free public API can provide on-chain address attribution.")
    lines.append("- **Why this is NOT a failure**:")
    lines.append("  - Blocked by manual evidence requirement / 需要人工证据，不是程序失败")
    lines.append("  - The pipeline (router, gate, formatting) is verified via fixture")
    lines.append("  - Fake evidence is worse than no evidence — whale_position_alert trust depends on real data")
    lines.append("- **Do NOT bypass**: Any automated attempt to guess address attribution would produce unreliable cards.")
    lines.append("- **Right action**: Complete the manual evidence workbook (see whale checklist).")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Five-Card Quick Status ──
    lines.append("## Five-Card Quick Status")
    lines.append("")
    lines.append("| # | Card Family | Fixture | Real API | TG Sent | Status |")
    lines.append("|---|-------------|---------|----------|---------|--------|")
    lines.append("| 1 | Whale Position Alert | ✅ | ❌ | ❌ | `blocked_manual_evidence` ⛔ |")
    lines.append("| 2 | Multi-Asset Market Sync | ✅ | ✅ | ✅ | `real_free_api_tg_test_sent` ⭐ |")
    lines.append("| 3 | Price/OI/Volume Anomaly | ✅ | ✅ | ✅ | `real_free_api_tg_test_sent` ⭐ |")
    lines.append("| 4 | Liquidation Pressure | ✅ | ✅ | ❌ | `blocked_gate_not_passed` ⚠ |")
    lines.append("| 5 | News Event Market Impact | ✅ | ✅ | ✅ | `real_free_public_source_tg_test_sent` ⭐ |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── TG Evidence Summary ──
    lines.append("## TG Evidence Summary")
    lines.append("")
    lines.append(f"- **Total TG test sends**: {len(evidence)} messages (all redacted)")
    lines.append("- **Breakdown**: 1 multi_asset_market_sync + 2 price_oi_volume_anomaly + 2 news_event_market_impact")
    lines.append("- **All message proofs**: SHA-256 redacted fingerprints (verifiable in TG test group)")
    lines.append("- **All production_send**: False")
    lines.append("- **All credentials_printed**: False")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── User Next Step: Three Choices ──
    lines.append("## 用户下一步：三选一")
    lines.append("")
    lines.append("| Option | Action | When to Choose |")
    lines.append("|--------|--------|---------------|")
    lines.append("| **A** | 接受当前里程碑，进入下一阶段优先级选择 | You're satisfied with the 3/5 real E2E demo and want to proceed to roadmap planning |")
    lines.append("| **B** | 先补 whale manual evidence checklist/workbook | Whale position alert is your top priority card family |")
    lines.append("| **C** | 等待高波动窗口后 rerun liquidation_pressure one-shot | Liquidation pressure is your top priority and you want to wait for a volatile market window |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Explicitly NOT Recommended ──
    lines.append("## 明确不建议")
    lines.append("")
    lines.append("| Not Recommended | Why |")
    lines.append("|-----------------|-----|")
    lines.append("| 🔴 现在进入 production send | 0/5 production ready; no user approval; no production target defined |")
    lines.append("| 🔴 降低 liquidation gate | Would destroy gate trust; undervalues the card family's design |")
    lines.append("| 🔴 绕过 whale evidence | Fake evidence = unreliable cards; defeats the purpose |")
    lines.append("| 🔴 启用 daemon/cron/loop | System is one-shot mode only; no persistent infrastructure yet |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Footer ──
    lines.append("## What Was Read to Generate This Report")
    lines.append("")
    lines.append("- `results/market_radar_v116l_milestone_pack_manifest.json`")
    lines.append("- `results/market_radar_v116l_real_e2e_acceptance_matrix.json`")
    lines.append("- `results/market_radar_v116l_tg_evidence_index.jsonl`")
    lines.append("")
    lines.append("> This is a presentation overlay. No v116L factual data was altered. No external APIs, TG sends, or production writes were performed in this run.")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Output: Operator Review Pack (User-Facing)
# ═══════════════════════════════════════════════════════════════════════════

def write_operator_review_pack_user_facing(manifest: dict, acceptance: dict, evidence: list[dict]):
    path = ROOT / "runs" / "market_radar" / "v116n_operator_review_pack_user_facing.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Market Radar v116N — Operator Review Pack (User-Facing)")
    lines.append("")
    lines.append("> **面向非技术用户 / 项目 Owner 的运营复核包**")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Overlay Version**: {OVERLAY_VERSION}")
    lines.append(f"**Source Milestone**: {SOURCE_MILESTONE_VERSION}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Version Quick-Reference Table ──
    lines.append("## 版本号速查表")
    lines.append("")
    lines.append("如果你看到 v116E/G/I/J/K/L/M/N，先查此表：")
    lines.append("")
    lines.append("| Version | What It Did |")
    lines.append("|---------|-------------|")
    for ver, desc in VERSION_QUICK_REF.items():
        lines.append(f"| {ver} | {desc} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── What CAN be demonstrated now ──
    lines.append("## 当前已能演示什么")
    lines.append("")
    lines.append("### ✅ 三类卡片已完成真实 E2E TG 测试发送")
    lines.append("")
    lines.append("**1. Multi-Asset Market Sync**")
    lines.append("- 使用 Binance 公开 API（无需 API Key），采集 BTC/ETH/SOL 三资产数据")
    lines.append("- 成功检测到市场同步下行风险（score=59.8）")
    lines.append("- 完整通过 quality gate + send readiness + secret preflight")
    lines.append("- 已通过 TG test group one-shot 发送 1 张卡片")
    lines.append("")
    lines.append("**2. Price/OI/Volume Anomaly**")
    lines.append("- 使用 Binance 公开 API 采集三资产价格/持仓量/交易量数据")
    lines.append("- 2/3 资产通过入场门禁（ETH -4.44%, SOL -5.46%）；BTC 被门禁正确拒绝")
    lines.append("- 已通过 TG test group one-shot 发送 2 张卡片")
    lines.append("")
    lines.append("**3. News Event Market Impact**")
    lines.append("- 使用 Binance 公开 RSS + REST（无需 API Key），采集 80 篇文章")
    lines.append("- 7 个事件被提取，2 个通过门禁")
    lines.append("- 已通过 TG test group one-shot 发送 2 张卡片")
    lines.append("")
    lines.append("### ✅ 五类卡片的 Fixture E2E 全部通过")
    lines.append("- 意味着所有五类卡片的算法管道、门禁逻辑、格式化流程均已验证")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── What It CANNOT Be Misunderstood As (moved to front as required) ──
    lines.append("## 不能被误解成什么")
    lines.append("")
    lines.append("### ❌ 不是 production send ready")
    lines.append("- **0/5** 类卡片达到生产发送就绪状态")
    lines.append("- TG 发送仅限 test group，不可用于生产频道")
    lines.append("- 所有卡片为 one-shot 发送，不存在 daemon/loop/定时任务")
    lines.append("")
    lines.append("### ❌ 不是完整的产品")
    lines.append("- 这是真实 E2E 里程碑交付包，证明核心管道在真实数据下工作")
    lines.append("- 到产品级系统还有空间：持久化、监控、运维、用户自定义等")
    lines.append("")
    lines.append("### ❌ 不是 5/5 完成")
    lines.append("- 只有 3/5 类卡片完成了真实 TG 测试发送")
    lines.append('- 另外 2/5 不是"未完成"而是"有设计的阻塞"（见下）')
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── SHA-256 Proof Explanation ──
    lines.append("## SHA-256 消息证明说明")
    lines.append("")
    lines.append("文档中出现的 `sha256:xxxxxxxxxxxxxxxx` 是**脱敏后的指纹**，不是要求用户手动复算。")
    lines.append("- 它是 TG 消息内容的 SHA-256 哈希前 16 位")
    lines.append("- 作用是：在 TG test group 中按相同算法对消息内容取哈希，如果匹配，就证明消息未被篡改")
    lines.append("- **你不会看到 raw token、raw chat_id、raw message_id** — 这些都是脱敏的")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Evidence Summary Table ──
    lines.append("## 三类已验证卡片的证据摘要")
    lines.append("")
    lines.append("| 卡片类型 | 数据源 | API Type | TG 消息数 | 消息证明（脱敏） |")
    lines.append("|----------|--------|----------|-----------|------------------|")
    lines.append("| Multi-Asset Market Sync | Binance 公开 API | Free REST | 1 | `sha256:4fbb9cf6972a100c` |")
    lines.append("| Price/OI/Volume Anomaly | Binance 公开 API | Free REST | 2 | `sha256:3045ad039274b9fc`, `sha256:1070a982af22fe71` |")
    lines.append("| News Event Market Impact | Binance RSS + REST | Free RSS | 2 | `sha256:9d1ef11e7923e54a`, `sha256:9dc6abc967dad3e2` |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── News Event Risk Disclaimer (NEW standalone item) ──
    lines.append("## News Event Market Impact — 重要风险声明")
    lines.append("")
    lines.append("### ⚠️ News Event Market Impact is observation, not causal proof")
    lines.append("")
    lines.append("**事件影响观察，不构成因果证明。**")
    lines.append("")
    lines.append("- News event cards show **correlation between events and price movements**, not causation.")
    lines.append("- An article mentioning BTC price movement does not prove the event caused the movement.")
    lines.append("- Multiple factors affect price: the observed event is only one of many possible contributors.")
    lines.append("- **Do not use these cards as trading signals.** They are informational observations only.")
    lines.append("- All news event cards carry this disclaimer in the TG message body.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Two Blocked Cards — Real Explanation ──
    lines.append("## 两类未完成卡片的真实阻塞")
    lines.append("")
    lines.append("### Liquidation Pressure — Gate 正确阻断（正常，不是故障）")
    lines.append("")
    lines.append("- **阻塞原因**：当前市场处于 calm market 状态，平仓压力门禁所有信号均未通过")
    lines.append("- **已完成**：Binance 公开 REST 数据管道验证通过（3/3 assets fetched）")
    lines.append("- **已完成**：信号处理管道验证通过（3/3 signals generated）")
    lines.append("- **已完成**：Gate 机制验证通过（在 calm market 下正确阻断）")
    lines.append("- **下一步**：等待市场波动增大时 one-shot rerun，不降低 gate 阈值")
    lines.append("")
    lines.append("### Whale Position Alert — 需要人工证据（正常，不是故障）")
    lines.append("")
    lines.append("- **阻塞原因**：Operator workbook 中 4 个地址的字段均为空，免费公开 API 无法提供地址归因信息")
    lines.append("- **已完成**：Fixture E2E 管道验证通过（4/4 地址 workflow-ready）")
    lines.append("- **已完成**：Router、门禁、格式化流程均验证通过")
    lines.append("- **下一步**：完成人工地址证据收集（见 whale evidence checklist）")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Why NOT lower liquidation gate ──
    lines.append("## 为什么 liquidation 不应降 gate")
    lines.append("")
    lines.append("1. Gate 行为正确：在 calm market 下正确阻断，证明了门禁系统的有效性")
    lines.append("2. 降低阈值会削弱信任度：如果人为降低阈值来制造\"成功\"，整个 quality gate 设计将被架空")
    lines.append("3. liquidation_pressure 是事件触发型卡片：它的价值在于高波动市场时的预警")
    lines.append("4. 数据管道已验证：3/3 assets fetched + 3/3 signals generated")
    lines.append("5. 正确做法：等待市场波动增大时重新 one-shot 运行")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Next Steps for User ──
    lines.append("## 下一步人工复核建议")
    lines.append("")
    lines.append("1. **复核 TG test group 中的实际消息**：使用指纹在 test group 中确认 5 条消息")
    lines.append("2. **复核 acceptance matrix**：确认五类卡片的状态与理解一致")
    lines.append("3. **选择 liquidity 下一步**：确认标记为 `future_volatility_rerun` 是否可接受")
    lines.append("4. **选择 whale 下一步**：是否启动 manual evidence collection")
    lines.append("5. **确认 demo 边界和路线图优先级**：见 decision tree 文档")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Output: User Decision Tree
# ═══════════════════════════════════════════════════════════════════════════

def write_user_decision_tree(manifest: dict):
    path = ROOT / "runs" / "market_radar" / "v116n_user_decision_tree.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    s = manifest.get("summary", {})

    lines = []
    lines.append("# Market Radar v116N — User Decision Tree")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Overlay Version**: {OVERLAY_VERSION}")
    lines.append("")
    lines.append("> 下图帮助你从当前里程碑状态出发，选择下一步行动路径。")
    lines.append("> 当前状态：Fixture E2E 5/5 | Real TG Sent 3/5 | Gate Blocked 1/5 | Manual Blocked 1/5 | Production 0/5")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Decision Tree")
    lines.append("")
    lines.append("```")
    lines.append("START: v116N Milestone Package")
    lines.append("│")
    lines.append("├─ Q: 你认可当前 demo 边界吗？")
    lines.append("│   (3/5 real E2E TG sent, 2/5 with design-justified blocks)")
    lines.append("│   │")
    lines.append("│   ├─ YES → 【路径 A】接受当前里程碑，进入下一阶段优先级选择")
    lines.append("│   │         → 阅读 v116l_next_phase_roadmap.md")
    lines.append("│   │         → 讨论 P0-P4 优先级排序")
    lines.append("│   │         → 确认下一步执行计划")
    lines.append("│   │")
    lines.append("│   └─ NO → 回到具体关切：")
    lines.append("│       │")
    lines.append("│       ├─ 最关心 whale → 【路径 B】")
    lines.append("│       │   → 先补人工证据 workbook")
    lines.append("│       │   → 阅读 v116n_whale_manual_evidence_checklist.md")
    lines.append("│       │   → 完成 4 个地址的归属验证")
    lines.append("│       │   → rerun v115R submission validator + v115Q fixture E2E gate")
    lines.append("│       │")
    lines.append("│       └─ 最关心 liquidation → 【路径 C】")
    lines.append("│           → 等待高波动窗口")
    lines.append("│           → 不降低 gate 阈值")
    lines.append("│           → one-shot rerun when: OI delta > threshold OR")
    lines.append("│             funding rate extreme OR L/S ratio shift")
    lines.append("│")
    lines.append("├─ Q: 你想上线生产吗？")
    lines.append("│   │")
    lines.append("│   └─ 不管选什么 → 先建立 production readiness gate")
    lines.append("│       → 阅读 v116n_production_readiness_checklist.md")
    lines.append("│       → 当前 0/5，不允许直接上线")
    lines.append("│       → 必须满足 6 个最低条件后才能进入 production send 流程")
    lines.append("│")
    lines.append("└─ Q: 你只想做作品集 / demo？")
    lines.append("    │")
    lines.append("    └─ YES → 当前可进入 demo 包整理")
    lines.append("        → 阅读 v116n_demo_sequence_10min.md")
    lines.append("        → 使用 10 分钟展示顺序进行演示")
    lines.append("        → 当前 3/5 类卡片可真实演示")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 三选项详细说明")
    lines.append("")
    lines.append("### 路径 A：接受当前里程碑，进入优先级选择")
    lines.append("")
    lines.append("- **适合**：你对 3/5 real E2E demo + 2/5 justified blocks 的状态满意")
    lines.append("- **下一步**：")
    lines.append("  1. 确认 v116L 交付包的内容和状态")
    lines.append("  2. 阅读 `v116l_next_phase_roadmap.md` 了解 P0-P4 路线图")
    lines.append("  3. 共同排序下一步优先级（adapter abstraction, Gemini audit, etc.）")
    lines.append("- **风险**：无 — 这是当前设计路径的延续")
    lines.append("")
    lines.append("### 路径 B：先补 whale manual evidence")
    lines.append("")
    lines.append("- **适合**：Whale position alert 是你的最高优先级卡片")
    lines.append("- **下一步**：")
    lines.append("  1. 阅读 `v116n_whale_manual_evidence_checklist.md`")
    lines.append("  2. 收集 4 个地址的链上归属证据")
    lines.append("  3. 填入 operator workbook")
    lines.append("  4. 重新运行 v115R submission validator + v115Q fixture E2E gate")
    lines.append("- **风险**：人工证据收集可能耗时，取决于地址复杂度")
    lines.append("")
    lines.append("### 路径 C：等待高波动，rerun liquidation")
    lines.append("")
    lines.append("- **适合**：Liquidation pressure 是你的最高优先级，且你愿意等待市场波动")
    lines.append("- **触发条件（任一满足）**：")
    lines.append("  - BTC/ETH/SOL 中任一资产 24h OI delta 超过配置阈值")
    lines.append("  - Funding rate 达到极端值（正或负）")
    lines.append("  - Long/Short ratio 出现显著偏移")
    lines.append("- **执行方式**：one-shot（不开启 daemon/cron/loop）")
    lines.append("- **安全约束**：不降低 admission threshold，不绕过 quality gate")
    lines.append("- **风险**：Gate 阈值是设计阶段的设定；如果多次 rerun 仍不通过，需要复盘阈值合理性")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 红线规则（适用于所有路径）")
    lines.append("")
    lines.append("| 规则 | 原因 |")
    lines.append("|------|------|")
    lines.append("| 不允许直接上线生产 | 0/5 production ready |")
    lines.append("| 不允许降低 liquidation gate | 会破坏 gate 信任度 |")
    lines.append("| 不允许绕过 whale evidence | 虚假证据 = 不可靠卡片 |")
    lines.append("| 不允许启用 daemon/cron/loop | 系统为 one-shot 模式 |")
    lines.append("| 不允许调用付费 API | 当前数据源均为免费公开 API |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Output: Demo Sequence (10 min)
# ═══════════════════════════════════════════════════════════════════════════

def write_demo_sequence_10min(manifest: dict):
    path = ROOT / "runs" / "market_radar" / "v116n_demo_sequence_10min.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    s = manifest.get("summary", {})

    lines = []
    lines.append("# Market Radar v116N — 10-Minute Demo Sequence")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append("**Total Time**: 10 minutes")
    lines.append("")
    lines.append("> 本顺序面向项目 Owner / 非技术用户，重点在于「展示边界、说清红线、给决策路径」。")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Segment 1
    lines.append("## Segment 1: 看 One-Pager 红线 (1 min)")
    lines.append("")
    lines.append("**打开**: `runs/market_radar/v116n_one_pager_acceptance_summary.md`")
    lines.append("")
    lines.append("**说清楚 3 件事**：")
    lines.append("1. Production Readiness: **0/5 — NOT FOR LIVE USE**")
    lines.append("2. TG test group sends ≠ production sends")
    lines.append("3. No daemon, no cron, no loop — 全部 one-shot")
    lines.append("")
    lines.append("**关键句**：「这是我们目前最诚实的状态 — 能做什么，不能做什么，都写在这一页。」")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Segment 2
    lines.append("## Segment 2: Five-Card 状态矩阵 (2 min)")
    lines.append("")
    lines.append("**展示**：五类卡片一览表")
    lines.append("")
    lines.append("| Card Family | Status | Meaning |")
    lines.append("|-------------|--------|---------|")
    lines.append("| Whale Position Alert | `blocked_manual_evidence` | 管道就绪，需人工链上证据 |")
    lines.append("| Multi-Asset Market Sync | `real_free_api_tg_test_sent` | ✅ 已真实验证 |")
    lines.append("| Price/OI/Volume Anomaly | `real_free_api_tg_test_sent` | ✅ 已真实验证 |")
    lines.append("| Liquidation Pressure | `blocked_gate_not_passed` | 管道就绪，等波动 |")
    lines.append("| News Event Market Impact | `real_free_public_source_tg_test_sent` | ✅ 已真实验证 |")
    lines.append("")
    lines.append("**关键句**：「五类卡片的设计管道全部验证完毕，3 类已走通全链路到 TG test group。剩下 2 类的阻塞是可解释的设计决定，不是 bug。」")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Segment 3
    lines.append("## Segment 3: Multi-Asset Market Sync (2 min)")
    lines.append("")
    lines.append("**展示内容**：")
    lines.append("- 数据来源：Binance 公开 API（BTCUSDT, ETHUSDT, SOLUSDT），无需 API Key")
    lines.append("- 检测结果：市场同步下行风险，score=59.8, direction=down")
    lines.append("- 门禁状态：quality_gate PASSED, send_readiness PASSED, secret_preflight PASSED")
    lines.append("- TG 发送：1 张卡片 → test group")
    lines.append("- 消息证明：`sha256:4fbb9cf6972a100c`")
    lines.append("")
    lines.append("**关键句**：「这是最早完成的真实 E2E 卡片，证明了从公开 API 到 TG test group 的全链路可以跑通。」")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Segment 4
    lines.append("## Segment 4: Price/OI/Volume Anomaly (2 min)")
    lines.append("")
    lines.append("**展示内容**：")
    lines.append("- 数据来源：Binance 公开 API（BTCUSDT, ETHUSDT, SOLUSDT）")
    lines.append("- 信号情况：2/3 资产通过入场门禁")
    lines.append("  - ETH: -4.44% → admitted ✅")
    lines.append("  - SOL: -5.46% → admitted ✅")
    lines.append("  - BTC: -2.24% → correctly rejected (gate working)")
    lines.append("- TG 发送：2 张卡片（ETH, SOL）→ test group")
    lines.append("")
    lines.append("**关键句**：「注意 BTC 被门禁拒绝了 — 这不是 bug，而是 gate 正确的行为。价格变化不够大，就不过。这和 liquidation pressure 的 gate block 是同一个设计逻辑。」")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Segment 5
    lines.append("## Segment 5: News Event Market Impact (1.5 min)")
    lines.append("")
    lines.append("**展示内容**：")
    lines.append("- 数据来源：Binance 公开 RSS + REST，5 sources attempted, 1 succeeded")
    lines.append("- 80 articles fetched → 7 events extracted → 2 admitted")
    lines.append("- TG 发送：2 张卡片 → test group")
    lines.append("")
    lines.append("### ⚠️ 强调：不是因果证明")
    lines.append("")
    lines.append("**必须明确说出来**：「这个卡片展示的是事件和价格的相关性观察，NOT 因果证明。")
    lines.append("一篇新闻提到 BTC 涨了，不代表新闻导致了涨。可能有其他因素。")
    lines.append("所有 TG 消息都已标注这个风险声明。")
    lines.append("**不要将这些卡片当作交易信号。**」")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Segment 6
    lines.append("## Segment 6: Liquidation & Whale 正常阻断解释 (1.5 min)")
    lines.append("")
    lines.append("### Liquidation Pressure — 正常 Gate Block")
    lines.append("")
    lines.append("- 展示：3/3 assets fetched, 3/3 signals generated, **0/3 admitted**")
    lines.append("- 解释：「Gate 在 calm market 下正确阻断了所有信号。这不是 bug。")
    lines.append("  liquidation_pressure 是事件触发型卡片 — 它的价值在高波动市场。")
    lines.append("  我们现在不是在 calm market 硬发一张没意义的卡片，而是在等正确的时机。」")
    lines.append("- 明确：「**不建议降低 gate 阈值。** 降低阈值等于架空了 gate 设计。」")
    lines.append("")
    lines.append("### Whale Position Alert — 正常 Manual Evidence Block")
    lines.append("")
    lines.append("- 展示：Fixture E2E passed, 4/4 addresses workflow-ready, **evidence workbook empty**")
    lines.append("- 解释：「免费公开 API 无法回答『这个地址是谁的』。")
    lines.append("  这不是技术问题，是信息问题。")
    lines.append("  我们需要人工确认这 4 个地址的归属（交易所、做市商、鲸鱼等）。")
    lines.append("  在没有证据的情况下生成卡片，比不发更糟。」")
    lines.append("- 明确：「**不建议绕过 manual evidence。** 虚假证据 = 不可靠卡片。」")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Wrap-up
    lines.append("## Demo Wrap-Up")
    lines.append("")
    lines.append("**结束时三句话**：")
    lines.append("")
    lines.append("1. 「Market Radar 的核心管道已经验证 — 5/5 fixture, 3/5 real E2E TG test sent。」")
    lines.append("2. 「剩下的 2/5 是设计上的阻塞，不是失败 — 人工证据和等待波动都是正确的做法。」")
    lines.append("3. 「下一步由你决定 — A 接受里程碑进入路线图，B 先补 whale 证据，还是 C 等波动 rerun liquidation。」")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Output: Production Readiness Checklist
# ═══════════════════════════════════════════════════════════════════════════

def write_production_readiness_checklist(manifest: dict):
    path = ROOT / "runs" / "market_radar" / "v116n_production_readiness_checklist.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Market Radar v116N — Production Readiness Checklist")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Overlay Version**: {OVERLAY_VERSION}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 当前结论")
    lines.append("")
    lines.append("| Metric | Status |")
    lines.append("|--------|--------|")
    lines.append("| **Production Readiness** | **0/5 — NOT READY FOR PRODUCTION** |")
    lines.append("| TG test group sends | 5 messages (test only) |")
    lines.append("| Production sends | 0 (none) |")
    lines.append("| Daemon/cron/loop enabled | No |")
    lines.append("| Automatic publishing enabled | No |")
    lines.append("")
    lines.append("当前不满足生产发送的任何条件。以下是最低要求：")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Production Send 最低条件")
    lines.append("")
    lines.append("以下 6 项条件**必须全部满足**，缺一不可：")
    lines.append("")
    lines.append("### 1. 明确用户批准")
    lines.append("")
    lines.append("- [ ] ❌ 未完成")
    lines.append("- **要求**：用户（项目 Owner）明确确认生产发送的目标频道、频率和范围")
    lines.append("- **当前状态**：未获取批准")
    lines.append("")
    lines.append("### 2. Production Target 明确")
    lines.append("")
    lines.append("- [ ] ❌ 未完成")
    lines.append("- **要求**：生产发送的 TG channel/group 已经明确指定")
    lines.append("- **当前状态**：仅配置了 test group target")
    lines.append("- **注意**：production target ≠ test group target")
    lines.append("")
    lines.append("### 3. Secret Preflight 通过")
    lines.append("")
    lines.append("- [ ] ❌ 未完成")
    lines.append("- **要求**：所有 credential（token, chat_id）经过脱敏检查，无 raw secret 出现在输出中")
    lines.append("- **当前状态**：v116L 验证脱敏正确，但尚未对 production target credential 进行 preflight")
    lines.append("")
    lines.append("### 4. Send-Readiness Gate 通过")
    lines.append("")
    lines.append("- [ ] ❌ 未完成")
    lines.append("- **要求**：每类卡片独立通过 send_readiness gate")
    lines.append("- **当前状态**：0/5 类卡片通过 production send-readiness gate")
    lines.append("")
    lines.append("### 5. Dry-Run Artifact 可审计")
    lines.append("")
    lines.append("- [ ] ❌ 未完成")
    lines.append("- **要求**：生产发送前必须有 dry-run 产生可审计的 artifact（消息内容、时间、目标）")
    lines.append("- **当前状态**：无 dry-run 可审计 artifact")
    lines.append("")
    lines.append("### 6. Rollback / Stop Path 明确")
    lines.append("")
    lines.append("- [ ] ❌ 未完成")
    lines.append("- **要求**：明确生产发送的停止路径和回滚方式")
    lines.append("- **当前状态**：仅支持 one-shot 手动执行，无自动化 rollback 设计")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 默认安全约束")
    lines.append("")
    lines.append("以下约束始终生效，不受 production send 状态影响：")
    lines.append("")
    lines.append("| 约束 | 说明 |")
    lines.append("|------|------|")
    lines.append("| **No daemon by default** | 系统默认为 one-shot 模式，不开启任何常驻进程 |")
    lines.append("| **No cron/loop by default** | 不开启定时任务或循环 |")
    lines.append("| **No automatic publishing** | 不自动发布到任何生产目标 |")
    lines.append("| **All sends are one-shot** | 所有发送均为手动触发的单次发送 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 当前不满足这些条件的原因")
    lines.append("")
    lines.append("| # | 条件 | 缺失原因 |")
    lines.append("|---|------|----------|")
    lines.append("| 1 | 用户批准 | 用户尚未验收 v116L/v116N 交付包，尚未选择下一步路径 |")
    lines.append("| 2 | Production target | 未指定生产目标频道 |")
    lines.append("| 3 | Secret preflight | 未对 production target credential 执行 preflight |")
    lines.append("| 4 | Send-readiness gate | 0/5 类卡片通过 production send-readiness |")
    lines.append("| 5 | Dry-run artifact | 无 production dry-run |")
    lines.append("| 6 | Rollback path | 无自动化 rollback 设计 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 显式禁止")
    lines.append("")
    lines.append("| 禁止行为 | 原因 |")
    lines.append("|----------|------|")
    lines.append("| 现在进入 production send | 6 项最低条件均未满足 |")
    lines.append("| 跳过用户验收直接发送 | 违反开发安全流程 |")
    lines.append("| 在无 dry-run 情况下发送 | 不可审计 |")
    lines.append("| 使用 test group credentials 做生产发送 | credential scope 不匹配 |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Output: Whale Manual Evidence Checklist
# ═══════════════════════════════════════════════════════════════════════════

def write_whale_manual_evidence_checklist(manifest: dict):
    path = ROOT / "runs" / "market_radar" / "v116n_whale_manual_evidence_checklist.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Market Radar v116N — Whale Position Alert Manual Evidence Checklist")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Overlay Version**: {OVERLAY_VERSION}")
    lines.append("")
    lines.append("> 本文档说明：要完成 whale_position_alert 的真实 E2E TG test send，")
    lines.append("> 用户/operator 需要提供哪些人工证据。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 当前状态")
    lines.append("")
    lines.append("- **卡类型**: whale_position_alert")
    lines.append("- **Real E2E 状态**: `blocked_manual_evidence`")
    lines.append("- **Fixture E2E**: ✅ Passed（4/4 地址 workflow-ready）")
    lines.append("- **阻塞原因**: Operator workbook 中 4 个地址的字段均为空")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 用户需要提供什么人工证据")
    lines.append("")
    lines.append("对于每个监控地址，请填写以下信息：")
    lines.append("")
    lines.append("### 每个地址必须收集")
    lines.append("")
    lines.append("| # | 证据类型 | 说明 | 示例 |")
    lines.append("|---|----------|------|------|")
    lines.append("| 1 | **地址标签 / 归属** | 这个地址属于谁？ | 交易所热钱包、做市商、已知鲸鱼、机构地址 |")
    lines.append("| 2 | **标签来源** | 从哪里确认的归属？ | Etherscan 标签、Nansen、Arkham、链上分析师报告 |")
    lines.append("| 3 | **仓位变化证据** | 地址最近的仓位发生了什么变化？ | 大额转入/转出、开仓/平仓记录、借贷操作 |")
    lines.append("| 4 | **时间窗口** | 仓位变化发生在什么时间范围？ | 例如：2026-06-01 到 2026-06-05 |")
    lines.append("| 5 | **置信度评估** | 对上述证据的置信度？ | High / Medium / Low + 简述理由 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 地址 / 实体标签来源")
    lines.append("")
    lines.append("以下是可用的公开信息来源（均为免费公开服务）：")
    lines.append("")
    lines.append("| 来源 | 类型 | 说明 |")
    lines.append("|------|------|------|")
    lines.append("| Etherscan | 区块浏览器 | 提供部分地址标签（交易所、项目方等） |")
    lines.append("| Solscan | 区块浏览器 | Solana 地址标签 |")
    lines.append("| BscScan | 区块浏览器 | BSC 地址标签 |")
    lines.append("| Arkham Intelligence | 链上分析 | 免费层提供部分地址标签 |")
    lines.append("| Nansen | 链上分析 | 免费层提供有限标签 |")
    lines.append("| 公开链上分析师报告 | 人工分析 | Twitter/X、Substack 等平台的分析师报告 |")
    lines.append("")
    lines.append("> ⚠️ 以上来源的标签可能有误 — 请交叉验证，不要依赖单一来源。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 仓位变化证据")
    lines.append("")
    lines.append("对于每个地址，请记录任何最近的显著仓位变化：")
    lines.append("")
    lines.append("- **转账记录**：大额转入/转出（提供 tx hash 或区块浏览器链接）")
    lines.append("- **交易所交互**：与 CEX/DEX 的交互记录")
    lines.append("- **借贷协议交互**：抵押、借款、还款操作")
    lines.append("- **衍生品仓位**：永续合约、期权等相关操作")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 时间窗口")
    lines.append("")
    lines.append("建议关注的时间窗口：")
    lines.append("")
    lines.append("- **短期窗口**: 过去 24 小时（适合实时 alert）")
    lines.append("- **中期窗口**: 过去 7 天（适合趋势判断）")
    lines.append("- **长期窗口**: 过去 30 天（适合地址行为模式分析）")
    lines.append("")
    lines.append("请根据你关注的 whale 行为类型选择合适时间窗口。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 风险说明")
    lines.append("")
    lines.append("| 风险 | 说明 | 缓解方式 |")
    lines.append("|------|------|----------|")
    lines.append("| 地址标签错误 | 公开标签服务可能将地址错误归因 | 交叉验证多个来源 |")
    lines.append("| 地址行为变化 | 地址归属可能随时间变化（如交易所更换热钱包） | 定期复核标签有效性 |")
    lines.append("| 证据不完整 | 部分链上数据可能不公开（如 OTC 交易） | 明确标注数据完整度 |")
    lines.append("| 时间延迟 | 链上数据有延迟（区块确认时间） | 注意时间戳与实际发生的差异 |")
    lines.append("| 虚假信息 | 公开分析师报告可能包含推测或错误信息 | 优先使用可验证的链上数据 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 显式禁止")
    lines.append("")
    lines.append("| 禁止行为 | 原因 |")
    lines.append("|----------|------|")
    lines.append("| 🔴 **不允许自动猜测地址归因** | 免费 API 无法可靠地确定地址归属 |")
    lines.append("| 🔴 **不允许没有证据就生成真实 whale_position_alert** | 虚假证据比没有证据更糟 — 卡片将不可靠 |")
    lines.append("| 🔴 **不允许使用 mock 数据填充 workbook 并声称真实** | 破坏 whale_position_alert 的信任基础 |")
    lines.append("| 🔴 **不允许用 AI/LLM 推测地址归属** | AI 推测不可靠且不可审计 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Workbook Template")
    lines.append("")
    lines.append("以下是手动填写的 workbook 模板。每个地址一行，完成后可用于 v115R submission validator。")
    lines.append("")
    lines.append("```")
    lines.append("| Address | Label | Label Source | Position Change | Time Window | Confidence | Evidence Link |")
    lines.append("|---------|-------|-------------|-----------------|-------------|------------|---------------|")
    lines.append("| 0x...   | ???   | ???         | ???             | ???         | ???        | ???           |")
    lines.append("| 0x...   | ???   | ???         | ???             | ???         | ???        | ???           |")
    lines.append("| 0x...   | ???   | ???         | ???             | ???         | ???        | ???           |")
    lines.append("| 0x...   | ???   | ???         | ???             | ???         | ???        | ???           |")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 完成后")
    lines.append("")
    lines.append("Workbook 填写完毕后，执行以下步骤：")
    lines.append("")
    lines.append("1. 将 workbook 填入 operator evidence 文件（v115O preflight 范围）")
    lines.append("2. 运行 v115R submission validator 检查数据格式和完整性")
    lines.append("3. 运行 v115Q fixture E2E gate 验证管道")
    lines.append("4. 最后运行 whale_position_alert real E2E one-shot + TG test send")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Output: Local-Only Handoff
# ═══════════════════════════════════════════════════════════════════════════

def write_local_only_handoff(files_created: list[str], source_files_read: list[str]):
    path = ROOT / "runs" / "market_radar" / "v116n_local_only_handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Market Radar v116N — Local-Only Handoff")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Overlay Version**: {OVERLAY_VERSION}")
    lines.append(f"**Source Milestone**: {SOURCE_MILESTONE_VERSION}")
    lines.append(f"**Task ID**: {TASK_ID}")
    lines.append(f"**Run ID**: {RUN_ID}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 本轮做了什么")
    lines.append("")
    lines.append("本轮只做验收呈现增强（user acceptance overlay），具体包括：")
    lines.append("")
    lines.append("- 补齐一页式验收摘要（one-pager）")
    lines.append("- 明确 Production Ready 0/5 红线")
    lines.append("- 明确 liquidation / whale 的正常阻断解释（不是故障）")
    lines.append("- 给出用户清晰的 A/B/C 下一步决策选项")
    lines.append("- 将 v116L 从「内部里程碑包」包装成「可交付验收包」")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 没有改变什么")
    lines.append("")
    lines.append("| v116L 数据 | 是否修改 |")
    lines.append("|------------|----------|")
    lines.append("| manifest JSON | ❌ 未修改（只读） |")
    lines.append("| acceptance matrix JSON | ❌ 未修改（只读） |")
    lines.append("| TG evidence index JSONL | ❌ 未修改（只读） |")
    lines.append("| v116L Markdown 文件 | ❌ 未修改（只读） |")
    lines.append("| v116A-K 历史产物 | ❌ 未修改 |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## New Files Created")
    lines.append("")
    lines.append("| File | Type | Description |")
    lines.append("|------|------|-------------|")
    for f in files_created:
        ftype = f.split(".")[-1] if "." in f else "unknown"
        lines.append(f"| `{f}` | {ftype} | v116N user acceptance overlay output |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Source Files Read (Read-Only)")
    lines.append("")
    lines.append("| File |")
    lines.append("|------|")
    for f in source_files_read:
        lines.append(f"| `{f}` |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Safety Confirmation")
    lines.append("")
    lines.append("| Constraint | Status |")
    lines.append("|------------|--------|")
    lines.append("| external_api_called_this_run | False |")
    lines.append("| public_source_called_this_run | False |")
    lines.append("| tg_sent_this_run | False |")
    lines.append("| prod_state_write | False |")
    lines.append("| ai_model_called | False |")
    lines.append("| daemon_or_loop_started | False |")
    lines.append("| files_deleted | False |")
    lines.append("| historical_artifacts_modified | False |")
    lines.append("| credentials_read | False |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 下一步建议")
    lines.append("")
    lines.append("1. **提交用户验收**：将 v116N 验收包提交给项目 Owner")
    lines.append("2. **要求用户选择 A/B/C**：参考 `v116n_user_decision_tree.md`")
    lines.append("3. **根据选择推进**：")
    lines.append("   - 选 A → 进入 v116l_next_phase_roadmap.md 优先级选择")
    lines.append("   - 选 B → 启动 whale evidence collection（参考 `v116n_whale_manual_evidence_checklist.md`）")
    lines.append("   - 选 C → 监控市场波动，等待 re-run liquidation pressure one-shot")
    lines.append("4. **不要推进 production send**：0/5 production ready，6 项最低条件均未满足")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- ✅ All source data from v116L artifacts (read-only)")
    lines.append("- ✅ No external API calls in this run")
    lines.append("- ✅ No TG sends in this run")
    lines.append("- ✅ No file deletions")
    lines.append("- ✅ No historical artifact modifications (v116A-L untouched)")
    lines.append("- ✅ No credential reads")
    lines.append("- ✅ All output is presentation-layer only")
    lines.append("- ❌ Not production send ready (0/5)")
    lines.append("- ❌ No daemon/cron/loop started")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════════════════

def run():
    print("=" * 72)
    print("Market Radar v116N — User Acceptance Overlay Pack (Local Only)")
    print(f"Started: {china_stamp()}")
    print("=" * 72)

    # ── Step 1: Load v116L source data ───────────────────────────────────
    print("\n[1/3] Loading v116L source artifacts (read-only)...")
    source_files_read = [
        "results/market_radar_v116l_milestone_pack_manifest.json",
        "results/market_radar_v116l_real_e2e_acceptance_matrix.json",
        "results/market_radar_v116l_tg_evidence_index.jsonl",
        "runs/market_radar/v116l_market_radar_real_e2e_milestone_summary.md",
        "runs/market_radar/v116l_operator_review_pack.md",
        "runs/market_radar/v116l_next_phase_roadmap.md",
        "runs/market_radar/v116l_local_only_handoff.md",
    ]

    print("  Reading results/market_radar_v116l_milestone_pack_manifest.json")
    v116l_manifest = read_v116l_manifest()
    assert v116l_manifest, "v116L manifest is empty"
    assert v116l_manifest["milestone_version"] == SOURCE_MILESTONE_VERSION
    print(f"  ✓ v116L manifest loaded: {v116l_manifest['milestone_version']}")

    print("  Reading results/market_radar_v116l_real_e2e_acceptance_matrix.json")
    v116l_acceptance = read_v116l_acceptance_matrix()
    assert v116l_acceptance, "v116L acceptance matrix is empty"
    assert len(v116l_acceptance.get("cards", [])) == 5
    print(f"  ✓ v116L acceptance matrix loaded: {len(v116l_acceptance['cards'])} cards")

    print("  Reading results/market_radar_v116l_tg_evidence_index.jsonl")
    v116l_evidence = read_v116l_tg_evidence_index()
    assert len(v116l_evidence) == 5, f"Expected 5 evidence entries, got {len(v116l_evidence)}"
    print(f"  ✓ v116L TG evidence index loaded: {len(v116l_evidence)} entries")

    # ── Step 2: Generate all v116N overlay documents ─────────────────────
    print("\n[2/3] Generating v116N user acceptance overlay documents...")
    files_created = []

    # One-pager (THE critical output)
    write_one_pager(v116l_manifest, v116l_acceptance, v116l_evidence)
    files_created.append("runs/market_radar/v116n_one_pager_acceptance_summary.md")

    # Operator review pack (user-facing rewrite)
    write_operator_review_pack_user_facing(v116l_manifest, v116l_acceptance, v116l_evidence)
    files_created.append("runs/market_radar/v116n_operator_review_pack_user_facing.md")

    # User decision tree
    write_user_decision_tree(v116l_manifest)
    files_created.append("runs/market_radar/v116n_user_decision_tree.md")

    # 10-minute demo sequence
    write_demo_sequence_10min(v116l_manifest)
    files_created.append("runs/market_radar/v116n_demo_sequence_10min.md")

    # Production readiness checklist
    write_production_readiness_checklist(v116l_manifest)
    files_created.append("runs/market_radar/v116n_production_readiness_checklist.md")

    # Whale manual evidence checklist
    write_whale_manual_evidence_checklist(v116l_manifest)
    files_created.append("runs/market_radar/v116n_whale_manual_evidence_checklist.md")

    # Local-only handoff
    write_local_only_handoff(files_created, source_files_read)
    files_created.append("runs/market_radar/v116n_local_only_handoff.md")

    # ── Step 3: Build and write overlay manifest ─────────────────────────
    print("\n[3/3] Building and writing v116N overlay manifest...")

    # Add manifest file path BEFORE build so it's included in created_files
    manifest_rel_path = "results/market_radar_v116n_user_acceptance_overlay_manifest.json"
    files_created.append(manifest_rel_path)

    overlay_manifest = build_overlay_manifest(
        v116l_manifest, v116l_acceptance, v116l_evidence,
        files_created, source_files_read
    )

    manifest_path = ROOT / manifest_rel_path
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(overlay_manifest, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {manifest_path}")

    # ── Done ─────────────────────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print(f"v116N user acceptance overlay pack complete: {china_stamp()}")
    print(f"Overlay: {OVERLAY_VERSION}")
    print(f"Source milestone: {SOURCE_MILESTONE_VERSION}")
    print(f"Audit source: {AUDIT_SOURCE}")
    print(f"Files created: {len(files_created)}")
    print(f"Status: presentation overlay only — no data changes, no external calls")
    print(f"Production ready: 0/5 (unchanged)")
    print(f"{'=' * 72}")

    return 0


if __name__ == "__main__":
    sys.exit(run())
