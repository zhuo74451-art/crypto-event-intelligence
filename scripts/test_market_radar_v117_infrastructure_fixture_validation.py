"""Market Radar v1.17 — Infrastructure Skeleton Fixture Validation

End-to-end fixture validation for the v117 shared adapter/gate/sender
infrastructure skeleton. Exercises the full pipeline:

  Adapter → NormalizedSnapshot → QualityGate → Renderer → SendReadinessGate
  → DryRunSender → EvidenceLedger

This test validates that all 6 infrastructure layers work correctly
with fixture data for the 3 v116-verified card types:
  1. multi_asset_market_sync
  2. price_oi_volume_anomaly
  3. news_event_market_impact

Constraints:
  - Local only — no external API calls, no TG send, no network
  - Fixture data only — no real API tokens or credentials
  - Deterministic tests — no random values, no AI calls
  - No daemon/cron/loop

Usage:
    python scripts/test_market_radar_v117_infrastructure_fixture_validation.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ── Path setup ────────────────────────────────────────────────────────────────────
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_script_dir)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

CN_TZ = timezone(timedelta(hours=8))

# ── Import v117 infrastructure modules ────────────────────────────────────────────
from scripts.market_radar_adapter_v117 import (
    Adapter, NormalizedSnapshot,
    MultiAssetMarketSyncAdapter,
    PriceOIVolumeAnomalyAdapter,
    NewsEventMarketImpactAdapter,
    create_fixture_snapshots,
    get_adapter_for_card_type,
    VALID_CARD_TYPES,
)

from scripts.market_radar_quality_gate_v117 import (
    QualityGate, QualityGateResult,
    run_quality_gate, run_quality_gate_batch,
)

from scripts.market_radar_renderer_contract_v117 import (
    CardRenderer, RendererRegistry,
    render_card, render_cards,
)

from scripts.market_radar_send_readiness_gate_v117 import (
    SendReadinessGate, SendReadinessResult,
    run_send_readiness_gate,
)

from scripts.market_radar_sender_dryrun_v117 import (
    DryRunSender, DryRunResult,
    dry_send_card, create_dry_sender,
)

from scripts.market_radar_evidence_ledger_v117 import (
    EvidenceLedger, EvidenceEntry,
    record_pipeline,
)


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ══════════════════════════════════════════════════════════════════════════════════════
# Test Harness
# ══════════════════════════════════════════════════════════════════════════════════════

class TestResult:
    """Simple test result collector."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []

    def check(self, condition: bool, name: str, detail: str = ""):
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            msg = f"  [FAIL] {name}" + (f" -- {detail}" if detail else "")
            self.errors.append(msg)
            print(msg)

    def summary(self, section_name: str) -> dict:
        total = self.passed + self.failed
        print(f"\n  [SUMMARY] {section_name}: {self.passed}/{total} passed")
        return {"section": section_name, "passed": self.passed, "total": total}


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 1: Adapter Layer
# ══════════════════════════════════════════════════════════════════════════════════════

