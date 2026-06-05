"""Market Radar v1.12-J — Eligible Signal Pack + Proposed State Dry-run

Builds a standardized eligible signal pack from v112h envelopes and v112i gate
decisions, then generates a proposed state dry-run — all local, no external APIs,
no real TG send, no live state writes.

Pipeline:
  adapter output -> signal envelope (v112h) -> dedupe/cooldown gate (v112i) ->
  eligible signal pack (v112j) -> proposed state dry-run

Functions:
  load_envelopes_jsonl(path)
  load_gate_decisions_jsonl(path)
  join_envelopes_with_decisions(envelopes, decisions)
  build_eligible_signal_record(envelope, decision, rank_score)
  build_blocked_signal_record(decision)
  rank_eligible_signals(eligible_records)
  build_proposed_signal_state(eligible_records, prior_state, run_ts)
  scan_pack_leaks(record, kind)
  write_jsonl(records, path)
  write_report(result, eligible, blocked, proposed_state, path)

Constraints:
  - No external API calls, no real TG send, no daemon/loop/cron
  - No token/key/secret read or print
  - Dry-run only — does NOT write to live state
  - Does NOT overwrite prior state fixture

Usage:
    from scripts.market_radar_eligible_signal_pack_v112j import (
        load_envelopes_jsonl, load_gate_decisions_jsonl,
        join_envelopes_with_decisions, build_eligible_signal_record,
        build_blocked_signal_record, rank_eligible_signals,
        build_proposed_signal_state, scan_pack_leaks,
        write_jsonl, write_report,
        PACK_VERSION, SCHEMA_VERSION,
    )
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PACK_VERSION = "v1.12-J"
SCHEMA_VERSION = "1.0.0"

CN_TZ = timezone(timedelta(hours=8))

# ── Cooldown Policy (same as v112i) ────────────────────────────────────────────────

COOLDOWN_POLICY: dict[str, int] = {
    "price_oi_volume_anomaly": 60,
    "whale_position_alert": 90,
    "liquidation_pressure": 30,
    "multi_asset_market_sync": 45,
    "news_event_market_impact": 120,
}

# ── Forbidden Terms for Leak Scan ──────────────────────────────────────────────────

FORBIDDEN_DEBUG_TERMS = [
    "debug", "internal", "trace", "fixture",
]

FORBIDDEN_SECRET_TERMS = [
    "secret", "token", "api_key", "chat_id", "password",
]

FORBIDDEN_PATH_TERMS = [
    "C:\\Users\\PC", "ai_relay_desk",
]

WALLET_ADDRESS_PATTERN = re.compile(r'0x[a-fA-F0-9]{40}')


# ══════════════════════════════════════════════════════════════════════════════════════
# Data Loading
# ══════════════════════════════════════════════════════════════════════════════════════

def load_envelopes_jsonl(path: str | Path) -> list[dict]:
    """Load signal envelopes from a JSONL file.

    Each line is a JSON object representing a unified signal envelope.
    Returns a list of envelope dicts. Empty lines are skipped.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of envelope dicts.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Envelope JSONL not found: {path}")

    envelopes: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                envelopes.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSONL line: {e}")
    return envelopes


def load_gate_decisions_jsonl(path: str | Path) -> list[dict]:
    """Load gate decisions from a JSONL file.

    Each line is a JSON object representing a gate decision from v112i.
    Returns a list of gate decision dicts. Empty lines are skipped.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of gate decision dicts.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Gate decisions JSONL not found: {path}")

    decisions: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                decisions.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSONL line: {e}")
    return decisions


def load_prior_signal_state(path: str | Path) -> list[dict]:
    """Load prior signal state from a JSON file.

    Args:
        path: Path to the prior state JSON file.

    Returns:
        List of prior state entry dicts.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Prior signal state not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("entries", [])
    return []


# ══════════════════════════════════════════════════════════════════════════════════════
# Join Envelopes with Decisions
# ══════════════════════════════════════════════════════════════════════════════════════

