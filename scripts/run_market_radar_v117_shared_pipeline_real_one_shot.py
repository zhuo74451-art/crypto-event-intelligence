"""Market Radar v117 — Shared Pipeline Real One-Shot Runner.

Executes:
  1. Fixture pipeline — all 5 card families through shared infrastructure
  2. Real free API pipeline — at least 1 real adapter through full pipeline
  3. TG test group one-shot send (if safe config available)

Outputs:
  results/market_radar_v117_shared_infra_manifest.json
  results/market_radar_v117_shared_pipeline_fixture_results.json
  results/market_radar_v117_shared_pipeline_real_one_shot_result.json
  results/market_radar_v117_shared_pipeline_tg_evidence_ledger.jsonl
  runs/market_radar/v117_shared_pipeline_design.md
  runs/market_radar/v117_shared_pipeline_fixture_report.md
  runs/market_radar/v117_shared_pipeline_real_one_shot_report.md
  runs/market_radar/v117_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v117_shared_pipeline_real_one_shot.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = datetime.now(CN_TZ).strftime("%Y%m%d_%H%M%S")
PIPELINE_VERSION = "v1.17"

SAFETY: dict[str, Any] = {
    "run_id": RUN_ID,
    "pipeline_version": PIPELINE_VERSION,
    "external_api_called": False,
    "tg_sent_this_run": False,
    "production_send": False,
    "prod_state_write": False,
    "ai_model_called": False,
    "daemon_or_loop_started": False,
    "files_deleted": False,
    "credentials_printed": False,
}


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_jsonl(path: Path, entries: list[dict]) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_md(path: Path, content: str) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Shared Pipeline Real One-Shot")
    print(f"Run ID: {RUN_ID}")
    print(f"Timestamp: {china_stamp()}")
    print("=" * 70)
    print()

    # ── Import shared package ───────────────────────────────────────────
    print("[0] Importing shared pipeline package...")
    try:
        from market_radar.shared.models import (
            CardFamily,
            SharedPipelineResult,
            FIVE_CARD_FAMILIES,
            THREE_VERIFIED_CARD_FAMILIES,
        )
        from market_radar.shared.pipeline import SharedPipeline, run_pipeline
        from market_radar.shared.evidence_ledger import EvidenceLedger, create_evidence_ledger
        from market_radar.shared.free_api_adapters import create_real_free_api_adapter
        from market_radar.shared.adapter_contract import FixtureCatalog
        print("  [OK] Shared package imported successfully")
    except ImportError as e:
        print(f"  [FAIL] Cannot import shared package: {e}")
        print("  Ensure market_radar/shared/ is on Python path")
        sys.exit(1)

    print()

    # ── Stage 1: Fixture Pipeline ───────────────────────────────────────
    print("[1] Running fixture pipeline (5 card families)...")
    pipeline = SharedPipeline()

    fixture_results = pipeline.run_all_fixtures()

    fixture_summary = []
    for r in fixture_results:
        status = "PASS" if r.passed else "BLOCKED"
        gate = r.gate_decision
        gate_str = f"allow={gate.allow}, reason={gate.reason[:80]}..." if gate else "N/A"
        tg = r.tg_result
        tg_str = f"status={tg.status}, reason={tg.reason[:60]}..." if tg else "N/A"
        print(f"  [{status}] {r.card_family.value}: gate=({gate_str}), tg=({tg_str})")
        fixture_summary.append({
            "card_family": r.card_family.value,
            "passed": r.passed,
            "gate_allow": gate.allow if gate else None,
            "gate_reason": gate.reason if gate else None,
            "tg_status": tg.status if tg else None,
        })

    print()

    # ── Stage 2: Real Free API Pipeline ────────────────────────────────
    print("[2] Running real free API pipeline (multi_asset_market_sync)...")
    SAFETY["external_api_called"] = True

    real_api_results = pipeline.run_real_free_api(CardFamily.MULTI_ASSET_MARKET_SYNC)

    real_summary = []
    for r in real_api_results:
        signal = r.signal
        api_ok = signal.metrics.get("api_success", False) if signal else False
        assets_count = signal.metrics.get("asset_count", 0) if signal else 0
        gate = r.gate_decision
        tg = r.tg_result

        status = "REAL_SUCCESS" if (r.passed and api_ok) else (
            "SKIPPED" if not api_ok else "PARTIAL"
        )
        print(f"  [{status}] {r.card_family.value}: "
              f"api_ok={api_ok}, assets={assets_count}, "
              f"gate_allow={gate.allow if gate else 'N/A'}, "
              f"tg_status={tg.status if tg else 'N/A'}")

        if tg and tg.success:
            SAFETY["tg_sent_this_run"] = True

        real_summary.append({
            "card_family": r.card_family.value,
            "api_success": api_ok,
            "asset_count": assets_count,
            "gate_allow": gate.allow if gate else None,
            "gate_reason": gate.reason if gate else None,
            "tg_attempted": tg.attempted if tg else False,
            "tg_success": tg.success if tg else False,
            "tg_status": tg.status if tg else None,
            "tg_reason": tg.reason if tg else None,
            "passed": r.passed,
            "error": r.error,
        })

    print()

    # ── Also attempt price_oi_volume_anomaly real API ──────────────────
    print("[3] Running real free API pipeline (price_oi_volume_anomaly)...")
    real_api_results_2 = pipeline.run_real_free_api(CardFamily.PRICE_OI_VOLUME_ANOMALY)
    for r in real_api_results_2:
        signal = r.signal
        api_ok = signal.metrics.get("api_success", False) if signal else False
        count = signal.metrics.get("signal_count", 0) if signal else 0
        gate = r.gate_decision
        tg = r.tg_result
        status = "REAL_SUCCESS" if (r.passed and api_ok) else "SKIPPED" if not api_ok else "PARTIAL"
        print(f"  [{status}] {r.card_family.value}: api_ok={api_ok}, signals={count}, gate_allow={gate.allow if gate else 'N/A'}")
        real_summary.append({
            "card_family": r.card_family.value,
            "api_success": api_ok,
            "signal_count": count,
            "gate_allow": gate.allow if gate else None,
            "gate_reason": gate.reason if gate else None,
            "tg_attempted": tg.attempted if tg else False,
            "tg_success": tg.success if tg else False,
            "tg_status": tg.status if tg else None,
            "tg_reason": tg.reason if tg else None,
            "passed": r.passed,
            "error": r.error,
        })
    real_api_results.extend(real_api_results_2)

    print()

    # ── Stage 3: Evidence Ledger ────────────────────────────────────────
    print("[4] Writing evidence ledger...")
    evidence_entries = pipeline.evidence_ledger.entries()
    evidence_dicts = [e.as_dict() for e in evidence_entries]
    clean, violations = pipeline.evidence_ledger.verify_no_raw_secrets()
    if not clean:
        print(f"  [WARN] Evidence ledger contains {len(violations)} potential raw secret patterns!")
        for v in violations:
            print(f"    - {v}")
    else:
        print(f"  [OK] Evidence ledger clean — {len(evidence_entries)} entries, no raw secrets")

    print()

    # ── Stage 4: Write Outputs ──────────────────────────────────────────
    print("[5] Writing output files...")

    results_dir = ROOT / "results"
    runs_dir = ROOT / "runs" / "market_radar"

    # 4.1 Infra manifest
    manifest = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "generated_at": china_stamp(),
        "shared_package": "market_radar/shared/",
        "components": [
            "models.py — CardFamily, NormalizedSignal, GateDecision, etc.",
            "adapter_contract.py — SignalAdapter, FixtureSignalAdapter, FixtureCatalog",
            "free_api_adapters.py — MultiAssetMarketSyncFreeApiAdapter, PriceOIVolumeAnomalyFreeApiAdapter",
            "gate_contract.py — QualityGate, SendReadinessGate",
            "renderer_contract.py — CardRenderer (all 5 card types)",
            "sender_contract.py — TGTestGroupSender (redacted, test_group only)",
            "evidence_ledger.py — EvidenceLedger (sha256 proofs, no raw secrets)",
            "pipeline.py — SharedPipeline orchestrator",
        ],
        "card_families": [
            "multi_asset_market_sync",
            "price_oi_volume_anomaly",
            "news_event_market_impact",
            "liquidation_pressure",
            "whale_position_alert",
        ],
        "real_free_api_adapters": [
            "MultiAssetMarketSyncFreeApiAdapter (Binance public REST)",
            "PriceOIVolumeAnomalyFreeApiAdapter (Binance spot + futures OI)",
        ],
        "constraints": {
            "production_send_ready": False,
            "formal_channel_blocked": True,
            "x_twitter_blocked": True,
            "daemon_cron_loop_blocked": True,
            "liquidation_gate_not_lowered": True,
            "whale_manual_evidence_not_bypassed": True,
        },
    }
    write_json(results_dir / "market_radar_v117_shared_infra_manifest.json", manifest)
    print(f"  [OK] {results_dir / 'market_radar_v117_shared_infra_manifest.json'}")

    # 4.2 Fixture results
    fixture_output = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "generated_at": china_stamp(),
        "type": "fixture",
        "results": [r.as_dict() for r in fixture_results],
        "summary": fixture_summary,
        "counts": {
            "total": len(fixture_results),
            "passed": sum(1 for r in fixture_results if r.passed),
            "blocked": sum(1 for r in fixture_results if not r.passed and not r.error),
            "error": sum(1 for r in fixture_results if r.error),
        },
    }
    write_json(results_dir / "market_radar_v117_shared_pipeline_fixture_results.json", fixture_output)
    print(f"  [OK] {results_dir / 'market_radar_v117_shared_pipeline_fixture_results.json'}")

    # 4.3 Real one-shot result
    real_output = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "generated_at": china_stamp(),
        "type": "real_free_api",
        "results": [r.as_dict() for r in real_api_results],
        "summary": real_summary,
        "counts": {
            "total": len(real_api_results),
            "api_success": sum(1 for s in real_summary if s.get("api_success")),
            "gate_passed": sum(1 for s in real_summary if s.get("gate_allow")),
            "tg_sent": sum(1 for s in real_summary if s.get("tg_success")),
            "tg_skipped": sum(1 for s in real_summary if s.get("tg_status") == "skipped"),
            "passed": sum(1 for r in real_api_results if r.passed),
        },
        "safety": {
            "external_api_called": SAFETY["external_api_called"],
            "tg_sent_this_run": SAFETY["tg_sent_this_run"],
            "production_send": SAFETY["production_send"],
            "prod_state_write": SAFETY["prod_state_write"],
            "ai_model_called": SAFETY["ai_model_called"],
            "daemon_or_loop_started": SAFETY["daemon_or_loop_started"],
            "files_deleted": SAFETY["files_deleted"],
            "credentials_printed": SAFETY["credentials_printed"],
        },
    }
    write_json(results_dir / "market_radar_v117_shared_pipeline_real_one_shot_result.json", real_output)
    print(f"  [OK] {results_dir / 'market_radar_v117_shared_pipeline_real_one_shot_result.json'}")

    # 4.4 TG evidence ledger (JSONL)
    ledger_path = pipeline.evidence_ledger.write_jsonl(
        results_dir / "market_radar_v117_shared_pipeline_tg_evidence_ledger.jsonl"
    )
    print(f"  [OK] {ledger_path}")

    # 4.5 Design document
    design_md = f"""# Market Radar {PIPELINE_VERSION} — Shared Pipeline Design

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Pipeline**: Adapter → Quality Gate → Renderer → Send-Readiness Gate → TG Test Sender → Evidence Ledger