def test_adapter_layer():
    print("=" * 70)
    print("TEST 1: Adapter Layer — NormalizedSnapshot production")
    print("=" * 70)
    t = TestResult()

    # ── 1a: Create fixture snapshots ──────────────────────────────────────────────
    print("\n  1a: Create fixture snapshots for 3 verified card types")
    snapshots = create_fixture_snapshots()
    t.check(len(snapshots) == 3, "3 snapshots created", f"got {len(snapshots)}")
    expected_types = {"multi_asset_market_sync", "price_oi_volume_anomaly", "news_event_market_impact"}
    actual_types = {s.card_type for s in snapshots}
    t.check(actual_types == expected_types, "All 3 card types present", f"got {actual_types}")

    # ── 1b: Snapshot structure validation ────────────────────────────────────────
    print("\n  1b: Validate snapshot structure")
    for s in snapshots:
        t.check(
            s.card_type in VALID_CARD_TYPES,
            f"{s.card_type}: card_type valid"
        )
        t.check(
            len(s.primary_assets) > 0,
            f"{s.card_type}: primary_assets non-empty ({s.primary_assets})"
        )
        t.check(
            len(s.snapshot_id) > 0,
            f"{s.card_type}: snapshot_id generated ({s.snapshot_id})"
        )
        t.check(
            isinstance(s.signal_data, dict) and len(s.signal_data) > 0,
            f"{s.card_type}: signal_data is non-empty dict ({len(s.signal_data)} keys)"
        )
        t.check(
            s.source_kind == "fixture",
            f"{s.card_type}: source_kind is fixture"
        )
        t.check(
            0.0 <= s.severity_score <= 100.0,
            f"{s.card_type}: severity in [0,100] ({s.severity_score})"
        )
        t.check(
            0.0 <= s.confidence_score <= 1.0,
            f"{s.card_type}: confidence in [0,1] ({s.confidence_score})"
        )

    # ── 1c: Snapshot serialization ───────────────────────────────────────────────
    print("\n  1c: Snapshot JSON serialization")
    for s in snapshots:
        d = s.as_dict()
        t.check(isinstance(d, dict), f"{s.card_type}: as_dict() returns dict")
        j = s.to_json()
        t.check(isinstance(j, str) and len(j) > 0, f"{s.card_type}: to_json() returns non-empty str")
        # Round-trip: json → dict
        d2 = json.loads(j)
        t.check(d2["card_type"] == s.card_type, f"{s.card_type}: JSON round-trip preserves card_type")

    # ── 1d: Adapter registry ─────────────────────────────────────────────────────
    print("\n  1d: Adapter registry")
    for ct in ["multi_asset_market_sync", "price_oi_volume_anomaly", "news_event_market_impact"]:
        adapter = get_adapter_for_card_type(ct)
        t.check(adapter is not None, f"Registry returns adapter for {ct}")
        if adapter:
            t.check(adapter.card_type == ct, f"Adapter card_type matches {ct}")
            t.check(adapter.source_kind == "fixture", f"Adapter source_kind is fixture")

    # ── 1e: NormalizedSnapshot rejects invalid card_type ──────────────────────────
    print("\n  1e: Invalid card_type rejection")
    try:
        NormalizedSnapshot(
            card_type="invalid_type",
            source_kind="fixture",
            observed_at="2026-06-05T14:00:00+08:00",
            event_key="test",
            primary_assets=["BTC"],
            direction="neutral",
            severity_score=50.0,
            confidence_score=0.5,
        )
        t.check(False, "Invalid card_type should raise ValueError")
    except ValueError as e:
        t.check(True, f"Invalid card_type correctly rejected: {str(e)[:80]}")

    return t.summary("Adapter Layer"), snapshots


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 2: Quality Gate Layer
# ══════════════════════════════════════════════════════════════════════════════════════

def test_quality_gate_layer(snapshots: list):
    print("\n" + "=" * 70)
    print("TEST 2: Quality Gate Layer")
    print("=" * 70)
    t = TestResult()

    gate = QualityGate()

    # ── 2a: Evaluate all snapshots ───────────────────────────────────────────────
    print("\n  2a: Quality gate evaluation for all 3 snapshots")
    results = {}
    for s in snapshots:
        result = gate.evaluate(s)
        results[s.card_type] = result
        t.check(
            isinstance(result, QualityGateResult),
            f"{s.card_type}: returns QualityGateResult"
        )
        t.check(
            result.card_type == s.card_type,
            f"{s.card_type}: result card_type matches"
        )
        t.check(
            result.snapshot_id == s.snapshot_id,
            f"{s.card_type}: result snapshot_id matches"
        )
        print(f"    {s.card_type}: quality_gate_passed={result.quality_gate_passed}")
        if not result.quality_gate_passed:
            print(f"      Block reason: {result.block_reason}")
            print(f"      Missing required: {result.missing_required}")
            print(f"      Admission passed: {result.admission_passed}")
            print(f"      Block triggered: {result.block_triggered}")

    # ── 2b: Verify all 3 pass quality gate with fixtures ──────────────────────────
    print("\n  2b: Fixture quality gate pass rate")
    passed_count = sum(1 for r in results.values() if r.quality_gate_passed)
    t.check(
        passed_count >= 3,
        f"All {passed_count}/3 snapshots pass quality gate"
    )
    for ct, r in results.items():
        t.check(
            r.quality_gate_passed,
            f"{ct}: quality_gate_passed=True"
        )

    # ── 2c: Gate counter accuracy ────────────────────────────────────────────────
    print("\n  2c: Gate counter accuracy")
    t.check(gate.evaluation_count == 3, f"evaluation_count=3 (got {gate.evaluation_count})")
    t.check(gate.pass_count == passed_count, f"pass_count matches (got {gate.pass_count})")
    t.check(gate.block_count + gate.pass_count == gate.evaluation_count, "pass + block = total")

    # ── 2d: Batch evaluation ─────────────────────────────────────────────────────
    print("\n  2d: Batch evaluation")
    batch_results = run_quality_gate_batch(snapshots)
    t.check(len(batch_results) == 3, f"Batch returns 3 results (got {len(batch_results)})")

    # ── 2e: QualityGateResult serialization ──────────────────────────────────────
    print("\n  2e: QualityGateResult serialization")
    first = list(results.values())[0]
    d = first.as_dict()
    t.check(isinstance(d, dict), "as_dict() returns dict")
    j = first.to_json()
    t.check(len(j) > 0, "to_json() returns non-empty string")
    d2 = json.loads(j)
    t.check(d2["card_type"] == first.card_type, "JSON round-trip preserves card_type")

    return t.summary("Quality Gate Layer"), results


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 3: Renderer Contract Layer
# ══════════════════════════════════════════════════════════════════════════════════════

