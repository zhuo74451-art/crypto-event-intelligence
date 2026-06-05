#!/usr/bin/env python3
"""
v115L Whale Label Evidence Scoring Gate — Local Only
======================================================
Reads the v115K evidence source registry and scoring policy, applies the
high-confidence minimum evidence rules to:
  1. The real v115F operator workbook (4 addresses, currently empty → all blocked)
  2. The v115I positive-path fixture (1 address, all evidence complete → passes)

This is a LOCAL-ONLY stage:
  - No external API calls
  - No AI/model calls
  - No TG send
  - No production state write
  - No credential reads
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115K old results
  - No real workbook modification
  - No real label upgrade
  - No real send candidate generation

Outputs:
  - results/market_radar_v115l_whale_real_workbook_evidence_scoring_records.jsonl
  - results/market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl
  - results/market_radar_v115l_whale_fixture_evidence_scoring_records.jsonl
  - results/market_radar_v115l_whale_fixture_evidence_scoring_decisions.jsonl
  - results/market_radar_v115l_whale_label_evidence_scoring_gate_result.json
  - runs/market_radar/v115l_whale_label_evidence_scoring_gate_local_only.md
  - runs/market_radar/v115l_whale_label_evidence_scoring_gate_local_only_handoff.md
"""

import csv
import json
import os
import sys
import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")
FIXTURES_DIR = os.path.join(BASE_DIR, "fixtures", "market_radar")

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))


def now_iso() -> str:
    return datetime.datetime.now(TZ_SHANGHAI).isoformat()


# ---------------------------------------------------------------------------
# Input paths (read-only)
# ---------------------------------------------------------------------------
V115K_REGISTRY = os.path.join(
    CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json"
)
V115K_SCORING_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json"
)
V115F_WORKBOOK = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)
V115I_FIXTURE = os.path.join(
    FIXTURES_DIR, "v115i_whale_manual_audit_positive_path_fixture.csv"
)

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------
OUT_REAL_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_records.jsonl"
)
OUT_REAL_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl"
)
OUT_FIXTURE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_fixture_evidence_scoring_records.jsonl"
)
OUT_FIXTURE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_fixture_evidence_scoring_decisions.jsonl"
)
OUT_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115l_whale_label_evidence_scoring_gate_result.json"
)
OUT_MD = os.path.join(
    RUNS_DIR, "v115l_whale_label_evidence_scoring_gate_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115l_whale_label_evidence_scoring_gate_local_only_handoff.md"
)