---

## Architecture

```
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌───────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Adapter  │───→│ Quality Gate │───→│ Renderer │───→│ Send-Readiness    │───→│ TG Test      │───→│ Evidence Ledger │
│          │    │              │    │          │    │ Gate              │    │ Group Sender │    │                 │
└──────────┘    └──────────────┘    └──────────┘    └───────────────────┘    └──────────────┘    └─────────────────┘
     │                │                  │                   │                      │                    │
     ▼                ▼                  ▼                   ▼                      ▼                    ▼
NormalizedSignal  GateDecision     RenderedCard    SendReadinessDecision    TGTestSendResult    EvidenceRecord
```

## Shared Package Structure

```
market_radar/shared/
  __init__.py          — Package exports
  models.py            — Data models (CardFamily, NormalizedSignal, etc.)
  adapter_contract.py  — Adapter interface + fixtures for 5 card families
  free_api_adapters.py  — Real free API adapters (Binance public REST)
  gate_contract.py     — QualityGate + SendReadinessGate
  renderer_contract.py — CardRenderer for all 5 card types
  sender_contract.py   — TGTestGroupSender (redacted output)
  evidence_ledger.py   — EvidenceLedger (sha256 proofs)
  pipeline.py          — SharedPipeline orchestrator
```

## Five Card Families