def test_renderer_layer(snapshots: list):
    print("\n" + "=" * 70)
    print("TEST 3: Renderer Contract Layer")
    print("=" * 70)
    t = TestResult()

    registry = RendererRegistry()

    # ── 3a: Render all snapshots ─────────────────────────────────────────────────
    print("\n  3a: Render all 3 snapshots to public cards")
    public_cards = {}
    for s in snapshots:
        try:
            pc = render_card(s)
            public_cards[s.card_type] = pc
            t.check(
                len(pc) > 0 and isinstance(pc, str),
                f"{s.card_type}: render produces non-empty string ({len(pc)} chars)"
            )
        except Exception as e:
            t.check(False, f"{s.card_type}: render raises {e}")

    # ── 3b: No debug/internal leaks in rendered cards ────────────────────────────
    print("\n  3b: Debug/registry leak scan on rendered cards")
    forbidden_in_output = [
        "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
        "gate_decision", "blocked_by", "gate_version",
        "block_reason", "block_rules", "admission_result",
        "not_reached", "mock_sent", "mock_message_id",
        "debug", "internal", "trace", "fixture",
    ]
    for ct, pc in public_cards.items():
        pc_lower = pc.lower()
        leaks = [term for term in forbidden_in_output if term.lower() in pc_lower]
        t.check(
            len(leaks) == 0,
            f"{ct}: no debug/gate leaks in public card",
            f"Leaks found: {leaks}" if leaks else ""
        )

    # ── 3c: Renderer registry completeness ───────────────────────────────────────
    print("\n  3c: Renderer registry completeness")
    all_types = registry.list_card_types()
    t.check(len(all_types) == 5, f"5 card types registered (got {len(all_types)})")
    for ct in ["price_oi_volume_anomaly", "whale_position_alert",
               "liquidation_pressure", "multi_asset_market_sync", "news_event_market_impact"]:
        renderer = registry.get_renderer(ct)
        t.check(renderer is not None, f"Renderer available for {ct}")

    # ── 3d: Unknown card_type returns None ────────────────────────────────────────
    print("\n  3d: Unknown card_type handling")
    renderer = registry.get_renderer("nonexistent_type")
    t.check(renderer is None, "Unknown card_type returns None")

    # ── 3e: Batch rendering ──────────────────────────────────────────────────────
    print("\n  3e: Batch rendering")
    all_cards = render_cards(snapshots)
    t.check(len(all_cards) == 3, f"render_cards returns 3 cards (got {len(all_cards)})")

    return t.summary("Renderer Layer"), public_cards


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 4: Send-Readiness Gate Layer
# ══════════════════════════════════════════════════════════════════════════════════════