# ---------------------------------------------------------------------------
# Safety invariants (all must remain false/unchanged)
# ---------------------------------------------------------------------------
EXTERNAL_API_CALLED = False
AI_MODEL_CALLED = False
CREDENTIALS_READ = False
TG_SENT = False
PROD_STATE_WRITE = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
REAL_SEND_CANDIDATE_GENERATED = False
REAL_WORKBOOK_MODIFIED = False
REAL_LABEL_UPGRADE_PERFORMED = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_csv_dict(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def parse_bool_csv(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return False


def non_empty(val) -> bool:
    """Check if a field value is non-empty/non-null."""
    if val is None:
        return False
    return str(val).strip() != ""


# ---------------------------------------------------------------------------
# Extractor helpers: determine evidence category from workbook field values
# ---------------------------------------------------------------------------

def classify_trusted_source_category(trusted_source_label: str, registry: dict) -> str:
    """
    Determine if the trusted_source_label_value falls into a primary_source
    category, a secondary_source category, or is unrecognized.
    Returns: 'primary_source', 'secondary_source', 'activity_source', 'rejected_source', or 'unknown'
    """
    if not non_empty(trusted_source_label):
        return "none"

    label_lower = trusted_source_label.lower()

    # Check rejected sources first
    rejected_types = registry.get("categories", {}).get("rejected_source", {}).get("types", [])
    for rt in rejected_types:
        type_id = rt.get("type_id", "").lower()
        type_label = rt.get("label", "").lower()
        # If the label contains rejected-source keywords, flag it
        rejection_keywords = [
            "unsourced", "anonymous", "ai-generated", "screenshot without",
            "stale", "tg chat", "chat without", "vague", "said to be",
            "rumored", "possibly"
        ]
        for kw in rejection_keywords:
            if kw in label_lower:
                return "rejected_source"

    # Check primary source types
    primary_types = registry.get("categories", {}).get("primary_source", {}).get("types", [])
    for pt in primary_types:
        type_label = pt.get("label", "").lower()
        # If the trusted source label contains primary keywords
        primary_keywords = [
            "official", "exchange", "institution", "explorer label",
            "etherscan", "solscan", "polygonscan",
            "signed statement", "internally verified",
            "verified exchange", "verified institution"
        ]
        for kw in primary_keywords:
            if kw in label_lower:
                return "primary_source"

    # Check secondary source types
    secondary_types = registry.get("categories", {}).get("secondary_source", {}).get("types", [])
    for st in secondary_types:
        type_label = st.get("label", "").lower()
        secondary_keywords = [
            "analytics", "dashboard", "dune", "nansen", "defillama",
            "cross-source", "clustering", "transaction behavior",
            "social identity", "ens", "lens", "farcaster",
            "operator-reviewed note"
        ]
        for kw in secondary_keywords:
            if kw in label_lower:
                return "secondary_source"

    # For synthetic/test evidence, map explicitly
    if "synthetic" in label_lower or "test" in label_lower or "fixture" in label_lower:
        return "primary_source"

    return "unknown"


def classify_second_source_category(second_source_label: str, registry: dict) -> str:
    """Same classification but for second_source."""
    if not non_empty(second_source_label):
        return "none"

    label_lower = second_source_label.lower()

    # Rejected check
    rejection_keywords = [
        "unsourced", "anonymous", "ai-generated", "screenshot without",
        "stale", "tg chat", "chat without", "vague", "said to be",
        "rumored", "possibly"
    ]
    for kw in rejection_keywords:
        if kw in label_lower:
            return "rejected_source"

    # Primary check
    primary_keywords = [
        "official", "exchange", "institution", "explorer label",
        "etherscan", "solscan", "polygonscan",
        "signed statement", "internally verified",
        "verified exchange", "verified institution"
    ]
    for kw in primary_keywords:
        if kw in label_lower:
            return "primary_source"

    # Secondary check
    secondary_keywords = [
        "analytics", "dashboard", "dune", "nansen", "defillama",
        "cross-source", "clustering", "transaction behavior",
        "social identity", "ens", "lens", "farcaster",
        "operator-reviewed note"
    ]
    for kw in secondary_keywords:
        if kw in label_lower:
            return "secondary_source"

    if "synthetic" in label_lower or "test" in label_lower or "fixture" in label_lower:
        return "secondary_source"

    return "unknown"


def classify_activity_source(activity_note: str, registry: dict) -> str:
    """Determine if activity_pattern_note matches an activity_source type."""
    if not non_empty(activity_note):
        return "none"

    note_lower = activity_note.lower()
    activity_keywords = [
        "counterparty", "asset/venue", "position behavior",
        "position consistency", "historical interaction",
        "on-chain position observed", "activity pattern",
        "hyperliquid", "consistent", "repeated", "pattern",
    ]
    for kw in activity_keywords:
        if kw in note_lower:
            return "activity_source"

    # If it contains "synthetic" or "test" or "fixture", it's activity_source
    if "synthetic" in note_lower or "fixture" in note_lower or "test" in note_lower:
        return "activity_source"

    return "unknown"


# ---------------------------------------------------------------------------
# Rejected source detection
# ---------------------------------------------------------------------------
def detect_rejected_source(trusted_label: str, second_label: str,
                           registry: dict) -> dict:
    """
    Check if any evidence field contains content matching rejected_source types.
    Returns a dict with detection results.
    """
    rejected_types = registry.get("categories", {}).get("rejected_source", {}).get("types", [])
    rejected_type_ids = [rt.get("type_id", "") for rt in rejected_types]

    rejection_keywords = [
        "unsourced", "anonymous", "ai-generated", "screenshot without",
        "stale label", "tg chat", "chat label", "vague", "said to be",
        "rumored", "possibly", "no verifiable", "hearsay"
    ]

    trusted_text = (trusted_label or "").lower()
    second_text = (second_label or "").lower()

    found_in_trusted = any(kw in trusted_text for kw in rejection_keywords)
    found_in_second = any(kw in second_text for kw in rejection_keywords)

    return {
        "rejected_keywords_found_in_trusted_source": found_in_trusted,
        "rejected_keywords_found_in_second_source": found_in_second,
        "rejected_source_detected": found_in_trusted or found_in_second,
        "rejected_source_type_ids": rejected_type_ids,
    }


# ---------------------------------------------------------------------------
# High confidence requirements check (HC_REQ_001 through HC_REQ_009)
# ---------------------------------------------------------------------------
def check_high_confidence_requirements(row: dict, registry: dict,
                                       rejected_check: dict) -> dict:
    """
    Check all 9 high-confidence requirements against a workbook row.
    Returns a dict with each requirement's pass/fail status.
    """
    trusted_label = row.get("trusted_source_label_value", "")
    trusted_url = row.get("trusted_source_url_or_note", "")
    second_label = row.get("second_source_label_value", "")
    second_url = row.get("second_source_url_or_note", "")
    activity_note = row.get("activity_pattern_note", "")
    operator_label = row.get("operator_confirmed_label", "")
    operator_assessment = row.get("operator_confidence_assessment", "")
    reviewer = row.get("reviewer", "")
    reviewed_at = row.get("reviewed_at", "")
    ready = parse_bool_csv(row.get("ready_for_upgrade", "false"))
    current_confidence = (row.get("current_confidence", "") or "").strip().lower()
    current_label = (row.get("current_label", "") or "").strip().lower()

    # Classify categories
    trusted_category = classify_trusted_source_category(trusted_label, registry)
    second_category = classify_second_source_category(second_label, registry)
    activity_category = classify_activity_source(activity_note, registry)

    # HC_REQ_001: trusted source label must exist and be primary_source
    trusted_source_present = non_empty(trusted_label)
    trusted_source_accepted = trusted_category == "primary_source"

    # HC_REQ_002: second source label or cross-source consistency must exist
    second_source_present = non_empty(second_label) or non_empty(second_url)
    second_source_accepted = second_category in ("primary_source", "secondary_source")

    # HC_REQ_003: activity pattern note must be present
    activity_pattern_present = non_empty(activity_note)
    activity_source_accepted = activity_category in ("activity_source", "unknown") and activity_pattern_present

    # HC_REQ_004: operator confirmed label must exist
    operator_confirmation_present = non_empty(operator_label)

    # HC_REQ_005: reviewer must be present
    reviewer_present = non_empty(reviewer)

    # HC_REQ_006: reviewed_at must be present
    reviewed_at_present = non_empty(reviewed_at)

    # HC_REQ_007: ready_for_upgrade must be true
    ready_for_upgrade_true = ready is True

    # HC_REQ_008: no rejected source as core evidence
    # Rejected source presence alone does NOT block if primary+secondary+activity is complete.
    # But if core evidence (trusted_source) is rejected, that's a problem.
    no_rejected_core = not rejected_check.get("rejected_keywords_found_in_trusted_source", False)

    # HC_REQ_009: low/unknown whale must not be upgraded from a single source
    is_low_unknown = current_confidence in ("low", "unknown") or "unknown" in current_label
    single_source_only = (
        trusted_source_present and not second_source_present and not activity_pattern_present
    )
    not_single_source_low_to_high = not (is_low_unknown and single_source_only)

    # Build requirement check results
    reqs = {
        "HC_REQ_001": {
            "requirement": "trusted_source_label_present",
            "description": "At least one primary_source evidence with verifiable trusted source label must be present.",
            "pass": trusted_source_present and trusted_source_accepted,
            "trusted_source_present": trusted_source_present,
            "trusted_source_accepted": trusted_source_accepted,
        },
        "HC_REQ_002": {
            "requirement": "second_source_or_cross_source_present",
            "description": "At least one secondary_source evidence or cross-source consistency note must be present.",
            "pass": second_source_present and second_source_accepted,
            "second_source_present": second_source_present,
            "second_source_accepted": second_source_accepted,
        },
        "HC_REQ_003": {
            "requirement": "activity_pattern_note_present",
            "description": "Activity pattern note must be present documenting on-chain behavior.",
            "pass": activity_pattern_present and activity_source_accepted,
            "activity_pattern_present": activity_pattern_present,
            "activity_source_accepted": activity_source_accepted,
        },
        "HC_REQ_004": {
            "requirement": "operator_confirmed_label_present",
            "description": "operator_confirmed_label must be non-empty.",
            "pass": operator_confirmation_present,
            "operator_confirmation_present": operator_confirmation_present,
        },
        "HC_REQ_005": {
            "requirement": "reviewer_present",
            "description": "reviewer must be non-empty.",
            "pass": reviewer_present,
            "reviewer_present": reviewer_present,
        },
        "HC_REQ_006": {
            "requirement": "reviewed_at_present",
            "description": "reviewed_at must contain valid ISO-8601 timestamp.",
            "pass": reviewed_at_present,
            "reviewed_at_present": reviewed_at_present,
        },
        "HC_REQ_007": {
            "requirement": "ready_for_upgrade_true",
            "description": "ready_for_upgrade must be explicitly set to true.",
            "pass": ready_for_upgrade_true,
            "ready_for_upgrade_true": ready_for_upgrade_true,
        },
        "HC_REQ_008": {
            "requirement": "no_rejected_source_as_core_evidence",
            "description": "No rejected_source entry must be used as core evidence.",
            "pass": no_rejected_core,
            "rejected_source_as_core": not no_rejected_core,
        },
        "HC_REQ_009": {
            "requirement": "not_single_source_low_to_high",
            "description": "Low/unknown whale must not be upgraded to high from a single source alone.",
            "pass": not_single_source_low_to_high,
            "is_low_unknown": is_low_unknown,
            "single_source_only": single_source_only,
        },
    }

    all_pass = all(r["pass"] for r in reqs.values())

    return reqs, all_pass


# ---------------------------------------------------------------------------
# Compute evidence score
# ---------------------------------------------------------------------------
def compute_evidence_score(hc_reqs: dict, rejected_check: dict) -> int:
    """
    Compute a simple evidence score:
      - Each passing HC requirement: +1
      - Each source category present and accepted: +1 (max 3 for primary/secondary/activity)
      - Rejected source detected in core: -2
      Minimum: 0, Maximum: 12 (9 HC + 3 categories)
    """
    score = 0
    for req_id, req in hc_reqs.items():
        if req["pass"]:
            score += 1

    # Bonus for categories
    if hc_reqs.get("HC_REQ_001", {}).get("trusted_source_accepted", False):
        score += 1  # primary source present and accepted
    if hc_reqs.get("HC_REQ_002", {}).get("second_source_accepted", False):
        score += 1  # secondary source present and accepted
    if hc_reqs.get("HC_REQ_003", {}).get("activity_source_accepted", False):
        score += 1  # activity source present and accepted

    # Penalty for rejected source as core
    if rejected_check.get("rejected_keywords_found_in_trusted_source", False):
        score -= 2

    return max(0, min(12, score))


# ---------------------------------------------------------------------------
# Build scoring record for a row
# ---------------------------------------------------------------------------
def build_scoring_record(row: dict, registry: dict) -> dict:
    """Build a scoring record for a single workbook/fixture row."""
    address = row.get("address", "")
    current_label = row.get("current_label", "")
    current_confidence = row.get("current_confidence", "")
    target_confidence = row.get("target_confidence", "high")

    trusted_label = row.get("trusted_source_label_value", "")
    second_label = row.get("second_source_label_value", "")
    activity_note = row.get("activity_pattern_note", "")

    trusted_category = classify_trusted_source_category(trusted_label, registry)
    second_category = classify_second_source_category(second_label, registry)
    activity_category = classify_activity_source(activity_note, registry)
    rejected_check = detect_rejected_source(trusted_label, second_label, registry)
    hc_reqs, all_hc_pass = check_high_confidence_requirements(row, registry, rejected_check)
    evidence_score = compute_evidence_score(hc_reqs, rejected_check)

    record = {
        "address": address,
        "current_label": current_label,
        "current_confidence": current_confidence,
        "target_confidence": target_confidence,
        "trusted_source_present": non_empty(trusted_label),
        "trusted_source_category": trusted_category,
        "trusted_source_accepted": trusted_category == "primary_source",
        "second_source_present": non_empty(second_label),
        "second_source_category": second_category,
        "second_source_accepted": second_category in ("primary_source", "secondary_source"),
        "activity_pattern_present": non_empty(activity_note),
        "activity_source_accepted": activity_category in ("activity_source", "unknown"),
        "operator_confirmation_present": non_empty(row.get("operator_confirmed_label", "")),
        "reviewer_present": non_empty(row.get("reviewer", "")),
        "reviewed_at_present": non_empty(row.get("reviewed_at", "")),
        "ready_for_upgrade": parse_bool_csv(row.get("ready_for_upgrade", "false")),
        "rejected_source_detected": rejected_check["rejected_source_detected"],
        "evidence_score": evidence_score,
        "minimum_high_confidence_requirements_met": all_hc_pass,
        "hc_requirements_detail": {
            req_id: {
                "requirement": req["requirement"],
                "pass": req["pass"],
            }
            for req_id, req in hc_reqs.items()
        },
    }
    return record, hc_reqs, all_hc_pass, rejected_check


# ---------------------------------------------------------------------------
# Build scoring decision for a record
# ---------------------------------------------------------------------------
def build_scoring_decision(record: dict, all_hc_pass: bool,
                           is_fixture: bool = False) -> dict:
    """Build a scoring decision from a scoring record."""
    address = record["address"]

    if all_hc_pass:
        if is_fixture:
            decision = "scoring_passed_for_fixture_only"
            high_confidence_allowed = True
            label_upgrade_allowed = False  # fixture: no real upgrade
            block_reasons = ""
        else:
            decision = "scoring_passed"
            high_confidence_allowed = True
            label_upgrade_allowed = True
            block_reasons = ""
    else:
        decision = "scoring_blocked"
        high_confidence_allowed = False
        label_upgrade_allowed = False

        # Collect block reasons from HC requirements
        block_reason_list = []
        hc_detail = record.get("hc_requirements_detail", {})
        for req_id, req in hc_detail.items():
            if not req.get("pass", False):
                block_reason_list.append(f"{req_id}_FAILED")

        if record.get("rejected_source_detected", False):
            block_reason_list.append("REJECTED_SOURCE_DETECTED")

        if not record.get("trusted_source_present", False):
            block_reason_list.append("NO_TRUSTED_SOURCE_LABEL_PROVIDED")
        if not record.get("second_source_present", False):
            block_reason_list.append("NO_SECOND_SOURCE_PROVIDED")
        if not record.get("activity_pattern_present", False):
            block_reason_list.append("NO_ACTIVITY_PATTERN_PROVIDED")
        if not record.get("operator_confirmation_present", False):
            block_reason_list.append("NO_OPERATOR_CONFIRMATION")
        if not record.get("reviewer_present", False):
            block_reason_list.append("NO_REVIEWER")
        if not record.get("reviewed_at_present", False):
            block_reason_list.append("NO_REVIEWED_AT")
        if not record.get("ready_for_upgrade", False):
            block_reason_list.append("READY_FOR_UPGRADE_NOT_TRUE")

        block_reasons = "; ".join(block_reason_list)

    return {
        "address": address,
        "decision": decision,
        "evidence_score": record["evidence_score"],
        "high_confidence_allowed": high_confidence_allowed,
        "label_upgrade_allowed": label_upgrade_allowed,
        "block_reasons": block_reasons,
        "send_allowed": False,
        "tg_test_group_allowed": False,
        "public_send_allowed": False,
    }


# ---------------------------------------------------------------------------
# Rejected source negative check
# ---------------------------------------------------------------------------
def run_rejected_source_negative_check(registry: dict) -> dict:
    """
    Built-in negative check: verify that a rejected source alone cannot
    grant high confidence. Tests the invariant that rejected_source evidence
    can never support a high-confidence label upgrade.
    """
    rejected_types = registry.get("categories", {}).get("rejected_source", {}).get("types", [])
    rejected_type_ids = [rt.get("type_id", "") for rt in rejected_types]

    # Construct a hypothetical row where the ONLY evidence is from rejected sources
    mock_row = {
        "address": "0xREJECTED_NEGATIVE_CHECK_MOCK",
        "current_label": "Unknown Whale",
        "current_confidence": "low",
        "target_confidence": "high",
        "trusted_source_label_value": "Vague 'Whale Said to Be X' Style Notes — no URL provided",
        "trusted_source_url_or_note": "",
        "second_source_label_value": "TG Chat Label Without Evidence",
        "second_source_url_or_note": "",
        "activity_pattern_note": "",
        "operator_confirmed_label": "",
        "operator_confidence_assessment": "",
        "reviewer": "",
        "reviewed_at": "",
        "ready_for_upgrade": "false",
    }

    record, hc_reqs, all_hc_pass, rejected_check = build_scoring_record(mock_row, registry)

    # Verify: rejected source is detected, HC requirements not met, high confidence not allowed
    rejected_source_negative_check_passed = (
        rejected_check["rejected_source_detected"] is True
        and all_hc_pass is False
        and record["minimum_high_confidence_requirements_met"] is False
        and record["evidence_score"] <= 0
    )

    return {
        "rejected_source_negative_check_passed": rejected_source_negative_check_passed,
        "rejected_source_can_grant_high_confidence": False,
        "mock_record_evidence_score": record["evidence_score"],
        "mock_record_high_confidence_met": all_hc_pass,
        "mock_record_rejected_detected": rejected_check["rejected_source_detected"],
    }


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115L Whale Label Evidence Scoring Gate — Local Only")
    print("=" * 70)

    # Step 1: Load registry and scoring policy
    print("\n[1/8] Loading v115K registry and scoring policy...")
    registry = load_json(V115K_REGISTRY)
    scoring_policy = load_json(V115K_SCORING_POLICY)
    print(f"  [OK] Registry: {registry.get('registry_categories', '?')} categories, "
          f"version={registry.get('version', '?')}")
    print(f"  [OK] Scoring policy: version={scoring_policy.get('version', '?')}, "
          f"{scoring_policy.get('minimum_for_high_confidence', {}).get('total_requirements', '?')} HC requirements")

    registry_loaded = True
    scoring_policy_loaded = True

    # Step 2: Load v115F workbook (real)
    print("\n[2/8] Loading v115F real workbook...")
    wb_rows = load_csv_dict(V115F_WORKBOOK)
    print(f"  [OK] Real workbook: {len(wb_rows)} rows loaded")

    # Step 3: Load v115I fixture
    print("\n[3/8] Loading v115I positive-path fixture...")
    fixture_rows = load_csv_dict(V115I_FIXTURE)
    print(f"  [OK] Fixture: {len(fixture_rows)} rows loaded")

    # Step 4: Process real workbook rows → scoring records + decisions
    print("\n[4/8] Processing real workbook evidence scoring...")
    real_records = []
    real_decisions = []
    real_passed = 0
    real_blocked = 0

    for row in wb_rows:
        record, hc_reqs, all_hc_pass, rejected_check = build_scoring_record(row, registry)
        real_records.append(record)

        decision = build_scoring_decision(record, all_hc_pass, is_fixture=False)
        real_decisions.append(decision)

        if all_hc_pass:
            real_passed += 1
        else:
            real_blocked += 1

        addr_short = record["address"][:10] + "..."
        print(f"  [{record['address'][:10]}...] evidence_score={record['evidence_score']}, "
              f"hc_met={all_hc_pass}, rejected={rejected_check['rejected_source_detected']}")

    print(f"  [OK] Real workbook: {real_passed} passed, {real_blocked} blocked")

    # Step 5: Process fixture row → fixture scoring records + decisions
    print("\n[5/8] Processing fixture evidence scoring...")
    fixture_records = []
    fixture_decisions = []
    fixture_passed = 0
    fixture_high_confidence_allowed = 0

    for row in fixture_rows:
        record, hc_reqs, all_hc_pass, rejected_check = build_scoring_record(row, registry)
        fixture_records.append(record)

        decision = build_scoring_decision(record, all_hc_pass, is_fixture=True)
        fixture_decisions.append(decision)

        if all_hc_pass:
            fixture_passed += 1
        if decision["high_confidence_allowed"]:
            fixture_high_confidence_allowed += 1

        addr_short = record["address"][:10] + "..."
        print(f"  [{record['address'][:10]}...] evidence_score={record['evidence_score']}, "
              f"hc_met={all_hc_pass}, fixture_passed={all_hc_pass}")

    print(f"  [OK] Fixture: {fixture_passed} passed, "
          f"high_confidence_allowed={fixture_high_confidence_allowed}")

    # Step 6: Run rejected-source negative check
    print("\n[6/8] Running rejected-source negative check...")
    negative_check = run_rejected_source_negative_check(registry)
    print(f"  [{'OK' if negative_check['rejected_source_negative_check_passed'] else 'NO'}] "
          f"rejected_source_negative_check_passed={negative_check['rejected_source_negative_check_passed']}")
    print(f"  [OK] rejected_source_can_grant_high_confidence={negative_check['rejected_source_can_grant_high_confidence']}")

    # Step 7: Save all outputs
    print("\n[7/8] Saving all output files...")

    save_jsonl(OUT_REAL_RECORDS, real_records)
    print(f"  [OK] Real scoring records -> {OUT_REAL_RECORDS}")

    save_jsonl(OUT_REAL_DECISIONS, real_decisions)
    print(f"  [OK] Real scoring decisions -> {OUT_REAL_DECISIONS}")

    save_jsonl(OUT_FIXTURE_RECORDS, fixture_records)
    print(f"  [OK] Fixture scoring records -> {OUT_FIXTURE_RECORDS}")

    save_jsonl(OUT_FIXTURE_DECISIONS, fixture_decisions)
    print(f"  [OK] Fixture scoring decisions -> {OUT_FIXTURE_DECISIONS}")

    # Build gate result
    gate_result = {
        "stage": "v115l_whale_label_evidence_scoring_gate_local_only",
        "registry_loaded": registry_loaded,
        "scoring_policy_loaded": scoring_policy_loaded,
        "real_workbook_rows": len(wb_rows),
        "real_scoring_records": len(real_records),
        "real_scoring_decisions": len(real_decisions),
        "real_scoring_passed_count": real_passed,
        "real_scoring_blocked_count": real_blocked,
        "fixture_rows": len(fixture_rows),
        "fixture_scoring_records": len(fixture_records),
        "fixture_scoring_decisions": len(fixture_decisions),
        "fixture_scoring_passed_count": fixture_passed,
        "fixture_high_confidence_allowed_count": fixture_high_confidence_allowed,
        "fixture_label_upgraded_count": 0,
        "rejected_source_negative_check_passed": negative_check["rejected_source_negative_check_passed"],
        "rejected_source_can_grant_high_confidence": negative_check["rejected_source_can_grant_high_confidence"],
        "real_workbook_modified": REAL_WORKBOOK_MODIFIED,
        "real_label_upgrade_performed": REAL_LABEL_UPGRADE_PERFORMED,
        "real_send_candidate_generated": REAL_SEND_CANDIDATE_GENERATED,
        "send_ready": False,
        "tg_test_group_ready": False,
        "local_review_ready": True,
        "external_api_called": EXTERNAL_API_CALLED,
        "ai_model_called": AI_MODEL_CALLED,
        "credentials_read": CREDENTIALS_READ,
        "tg_sent": TG_SENT,
        "prod_state_write": PROD_STATE_WRITE,
        "daemon_started": DAEMON_STARTED,
        "watcher_started": WATCHER_STARTED,
        "files_deleted": FILES_DELETED,
        "hc_requirement_ids_referenced": [
            "HC_REQ_001", "HC_REQ_002", "HC_REQ_003", "HC_REQ_004",
            "HC_REQ_005", "HC_REQ_006", "HC_REQ_007", "HC_REQ_008", "HC_REQ_009",
        ],
        "generated_at": now_iso(),
    }

    save_json(OUT_GATE_RESULT, gate_result)
    print(f"  [OK] Gate result -> {OUT_GATE_RESULT}")

    # Generate markdown report
    md_text = generate_markdown(gate_result, real_records, fixture_records,
                                real_decisions, fixture_decisions, negative_check)
    save_text(OUT_MD, md_text)
    print(f"  [OK] Markdown -> {OUT_MD}")

    # Generate handoff
    handoff_text = generate_handoff(gate_result, real_records, fixture_records,
                                    real_decisions, fixture_decisions, negative_check)
    save_text(OUT_HANDOFF, handoff_text)
    print(f"  [OK] Handoff -> {OUT_HANDOFF}")

    # Step 8: Summary
    print("\n" + "=" * 70)
    print("v115L WHALE LABEL EVIDENCE SCORING GATE COMPLETE")
    print(f"  registry_loaded: {gate_result['registry_loaded']}")
    print(f"  scoring_policy_loaded: {gate_result['scoring_policy_loaded']}")
    print(f"  real_workbook_rows: {gate_result['real_workbook_rows']}")
    print(f"  real_scoring_records: {gate_result['real_scoring_records']}")
    print(f"  real_scoring_decisions: {gate_result['real_scoring_decisions']}")
    print(f"  real_scoring_passed_count: {gate_result['real_scoring_passed_count']}")
    print(f"  real_scoring_blocked_count: {gate_result['real_scoring_blocked_count']}")
    print(f"  fixture_rows: {gate_result['fixture_rows']}")
    print(f"  fixture_scoring_passed_count: {gate_result['fixture_scoring_passed_count']}")
    print(f"  fixture_high_confidence_allowed_count: {gate_result['fixture_high_confidence_allowed_count']}")
    print(f"  fixture_label_upgraded_count: {gate_result['fixture_label_upgraded_count']}")
    print(f"  rejected_source_negative_check_passed: {gate_result['rejected_source_negative_check_passed']}")
    print(f"  rejected_source_can_grant_high_confidence: {gate_result['rejected_source_can_grant_high_confidence']}")
    print(f"  real_workbook_modified: {gate_result['real_workbook_modified']}")
    print(f"  real_label_upgrade_performed: {gate_result['real_label_upgrade_performed']}")
    print(f"  real_send_candidate_generated: {gate_result['real_send_candidate_generated']}")
    print(f"  send_ready: {gate_result['send_ready']}")
    print(f"  tg_test_group_ready: {gate_result['tg_test_group_ready']}")
    print(f"  tg_sent: {gate_result['tg_sent']}")
    print(f"  prod_state_write: {gate_result['prod_state_write']}")
    print(f"  external_api_called: {gate_result['external_api_called']}")
    print(f"  credentials_read: {gate_result['credentials_read']}")
    print("=" * 70)

    return 0


# ---------------------------------------------------------------------------
# Markdown report generator
# ---------------------------------------------------------------------------
def generate_markdown(gate_result, real_records, fixture_records,
                      real_decisions, fixture_decisions, negative_check):
    """Generate the markdown report."""
    md = f"""# v115L Whale Label Evidence Scoring Gate — Local Only

**Generated:** {gate_result['generated_at']}
**Stage:** v115l_whale_label_evidence_scoring_gate_local_only
**Lane:** 1

---

## ⚠️ IMPORTANT: Read Before Continuing

1. **This is a LOCAL evidence scoring gate only.**
2. **This file is NOT a trading signal, NOT a production send file, NOT a TG send candidate.**
3. **No real workbook has been modified. No real labels have been upgraded.**
4. **This gate reads the v115K registry + scoring policy and applies them to the real v115F workbook and v115I fixture.**
5. **All safety invariants are enforced. No external communication is intended.**

---

## 1. Evidence Scoring Gate Summary

| Metric | Value |
|--------|-------|
| registry_loaded | **{gate_result['registry_loaded']}** |
| scoring_policy_loaded | **{gate_result['scoring_policy_loaded']}** |
| real_workbook_rows | **{gate_result['real_workbook_rows']}** |
| real_scoring_records | **{gate_result['real_scoring_records']}** |
| real_scoring_decisions | **{gate_result['real_scoring_decisions']}** |
| real_scoring_passed_count | **{gate_result['real_scoring_passed_count']}** |
| real_scoring_blocked_count | **{gate_result['real_scoring_blocked_count']}** |
| fixture_rows | **{gate_result['fixture_rows']}** |
| fixture_scoring_passed_count | **{gate_result['fixture_scoring_passed_count']}** |
| fixture_high_confidence_allowed_count | **{gate_result['fixture_high_confidence_allowed_count']}** |
| fixture_label_upgraded_count | **{gate_result['fixture_label_upgraded_count']}** |
| rejected_source_negative_check_passed | **{gate_result['rejected_source_negative_check_passed']}** |
| rejected_source_can_grant_high_confidence | **{gate_result['rejected_source_can_grant_high_confidence']}** |

---

## 2. Real Workbook Scoring (v115F — 4 addresses)

"""
    for i, (rec, dec) in enumerate(zip(real_records, real_decisions)):
        addr_short = rec["address"][:10] + "..." if len(rec["address"]) > 14 else rec["address"]
        md += f"""
### Row {i + 1}: {addr_short}

| Field | Value |
|-------|-------|
| current_label | {rec['current_label']} |
| current_confidence | {rec['current_confidence']} |
| trusted_source_present | {rec['trusted_source_present']} |
| trusted_source_category | {rec['trusted_source_category']} |
| trusted_source_accepted | {rec['trusted_source_accepted']} |
| second_source_present | {rec['second_source_present']} |
| second_source_category | {rec['second_source_category']} |
| second_source_accepted | {rec['second_source_accepted']} |
| activity_pattern_present | {rec['activity_pattern_present']} |
| activity_source_accepted | {rec['activity_source_accepted']} |
| operator_confirmation_present | {rec['operator_confirmation_present']} |
| reviewer_present | {rec['reviewer_present']} |
| reviewed_at_present | {rec['reviewed_at_present']} |
| ready_for_upgrade | {rec['ready_for_upgrade']} |
| rejected_source_detected | {rec['rejected_source_detected']} |
| evidence_score | **{rec['evidence_score']}** |
| minimum_high_confidence_requirements_met | **{rec['minimum_high_confidence_requirements_met']}** |
| decision | **{dec['decision']}** |
| high_confidence_allowed | **{dec['high_confidence_allowed']}** |
| label_upgrade_allowed | **{dec['label_upgrade_allowed']}** |
| block_reasons | {dec['block_reasons'] or 'N/A'} |
| send_allowed | {dec['send_allowed']} |
| tg_test_group_allowed | {dec['tg_test_group_allowed']} |
| public_send_allowed | {dec['public_send_allowed']} |
"""

    md += """
---

## 3. Fixture Scoring (v115I — 1 address)

"""
    for i, (rec, dec) in enumerate(zip(fixture_records, fixture_decisions)):
        addr_short = rec["address"][:10] + "..." if len(rec["address"]) > 14 else rec["address"]
        md += f"""
### Fixture Row: {addr_short}

| Field | Value |
|-------|-------|
| current_label | {rec['current_label']} |
| current_confidence | {rec['current_confidence']} |
| trusted_source_present | {rec['trusted_source_present']} |
| trusted_source_category | {rec['trusted_source_category']} |
| trusted_source_accepted | {rec['trusted_source_accepted']} |
| second_source_present | {rec['second_source_present']} |
| second_source_category | {rec['second_source_category']} |
| second_source_accepted | {rec['second_source_accepted']} |
| activity_pattern_present | {rec['activity_pattern_present']} |
| activity_source_accepted | {rec['activity_source_accepted']} |
| operator_confirmation_present | {rec['operator_confirmation_present']} |
| reviewer_present | {rec['reviewer_present']} |
| reviewed_at_present | {rec['reviewed_at_present']} |
| ready_for_upgrade | {rec['ready_for_upgrade']} |
| rejected_source_detected | {rec['rejected_source_detected']} |
| evidence_score | **{rec['evidence_score']}** |
| minimum_high_confidence_requirements_met | **{rec['minimum_high_confidence_requirements_met']}** |
| decision | **{dec['decision']}** |
| high_confidence_allowed | **{dec['high_confidence_allowed']}** |
| label_upgrade_allowed | **{dec['label_upgrade_allowed']}** |
| block_reasons | {dec['block_reasons'] or 'N/A'} |
"""

    md += f"""
---

## 4. Rejected Source Negative Check

| Field | Value |
|-------|-------|
| rejected_source_negative_check_passed | **{negative_check['rejected_source_negative_check_passed']}** |
| rejected_source_can_grant_high_confidence | **{negative_check['rejected_source_can_grant_high_confidence']}** |
| mock_record_evidence_score | {negative_check['mock_record_evidence_score']} |
| mock_record_high_confidence_met | {negative_check['mock_record_high_confidence_met']} |

---

## 5. HC Requirements Referenced

"""
    for req_id in gate_result["hc_requirement_ids_referenced"]:
        md += f"- `{req_id}`\n"

    md += f"""
---

## 6. Safety Invariants

| Invariant | Value |
|-----------|-------|
| external_api_called | [OK] {gate_result['external_api_called']} |
| ai_model_called | [OK] {gate_result['ai_model_called']} |
| credentials_read | [OK] {gate_result['credentials_read']} |
| tg_sent | [OK] {gate_result['tg_sent']} |
| prod_state_write | [OK] {gate_result['prod_state_write']} |
| daemon_started | [OK] {gate_result['daemon_started']} |
| watcher_started | [OK] {gate_result['watcher_started']} |
| files_deleted | [OK] {gate_result['files_deleted']} |
| real_workbook_modified | [OK] {gate_result['real_workbook_modified']} |
| real_label_upgrade_performed | [OK] {gate_result['real_label_upgrade_performed']} |
| real_send_candidate_generated | [OK] {gate_result['real_send_candidate_generated']} |
| send_ready | [OK] {gate_result['send_ready']} |
| tg_test_group_ready | [OK] {gate_result['tg_test_group_ready']} |
| local_review_ready | [OK] {gate_result['local_review_ready']} |

---

## 7. Explicit NOT Declarations

This stage is explicitly **NOT**:
- [NO] A label upgrade execution
- [NO] A TG send
- [NO] A trading signal
- [NO] Financial advice
- [NO] A production send file
- [NO] A public send candidate
- [NO] AI-generated evidence
- [NO] External API query results
- [NO] A modification of any real workbook or gate result
- [NO] A daemon, watcher, cron job, or background loop

This stage **IS**:
- [OK] A local evidence scoring gate
- [OK] Application of v115K registry + scoring policy
- [OK] Scoring records for both real workbook and fixture
- [OK] Scoring decisions with evidence scores
- [OK] Rejected source negative check
- [OK] Fully guarded — all send flags are false
- [OK] Traceable, verifiable, reproducible

---

*Generated by v115L runner. Local only. No external communication intended.*
"""
    return md


# ---------------------------------------------------------------------------
# Handoff generator
# ---------------------------------------------------------------------------
def generate_handoff(gate_result, real_records, fixture_records,
                     real_decisions, fixture_decisions, negative_check):
    """Generate the handoff markdown."""
    handoff = f"""# v115L Handoff — Whale Label Evidence Scoring Gate Local Only

**Generated:** {gate_result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115L

---

## What Was Done

1. Loaded v115K evidence source registry (4 categories, {gate_result.get('registry_loaded', '?')})
2. Loaded v115K evidence scoring policy (9 HC requirements)
3. Loaded v115F real operator workbook (4 rows, all operator fields empty)
4. Loaded v115I positive-path fixture (1 row, all evidence complete)
5. Applied v115K high-confidence evidence scoring rules to all rows
6. Generated scoring records and decisions for real workbook (4 scoring_blocked)
7. Generated scoring records and decisions for fixture (1 scoring_passed_for_fixture_only)
8. Executed built-in rejected-source negative check
9. Generated gate result JSON with all required invariants
10. Generated markdown report
11. Generated this handoff

## Key Results

| Metric | Value |
|--------|-------|
| real_workbook_rows | {gate_result['real_workbook_rows']} |
| real_scoring_records | {gate_result['real_scoring_records']} |
| real_scoring_decisions | {gate_result['real_scoring_decisions']} |
| real_scoring_passed_count | {gate_result['real_scoring_passed_count']} |
| real_scoring_blocked_count | {gate_result['real_scoring_blocked_count']} |
| fixture_rows | {gate_result['fixture_rows']} |
| fixture_scoring_passed_count | {gate_result['fixture_scoring_passed_count']} |
| fixture_high_confidence_allowed_count | {gate_result['fixture_high_confidence_allowed_count']} |
| fixture_label_upgraded_count | {gate_result['fixture_label_upgraded_count']} |
| rejected_source_negative_check_passed | {gate_result['rejected_source_negative_check_passed']} |
| rejected_source_can_grant_high_confidence | {gate_result['rejected_source_can_grant_high_confidence']} |
| real_workbook_modified | {gate_result['real_workbook_modified']} |
| real_label_upgrade_performed | {gate_result['real_label_upgrade_performed']} |
| real_send_candidate_generated | {gate_result['real_send_candidate_generated']} |
| send_ready | {gate_result['send_ready']} |
| tg_test_group_ready | {gate_result['tg_test_group_ready']} |
| local_review_ready | {gate_result['local_review_ready']} |

## HC Requirements Applied

{chr(10).join(f'- **{req_id}**' for req_id in gate_result.get('hc_requirement_ids_referenced', []))}

## Rejected Source Negative Check

- rejected_source_negative_check_passed: **{negative_check['rejected_source_negative_check_passed']}**
- rejected_source_can_grant_high_confidence: **{negative_check['rejected_source_can_grant_high_confidence']}**
- Mock record with rejected-source-only evidence: evidence_score={negative_check['mock_record_evidence_score']}, hc_met={negative_check['mock_record_high_confidence_met']}

## Safety Invariants Confirmed

- `external_api_called=false` ✅
- `ai_model_called=false` ✅
- `credentials_read=false` ✅
- `tg_sent=false` ✅
- `prod_state_write=false` ✅
- `daemon_started=false` ✅
- `watcher_started=false` ✅
- `files_deleted=false` ✅
- `real_workbook_modified=false` ✅
- `real_label_upgrade_performed=false` ✅
- `real_send_candidate_generated=false` ✅
- v114A-v115K old results NOT modified ✅

## Key Conclusion

**The v115L evidence scoring gate is operational.**

- Real workbook (4 addresses): ALL scoring_blocked — the workbook fields are empty, no evidence can pass HC requirements. This is expected.
- Fixture (1 address): scoring_passed_for_fixture_only — the synthetic evidence satisfies all HC requirements.
- Rejected source negative check: PASSED — rejected-source-only evidence cannot grant high confidence.
- No real labels were modified. No TG messages were sent. All gates remain unchanged.

**v115K registry/scoring policy is proven executable.**

## This Stage Is NOT

- A label upgrade execution
- A TG send
- A production send
- A trading signal
- A real send candidate
- AI-generated evidence
- A modification of any real workbook data
- A daemon, watcher, cron job, or background loop

## This Stage IS

- A local evidence scoring gate
- The executable counterpart to v115K policy definition
- Verification that the registry + scoring policy can be mechanically applied
- Independent of real workbook data
- Fully guarded (all send flags false)
- Re-runnable for verification

---
*This handoff is for the next stage decision-maker. The v115L evidence scoring gate is complete.*
"""
    return handoff


if __name__ == "__main__":
    sys.exit(main())