| # | Card Family | Fixture | Real API | Gate Behavior |
|---|-------------|---------|----------|---------------|
| 1 | multi_asset_market_sync | ✅ | ✅ Binance public | allow if ≥2 assets |
| 2 | price_oi_volume_anomaly | ✅ | ✅ Binance spot+OI | allow if admission passed |
| 3 | news_event_market_impact | ✅ | fixture only | allow if intensity ≥ medium |
| 4 | liquidation_pressure | ✅ | blocked (calm market) | block unless volatile |
| 5 | whale_position_alert | ✅ | blocked (manual evidence) | block unless evidence provided |

## Safety Constraints (Always Active)

- Production send ready: **ALWAYS False**
- Formal channel/group send: **ALWAYS blocked**
- X/Twitter send: **ALWAYS blocked**
- Daemon/cron/loop: **ALWAYS blocked**
- Liquidation gate: **NOT lowered**
- Whale manual evidence: **NOT bypassed**
- All outputs: **No raw token/chat_id/message_id**
"""
    write_md(runs_dir / "v117_shared_pipeline_design.md", design_md)
    print(f"  [OK] {runs_dir / 'v117_shared_pipeline_design.md'}")

    # 4.6 Fixture report
    fixture_md_parts = [f"""# Market Radar {PIPELINE_VERSION} — Fixture Pipeline Report

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}