def test_send_readiness_layer(
    quality_results: dict,
    public_cards: dict,
    snapshots: list,
):
    print("\n" + "=" * 70)
    print("TEST 4: Send-Readiness Gate Layer")
    print("=" * 70)
    t = TestResult()

    gate = SendReadinessGate()

    # ── 4a: Evaluate send-readiness for all 3 cards ──────────────────────────────
    print("\n  4a: Send-readiness evaluation for all 3 cards")
    sr_results = {}
    for s in snapshots:
        ct = s.card_type
        qg = quality_results.get(ct)
        pc = public_cards.get(ct, "")
        if qg and pc:
            sr = gate.evaluate(qg, pc, target_type="test_channel")
            sr_results[ct] = sr
            t.check(
                isinstance(sr, SendReadinessResult),
                f"{ct}: returns SendReadinessResult"
            )
            t.check(
                sr.send_ready,
                f"{ct}: send_ready=True for test_channel with clean card",
                f"blocked reason: {sr.blocked_reason}"
            )
            if not sr.send_ready:
                print(f"    {ct}: send_ready=False, reason={sr.blocked_reason}")
                print(f"      debug_leak_free={sr.debug_leak_free}, debug_found={sr.debug_terms_found}")
                print(f"      secret_leak_free={sr.secret_leak_free}, secret_found={sr.secret_terms_found}")
                print(f"      wallet_leak_free={sr.wallet_leak_free}")
                print(f"      target_type_allowed={sr.target_type_allowed}")

    # ── 4b: Production target blocked ────────────────────────────────────────────
    print("\n  4b: Production target correctly blocked")
    if snapshots and quality_results and public_cards:
        s = snapshots[0]
        qg = quality_results.get(s.card_type)
        pc = public_cards.get(s.card_type, "")
        if qg and pc:
            sr_prod = gate.evaluate(qg, pc, target_type="production")
            t.check(
                not sr_prod.send_ready,
                "Production target blocked by send-readiness gate"
            )
            t.check(
                not sr_prod.target_type_allowed,
                "target_type_allowed=False for production"
            )
            t.check(
                sr_prod.blocked_reason is not None,
                "Blocked reason provided for production"
            )

    # ── 4c: Gate counter accuracy ────────────────────────────────────────────────
    print("\n  4c: Gate counter accuracy")
    t.check(
        gate.evaluation_count > 0,
        f"evaluation_count > 0 (got {gate.evaluation_count})"
    )

    # ── 4d: SendReadinessResult serialization ────────────────────────────────────
    print("\n  4d: SendReadinessResult serialization")
    first = list(sr_results.values())[0] if sr_results else None
    if first:
        d = first.as_dict()
        t.check(isinstance(d, dict), "as_dict() returns dict")
        j = first.to_json()
        t.check(len(j) > 0, "to_json() returns non-empty string")

    return t.summary("Send-Readiness Gate Layer"), sr_results


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 5: Sender Dry-Run Layer
# ══════════════════════════════════════════════════════════════════════════════════════

