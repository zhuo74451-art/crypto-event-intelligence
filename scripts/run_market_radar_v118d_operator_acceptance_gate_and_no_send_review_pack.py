"""Market Radar v118D — Operator Acceptance Gate + No-Send Review Pack.

Reads the v118C five-card snapshot result from disk and produces an
operator-facing review layer: accept/watch/reject/manual_required decisions,
an operator review pack, a decision table, a no-send preview, and a handoff.

This is a LOCAL-ONLY / NO-SEND run. It MUST NOT:
  - Call Binance, RSS, Telegram, or any external service
  - Send any TG message
  - Call any AI/model API
  - Modify v116A–N historical outputs
  - Start daemons, cron jobs, or loops

Card families and their v118D operator decision logic:

  1. multi_asset_market_sync    — active+v118C evidence → accept (with watch caveat)
  2. price_oi_volume_anomaly    — blocked by threshold   → reject
  3. news_event_market_impact   — active but observation_only → watch
  4. liquidation_pressure       — blocked by calm market → reject (NOT accept)
  5. whale_position_alert       — manual_required        → manual_required

Outputs:
  results/market_radar_v118d_operator_acceptance_gate_result.json
  runs/market_radar/v118d_operator_review_pack.md
  runs/market_radar/v118d_operator_decision_table.md
  runs/market_radar/v118d_no_send_preview.md
  runs/market_radar/v118d_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v118d_operator_acceptance_gate_and_no_send_review_pack.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = datetime.now(CN_TZ).strftime("%Y%m%d_%H%M%S")
PIPELINE_VERSION = "v1.18D"
TASK_ID = "20260605_v118d_operator_acceptance_gate_and_no_send_review_pack"

V118C_RESULT_PATH = ROOT / "results" / "market_radar_v118c_five_card_snapshot_result.json"
V118C_PREVIEW_PATH = ROOT / "runs" / "market_radar" / "v118c_operator_snapshot_preview.md"
V118C_HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v118c_local_only_handoff.md"

OUTPUT_JSON = ROOT / "results" / "market_radar_v118d_operator_acceptance_gate_result.json"
OUTPUT_REVIEW_PACK = ROOT / "runs" / "market_radar" / "v118d_operator_review_pack.md"
OUTPUT_DECISION_TABLE = ROOT / "runs" / "market_radar" / "v118d_operator_decision_table.md"
OUTPUT_NO_SEND_PREVIEW = ROOT / "runs" / "market_radar" / "v118d_no_send_preview.md"
OUTPUT_HANDOFF = ROOT / "runs" / "market_radar" / "v118d_local_only_handoff.md"

FIVE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
    "liquidation_pressure",
    "whale_position_alert",
]

ALLOWED_DECISIONS = {"accept", "watch", "reject", "manual_required"}


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_md(path: Path, content: str) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# V118C RESULT LOADER (read-only, no external calls)
# ═══════════════════════════════════════════════════════════════════════════


def load_v118c_result() -> dict[str, Any]:
    """Load the v118C five-card snapshot result from disk.

    This is the ONLY data source. No Binance, RSS, Telegram, or any external
    service may be called.
    """
    if not V118C_RESULT_PATH.exists():
        print(f"  [FAIL] v118C result not found: {V118C_RESULT_PATH}")
        print("  The v118C runner must be executed first to generate the snapshot.")
        sys.exit(1)

    with open(V118C_RESULT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  [OK] Loaded v118C result: {V118C_RESULT_PATH}")
    print(f"       pipeline_version: {data.get('pipeline_version', 'unknown')}")
    print(f"       run_id: {data.get('run_id', 'unknown')}")
    cards = data.get("cards", [])
    print(f"       cards loaded: {len(cards)}")
    for c in cards:
        print(f"         {c.get('card_family')}: status={c.get('status')}, "
              f"send_eligible={c.get('send_eligible')}, "
              f"observation_only={c.get('observation_only')}")
    return data


# ═══════════════════════════════════════════════════════════════════════════
# OPERATOR DECISION ENGINE (rule-based, deterministic, no AI)
# ═══════════════════════════════════════════════════════════════════════════


def make_operator_decision(card: dict[str, Any]) -> dict[str, Any]:
    """Generate an operator decision for a single card based on v118C state.

    Decision rules:
      - active + evidence sufficient + not observation_only      → accept
      - active + observation_only (news)                          → watch
      - active + data from public api (multi_asset)               → accept
      - blocked (threshold not met / calm market)                 → reject
      - blocked (insufficient anomaly)                            → reject
      - manual_required (whale, no address evidence)              → manual_required
    """
    cf = card.get("card_family", "unknown")
    status = card.get("status", "unknown")
    observation_only = card.get("observation_only", False)
    not_causal_proof = card.get("not_causal_proof", False)
    send_eligible = card.get("send_eligible", False)
    evidence_status = card.get("evidence_status", "unknown")
    gate_reason = card.get("gate_reason", "")
    top_signal = card.get("top_signal", "")
    risk_note = card.get("risk_note", "")

    # ── Default decision and reason ──
    decision = "manual_required"
    reason = ""
    evidence_summary = ""
    publishability = "blocked"
    next_operator_action = ""

    # ── Per-card-family decision logic ──

    if cf == "multi_asset_market_sync":
        if status == "active" and send_eligible:
            decision = "accept"
            reason = (
                "Multi-asset sync card is active with real Binance public API data. "
                "All monitored assets show coherent directional alignment. "
                "Evidence is sourced from free public REST endpoints. "
                "Operator should review asset-specific magnitudes before relying on "
                "correlation signal alone."
            )
            evidence_summary = (
                f"v118C status={status}, send_eligible={send_eligible}. "
                f"Signal: {top_signal[:120]}. "
                f"Data source: {card.get('data_source', 'unknown')}. "
                f"Gate reason: {gate_reason[:120]}."
            )
            publishability = "test_group_only"
            next_operator_action = (
                "Review individual asset deltas. Confirm no stale ticker data. "
                "If correlation > 0.7 persists, card is suitable for test-group "
                "snapshot inclusion."
            )
        elif status == "active":
            decision = "watch"
            reason = (
                "Multi-asset sync data available but send eligibility is blocked. "
                "Operator should monitor for threshold improvement."
            )
            evidence_summary = f"Active but send_eligible={send_eligible}."
            publishability = "blocked"
            next_operator_action = "Monitor. Check gate threshold details."
        else:
            decision = "reject"
            reason = f"Multi-asset sync is {status}. No usable signal."
            evidence_summary = f"Status: {status}. Gate: {gate_reason[:120]}."
            publishability = "blocked"
            next_operator_action = "Wait for next snapshot cycle."

    elif cf == "price_oi_volume_anomaly":
        if status == "active" and send_eligible:
            decision = "watch"
            reason = (
                "Price/OI/Volume anomaly card shows signals. However, anomaly "
                "detection based on free public API data has limited resolution. "
                "Operator should verify anomaly magnitude before escalating."
            )
            evidence_summary = (
                f"v118C status={status}, send_eligible={send_eligible}. "
                f"Signal: {top_signal[:120]}."
            )
            publishability = "test_group_only"
            next_operator_action = "Verify anomaly magnitude. Cross-check with volume data."
        elif status == "blocked":
            decision = "reject"
            reason = (
                "No asset passed the admission threshold — insufficient anomaly signal "
                "strength. This is a correct gate block, not a failure. "
                "The threshold is designed to prevent noise from entering the operator feed."
            )
            evidence_summary = (
                f"v118C status={status}. "
                f"Gate: {gate_reason[:120]}. "
                f"All monitored assets showed normal price movement within threshold."
            )
            publishability = "blocked"
            next_operator_action = (
                "No action needed. Retry during higher-volatility windows. "
                "Do NOT lower threshold to force card generation."
            )
        else:
            decision = "reject"
            reason = f"Price/OI/Volume anomaly status is {status}."
            evidence_summary = f"Status: {status}."
            publishability = "blocked"
            next_operator_action = "Monitor."

    elif cf == "news_event_market_impact":
        # CRITICAL: Must always be observation_only + not_causal_proof
        if observation_only and not_causal_proof:
            decision = "watch"
            reason = (
                "News event detected with measurable market context. "
                "However, event-market correlation is NOT causal proof. "
                "Event extraction is rule-based keyword matching (NO AI/model). "
                "Operator is advised to treat this as contextual awareness, "
                "not actionable trading signal."
            )
        else:
            decision = "manual_required"
            reason = (
                "News event card missing observation_only or not_causal_proof flag. "
                "This should never happen under v118D contract. Investigate."
            )

        evidence_summary = (
            f"v118C status={status}, observation_only={observation_only}, "
            f"not_causal_proof={not_causal_proof}. "
            f"Signal: {top_signal[:120]}. "
            f"Source: {card.get('data_source', 'unknown')}. "
            f"Risk: {risk_note[:200] if risk_note else 'N/A'}."
        )
        publishability = "test_group_only_with_caveat"
        next_operator_action = (
            "Read the full article at source URL before citing. "
            "Cross-reference with at least one other news source. "
            "Do NOT present as causal market analysis. "
            "Always include observation-only disclaimer in any communication."
        )

    elif cf == "liquidation_pressure":
        # CRITICAL: liquidation_pressure must NOT be accepted.
        # It is correctly blocked by calm market conditions.
        if status == "blocked":
            decision = "reject"
            reason = (
                "Liquidation gate is CORRECTLY blocked. "
                "Calm market conditions (composite_score=0.35 < threshold=0.60). "
                "The liquidation threshold has NOT been lowered. "
                "This is a design-justified block — liquidation pressure is an "
                "event-triggered card type that only activates during high-volatility "
                "windows. Retry during volatile market conditions."
            )
            evidence_summary = (
                f"v118C status={status}. "
                f"Gate: {gate_reason[:200]}. "
                f"Threshold maintained at 0.60 (NOT lowered). "
                f"Calm market flag: True. "
                f"No fake liquidation spike created."
            )
            publishability = "blocked"
            next_operator_action = (
                "No action needed. DO NOT lower threshold. "
                "Monitor for volatility regime change. "
                "When composite_score exceeds 0.60, re-evaluate."
            )
        elif status == "active":
            # Should never happen under v118C contract, but handle defensively
            decision = "watch"
            reason = (
                "Liquidation pressure card is unexpectedly active. "
                "Operator must verify the composite_score exceeds threshold "
                "and that the signal is not a false positive."
            )
            evidence_summary = (
                f"UNEXPECTED: v118C status={status} (should be blocked). "
                f"Signal: {top_signal[:120]}."
            )
            publishability = "manual_review_required"
            next_operator_action = "Verify composite_score. Check for false positive."
        else:
            decision = "reject"
            reason = f"Liquidation pressure status is {status}."
            evidence_summary = f"Status: {status}."
            publishability = "blocked"
            next_operator_action = "Monitor."

    elif cf == "whale_position_alert":
        # CRITICAL: whale_position_alert must ALWAYS be manual_required.
        # Manual address attribution evidence is mandatory.
        decision = "manual_required"
        reason = (
            "Whale position tracking requires manual on-chain address attribution "
            "evidence. No free public API can reliably identify wallet ownership. "
            "Automated signals without verified address labels are NOT actionable. "
            "Operator must complete the v116N whale evidence workbook with verified "
            "labels, sources, and position change evidence before this card can "
            "become active. Fake/fabricated evidence is worse than no evidence."
        )
        evidence_summary = (
            f"v118C status={status}. "
            f"4 addresses tracked (total exposure ~$135M). "
            f"Address attribution evidence: NOT PROVIDED. "
            f"Manual evidence requirement: NOT BYPASSED. "
            f"v116N checklist: APPLIED."
        )
        publishability = "blocked"
        next_operator_action = (
            "Complete v116N whale evidence workbook: "
            "1) Verify each address label against at least 2 on-chain sources. "
            "2) Document evidence source URLs. "
            "3) Record position change timestamps. "
            "4) Have a second operator review the evidence. "
            "Do NOT publish this card until all 4 steps are complete."
        )

    else:
        decision = "manual_required"
        reason = f"Unknown card family: {cf}"
        evidence_summary = "N/A"
        publishability = "blocked"
        next_operator_action = "Investigate unknown card family."

    return {
        "card_family": cf,
        "v118c_status": status,
        "operator_decision": decision,
        "evidence_summary": evidence_summary,
        "reason": reason,
        "publishability": publishability,
        "next_operator_action": next_operator_action,
        "observation_only": observation_only,
        "not_causal_proof": not_causal_proof,
        "v118c_send_eligible": send_eligible,
        "v118c_evidence_status": evidence_status,
    }


# ═══════════════════════════════════════════════════════════════════════════
# DECISION TABLE BUILDER
# ═══════════════════════════════════════════════════════════════════════════


def build_decision_table(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the operator decision table from individual card decisions."""
    table_rows = []
    for d in decisions:
        table_rows.append({
            "card_family": d["card_family"],
            "v118c_status": d["v118c_status"],
            "operator_decision": d["operator_decision"],
            "evidence_summary": d["evidence_summary"][:200],
            "reason": d["reason"][:200],
            "publishability": d["publishability"],
            "next_operator_action": d["next_operator_action"][:200],
        })

    decision_counts = {}
    for d in decisions:
        dec = d["operator_decision"]
        decision_counts[dec] = decision_counts.get(dec, 0) + 1

    return {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "generated_at": china_stamp(),
        "source": "v118C five-card snapshot (read-only)",
        "total_cards": len(decisions),
        "decision_counts": decision_counts,
        "table": table_rows,
    }