def join_envelopes_with_decisions(
    envelopes: list[dict],
    decisions: list[dict],
) -> list[dict]:
    """Join envelopes with their corresponding gate decisions by signal_id.

    Each envelope is matched with its gate decision. The resulting join records
    contain both the full envelope and the gate decision data.

    Args:
        envelopes: List of signal envelope dicts.
        decisions: List of gate decision dicts.

    Returns:
        List of joined dicts, each with 'envelope' and 'decision' keys.
        Signals present only in envelopes but not in decisions are included
        with decision=None. Signals only in decisions but not in envelopes
        are logged as warnings.
    """
    decision_map: dict[str, dict] = {}
    for d in decisions:
        sid = d.get("signal_id", "")
        if sid:
            decision_map[sid] = d

    joined: list[dict] = []
    seen_decision_ids = set()

    for env in envelopes:
        sid = env.get("signal_id", "")
        decision = decision_map.get(sid)
        joined.append({"envelope": env, "decision": decision})
        if decision:
            seen_decision_ids.add(sid)

    # Check for orphan decisions
    for d in decisions:
        sid = d.get("signal_id", "")
        if sid and sid not in seen_decision_ids:
            print(f"  [WARN] Gate decision has no matching envelope: {sid}")

    return joined


# ══════════════════════════════════════════════════════════════════════════════════════
# Ranking
# ══════════════════════════════════════════════════════════════════════════════════════

def _compute_rank_score(severity_score: float, confidence_score: float) -> float:
    """Compute rank score using the v112j deterministic formula.

    rank_score = severity_score * 0.7 + confidence_score * 100 * 0.3

    Args:
        severity_score: 0-100 severity score.
        confidence_score: 0-1 confidence score.

    Returns:
        Rank score (float).
    """
    sev = float(severity_score)
    conf = float(confidence_score)
    return round(sev * 0.7 + conf * 100.0 * 0.3, 2)


def rank_eligible_signals(eligible_records: list[dict]) -> list[dict]:
    """Rank eligible signals by deterministic local rules.

    Sort order:
      1. rank_score descending
      2. severity_score descending
      3. observed_at newest to oldest

    Args:
        eligible_records: List of eligible signal record dicts.

    Returns:
        Sorted list of eligible signal record dicts, each with rank
        position added as 'rank_position' (1-based).
    """
    def sort_key(rec: dict) -> tuple:
        rank_score = float(rec.get("rank_score", 0))
        severity_score = float(rec.get("severity_score", 0))
        observed_at = str(rec.get("observed_at", ""))
        # Negate rank_score and severity_score for descending
        # observed_at: newer timestamps sort first (lexicographic works for ISO)
        return (-rank_score, -severity_score, _reverse_ts(observed_at))

    sorted_records = sorted(eligible_records, key=sort_key)

    for i, rec in enumerate(sorted_records):
        rec["rank_position"] = i + 1

    return sorted_records


def _reverse_ts(ts: str) -> str:
    """Reverse an ISO timestamp so newer sorts first lexicographically."""
    # "2026-06-04T20:22:00+08:00" -> flip chars
    ts_clean = ts.replace(":", "").replace("-", "").replace("+", "").replace("T", "")
    # Reverse so that larger (newer) timestamps sort first when negated
    return ts_clean


# ══════════════════════════════════════════════════════════════════════════════════════
# Eligible Signal Record Builder
# ══════════════════════════════════════════════════════════════════════════════════════