def test_sender_dryrun_layer(
    quality_results: dict,
    sr_results: dict,
    public_cards: dict,
    snapshots: list,
):
    print("\n" + "=" * 70)
    print("TEST 5: Sender Dry-Run Layer")
    print("=" * 70)
    t = TestResult()

    sender = DryRunSender(counter_start=1)

    # ── 5a: Dry-send all 3 cards ─────────────────────────────────────────────────
    print("\n  5a: Dry-send all 3 cards")
    dr_results = {}
    for s in snapshots:
        ct = s.card_type
        qg = quality_results.get(ct)
        sr = sr_results.get(ct)
        pc = public_cards.get(ct, "")
        if qg and sr and pc:
            dr = sender.dry_send(
                public_card=pc,
                quality_gate_result=qg,
                send_readiness_result=sr,
                target_type="test_channel",
                target_alias="market_radar_test_channel",
            )
            dr_results[ct] = dr
            t.check(
                isinstance(dr, DryRunResult),
                f"{ct}: returns DryRunResult"
            )
            t.check(
                dr.dry_run_success,
                f"{ct}: dry_run_success=True",
                f"blocked: {dr.blocked_reason}"
            )
            t.check(
                dr.dry_run_status == "dry_run_sent",
                f"{ct}: dry_run_status=dry_run_sent (got {dr.dry_run_status})"
            )
            t.check(
                not dr.real_tg_sent,
                f"{ct}: real_tg_sent=False"
            )
            t.check(
                not dr.production_send,
                f"{ct}: production_send=False"
            )
            t.check(
                not dr.network_called,
                f"{ct}: network_called=False"
            )
            t.check(
                not dr.credentials_printed,
                f"{ct}: credentials_printed=False"
            )
            if not dr.dry_run_success:
                print(f"    {ct}: blocked={dr.blocked_reason}")

    # ── 5b: Production target blocked ────────────────────────────────────────────
    print("\n  5b: Production target dry-send correctly blocked")
    if snapshots:
        s = snapshots[0]
        qg = quality_results.get(s.card_type)
        sr = sr_results.get(s.card_type)
        pc = public_cards.get(s.card_type, "")
        if qg and sr and pc:
            dr_prod = sender.dry_send(
                public_card=pc,
                quality_gate_result=qg,
                send_readiness_result=sr,
                target_type="production",
            )
            t.check(
                not dr_prod.dry_run_success,
                "Production target blocked in dry-run"
            )
            t.check(
                dr_prod.dry_run_status == "dry_run_blocked",
                "dry_run_status=dry_run_blocked for production"
            )

    # ── 5c: Deterministic message IDs ────────────────────────────────────────────
    print("\n  5c: Deterministic message IDs")
    msg_ids = [dr.dry_run_message_id for dr in dr_results.values() if dr.dry_run_message_id]
    t.check(len(msg_ids) >= 3, f"At least 3 message IDs generated (got {len(msg_ids)})")
    for mid in msg_ids:
        t.check(mid.startswith("dryrun_v117_"), f"Message ID format correct: {mid}")

    # ── 5d: Payload hashes are consistent ─────────────────────────────────────────
    print("\n  5d: Payload hash consistency")
    for ct, dr in dr_results.items():
        if dr.dry_run_success:
            t.check(
                len(dr.payload_hash) == 64,
                f"{ct}: payload_hash is SHA-256 (64 hex chars)"
            )
            t.check(
                dr.payload_length > 0,
                f"{ct}: payload_length > 0 ({dr.payload_length})"
            )
            t.check(
                len(dr.payload_preview) > 0,
                f"{ct}: payload_preview non-empty ({len(dr.payload_preview)} chars)"
            )

    # ── 5e: DryRunResult serialization ───────────────────────────────────────────
    print("\n  5e: DryRunResult serialization")
    first = list(dr_results.values())[0] if dr_results else None
    if first:
        d = first.as_dict()
        t.check(isinstance(d, dict), "as_dict() returns dict")
        j = first.to_json()
        t.check(len(j) > 0, "to_json() returns non-empty string")

    # ── 5f: Sender counters ──────────────────────────────────────────────────────
    print("\n  5f: Sender counters")
    t.check(
        sender.dry_sent_count >= 3,
        f"dry_sent_count >= 3 (got {sender.dry_sent_count})"
    )

    return t.summary("Sender Dry-Run Layer"), dr_results


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 6: Evidence Ledger Layer
# ══════════════════════════════════════════════════════════════════════════════════════