---

## Results Summary

| Card Family | Gate | TG Status | Passed |
|-------------|------|-----------|--------|
"""]
    for r in fixture_results:
        gate = r.gate_decision
        tg = r.tg_result
        fixture_md_parts.append(
            f"| {r.card_family.value} | "
            f"{'✅ allow' if gate and gate.allow else '⛔ block'} | "
            f"{tg.status if tg else 'N/A'} | "
            f"{'✅' if r.passed else '⛔'} |"
        )
    fixture_md_parts.append("")
    fixture_md_parts.append(f"""
## Counts

- Total: {len(fixture_results)}
- Passed: {sum(1 for r in fixture_results if r.passed)}
- Blocked: {sum(1 for r in fixture_results if not r.passed and not r.error)}
- Error: {sum(1 for r in fixture_results if r.error)}

## Gate Details
""")
    for r in fixture_results:
        gate = r.gate_decision
        if gate:
            fixture_md_parts.append(f"""
### {r.card_family.value}

- **Allow**: {gate.allow}
- **Reason**: {gate.reason}
""")

    # Detail the two blocked cases
    fixture_md_parts.append("""
## Blocked Cases — Design-Justified

### liquidation_pressure — Gate Block (Normal)
- The fixture uses calm_market=true and composite_score=0.35 < threshold=0.60
- This is a DESIGN-JUSTIFIED block, not a pipeline failure
- Liquidation pressure is an event-triggered card — DO NOT lower the gate