def build_eligible_signal_record(
    envelope: dict,
    decision: dict,
    rank_score: float | None = None,
) -> dict:
    """Build an eligible signal record from an envelope and its gate decision.

    Args:
        envelope: Signal envelope dict.
        decision: Gate decision dict (must have gate_status="pass").
        rank_score: Pre-computed rank_score. Computed if None.

    Returns:
        Eligible signal record dict with all required fields.
    """
    severity = float(envelope.get("severity_score", 0))
    confidence = float(envelope.get("confidence_score", 0))
    if rank_score is None:
        rank_score = _compute_rank_score(severity, confidence)

    card_type = str(envelope.get("card_type", ""))
    primary_assets = envelope.get("primary_assets", [])
    direction = str(envelope.get("direction", ""))
    signal_id = str(envelope.get("signal_id", ""))
    dedupe_key = str(envelope.get("dedupe_key", ""))
    cooldown_key = str(envelope.get("cooldown_key", ""))
    payload_hash = str(envelope.get("payload_hash", ""))
    observed_at = str(envelope.get("observed_at", ""))
    public_card = str(envelope.get("public_card", ""))
    gate_status = str(decision.get("gate_status", "pass")) if decision else "unknown"

    # ── Send policy ──────────────────────────────────────────────────────────
    send_policy = {
        "dry_run_only": True,
        "real_tg_sent": False,
        "requires_manual_review": True,
        "production_send_allowed": False,
    }

    # ── Safety flags ─────────────────────────────────────────────────────────
    safety_flags = {
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
    }

    # ── State update preview ─────────────────────────────────────────────────
    state_update_preview = {
        "action": "proposed_upsert",
        "dedupe_key": dedupe_key,
        "cooldown_key": cooldown_key,
        "payload_hash": payload_hash,
        "card_type": card_type,
        "primary_assets": primary_assets,
        "direction": direction,
    }

    record = {
        "pack_schema_version": SCHEMA_VERSION,
        "pack_version": PACK_VERSION,
        "signal_id": signal_id,
        "card_type": card_type,
        "primary_assets": primary_assets,
        "direction": direction,
        "severity_score": round(severity, 1),
        "confidence_score": round(confidence, 4),
        "rank_score": rank_score,
        "rank_position": 0,  # filled by rank_eligible_signals
        "dedupe_key": dedupe_key,
        "cooldown_key": cooldown_key,
        "payload_hash": payload_hash,
        "gate_status": gate_status,
        "eligible_for_send": True,
        "observed_at": observed_at,
        "public_card": public_card,
        "send_policy": send_policy,
        "state_update_preview": state_update_preview,
        "safety_flags": safety_flags,
    }

    return record


# ══════════════════════════════════════════════════════════════════════════════════════
# Blocked Signal Record Builder
# ══════════════════════════════════════════════════════════════════════════════════════

def build_blocked_signal_record(decision: dict) -> dict:
    """Build a blocked signal record from a gate decision.

    Args:
        decision: Gate decision dict (must have eligible_for_send=False).

    Returns:
        Blocked signal record dict with all required fields.
    """
    gate_reasons = decision.get("gate_reasons", [])
    if isinstance(gate_reasons, str):
        gate_reasons = [gate_reasons]

    record = {
        "signal_id": str(decision.get("signal_id", "")),
        "card_type": str(decision.get("card_type", "")),
        "primary_assets": decision.get("primary_assets", []),
        "direction": str(decision.get("direction", "")),
        "gate_status": str(decision.get("gate_status", "")),
        "gate_reasons": gate_reasons,
        "dedupe_hit": bool(decision.get("dedupe_hit", False)),
        "cooldown_hit": bool(decision.get("cooldown_hit", False)),
        "eligible_for_send": False,
    }

    return record


# ══════════════════════════════════════════════════════════════════════════════════════
# Proposed State Builder
# ══════════════════════════════════════════════════════════════════════════════════════

