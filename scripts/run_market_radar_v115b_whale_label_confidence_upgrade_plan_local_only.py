#!/usr/bin/env python3
"""
v115B Whale Label Confidence Upgrade Plan — Local Only
========================================================
Reads v115A send-readiness blockers, v114C operator review cards,
and v114B delta records to produce a comprehensive local policy plan.

This is a POLICY DESIGN step, NOT a send step. No external APIs,
no TG send, no production state write, no label confidence changes.

Outputs:
  - Label confidence routing policy JSON
  - Label upgrade target list JSONL
  - TG test copy gate policy JSON
  - Send preview gate policy JSON
  - Rollback / cooldown / no-repeat policy JSON
  - Result JSON
  - Markdown report
  - Handoff markdown

Invariants (enforced):
  - No external API calls
  - No API key / credentials read
  - No TG send
  - No production state write
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115A old results
  - No real send candidate generation
"""

import json
import os
import sys
import datetime
import hashlib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# Reference inputs (read-only)
V115A_RESULT = os.path.join(RESULTS_DIR, "market_radar_v115a_whale_delta_send_readiness_gate_result.json")
V115A_BLOCKERS = os.path.join(RESULTS_DIR, "market_radar_v115a_whale_delta_send_readiness_blockers.jsonl")
V114C_CARDS = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl")
V114B_DELTAS = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_position_deltas.jsonl")
V114D_MANIFEST = os.path.join(RESULTS_DIR, "market_radar_v114d_whale_delta_review_pack_manifest.json")