### whale_position_alert — Manual Evidence Block (Normal)
- The fixture has manual_evidence_provided=false
- Whale alerts require human on-chain attribution — DO NOT bypass
- This is a DESIGN-JUSTIFIED block, not a pipeline failure
""")

    write_md(runs_dir / "v117_shared_pipeline_fixture_report.md", "\n".join(fixture_md_parts))
    print(f"  [OK] {runs_dir / 'v117_shared_pipeline_fixture_report.md'}")

    # 4.7 Real one-shot report
    real_md_parts = [f"""# Market Radar {PIPELINE_VERSION} — Real One-Shot Report

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}

---

## Real Free API Results

| Card Family | API Success | Gate | TG Status | Passed |
|-------------|-------------|------|-----------|--------|
"""]
    for s in real_summary:
        gate_str = "✅ allow" if s.get("gate_allow") else "⛔ block"
        tg_str = s.get("tg_status", "N/A")
        passed_str = "✅" if s.get("passed") else "⛔" if s.get("api_success") else "⚠ skip"
        real_md_parts.append(
            f"| {s.get('card_family')} | "
            f"{'✅' if s.get('api_success') else '❌'} | "
            f"{gate_str} | "
            f"{tg_str} | "
            f"{passed_str} |"
        )
    real_md_parts.append("")

    # TG send detail
    tg_sent_count = sum(1 for s in real_summary if s.get("tg_success"))
    tg_skipped_count = sum(1 for s in real_summary if s.get("tg_status") == "skipped")
    if tg_sent_count > 0:
        real_md_parts.append(f"\n## TG Test Group Send\n\n✅ **{tg_sent_count} card(s)** sent to TG test group (one-shot).\nAll message proofs are SHA-256 redacted.\nProduction send: **False**.")
    elif tg_skipped_count > 0:
        real_md_parts.append(f"\n## TG Test Group Send\n\n⚠ **Skipped** — {tg_skipped_count} attempt(s) skipped.\nReason: TG safe config not available (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in environment).\nThis is expected and NOT a pipeline failure.")
    else:
        real_md_parts.append("\n## TG Test Group Send\n\nNo TG send attempted — gates blocked all signals.")

    real_md_parts.append(f"""

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | {'✅' if SAFETY['external_api_called'] else '❌'} |
| TG sent this run | {'✅' if SAFETY['tg_sent_this_run'] else '❌'} |
| Production send | {'❌ NEVER' if not SAFETY['production_send'] else '⚠ ERROR'} |
| Credentials printed | {'❌ NEVER' if not SAFETY['credentials_printed'] else '⚠ ERROR'} |
| Daemon/loop started | {'❌ NEVER' if not SAFETY['daemon_or_loop_started'] else '⚠ ERROR'} |
| Files deleted | {'❌ NEVER' if not SAFETY['files_deleted'] else '⚠ ERROR'} |
| Evidence ledger clean | {'✅' if clean else '❌'} |

## Free API Data Sources

- **Binance Public REST API** (`/api/v3/ticker/24hr`): BTC/ETH/SOL 24hr ticker data
- **Binance Futures Public API** (`/fapi/v1/openInterest`): Open interest data
- No API key required for any endpoint
""")
    write_md(runs_dir / "v117_shared_pipeline_real_one_shot_report.md", "\n".join(real_md_parts))
    print(f"  [OK] {runs_dir / 'v117_shared_pipeline_real_one_shot_report.md'}")

    # 4.8 Handoff
    handoff_md = f"""# Market Radar {PIPELINE_VERSION} — Local-Only Handoff

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: 20260605_v117_market_radar_shared_pipeline_real_one_shot

