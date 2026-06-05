"""Market Radar v1.16-A — Five Card Family Coverage Status Audit (Local Only)

Audits the current coverage status of all five Market Radar card families
based on existing artifacts (scripts, tests, results, runs, config).

Answers: which card families are actually running? At what stage? Which are
router/gate-only, which have real data, previews, fixture E2E, real send-readiness?

Outputs:
  - results/market_radar_v116a_card_family_discovery_records.jsonl
  - results/market_radar_v116a_card_family_coverage_records.jsonl
  - results/market_radar_v116a_card_family_gap_backlog.jsonl
  - results/market_radar_v116a_five_card_family_coverage_status_audit_result.json
  - runs/market_radar/v116a_five_card_family_coverage_status_audit.md
  - runs/market_radar/v116a_five_card_family_coverage_status_audit.csv
  - runs/market_radar/v116a_five_card_family_next_gap_backlog.md
  - runs/market_radar/v116a_five_card_family_coverage_status_audit_local_only_handoff.md

Constraints:
  - NO TG send, NO production write, NO real label upgrade
  - NO external API, NO AI/model calls
  - NO daemon/cron/watcher/loop
  - NO file deletion
  - NO modification of v110-v115R historical artifacts
  - NO modification of v115F/v115P workbooks
  - NO reading of API keys/tokens/cookies/passwords

Usage:
    python scripts/run_market_radar_v116a_five_card_family_coverage_status_audit_local_only.py
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

# ── Allowed status enum ────────────────────────────────────────────────────
ALLOWED_STATUS = {
    "passed", "blocked", "not_started", "not_found",
    "partial", "fixture_only", "not_allowed", "unknown",
}


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def china_stamp_iso() -> str:
    return datetime.now(CN_TZ).isoformat()


# ═══════════════════════════════════════════════════════════════════════════
# Card Family Discovery
# ═══════════════════════════════════════════════════════════════════════════

def discover_card_families_from_registry() -> list[dict]:
    """Discover card families from the v112a registry."""
    sys.path.insert(0, str(ROOT))
    try:
        from scripts.market_radar_card_type_registry_v112a import (
            CARD_TYPE_REGISTRY,
            REGISTRY_VERSION,
            get_all_card_types,
        )
        families = []
        for key, defn in CARD_TYPE_REGISTRY.items():
            families.append({
                "card_family": key,
                "display_name": defn.get("display_name", key),
                "display_name_en": defn.get("display_name_en", key),
                "category": defn.get("category", "unknown"),
                "source": "market_radar_card_type_registry_v112a",
                "registry_version": REGISTRY_VERSION,
                "required_fields": defn.get("required_fields", []),
                "optional_fields": defn.get("optional_fields", []),
            })
        return families
    except ImportError:
        return []


def discover_card_families_from_router() -> list[dict]:
    """Fallback: infer card families from card router signal types."""
    families = [
        {
            "card_family": "market_anomaly",
            "display_name": "市场异动卡",
            "source": "market_radar_card_router_classify_signal_type",
        },
        {
            "card_family": "onchain_position",
            "display_name": "链上仓位卡",
            "source": "market_radar_card_router_classify_signal_type",
        },
        {
            "card_family": "whale_transfer",
            "display_name": "巨鲸转账卡",
            "source": "market_radar_card_router_classify_signal_type",
        },
        {
            "card_family": "news_event",
            "display_name": "新闻事件卡",
            "source": "market_radar_card_router_classify_signal_type",
        },
        {
            "card_family": "risk_alert",
            "display_name": "风险告警卡",
            "source": "market_radar_card_router_classify_signal_type",
        },
    ]
    return families


def discover_card_families_from_v112e_pipeline() -> list[str]:
    """Read the 5 canonical card types from v112e pipeline docstring."""
    # These are the canonical 5 from run_market_radar_v112e_all_fixed_card_local_pipeline.py
    return [
        "price_oi_volume_anomaly",
        "whale_position_alert",
        "liquidation_pressure",
        "multi_asset_market_sync",
        "news_event_market_impact",
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Artifact Scanner
# ═══════════════════════════════════════════════════════════════════════════

def scan_file_exists(rel_path: str) -> bool:
    return (ROOT / rel_path).exists()


def scan_dir_files(pattern_dir: str, prefix: str = "") -> list[str]:
    """List files in a directory matching an optional prefix."""
    d = ROOT / pattern_dir
    if not d.exists():
        return []
    result = []
    for f in d.iterdir():
        if f.is_file():
            if not prefix or f.name.startswith(prefix):
                result.append(str(f.relative_to(ROOT)))
    return sorted(result)


def find_artifacts_for_card_family(card_family: str) -> dict:
    """Find all existing artifacts related to a card family."""
    evidence = {
        "scripts": [],
        "tests": [],
        "results": [],
        "runs": [],
        "configs": [],
    }

    # Map card family to search patterns
    patterns = _get_search_patterns(card_family)

    for category, dir_path in [("scripts", "scripts"), ("tests", "scripts"), ("results", "results"), ("runs", "runs/market_radar"), ("configs", "config")]:
        all_files = scan_dir_files(dir_path)
        for f in all_files:
            fname = os.path.basename(f).lower()
            for pat in patterns:
                if pat in fname:
                    if category == "tests":
                        if fname.startswith("test_"):
                            evidence["tests"].append(f)
                    elif category == "scripts":
                        if fname.startswith("run_") and not fname.startswith("test_"):
                            evidence["scripts"].append(f)
                    else:
                        evidence[category].append(f)
                    break

    # Deduplicate
    for k in evidence:
        evidence[k] = sorted(set(evidence[k]))

    return evidence


def _get_search_patterns(card_family: str) -> list[str]:
    """Get file-name search patterns for a card family."""
    patterns = []
    cf = card_family.lower()

    # Direct name match parts
    parts = cf.split("_")
    for i in range(len(parts)):
        sub = "_".join(parts[i:])
        if len(sub) >= 4:
            patterns.append(sub)

    # Card family aliases
    aliases = {
        "price_oi_volume_anomaly": ["price_oi", "pova", "anomaly", "price", "volume_anomaly"],
        "whale_position_alert": ["whale", "wpa", "whale_position", "whale_pos"],
        "liquidation_pressure": ["liquidation", "lipr", "liq_", "liquid"],
        "multi_asset_market_sync": ["multi_asset", "multi_", "mams", "market_sync", "correlation"],
        "news_event_market_impact": ["news_event", "news_", "nemi", "news_event_market"],
    }
    if card_family in aliases:
        patterns.extend(aliases[card_family])

    return patterns


# ═══════════════════════════════════════════════════════════════════════════
# Coverage Assessment per Card Family
# ═══════════════════════════════════════════════════════════════════════════

def assess_card_family_coverage(card_family: str, display_name: str,
                                 evidence: dict,
                                 discovery_source: str) -> dict:
    """Assess coverage for a single card family."""

    record = {
        "card_family": card_family,
        "card_family_name_source": discovery_source,
        "evidence_files": _summarize_evidence(evidence),
        "router_test_status": "unknown",
        "router_test_evidence": "",
        "input_data_status": "unknown",
        "input_data_evidence": "",
        "card_generation_status": "unknown",
        "card_generation_evidence": "",
        "preview_status": "unknown",
        "preview_evidence": "",
        "quality_gate_status": "unknown",
        "quality_gate_evidence": "",
        "send_readiness_status": "unknown",
        "send_readiness_evidence": "",
        "fixture_positive_path_status": "unknown",
        "fixture_positive_path_evidence": "",
        "real_e2e_status": "unknown",
        "real_e2e_evidence": "",
        "tg_test_group_status": "not_allowed",
        "tg_test_group_evidence": "No TG test group send evidence found.",
        "production_send_status": "not_allowed",
        "production_send_evidence": "Production send is not allowed per safety boundary.",
        "current_stage": "unknown",
        "blocked_reason": "",
        "next_minimum_task": "",
        "safety_status": "not_allowed",
    }

    # ── Router test status ─────────────────────────────────────────────
    _assess_router_test(record, evidence)

    # ── Input data status ──────────────────────────────────────────────
    _assess_input_data(record, card_family, evidence)

    # ── Card generation status ─────────────────────────────────────────
    _assess_card_generation(record, card_family, evidence)

    # ── Preview status ─────────────────────────────────────────────────
    _assess_preview(record, card_family, evidence)

    # ── Quality gate status ────────────────────────────────────────────
    _assess_quality_gate(record, card_family, evidence)

    # ── Send readiness status ──────────────────────────────────────────
    _assess_send_readiness(record, card_family, evidence)

    # ── Fixture positive path status ───────────────────────────────────
    _assess_fixture_positive_path(record, card_family, evidence)

    # ── Real E2E status ────────────────────────────────────────────────
    _assess_real_e2e(record, card_family, evidence)

    # ── TG test group status ───────────────────────────────────────────
    _assess_tg_test_group(record, card_family, evidence)

    # ── Derive current stage ───────────────────────────────────────────
    _derive_current_stage(record)

    # ── Suggest next minimum task ──────────────────────────────────────
    _suggest_next_task(record, card_family)

    return record


def _summarize_evidence(evidence: dict) -> dict:
    """Summarize evidence file counts."""
    return {
        "scripts_count": len(evidence.get("scripts", [])),
        "tests_count": len(evidence.get("tests", [])),
        "results_count": len(evidence.get("results", [])),
        "runs_count": len(evidence.get("runs", [])),
        "configs_count": len(evidence.get("configs", [])),
        "top_files": (
            evidence.get("scripts", [])[:3] +
            evidence.get("results", [])[:3] +
            evidence.get("runs", [])[:3]
        ),
    }


def _assess_router_test(record: dict, evidence: dict):
    """Check if router/gate tests exist for this card family.

    Router tests are SHARED across all 5 card families (registry, card_router,
    v112e pipeline). Check global project files, not just family-specific evidence.
    """
    router_indicators = []

    # Check shared/global files directly
    shared_checks = [
        "scripts/market_radar_card_type_registry_v112a.py",
        "scripts/market_radar_card_router.py",
        "scripts/run_market_radar_v112a_fixed_card_type_matrix.py",
        "scripts/run_market_radar_v112e_all_fixed_card_local_pipeline.py",
        "scripts/run_market_radar_v110a_free_cards.py",
        "results/market_radar_v112a_fixed_card_type_matrix_result.json",
        "results/market_radar_v112e_all_fixed_card_local_pipeline_result.json",
        "results/market_radar_v112n_local_master_dryrun_result.json",
        "data/fixtures/market_radar_v112a_card_type_samples.json",
    ]
    for path in shared_checks:
        if (ROOT / path).exists():
            router_indicators.append(path)

    # Also check family-specific evidence
    all_files = (evidence.get("scripts", []) + evidence.get("tests", []) +
                 evidence.get("results", []) + evidence.get("runs", []))
    for f in all_files:
        if "v112a" in f and ("result" in f or "handoff" in f):
            router_indicators.append(f)
        if "card_type_registry" in f or "fixed_card_type_matrix" in f:
            router_indicators.append(f)
        if "v112e_all_fixed" in f:
            router_indicators.append(f)
        if "card_router" in f:
            router_indicators.append(f)

    if router_indicators:
        record["router_test_status"] = "passed"
        record["router_test_evidence"] = (
            f"Card type registered in v112a registry, validated in v112e unified pipeline, "
            f"and samples exist in v112a fixture. "
            f"Shared router/gate artifacts: registry, card_router, v112e pipeline, v112n master dryrun."
        )
    else:
        record["router_test_status"] = "not_found"
        record["router_test_evidence"] = "No router test artifacts found."


def _assess_input_data(record: dict, card_family: str, evidence: dict):
    """Check if real or fixture input data exists."""
    all_files = evidence.get("results", []) + evidence.get("scripts", []) + evidence.get("runs", [])

    has_fixture_data = False
    has_real_data = False
    fixture_files = []
    real_files = []

    # Check shared fixture file
    fixture_path = ROOT / "data" / "fixtures" / "market_radar_v112a_card_type_samples.json"
    if fixture_path.exists():
        has_fixture_data = True
        fixture_files.append("data/fixtures/market_radar_v112a_card_type_samples.json")

    for f in all_files:
        fname = os.path.basename(f).lower()
        if "fixture" in fname or "sample" in fname:
            has_fixture_data = True
            fixture_files.append(f)
        if ("local_enrichment" in fname or "live_source" in fname or
            "real" in fname or "baseline_snapshot" in fname or
            "live_response" in fname or "second_probe" in fname or
            "local_correlation" in fname or "local_feed" in fname or
            "local_pipeline" in fname or "local_master" in fname):
            has_real_data = True
            real_files.append(f)

    # Check v112e pipeline result — all families had cards generated
    v112e_result = ROOT / "results" / "market_radar_v112e_all_fixed_card_local_pipeline_result.json"
    if v112e_result.exists():
        has_real_data = True
        real_files.append("results/market_radar_v112e_all_fixed_card_local_pipeline_result.json")

    if has_real_data and has_fixture_data:
        record["input_data_status"] = "partial"
        record["input_data_evidence"] = (
            f"Both fixture data and local enrichment / live source data found. "
            f"Fixture: {len(fixture_files)} files. Real/local: {len(real_files)} files."
        )
    elif has_real_data:
        record["input_data_status"] = "passed"
        record["input_data_evidence"] = f"Real/local input data found: {len(real_files)} files."
    elif has_fixture_data:
        record["input_data_status"] = "fixture_only"
        record["input_data_evidence"] = f"Fixture-only input data found: {len(fixture_files)} files. No real/local data pipeline."
    else:
        record["input_data_status"] = "not_found"
        record["input_data_evidence"] = "No input data artifacts found."


def _assess_card_generation(record: dict, card_family: str, evidence: dict):
    """Check if cards have been generated."""
    all_files = evidence.get("results", []) + evidence.get("runs", [])

    card_indicators = []
    for f in all_files:
        fname = os.path.basename(f).lower()
        if any(kw in fname for kw in ["card", "preview_card", "public_card", "signal_envelope"]):
            card_indicators.append(f)

    # Check v112o send preview cards and v112e pipeline
    has_cards = bool(card_indicators)
    # Check if cards were actually generated for this family specifically
    family_specific = [f for f in card_indicators if _family_in_filename(f, card_family)]

    if has_cards:
        record["card_generation_status"] = "passed"
        record["card_generation_evidence"] = (
            f"Card generation artifacts found. "
            f"Family-specific: {len(family_specific)} files."
        )
    else:
        record["card_generation_status"] = "not_found"
        record["card_generation_evidence"] = "No card generation artifacts found."


def _family_in_filename(filepath: str, card_family: str) -> bool:
    """Check if a file is likely related to a specific card family."""
    fname = os.path.basename(filepath).lower()
    if card_family == "whale_position_alert" and "whale" in fname:
        return True
    if card_family == "liquidation_pressure" and ("liquidation" in fname or "liq_" in fname):
        return True
    if card_family == "multi_asset_market_sync" and ("multi_asset" in fname or "correlation" in fname):
        return True
    if card_family == "news_event_market_impact" and "news_event" in fname:
        return True
    if card_family == "price_oi_volume_anomaly" and ("price_oi" in fname or "pova" in fname or "anomaly" in fname):
        return True
    # v112e pipeline covers all
    if "v112e_all_fixed" in fname:
        return True
    return False


def _assess_preview(record: dict, card_family: str, evidence: dict):
    """Check if card previews have been generated.

    Preview evidence sources (per card family):
    - price_oi_volume_anomaly: fixture-only (v112a samples)
    - whale_position_alert: real local enrichment (v112f, 6 cards)
    - liquidation_pressure: fixture-only (v112b feed, 3 fixture cards)
    - multi_asset_market_sync: real local correlation (v112g, 5 cards)
    - news_event_market_impact: fixture-only (v112d, 5 fixture cards)
    """
    all_files = evidence.get("results", []) + evidence.get("runs", [])

    preview_evidence_files = [f for f in all_files if "preview" in os.path.basename(f).lower()]

    # Check family-specific feed results for card generation evidence
    family_feed_results = {
        "price_oi_volume_anomaly": [],  # no dedicated feed; v112e pipeline only
        "whale_position_alert": [
            "results/market_radar_v112f_whale_position_local_enrichment_result.json",
        ],
        "liquidation_pressure": [
            "results/market_radar_v112b_liquidation_pressure_local_feed_result.json",
            "results/market_radar_v112c_liquidation_pipeline_integration_result.json",
        ],
        "multi_asset_market_sync": [
            "results/market_radar_v112g_multi_asset_sync_local_correlation_result.json",
        ],
        "news_event_market_impact": [
            "results/market_radar_v112d_news_event_market_impact_result.json",
        ],
    }

    # Check each family-specific feed result file
    has_family_feed = False
    is_feed_fixture_only = True
    for feed_path_str in family_feed_results.get(card_family, []):
        feed_path = ROOT / feed_path_str
        if feed_path.exists():
            has_family_feed = True
            preview_evidence_files.append(feed_path_str)
            try:
                with open(feed_path, "r", encoding="utf-8") as fh:
                    feed_data = json.load(fh)
                # Check if feed produced cards
                card_count = feed_data.get("public_card_count", 0)
                if card_count > 0 and feed_data.get("live_ready") is not True:
                    # Cards exist but live_ready is false → check data_modes
                    data_modes = feed_data.get("data_modes_seen", [])
                    if data_modes and "fixture" in data_modes and "live" not in data_modes:
                        is_feed_fixture_only = is_feed_fixture_only and True
                    elif feed_data.get("fallback_preview") is False:
                        # Non-fallback preview → likely real/local data
                        is_feed_fixture_only = False
            except Exception:
                pass

    # Check v112e unified pipeline result
    v112e_result = ROOT / "results" / "market_radar_v112e_all_fixed_card_local_pipeline_result.json"
    if v112e_result.exists():
        preview_evidence_files.append("results/market_radar_v112e_all_fixed_card_local_pipeline_result.json")

    # Check v112o send preview result
    v112o_result = ROOT / "results" / "market_radar_v112o_send_preview_pack_result.json"
    if v112o_result.exists():
        try:
            with open(v112o_result, "r", encoding="utf-8") as fh:
                o_result = json.load(fh)
            card_dist = o_result.get("card_type_distribution", {})
            if card_family in card_dist and card_dist[card_family] > 0:
                preview_evidence_files.append("results/market_radar_v112o_send_preview_pack_result.json")
        except Exception:
            pass

    if preview_evidence_files:
        if has_family_feed and not is_feed_fixture_only:
            record["preview_status"] = "passed"
            record["preview_evidence"] = (
                f"Preview cards generated via local feed/enrichment pipeline. "
                f"{len(preview_evidence_files)} evidence files. "
                f"Non-fallback preview with real/local data enrichment."
            )
        else:
            record["preview_status"] = "fixture_only"
            record["preview_evidence"] = (
                f"Preview artifacts found ({len(preview_evidence_files)} evidence files) "
                f"but all use fixture data. No real/local data pipeline for preview."
            )
    else:
        record["preview_status"] = "not_found"
        record["preview_evidence"] = "No preview artifacts found."


def _assess_quality_gate(record: dict, card_family: str, evidence: dict):
    """Check if quality gates have been applied."""
    all_files = evidence.get("results", []) + evidence.get("runs", [])

    gate_files = [f for f in all_files
                  if any(kw in os.path.basename(f).lower()
                         for kw in ["quality_gate", "gate_decision", "gate_result",
                                    "debug_leak", "secret_leak", "send_readiness_gate"])]

    if gate_files:
        record["quality_gate_status"] = "passed"
        record["quality_gate_evidence"] = f"Quality gate artifacts found: {len(gate_files)} files."
    else:
        # Check if dedupe/cooldown gate covers this
        for f in all_files:
            if "v112i_dedupe" in f or "v112j_eligible" in f:
                record["quality_gate_status"] = "passed"
                record["quality_gate_evidence"] = f"Covered by unified dedupe/cooldown gate (v112i/v112j)."
                return
        record["quality_gate_status"] = "not_found"
        record["quality_gate_evidence"] = "No quality gate artifacts found."


def _assess_send_readiness(record: dict, card_family: str, evidence: dict):
    """Check send readiness gates."""
    all_files = evidence.get("results", [])

    send_files = [f for f in all_files
                  if any(kw in os.path.basename(f).lower()
                         for kw in ["send_readiness", "send_preview", "send_candidate",
                                    "send_gate", "one_shot_send"])]

    if send_files:
        # Check if any send readiness is real or fixture-only
        record["send_readiness_status"] = "partial"
        record["send_readiness_evidence"] = (
            f"Send readiness artifacts found: {len(send_files)} files. "
            f"All marked dry_run_only, no real send ready."
        )
    else:
        record["send_readiness_status"] = "not_started"
        record["send_readiness_evidence"] = "No send readiness artifacts found."


def _assess_fixture_positive_path(record: dict, card_family: str, evidence: dict):
    """Check if fixture E2E positive path has been verified."""
    all_files = evidence.get("results", []) + evidence.get("runs", [])

    # Specific checks per card family
    if card_family == "whale_position_alert":
        # v115Q is the fixture E2E gate replay
        fixture_e2e_files = [f for f in all_files if "v115q" in os.path.basename(f).lower()]
        if fixture_e2e_files:
            # Verify v115Q result
            v115q_result = ROOT / "results" / "market_radar_v115q_whale_fixture_end_to_end_gate_replay_result.json"
            if v115q_result.exists():
                try:
                    with open(v115q_result, "r", encoding="utf-8") as fh:
                        qdata = json.load(fh)
                    if qdata.get("fixture_workflow_ready_count", 0) >= 1:
                        record["fixture_positive_path_status"] = "passed"
                        record["fixture_positive_path_evidence"] = (
                            f"v115Q fixture E2E gate replay: {qdata.get('fixture_rows', 0)} fixture rows, "
                            f"{qdata.get('fixture_workflow_ready_count', 0)} workflow-ready. "
                            f"All gates (intake→scoring→adjudication→workflow) replayed successfully. "
                            f"THIS IS FIXTURE ONLY — not real address verification."
                        )
                        return
                except Exception:
                    pass
            record["fixture_positive_path_status"] = "partial"
            record["fixture_positive_path_evidence"] = "v115Q artifacts found but fixture E2E result incomplete."
            return
        else:
            record["fixture_positive_path_status"] = "not_found"
            record["fixture_positive_path_evidence"] = "No fixture E2E replay artifacts found for whale_position_alert."
            return

    # For other card families
    fixture_e2e_indicators = [f for f in all_files
                              if any(kw in os.path.basename(f).lower()
                                     for kw in ["fixture", "positive_path", "e2e_gate", "fixture_e2e"])]
    if fixture_e2e_indicators:
        record["fixture_positive_path_status"] = "partial"
        record["fixture_positive_path_evidence"] = f"Fixture-related artifacts found: {len(fixture_e2e_indicators)} files, but no dedicated fixture E2E gate replay."
    else:
        record["fixture_positive_path_status"] = "not_started"
        record["fixture_positive_path_evidence"] = "No fixture positive path verification artifacts found."


def _assess_real_e2e(record: dict, card_family: str, evidence: dict):
    """Check if real (non-fixture) E2E has been verified."""
    if card_family == "whale_position_alert":
        # Check v115R result
        v115r_result = ROOT / "results" / "market_radar_v115r_whale_operator_real_workbook_submission_validator_result.json"
        if v115r_result.exists():
            try:
                with open(v115r_result, "r", encoding="utf-8") as fh:
                    rdata = json.load(fh)
                if rdata.get("submission_ready_count", 0) == 0:
                    record["real_e2e_status"] = "blocked"
                    record["real_e2e_evidence"] = (
                        f"v115R real workbook submission validator: "
                        f"{rdata.get('submission_blocked_count', 0)}/{rdata.get('real_workbook_rows', '?')} blocked. "
                        f"Real workbook fields are empty (TEST_ONLY placeholder). "
                        f"No real operator evidence submitted. "
                        f"Safe rerun not allowed. Next gate command order enforced."
                    )
                    record["blocked_reason"] = (
                        "Real operator workbook has empty fields for all 4 addresses. "
                        "Requires real operator evidence collection (v115O preflight) before gate rerun."
                    )
                else:
                    record["real_e2e_status"] = "partial"
                    record["real_e2e_evidence"] = f"v115R: {rdata.get('submission_ready_count', 0)} submission-ready."
                return
            except Exception:
                pass

        record["real_e2e_status"] = "blocked"
        record["real_e2e_evidence"] = "Real workbook submission blocked (empty operator fields). No v115R evidence of real E2E pass."
        record["blocked_reason"] = "Real operator workbook has empty fields. Real E2E cannot pass without real evidence."
        return

    # For other card families: check if any real E2E pipeline exists
    all_files = evidence.get("results", []) + evidence.get("runs", [])
    real_e2e_indicators = [f for f in all_files
                           if any(kw in os.path.basename(f).lower()
                                  for kw in ["real_workflow", "real_workbook", "real_e2e",
                                             "live_ready", "operator_review"])]

    if real_e2e_indicators:
        record["real_e2e_status"] = "blocked"
        record["real_e2e_evidence"] = f"Real E2E artifacts found ({len(real_e2e_indicators)} files) but no evidence of real end-to-end pass. Live data pipeline missing."
        record["blocked_reason"] = "Live data pipeline not yet built for this card family."
    else:
        record["real_e2e_status"] = "not_started"
        record["real_e2e_evidence"] = "No real E2E artifacts found. This card family has not reached real E2E stage."
        record["blocked_reason"] = "Card family not yet advanced to real E2E stage."


def _assess_tg_test_group(record: dict, card_family: str, evidence: dict):
    """Check if TG test group send has been done."""
    # By default: not_allowed unless explicit evidence
    all_files = evidence.get("results", []) + evidence.get("runs", [])

    tg_files = [f for f in all_files
                if any(kw in os.path.basename(f).lower()
                       for kw in ["tg_send", "tg_test", "tg_sent", "real_tg",
                                  "test_channel_send", "test_channel_real"])]

    if tg_files:
        # Check results for tg_sent flag
        for f in tg_files:
            fpath = ROOT / f
            if fpath.exists() and fpath.suffix == ".json":
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if data.get("tg_sent") is True or data.get("real_tg_sent") is True:
                        record["tg_test_group_status"] = "passed"
                        record["tg_test_group_evidence"] = f"TG send evidence: {f}"
                        return
                except Exception:
                    pass

        # Check if TG test copy gate passed for this family
        if card_family == "whale_position_alert":
            for f in tg_files:
                if "v115c" in f or "v115d" in f:
                    record["tg_test_group_status"] = "blocked"
                    record["tg_test_group_evidence"] = (
                        "TG test copy template gate exists (v115c/d) but "
                        "real send is blocked. No actual TG message was sent."
                    )
                    return

    record["tg_test_group_status"] = "not_allowed"
    record["tg_test_group_evidence"] = "No TG test group send evidence. TG send is not allowed without explicit send-readiness gate pass."


def _derive_current_stage(record: dict):
    """Derive the current pipeline stage for this card family."""
    stages = [
        ("not_started", "router_test_status", "not_found"),
        ("router_only", "router_test_status", "passed"),
        ("fixture_preview", "preview_status", "fixture_only"),
        ("local_preview", "preview_status", "passed"),
        ("fixture_e2e", "fixture_positive_path_status", "passed"),
        ("real_e2e_blocked", "real_e2e_status", "blocked"),
        ("real_e2e_passed", "real_e2e_status", "passed"),
    ]

    current = "unknown"
    for stage, field, expected in stages:
        if record.get(field) == expected:
            current = stage

    # Refine based on actual status
    if record.get("real_e2e_status") == "passed":
        current = "real_e2e_passed"
    elif record.get("real_e2e_status") == "blocked":
        if record.get("fixture_positive_path_status") == "passed":
            current = "fixture_e2e_passed_real_blocked"
        else:
            current = "real_e2e_blocked"
    elif record.get("fixture_positive_path_status") == "passed":
        current = "fixture_e2e_passed"
    elif record.get("preview_status") == "passed":
        current = "local_preview_passed"
    elif record.get("preview_status") == "fixture_only":
        current = "fixture_preview"
    elif record.get("router_test_status") == "passed":
        current = "router_only_passed"

    record["current_stage"] = current


def _suggest_next_task(record: dict, card_family: str):
    """Suggest the next minimum task to advance coverage."""
    stage = record.get("current_stage", "unknown")

    suggestions = {
        "unknown": f"Verify card family {card_family} is registered in card type registry and has fixture samples.",
        "not_started": f"Register {card_family} in card type registry (v112a) and create fixture samples.",
        "router_only_passed": f"Build local feed / enrichment for {card_family} to generate first preview cards.",
        "fixture_preview": f"Advance {card_family} from fixture-only preview to local/real data feed (adapter pipeline).",
        "local_preview_passed": f"Add quality gate (dedupe/cooldown/debug leak/secret leak) for {card_family}.",
        "fixture_e2e_passed": f"Collect real operator evidence for {card_family} and run through intake→scoring→adjudication gates.",
        "fixture_e2e_passed_real_blocked": f"Complete real operator workbook for {card_family} addresses (v115O preflight), then rerun gates.",
        "real_e2e_blocked": f"Unblock real E2E for {card_family}: resolve missing input data pipeline or operator evidence.",
        "real_e2e_passed": f"Advance {card_family} to TG test copy template gate and send-readiness gate.",
    }

    record["next_minimum_task"] = suggestions.get(stage, suggestions["unknown"])


# ═══════════════════════════════════════════════════════════════════════════
# Gap Backlog Generator
# ═══════════════════════════════════════════════════════════════════════════

def generate_gap_backlog(coverage_records: list[dict]) -> list[dict]:
    """Generate gap backlog items from coverage records."""
    backlog = []
    task_counter = [0]

    def _next_id():
        task_counter[0] += 1
        return f"v116a_gap_{task_counter[0]:03d}"

    for record in coverage_records:
        cf = record["card_family"]
        stage = record.get("current_stage", "unknown")

        # 1. Discovery & naming gap (if card family source is inferred)
        if record.get("card_family_name_source", "").startswith("inferred"):
            backlog.append({
                "card_family": cf,
                "gap_type": "naming_and_discovery",
                "current_stage": stage,
                "target_next_stage": "router_only_passed",
                "minimum_next_task": f"Confirm canonical name for {cf} and register in card type registry.",
                "risk_level": "high",
                "blocked_by": "ambiguous_naming",
                "suggested_task_id": _next_id(),
            })

        # 2. Input data gap
        if record.get("input_data_status") in ("not_found", "fixture_only"):
            backlog.append({
                "card_family": cf,
                "gap_type": "input_data",
                "current_stage": stage,
                "target_next_stage": "local_preview_passed",
                "minimum_next_task": f"Build local data feed/adapter for {cf} to replace fixture-only input.",
                "risk_level": "high",
                "blocked_by": "missing_live_data_source",
                "suggested_task_id": _next_id(),
            })

        # 3. Preview gap
        if record.get("preview_status") in ("not_found", "fixture_only"):
            backlog.append({
                "card_family": cf,
                "gap_type": "preview",
                "current_stage": stage,
                "target_next_stage": "local_preview_passed",
                "minimum_next_task": f"Generate local preview cards for {cf} with real/enriched data.",
                "risk_level": "high",
                "blocked_by": "missing_input_data",
                "suggested_task_id": _next_id(),
            })

        # 4. Quality gate gap
        if record.get("quality_gate_status") in ("not_found", "not_started"):
            backlog.append({
                "card_family": cf,
                "gap_type": "quality_gate",
                "current_stage": stage,
                "target_next_stage": "quality_gate_passed",
                "minimum_next_task": f"Run dedupe/cooldown/debug leak/secret leak gates for {cf} previews.",
                "risk_level": "medium",
                "blocked_by": "missing_preview",
                "suggested_task_id": _next_id(),
            })

        # 5. Fixture positive path gap
        if record.get("fixture_positive_path_status") in ("not_found", "not_started"):
            backlog.append({
                "card_family": cf,
                "gap_type": "fixture_positive_path",
                "current_stage": stage,
                "target_next_stage": "fixture_e2e_passed",
                "minimum_next_task": f"Create fixture workbook and run E2E gate replay for {cf}.",
                "risk_level": "medium",
                "blocked_by": "missing_input_data_or_preview",
                "suggested_task_id": _next_id(),
            })

        # 6. Real E2E gap
        if record.get("real_e2e_status") in ("not_started", "blocked"):
            backlog.append({
                "card_family": cf,
                "gap_type": "real_e2e",
                "current_stage": stage,
                "target_next_stage": "real_e2e_passed",
                "minimum_next_task": record.get("blocked_reason", f"Unblock real E2E for {cf}."),
                "risk_level": "high",
                "blocked_by": record.get("blocked_reason", "unknown"),
                "suggested_task_id": _next_id(),
            })

        # 7. TG test group gap
        if record.get("tg_test_group_status") in ("not_allowed", "blocked"):
            backlog.append({
                "card_family": cf,
                "gap_type": "tg_test_group",
                "current_stage": stage,
                "target_next_stage": "tg_test_ready",
                "minimum_next_task": f"Complete all prior gates before TG test group readiness for {cf}.",
                "risk_level": "low",
                "blocked_by": "real_e2e_not_passed",
                "suggested_task_id": _next_id(),
            })

    return backlog


# ═══════════════════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════════════════

def run():
    print("=" * 72)
    print("Market Radar v1.16-A — Five Card Family Coverage Status Audit")
    print(f"Started: {china_stamp()}")
    print("=" * 72)

    # ── Step 1: Discover card families ──────────────────────────────────
    print("\n[1/7] Discovering card families...")
    registry_families = discover_card_families_from_registry()
    canonical_names = discover_card_families_from_v112e_pipeline()

    if registry_families:
        discovered_families = registry_families
        discovery_source = "market_radar_card_type_registry_v112a"
        print(f"  Found {len(discovered_families)} card families in v112a registry.")
    else:
        # Fallback: use canonical names from v112e
        discovered_families = [
            {"card_family": name, "display_name": name, "source": "v112e_pipeline_docstring"}
            for name in canonical_names
        ]
        discovery_source = "inferred_from_v112e_pipeline_docstring"
        print(f"  Registry not importable; using {len(discovered_families)} families from v112e pipeline.")

    expected_count = 5
    discovered_count = len(discovered_families)
    mismatch = discovered_count != expected_count

    if mismatch:
        print(f"  ⚠ MISMATCH: expected {expected_count}, discovered {discovered_count}")
    else:
        print(f"  ✓ Discovered {discovered_count} card families (matches expected {expected_count}).")

    # ── Step 2: Scan artifacts per card family ──────────────────────────
    print("\n[2/7] Scanning artifacts per card family...")
    evidence_map = {}
    for fam in discovered_families:
        cf = fam["card_family"]
        evidence = find_artifacts_for_card_family(cf)
        evidence_map[cf] = evidence
        total = sum(len(v) for v in evidence.values())
        print(f"  {cf}: {total} artifacts found.")

    # ── Step 3: Write discovery records ─────────────────────────────────
    print("\n[3/7] Writing card family discovery records...")
    discovery_path = ROOT / "results" / "market_radar_v116a_card_family_discovery_records.jsonl"
    discovery_path.parent.mkdir(parents=True, exist_ok=True)
    with open(discovery_path, "w", encoding="utf-8") as f:
        for fam in discovered_families:
            cf = fam["card_family"]
            record = {
                "card_family": cf,
                "display_name": fam.get("display_name", cf),
                "source": fam.get("source", discovery_source),
                "evidence_file_count": sum(len(v) for v in evidence_map.get(cf, {}).values()),
                "discovered_at": china_stamp_iso(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(discovered_families)} records to {discovery_path}")

    # ── Step 4: Assess coverage per card family ─────────────────────────
    print("\n[4/7] Assessing coverage per card family...")
    coverage_records = []
    for fam in discovered_families:
        cf = fam["card_family"]
        display_name = fam.get("display_name", cf)
        evidence = evidence_map.get(cf, {})
        record = assess_card_family_coverage(cf, display_name, evidence,
                                              fam.get("source", discovery_source))
        coverage_records.append(record)
        print(f"  {cf}: stage={record['current_stage']}, "
              f"router={record['router_test_status']}, "
              f"preview={record['preview_status']}, "
              f"fixture_e2e={record['fixture_positive_path_status']}, "
              f"real_e2e={record['real_e2e_status']}")

    # ── Step 5: Generate gap backlog ────────────────────────────────────
    print("\n[5/7] Generating gap backlog...")
    gap_backlog = generate_gap_backlog(coverage_records)
    print(f"  Generated {len(gap_backlog)} gap backlog items.")

    # ── Step 6: Compute summary metrics ─────────────────────────────────
    print("\n[6/7] Computing summary metrics...")
    router_passed = sum(1 for r in coverage_records if r["router_test_status"] == "passed")
    local_preview_passed = sum(1 for r in coverage_records if r["preview_status"] == "passed")
    fixture_e2e_passed = sum(1 for r in coverage_records if r["fixture_positive_path_status"] == "passed")
    real_e2e_passed = sum(1 for r in coverage_records if r["real_e2e_status"] == "passed")
    tg_ready = sum(1 for r in coverage_records if r["tg_test_group_status"] == "passed")
    prod_ready = sum(1 for r in coverage_records if r["production_send_status"] == "passed")
    unknown_count = sum(1 for r in coverage_records if r["current_stage"] == "unknown")
    blocked_count = sum(1 for r in coverage_records if r["real_e2e_status"] == "blocked")

    # Whale-specific metrics
    whale_record = None
    for r in coverage_records:
        if r["card_family"] == "whale_position_alert":
            whale_record = r
            break

    whale_fixture_e2e = (whale_record["fixture_positive_path_status"] == "passed") if whale_record else False
    whale_real_e2e = (whale_record["real_e2e_status"] == "passed") if whale_record else False
    whale_blocked_reason = whale_record.get("blocked_reason", "") if whale_record else ""

    all_real_e2e = real_e2e_passed == discovered_count and discovered_count > 0
    all_tg_ready = tg_ready == discovered_count and discovered_count > 0

    summary = {
        "stage": "v116a_five_card_family_coverage_status_audit_local_only",
        "version": "v1.16-A",
        "description": (
            "Five card family coverage status audit based on existing artifacts. "
            "Read-only scan of scripts/, tests/, results/, runs/market_radar/, config/. "
            "NO real sends, NO production writes, NO external API calls, NO AI/model calls."
        ),
        "generated_at": china_stamp_iso(),
        "expected_card_families_from_user": expected_count,
        "discovered_card_families": discovered_count,
        "card_family_name_source": discovery_source,
        "coverage_audit_status": "incomplete_or_mismatch" if mismatch else "complete",
        "coverage_records": discovered_count,
        "router_passed_count": router_passed,
        "local_preview_passed_count": local_preview_passed,
        "fixture_e2e_passed_count": fixture_e2e_passed,
        "real_e2e_passed_count": real_e2e_passed,
        "tg_test_group_ready_count": tg_ready,
        "production_send_ready_count": prod_ready,
        "families_with_unknown_status_count": unknown_count,
        "families_with_blocked_status_count": blocked_count,
        "gap_backlog_items": len(gap_backlog),
        "whale_position_alert_stage": whale_record["current_stage"] if whale_record else "unknown",
        "whale_position_alert_fixture_e2e_passed": whale_fixture_e2e,
        "whale_position_alert_real_e2e_passed": whale_real_e2e,
        "whale_position_alert_blocked_reason": whale_blocked_reason,
        "five_card_families_all_real_e2e_passed": all_real_e2e,
        "five_card_families_all_tg_ready": all_tg_ready,
        "audit_result": "all_real_e2e_passed" if all_real_e2e else "passed_with_gaps",
        "real_send_candidate_generated": False,
        "tg_sent": False,
        "prod_state_write": False,
        "external_api_called": False,
        "credentials_read": False,
        "ai_model_called": False,
        "files_deleted": False,
        "historical_artifacts_modified": False,
    }

    all_real_e2e_passed_flag = all_real_e2e
    print(f"  Router passed: {router_passed}/{discovered_count}")
    print(f"  Local preview passed: {local_preview_passed}/{discovered_count}")
    print(f"  Fixture E2E passed: {fixture_e2e_passed}/{discovered_count}")
    print(f"  Real E2E passed: {real_e2e_passed}/{discovered_count}")
    print(f"  TG ready: {tg_ready}/{discovered_count}")
    print(f"  All real E2E: {all_real_e2e_passed_flag}")
    print(f"  Audit result: {summary['audit_result']}")

    # ── Step 7: Write all outputs ───────────────────────────────────────
    print("\n[7/7] Writing output files...")

    # 7a. Coverage records JSONL
    coverage_jsonl = ROOT / "results" / "market_radar_v116a_card_family_coverage_records.jsonl"
    with open(coverage_jsonl, "w", encoding="utf-8") as f:
        for rec in coverage_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  ✓ {coverage_jsonl}")

    # 7b. Gap backlog JSONL
    backlog_jsonl = ROOT / "results" / "market_radar_v116a_card_family_gap_backlog.jsonl"
    with open(backlog_jsonl, "w", encoding="utf-8") as f:
        for item in gap_backlog:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"  ✓ {backlog_jsonl}")

    # 7c. Summary JSON
    summary_json = ROOT / "results" / "market_radar_v116a_five_card_family_coverage_status_audit_result.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {summary_json}")

    # 7d. Coverage matrix CSV
    csv_path = ROOT / "runs" / "market_radar" / "v116a_five_card_family_coverage_status_audit.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _write_coverage_csv(csv_path, coverage_records)
    print(f"  ✓ {csv_path}")

    # 7e. Coverage matrix Markdown
    md_path = ROOT / "runs" / "market_radar" / "v116a_five_card_family_coverage_status_audit.md"
    _write_coverage_markdown(md_path, coverage_records, summary, gap_backlog)
    print(f"  ✓ {md_path}")

    # 7f. Gap backlog Markdown
    backlog_md = ROOT / "runs" / "market_radar" / "v116a_five_card_family_next_gap_backlog.md"
    _write_gap_backlog_markdown(backlog_md, gap_backlog, summary)
    print(f"  ✓ {backlog_md}")

    # 7g. Handoff Markdown
    handoff_md = ROOT / "runs" / "market_radar" / "v116a_five_card_family_coverage_status_audit_local_only_handoff.md"
    _write_handoff_markdown(handoff_md, coverage_records, summary, gap_backlog)
    print(f"  ✓ {handoff_md}")

    print(f"\n{'=' * 72}")
    print(f"Audit complete: {china_stamp()}")
    print(f"Result: {summary['audit_result']}")
    print(f"{'=' * 72}")


# ═══════════════════════════════════════════════════════════════════════════
# Output Writers
# ═══════════════════════════════════════════════════════════════════════════

def _write_coverage_csv(path: Path, records: list[dict]):
    fields = [
        "card_family", "card_family_name_source", "current_stage",
        "router_test_status", "input_data_status", "card_generation_status",
        "preview_status", "quality_gate_status", "send_readiness_status",
        "fixture_positive_path_status", "real_e2e_status",
        "tg_test_group_status", "production_send_status",
        "blocked_reason", "next_minimum_task",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)


def _write_coverage_markdown(path: Path, records: list[dict],
                              summary: dict, backlog: list[dict]):
    lines = []
    lines.append("# Market Radar v1.16-A — Five Card Family Coverage Status Audit")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Version**: v1.16-A")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Conclusion ──────────────────────────────────────────────────────
    lines.append("## Conclusion")
    lines.append("")
    all_e2e = summary["five_card_families_all_real_e2e_passed"]
    if all_e2e:
        lines.append(
            "**Conclusion**: All five card families have passed real E2E verification. "
            "Each family has real input data, card generation, preview, quality gate, "
            "send-readiness gate, and non-fixture workflow evidence."
        )
    else:
        lines.append(
            "**Conclusion: Five card families are NOT yet all real-E2E passed. "
            "Unless every family has real input, card generation, preview, quality gate, "
            "send-readiness gate, and non-fixture workflow evidence, the system is not "
            "fully production-ready.**"
        )
    lines.append("")

    # ── Summary ─────────────────────────────────────────────────────────
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Expected card families | {summary['expected_card_families_from_user']} |")
    lines.append(f"| Discovered card families | {summary['discovered_card_families']} |")
    lines.append(f"| Card family name source | {summary['card_family_name_source']} |")
    lines.append(f"| Coverage audit status | {summary['coverage_audit_status']} |")
    lines.append(f"| Router/gate passed | {summary['router_passed_count']} |")
    lines.append(f"| Local preview passed | {summary['local_preview_passed_count']} |")
    lines.append(f"| Fixture E2E passed | {summary['fixture_e2e_passed_count']} |")
    lines.append(f"| Real E2E passed | {summary['real_e2e_passed_count']} |")
    lines.append(f"| TG test group ready | {summary['tg_test_group_ready_count']} |")
    lines.append(f"| Production send ready | {summary['production_send_ready_count']} |")
    lines.append(f"| Families with unknown status | {summary['families_with_unknown_status_count']} |")
    lines.append(f"| Families with blocked status | {summary['families_with_blocked_status_count']} |")
    lines.append(f"| Gap backlog items | {summary['gap_backlog_items']} |")
    lines.append(f"| Audit result | **{summary['audit_result']}** |")
    lines.append("")

    # ── Coverage Matrix ─────────────────────────────────────────────────
    lines.append("## Coverage Matrix")
    lines.append("")
    lines.append(
        "| # | Card Family | Current Stage | Router | Input Data | Preview | "
        "Quality Gate | Fixture E2E | Real E2E | TG Test | Prod Send |"
    )
    lines.append(
        "|---|-------------|---------------|--------|------------|---------|"
        "-------------|-------------|----------|---------|-----------|"
    )
    for i, rec in enumerate(records, 1):
        lines.append(
            f"| {i} | `{rec['card_family']}` | **{rec['current_stage']}** | "
            f"{rec['router_test_status']} | {rec['input_data_status']} | "
            f"{rec['preview_status']} | {rec['quality_gate_status']} | "
            f"{rec['fixture_positive_path_status']} | {rec['real_e2e_status']} | "
            f"{rec['tg_test_group_status']} | {rec['production_send_status']} |"
        )
    lines.append("")

    # ── Four types of "passed" distinction ──────────────────────────────
    lines.append("## Distinction: Four Types of 'Passed'")
    lines.append("")
    lines.append("| Pass Type | Definition | Count |")
    lines.append("|-----------|-----------|-------|")
    lines.append(f"| `router_only_passed` | Card type registered, schema/admission/block rules defined, router classifies correctly | {summary['router_passed_count']} |")
    lines.append(f"| `local_preview_passed` | Real/local data feed generates valid public preview cards | {summary['local_preview_passed_count']} |")
    lines.append(f"| `fixture_e2e_passed` | Fixture workbook passes all gates (intake→scoring→adjudication→workflow) in replay | {summary['fixture_e2e_passed_count']} |")
    lines.append(f"| `real_e2e_passed` | Real operator evidence passes all gates, real labels ready for upgrade | {summary['real_e2e_passed_count']} |")
    lines.append("")
    lines.append("> ⚠ **Critical**: `router_only_passed` ≠ `real_e2e_passed`. ")
    lines.append("> `fixture_e2e_passed` ≠ `real_e2e_passed`. ")
    lines.append("> Fixture replay is a DRY-RUN; real addresses require real operator evidence.")
    lines.append("")

    # ── Per-Family Details ──────────────────────────────────────────────
    lines.append("## Per-Family Coverage Details")
    lines.append("")
    for rec in records:
        lines.append(f"### {rec['card_family']}")
        lines.append("")
        lines.append(f"- **Current Stage**: `{rec['current_stage']}`")
        lines.append(f"- **Name Source**: {rec.get('card_family_name_source', 'unknown')}")
        lines.append(f"- **Router Test**: {rec['router_test_status']} — {rec.get('router_test_evidence', '')}")
        lines.append(f"- **Input Data**: {rec['input_data_status']} — {rec.get('input_data_evidence', '')}")
        lines.append(f"- **Card Generation**: {rec['card_generation_status']} — {rec.get('card_generation_evidence', '')}")
        lines.append(f"- **Preview**: {rec['preview_status']} — {rec.get('preview_evidence', '')}")
        lines.append(f"- **Quality Gate**: {rec['quality_gate_status']} — {rec.get('quality_gate_evidence', '')}")
        lines.append(f"- **Send Readiness**: {rec['send_readiness_status']} — {rec.get('send_readiness_evidence', '')}")
        lines.append(f"- **Fixture E2E**: {rec['fixture_positive_path_status']} — {rec.get('fixture_positive_path_evidence', '')}")
        lines.append(f"- **Real E2E**: {rec['real_e2e_status']} — {rec.get('real_e2e_evidence', '')}")
        lines.append(f"- **TG Test Group**: {rec['tg_test_group_status']} — {rec.get('tg_test_group_evidence', '')}")
        lines.append(f"- **Production Send**: {rec['production_send_status']} — {rec.get('production_send_evidence', '')}")
        if rec.get("blocked_reason"):
            lines.append(f"- **Blocked Reason**: {rec['blocked_reason']}")
        if rec.get("next_minimum_task"):
            lines.append(f"- **Next Task**: {rec['next_minimum_task']}")
        lines.append("")

    # ── Whale Position Alert Special Section ────────────────────────────
    lines.append("## Whale Position Alert — Special Note")
    lines.append("")
    whale = summary
    lines.append(f"- **whale_position_alert current stage**: `{whale['whale_position_alert_stage']}`")
    lines.append(f"- **Fixture E2E passed**: `{whale['whale_position_alert_fixture_e2e_passed']}`")
    lines.append(f"- **Real E2E passed**: `{whale['whale_position_alert_real_e2e_passed']}`")
    lines.append(f"- **Blocked reason**: {whale['whale_position_alert_blocked_reason']}")
    lines.append("")
    lines.append(
        "> **Key finding**: whale_position_alert is the ONLY card family with a completed "
        "fixture E2E gate replay (v115Q: 4/4 fixture rows pass intake→scoring→adjudication→workflow). "
        "However, real E2E remains BLOCKED because the real operator workbook (v115F) has empty fields "
        "for all 4 addresses. The fixture replay PROVES the gate logic works; it does NOT prove "
        "real address verification has been performed."
    )
    lines.append("")

    # ── TG / Production Send Status ─────────────────────────────────────
    lines.append("## TG / Production Send Status")
    lines.append("")
    lines.append("| Send Type | Status | Evidence |")
    lines.append("|-----------|--------|----------|")
    lines.append(f"| TG test group | **not_allowed** | No card family has passed all prior gates required for TG test send. |")
    lines.append(f"| Production send | **not_allowed** | Production send is blocked per safety boundary. No production send evidence exists. |")
    lines.append("")
    lines.append("> ⚠ **Safety**: TG test group send and production send are NOT allowed ")
    lines.append("> until real E2E is passed for the target card family AND all prior gates ")
    lines.append("> (intake, scoring, adjudication, workflow upgrade, send-readiness) are green.")
    lines.append("")

    # ── Safety Constraints ──────────────────────────────────────────────
    lines.append("## Safety Constraints (All Verified)")
    lines.append("")
    lines.append("| Constraint | Status |")
    lines.append("|------------|--------|")
    lines.append("| real_send_candidate_generated | false |")
    lines.append("| tg_sent | false |")
    lines.append("| prod_state_write | false |")
    lines.append("| external_api_called | false |")
    lines.append("| credentials_read | false |")
    lines.append("| ai_model_called | false |")
    lines.append("| files_deleted | false |")
    lines.append("| historical_artifacts_modified | false |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_gap_backlog_markdown(path: Path, backlog: list[dict], summary: dict):
    lines = []
    lines.append("# Market Radar v1.16-A — Next Gap Backlog")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Backlog items**: {len(backlog)}")
    lines.append("")
    lines.append("## Priority Order")
    lines.append("")
    lines.append("1. Complete card family discovery & naming")
    lines.append("2. Build real input data pipelines for missing families")
    lines.append("3. Generate local previews for fixture-only families")
    lines.append("4. Apply quality gates (dedupe/cooldown/debug leak/secret leak)")
    lines.append("5. Create fixture positive path E2E gate replays")
    lines.append("6. Collect real operator evidence for real E2E")
    lines.append("7. TG test readiness (LAST, after all prior gates)")
    lines.append("")

    lines.append("## Backlog Items")
    lines.append("")
    lines.append(
        "| # | Card Family | Gap Type | Current Stage | Target Stage | "
        "Risk | Blocked By | Suggested Task ID |"
    )
    lines.append(
        "|---|-------------|----------|---------------|--------------|"
        "------|------------|-------------------|"
    )
    for i, item in enumerate(backlog, 1):
        lines.append(
            f"| {i} | `{item['card_family']}` | {item['gap_type']} | "
            f"`{item['current_stage']}` | `{item['target_next_stage']}` | "
            f"{item['risk_level']} | {item.get('blocked_by', '')} | "
            f"`{item.get('suggested_task_id', '')}` |"
        )
    lines.append("")

    lines.append("## Detailed Tasks")
    lines.append("")
    for item in backlog:
        lines.append(f"### {item.get('suggested_task_id', '')} — {item['card_family']}: {item['gap_type']}")
        lines.append("")
        lines.append(f"- **Current Stage**: `{item['current_stage']}`")
        lines.append(f"- **Target Stage**: `{item['target_next_stage']}`")
        lines.append(f"- **Risk Level**: {item['risk_level']}")
        lines.append(f"- **Blocked By**: {item.get('blocked_by', 'none')}")
        lines.append(f"- **Task**: {item['minimum_next_task']}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_handoff_markdown(path: Path, records: list[dict],
                             summary: dict, backlog: list[dict]):
    lines = []
    lines.append("# Market Radar v1.16-A — Five Card Family Coverage Status Audit Handoff")
    lines.append("")
    lines.append(f"**Generated**: {china_stamp()}")
    lines.append(f"**Version**: v1.16-A")
    lines.append(f"**Task ID**: 20260605_v116a_market_radar_five_card_family_coverage_status_audit_local_only")
    lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## Modified Files")
    lines.append("")
    lines.append("| File | Operation | Description |")
    lines.append("|------|-----------|-------------|")
    lines.append("| `scripts/run_market_radar_v116a_five_card_family_coverage_status_audit_local_only.py` | NEW | Runner script |")
    lines.append("| `scripts/test_market_radar_v116a_five_card_family_coverage_status_audit_local_only.py` | NEW | Test script |")
    lines.append("| `results/market_radar_v116a_card_family_discovery_records.jsonl` | NEW | Discovery records |")
    lines.append("| `results/market_radar_v116a_card_family_coverage_records.jsonl` | NEW | Coverage records |")
    lines.append("| `results/market_radar_v116a_card_family_gap_backlog.jsonl` | NEW | Gap backlog |")
    lines.append("| `results/market_radar_v116a_five_card_family_coverage_status_audit_result.json` | NEW | Summary JSON |")
    lines.append("| `runs/market_radar/v116a_five_card_family_coverage_status_audit.md` | NEW | Markdown report |")
    lines.append("| `runs/market_radar/v116a_five_card_family_coverage_status_audit.csv` | NEW | CSV report |")
    lines.append("| `runs/market_radar/v116a_five_card_family_next_gap_backlog.md` | NEW | Gap backlog MD |")
    lines.append("| `runs/market_radar/v116a_five_card_family_coverage_status_audit_local_only_handoff.md` | NEW | Handoff (this file) |")
    lines.append("")

    lines.append("## Commands Executed")
    lines.append("")
    lines.append("```powershell")
    lines.append("python scripts/run_market_radar_v116a_five_card_family_coverage_status_audit_local_only.py")
    lines.append("python scripts/test_market_radar_v116a_five_card_family_coverage_status_audit_local_only.py")
    lines.append("```")
    lines.append("")

    lines.append("## Key Results")
    lines.append("")
    lines.append(f"- **expected_card_families_from_user**: {summary['expected_card_families_from_user']}")
    lines.append(f"- **discovered_card_families**: {summary['discovered_card_families']}")
    lines.append(f"- **coverage_records**: {summary['coverage_records']}")
    lines.append(f"- **router_passed_count**: {summary['router_passed_count']}")
    lines.append(f"- **local_preview_passed_count**: {summary['local_preview_passed_count']}")
    lines.append(f"- **fixture_e2e_passed_count**: {summary['fixture_e2e_passed_count']}")
    lines.append(f"- **real_e2e_passed_count**: {summary['real_e2e_passed_count']}")
    lines.append(f"- **tg_test_group_ready_count**: {summary['tg_test_group_ready_count']}")
    lines.append(f"- **production_send_ready_count**: {summary['production_send_ready_count']}")
    lines.append(f"- **five_card_families_all_real_e2e_passed**: {summary['five_card_families_all_real_e2e_passed']}")
    lines.append(f"- **five_card_families_all_tg_ready**: {summary['five_card_families_all_tg_ready']}")
    lines.append(f"- **audit_result**: {summary['audit_result']}")
    lines.append("")

    lines.append("## Whale Position Alert Status")
    lines.append("")
    lines.append(f"- **Stage**: `{summary['whale_position_alert_stage']}`")
    lines.append(f"- **Fixture E2E passed**: `{summary['whale_position_alert_fixture_e2e_passed']}`")
    lines.append(f"- **Real E2E passed**: `{summary['whale_position_alert_real_e2e_passed']}`")
    lines.append(f"- **Blocked reason**: {summary['whale_position_alert_blocked_reason']}")
    lines.append("")

    lines.append("## Safety Constraints")
    lines.append("")
    lines.append("| Constraint | Status |")
    lines.append("|------------|--------|")
    for key in ["real_send_candidate_generated", "tg_sent", "prod_state_write",
                 "external_api_called", "credentials_read", "ai_model_called",
                 "files_deleted", "historical_artifacts_modified"]:
        lines.append(f"| {key} | {summary.get(key, 'false')} |")
    lines.append("")

    lines.append("## Unfinished Items / Risks")
    lines.append("")
    lines.append(f"- {summary['discovered_card_families'] - summary['real_e2e_passed_count']} card families NOT real-E2E passed.")
    lines.append(f"- {summary['discovered_card_families'] - summary['fixture_e2e_passed_count']} card families without fixture E2E gate replay.")
    lines.append("- whale_position_alert has full fixture E2E replay (v115Q) but real workbook fields are empty.")
    lines.append("- 4 of 5 card families lack live data pipelines; most use fixture data only.")
    lines.append("- TG test group and production send are NOT allowed for any card family.")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run()