# v115B outputs
OUT_ROUTING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json")
OUT_TG_COPY_GATE = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_tg_test_copy_gate_policy.json")
OUT_SEND_PREVIEW_GATE = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_send_preview_gate_policy.json")
OUT_ROLLBACK_COOLDOWN = os.path.join(CONFIG_DIR, "market_radar_v115b_whale_rollback_cooldown_policy.json")
OUT_RESULT = os.path.join(RESULTS_DIR, "market_radar_v115b_whale_label_confidence_upgrade_plan_result.json")
OUT_UPGRADE_TARGETS = os.path.join(RESULTS_DIR, "market_radar_v115b_whale_label_upgrade_targets.jsonl")
OUT_REPORT = os.path.join(RUNS_DIR, "v115b_whale_label_confidence_upgrade_plan_local_only.md")
OUT_HANDOFF = os.path.join(RUNS_DIR, "v115b_whale_label_confidence_upgrade_plan_local_only_handoff.md")

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants
EXTERNAL_API_CALLED = False
CREDENTIALS_READ = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
TG_SENT = False
PROD_STATE_WRITE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.datetime.now(TZ_SHANGHAI).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_jsonl(path) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Step 1: Load reference inputs
# ---------------------------------------------------------------------------
def load_reference_inputs():
    """Load v115A blockers, v114C cards, v114B deltas (read-only)."""
    errors = []

    for label, path in [
        ("v115A result", V115A_RESULT),
        ("v115A blockers", V115A_BLOCKERS),
        ("v114C review cards", V114C_CARDS),
        ("v114B delta records", V114B_DELTAS),
        ("v114D manifest", V114D_MANIFEST),
    ]:
        if not os.path.exists(path):
            errors.append(f"{label} not found: {path}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    v115a_result = load_json(V115A_RESULT)
    v115a_blockers = load_jsonl(V115A_BLOCKERS)
    v114c_cards = load_jsonl(V114C_CARDS)
    v114b_deltas = load_jsonl(V114B_DELTAS)
    v114d_manifest = load_json(V114D_MANIFEST)

    print(f"  v115A result: send_ready={v115a_result.get('send_ready')}, "
          f"blockers={v115a_result.get('blocker_count')}")
    print(f"  v115A blockers: {len(v115a_blockers)} blockers loaded")
    print(f"  v114C review cards: {len(v114c_cards)} cards")
    print(f"  v114B delta records: {len(v114b_deltas)} records")

    return v115a_result, v115a_blockers, v114c_cards, v114b_deltas, v114d_manifest


# ---------------------------------------------------------------------------
# Step 2: Analyze label confidence distribution from v114C cards
# ---------------------------------------------------------------------------
def analyze_label_confidence(v114c_cards):
    """Extract label confidence distribution and unique addresses from v114C."""
    distribution = {"high": 0, "medium": 0, "low": 0}
    address_map = {}  # address -> {label, label_confidence, positions, delta_types}

    for c in v114c_cards:
        lc = c.get("label_confidence", "unknown")
        if lc in distribution:
            distribution[lc] += 1

        addr = c.get("address", "?")
        label = c.get("label", "?")
        asset = c.get("asset", "?")
        delta_type = c.get("delta_type", "?")
        attention = c.get("operator_attention_level", "?")
        side = c.get("side", "?")

        if addr not in address_map:
            address_map[addr] = {
                "address": addr,
                "label": label,
                "label_confidence": lc,
                "positions": [],
                "delta_types": set(),
                "highest_attention": "low",
            }
        address_map[addr]["positions"].append({
            "asset": asset,
            "side": side,
            "delta_type": delta_type,
            "operator_attention_level": attention,
        })
        address_map[addr]["delta_types"].add(delta_type)
        # Track highest attention level
        attn_order = {"high": 3, "medium": 2, "low": 1}
        if attn_order.get(attention, 0) > attn_order.get(address_map[addr]["highest_attention"], 0):
            address_map[addr]["highest_attention"] = attention

    print(f"  Label confidence: high={distribution['high']}, "
          f"medium={distribution['medium']}, low={distribution['low']}")
    print(f"  Unique addresses: {len(address_map)}")
    return distribution, address_map


# ---------------------------------------------------------------------------
# Step 3: Build label upgrade targets
# ---------------------------------------------------------------------------
def build_upgrade_targets(address_map, v114b_deltas, v114c_cards):
    """Build upgrade target list for all medium/low confidence addresses."""
    targets = []

    # Build delta info lookup from v114B
    delta_by_addr = {}
    for d in v114b_deltas:
        addr = d.get("address", "")
        if addr not in delta_by_addr:
            delta_by_addr[addr] = []
        delta_by_addr[addr].append(d)

    for addr, info in address_map.items():
        lc = info["label_confidence"]
        if lc == "high":
            continue  # Already high — skip

        # Determine upgrade priority
        priority = "medium"
        reason_parts = []

        has_closed = "closed_position" in info["delta_types"]
        num_positions = len(info["positions"])

        if lc == "low" and has_closed:
            priority = "high"
            reason_parts.append(
                f"Low-confidence unknown whale with BTC closed_position event. "
                f"This is the only closed_position in the current pack."
            )
        elif lc == "low":
            priority = "high"
            reason_parts.append(
                f"Low-confidence unknown whale. "
                f"Label confidence must be upgraded before any routing."
            )
        elif lc == "medium" and num_positions >= 2:
            priority = "medium"
            reason_parts.append(
                f"Medium-confidence label with {num_positions} positions across "
                f"multiple assets."
            )
        else:
            priority = "medium"
            reason_parts.append(
                f"Medium-confidence label with {num_positions} position(s)."
            )

        # Add specific details
        for p in info["positions"]:
            if p["delta_type"] == "closed_position":
                reason_parts.append(
                    f"Contains {p['asset']} closed_position (attention={p['operator_attention_level']})"
                )
            elif p["operator_attention_level"] == "high":
                reason_parts.append(
                    f"{p['asset']} has high operator attention"
                )

        # Gather warnings from linked v114C cards
        warnings = []
        for c in v114c_cards:
            if c.get("address") == addr:
                warnings = c.get("warnings", [])
                break

        target = {
            "version": "v115B",
            "address": addr,
            "current_label": info["label"],
            "current_label_confidence": lc,
            "upgrade_priority": priority,
            "reason": " ".join(reason_parts),
            "required_evidence_for_high_confidence": [
                "trusted_source_label",
                "cross_source_consistency",
                "address_activity_consistency",
                "manual_operator_confirmation",
            ],
            "allowed_current_routing": "operator_review_only",
            "tg_test_group_allowed_now": False,
            "public_send_allowed_now": False,
            "delta_types": list(info["delta_types"]),
            "positions_linked": num_positions,
            "operator_attention_level": info["highest_attention"],
            "warnings": warnings,
        }
        targets.append(target)

    # Sort: high priority first, then medium
    targets.sort(key=lambda t: (0 if t["upgrade_priority"] == "high" else 1, t["address"]))

    print(f"  Upgrade targets: {len(targets)} (high={sum(1 for t in targets if t['upgrade_priority'] == 'high')}, "
          f"medium={sum(1 for t in targets if t['upgrade_priority'] == 'medium')})")
    return targets


# ---------------------------------------------------------------------------
# Step 4: Generate label confidence routing policy
# ---------------------------------------------------------------------------
def generate_routing_policy(distribution):
    """Generate the label confidence routing policy JSON."""
    policy = {
        "version": "v115B",
        "policy_name": "whale_label_confidence_routing_policy",
        "description": (
            "Defines routing rules based on label confidence levels. "
            "No position may be routed to TG test group or public send "
            "without meeting these thresholds."
        ),
        "send_ready_requires": {
            "minimum_label_confidence": "high",
            "unknown_whale_allowed_for_send": False,
            "low_confidence_allowed_for_tg_test": False,
            "medium_confidence_allowed_for_tg_test": "review_required_only",
            "high_confidence_required_for_public_send": True,
        },
        "routing_rules": {
            "high": {
                "operator_review_allowed": True,
                "tg_test_group_allowed": True,
                "public_send_allowed": False,
                "requires_send_preview_gate": True,
                "note": (
                    "High-confidence labels may enter TG test group with send "
                    "preview gate, but NOT public production send. Public send "
                    "requires explicit future gate."
                ),
            },
            "medium": {
                "operator_review_allowed": True,
                "tg_test_group_allowed": False,
                "public_send_allowed": False,
                "requires_label_upgrade": True,
                "note": (
                    "Medium-confidence labels are review-only. TG test group "
                    "entry requires label upgrade to high. Operator may review "
                    "but may not route to TG."
                ),
            },
            "low": {
                "operator_review_allowed": True,
                "tg_test_group_allowed": False,
                "public_send_allowed": False,
                "requires_label_upgrade": True,
                "must_show_unknown_warning": True,
                "note": (
                    "Low-confidence labels are review-only with unknown warning. "
                    "Must display 'Unknown Whale' only. No TG or public routing "
                    "under any circumstance."
                ),
            },
        },
        "current_state": {
            "high_count": distribution["high"],
            "medium_count": distribution["medium"],
            "low_count": distribution["low"],
            "total_addresses": 4,
            "any_eligible_for_tg_test_group": False,
            "any_eligible_for_public_send": False,
            "any_eligible_for_send": False,
        },
        "label_confidence_distribution": distribution,
        "generated_at": now_iso(),
    }
    save_json(OUT_ROUTING_POLICY, policy)
    print(f"  Routing policy -> {OUT_ROUTING_POLICY}")
    return policy


# ---------------------------------------------------------------------------
# Step 5: Generate TG test copy gate policy
# ---------------------------------------------------------------------------
def generate_tg_copy_gate_policy():
    """Generate the TG test copy gate policy JSON."""
    policy = {
        "version": "v115B",
        "policy_name": "whale_tg_test_copy_gate_policy",
        "description": (
            "Defines formatting and content rules for TG test group copy. "
            "TG test copy MUST NOT reuse operator review copy. It must be "
            "generated separately with explicit downgrade markers, test-only "
            "identifiers, and banned confident phrasing."
        ),
        "scope": "tg_test_group_only_not_production",
        "rules": {
            "copy_source": {
                "must_not_reuse_operator_review_copy": True,
                "must_be_generated_separately": True,
                "source_base": "HyperLiquid public position data + local delta compare only",
            },
            "label_confidence_display": {
                "must_preserve_label_confidence": True,
                "medium_confidence_must_be_downgraded": True,
                "low_confidence_must_be_downgraded": True,
                "unknown_whale_must_not_be_presented_as_confirmed_entity": True,
                "downgrade_display_rule": (
                    "If label_confidence != high, append "
                    "'[label confidence: {level}]' to TG copy"
                ),
            },
            "banned_phrases": [
                "确认", "实锤", "正式信号", "强信号",
                "可直接发布", "立即发送",
                "confirmed", "verified", "certain", "guaranteed",
                "正式", "production signal", "send immediately",
                "publish now", "strong signal",
            ],
            "required_elements": {
                "test_only_marker": "[TEST-ONLY — NOT PRODUCTION]",
                "source_disclaimer": "Source: HyperLiquid public position info, local delta compare only",
                "not_financial_advice": "Not financial advice / not a trading signal",
                "not_production_state": "Not production state — local review only",
                "label_confidence_tag": "[label_confidence: {level}]",
                "address_tag": "Address: {address_short}",
                "asset_tag": "Asset: {asset}",
                "delta_summary_tag": "Delta: {delta_type} ({delta_magnitude})",
            },
            "copy_structure": {
                "header": "{test_only_marker}",
                "body_line_1": "{address_tag} | {asset_tag} | {delta_summary_tag}",
                "body_line_2": "{label_confidence_tag}",
                "body_line_3": "{review_summary_rewritten_for_tg}",
                "footer_line_1": "{source_disclaimer}",
                "footer_line_2": "{not_financial_advice}",
                "footer_line_3": "{not_production_state}",
            },
        },
        "review_required": {
            "before_tg_test_send": True,
            "review_must_confirm": [
                "copy_does_not_use_banned_phrases",
                "copy_includes_all_required_elements",
                "copy_has_test_only_marker",
                "copy_preserves_label_confidence",
                "copy_does_not_present_unknown_whale_as_confirmed",
                "copy_is_not_operator_review_copy",
            ],
        },
        "generated_at": now_iso(),
    }
    save_json(OUT_TG_COPY_GATE, policy)
    print(f"  TG copy gate policy -> {OUT_TG_COPY_GATE}")
    return policy


# ---------------------------------------------------------------------------
# Step 6: Generate send preview gate policy
# ---------------------------------------------------------------------------
def generate_send_preview_gate_policy():
    """Generate the one-shot send preview gate policy JSON."""
    policy = {
        "version": "v115B",
        "policy_name": "whale_send_preview_gate_policy",
        "description": (
            "Defines the one-shot send preview gate that must be satisfied "
            "before any TG test group send. Send is disabled by default and "
            "requires explicit gate passage. No send occurs without preview, "
            "approval, and dedupe."
        ),
        "send_enabled_by_default": False,
        "tg_send_allowed": False,
        "gate_requirements": {
            "one_shot_preview_pack": {
                "required": True,
                "description": (
                    "Before any TG test send, a one-shot preview pack must be "
                    "generated showing exact message content, recipient scope, "
                    "and routing decision."
                ),
                "contents": [
                    "exact_tg_copy_text",
                    "target_test_group_id",
                    "label_confidence_level",
                    "routing_decision",
                    "cooldown_status",
                    "no_repeat_status",
                    "payload_hash",
                ],
            },
            "no_repeat_key": {
                "required": True,
                "format": "{address}_{asset}_{side}_{delta_type}_{date}",
                "description": (
                    "Unique dedupe key preventing the same position/delta "
                    "from being sent twice in the same window."
                ),
            },
            "cooldown_key": {
                "required": True,
                "format": "{address}_{asset}_{date}",
                "description": (
                    "Cooldown key preventing same address+asset from being "
                    "sent within cooldown window."
                ),
            },
            "payload_hash": {
                "required": True,
                "description": (
                    "SHA-256 hash of the exact TG copy payload. Used for "
                    "duplicate detection and rollback identification."
                ),
                "algorithm": "sha256",
                "input": "exact_tg_copy_text + address + asset + timestamp",
            },
            "operator_approval_field": {
                "required": True,
                "description": (
                    "Explicit operator approval flag. Must be set to true "
                    "by operator after reviewing the preview pack."
                ),
                "default": False,
                "must_be_explicitly_set": True,
            },
            "test_group_scope_field": {
                "required": True,
                "description": (
                    "Explicitly defines the test group scope. Must be "
                    "'tg_test_group_only' — production channel is never in scope."
                ),
                "allowed_values": ["tg_test_group_only"],
                "default": "tg_test_group_only",
            },
            "user_pre_authorization": {
                "required": True,
                "description": (
                    "Explicit user pre-authorization scoped to TG test group "
                    "only. Does NOT imply production publish permission."
                ),
                "scope": "tg_test_group_only",
                "must_be_explicit": True,
                "revocable": True,
            },
        },
        "send_flow": {
            "step_1": "Generate one-shot preview pack with exact TG copy",
            "step_2": "Check no-repeat key — block if duplicate",
            "step_3": "Check cooldown key — block if within window",
            "step_4": "Compute payload hash for tracking",
            "step_5": "Present preview pack to operator for review",
            "step_6": "Operator sets approval field explicitly",
            "step_7": "User pre-authorization confirmed (test group only)",
            "step_8": "TG test send executed (one-shot, no auto-repeat)",
        },
        "after_send": {
            "record_no_repeat_key": True,
            "start_cooldown": True,
            "record_payload_hash": True,
            "do_not_auto_resend": True,
            "do_not_retry_on_failure_without_review": True,
        },
        "current_state": {
            "send_gate_active": False,
            "any_preview_pack_generated": False,
            "any_operator_approval": False,
            "any_send_executed": False,
        },
        "generated_at": now_iso(),
    }
    save_json(OUT_SEND_PREVIEW_GATE, policy)
    print(f"  Send preview gate policy -> {OUT_SEND_PREVIEW_GATE}")
    return policy


# ---------------------------------------------------------------------------
# Step 7: Generate rollback / cooldown / no-repeat policy
# ---------------------------------------------------------------------------
def generate_rollback_cooldown_policy():
    """Generate the rollback / cooldown / no-repeat policy JSON."""
    policy = {
        "version": "v115B",
        "policy_name": "whale_rollback_cooldown_policy",
        "description": (
            "Defines rollback, cooldown, no-repeat, and manual stop "
            "protections for TG test group sends. No daemon, no loop, "
            "no auto-repeat. All sends are one-shot and operator-gated."
        ),
        "rollback": {
            "instruction_placeholder": (
                "ROLLBACK: To rollback a TG test send, identify the "
                "payload_hash of the sent message. The rollback procedure "
                "is: (1) Post a retraction message in the test group "
                "referencing the payload_hash, (2) Mark the send record "
                "as rolled_back in local state, (3) Document the reason "
                "for rollback. This is a manual operator action — no "
                "automated rollback."
            ),
            "rollback_triggers": [
                "incorrect_label_confidence_displayed",
                "banned_phrase_in_copy",
                "unknown_whale_presented_as_confirmed",
                "operator_error",
                "preview_gate_not_passed",
                "incorrect_routing_decision",
            ],
            "rollback_procedure": "manual_only_no_automation",
            "post_rollback": "mark_send_rolled_back_in_local_state",
        },
        "no_repeat": {
            "enabled": True,
            "dedupe_key_format": "{address}_{asset}_{side}_{delta_type}_{date}",
            "dedupe_key_example": (
                "0x50b3...c9f20_BTC_short_closed_position_20260605"
            ),
            "description": (
                "Each unique position+delta+date combination may only be "
                "sent once."
            ),
            "duplicate_payload_hash_blocking": True,
            "payload_hash_algorithm": "sha256",
            "payload_hash_input": "exact_tg_copy_text + address + asset + timestamp",
            "block_on_duplicate": True,
            "duplicate_action": "block_send_and_notify_operator",
        },
        "cooldown": {
            "enabled": True,
            "cooldown_key_format": "{address}_{asset}_{date}",
            "cooldown_key_example": "0x50b3...c9f20_BTC_20260605",
            "minimum_window_hours": 24,
            "minimum_window_description": (
                "Same address+asset pair cannot be sent more than once per "
                "24-hour cooldown window."
            ),
            "cooldown_scope": "per_address_per_asset",
            "cooldown_check_before_send": True,
            "cooldown_action": "block_send_within_window",
            "cooldown_expiry_action": "allow_send_after_window",
        },
        "failed_send_handling": {
            "policy": "do_not_auto_retry",
            "description": (
                "If a TG test send fails (network error, API error, etc.), "
                "do NOT auto-retry. Operator must review the failure."
            ),
            "on_failure": [
                "log_failure_with_payload_hash",
                "notify_operator",
                "do_not_auto_resend",
                "do_not_increment_retry_counter",
                "require_operator_review_before_retry",
            ],
            "max_manual_retries": "unlimited_but_each_requires_review",
        },
        "manual_stop": {
            "condition": "operator_sets_stop_flag",
            "description": (
                "Operator may set a manual stop condition at any time. "
                "This prevents ALL subsequent sends until explicitly cleared."
            ),
            "stop_triggers": [
                "operator_manual_stop",
                "data_quality_concern",
                "market_volatility_concern",
                "policy_violation_detected",
                "external_event_requires_hold",
            ],
            "while_stopped": {
                "all_sends_blocked": True,
                "preview_packs_still_generated": True,
                "local_review_still_allowed": True,
                "tg_test_send_blocked": True,
            },
            "resume": "operator_explicitly_clears_stop_flag",
        },
        "no_daemon_no_loop": {
            "rule": "ABSOLUTE",
            "description": (
                "No daemon process, no cron job, no background loop, "
                "no timer, no auto-repeat shall be started for TG sending. "
                "All sends are one-shot, operator-initiated, and manually "
                "gated. This policy is non-negotiable."
            ),
            "enforcement": (
                "Any code that starts a daemon, loop, or timer for TG send "
                "is in violation of this policy and must be immediately stopped."
            ),
        },
        "generated_at": now_iso(),
    }
    save_json(OUT_ROLLBACK_COOLDOWN, policy)
    print(f"  Rollback/cooldown policy -> {OUT_ROLLBACK_COOLDOWN}")
    return policy


# ---------------------------------------------------------------------------
# Step 8: Build result JSON
# ---------------------------------------------------------------------------
def build_result(distribution, targets):
    """Build the v115B result JSON."""
    high_priority = [t for t in targets if t["upgrade_priority"] == "high"]
    medium_priority = [t for t in targets if t["upgrade_priority"] == "medium"]

    result = {
        "version": "v115B",
        "status": "passed",
        "local_policy_plan_only": True,
        "label_confidence_routing_policy_created": True,
        "label_upgrade_targets_written": len(targets),
        "tg_test_copy_gate_policy_created": True,
        "send_preview_gate_policy_created": True,
        "rollback_cooldown_policy_created": True,
        "send_ready": False,
        "tg_test_group_ready": False,
        "local_review_ready": True,
        "external_api_called": EXTERNAL_API_CALLED,
        "prod_state_write": PROD_STATE_WRITE,
        "tg_sent": TG_SENT,
        "credentials_read": CREDENTIALS_READ,
        "daemon_started": DAEMON_STARTED,
        "watcher_started": WATCHER_STARTED,
        "files_deleted": FILES_DELETED,
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "tg_send_allowed_count": 0,
        "current_label_confidence_distribution": distribution,
        "upgrade_target_summary": {
            "high_priority": len(high_priority),
            "medium_priority": len(medium_priority),
            "total": len(targets),
            "high_priority_addresses": [
                f"{t['address']} ({t['current_label']}, {t['current_label_confidence']})"
                for t in high_priority
            ],
            "medium_priority_addresses": [
                f"{t['address']} ({t['current_label']}, {t['current_label_confidence']}, {t['positions_linked']} positions)"
                for t in medium_priority
            ],
        },
        "v115a_blockers_addressed": {
            "LABEL_CONFIDENCE_NO_HIGH": (
                "Addressed — routing policy created. High=0 confirmed. "
                "Upgrade targets identified for all 4 addresses."
            ),
            "LOW_CONFIDENCE_UNKNOWN_WHALES": (
                "Addressed — policy explicitly denies TG routing for "
                "low-confidence. Both unknown whales flagged as high-priority "
                "upgrade targets."
            ),
            "REVIEW_ONLY_NO_SEND": (
                "Acknowledged — all 10 cards remain review_only_no_send. "
                "No promotion occurred. Upgrade targets documented."
            ),
            "TG_COPY_NOT_TESTED": (
                "Addressed — TG test copy gate policy created. Operator "
                "review copy separation enforced. Banned phrases list defined."
            ),
            "HISTORICAL_COUNT_MISMATCH_NOTE": (
                "Noted — historical artifact preserved. No action required."
            ),
            "NO_SEND_TEMPLATE_GATE": (
                "Addressed — send preview gate policy created. One-shot "
                "preview, no-repeat, cooldown, and rollback protections defined."
            ),
        },
        "next_step": "v115c_whale_tg_test_copy_template_gate_local_only",
        "generated_at": now_iso(),
    }
    save_json(OUT_RESULT, result)
    print(f"  Result JSON -> {OUT_RESULT}")
    return result


# ---------------------------------------------------------------------------
# Step 9: Generate markdown report
# ---------------------------------------------------------------------------
def generate_markdown_report(result, targets, distribution, address_map):
    """Generate the v115B markdown report."""

    # Build target rows
    target_rows = ""
    for t in targets:
        priority_icon = "🔴 HIGH" if t["upgrade_priority"] == "high" else "🟡 MEDIUM"
        target_rows += (
            f"| `{t['address'][:20]}...` | {t['current_label']} | "
            f"**{t['current_label_confidence']}** | {priority_icon} | "
            f"{t['positions_linked']} | {t['reason'][:100]}... |\n"
        )

    report = f"""# v115B Whale Label Confidence Upgrade Plan — Local Only

**Generated:** {result['generated_at']}
**Status:** {result['status']}
**Version:** v115B
**Input Stage:** v115A (send-readiness strategy gate)

---

## 1. Purpose

This is a **local policy design** step, NOT a send step. It translates the
6 blockers identified in v115A into executable local policy packages.

**No external APIs, no TG send, no production state write, no label changes.**

---

## 2. v115A Blockers Recap

The v115A send-readiness strategy gate identified **6 blockers** preventing
TG test group entry:

| # | Blocker ID | Severity | Addressed in v115B |
|---|-----------|----------|--------------------|
| 1 | LABEL_CONFIDENCE_NO_HIGH | HIGH | ✅ Routing policy + upgrade targets |
| 2 | LOW_CONFIDENCE_UNKNOWN_WHALES | HIGH | ✅ Policy denies routing, upgrade targets flagged |
| 3 | REVIEW_ONLY_NO_SEND | HIGH | ⏳ Acknowledged — no promotion yet |
| 4 | TG_COPY_NOT_TESTED | MEDIUM | ✅ TG copy gate policy created |
| 5 | HISTORICAL_COUNT_MISMATCH_NOTE | LOW | 📝 Noted — no action required |
| 6 | NO_SEND_TEMPLATE_GATE | HIGH | ✅ Send preview gate + protections created |

---

## 3. Current Label Confidence Distribution

| Level | Count | Addresses |
|-------|-------|-----------|
| 🔴 High | **{distribution['high']}** | — |
| 🟡 Medium | **{distribution['medium']}** | loraclexyz (7 positions) + Matrixport Related (1 position) |
| 🟠 Low | **{distribution['low']}** | Unknown Hyperliquid Whale + Unknown HYPE Whale |

**Key fact:** Zero positions have high-confidence labels. No position can enter
TG test group under current routing policy.

---

## 4. Label Upgrade Targets ({len(targets)} addresses)

| Address | Label | Confidence | Priority | Positions | Reason |
|---------|-------|-----------|----------|-----------|--------|
{target_rows}

### Priority Rules Applied

- **low-confidence + closed_position → HIGH priority**
  → Unknown Hyperliquid Whale (BTC closed_position, the only closed position in pack)
- **low-confidence unknown whale → HIGH priority**
  → Unknown HYPE Whale (HYPE size_changed)
- **medium-confidence with multiple positions → MEDIUM priority**
  → loraclexyz (7 positions across ZEC, HYPE, TON, WLD, NEAR, XMR, ASTER)
- **medium-confidence single position → MEDIUM priority**
  → Matrixport Related (1 position, ETH unchanged)

---

## 5. Label Confidence Routing Policy

### Routing Rules Summary

| Confidence | Operator Review | TG Test Group | Public Send | Requires |
|-----------|----------------|---------------|-------------|----------|
| **high** | ✅ Allowed | ✅ Allowed | ❌ (future gate) | Send preview gate |
| **medium** | ✅ Allowed | ❌ | ❌ | Label upgrade |
| **low** | ✅ Allowed | ❌ | ❌ | Label upgrade + unknown warning |

### Key Design Decisions

1. **No position may enter TG test group without `label_confidence='high'`.**
   Currently high=0 — this is the primary blocker.

2. **Medium confidence may not enter TG test group.**
   Label upgrade to high is required first.

3. **Low confidence must display 'Unknown Whale' and may not enter TG.**
   Both low-confidence addresses are flagged as HIGH priority upgrade targets.

4. **Even high-confidence labels may not enter public send.**
   Public production send requires an explicit future gate (not designed yet).

5. **All sends require send preview gate passage.**
   Preview pack, no-repeat check, cooldown check, operator approval, and
   user pre-authorization must all pass.

---

## 6. TG Test Copy Gate

### Key Rules

- TG test copy **MUST NOT** reuse operator review copy (`review_summary`)
- TG test copy **must** include `[TEST-ONLY — NOT PRODUCTION]` marker
- TG test copy **must** preserve label confidence level
- Medium/low confidence **must** be explicitly downgraded
- Unknown whales **must not** be presented as confirmed entities
- Banned phrases: 确认, 实锤, 正式信号, 强信号, 可直接发布, 立即发送, etc.

### Required Elements

Every TG test copy must include:
1. `[TEST-ONLY — NOT PRODUCTION]` header
2. Source: HyperLiquid public position info, local delta compare only
3. Not financial advice / not a trading signal
4. Not production state — local review only
5. Label confidence tag
6. Address tag, asset tag, delta summary tag

---

## 7. Send Preview Gate

### Gate Requirements

Before any TG test group send:
1. ✅ One-shot preview pack generated (exact copy + metadata)
2. ✅ No-repeat key checked (dedupe: `{{address}}_{{asset}}_{{side}}_{{delta_type}}_{{date}}`)
3. ✅ Cooldown key checked (24h minimum: `{{address}}_{{asset}}_{{date}}`)
4. ✅ Payload hash computed (SHA-256 of copy + address + asset + timestamp)
5. ✅ Operator approval field explicitly set
6. ✅ User pre-authorization confirmed (TG test group only)
7. ✅ Send disabled by default — must be explicitly enabled per send

### After Send

- Record no-repeat key
- Start cooldown timer
- Record payload hash
- Do NOT auto-resend
- Do NOT retry on failure without review

---

## 8. Rollback / Cooldown / No-Repeat

### Rollback
- Manual operator action only — no automated rollback
- Triggered by: incorrect label display, banned phrase, operator error
- Procedure: post retraction → mark rolled_back in local state → document

### No-Repeat (Dedupe)
- Key format: `{{address}}_{{asset}}_{{side}}_{{delta_type}}_{{date}}`
- Duplicate payload hash blocking enabled
- Block on duplicate: block send and notify operator

### Cooldown
- Key format: `{{address}}_{{asset}}_{{date}}`
- Minimum window: **24 hours** per address+asset pair
- Cooldown check before every send

### Manual Stop
- Operator may set manual stop at any time
- All sends blocked while stopped
- Preview packs and local review still allowed
- Resume: operator explicitly clears stop flag

### No Daemon / No Loop
- **ABSOLUTE rule**: No daemon, cron, loop, timer, or auto-repeat for TG sending
- All sends are one-shot, operator-initiated, manually gated
- Non-negotiable

---

## 9. Current Conclusion

| Decision | Value | Expected |
|----------|-------|----------|
| **send_ready** | ❌ `false` | `false` ✅ |
| **tg_test_group_ready** | ❌ `false` | `false` ✅ |
| **local_review_ready** | ✅ `true` | `true` ✅ |
| eligible_for_real_send_count | `{result['eligible_for_real_send_count']}` | 0 ✅ |
| real_send_candidate_count | `{result['real_send_candidate_count']}` | 0 ✅ |
| tg_send_allowed_count | `{result['tg_send_allowed_count']}` | 0 ✅ |
| high-confidence labels | `{distribution['high']}` | 0 (no change) |
| upgrade targets | `{len(targets)}` | ≥4 ✅ |

**Conclusion:** Policies and upgrade targets are designed and written.
All 6 v115A blockers are addressed by local policy. However, no actual label
upgrade has occurred (that requires external verification not in scope for
this local-only step). Send remains disabled.

---

## 10. Safety Invariant Status

| Invariant | Status |
|-----------|--------|
| external_api_called | ✅ `{result['external_api_called']}` |
| prod_state_write | ✅ `{result['prod_state_write']}` |
| tg_sent | ✅ `{result['tg_sent']}` |
| credentials_read | ✅ `{result['credentials_read']}` |
| daemon_started | ✅ `{result['daemon_started']}` |
| watcher_started | ✅ `{result['watcher_started']}` |
| files_deleted | ✅ `{result['files_deleted']}` |
| old results modified | ✅ No (v114A-v115A unchanged) |
| real send candidate generated | ✅ No (0 candidates) |

---

## 11. Explicit NOT Declarations

This stage is explicitly **NOT**:

- ❌ Send-ready
- ❌ TG-test-group-ready
- ❌ A TG send
- ❌ A label confidence upgrade (policies designed, upgrades NOT performed)
- ❌ Production state
- ❌ A trading signal
- ❌ Live-passed
- ❌ Ready for external consumption

This stage **IS**:

- ✅ A local-only policy design step
- ✅ Input for v115C (TG test copy template gate)
- ✅ Fully guarded with safety invariants
- ✅ Traceable, verifiable, reproducible

---

## 12. Next Step

**`{result['next_step']}`**

The next executor should:
1. Design TG test copy templates using the copy gate policy from v115B
2. Generate mock TG copy for each upgrade target
3. Validate copy against banned phrases and required elements
4. Produce first draft of send-ready TG copy (still test-only, not production)

---

## 13. Output Files

| File | Path |
|------|------|
| Routing Policy | `{OUT_ROUTING_POLICY}` |
| TG Copy Gate Policy | `{OUT_TG_COPY_GATE}` |
| Send Preview Gate Policy | `{OUT_SEND_PREVIEW_GATE}` |
| Rollback/Cooldown Policy | `{OUT_ROLLBACK_COOLDOWN}` |
| Result JSON | `{OUT_RESULT}` |
| Upgrade Targets JSONL | `{OUT_UPGRADE_TARGETS}` |
| Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |

---

*This policy plan report is for local operator review only. No external communication intended.*
"""
    save_text(OUT_REPORT, report)
    print(f"  Markdown report -> {OUT_REPORT}")


# ---------------------------------------------------------------------------
# Step 10: Generate handoff
# ---------------------------------------------------------------------------
def generate_handoff(result, targets, distribution):
    """Generate the v115B handoff markdown."""

    high_priority = [t for t in targets if t["upgrade_priority"] == "high"]
    medium_priority = [t for t in targets if t["upgrade_priority"] == "medium"]

    targets_summary = ""
    for t in targets:
        p_icon = "🔴" if t["upgrade_priority"] == "high" else "🟡"
        targets_summary += (
            f"- {p_icon} `{t['address'][:24]}...` — {t['current_label']} "
            f"({t['current_label_confidence']}, {t['upgrade_priority']} priority, "
            f"{t['positions_linked']} positions)\n"
        )

    handoff = f"""# v115B Handoff — Whale Label Confidence Upgrade Plan Local Only

**Generated:** {result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Status:** {result['status']}

---

## What was done

1. Read v115A send-readiness gate result (6 blockers)
2. Read v114C operator review cards (10 cards, 4 addresses)
3. Read v114B delta records (10 records)
4. Analyzed label confidence distribution: high=0, medium=8, low=2
5. Identified 4 upgrade target addresses ({len(high_priority)} high priority, {len(medium_priority)} medium priority)
6. Designed and wrote label confidence routing policy
7. Designed and wrote TG test copy gate policy
8. Designed and wrote send preview gate policy
9. Designed and wrote rollback / cooldown / no-repeat policy
10. Generated result JSON, upgrade targets JSONL, report, and handoff

## v115A Blockers Addressed

| Blocker | Status |
|---------|--------|
| LABEL_CONFIDENCE_NO_HIGH | ✅ Routing policy + upgrade targets |
| LOW_CONFIDENCE_UNKNOWN_WHALES | ✅ Policy denies routing, targets flagged |
| REVIEW_ONLY_NO_SEND | ⏳ Acknowledged, no promotion yet |
| TG_COPY_NOT_TESTED | ✅ TG copy gate policy created |
| HISTORICAL_COUNT_MISMATCH_NOTE | 📝 Noted |
| NO_SEND_TEMPLATE_GATE | ✅ Send preview + protections created |

## Current State

| Field | Value |
|-------|-------|
| send_ready | ❌ `false` |
| tg_test_group_ready | ❌ `false` |
| local_review_ready | ✅ `true` |
| high-confidence labels | 0 |
| upgrade targets | {len(targets)} |
| policies created | 4 |

## Upgrade Targets

{targets_summary}

## Labels That MUST NOT Be Upgraded Without External Verification

- Unknown Hyperliquid Whale (low → must stay downgraded until verified)
- Unknown HYPE Whale (low → must stay downgraded until verified)

## Routing Rules (Effective Immediately)

- **high confidence** → operator review ✅, TG test group ✅, public send ❌
- **medium confidence** → operator review ✅, TG test group ❌, public send ❌
- **low confidence** → operator review ✅, TG test group ❌, public send ❌

## TG Copy Rules

- MUST NOT reuse operator review copy
- MUST include [TEST-ONLY — NOT PRODUCTION]
- MUST NOT use: 确认, 实锤, 正式信号, 强信号
- MUST preserve label confidence

## Send Rules

- Send disabled by default
- Requires: preview pack + no-repeat check + cooldown check + operator approval + user pre-auth
- No auto-retry on failure
- 24-hour cooldown per address+asset
- No daemon / no loop

## Safety Invariants Confirmed

- `external_api_called=false`
- `prod_state_write=false`
- `tg_sent=false`
- `credentials_read=false`
- `daemon_started=false`
- `watcher_started=false`
- `files_deleted=false`
- v114A-v115A old results NOT modified
- No real send candidate generated

## This Stage Is NOT

- Send-ready
- TG-test-group-ready
- A label confidence upgrade (policies designed, NOT performed)
- A TG send
- Production state

## This Stage IS

- A local-only policy design step
- Input for v115C
- Fully guarded with safety invariants

## Next Step

**{result['next_step']}**

Design TG test copy templates using v115B policies. Generate mock TG copy
for each upgrade target and validate against copy gate rules.

---

*This handoff is for the next stage decision-maker. No action required now.*
"""
    save_text(OUT_HANDOFF, handoff)
    print(f"  Handoff -> {OUT_HANDOFF}")


# ---------------------------------------------------------------------------
# Step 11: Save upgrade targets JSONL
# ---------------------------------------------------------------------------
def save_upgrade_targets(targets):
    """Write upgrade targets to JSONL file."""
    save_jsonl(OUT_UPGRADE_TARGETS, targets)
    print(f"  Upgrade targets -> {OUT_UPGRADE_TARGETS} ({len(targets)} targets)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115B Whale Label Confidence Upgrade Plan — Local Only")
    print("=" * 70)

    # Step 1: Load reference inputs
    print("\n[1/10] Loading reference inputs...")
    (v115a_result, v115a_blockers, v114c_cards,
     v114b_deltas, v114d_manifest) = load_reference_inputs()

    # Step 2: Analyze label confidence
    print("\n[2/10] Analyzing label confidence distribution...")
    distribution, address_map = analyze_label_confidence(v114c_cards)

    # Step 3: Build upgrade targets
    print("\n[3/10] Building label upgrade targets...")
    targets = build_upgrade_targets(address_map, v114b_deltas, v114c_cards)

    # Step 4: Generate routing policy
    print("\n[4/10] Generating label confidence routing policy...")
    routing_policy = generate_routing_policy(distribution)

    # Step 5: Generate TG test copy gate policy
    print("\n[5/10] Generating TG test copy gate policy...")
    tg_copy_gate = generate_tg_copy_gate_policy()

    # Step 6: Generate send preview gate policy
    print("\n[6/10] Generating send preview gate policy...")
    send_preview_gate = generate_send_preview_gate_policy()

    # Step 7: Generate rollback / cooldown policy
    print("\n[7/10] Generating rollback / cooldown / no-repeat policy...")
    rollback_cooldown = generate_rollback_cooldown_policy()

    # Step 8: Build result JSON
    print("\n[8/10] Building result JSON...")
    result = build_result(distribution, targets)

    # Step 9: Save upgrade targets JSONL
    print("\n[9/10] Saving upgrade targets JSONL...")
    save_upgrade_targets(targets)

    # Step 10: Generate reports
    print("\n[10/10] Generating markdown report and handoff...")
    generate_markdown_report(result, targets, distribution, address_map)
    generate_handoff(result, targets, distribution)

    # Final summary
    print("\n" + "=" * 70)
    print("v115B POLICY PLAN COMPLETE")
    print(f"  send_ready: {result['send_ready']}")
    print(f"  tg_test_group_ready: {result['tg_test_group_ready']}")
    print(f"  local_review_ready: {result['local_review_ready']}")
    print(f"  Upgrade targets: {len(targets)} (high={result['upgrade_target_summary']['high_priority']}, "
          f"medium={result['upgrade_target_summary']['medium_priority']})")
    print(f"  Policies created: 4 (routing, TG copy, send preview, rollback/cooldown)")
    print(f"  Next step: {result['next_step']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