def build_proposed_signal_state(
    eligible_records: list[dict],
    prior_state: list[dict],
    run_ts: str | None = None,
) -> dict:
    """Build a proposed next state from eligible signals and prior state.

    This is a DRY-RUN ONLY — it does NOT write to any live state.
    It produces a proposed state JSON that shows what the state WOULD look
    like if all eligible signals were committed.

    The proposed state merges:
      - Prior state entries (kept as-is, not overwritten)
      - New entries for eligible signals (with cooldown_until computed)

    Args:
        eligible_records: List of eligible signal record dicts.
        prior_state: List of prior state entry dicts.
        run_ts: Run timestamp string. Uses current time if None.

    Returns:
        Dict with:
          - version: str
          - description: str
          - generated_at: str
          - dry_run_only: bool
          - prior_state_entries_kept: int
          - new_proposed_entries: int
          - total_entries: int
          - entries: list[dict]
    """
    if run_ts is None:
        run_ts = china_stamp()

    # Parse run_ts for cooldown computation
    now = _parse_timestamp(run_ts)

    # ── Build proposed entries from eligible signals ──────────────────────
    new_entries: list[dict] = []
    seen_dedupe_keys = set()

    for rec in eligible_records:
        dedupe_key = str(rec.get("dedupe_key", ""))
        if not dedupe_key:
            continue
        seen_dedupe_keys.add(dedupe_key)

        card_type = str(rec.get("card_type", ""))
        cooldown_minutes = COOLDOWN_POLICY.get(card_type, 60)
        cooldown_until = now + timedelta(minutes=cooldown_minutes)
        cooldown_until_str = cooldown_until.strftime("%Y-%m-%dT%H:%M:%S+08:00")

        entry = {
            "dedupe_key": dedupe_key,
            "cooldown_key": str(rec.get("cooldown_key", "")),
            "payload_hash": str(rec.get("payload_hash", "")),
            "card_type": card_type,
            "primary_assets": rec.get("primary_assets", []),
            "direction": str(rec.get("direction", "")),
            "last_seen_at": str(rec.get("observed_at", "")),
            "cooldown_until": cooldown_until_str,
            "decision_history": [
                {
                    "status": "pass",
                    "evaluated_at": run_ts,
                    "reason": "proposed state entry from v112j eligible signal pack",
                }
            ],
        }
        new_entries.append(entry)

    # ── Merge with prior state (keep prior entries that aren't replaced) ──
    merged_entries = list(new_entries)
    prior_kept = 0

    for prior_entry in prior_state:
        prior_dedupe = str(prior_entry.get("dedupe_key", ""))
        if prior_dedupe and prior_dedupe in seen_dedupe_keys:
            # This prior entry is being updated by a new eligible signal
            # We keep the new version (already in merged_entries)
            continue
        # Keep prior entry as-is
        merged_entries.append(prior_entry)
        prior_kept += 1

    proposed_state = {
        "version": PACK_VERSION,
        "schema_version": SCHEMA_VERSION,
        "description": (
            "Proposed signal state dry-run from v112j eligible signal pack. "
            "This file is a PROPOSAL ONLY — it does NOT overwrite the live "
            "state or the prior state fixture."
        ),
        "generated_at": run_ts,
        "dry_run_only": True,
        "prior_state_entries_kept": prior_kept,
        "new_proposed_entries": len(new_entries),
        "total_entries": len(merged_entries),
        "entries": merged_entries,
    }

    return proposed_state


# ══════════════════════════════════════════════════════════════════════════════════════
# Leak Scanning
# ══════════════════════════════════════════════════════════════════════════════════════