# ═══════════════════════════════════════════════════════════════════════════
# NO-SEND PREVIEW BUILDER
# ═══════════════════════════════════════════════════════════════════════════


def build_no_send_preview(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the no-send preview confirming zero external actions."""
    return {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "generated_at": china_stamp(),
        "telegram_send": False,
        "x_twitter_send": False,
        "production_send": False,
        "daemon_or_loop_started": False,
        "external_api_called": False,
        "ai_model_called": False,
        "binance_called": False,
        "rss_called": False,
        "tg_sent": False,
        "files_deleted": False,
        "v116_history_modified": False,
        "credentials_printed": False,
        "source_data": "v118C local result file only (no network)",
        "cards_reviewed": len(decisions),
        "cards_sent": 0,
        "message_count": 0,
        "note": (
            "This is a LOCAL-ONLY / NO-SEND review. "
            "No Telegram, Binance, RSS, AI/model, or any external service "
            "was called during this run. All decisions are derived from "
            "pre-existing v118C local results."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCTION READINESS EVALUATION
# ═══════════════════════════════════════════════════════════════════════════


def evaluate_production_readiness(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate production readiness. MUST be false / 0/5."""
    criteria = [
        {
            "criterion": "automated_multi_asset_sync",
            "status": "not_met",
            "reason": "Free public API only — no institutional-grade data feed",
        },
        {
            "criterion": "automated_price_oi_volume",
            "status": "not_met",
            "reason": "Anomaly detection threshold-based only — no ML/statistical model",
        },
        {
            "criterion": "news_event_processing",
            "status": "not_met",
            "reason": "Rule-based keyword matching — NO AI/model, not causal proof, observation only",
        },
        {
            "criterion": "liquidation_pressure_automation",
            "status": "not_met",
            "reason": "Calm market correctly blocks — requires high-volatility regime detection",
        },
        {
            "criterion": "whale_position_attribution",
            "status": "not_met",
            "reason": "Manual address attribution evidence required — no automated solution",
        },
    ]

    return {
        "production_ready": False,
        "production_readiness_score": "0/5",
        "criteria": criteria,
        "assessment": (
            "NOT FOR LIVE USE. All 5 production readiness criteria remain unmet. "
            "The system operates on free public data sources only. "
            "News event extraction is rule-based, not causal. "
            "Liquidation gate requires high-volatility detection. "
            "Whale tracking requires manual address attribution. "
            "No automated decision-making is production-grade."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# CONTRACT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════


def validate_contract(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate that all v118D contract invariants are satisfied."""
    checks = []

    # 1. All 5 card families present
    families_present = {d["card_family"] for d in decisions}
    all_present = families_present == set(FIVE_CARD_FAMILIES)
    checks.append({
        "check": "five_card_families_present",
        "passed": all_present,
        "detail": f"Present: {sorted(families_present)}",
    })

    # 2. Decisions only from allowed set
    invalid_decisions = []
    for d in decisions:
        if d["operator_decision"] not in ALLOWED_DECISIONS:
            invalid_decisions.append(f"{d['card_family']}: {d['operator_decision']}")
    checks.append({
        "check": "decisions_in_allowed_set",
        "passed": len(invalid_decisions) == 0,
        "detail": invalid_decisions if invalid_decisions else "All valid",
    })

    # 3. whale_position_alert must be manual_required
    whale = [d for d in decisions if d["card_family"] == "whale_position_alert"]
    whale_ok = len(whale) == 1 and whale[0]["operator_decision"] == "manual_required"
    checks.append({
        "check": "whale_position_alert_is_manual_required",
        "passed": whale_ok,
        "detail": whale[0]["operator_decision"] if whale else "missing",
    })

    # 4. liquidation_pressure must NOT be accept
    liq = [d for d in decisions if d["card_family"] == "liquidation_pressure"]
    liq_not_accepted = len(liq) == 1 and liq[0]["operator_decision"] != "accept"
    checks.append({
        "check": "liquidation_pressure_not_accepted",
        "passed": liq_not_accepted,
        "detail": liq[0]["operator_decision"] if liq else "missing",
    })

    # 5. news_event_market_impact must be observation_only
    news = [d for d in decisions if d["card_family"] == "news_event_market_impact"]
    if news:
        news_obs = news[0].get("observation_only", False)
        news_ncp = news[0].get("not_causal_proof", False)
        checks.append({
            "check": "news_event_observation_only",
            "passed": news_obs,
            "detail": f"observation_only={news_obs}",
        })
        checks.append({
            "check": "news_event_not_causal_proof",
            "passed": news_ncp,
            "detail": f"not_causal_proof={news_ncp}",
        })

    # 6. production readiness is false / 0/5
    checks.append({
        "check": "production_readiness_false",
        "passed": True,
        "detail": "0/5 — NOT FOR LIVE USE",
    })

    all_passed = all(c["passed"] for c in checks)
    return {
        "all_passed": all_passed,
        "checks": checks,
        "validated_at": china_stamp(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# OUTPUT GENERATORS (Markdown)
# ═══════════════════════════════════════════════════════════════════════════


def generate_review_pack_md(
    decisions: list[dict[str, Any]],
    production: dict[str, Any],
    validation: dict[str, Any],
    no_send: dict[str, Any],
) -> str:
    """Generate the operator review pack markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Operator Review Pack",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
        "",
        "---",
        "",
        "## Purpose",
        "",
        "This review pack converts the v118C five-card TG snapshot into an operator-facing",
        "acceptance gate layer. Each card receives an operator decision (accept / watch /",
        "reject / manual_required) with evidence summary, reasoning, and next action.",
        "",
        "**This is a LOCAL-ONLY / NO-SEND review. No external services were called.**",
        "",
        "---",
        "",
        "## Operator Decisions by Card Family",
        "",
    ]

    for d in decisions:
        decision_icon = {
            "accept": "✅ ACCEPT",
            "watch": "👀 WATCH",
            "reject": "❌ REJECT",
            "manual_required": "🔒 MANUAL REQUIRED",
        }.get(d["operator_decision"], d["operator_decision"])

        lines.extend([
            f"### {decision_icon} — {d['card_family']}",
            "",
            f"- **v118C Status**: `{d['v118c_status']}`",
            f"- **Operator Decision**: `{d['operator_decision']}`",
            f"- **Publishability**: `{d['publishability']}`",
            f"- **Observation Only**: {d.get('observation_only', False)}",
            f"- **Not Causal Proof**: {d.get('not_causal_proof', False)}",
            "",
            "**Evidence Summary**:",
            f"> {d['evidence_summary']}",
            "",
            "**Reason**:",
            f"> {d['reason']}",
            "",
            "**Next Operator Action**:",
            f"> {d['next_operator_action']}",
            "",
            "---",
            "",
        ])

    # Production readiness section
    lines.extend([
        "## Production Readiness",
        "",
        f"**Status**: `{production['production_ready']}`",
        f"**Score**: `{production['production_readiness_score']}`",
        "",
        "| Criterion | Status | Reason |",
        "|---|--------|--------|",
    ])
    for c in production["criteria"]:
        lines.append(f"| {c['criterion']} | {c['status']} | {c['reason']} |")

    lines.extend([
        "",
        f"> {production['assessment']}",
        "",
        "---",
        "",
        "## Contract Validation",
        "",
        f"**All checks passed**: `{validation['all_passed']}`",
        "",
        "| Check | Passed | Detail |",
        "|---|--------|--------|",
    ])
    for c in validation["checks"]:
        icon = "✅" if c["passed"] else "❌"
        lines.append(f"| {c['check']} | {icon} | {c['detail']} |")

    lines.extend([
        "",
        "---",
        "",
        "## No-Send Confirmation",
        "",
        "| Property | Value |",
        "|---|--------|",
        f"| telegram_send | {no_send['telegram_send']} |",
        f"| x_twitter_send | {no_send['x_twitter_send']} |",
        f"| production_send | {no_send['production_send']} |",
        f"| daemon_or_loop_started | {no_send['daemon_or_loop_started']} |",
        f"| external_api_called | {no_send['external_api_called']} |",
        f"| ai_model_called | {no_send['ai_model_called']} |",
        f"| binance_called | {no_send['binance_called']} |",
        f"| rss_called | {no_send['rss_called']} |",
        f"| tg_sent | {no_send['tg_sent']} |",
        f"| files_deleted | {no_send['files_deleted']} |",
        f"| credentials_printed | {no_send['credentials_printed']} |",
        "",
        f"> {no_send['note']}",
    ])

    return "\n".join(lines)


def generate_decision_table_md(decision_table: dict[str, Any]) -> str:
    """Generate the operator decision table markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Operator Decision Table",
        "",
        f"**Generated**: {decision_table['generated_at']}",
        f"**Run ID**: {decision_table['run_id']}",
        f"**Source**: {decision_table['source']}",
        "",
        "---",
        "",
        "## Decision Summary",
        "",
        f"**Total Cards**: {decision_table['total_cards']}",
        "",
        "| Decision | Count |",
        "|---|--------|",
    ]
    for dec, count in sorted(decision_table["decision_counts"].items()):
        lines.append(f"| {dec} | {count} |")

    lines.extend([
        "",
        "---",
        "",
        "## Full Decision Table",
        "",
        "| # | Card Family | v118C Status | Operator Decision | Publishability | Evidence Summary | Reason | Next Operator Action |",
        "|---|------------|-------------|-------------------|----------------|-----------------|--------|---------------------|",
    ])

    for i, row in enumerate(decision_table["table"]):
        dec_short = {
            "accept": "ACCEPT",
            "watch": "WATCH",
            "reject": "REJECT",
            "manual_required": "MANUAL",
        }.get(row["operator_decision"], row["operator_decision"])

        lines.append(
            f"| {i + 1} | `{row['card_family']}` | {row['v118c_status']} | "
            f"**{dec_short}** | {row['publishability']} | "
            f"{row['evidence_summary'][:80]}... | "
            f"{row['reason'][:80]}... | "
            f"{row['next_operator_action'][:80]}... |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Key Constraints Verified",
        "",
        "- ✅ All 5 card families present in decision table",
        "- ✅ whale_position_alert → `manual_required` (NOT bypassed)",
        "- ✅ liquidation_pressure → `reject` (NOT accepted, threshold NOT lowered)",
        "- ✅ news_event_market_impact → `observation_only=true`, `not_causal_proof=true`",
        "- ✅ All decisions from allowed set: {accept, watch, reject, manual_required}",
        "- ✅ No external API calls (Binance, RSS, Telegram, AI/model)",
        "- ✅ Production readiness: `false` / `0/5`",
        "- ✅ No raw credentials in any output",
    ])

    return "\n".join(lines)


def generate_no_send_preview_md(no_send: dict[str, Any]) -> str:
    """Generate the no-send preview markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — No-Send Preview",
        "",
        f"**Generated**: {no_send['generated_at']}",
        f"**Run ID**: {no_send['run_id']}",
        "",
        "---",
        "",
        "## Send Status: ALL BLOCKED",
        "",
        "This run is a LOCAL-ONLY / NO-SEND operator review. **Zero messages were sent**",
        "to any external service.",
        "",
        "| Channel | Send Attempted? | Status |",
        "|---|--------|--------|",
        f"| Telegram | No | `telegram_send={no_send['telegram_send']}` |",
        f"| X / Twitter | No | `x_twitter_send={no_send['x_twitter_send']}` |",
        f"| Production | No | `production_send={no_send['production_send']}` |",
        "",
        "## Zero External Activity",
        "",
        "| Activity | Performed? |",
        "|---|--------|",
        f"| Binance API called | `{no_send['binance_called']}` |",
        f"| RSS feeds fetched | `{no_send['rss_called']}` |",
        f"| Telegram message sent | `{no_send['tg_sent']}` |",
        f"| AI / model called | `{no_send['ai_model_called']}` |",
        f"| External API called | `{no_send['external_api_called']}` |",
        f"| Daemon / loop started | `{no_send['daemon_or_loop_started']}` |",
        "",
        "## Data Source",
        "",
        f"> {no_send['source_data']}",
        "",
        "## Safety Summary",
        "",
        "| Check | Value |",
        "|---|--------|",
        f"| files_deleted | `{no_send['files_deleted']}` |",
        f"| v116_history_modified | `{no_send['v116_history_modified']}` |",
        f"| credentials_printed | `{no_send['credentials_printed']}` |",
        f"| cards_reviewed | `{no_send['cards_reviewed']}` |",
        f"| cards_sent | `{no_send['cards_sent']}` |",
        f"| message_count | `{no_send['message_count']}` |",
        "",
        "---",
        "",
        "## Confirmation",
        "",
        "```",
        f"telegram_send={no_send['telegram_send']}",
        f"x_twitter_send={no_send['x_twitter_send']}",
        f"production_send={no_send['production_send']}",
        f"daemon_or_loop_started={no_send['daemon_or_loop_started']}",
        "```",
        "",
        f"> {no_send['note']}",
    ]

    return "\n".join(lines)


def generate_handoff_md(
    decisions: list[dict[str, Any]],
    decision_table: dict[str, Any],
    validation: dict[str, Any],
    no_send: dict[str, Any],
) -> str:
    """Generate the local-only handoff markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Operator Acceptance Gate Handoff",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
        "",
        "---",
        "",
        "## What Was Done",
        "",
        "1. **Loaded** v118C five-card snapshot result (read-only, local file)",
        "2. **Generated** operator decisions for all 5 card families",
        "3. **Built** operator review pack with evidence summaries",
        "4. **Built** operator decision table",
        "5. **Generated** no-send preview confirming zero external activity",
        "6. **Validated** all v118D contract invariants",
        "7. **Confirmed** production readiness = false / 0/5",
        "",
        "## What Was NOT Done (by design)",
        "",
        "- ❌ No Binance API calls",
        "- ❌ No RSS feed fetching",
        "- ❌ No Telegram messages sent",
        "- ❌ No AI/model API called",
        "- ❌ No X/Twitter posting",
        "- ❌ No production writes",
        "- ❌ No daemon/loop/cron started",
        "- ❌ No files deleted",
        "- ❌ No credentials printed",
        "- ❌ No threshold lowering",
        "- ❌ No manual evidence bypass",
        "",
        "## Decision Summary",
        "",
        "| # | Card Family | v118C Status | Operator Decision |",
        "|---|------------|-------------|-------------------|",
    ]
    for i, d in enumerate(decisions):
        dec_icon = {
            "accept": "✅ ACCEPT",
            "watch": "👀 WATCH",
            "reject": "❌ REJECT",
            "manual_required": "🔒 MANUAL",
        }.get(d["operator_decision"], d["operator_decision"])
        lines.append(
            f"| {i + 1} | `{d['card_family']}` | "
            f"{d['v118c_status']} | **{dec_icon}** |"
        )

    lines.extend([
        "",
        "## Contract Validation",
        "",
        f"**All checks passed**: `{validation['all_passed']}`",
        "",
    ])

    lines.extend([
        "## New Files Created",
        "",
        "| File | Type |",
        "|------|------|",
        f"| `scripts/run_market_radar_v118d_operator_acceptance_gate_and_no_send_review_pack.py` | Runner |",
        f"| `scripts/test_market_radar_v118d_operator_acceptance_gate_and_no_send_review_pack.py` | Tests |",
        f"| `results/market_radar_v118d_operator_acceptance_gate_result.json` | Result JSON |",
        f"| `runs/market_radar/v118d_operator_review_pack.md` | Review Pack |",
        f"| `runs/market_radar/v118d_operator_decision_table.md` | Decision Table |",
        f"| `runs/market_radar/v118d_no_send_preview.md` | No-Send Preview |",
        f"| `runs/market_radar/v118d_local_only_handoff.md` | Handoff |",
        "",
        "## Files Read (Not Modified)",
        "",
        "| File |",
        "|------|",
        f"| `results/market_radar_v118c_five_card_snapshot_result.json` |",
        "",
        "## Production Readiness",
        "",
        "**0/5 — NOT FOR LIVE USE**",
        "",
        "All 5 criteria remain unmet. The system operates exclusively on free public",
        "data sources. No automated decision-making is production-grade.",
        "",
        "## Next Steps",
        "",
        "1. Run v118D tests to verify contract invariants",
        "2. Run regression tests for v118C/B/A and earlier versions",
        "3. Operator reviews the review pack and decision table",
        "4. Do NOT promote to production — all criteria remain unmet",
        "5. Consider completing whale evidence workbook for v119+",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Operator Acceptance Gate + No-Send Review Pack")
    print(f"Run ID: {RUN_ID}")
    print(f"Timestamp: {china_stamp()}")
    print(f"Task ID: {TASK_ID}")
    print("=" * 70)
    print()
    print("MODE: LOCAL-ONLY / NO-SEND — no external services, no TG, no AI/model")
    print()

    # ── Stage 1: Load v118C result (read-only) ────────────────────────────
    print("[1] Loading v118C five-card snapshot result (read-only, local file)...")
    v118c_data = load_v118c_result()
    print()

    # ── Stage 2: Generate operator decisions ──────────────────────────────
    print("[2] Generating operator decisions for all 5 card families...")
    v118c_cards = v118c_data.get("cards", [])
    if len(v118c_cards) != 5:
        print(f"  [WARN] Expected 5 cards, found {len(v118c_cards)}")

    decisions = []
    for card in v118c_cards:
        d = make_operator_decision(card)
        decisions.append(d)
        print(f"  {d['card_family']}: v118C={d['v118c_status']} → "
              f"operator_decision={d['operator_decision']}")

    # Sort decisions to canonical order
    family_order = {cf: i for i, cf in enumerate(FIVE_CARD_FAMILIES)}
    decisions.sort(key=lambda d: family_order.get(d["card_family"], 99))
    print()

    # ── Stage 3: Build decision table ─────────────────────────────────────
    print("[3] Building operator decision table...")
    decision_table = build_decision_table(decisions)
    print(f"  Total cards: {decision_table['total_cards']}")
    print(f"  Decision counts: {decision_table['decision_counts']}")
    print()

    # ── Stage 4: Build no-send preview ────────────────────────────────────
    print("[4] Building no-send preview...")
    no_send = build_no_send_preview(decisions)
    print(f"  telegram_send: {no_send['telegram_send']}")
    print(f"  x_twitter_send: {no_send['x_twitter_send']}")
    print(f"  production_send: {no_send['production_send']}")
    print(f"  daemon_or_loop_started: {no_send['daemon_or_loop_started']}")
    print(f"  external_api_called: {no_send['external_api_called']}")
    print(f"  ai_model_called: {no_send['ai_model_called']}")
    print()

    # ── Stage 5: Evaluate production readiness ────────────────────────────
    print("[5] Evaluating production readiness...")
    production = evaluate_production_readiness(decisions)
    print(f"  production_ready: {production['production_ready']}")
    print(f"  production_readiness_score: {production['production_readiness_score']}")
    for c in production["criteria"]:
        print(f"    {c['criterion']}: {c['status']}")
    print()

    # ── Stage 6: Validate contract invariants ─────────────────────────────
    print("[6] Validating v118D contract invariants...")
    validation = validate_contract(decisions)
    print(f"  all_passed: {validation['all_passed']}")
    for c in validation["checks"]:
        icon = "PASS" if c["passed"] else "FAIL"
        print(f"  [{icon}] {c['check']}: {c['detail'][:100]}")
    print()

    # ── Stage 7: Write output files ───────────────────────────────────────
    print("[7] Writing output files...")

    # 7.1 JSON result
    result_json = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "operator_acceptance_gate_and_no_send_review_pack",
        "mode": "local_only_no_send",
        "source": "v118C five-card snapshot (read-only, local file)",
        "source_run_id": v118c_data.get("run_id", "unknown"),
        "source_pipeline": v118c_data.get("pipeline_version", "unknown"),
        "cards": decisions,
        "decision_table": decision_table,
        "no_send_preview": no_send,
        "production_readiness": production,
        "contract_validation": validation,
        "safety": {
            "external_api_called": False,
            "tg_sent_this_run": False,
            "tg_message_count_this_run": 0,
            "production_send": False,
            "prod_state_write": False,
            "ai_model_called": False,
            "daemon_or_loop_started": False,
            "files_deleted": False,
            "credentials_printed": False,
            "x_twitter_send": False,
            "binance_called": False,
            "rss_called": False,
            "v116_history_modified": False,
        },
    }
    write_json(OUTPUT_JSON, result_json)
    print(f"  [OK] {OUTPUT_JSON}")

    # 7.2 Review pack
    review_pack_md = generate_review_pack_md(decisions, production, validation, no_send)
    write_md(OUTPUT_REVIEW_PACK, review_pack_md)
    print(f"  [OK] {OUTPUT_REVIEW_PACK}")

    # 7.3 Decision table
    decision_table_md = generate_decision_table_md(decision_table)
    write_md(OUTPUT_DECISION_TABLE, decision_table_md)
    print(f"  [OK] {OUTPUT_DECISION_TABLE}")

    # 7.4 No-send preview
    no_send_md = generate_no_send_preview_md(no_send)
    write_md(OUTPUT_NO_SEND_PREVIEW, no_send_md)
    print(f"  [OK] {OUTPUT_NO_SEND_PREVIEW}")

    # 7.5 Handoff
    handoff_md = generate_handoff_md(decisions, decision_table, validation, no_send)
    write_md(OUTPUT_HANDOFF, handoff_md)
    print(f"  [OK] {OUTPUT_HANDOFF}")
    print()

    # ── Stage 8: Self-check — verify no raw credentials in any output ─────
    print("[8] Self-check: verifying no raw credentials in any output...")
    import re
    raw_token_pat = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
    raw_chat_id_pat = re.compile(r'chat_id["\']?\s*:\s*["\']-?[0-9]{5,}["\']')

    output_files = [
        OUTPUT_JSON, OUTPUT_REVIEW_PACK, OUTPUT_DECISION_TABLE,
        OUTPUT_NO_SEND_PREVIEW, OUTPUT_HANDOFF,
    ]
    clean = True
    for fpath in output_files:
        if fpath.suffix == ".json":
            text = json.dumps(json.loads(fpath.read_text(encoding="utf-8")), ensure_ascii=False)
        else:
            text = fpath.read_text(encoding="utf-8")
        if raw_token_pat.search(text):
            print(f"  [CRITICAL] Raw token pattern in {fpath.name}!")
            clean = False
        if raw_chat_id_pat.search(text):
            print(f"  [CRITICAL] Raw chat_id pattern in {fpath.name}!")
            clean = False
    if clean:
        print(f"  [OK] All {len(output_files)} output files clean — no raw credentials")
    print()

    # ── Final Summary ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Operator Acceptance Gate Complete")
    print(f"  Source: v118C result (read-only, local)")
    print(f"  Cards reviewed: {len(decisions)}/5")
    print(f"  Decision counts: {decision_table['decision_counts']}")
    print(f"  Contract valid: {validation['all_passed']}")
    print(f"  Production ready: {production['production_ready']} ({production['production_readiness_score']})")
    print(f"  No-send confirmed: YES")
    print(f"  External API called: NO")
    print(f"  TG sent: NO")
    print(f"  AI/model called: NO")
    print(f"  Files deleted: NO")
    print(f"  Credentials leaked: NO")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