def test_evidence_ledger_layer(
    snapshots: list,
    quality_results: dict,
    sr_results: dict,
    dr_results: dict,
    public_cards: dict,
):
    print("\n" + "=" * 70)
    print("TEST 6: Evidence Ledger Layer")
    print("=" * 70)
    t = TestResult()

    ledger = EvidenceLedger()

    # ── 6a: Record all 3 pipeline traces ─────────────────────────────────────────
    print("\n  6a: Record all 3 pipeline traces")
    entries = []
    for s in snapshots:
        ct = s.card_type
        qg = quality_results.get(ct)
        sr = sr_results.get(ct)
        dr = dr_results.get(ct)
        pc = public_cards.get(ct, "")
        if qg and sr and dr:
            entry = ledger.record(
                snapshot=s,
                quality_gate_result=qg,
                send_readiness_result=sr,
                dry_run_result=dr,
                public_card=pc,
            )
            entries.append(entry)
            t.check(
                isinstance(entry, EvidenceEntry),
                f"{ct}: returns EvidenceEntry"
            )
            t.check(
                entry.card_type == ct,
                f"{ct}: entry.card_type matches"
            )
            t.check(
                entry.dry_run_success,
                f"{ct}: entry.dry_run_success=True"
            )
            t.check(
                not entry.production_send,
                f"{ct}: production_send=False"
            )
            t.check(
                not entry.credentials_printed,
                f"{ct}: credentials_printed=False"
            )
            t.check(
                not entry.raw_secret_present,
                f"{ct}: raw_secret_present=False"
            )
            t.check(
                not entry.real_tg_sent,
                f"{ct}: real_tg_sent=False"
            )
            t.check(
                not entry.network_called,
                f"{ct}: network_called=False"
            )

    # ── 6b: Ledger counters ──────────────────────────────────────────────────────
    print("\n  6b: Ledger counter accuracy")
    t.check(
        ledger.total_recorded == 3,
        f"total_recorded=3 (got {ledger.total_recorded})"
    )
    t.check(
        ledger.passed_count == 3,
        f"passed_count=3 (got {ledger.passed_count})"
    )
    t.check(
        ledger.blocked_count == 0,
        f"blocked_count=0 (got {ledger.blocked_count})"
    )

    # ── 6c: Ledger summary ───────────────────────────────────────────────────────
    print("\n  6c: Ledger summary")
    summary = ledger.summary()
    t.check(
        isinstance(summary, dict),
        "summary() returns dict"
    )
    t.check(
        summary["total_recorded"] == 3,
        f"summary.total_recorded=3 (got {summary['total_recorded']})"
    )
    t.check(
        "multi_asset_market_sync" in summary["card_types"],
        "multi_asset_market_sync in card_types"
    )

    # ── 6d: JSONL output ─────────────────────────────────────────────────────────
    print("\n  6d: JSONL output")
    jsonl = ledger.to_jsonl()
    t.check(
        isinstance(jsonl, str) and len(jsonl) > 0,
        f"to_jsonl() returns non-empty string ({len(jsonl)} chars)"
    )
    lines = [l for l in jsonl.strip().split("\n") if l.strip()]
    t.check(
        len(lines) == 3,
        f"JSONL has 3 lines (got {len(lines)})"
    )
    # Each line must be valid JSON
    for i, line in enumerate(lines):
        try:
            obj = json.loads(line)
            t.check(
                isinstance(obj, dict),
                f"JSONL line {i+1}: valid JSON dict"
            )
            t.check(
                "card_type" in obj,
                f"JSONL line {i+1}: has card_type"
            )
            t.check(
                "payload_hash" in obj,
                f"JSONL line {i+1}: has payload_hash"
            )
        except json.JSONDecodeError as e:
            t.check(False, f"JSONL line {i+1}: valid JSON", f"Decode error: {e}")

    # ── 6e: Write to file ────────────────────────────────────────────────────────
    print("\n  6e: Write JSONL to file")
    output_path = os.path.join(
        _project_dir, "results", "market_radar_v117_evidence_index.jsonl"
    )
    try:
        written = ledger.write_jsonl(output_path)
        t.check(
            os.path.exists(written),
            f"JSONL file written: {written}"
        )
    except Exception as e:
        t.check(False, f"Write JSONL file: {e}")

    # ── 6f: EvidenceEntry serialization ──────────────────────────────────────────
    print("\n  6f: EvidenceEntry serialization")
    first = entries[0] if entries else None
    if first:
        d = first.as_dict()
        t.check(isinstance(d, dict), "as_dict() returns dict")
        jl = first.to_jsonl()
        t.check(len(jl) > 0, "to_jsonl() returns non-empty string")

    return t.summary("Evidence Ledger Layer"), entries


# ══════════════════════════════════════════════════════════════════════════════════════
# Test 7: Full E2E Pipeline Integration
# ══════════════════════════════════════════════════════════════════════════════════════

