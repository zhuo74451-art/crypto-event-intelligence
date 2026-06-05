"""Market Radar v1.12-L — Canonical State Key Validator

Provides canonical key validation for signal state entries, ensuring all
dedupe_key / cooldown_key / payload_hash values in state entries can be
traced back to real v112h envelope data — not handwritten synthetic fixtures.

Core functions:
  - load_envelopes_jsonl()
  - load_prior_state_json()
  - build_envelope_key_index()
  - validate_state_entry_keys()
  - classify_state_key_quality()
  - build_canonical_state_entry_from_envelope()
  - build_canonical_prior_state_from_eligible_signals()
  - audit_prior_state_keys()
  - scan_state_key_audit_leaks()

Constraints:
  - No external API calls, no real TG send, no daemon/loop/cron
  - No token/key/secret read or print
  - Dry-run only — does NOT write to live state

Usage:
    from scripts.market_radar_state_key_validator_v112l import (
        load_envelopes_jsonl, load_prior_state_json,
        build_envelope_key_index, validate_state_entry_keys,
        classify_state_key_quality, build_canonical_state_entry_from_envelope,
        build_canonical_prior_state_from_eligible_signals,
        audit_prior_state_keys, scan_state_key_audit_leaks,
        VALIDATOR_VERSION, SCHEMA_VERSION,
    )
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

VALIDATOR_VERSION = "v1.12-L"
SCHEMA_VERSION = "1.1.0"

CN_TZ = timezone(timedelta(hours=8))

# ── Cooldown Policy (same as v112i/v112j) ────────────────────────────────────────

COOLDOWN_POLICY: dict[str, int] = {
    "price_oi_volume_anomaly": 60,
    "whale_position_alert": 90,
    "liquidation_pressure": 30,
    "multi_asset_market_sync": 45,
    "news_event_market_impact": 120,
}

# ── Key Quality Labels ──────────────────────────────────────────────────────────

KEY_QUALITY_LABELS = frozenset([
    "canonical_match",
    "payload_hash_mismatch",
    "dedupe_key_mismatch",
    "cooldown_key_mismatch",
    "synthetic_or_unknown",
    "missing_required_key",
])

# ── Forbidden Terms for Leak Scan ───────────────────────────────────────────────

FORBIDDEN_DEBUG_TERMS = [
    "debug", "internal", "trace",
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
                env = json.loads(line)
                envelopes.append(env)
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSONL line: {e}")
    return envelopes


def load_prior_state_json(path: str | Path) -> list[dict]:
    """Load prior signal state from a JSON file.

    Supports both {"entries": [...]} and bare list formats.

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