def scan_pack_leaks(record: dict, kind: str = "eligible") -> dict:
    """Scan a pack record (eligible, blocked, or state entry) for forbidden content.

    Checks for:
      - Debug terms (debug, internal, trace, fixture)
      - Secret terms (secret, token, api_key, chat_id, password)
      - Path leaks (C:\\Users\\PC, ai_relay_desk)
      - Full wallet addresses in public_card

    Args:
        record: A pack record dict.
        kind: Record kind — "eligible", "blocked", or "state".

    Returns:
        Dict with:
          - debug_leak_count: int
          - secret_leak_count: int
          - debug_terms_found: list[str]
          - secret_terms_found: list[str]
          - full_wallet_leak: bool
          - wallet_leak_details: list[str]
          - clean: bool
    """
    # Build text for scanning
    scannable_parts: list[str] = []

    public_card = str(record.get("public_card", ""))
    scannable_parts.append(public_card)

    if kind == "eligible":
        scannable_parts.append(str(record.get("signal_id", "")))
        scannable_parts.append(str(record.get("card_type", "")))
        scannable_parts.append(str(record.get("direction", "")))
        scannable_parts.append(" ".join(str(a) for a in record.get("primary_assets", [])))
        scannable_parts.append(str(record.get("gate_status", "")))
        # Check send_policy and state_update_preview too
        sp = record.get("send_policy", {})
        if isinstance(sp, dict):
            scannable_parts.append(json.dumps(sp, sort_keys=True))
        sup = record.get("state_update_preview", {})
        if isinstance(sup, dict):
            scannable_parts.append(json.dumps(sup, sort_keys=True))
    elif kind == "blocked":
        scannable_parts.append(str(record.get("signal_id", "")))
        scannable_parts.append(str(record.get("card_type", "")))
        scannable_parts.append(str(record.get("direction", "")))
        scannable_parts.append(str(record.get("gate_status", "")))
        scannable_parts.append(" ".join(str(a) for a in record.get("primary_assets", [])))
        scannable_parts.append("; ".join(record.get("gate_reasons", [])))
    elif kind == "state":
        scannable_parts.append(str(record.get("card_type", "")))
        scannable_parts.append(str(record.get("direction", "")))
        scannable_parts.append(" ".join(str(a) for a in record.get("primary_assets", [])))
        # decision_history
        dh = record.get("decision_history", [])
        if isinstance(dh, list):
            scannable_parts.append(json.dumps(dh, sort_keys=True))

    check_text = " ".join(scannable_parts).lower()

    # ── Debug term scan ──────────────────────────────────────────────────────
    debug_found: list[str] = []
    for term in FORBIDDEN_DEBUG_TERMS:
        if term.lower() in check_text:
            debug_found.append(term)

    # ── Secret term scan ─────────────────────────────────────────────────────
    secret_found: list[str] = []
    for term in FORBIDDEN_SECRET_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)
    for term in FORBIDDEN_PATH_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)

    # ── Wallet address scan ──────────────────────────────────────────────────
    wallet_leak_details: list[str] = []
    for part in scannable_parts:
        matches = WALLET_ADDRESS_PATTERN.findall(part)
        wallet_leak_details.extend(matches)
    full_wallet_leak = len(wallet_leak_details) > 0

    debug_found = sorted(set(debug_found))
    secret_found = sorted(set(secret_found))

    debug_leak_count = len(debug_found)
    secret_leak_count = len(secret_found) + (1 if full_wallet_leak else 0)

    clean = debug_leak_count == 0 and secret_leak_count == 0 and not full_wallet_leak

    return {
        "debug_leak_count": debug_leak_count,
        "secret_leak_count": secret_leak_count,
        "debug_terms_found": debug_found,
        "secret_terms_found": secret_found,
        "full_wallet_leak": full_wallet_leak,
        "wallet_leak_details": wallet_leak_details,
        "clean": clean,
    }