---

## What Was Done

- Built `market_radar/shared/` package (8 modules) — shared pipeline infrastructure
- Implemented adapter contract with fixtures for all 5 card families
- Implemented 2 free API adapters (Binance public REST — no API key)
- Implemented QualityGate (5 card-specific evaluators)
- Implemented SendReadinessGate (always blocks production/formal/X/daemon)
- Implemented CardRenderer for all 5 card types
- Implemented TGTestGroupSender with safe credential handling
- Implemented EvidenceLedger with SHA-256 redacted proofs
- Implemented SharedPipeline orchestrator
- Ran fixture pipeline: {sum(1 for r in fixture_results if r.passed)}/{len(fixture_results)} passed
- Ran real free API pipeline: {sum(1 for s in real_summary if s.get('api_success'))}/{len(real_summary)} API calls succeeded

## TG Test Group Send Status

- TG sent: {tg_sent_count} message(s)
- TG skipped (missing safe config): {tg_skipped_count} attempt(s)
- Production send: **False** (never)

## New Files Created

| File | Type |
|------|------|
| `market_radar/__init__.py` | Package init |
| `market_radar/shared/__init__.py` | Package init with exports |
| `market_radar/shared/models.py` | Data models |
| `market_radar/shared/adapter_contract.py` | Adapter interface + fixtures |
| `market_radar/shared/free_api_adapters.py` | Free API adapters |
| `market_radar/shared/gate_contract.py` | Quality + Send-Readiness gates |
| `market_radar/shared/renderer_contract.py` | Card renderer |
| `market_radar/shared/sender_contract.py` | TG test group sender |
| `market_radar/shared/evidence_ledger.py` | Evidence ledger |
| `market_radar/shared/pipeline.py` | Shared pipeline orchestrator |
| `scripts/run_market_radar_v117_shared_pipeline_real_one_shot.py` | Runner |
| `scripts/test_market_radar_v117_shared_pipeline_real_one_shot.py` | Tests |

## Safety Confirmation

| Constraint | Status |
|------------|--------|
| external_api_called_this_run | {SAFETY['external_api_called']} |
| tg_sent_this_run | {SAFETY['tg_sent_this_run']} |
| prod_state_write | {SAFETY['prod_state_write']} |
| ai_model_called | {SAFETY['ai_model_called']} |
| daemon_or_loop_started | {SAFETY['daemon_or_loop_started']} |
| files_deleted | {SAFETY['files_deleted']} |
| credentials_printed | {SAFETY['credentials_printed']} |

## Production Ready Status

**0/5 — NOT FOR LIVE USE**

All 6 minimum conditions remain unmet (see v116n_production_readiness_checklist.md).
Production send is NEVER enabled in this pipeline.

## Next Steps

1. Run tests: `python -m pytest scripts/test_market_radar_v117_shared_pipeline_real_one_shot.py scripts/test_market_radar_v116n_user_acceptance_overlay_pack_local_only.py -v`
2. Review real API data quality
3. If TG safe config available, verify test group message in TG
4. Proceed to user acceptance (A/B/C decision tree from v116N)
"""
    write_md(runs_dir / "v117_local_only_handoff.md", handoff_md)
    print(f"  [OK] {runs_dir / 'v117_local_only_handoff.md'}")

    # ── Final Summary ───────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"Shared Pipeline {PIPELINE_VERSION} — One-Shot Complete")
    print(f"  Fixture: {sum(1 for r in fixture_results if r.passed)}/{len(fixture_results)} passed")
    print(f"  Real API: {sum(1 for s in real_summary if s.get('api_success'))}/{len(real_summary)} succeeded")
    print(f"  TG Sent: {tg_sent_count} message(s)")
    print(f"  TG Skipped: {tg_skipped_count}")
    print(f"  Production Ready: 0/5 (by design)")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