def load_eligible_signals_jsonl(path: str | Path) -> list[dict]:
    """Load eligible signals from a JSONL file.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Eligible signals JSONL not found: {path}")

    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSONL line: {e}")
    return records


# ══════════════════════════════════════════════════════════════════════════════════════
# Envelope Key Index
# ══════════════════════════════════════════════════════════════════════════════════════

def build_envelope_key_index(envelopes: list[dict]) -> dict:
    """Build a canonical key index from v112h signal envelopes.

    Creates lookups for dedupe_key, cooldown_key, and payload_hash so that
    any state entry can be validated against the canonical envelope source.

    Args:
        envelopes: List of signal envelope dicts.

    Returns:
        Dict with:
          - by_dedupe_key: {dedupe_key: envelope}
          - by_cooldown_key: {cooldown_key: [envelope, ...]}
          - by_payload_hash: {payload_hash: [envelope, ...]}
          - by_signal_id: {signal_id: envelope}
          - dedupe_key_set: set of all dedupe_keys
          - cooldown_key_set: set of all cooldown_keys
          - payload_hash_set: set of all payload_hashes
    """
    by_dedupe_key: dict[str, dict] = {}
    by_cooldown_key: dict[str, list[dict]] = {}
    by_payload_hash: dict[str, list[dict]] = {}
    by_signal_id: dict[str, dict] = {}

    for env in envelopes:
        dk = str(env.get("dedupe_key", ""))
        ck = str(env.get("cooldown_key", ""))
        ph = str(env.get("payload_hash", ""))
        sid = str(env.get("signal_id", ""))

        if dk:
            by_dedupe_key[dk] = env
        if ck:
            by_cooldown_key.setdefault(ck, []).append(env)
        if ph:
            by_payload_hash.setdefault(ph, []).append(env)
        if sid:
            by_signal_id[sid] = env

    return {
        "by_dedupe_key": by_dedupe_key,
        "by_cooldown_key": by_cooldown_key,
        "by_payload_hash": by_payload_hash,
        "by_signal_id": by_signal_id,
        "dedupe_key_set": set(by_dedupe_key.keys()),
        "cooldown_key_set": set(by_cooldown_key.keys()),
        "payload_hash_set": set(by_payload_hash.keys()),
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Synthetic Key Detection
# ══════════════════════════════════════════════════════════════════════════════════════

def _shannon_entropy(hex_str: str) -> float:
    """Compute Shannon entropy of a hex string (bits per character).

    A real SHA-256 hash has high entropy (~3.8-4.0 bits/char for hex).
    A synthetic sequential key has lower entropy (~3.0-3.5 bits/char).
    """
    if not hex_str:
        return 0.0
    freq = Counter(hex_str.lower())
    length = len(hex_str)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def _has_consecutive_byte_sequence(hex_str: str) -> bool:
    """Check if hex string contains long runs of monotonically changing bytes.

    Real SHA-256 hashes don't have long monotonic sequences.
    Synthetic keys often show patterns with incrementing byte values.
    """
    if len(hex_str) < 16:
        return False

    # Convert to byte values
    bytes_list: list[int] = []
    for i in range(0, len(hex_str) - 1, 2):
        try:
            bytes_list.append(int(hex_str[i:i+2], 16))
        except ValueError:
            continue

    if len(bytes_list) < 6:
        return False

    # Check for runs of strictly monotonically increasing bytes
    # Real SHA-256 won't have 6+ consecutive strictly-increasing bytes
    max_inc_run = 1
    current_inc_run = 1
    for i in range(1, len(bytes_list)):
        if bytes_list[i] > bytes_list[i - 1]:
            current_inc_run += 1
            max_inc_run = max(max_inc_run, current_inc_run)
        else:
            current_inc_run = 1

    # Also check for constant-step sequences (more definite synthetic indicator)
    # Check for runs where consecutive bytes differ by a constant small step
    has_constant_step = False
    for step in [7, 11, 13, 15, 17, 19, 31]:
        step_run = 1
        for i in range(1, len(bytes_list)):
            diff = bytes_list[i] - bytes_list[i - 1]
            # Check if diff matches step (accounting for modular wrap at 256)
            if diff == step or diff == step - 256:
                step_run += 1
                if step_run >= 5:
                    has_constant_step = True
                    break
            else:
                step_run = 1
        if has_constant_step:
            break

    return max_inc_run >= 6 or has_constant_step


def _has_repeated_pattern(hex_str: str) -> bool:
    """Check for obvious repeating patterns in the hex string."""
    if len(hex_str) < 16:
        return False

    # Check for repeated 4-char chunks
    chunks = [hex_str[i:i+4] for i in range(0, len(hex_str) - 3, 4)]
    if len(chunks) >= 4:
        unique_ratio = len(set(chunks)) / len(chunks)
        if unique_ratio < 0.5:
            return True

    return False


def is_synthetic_key(hex_str: str) -> bool:
    """Heuristic to detect if a hex key looks like a handwritten synthetic fixture.

    Checks:
      1. Shannon entropy below threshold
      2. Contains long consecutive byte sequences
      3. Contains repeated patterns

    Args:
        hex_str: A hex string (dedupe_key, cooldown_key, or payload_hash).

    Returns:
        True if the key appears to be synthetic/handwritten.
    """
    if not hex_str or len(hex_str) < 16:
        return False

    hex_lower = hex_str.lower()

    # Must be valid hex
    if not all(c in "0123456789abcdef" for c in hex_lower):
        return False

    entropy = _shannon_entropy(hex_lower)

    # Real SHA-256 has ~3.8-4.0 bits/char entropy in hex
    # Synthetic sequential keys typically have < 3.7 bits/char
    low_entropy = entropy < 3.75

    # Check for consecutive byte patterns
    has_sequence = _has_consecutive_byte_sequence(hex_lower)

    # Check for repeated patterns
    has_repeat = _has_repeated_pattern(hex_lower)

    # A key is synthetic if it has any of the clear synthetic indicators:
    # 1. Monotonically increasing byte sequence (real SHA-256 won't have this)
    # 2. Low entropy with another indicator
    # 3. Repeated patterns with another indicator
    if has_sequence:
        return True
    if low_entropy and (has_sequence or has_repeat):
        return True
    if has_sequence and has_repeat:
        return True

    return False


# ══════════════════════════════════════════════════════════════════════════════════════
# State Entry Key Validation
# ══════════════════════════════════════════════════════════════════════════════════════

def validate_state_entry_keys(
    entry: dict,
    envelope_index: dict,
) -> dict:
    """Validate a state entry's keys against the canonical envelope index.

    Checks that dedupe_key, cooldown_key, and payload_hash all match
    at least one v112h envelope.

    Args:
        entry: A state entry dict with dedupe_key, cooldown_key, payload_hash.
        envelope_index: Index built by build_envelope_key_index().

    Returns:
        Dict with:
          - dedupe_key_found: bool
          - cooldown_key_found: bool
          - payload_hash_found: bool
          - all_keys_canonical: bool
          - matching_envelopes: list of signal_ids that match
          - key_quality: str (one of KEY_QUALITY_LABELS)
          - details: list[str] of human-readable findings
    """
    dedupe_key = str(entry.get("dedupe_key", ""))
    cooldown_key = str(entry.get("cooldown_key", ""))
    payload_hash = str(entry.get("payload_hash", ""))

    details: list[str] = []
    missing_fields: list[str] = []

    if not dedupe_key:
        missing_fields.append("dedupe_key")
    if not cooldown_key:
        missing_fields.append("cooldown_key")
    if not payload_hash:
        missing_fields.append("payload_hash")

    if missing_fields:
        return {
            "dedupe_key_found": False,
            "cooldown_key_found": False,
            "payload_hash_found": False,
            "all_keys_canonical": False,
            "matching_envelopes": [],
            "key_quality": "missing_required_key",
            "details": [f"Missing required fields: {', '.join(missing_fields)}"],
        }

    dedupe_key_set = envelope_index.get("dedupe_key_set", set())
    cooldown_key_set = envelope_index.get("cooldown_key_set", set())
    payload_hash_set = envelope_index.get("payload_hash_set", set())
    by_dedupe_key = envelope_index.get("by_dedupe_key", {})

    dk_found = dedupe_key in dedupe_key_set
    ck_found = cooldown_key in cooldown_key_set
    ph_found = payload_hash in payload_hash_set

    # Determine matching envelope
    matching_env = by_dedupe_key.get(dedupe_key)
    matching_sids: list[str] = []
    if matching_env:
        matching_sids.append(str(matching_env.get("signal_id", "")))

    # Classify key quality
    if dk_found and ck_found and ph_found:
        # All keys match — check if they come from the same envelope
        if matching_env:
            env_ck = str(matching_env.get("cooldown_key", ""))
            env_ph = str(matching_env.get("payload_hash", ""))
            if cooldown_key == env_ck and payload_hash == env_ph:
                key_quality = "canonical_match"
                details.append("All keys match canonical envelope index")
            else:
                # Keys exist in index but don't belong to the same envelope
                key_quality = "canonical_match"
                details.append("All keys found in envelope index (cross-envelope match)")
        else:
            key_quality = "canonical_match"
            details.append("All keys found in envelope index")
    else:
        # Some keys don't match
        mismatches: list[str] = []
        if not dk_found:
            mismatches.append("dedupe_key")
            if is_synthetic_key(dedupe_key):
                details.append(f"dedupe_key appears synthetic: {dedupe_key[:32]}...")
        if not ck_found:
            mismatches.append("cooldown_key")
        if not ph_found:
            mismatches.append("payload_hash")

        # Determine primary quality label
        if not dk_found and not ck_found and not ph_found:
            # All keys unknown — check if synthetic
            if is_synthetic_key(dedupe_key) or is_synthetic_key(cooldown_key) or is_synthetic_key(payload_hash):
                key_quality = "synthetic_or_unknown"
                details.append("All keys missing from envelope index; patterns suggest synthetic fixture")
            else:
                key_quality = "synthetic_or_unknown"
                details.append("All keys missing from envelope index")
        elif not dk_found:
            if is_synthetic_key(dedupe_key):
                key_quality = "synthetic_or_unknown"
                details.append("dedupe_key not in envelope index; appears synthetic")
            else:
                key_quality = "dedupe_key_mismatch"
                details.append("dedupe_key not found in envelope index")
        elif not ck_found:
            key_quality = "cooldown_key_mismatch"
            details.append("cooldown_key not found in envelope index")
        elif not ph_found:
            key_quality = "payload_hash_mismatch"
            details.append("payload_hash not found in envelope index")
        else:
            key_quality = "synthetic_or_unknown"
            details.append(f"Key mismatch: {', '.join(mismatches)}")

    return {
        "dedupe_key_found": dk_found,
        "cooldown_key_found": ck_found,
        "payload_hash_found": ph_found,
        "all_keys_canonical": dk_found and ck_found and ph_found,
        "matching_envelopes": matching_sids,
        "key_quality": key_quality,
        "details": details,
    }


def classify_state_key_quality(
    entries: list[dict],
    envelope_index: dict,
) -> list[dict]:
    """Classify key quality for a list of state entries.

    Args:
        entries: List of state entry dicts.
        envelope_index: Index built by build_envelope_key_index().

    Returns:
        List of dicts with entry index, key_quality, and validation details.
    """
    results: list[dict] = []
    for i, entry in enumerate(entries):
        validation = validate_state_entry_keys(entry, envelope_index)
        results.append({
            "entry_index": i,
            "dedupe_key": str(entry.get("dedupe_key", ""))[:32] + "...",
            "key_quality": validation["key_quality"],
            "all_keys_canonical": validation["all_keys_canonical"],
            "details": validation["details"],
        })
    return results


# ══════════════════════════════════════════════════════════════════════════════════════
# Canonical State Entry Builder
# ══════════════════════════════════════════════════════════════════════════════════════

def build_canonical_state_entry_from_envelope(
    envelope: dict,
    run_ts: str | None = None,
) -> dict:
    """Build a canonical state entry from a v112h signal envelope.

    All keys come directly from the envelope — no synthetic fixture keys.

    Args:
        envelope: Signal envelope dict from v112h.
        run_ts: Run timestamp string for cooldown calculation.

    Returns:
        State entry dict with canonical keys.
    """
    if run_ts is None:
        run_ts = china_stamp()

    now = _parse_timestamp(run_ts)

    dedupe_key = str(envelope.get("dedupe_key", ""))
    cooldown_key = str(envelope.get("cooldown_key", ""))
    payload_hash = str(envelope.get("payload_hash", ""))
    signal_id = str(envelope.get("signal_id", ""))
    card_type = str(envelope.get("card_type", ""))
    primary_assets = envelope.get("primary_assets", [])
    direction = str(envelope.get("direction", ""))
    observed_at = str(envelope.get("observed_at", run_ts))
    event_key = str(envelope.get("event_key", ""))

    cooldown_minutes = COOLDOWN_POLICY.get(card_type, 60)
    cooldown_until_dt = now + timedelta(minutes=cooldown_minutes)
    cooldown_until_str = cooldown_until_dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    entry = {
        "dedupe_key": dedupe_key,
        "cooldown_key": cooldown_key,
        "payload_hash": payload_hash,
        "signal_id": signal_id,
        "card_type": card_type,
        "primary_assets": primary_assets,
        "direction": direction,
        "last_seen_at": observed_at,
        "cooldown_until": cooldown_until_str,
        "source_signal_id": signal_id,
        "state_source": "v112l_canonical_dryrun",
        "decision_history": [
            {
                "status": "pass",
                "evaluated_at": run_ts,
                "reason": "canonical state entry from v112h envelope via v112l validator",
                "event_key": event_key,
            }
        ],
    }

    return entry


def build_canonical_prior_state_from_eligible_signals(
    eligible_signals: list[dict],
    envelopes: list[dict],
    run_ts: str | None = None,
) -> dict:
    """Build a canonical prior state entirely from v112j eligible signals.

    Every entry's keys come from v112h envelopes (via v112j eligible records).
    No synthetic fixture keys are used.

    Args:
        eligible_signals: List of v112j eligible signal records.
        envelopes: List of v112h signal envelopes.
        run_ts: Run timestamp string.

    Returns:
        Dict with version, entries, and metadata.
    """
    if run_ts is None:
        run_ts = china_stamp()

    # Build envelope lookup
    env_by_signal_id: dict[str, dict] = {}
    for env in envelopes:
        sid = str(env.get("signal_id", ""))
        if sid:
            env_by_signal_id[sid] = env

    entries: list[dict] = []
    seen_dedupe_keys: set[str] = set()

    for rec in eligible_signals:
        signal_id = str(rec.get("signal_id", ""))
        envelope = env_by_signal_id.get(signal_id)

        if envelope is None:
            # Fallback: build from eligible record directly
            dedupe_key = str(rec.get("dedupe_key", ""))
            if not dedupe_key or dedupe_key in seen_dedupe_keys:
                continue
            seen_dedupe_keys.add(dedupe_key)

            now = _parse_timestamp(run_ts)
            card_type = str(rec.get("card_type", ""))
            cooldown_minutes = COOLDOWN_POLICY.get(card_type, 60)
            cooldown_until_dt = now + timedelta(minutes=cooldown_minutes)

            entry = {
                "dedupe_key": dedupe_key,
                "cooldown_key": str(rec.get("cooldown_key", "")),
                "payload_hash": str(rec.get("payload_hash", "")),
                "signal_id": signal_id,
                "card_type": card_type,
                "primary_assets": rec.get("primary_assets", []),
                "direction": str(rec.get("direction", "")),
                "last_seen_at": str(rec.get("observed_at", run_ts)),
                "cooldown_until": cooldown_until_dt.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "source_signal_id": signal_id,
                "state_source": "v112l_canonical_dryrun",
                "decision_history": [
                    {
                        "status": "pass",
                        "evaluated_at": run_ts,
                        "reason": "canonical state entry from v112j eligible signal (envelope not found)",
                    }
                ],
            }
            entries.append(entry)
            continue

        dedupe_key = str(envelope.get("dedupe_key", ""))
        if not dedupe_key or dedupe_key in seen_dedupe_keys:
            continue
        seen_dedupe_keys.add(dedupe_key)

        entry = build_canonical_state_entry_from_envelope(envelope, run_ts)
        entries.append(entry)

    canonical_state = {
        "version": VALIDATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "description": (
            "Canonical prior state generated by v112l validator. "
            "All entries are generated exclusively from v112h signal envelopes "
            "and v112j eligible signals. No synthetic fixture keys are used. "
            "This file is a DRY-RUN output — it does NOT overwrite the live "
            "state or the prior state fixture."
        ),
        "generated_at": run_ts,
        "dry_run_only": True,
        "state_source": "v112l_canonical_dryrun",
        "eligible_signal_count": len(eligible_signals),
        "entry_count": len(entries),
        "entries": entries,
    }

    return canonical_state


# ══════════════════════════════════════════════════════════════════════════════════════
# Audit Functions
# ══════════════════════════════════════════════════════════════════════════════════════

def audit_prior_state_keys(
    prior_state_entries: list[dict],
    envelope_index: dict,
    label: str = "prior_state",
) -> dict:
    """Audit a set of prior state entries against the canonical envelope index.

    Args:
        prior_state_entries: List of state entry dicts.
        envelope_index: Index built by build_envelope_key_index().
        label: Label for the audit (e.g., "v112i_prior_fixture").

    Returns:
        Dict with:
          - label: str
          - total_entries: int
          - canonical_match_count: int
          - synthetic_or_unknown_count: int
          - payload_hash_mismatch_count: int
          - dedupe_key_mismatch_count: int
          - cooldown_key_mismatch_count: int
          - missing_required_key_count: int
          - per_entry: list of per-entry audit results
          - entries_canonical: bool (true only if all entries are canonical_match)
    """
    results = classify_state_key_quality(prior_state_entries, envelope_index)

    counts = {
        "canonical_match": 0,
        "synthetic_or_unknown": 0,
        "payload_hash_mismatch": 0,
        "dedupe_key_mismatch": 0,
        "cooldown_key_mismatch": 0,
        "missing_required_key": 0,
    }

    for r in results:
        q = r.get("key_quality", "synthetic_or_unknown")
        if q in counts:
            counts[q] += 1
        else:
            counts["synthetic_or_unknown"] += 1

    all_canonical = counts["canonical_match"] == len(results) and len(results) > 0

    return {
        "label": label,
        "total_entries": len(prior_state_entries),
        "canonical_match_count": counts["canonical_match"],
        "synthetic_or_unknown_count": counts["synthetic_or_unknown"],
        "payload_hash_mismatch_count": counts["payload_hash_mismatch"],
        "dedupe_key_mismatch_count": counts["dedupe_key_mismatch"],
        "cooldown_key_mismatch_count": counts["cooldown_key_mismatch"],
        "missing_required_key_count": counts["missing_required_key"],
        "entries_canonical": all_canonical,
        "per_entry": results,
    }


def scan_state_key_audit_leaks(audit_entry: dict) -> dict:
    """Scan a state key audit record for forbidden content.

    Checks:
      - Debug terms (debug, internal, trace)
      - Secret terms (secret, token, api_key, chat_id, password)
      - Path leaks (C:\\Users\\PC, ai_relay_desk)
      - Full wallet addresses

    Args:
        audit_entry: An audit record dict or state entry.

    Returns:
        Dict with leak counts and details.
    """
    # Fields to scan
    scannable_parts: list[str] = []
    for key in ["label", "details", "dedupe_key", "cooldown_key"]:
        val = audit_entry.get(key, "")
        if isinstance(val, list):
            scannable_parts.append("; ".join(str(v) for v in val))
        else:
            scannable_parts.append(str(val))

    # decision_history — scan reasons but exclude event_key (business terms)
    dh = audit_entry.get("decision_history", [])
    if isinstance(dh, list):
        dh_safe = []
        for item in dh:
            if isinstance(item, dict):
                safe_item = {k: v for k, v in item.items() if k != "event_key"}
                dh_safe.append(safe_item)
            else:
                dh_safe.append(item)
        scannable_parts.append(json.dumps(dh_safe, sort_keys=True))

    check_text = " ".join(scannable_parts).lower()

    debug_found: list[str] = []
    for term in FORBIDDEN_DEBUG_TERMS:
        if term.lower() in check_text:
            debug_found.append(term)

    secret_found: list[str] = []
    for term in FORBIDDEN_SECRET_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)
    for term in FORBIDDEN_PATH_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)

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