def scan_all_pack_leaks(
    eligible_records: list[dict],
    blocked_records: list[dict],
    proposed_state: dict,
) -> dict:
    """Aggregate leak scan across all pack outputs.

    Args:
        eligible_records: List of eligible signal records.
        blocked_records: List of blocked signal records.
        proposed_state: Proposed state dict.

    Returns:
        Aggregated leak scan dict with totals and per-record details.
    """
    total_debug = 0
    total_secret = 0
    any_full_wallet = False
    all_wallet_details: list[str] = []

    for rec in eligible_records:
        result = scan_pack_leaks(rec, kind="eligible")
        total_debug += result["debug_leak_count"]
        total_secret += result["secret_leak_count"]
        if result["full_wallet_leak"]:
            any_full_wallet = True
            all_wallet_details.extend(result["wallet_leak_details"])

    for rec in blocked_records:
        result = scan_pack_leaks(rec, kind="blocked")
        total_debug += result["debug_leak_count"]
        total_secret += result["secret_leak_count"]
        if result["full_wallet_leak"]:
            any_full_wallet = True
            all_wallet_details.extend(result["wallet_leak_details"])

    # Scan proposed state entries
    entries = proposed_state.get("entries", [])
    for entry in entries:
        result = scan_pack_leaks(entry, kind="state")
        total_debug += result["debug_leak_count"]
        total_secret += result["secret_leak_count"]
        if result["full_wallet_leak"]:
            any_full_wallet = True
            all_wallet_details.extend(result["wallet_leak_details"])

    return {
        "debug_leak_count": total_debug,
        "secret_leak_count": total_secret,
        "full_wallet_leak": any_full_wallet,
        "wallet_leak_details": sorted(set(all_wallet_details)),
        "clean": total_debug == 0 and total_secret == 0 and not any_full_wallet,
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Output Writers
# ══════════════════════════════════════════════════════════════════════════════════════

def write_jsonl(records: list[dict], path: str | Path) -> None:
    """Write a list of dicts to a JSONL file.

    Args:
        records: List of record dicts.
        path: Output file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_json(data: dict | list, path: str | Path) -> None:
    """Write a dict or list to a JSON file.

    Args:
        data: Dict or list to write.
        path: Output file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════════════
# Report Writer
# ══════════════════════════════════════════════════════════════════════════════════════

def write_report(
    result: dict,
    eligible_records: list[dict],
    blocked_records: list[dict],
    proposed_state: dict,
    report_path: str | Path,
    handoff_path: str | Path,
    run_ts: str | None = None,
) -> None:
    """Write the markdown report and handoff files.

    Args:
        result: Summary result dict.
        eligible_records: List of eligible signal records.
        blocked_records: List of blocked signal records.
        proposed_state: Proposed state dict.
        report_path: Path for the main report markdown file.
        handoff_path: Path for the handoff markdown file.
        run_ts: Run timestamp string.
    """
    if run_ts is None:
        run_ts = china_stamp()

    # ── Build main report ────────────────────────────────────────────────────
    report_lines = [
        f"# Market Radar v1.12-J — Eligible Signal Pack + State Dry-run",
        "",
        f"**Run timestamp**: {run_ts}",
        f"**Pack version**: {PACK_VERSION}",
        f"**Schema version**: {SCHEMA_VERSION}",
        "",
        "## Summary",
        "",
        f"- Input envelopes: {result.get('input_envelope_count', 0)}",
        f"- Input gate decisions: {result.get('input_decision_count', 0)}",
        f"- Eligible signals: {result.get('eligible_signal_count', 0)}",
        f"- Blocked signals: {result.get('blocked_signal_count', 0)}",
        f"- Proposed state entries: {result.get('proposed_state_entry_count', 0)}",
        f"- Top ranked: `{result.get('top_ranked_signal_id', 'N/A')}` ({result.get('top_ranked_card_type', 'N/A')})",
        "",
        "## Card Type Summary",
        "",
    ]

    card_type_summary = result.get("card_type_summary", {})
    if card_type_summary:
        report_lines.append("| Card Type | Total | Eligible | Blocked |")
        report_lines.append("|-----------|-------|----------|---------|")
        for ct, counts in sorted(card_type_summary.items()):
            report_lines.append(
                f"| {ct} | {counts.get('total', 0)} | {counts.get('eligible', 0)} | {counts.get('blocked', 0)} |"
            )
    report_lines.append("")

    # ── Top eligible signals ─────────────────────────────────────────────────
    report_lines.append("## Top Eligible Signals (by rank)")
    report_lines.append("")
    for rec in eligible_records[:10]:
        rank = rec.get("rank_position", "?")
        sid = rec.get("signal_id", "?")
        ct = rec.get("card_type", "?")
        rank_score = rec.get("rank_score", 0)
        sev = rec.get("severity_score", 0)
        report_lines.append(
            f"1. **#{rank}** `{sid}` — {ct} — rank={rank_score:.1f} sev={sev} dir={rec.get('direction', '?')}"
        )
    report_lines.append("")

    # ── Safety flags ─────────────────────────────────────────────────────────
    report_lines.append("## Safety Flags")
    report_lines.append("")
    report_lines.append(f"- `real_tg_sent`: {result.get('real_tg_sent', False)}")
    report_lines.append(f"- `external_api_called`: {result.get('external_api_called', False)}")
    report_lines.append(f"- `external_ai_called`: {result.get('external_ai_called', False)}")
    report_lines.append(f"- `daemon_started`: {result.get('daemon_started', False)}")
    report_lines.append(f"- `live_ready`: {result.get('live_ready', False)}")
    report_lines.append(f"- `dry_run_only`: {result.get('dry_run_only', True)}")
    report_lines.append(f"- `production_send_allowed`: {result.get('production_send_allowed', False)}")
    report_lines.append("")

    # ── Leak scan ────────────────────────────────────────────────────────────
    report_lines.append("## Leak Scan")
    report_lines.append("")
    report_lines.append(f"- Debug leaks: {result.get('debug_leak_count', 0)}")
    report_lines.append(f"- Secret leaks: {result.get('secret_leak_count', 0)}")
    report_lines.append(f"- Full wallet leak: {result.get('full_wallet_leak', False)}")
    report_lines.append("")

    # ── Output files ─────────────────────────────────────────────────────────
    report_lines.append("## Output Files")
    report_lines.append("")
    report_lines.append("- `results/market_radar_v112j_eligible_signal_pack_result.json`")
    report_lines.append("- `results/market_radar_v112j_eligible_signals.jsonl`")
    report_lines.append("- `results/market_radar_v112j_blocked_signals.jsonl`")
    report_lines.append("- `results/market_radar_v112j_proposed_signal_state.json`")
    report_lines.append("- `runs/market_radar/v112j_eligible_signal_pack.md` (this file)")
    report_lines.append("- `runs/market_radar/v112j_eligible_signal_pack_handoff.md`")
    report_lines.append("")

    report_md = "\n".join(report_lines)

    # ── Build handoff ────────────────────────────────────────────────────────
    handoff_lines = [
        f"# v1.12-J Eligible Signal Pack — Handoff",
        "",
        f"**Run**: {run_ts}",
        f"**Status**: dry-run complete",
        "",
        "## Pipeline Chain",
        "",
        "```",
        "adapter output",
        "  -> v112h signal envelope",
        "  -> v112i dedupe/cooldown gate",
        "  -> v112j eligible signal pack  <-- you are here",
        "  -> proposed state dry-run",
        "```",
        "",
        "## Eligible Signals",
        "",
        f"{result.get('eligible_signal_count', 0)} signals passed the gate and are in the eligible pack.",
        "",
        "## Blocked Signals",
        "",
        f"{result.get('blocked_signal_count', 0)} signals were blocked by dedupe or cooldown.",
        "",
        "## Proposed State",
        "",
        f"The proposed state contains {result.get('proposed_state_entry_count', 0)} new entries.",
        "Prior state entries are preserved — this is a dry-run only.",
        "",
        "## Safety",
        "",
        "- No real TG send",
        "- No external API/AI calls",
        "- No daemon/loop/cron",
        "- No live state writes",
        "- No credential/key/secret exposure",
        "",
        "## Next Steps",
        "",
        "1. Human review of eligible signal pack",
        "2. Manual approval before any real TG send",
        "3. When approved: commit proposed state to live state",
        "",
        "---",
        "",
        f"*Generated by v112j eligible signal pack at {run_ts}*",
    ]

    handoff_md = "\n".join(handoff_lines)

    # Write files
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")

    handoff_path = Path(handoff_path)
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(handoff_md, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════════════

def china_stamp() -> str:
    """Return current time in UTC+8 format string."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _parse_timestamp(ts: str) -> datetime:
    """Parse a timestamp string to a timezone-aware datetime."""
    if not ts:
        return datetime.now(CN_TZ)

    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S+08:00",
        "%Y-%m-%d %H:%M:%S UTC+8",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CN_TZ)
            return dt
        except ValueError:
            continue

    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CN_TZ)
        return dt
    except (ValueError, TypeError):
        pass

    return datetime.now(CN_TZ)