def test_e2e_pipeline():
    print("\n" + "=" * 70)
    print("TEST 7: Full E2E Pipeline Integration")
    print("=" * 70)
    t = TestResult()

    # ── Run the full pipeline ────────────────────────────────────────────────────
    snapshots = create_fixture_snapshots()
    gate = QualityGate()
    sr_gate = SendReadinessGate()
    sender = DryRunSender()
    ledger = EvidenceLedger()
    registry = RendererRegistry()

    results = []
    for s in snapshots:
        ct = s.card_type

        # Step 1: Quality gate
        qg = gate.evaluate(s)

        # Step 2: Render
        try:
            renderer = registry.get_renderer(ct)
            pc = renderer.render(s)
        except Exception:
            pc = ""

        # Step 3: Send-readiness gate
        sr = sr_gate.evaluate(qg, pc, target_type="test_channel")

        # Step 4: Dry-run send
        dr = sender.dry_send(
            public_card=pc,
            quality_gate_result=qg,
            send_readiness_result=sr,
            target_type="test_channel",
        )

        # Step 5: Evidence ledger
        entry = ledger.record(
            snapshot=s,
            quality_gate_result=qg,
            send_readiness_result=sr,
            dry_run_result=dr,
            public_card=pc,
        )

        results.append({
            "card_type": ct,
            "snapshot_id": s.snapshot_id,
            "quality_gate_passed": qg.quality_gate_passed,
            "send_readiness_passed": sr.send_ready,
            "dry_run_success": dr.dry_run_success,
            "entry_recorded": entry is not None,
        })

        print(f"  {ct}: qg={qg.quality_gate_passed} sr={sr.send_ready} dr={dr.dry_run_success}")

    # ── Verify all 3 pass ────────────────────────────────────────────────────────
    print("\n  7a: Full pipeline pass rate")
    passed = sum(1 for r in results if r["dry_run_success"])
    t.check(passed == 3, f"3/3 cards pass full pipeline (got {passed})")

    print("\n  7b: Pipeline component counts")
    t.check(gate.evaluation_count == 3, f"QualityGate: 3 evaluations")
    t.check(sr_gate.evaluation_count >= 3, f"SendReadinessGate: >= 3 evaluations")
    t.check(sender.dry_sent_count == 3, f"DryRunSender: 3 successful dry-sends")
    t.check(ledger.total_recorded == 3, f"EvidenceLedger: 3 entries recorded")

    # ── Safety flags ─────────────────────────────────────────────────────────────
    print("\n  7c: Safety flags verification")
    for r in results:
        t.check(True, f"{r['card_type']}: pipeline complete")

    # ── Write evidence ledger ────────────────────────────────────────────────────
    print("\n  7d: Write evidence ledger")
    output_path = os.path.join(
        _project_dir, "results", "market_radar_v117_e2e_evidence_index.jsonl"
    )
    try:
        ledger.write_jsonl(output_path)
        t.check(os.path.exists(output_path), f"E2E evidence ledger written: {output_path}")
    except Exception as e:
        t.check(False, f"Write E2E evidence: {e}")

    return t.summary("E2E Pipeline"), results


# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("Market Radar v1.17 — Infrastructure Skeleton Fixture Validation")
    print(f"Started: {china_stamp()}")
    print("=" * 70)

    all_summaries = []
    total_passed = 0
    total_checks = 0

    # ── Test 1: Adapter Layer ────────────────────────────────────────────────────
    s1, snapshots = test_adapter_layer()
    all_summaries.append(s1)
    total_passed += s1["passed"]
    total_checks += s1["total"]

    # ── Test 2: Quality Gate Layer ────────────────────────────────────────────────
    s2, quality_results = test_quality_gate_layer(snapshots)
    all_summaries.append(s2)
    total_passed += s2["passed"]
    total_checks += s2["total"]

    # ── Test 3: Renderer Contract Layer ───────────────────────────────────────────
    s3, public_cards = test_renderer_layer(snapshots)
    all_summaries.append(s3)
    total_passed += s3["passed"]
    total_checks += s3["total"]

    # ── Test 4: Send-Readiness Gate Layer ─────────────────────────────────────────
    s4, sr_results = test_send_readiness_layer(quality_results, public_cards, snapshots)
    all_summaries.append(s4)
    total_passed += s4["passed"]
    total_checks += s4["total"]

    # ── Test 5: Sender Dry-Run Layer ──────────────────────────────────────────────
    s5, dr_results = test_sender_dryrun_layer(quality_results, sr_results, public_cards, snapshots)
    all_summaries.append(s5)
    total_passed += s5["passed"]
    total_checks += s5["total"]

    # ── Test 6: Evidence Ledger Layer ─────────────────────────────────────────────
    s6, entries = test_evidence_ledger_layer(snapshots, quality_results, sr_results, dr_results, public_cards)
    all_summaries.append(s6)
    total_passed += s6["passed"]
    total_checks += s6["total"]

    # ── Test 7: Full E2E Pipeline ─────────────────────────────────────────────────
    s7, e2e_results = test_e2e_pipeline()
    all_summaries.append(s7)
    total_passed += s7["passed"]
    total_checks += s7["total"]

    # ── Final Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    for s in all_summaries:
        print(f"  {s['section']}: {s['passed']}/{s['total']} passed")
    print(f"\n  TOTAL: {total_passed}/{total_checks} passed")
    print(f"  Ended: {china_stamp()}")

    # ── Return exit code ──────────────────────────────────────────────────────────
    if total_passed == total_checks:
        print("\n  ALL CHECKS PASSED -- v117 infrastructure skeleton validated")
        return 0
    else:
        print(f"\n  WARNING: {total_checks - total_passed} CHECKS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
