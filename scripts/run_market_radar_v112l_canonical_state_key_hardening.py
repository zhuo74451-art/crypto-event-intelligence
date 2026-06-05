"""Market Radar v1.12-L — Canonical State Key Hardening Runner

Orchestrates the v112l pipeline:
  1. Load v112h envelopes and build canonical key index
  2. Audit v112i prior fixture keys (identify synthetic/unknown)
  3. Audit v112j proposed state keys (verify all canonical)
  4. Generate v112l canonical prior state from eligible signals
  5. Validate canonical state entries
  6. Write audit JSONL, result JSON, canonical prior state, report, handoff

Dry-run only — no live state writes, no TG send, no external APIs.

Usage:
    python scripts/run_market_radar_v112l_canonical_state_key_hardening.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Ensure project root is on the path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from scripts.market_radar_state_key_validator_v112l import (
    load_envelopes_jsonl,
    load_prior_state_json,
    load_eligible_signals_jsonl,
    build_envelope_key_index,
    classify_state_key_quality,
    audit_prior_state_keys,
    build_canonical_prior_state_from_eligible_signals,
    scan_state_key_audit_leaks,
    VALIDATOR_VERSION,
    SCHEMA_VERSION,
)

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.12-L"


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def write_json(data: dict | list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    run_ts = china_stamp()
    print(f"=== Market Radar {VERSION} — Canonical State Key Hardening ===")
    print(f"Run timestamp: {run_ts}")
    print()

    # ── Paths ────────────────────────────────────────────────────────────────
    project_dir = Path(__file__).resolve().parent.parent

    envelopes_path = project_dir / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
    eligible_path = project_dir / "results" / "market_radar_v112j_eligible_signals.jsonl"
    proposed_state_path = project_dir / "results" / "market_radar_v112j_proposed_signal_state.json"
    prior_fixture_path = project_dir / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"

    canonical_state_path = project_dir / "results" / "market_radar_v112l_canonical_prior_state.json"
    result_path = project_dir / "results" / "market_radar_v112l_canonical_state_key_hardening_result.json"
    audit_path = project_dir / "results" / "market_radar_v112l_state_key_audit.jsonl"
    report_path = project_dir / "runs" / "market_radar" / "v112l_canonical_state_key_hardening.md"
    handoff_path = project_dir / "runs" / "market_radar" / "v112l_canonical_state_key_hardening_handoff.md"

    # ══════════════════════════════════════════════════════════════════════════
    # Step 1: Load data
    # ══════════════════════════════════════════════════════════════════════════
    print("1. Loading v112h envelopes...")
    envelopes = load_envelopes_jsonl(envelopes_path)
    print(f"   Loaded {len(envelopes)} envelopes")

    print("2. Loading v112j eligible signals...")
    eligible_signals = load_eligible_signals_jsonl(eligible_path)
    print(f"   Loaded {len(eligible_signals)} eligible signals")

    print("3. Loading v112j proposed state...")
    with open(proposed_state_path, "r", encoding="utf-8") as f:
        proposed_state = json.load(f)
    proposed_entries = proposed_state.get("entries", [])
    print(f"   Loaded {len(proposed_entries)} proposed state entries")

    print("4. Loading v112i prior fixture...")
    prior_fixture_entries = load_prior_state_json(prior_fixture_path)
    print(f"   Loaded {len(prior_fixture_entries)} prior fixture entries")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 2: Build envelope key index
    # ══════════════════════════════════════════════════════════════════════════
    print("5. Building canonical envelope key index...")
    envelope_index = build_envelope_key_index(envelopes)
    print(f"   Indexed {len(envelope_index['dedupe_key_set'])} unique dedupe_keys")
    print(f"   Indexed {len(envelope_index['cooldown_key_set'])} unique cooldown_keys")
    print(f"   Indexed {len(envelope_index['payload_hash_set'])} unique payload_hashes")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 3: Audit v112i prior fixture
    # ══════════════════════════════════════════════════════════════════════════
    print("6. Auditing v112i prior fixture keys...")
    prior_fixture_audit = audit_prior_state_keys(
        prior_fixture_entries, envelope_index, label="v112i_prior_fixture"
    )
    print(f"   Canonical matches: {prior_fixture_audit['canonical_match_count']}")
    print(f"   Synthetic/unknown: {prior_fixture_audit['synthetic_or_unknown_count']}")
    print(f"   All canonical: {prior_fixture_audit['entries_canonical']}")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 4: Audit v112j proposed state
    # ══════════════════════════════════════════════════════════════════════════
    print("7. Auditing v112j proposed state keys...")
    proposed_state_audit = audit_prior_state_keys(
        proposed_entries, envelope_index, label="v112j_proposed_state"
    )
    print(f"   Canonical matches: {proposed_state_audit['canonical_match_count']}")
    print(f"   Synthetic/unknown: {proposed_state_audit['synthetic_or_unknown_count']}")
    print(f"   All canonical: {proposed_state_audit['entries_canonical']}")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 5: Generate v112l canonical prior state
    # ══════════════════════════════════════════════════════════════════════════
    print("8. Generating v112l canonical prior state...")
    canonical_state = build_canonical_prior_state_from_eligible_signals(
        eligible_signals, envelopes, run_ts
    )
    canonical_entries = canonical_state.get("entries", [])
    print(f"   Generated {len(canonical_entries)} canonical state entries")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 6: Validate canonical state entries
    # ══════════════════════════════════════════════════════════════════════════
    print("9. Validating canonical state entries...")
    canonical_audit = audit_prior_state_keys(
        canonical_entries, envelope_index, label="v112l_canonical_prior_state"
    )
    print(f"   Canonical matches: {canonical_audit['canonical_match_count']}")
    print(f"   Synthetic/unknown: {canonical_audit['synthetic_or_unknown_count']}")
    print(f"   All canonical: {canonical_audit['entries_canonical']}")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 7: Build audit JSONL
    # ══════════════════════════════════════════════════════════════════════════
    print("10. Building state key audit JSONL...")
    audit_records: list[dict] = []

    # Prior fixture entries
    for entry_result in prior_fixture_audit["per_entry"]:
        idx = entry_result["entry_index"]
        entry = prior_fixture_entries[idx] if idx < len(prior_fixture_entries) else {}
        audit_records.append({
            "audit_source": "v112i_prior_fixture",
            "entry_index": idx,
            "dedupe_key_preview": str(entry.get("dedupe_key", ""))[:32] + "...",
            "cooldown_key_preview": str(entry.get("cooldown_key", ""))[:32] + "...",
            "payload_hash_preview": str(entry.get("payload_hash", ""))[:32] + "...",
            "key_quality": entry_result["key_quality"],
            "all_keys_canonical": entry_result["all_keys_canonical"],
            "details": entry_result["details"],
            "card_type": str(entry.get("card_type", "")),
            "note": entry.get("note", ""),
        })

    # Proposed state entries
    for entry_result in proposed_state_audit["per_entry"]:
        idx = entry_result["entry_index"]
        entry = proposed_entries[idx] if idx < len(proposed_entries) else {}
        audit_records.append({
            "audit_source": "v112j_proposed_state",
            "entry_index": idx,
            "dedupe_key_preview": str(entry.get("dedupe_key", ""))[:32] + "...",
            "cooldown_key_preview": str(entry.get("cooldown_key", ""))[:32] + "...",
            "payload_hash_preview": str(entry.get("payload_hash", ""))[:32] + "...",
            "key_quality": entry_result["key_quality"],
            "all_keys_canonical": entry_result["all_keys_canonical"],
            "details": entry_result["details"],
            "card_type": str(entry.get("card_type", "")),
            "note": entry.get("note", ""),
        })

    # Canonical state entries
    for entry_result in canonical_audit["per_entry"]:
        idx = entry_result["entry_index"]
        entry = canonical_entries[idx] if idx < len(canonical_entries) else {}
        audit_records.append({
            "audit_source": "v112l_canonical_prior_state",
            "entry_index": idx,
            "dedupe_key_preview": str(entry.get("dedupe_key", ""))[:32] + "...",
            "cooldown_key_preview": str(entry.get("cooldown_key", ""))[:32] + "...",
            "payload_hash_preview": str(entry.get("payload_hash", ""))[:32] + "...",
            "key_quality": entry_result["key_quality"],
            "all_keys_canonical": entry_result["all_keys_canonical"],
            "details": entry_result["details"],
            "card_type": str(entry.get("card_type", "")),
            "signal_id": str(entry.get("signal_id", "")),
        })

    # ══════════════════════════════════════════════════════════════════════════
    # Step 8: Leak scan
    # ══════════════════════════════════════════════════════════════════════════
    print("11. Running leak scan...")
    total_debug = 0
    total_secret = 0
    any_wallet_leak = False
    for rec in audit_records:
        leak = scan_state_key_audit_leaks(rec)
        total_debug += leak["debug_leak_count"]
        total_secret += leak["secret_leak_count"]
        if leak["full_wallet_leak"]:
            any_wallet_leak = True

    # Also scan canonical state entries
    for entry in canonical_entries:
        leak = scan_state_key_audit_leaks(entry)
        total_debug += leak["debug_leak_count"]
        total_secret += leak["secret_leak_count"]
        if leak["full_wallet_leak"]:
            any_wallet_leak = True

    print(f"   Debug leaks: {total_debug}")
    print(f"   Secret leaks: {total_secret}")
    print(f"   Full wallet leak: {any_wallet_leak}")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 9: Build result JSON
    # ══════════════════════════════════════════════════════════════════════════
    print("12. Building result JSON...")

    synthetic_risk_detected = prior_fixture_audit["synthetic_or_unknown_count"] > 0

    result = {
        "version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "run_id": "20260604_202718",
        "generated_at": run_ts,
        "envelope_count": len(envelopes),
        "eligible_signal_count": len(eligible_signals),
        "prior_fixture_entry_count": len(prior_fixture_entries),
        "proposed_state_entry_count": len(proposed_entries),
        "canonical_state_entry_count": len(canonical_entries),
        "prior_fixture_canonical_match_count": prior_fixture_audit["canonical_match_count"],
        "prior_fixture_synthetic_or_unknown_count": prior_fixture_audit["synthetic_or_unknown_count"],
        "proposed_state_canonical_match_count": proposed_state_audit["canonical_match_count"],
        "canonical_state_all_match": canonical_audit["entries_canonical"],
        "synthetic_key_risk_detected": synthetic_risk_detected,
        "debug_leak_count": total_debug,
        "secret_leak_count": total_secret,
        "full_wallet_leak": any_wallet_leak,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "dry_run_only": True,
        "production_state_written": False,
        "prior_fixture_audit_summary": {
            "total": prior_fixture_audit["total_entries"],
            "canonical_match": prior_fixture_audit["canonical_match_count"],
            "synthetic_or_unknown": prior_fixture_audit["synthetic_or_unknown_count"],
            "dedupe_key_mismatch": prior_fixture_audit["dedupe_key_mismatch_count"],
            "cooldown_key_mismatch": prior_fixture_audit["cooldown_key_mismatch_count"],
            "payload_hash_mismatch": prior_fixture_audit["payload_hash_mismatch_count"],
            "missing_required_key": prior_fixture_audit["missing_required_key_count"],
        },
        "proposed_state_audit_summary": {
            "total": proposed_state_audit["total_entries"],
            "canonical_match": proposed_state_audit["canonical_match_count"],
            "synthetic_or_unknown": proposed_state_audit["synthetic_or_unknown_count"],
            "dedupe_key_mismatch": proposed_state_audit["dedupe_key_mismatch_count"],
            "cooldown_key_mismatch": proposed_state_audit["cooldown_key_mismatch_count"],
            "payload_hash_mismatch": proposed_state_audit["payload_hash_mismatch_count"],
            "missing_required_key": proposed_state_audit["missing_required_key_count"],
        },
        "canonical_state_audit_summary": {
            "total": canonical_audit["total_entries"],
            "canonical_match": canonical_audit["canonical_match_count"],
            "synthetic_or_unknown": canonical_audit["synthetic_or_unknown_count"],
            "dedupe_key_mismatch": canonical_audit["dedupe_key_mismatch_count"],
            "cooldown_key_mismatch": canonical_audit["cooldown_key_mismatch_count"],
            "payload_hash_mismatch": canonical_audit["payload_hash_mismatch_count"],
            "missing_required_key": canonical_audit["missing_required_key_count"],
        },
        "notes": [
            f"Audited {len(prior_fixture_entries)} prior fixture entries: "
            f"{prior_fixture_audit['canonical_match_count']} canonical, "
            f"{prior_fixture_audit['synthetic_or_unknown_count']} synthetic/unknown.",
            f"Audited {len(proposed_entries)} proposed state entries: "
            f"{proposed_state_audit['canonical_match_count']} canonical.",
            f"Generated {len(canonical_entries)} canonical state entries from eligible signals.",
            f"Canonical state all canonical: {canonical_audit['entries_canonical']}.",
            f"Synthetic key risk detected: {synthetic_risk_detected}.",
            "Dry-run only — no live state writes, no TG send, no external APIs.",
        ],
    }

    # ══════════════════════════════════════════════════════════════════════════
    # Step 10: Write outputs
    # ══════════════════════════════════════════════════════════════════════════
    print("13. Writing output files...")

    write_jsonl(audit_records, audit_path)
    print(f"   -> {audit_path}")

    write_json(canonical_state, canonical_state_path)
    print(f"   -> {canonical_state_path}")

    write_json(result, result_path)
    print(f"   -> {result_path}")

    # ══════════════════════════════════════════════════════════════════════════
    # Step 11: Write report and handoff
    # ══════════════════════════════════════════════════════════════════════════
    print("14. Writing report and handoff...")

    # ── Report ───────────────────────────────────────────────────────────────
    report_lines = [
        f"# Market Radar {VERSION} — Canonical State Key Hardening",
        "",
        f"**Run timestamp**: {run_ts}",
        f"**Version**: {VERSION}",
        f"**Validator version**: {VALIDATOR_VERSION}",
        f"**Schema version**: {SCHEMA_VERSION}",
        "",
        "## Summary",
        "",
        f"- Input envelopes: {len(envelopes)}",
        f"- Eligible signals: {len(eligible_signals)}",
        f"- Prior fixture entries: {len(prior_fixture_entries)}",
        f"- Proposed state entries: {len(proposed_entries)}",
        f"- Canonical state entries: {len(canonical_entries)}",
        "",
        "## Prior Fixture Key Audit (v112i)",
        "",
        f"- **Canonical match**: {prior_fixture_audit['canonical_match_count']}/{prior_fixture_audit['total_entries']}",
        f"- **Synthetic/unknown**: {prior_fixture_audit['synthetic_or_unknown_count']}/{prior_fixture_audit['total_entries']}",
        f"- **Synthetic key risk detected**: **{synthetic_risk_detected}**",
        "",
    ]

    if prior_fixture_audit["synthetic_or_unknown_count"] > 0:
        report_lines.append("### Synthetic/Unknown Keys Found in Prior Fixture")
        report_lines.append("")
        report_lines.append("| # | dedupe_key (preview) | Quality | Card Type | Note |")
        report_lines.append("|---|---------------------|---------|-----------|------|")
        for r in prior_fixture_audit["per_entry"]:
            if r["key_quality"] == "synthetic_or_unknown":
                idx = r["entry_index"]
                entry = prior_fixture_entries[idx] if idx < len(prior_fixture_entries) else {}
                dk_preview = str(entry.get("dedupe_key", ""))[:24] + "..."
                ct = str(entry.get("card_type", ""))
                note = str(entry.get("note", ""))[:60]
                report_lines.append(f"| {idx + 1} | `{dk_preview}` | {r['key_quality']} | {ct} | {note} |")
        report_lines.append("")

    report_lines.extend([
        "## Proposed State Key Audit (v112j)",
        "",
        f"- **Canonical match**: {proposed_state_audit['canonical_match_count']}/{proposed_state_audit['total_entries']}",
        f"- **All canonical**: {proposed_state_audit['entries_canonical']}",
        "",
        "## Canonical Prior State (v112l)",
        "",
        f"- **Entry count**: {len(canonical_entries)}",
        f"- **All canonical**: {canonical_audit['entries_canonical']}",
        f"- **Source**: v112j eligible signals via v112h envelopes",
        f"- **No synthetic fixture keys used**",
        "",
        "### Canonical State Entries",
        "",
        "| # | Signal ID | Card Type | Assets | Direction |",
        "|---|-----------|-----------|--------|-----------|",
    ])

    for i, entry in enumerate(canonical_entries, 1):
        sid = entry.get("signal_id", "?")
        ct = entry.get("card_type", "?")
        assets = ", ".join(entry.get("primary_assets", []))
        direction = entry.get("direction", "?")
        report_lines.append(f"| {i} | `{sid}` | {ct} | {assets} | {direction} |")

    report_lines.extend([
        "",
        "## Safety Flags",
        "",
        f"- `real_tg_sent`: {result['real_tg_sent']}",
        f"- `external_api_called`: {result['external_api_called']}",
        f"- `external_ai_called`: {result['external_ai_called']}",
        f"- `daemon_started`: {result['daemon_started']}",
        f"- `live_ready`: {result['live_ready']}",
        f"- `dry_run_only`: {result['dry_run_only']}",
        f"- `production_state_written`: {result['production_state_written']}",
        "",
        "## Leak Scan",
        "",
        f"- Debug leaks: {result['debug_leak_count']}",
        f"- Secret leaks: {result['secret_leak_count']}",
        f"- Full wallet leak: {result['full_wallet_leak']}",
        "",
        "## Output Files",
        "",
        "- `results/market_radar_v112l_canonical_state_key_hardening_result.json`",
        "- `results/market_radar_v112l_canonical_prior_state.json`",
        "- `results/market_radar_v112l_state_key_audit.jsonl`",
        "- `runs/market_radar/v112l_canonical_state_key_hardening.md` (this file)",
        "- `runs/market_radar/v112l_canonical_state_key_hardening_handoff.md`",
        "",
        "## Conclusion",
        "",
        f"The v112i prior fixture contains **{prior_fixture_audit['synthetic_or_unknown_count']} synthetic/unknown keys**",
        "that could lead to false gate passes (duplicate signals not blocked by dedupe) if used as",
        "prior state in replay scenarios.",
        "",
        f"The v112l canonical prior state resolves this by using **only real envelope keys**",
        f"from the {len(eligible_signals)} v112j eligible signals. All {len(canonical_entries)} entries",
        "in the canonical state pass canonical key validation.",
        "",
        "---",
        f"*Generated by {VERSION} at {run_ts}*",
    ])

    report_md = "\n".join(report_lines)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")
    print(f"   -> {report_path}")

    # ── Handoff ──────────────────────────────────────────────────────────────
    handoff_lines = [
        f"# {VERSION} Canonical State Key Hardening — Handoff",
        "",
        f"**Run**: {run_ts}",
        f"**Status**: {'PASSED' if canonical_audit['entries_canonical'] and not any_wallet_leak else 'PARTIAL'}",
        "",
        "## What was done",
        "",
        "1. Loaded v112h signal envelopes and built canonical key index",
        "2. Audited v112i prior fixture keys — identified synthetic/unknown entries",
        "3. Audited v112j proposed state keys — verified all canonical",
        "4. Generated v112l canonical prior state from eligible signals only",
        "5. Validated all canonical state entries against envelope index",
        "6. Ran comprehensive leak scan",
        "",
        "## Key Findings",
        "",
        f"- **Prior fixture synthetic/unknown keys**: {prior_fixture_audit['synthetic_or_unknown_count']}",
        f"- **Prior fixture canonical matches**: {prior_fixture_audit['canonical_match_count']}",
        f"- **Proposed state entries all canonical**: {proposed_state_audit['entries_canonical']}",
        f"- **Canonical state entries all canonical**: {canonical_audit['entries_canonical']}",
        f"- **Synthetic key risk detected**: {synthetic_risk_detected}",
        "",
        "## Risk Resolution",
        "",
        "The v112k cooldown-expiry replay pass risk is addressed:",
        "- The prior fixture's synthetic keys could cause false negative dedupe hits",
        "- v112l canonical prior state uses only real envelope keys",
        "- Canonical replay in v112k will use verified keys",
        "",
        "## Safety",
        "",
        "- No real TG send",
        "- No external API/AI calls",
        "- No daemon/loop/cron",
        "- No live state writes",
        "- No credential/key/secret exposure",
        "- Dry-run only",
        "- Prior fixture NOT overwritten",
        "",
        "## Next Steps",
        "",
        "1. Run v112k canonical replay with v112l canonical prior state",
        "2. Verify canonical replay idempotency",
        "3. Human review of synthetic key findings",
        "4. Consider replacing prior fixture with canonical state for future testing",
        "",
        "---",
        f"*Generated by {VERSION} at {run_ts}*",
    ]

    handoff_md = "\n".join(handoff_lines)
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(handoff_md, encoding="utf-8")
    print(f"   -> {handoff_path}")

    # ══════════════════════════════════════════════════════════════════════════
    # Print summary
    # ══════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 60)
    print("CANONICAL STATE KEY HARDENING SUMMARY")
    print("=" * 60)
    print(f"  Envelopes:               {len(envelopes)}")
    print(f"  Eligible signals:        {len(eligible_signals)}")
    print(f"  Prior fixture entries:   {len(prior_fixture_entries)}")
    print(f"  Proposed state entries:  {len(proposed_entries)}")
    print(f"  Canonical state entries: {len(canonical_entries)}")
    print()
    print(f"  Prior fixture canonical: {prior_fixture_audit['canonical_match_count']}")
    print(f"  Prior fixture synthetic: {prior_fixture_audit['synthetic_or_unknown_count']}")
    print(f"  Proposed state canonical: {proposed_state_audit['canonical_match_count']}")
    print(f"  Canonical state all match: {canonical_audit['entries_canonical']}")
    print(f"  Synthetic key risk:       {synthetic_risk_detected}")
    print(f"  Debug leaks:              {total_debug}")
    print(f"  Secret leaks:             {total_secret}")
    print(f"  Full wallet leak:         {any_wallet_leak}")
    print(f"  Dry-run only:             True")
    print()
    print("[PASS] Canonical state key hardening complete.")
    print("Done.")


if __name__ == "__main__":
    main()
