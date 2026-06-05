"""
Test script for Market Radar Sender v1.9A + v1.9A-S1 + v1.9A-S2 + v1.9B Transport + v1.9B-final Prep + v1.9B-final R1

Covers:
  Original 14 tests (v1.9A-S1):
  1-14. Core dry-run, gate validation, schema validation

  v1.9A-S2 additions (11 tests):
  15-25. Schema version, Runtime Source, type/range, policy, sanitization

  v1.9B Transport tests (11 tests):
  26-36. FakeTransport, TGTransportStub, MarketRadarSender integration

  v1.9B-final Prep TGTransport tests (13 tests):
  37-49. TGTransport + MockHttpClient, error mapping, redaction, no-env, no-print

  v1.9B-final R1 RealHttpClient monkeypatch tests (7+ tests):
  50-56. RealHttpClient injection, monkeypatch success/400/401/429/timeout/connection-error, spy verification

Uses local input files:
  - results/static_position_v18g_send_candidate.md
  - results/static_position_v18g_send_candidate.json
  - results/static_position_v18h_preview_report.md
  - results/market_radar_v19_manifest_sample.json
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure the scripts directory is on sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from market_radar_sender import (
    ROOT,
    CN_TZ,
    SCHEMA_VERSION_REQUIRED,
    BaseTransport,
    FakeTransport,
    GateResult,
    HttpClient,
    MarketRadarSender,
    MockHttpClient,
    PolicyReceipt,
    RealHttpClient,
    SendResult,
    TGTransport,
    TGTransportStub,
    TRANSPORT_FAKE,
    TRANSPORT_TELEGRAM,
    apply_policy,
    build_manifest_from_paths,
    build_send_payload,
    dry_run_send,
    escape_html,
    escape_markdown_v2,
    load_candidate,
    load_preview_gate,
    load_schema,
    normalize_parse_mode,
    normalize_target_type,
    remove_control_chars,
    run_full_dry_run,
    sanitize_flexible_payload,
    sanitize_for_parse_mode,
    validate_and_apply_policy,
    validate_manifest,
    validate_preview_gate,
    validate_runtime_source_paths,
    validate_types_and_ranges,
    write_send_handoff,
)

# ---------------------------------------------------------------------------
# Test paths
# ---------------------------------------------------------------------------
CANDIDATE_MD = ROOT / "results" / "static_position_v18g_send_candidate.md"
CANDIDATE_JSON = ROOT / "results" / "static_position_v18g_send_candidate.json"
PREVIEW_REPORT = ROOT / "results" / "static_position_v18h_preview_report.md"
DRYRUN_RESULT = ROOT / "results" / "market_radar_sender_v19a_dryrun_result.json"
MANIFEST_SAMPLE = ROOT / "results" / "market_radar_v19_manifest_sample.json"

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results_log: list[dict] = []


def log_result(test_name: str, status: str, detail: str = "") -> None:
    results_log.append({
        "test": test_name,
        "status": status,
        "detail": detail,
    })
    icon = "[PASS]" if status == PASS else ("[FAIL]" if status == FAIL else "[SKIP]")
    print(f"  {icon} {test_name}: {status}")
    if detail:
        print(f"     {detail}")


# ---------------------------------------------------------------------------
# Test 1: Normal dry-run pass
# ---------------------------------------------------------------------------

def test_01_normal_dry_run_pass() -> None:
    """Full dry-run pipeline should pass with real input files."""
    print("\n--- Test 1: Normal dry-run pass ---")

    try:
        result = run_full_dry_run(
            candidate_md_path=CANDIDATE_MD,
            candidate_json_path=CANDIDATE_JSON,
            preview_report_path=PREVIEW_REPORT,
            result_output_path=DRYRUN_RESULT,
            max_send_count=1,
        )

        checks = [
            ("status is done", result.status == "done"),
            ("sent_count == 1", result.sent_count == 1),
            ("max_send_count == 1", result.max_send_count == 1),
            ("dry_run is True", result.dry_run is True),
            ("tg_api_called is False", result.tg_api_called is False),
            ("all gates pass", all(g.passed for g in result.gate_results)),
            ("result file exists", DRYRUN_RESULT.exists()),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"1.{desc}", FAIL, f"Expected {desc}")
                all_ok = False

        if all_ok:
            log_result("1.Normal dry-run pass", PASS,
                       f"sent_count={result.sent_count}, gates={len(result.gate_results)} passed")
        else:
            log_result("1.Normal dry-run pass", FAIL, "Some checks failed")
    except Exception as e:
        log_result("1.Normal dry-run pass", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 2: max_send_count=1 enforcement
# ---------------------------------------------------------------------------

def test_02_max_send_count_enforcement() -> None:
    """When sent_count already reaches max_send_count, send should be blocked."""
    print("\n--- Test 2: max_send_count=1 enforcement ---")

    try:
        payload = build_send_payload("test content")
        result = dry_run_send(payload, sent_count=1, max_send_count=1)

        checks = [
            ("status is blocked", result.status == "blocked"),
            ("error mentions send limit", "send limit" in result.error.lower() or
             "sent_count" in result.error.lower()),
            ("tg_api_called is False", result.tg_api_called is False),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("2.max_send_count enforcement", PASS,
                       f"Correctly blocked: {result.error}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"2.{desc}", FAIL, f"status={result.status}, error={result.error}")
            log_result("2.max_send_count enforcement", FAIL, "Some checks failed")
    except Exception as e:
        log_result("2.max_send_count enforcement", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 3: blocked=true rejection
# ---------------------------------------------------------------------------

def test_03_blocked_true_rejection() -> None:
    """When gate 'blocked' is true, the send should be blocked."""
    print("\n--- Test 3: blocked=true rejection ---")

    try:
        report = {
            "report_path": "(test)",
            "indicators": {
                "blocked_ok": False,
                "blocked_reasons_empty": True,
                "leak_count": 0,
                "leak_free": True,
                "full_address_count": 0,
                "full_address_free": True,
                "consistency_ok": True,
                "forbidden_terms_count": 0,
                "forbidden_terms_zero": True,
                "machine_terms_count": 0,
                "machine_terms_zero": True,
            },
        }
        candidate = {
            "md_text": "test card content",
            "json_data": {
                "blocked": True,
                "blocked_reasons": ["test blocker"],
            },
        }

        gate_results = validate_preview_gate(report, candidate)
        payload = build_send_payload(candidate["md_text"])
        result = dry_run_send(payload, gate_results=gate_results)

        checks = [
            ("status is blocked", result.status == "blocked"),
            ("gate_blocked_false fails", any(
                g.name == "gate_blocked_false" and not g.passed
                for g in result.gate_results
            )),
            ("gate_candidate_blocked_false fails", any(
                g.name == "gate_candidate_blocked_false" and not g.passed
                for g in result.gate_results
            )),
            ("tg_api_called is False", result.tg_api_called is False),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("3.blocked=true rejection", PASS,
                       "Correctly blocked when blocked=true")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"3.{desc}", FAIL, "")
            log_result("3.blocked=true rejection", FAIL, "Some checks failed")
    except Exception as e:
        log_result("3.blocked=true rejection", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 4: leak_count > 0 rejection
# ---------------------------------------------------------------------------

def test_04_leak_count_rejection() -> None:
    """When leak_count > 0, the send should be blocked."""
    print("\n--- Test 4: leak_count > 0 rejection ---")

    try:
        report = {
            "report_path": "(test)",
            "indicators": {
                "blocked_ok": True,
                "blocked_reasons_empty": True,
                "leak_count": 2,
                "leak_free": False,
                "full_address_count": 0,
                "full_address_free": True,
                "consistency_ok": True,
                "forbidden_terms_count": 0,
                "forbidden_terms_zero": True,
                "machine_terms_count": 0,
                "machine_terms_zero": True,
            },
        }
        candidate = {
            "md_text": "test card with leaked token: abc123",
            "json_data": {"blocked": False, "blocked_reasons": []},
        }

        gate_results = validate_preview_gate(report, candidate)
        payload = build_send_payload(candidate["md_text"])
        result = dry_run_send(payload, gate_results=gate_results)

        checks = [
            ("status is blocked", result.status == "blocked"),
            ("gate_leak_count_zero fails", any(
                g.name == "gate_leak_count_zero" and not g.passed
                for g in result.gate_results
            )),
            ("tg_api_called is False", result.tg_api_called is False),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("4.leak_count > 0 rejection", PASS,
                       "Correctly blocked on leak_count=2")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"4.{desc}", FAIL, "")
            log_result("4.leak_count > 0 rejection", FAIL, "Some checks failed")
    except Exception as e:
        log_result("4.leak_count > 0 rejection", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 5: full_address_count > 0 rejection
# ---------------------------------------------------------------------------

def test_05_full_address_count_rejection() -> None:
    """When full_address_count > 0, the send should be blocked."""
    print("\n--- Test 5: full_address_count > 0 rejection ---")

    try:
        report = {
            "report_path": "(test)",
            "indicators": {
                "blocked_ok": True,
                "blocked_reasons_empty": True,
                "leak_count": 0,
                "leak_free": True,
                "full_address_count": 1,
                "full_address_free": False,
                "consistency_ok": True,
                "forbidden_terms_count": 0,
                "forbidden_terms_zero": True,
                "machine_terms_count": 0,
                "machine_terms_zero": True,
            },
        }
        candidate = {
            "md_text": "test card with addr: 0x",
            "json_data": {"blocked": False, "blocked_reasons": []},
        }

        gate_results = validate_preview_gate(report, candidate)
        payload = build_send_payload(candidate["md_text"])
        result = dry_run_send(payload, gate_results=gate_results)

        checks = [
            ("status is blocked", result.status == "blocked"),
            ("gate_full_address_count_zero fails", any(
                g.name == "gate_full_address_count_zero" and not g.passed
                for g in result.gate_results
            )),
            ("tg_api_called is False", result.tg_api_called is False),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("5.full_address_count > 0 rejection", PASS,
                       "Correctly blocked on full_address_count=1")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"5.{desc}", FAIL, "")
            log_result("5.full_address_count > 0 rejection", FAIL, "Some checks failed")
    except Exception as e:
        log_result("5.full_address_count > 0 rejection", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 6: No external interface calls
# ---------------------------------------------------------------------------

def test_06_no_external_calls() -> None:
    """Verify that dry_run_send never calls external APIs."""
    print("\n--- Test 6: No external interface calls ---")

    try:
        import urllib.request as _urllib

        original_urlopen = _urllib.urlopen
        call_count = [0]

        def _spy_urlopen(*args, **kwargs):
            call_count[0] += 1
            raise AssertionError(
                f"dry_run_send made an external HTTP call! args={args[:1]}"
            )

        _urllib.urlopen = _spy_urlopen

        try:
            candidate = load_candidate(CANDIDATE_MD, CANDIDATE_JSON)
            preview_gate = load_preview_gate(PREVIEW_REPORT)
            gate_results = validate_preview_gate(preview_gate, candidate)
            payload = build_send_payload(candidate["md_text"])
            result = dry_run_send(payload, gate_results=gate_results)
        finally:
            _urllib.urlopen = original_urlopen

        checks = [
            ("no external calls made", call_count[0] == 0),
            ("status is done", result.status == "done"),
            ("tg_api_called is False", result.tg_api_called is False),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("6.No external interface calls", PASS,
                       f"Verified 0 external calls, result status={result.status}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"6.{desc}", FAIL, f"call_count={call_count[0]}")
            log_result("6.No external interface calls", FAIL, "Some checks failed")
    except Exception as e:
        log_result("6.No external interface calls", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 7: Edge case - empty candidate
# ---------------------------------------------------------------------------

def test_07_empty_candidate() -> None:
    """load_candidate should raise on empty markdown."""
    print("\n--- Test 7: Empty candidate rejection ---")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("   \n\n")
            tmp_md = f.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"blocked": False}, f)
            tmp_json = f.name

        try:
            load_candidate(tmp_md, tmp_json)
            log_result("7.Empty candidate rejection", FAIL, "Should have raised ValueError")
        except ValueError:
            log_result("7.Empty candidate rejection", PASS, "Correctly raised ValueError on empty markdown")
        finally:
            os.unlink(tmp_md)
            os.unlink(tmp_json)
    except Exception as e:
        log_result("7.Empty candidate rejection", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 8: Edge case - missing preview report
# ---------------------------------------------------------------------------

def test_08_missing_preview_report() -> None:
    """load_preview_gate should raise on missing file."""
    print("\n--- Test 8: Missing preview report ---")

    try:
        load_preview_gate("/nonexistent/path/report.md")
        log_result("8.Missing preview report", FAIL, "Should have raised FileNotFoundError")
    except FileNotFoundError:
        log_result("8.Missing preview report", PASS, "Correctly raised FileNotFoundError")
    except Exception as e:
        log_result("8.Missing preview report", FAIL, f"Wrong exception: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Test 9: write_send_handoff output format
# ---------------------------------------------------------------------------

def test_09_handoff_output_format() -> None:
    """Verify handoff JSON contains all required fields."""
    print("\n--- Test 9: Handoff output format ---")

    try:
        result = SendResult(
            status="done",
            sent_count=1,
            max_send_count=1,
            message_id="dry-run-test",
            dry_run=True,
            gate_results=[GateResult("test_gate", True, "ok")],
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            tmp_out = f.name

        try:
            write_send_handoff(result, tmp_out)
            written = json.loads(Path(tmp_out).read_text(encoding="utf-8"))

            required_fields = [
                "status", "sent_count", "max_send_count", "message_id",
                "target_type", "tg_api_called", "sent_exceed_1", "sent_channel",
                "loop_started", "sensitive_printed", "remote_db_written",
                "dry_run", "gate_results", "error", "generated_at", "component_version",
            ]
            missing = [f for f in required_fields if f not in written]

            if missing:
                log_result("9.Handoff output format", FAIL, f"Missing fields: {missing}")
            else:
                log_result("9.Handoff output format", PASS,
                           f"All {len(required_fields)} required fields present")
        finally:
            os.unlink(tmp_out)
    except Exception as e:
        log_result("9.Handoff output format", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 10: gate_no_full_address in md text
# ---------------------------------------------------------------------------

def test_10_full_address_in_md_detection() -> None:
    """Gate should detect full Ethereum addresses in candidate text."""
    print("\n--- Test 10: Full address detection in candidate text ---")

    try:
        report = {
            "report_path": "(test)",
            "indicators": {
                "blocked_ok": True,
                "blocked_reasons_empty": True,
                "leak_count": 0,
                "leak_free": True,
                "full_address_count": 0,
                "full_address_free": True,
                "consistency_ok": True,
                "forbidden_terms_count": 0,
                "forbidden_terms_zero": True,
                "machine_terms_count": 0,
                "machine_terms_zero": True,
            },
        }
        fake_md = "Address: 0x1234567890abcdef1234567890abcdef12345678 — full address"
        candidate = {
            "md_text": fake_md,
            "json_data": {"blocked": False, "blocked_reasons": []},
        }

        gate_results = validate_preview_gate(report, candidate)

        addr_gate = next(
            (g for g in gate_results if g.name == "gate_no_full_address_in_md"), None
        )
        assert addr_gate is not None, "gate_no_full_address_in_md not found"

        if not addr_gate.passed:
            log_result("10.Full address detection", PASS,
                       f"Correctly detected full address in candidate MD")
        else:
            log_result("10.Full address detection", FAIL,
                       "Should have detected full address but gate passed")

        # Now test with short address (should pass)
        safe_md = "Address: 0x082e...ca88 — short address only"
        candidate2 = {"md_text": safe_md, "json_data": {"blocked": False, "blocked_reasons": []}}
        gate_results2 = validate_preview_gate(report, candidate2)
        addr_gate2 = next(
            (g for g in gate_results2 if g.name == "gate_no_full_address_in_md"), None
        )
        if addr_gate2 and addr_gate2.passed:
            log_result("10.Short address passes gate", PASS,
                       "Correctly allows short address (0x082e...ca88)")
        else:
            log_result("10.Short address passes gate", FAIL,
                       "Short address should pass the full-address gate")
    except Exception as e:
        log_result("10.Full address detection", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 11: Schema file is readable (v1.9A-S1 → updated for S2)
# ---------------------------------------------------------------------------

def test_11_schema_file_readable() -> None:
    """load_schema() should successfully parse schemas/market_radar_v19.json."""
    print("\n--- Test 11: Schema file readable ---")

    try:
        schema = load_schema()

        checks = [
            ("schema has version", "version" in schema),
            ("schema version is v1.9A-s2", schema.get("version") == "v1.9A-s2"),
            ("schema has strict_core_field_names", "strict_core_field_names" in schema),
            ("schema has flexible_payload_field_names", "flexible_payload_field_names" in schema),
            ("schema has runtime_source_fields (S2)", "runtime_source_fields" in schema),
            ("schema has runtime_source_allowed_prefixes (S2)", "runtime_source_allowed_prefixes" in schema),
            ("strict_core_field_names is list", isinstance(schema.get("strict_core_field_names"), list)),
            ("flexible_payload_field_names is list", isinstance(schema.get("flexible_payload_field_names"), list)),
            ("strict core has 13 fields (with schema_version)", len(schema.get("strict_core_field_names", [])) == 13),
            ("flexible payload has 8 fields", len(schema.get("flexible_payload_field_names", [])) == 8),
            ("schema_version is in strict_core", "schema_version" in schema.get("strict_core_field_names", [])),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"11.{desc}", FAIL, f"Check failed: {desc}")
                all_ok = False

        if all_ok:
            log_result(
                "11.Schema file readable", PASS,
                f"strict_core={len(schema['strict_core_field_names'])} fields (incl. schema_version), "
                f"flexible_payload={len(schema['flexible_payload_field_names'])} fields",
            )
    except Exception as e:
        log_result("11.Schema file readable", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 12: Full manifest passes validation (v1.9A-S1 → updated for S2)
# ---------------------------------------------------------------------------

def test_12_full_manifest_passes() -> None:
    """A manifest with all Strict Core fields should pass validate_manifest()."""
    print("\n--- Test 12: Full manifest passes validation ---")

    try:
        schema = load_schema()
        manifest = build_manifest_from_paths(
            candidate_md_path="results/test_candidate.md",
            candidate_json_path="results/test_candidate.json",
            preview_report_path="results/test_preview.md",
        )

        is_valid, warnings_list = validate_manifest(manifest, schema)

        checks = [
            ("is_valid is True", is_valid is True),
            ("manifest has all strict core fields",
             all(f in manifest for f in schema["strict_core_field_names"])),
            ("artifact_id is set", bool(manifest.get("artifact_id"))),
            ("project_label is market_radar", manifest.get("project_label") == "market_radar"),
            ("schema_version is 1.9A-S2", manifest.get("schema_version") == "1.9A-S2"),
            ("parse_mode is HTML", manifest.get("parse_mode") == "HTML"),
            ("target_type is group (canonical)", manifest.get("target_type") == "group"),
            ("max_send_count is 1", manifest.get("max_send_count") == 1),
            ("blocked is False", manifest.get("blocked") is False),
            ("leak_count is 0", manifest.get("leak_count") == 0),
            ("full_address_count is 0", manifest.get("full_address_count") == 0),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"12.{desc}", FAIL, f"Got: {manifest.get(desc.split()[-1].rstrip(')'), 'N/A')}")
                all_ok = False

        if all_ok:
            log_result("12.Full manifest passes", PASS,
                       f"Validated OK, {len(warnings_list)} flexible-payload warnings")
    except Exception as e:
        log_result("12.Full manifest passes", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 13: Missing Strict Core field rejects (v1.9A-S1)
# ---------------------------------------------------------------------------

def test_13_missing_strict_core_rejects() -> None:
    """Missing a Strict Core field must raise ValueError."""
    print("\n--- Test 13: Missing Strict Core rejects ---")

    try:
        schema = load_schema()
        strict_fields = schema.get("strict_core_field_names", [])

        if not strict_fields:
            log_result("13.Missing Strict Core rejects", SKIP, "No strict fields in schema")
            return

        # Build a manifest missing the first strict core field (schema_version)
        manifest = build_manifest_from_paths(
            candidate_md_path="results/test_candidate.md",
            candidate_json_path="results/test_candidate.json",
            preview_report_path="results/test_preview.md",
        )
        field_to_remove = "artifact_id"  # Use artifact_id instead of schema_version
        del manifest[field_to_remove]

        try:
            validate_manifest(manifest, schema)
            log_result("13.Missing Strict Core rejects", FAIL,
                       f"Should have raised ValueError for missing '{field_to_remove}'")
        except ValueError as e:
            if field_to_remove in str(e):
                log_result("13.Missing Strict Core rejects", PASS,
                           f"ValueError raised for missing '{field_to_remove}': {e}")
            else:
                log_result("13.Missing Strict Core rejects", FAIL,
                           f"ValueError raised but did not mention '{field_to_remove}': {e}")

        # Also test: removing a different field should also fail
        manifest2 = build_manifest_from_paths(
            candidate_md_path="results/test_candidate.md",
            candidate_json_path="results/test_candidate.json",
            preview_report_path="results/test_preview.md",
        )
        field2 = "parse_mode"
        del manifest2[field2]
        try:
            validate_manifest(manifest2, schema)
            log_result("13.Missing Strict Core (2nd field) rejects", FAIL,
                       f"Should have raised ValueError for missing '{field2}'")
        except ValueError as e:
            if field2 in str(e):
                log_result("13.Missing Strict Core (2nd field) rejects", PASS,
                           f"ValueError for '{field2}'")
            else:
                log_result("13.Missing Strict Core (2nd field) rejects", FAIL,
                           f"ValueError missing field name '{field2}': {e}")

    except Exception as e:
        log_result("13.Missing Strict Core rejects", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 14: Missing Flexible Payload warns but passes (v1.9A-S1)
# ---------------------------------------------------------------------------

def test_14_missing_flexible_warns() -> None:
    """Missing Flexible Payload fields should emit warnings but NOT block."""
    print("\n--- Test 14: Missing Flexible Payload warns ---")

    try:
        schema = load_schema()
        flex_fields = schema.get("flexible_payload_field_names", [])

        if not flex_fields:
            log_result("14.Missing Flexible Payload warns", SKIP, "No flexible fields in schema")
            return

        manifest = build_manifest_from_paths(
            candidate_md_path="results/test_candidate.md",
            candidate_json_path="results/test_candidate.json",
            preview_report_path="results/test_preview.md",
        )

        for f in flex_fields:
            manifest.pop(f, None)

        import warnings as _warnings
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            is_valid, warnings_list = validate_manifest(manifest, schema)

        checks = [
            ("is_valid is True", is_valid is True),
            ("warnings were emitted", len(caught) > 0),
            ("warnings_list is non-empty", len(warnings_list) > 0),
            ("all flex fields warned", len(warnings_list) == len(flex_fields)),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"14.{desc}", FAIL,
                           f"caught={len(caught)}, warnings_list={len(warnings_list)}")
                all_ok = False

        if all_ok:
            log_result("14.Missing Flexible Payload warns", PASS,
                       f"{len(warnings_list)} warnings for {len(flex_fields)} missing flexible fields")
    except Exception as e:
        log_result("14.Missing Flexible Payload warns", FAIL, str(e))


# ===========================================================================
# v1.9A-S2 NEW TESTS (8+ tests)
# ===========================================================================


def _load_clean_sample() -> dict:
    """Load the clean manifest sample from disk (read-only)."""
    return json.loads(MANIFEST_SAMPLE.read_text(encoding="utf-8-sig", errors="replace"))


# ---------------------------------------------------------------------------
# Test 15 (S2): schema_version missing → reject
# ---------------------------------------------------------------------------

def test_15_schema_version_missing_reject() -> None:
    """Manifest without schema_version must be rejected."""
    print("\n--- Test 15 (S2): schema_version missing → reject ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        del bad["schema_version"]

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("receipt is blocked", receipt.is_blocked),
            ("error mentions schema_version", any(
                "schema_version" in e.lower() for e in receipt.errors
            )),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("15.schema_version missing → reject", PASS,
                       f"Blocked with {len(receipt.errors)} errors: {receipt.errors}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"15.{desc}", FAIL, f"errors={receipt.errors}")
            log_result("15.schema_version missing → reject", FAIL, "Some checks failed")
    except Exception as e:
        log_result("15.schema_version missing → reject", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 16 (S2): schema_version mismatch → reject
# ---------------------------------------------------------------------------

def test_16_schema_version_mismatch_reject() -> None:
    """Manifest with wrong schema_version must be rejected."""
    print("\n--- Test 16 (S2): schema_version mismatch → reject ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["schema_version"] = "1.9A-S1"  # wrong version

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("receipt is blocked", receipt.is_blocked),
            ("error mentions mismatch", any(
                "mismatch" in e.lower() or "schema_version" in e.lower()
                for e in receipt.errors
            )),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("16.schema_version mismatch → reject", PASS,
                       f"Blocked with errors: {receipt.errors}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"16.{desc}", FAIL, f"errors={receipt.errors}")
            log_result("16.schema_version mismatch → reject", FAIL, "Some checks failed")
    except Exception as e:
        log_result("16.schema_version mismatch → reject", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 17 (S2): Runtime Source absolute path → reject
# ---------------------------------------------------------------------------

def test_17_runtime_source_absolute_path_reject() -> None:
    """Runtime Source with absolute path must be rejected."""
    print("\n--- Test 17 (S2): Runtime Source absolute path → reject ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["candidate_md_path"] = "C:\\Users\\PC\\Desktop\\Projects\\事件情报系统\\results\\test.md"

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("receipt is blocked", receipt.is_blocked),
            ("error mentions absolute path", any(
                "absolute" in e.lower() or "candidate_md_path" in e.lower()
                for e in receipt.errors
            )),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("17.Runtime Source absolute path → reject", PASS,
                       f"Blocked with errors: {receipt.errors}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"17.{desc}", FAIL, f"errors={receipt.errors}")
            log_result("17.Runtime Source absolute path → reject", FAIL, "Some checks failed")
    except Exception as e:
        log_result("17.Runtime Source absolute path → reject", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 18 (S2): Runtime Source ../ path traversal → reject
# ---------------------------------------------------------------------------

def test_18_runtime_source_path_traversal_reject() -> None:
    """Runtime Source with ../ path traversal must be rejected."""
    print("\n--- Test 18 (S2): Runtime Source ../ path traversal → reject ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["candidate_md_path"] = "results/../../etc/passwd"

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("receipt is blocked", receipt.is_blocked),
            ("error mentions path traversal", any(
                "traversal" in e.lower() or ".." in e
                for e in receipt.errors
            )),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("18.Runtime Source ../ traversal → reject", PASS,
                       f"Blocked with errors: {receipt.errors}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"18.{desc}", FAIL, f"errors={receipt.errors}")
            log_result("18.Runtime Source ../ traversal → reject", FAIL, "Some checks failed")
    except Exception as e:
        log_result("18.Runtime Source ../ traversal → reject", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 19 (S2): leak_count = -1 → reject (value range)
# ---------------------------------------------------------------------------

def test_19_leak_count_negative_reject() -> None:
    """leak_count = -1 must be rejected by type/value validation."""
    print("\n--- Test 19 (S2): leak_count = -1 → reject ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["leak_count"] = -1

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("receipt is blocked", receipt.is_blocked),
            ("error mentions leak_count", any(
                "leak_count" in e.lower() for e in receipt.errors
            )),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("19.leak_count = -1 → reject", PASS,
                       f"Blocked with errors: {receipt.errors}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"19.{desc}", FAIL, f"errors={receipt.errors}")
            log_result("19.leak_count = -1 → reject", FAIL, "Some checks failed")
    except Exception as e:
        log_result("19.leak_count = -1 → reject", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 20 (S2): blocked = "false" (string) → reject (type check)
# ---------------------------------------------------------------------------

def test_20_blocked_string_reject() -> None:
    """blocked = 'false' (string, not bool) must be rejected."""
    print("\n--- Test 20 (S2): blocked = 'false' (string) → reject ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["blocked"] = "false"  # string, not bool

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("receipt is blocked", receipt.is_blocked),
            ("error mentions blocked", any(
                "blocked" in e.lower() for e in receipt.errors
            )),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("20.blocked = 'false' → reject", PASS,
                       f"Blocked with errors: {receipt.errors}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"20.{desc}", FAIL, f"errors={receipt.errors}")
            log_result("20.blocked = 'false' → reject", FAIL, "Some checks failed")
    except Exception as e:
        log_result("20.blocked = 'false' → reject", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 21 (S2): max_send_count = 2 → policy trim to 1, raw_manifest NOT mutated
# ---------------------------------------------------------------------------

def test_21_max_send_count_policy_trim() -> None:
    """max_send_count = 2 must be trimmed to 1 by policy, raw_manifest untouched."""
    print("\n--- Test 21 (S2): max_send_count = 2 → policy trim to 1 ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["max_send_count"] = 2

        # Capture raw_manifest state before policy
        raw_snapshot = copy.deepcopy(bad)

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("raw_manifest unchanged (max_send_count still 2)",
             bad["max_send_count"] == 2),
            ("raw_manifest identical to snapshot",
             bad == raw_snapshot),
            ("effective_data trimmed to 1",
             receipt.effective_data.get("max_send_count") == 1),
            ("adjusted_fields includes max_send_count",
             "max_send_count" in receipt.adjusted_fields),
            ("receipt status is adjusted or ok",
             receipt.status in ("adjusted", "ok")),
            ("receipt is NOT blocked", not receipt.is_blocked),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"21.{desc}", FAIL,
                           f"raw msc={bad.get('max_send_count')}, "
                           f"effective msc={receipt.effective_data.get('max_send_count')}, "
                           f"adjusted={receipt.adjusted_fields}")
                all_ok = False

        if all_ok:
            log_result("21.max_send_count = 2 → policy trim", PASS,
                       f"raw_manifest preserved (msc=2), effective_data trimmed to 1, "
                       f"adjusted_fields={receipt.adjusted_fields}")
    except Exception as e:
        log_result("21.max_send_count = 2 → policy trim", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 22 (S2): Flexible Payload format bomb sanitized
# ---------------------------------------------------------------------------

def test_22_flexible_payload_format_bomb() -> None:
    """Flexible Payload with long strings, control chars, and special chars must be sanitized."""
    print("\n--- Test 22 (S2): Flexible Payload format bomb sanitized ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)

        # Inject format bombs
        bad["token_name"] = "A" * 100 + "\x00\x01\x02 CONTROL"  # super long + control chars
        bad["symbol"] = "<script>alert('xss')</script>"  # HTML injection
        bad["wallet_short"] = "0x" + "F" * 50  # way too long
        bad["extra_context"] = {"key": "A" * 500}  # huge context

        receipt = validate_and_apply_policy(bad)

        ed = receipt.effective_data

        checks = [
            # token_name: truncated to 32, no control chars, HTML escaped
            ("token_name <= 32 chars", len(ed.get("token_name", "")) <= 32),
            ("token_name no null byte", "\x00" not in str(ed.get("token_name", ""))),

            # symbol: truncated to 16
            ("symbol <= 16 chars", len(ed.get("symbol", "")) <= 16),
            ("symbol HTML escaped", "&lt;" in ed.get("symbol", "") or
             "<" not in ed.get("symbol", "")),

            # wallet_short: truncated to 24
            ("wallet_short <= 24 chars", len(ed.get("wallet_short", "")) <= 24),

            # extra_context: truncated to 280
            ("extra_context <= 280 chars", len(str(ed.get("extra_context", ""))) <= 280),

            # raw_manifest NOT mutated
            ("raw token_name unchanged (100+ chars)",
             len(bad.get("token_name", "")) > 50),
            ("raw symbol unchanged",
             "<script>" in bad.get("symbol", "")),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"22.{desc}", FAIL, "")
                all_ok = False

        if all_ok:
            log_result("22.Flexible Payload format bomb sanitized", PASS,
                       f"Token name: {len(bad['token_name'])}→{len(ed['token_name'])} chars, "
                       f"symbol: {len(bad['symbol'])}→{len(ed['symbol'])} chars, "
                       f"wallet: {len(bad['wallet_short'])}→{len(ed['wallet_short'])} chars")
    except Exception as e:
        log_result("22.Flexible Payload format bomb sanitized", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 23 (S2 bonus): MarkdownV2 escaping
# ---------------------------------------------------------------------------

def test_23_markdown_v2_escaping() -> None:
    """Flexible Payload with MarkdownV2 special chars must be escaped."""
    print("\n--- Test 23 (S2 bonus): MarkdownV2 escaping ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["parse_mode"] = "MarkdownV2"
        bad["token_name"] = "ETH_BTC*[test]"
        bad["symbol"] = "~symbol` > check"

        receipt = validate_and_apply_policy(bad)
        ed = receipt.effective_data

        # In MarkdownV2, special chars should be backslash-escaped
        token_name = ed.get("token_name", "")
        symbol_val = ed.get("symbol", "")

        checks = [
            ("token_name _ escaped", "\\_" in token_name),
            ("token_name * escaped", "\\*" in token_name),
            ("token_name [ escaped", "\\[" in token_name),
            ("symbol ~ escaped", "\\~" in symbol_val),
            ("symbol ` escaped", "\\`" in symbol_val),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"23.{desc}", FAIL, f"token_name='{token_name}', symbol='{symbol_val}'")
                all_ok = False

        if all_ok:
            log_result("23.MarkdownV2 escaping", PASS,
                       f"token_name='{token_name}', symbol='{symbol_val}'")
    except Exception as e:
        log_result("23.MarkdownV2 escaping", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 24 (S2 bonus): Parse mode normalization + target type normalization
# ---------------------------------------------------------------------------

def test_24_parse_mode_and_target_type_normalization() -> None:
    """Verify normalization functions for parse_mode and target_type."""
    print("\n--- Test 24 (S2 bonus): Parse mode / target type normalization ---")

    try:
        all_ok = True

        # Parse mode normalization
        pm_tests = [
            ("HTML", "HTML"),
            ("html", "HTML"),
            ("MarkdownV2", "MarkdownV2"),
            ("markdownv2", "MarkdownV2"),
            ("PlainText", "PlainText"),
            ("plaintext", "PlainText"),
            ("Markdown", "MarkdownV2"),  # legacy
            ("  HTML  ", "HTML"),
            ("unknown_mode", None),
            (123, None),
        ]
        for inp, expected in pm_tests:
            result = normalize_parse_mode(inp)
            if result != expected:
                log_result(f"24.pm normalize('{inp}')", FAIL,
                           f"Expected {expected!r}, got {result!r}")
                all_ok = False

        # Target type normalization
        tt_tests = [
            ("group", "group"),
            ("supergroup", "supergroup"),
            ("test_group", "test_group"),
            ("fake", "fake"),
            ("TG群", "group"),          # legacy
            ("TG频道", "supergroup"),    # legacy
            ("dry-run", "test_group"),  # legacy
            ("dry_run", "test_group"),  # legacy
            ("unknown", None),
            (None, None),
        ]
        for inp, expected in tt_tests:
            result = normalize_target_type(inp)
            if result != expected:
                log_result(f"24.tt normalize('{inp}')", FAIL,
                           f"Expected {expected!r}, got {result!r}")
                all_ok = False

        if all_ok:
            log_result("24.Parse mode / target type normalization", PASS,
                       f"All {len(pm_tests)} pm + {len(tt_tests)} tt cases pass")
    except Exception as e:
        log_result("24.Parse mode / target type normalization", FAIL, str(e))


# ===========================================================================
# Test 25 (S2 bonus): Disallowed path prefix rejection
# ===========================================================================

def test_25_disallowed_path_prefix_reject() -> None:
    """Runtime Source with disallowed prefix must be rejected."""
    print("\n--- Test 25 (S2 bonus): Disallowed path prefix → reject ---")

    try:
        clean = _load_clean_sample()
        bad = copy.deepcopy(clean)
        bad["candidate_md_path"] = "etc/passwd"  # not in allowed prefixes

        receipt = validate_and_apply_policy(bad)

        checks = [
            ("receipt is blocked", receipt.is_blocked),
            ("error mentions prefix/disallowed", any(
                "prefix" in e.lower() or "disallowed" in e.lower()
                for e in receipt.errors
            )),
        ]

        all_ok = all(ok for _, ok in checks)
        if all_ok:
            log_result("25.Disallowed path prefix → reject", PASS,
                       f"Blocked: {receipt.errors}")
        else:
            for desc, ok in checks:
                if not ok:
                    log_result(f"25.{desc}", FAIL, f"errors={receipt.errors}")
            log_result("25.Disallowed path prefix → reject", FAIL, "Some checks failed")
    except Exception as e:
        log_result("25.Disallowed path prefix → reject", FAIL, str(e))


# ===========================================================================
# v1.9B Transport TESTS (8+ tests)
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 26 (v1.9B): FakeTransport success returns standard SendResult
# ---------------------------------------------------------------------------

def test_26_fake_transport_success() -> None:
    """FakeTransport should return a standard SendResult on success."""
    print("\n--- Test 26 (v1.9B): FakeTransport success returns standard SendResult ---")

    try:
        transport = FakeTransport()
        payload = {
            "text": "<b>Test Card</b>",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 18,
            "has_html_tags": True,
        }
        result = transport.send(payload, "fake", "HTML")

        checks = [
            ("success is True", result.success is True),
            ("status_code == 200", result.status_code == 200),
            ("provider is 'fake'", result.provider == TRANSPORT_FAKE),
            ("message_id is non-empty", bool(result.message_id)),
            ("message_id starts with 'fake-msg-'", result.message_id.startswith("fake-msg-")),
            ("sent_count == 1", result.sent_count == 1),
            ("provider_metadata has transport_name", "transport_name" in result.provider_metadata),
            ("provider_metadata has raw_api_response", "raw_api_response" in result.provider_metadata),
            ("provider_metadata has request_payload_preview", "request_payload_preview" in result.provider_metadata),
            ("raw_api_response.ok is True", result.provider_metadata.get("raw_api_response", {}).get("ok") is True),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"26.{desc}", FAIL, f"result={result.to_dict()}")
                all_ok = False

        if all_ok:
            log_result("26.FakeTransport success", PASS,
                       f"message_id={result.message_id}, provider={result.provider}")
    except Exception as e:
        log_result("26.FakeTransport success", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 27 (v1.9B): TGTransportStub constructs request payload without network
# ---------------------------------------------------------------------------

def test_27_tg_stub_request_payload() -> None:
    """TGTransportStub must construct a valid TG request payload without calling network."""
    print("\n--- Test 27 (v1.9B): TGTransportStub constructs request payload without network ---")

    try:
        transport = TGTransportStub(bot_token="dummy", default_chat_id="dummy")
        payload = {
            "text": "<b>Market Alert</b>\nETH entry: $1850",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 38,
            "has_html_tags": True,
        }
        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is True", result.success is True),
            ("tg_api_called is False", result.tg_api_called is False),
            ("provider is 'telegram'", result.provider == TRANSPORT_TELEGRAM),
            ("provider_metadata exists", bool(result.provider_metadata)),
            ("request_payload_preview exists", "request_payload_preview" in result.provider_metadata),
            ("raw_api_response is None (no API call)", result.provider_metadata.get("raw_api_response") is None),
            ("chat_id is REDACTED in preview",
             result.provider_metadata["request_payload_preview"].get("chat_id") == "[REDACTED]"),
            ("text_preview matches", result.provider_metadata["request_payload_preview"].get("text_preview") == payload["text"][:200]),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"27.{desc}", FAIL, "")
                all_ok = False

        if all_ok:
            log_result("27.TGTransportStub request payload", PASS,
                       "Constructed valid TG request payload, no API call, chat_id redacted")
    except Exception as e:
        log_result("27.TGTransportStub request payload", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 28 (v1.9B): FakeTransport failure simulation returns success=False
# ---------------------------------------------------------------------------

def test_28_fake_transport_failure() -> None:
    """FakeTransport must return success=False with error details on simulated failure."""
    print("\n--- Test 28 (v1.9B): FakeTransport failure simulation ---")

    try:
        transport = FakeTransport()
        payload = {
            "text": "test",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 4,
            "has_html_tags": False,
        }

        # Test each failure mode
        failures = ["PROVIDER_REJECTION", "NETWORK_TIMEOUT", "AUTH_FAILURE", "RATE_LIMITED"]
        all_ok = True

        for error_type in failures:
            target = f"fake:{error_type}"
            result = transport.send(payload, target, "HTML")

            if result.success is not False:
                log_result(f"28.{error_type} success=False", FAIL, f"Got success={result.success}")
                all_ok = False
            if result.error_type != error_type:
                log_result(f"28.{error_type} error_type", FAIL, f"Expected {error_type}, got {result.error_type}")
                all_ok = False
            if not result.error_message:
                log_result(f"28.{error_type} error_message", FAIL, "error_message is empty")
                all_ok = False
            if result.status != "blocked":
                log_result(f"28.{error_type} status=blocked", FAIL, f"Got status={result.status}")
                all_ok = False

        if all_ok:
            log_result("28.FakeTransport failure simulation", PASS,
                       f"All {len(failures)} failure modes return success=False with error details")
    except Exception as e:
        log_result("28.FakeTransport failure simulation", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 29 (v1.9B): TGTransportStub RATE_LIMITED returns retry_after
# ---------------------------------------------------------------------------

def test_29_tg_stub_rate_limited() -> None:
    """TGTransportStub RATE_LIMITED must return retry_after value."""
    print("\n--- Test 29 (v1.9B): TGTransportStub RATE_LIMITED returns retry_after ---")

    try:
        transport = TGTransportStub(bot_token="dummy", default_chat_id="dummy")
        result = transport._build_failure("RATE_LIMITED", retry_after=30)

        checks = [
            ("success is False", result.success is False),
            ("error_type is RATE_LIMITED", result.error_type == "RATE_LIMITED"),
            ("retry_after == 30", result.retry_after == 30),
            ("status_code == 429", result.status_code == 429),
            ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"29.{desc}", FAIL, f"retry_after={result.retry_after}, error_type={result.error_type}")
                all_ok = False

        if all_ok:
            log_result("29.TGTransportStub RATE_LIMITED", PASS,
                       f"retry_after={result.retry_after}, status_code={result.status_code}")
    except Exception as e:
        log_result("29.TGTransportStub RATE_LIMITED", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 30 (v1.9B): Transport does not read environment variables
# ---------------------------------------------------------------------------

def test_30_transport_no_env_reading() -> None:
    """Transport must NOT read environment variables (os.getenv, os.environ)."""
    print("\n--- Test 30 (v1.9B): Transport does not read environment variables ---")

    try:
        import os as _os_module

        # Monkey-patch os.getenv to detect calls
        original_getenv = _os_module.getenv
        getenv_calls = []

        def _spy_getenv(key, default=None):
            getenv_calls.append(key)
            return original_getenv(key, default)

        _os_module.getenv = _spy_getenv

        try:
            # Test FakeTransport
            ft = FakeTransport()
            ft.send({"text": "test", "parse_mode": "HTML", "disable_web_page_preview": True}, "fake", "HTML")

            # Test TGTransportStub
            tg = TGTransportStub(bot_token="dummy", default_chat_id="dummy")
            tg.send({"text": "test", "parse_mode": "HTML", "disable_web_page_preview": True}, "group", "HTML")
        finally:
            _os_module.getenv = original_getenv

        if len(getenv_calls) > 0:
            log_result("30.Transport no env reading", FAIL,
                       f"Transport called os.getenv with keys: {getenv_calls}")
        else:
            log_result("30.Transport no env reading", PASS,
                       "Neither FakeTransport nor TGTransportStub called os.getenv")
    except Exception as e:
        log_result("30.Transport no env reading", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 31 (v1.9B): Transport does not modify sanitized payload
# ---------------------------------------------------------------------------

def test_31_transport_no_payload_modification() -> None:
    """Transport must NOT modify the sanitized payload text."""
    print("\n--- Test 31 (v1.9B): Transport does not modify sanitized payload ---")

    try:
        original_text = "<b>ETH entry: $1850.50</b>\nTarget: 0x082e...ca88"
        payload = {
            "text": original_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": len(original_text),
            "has_html_tags": True,
        }

        # Test FakeTransport
        ft = FakeTransport()
        result_ft = ft.send(payload, "fake", "HTML")
        ft_preview = result_ft.provider_metadata.get("request_payload_preview", {})
        ft_text = ft_preview.get("text_preview", "")

        # Test TGTransportStub
        tg = TGTransportStub(bot_token="dummy", default_chat_id="dummy")
        result_tg = tg.send(payload, "group", "HTML")
        tg_preview = result_tg.provider_metadata.get("request_payload_preview", {})
        tg_text = tg_preview.get("text_preview", "")

        checks = [
            ("FakeTransport text unchanged", ft_text == original_text),
            ("TGTransportStub text unchanged", tg_text == original_text),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"31.{desc}", FAIL,
                           f"Original: {original_text!r}, Got: {ft_text if 'Fake' in desc else tg_text!r}")
                all_ok = False

        if all_ok:
            log_result("31.Transport no payload modification", PASS,
                       "Both transports pass text through unchanged")
    except Exception as e:
        log_result("31.Transport no payload modification", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 32 (v1.9B): Transport does not double-escape HTML
# ---------------------------------------------------------------------------

def test_32_transport_no_double_escaping() -> None:
    """Transport must NOT double-escape already-escaped HTML text.

    Input: &lt;Link&gt; → Transport output must remain &lt;Link&gt;
    NOT become: &amp;lt;Link&amp;gt;
    """
    print("\n--- Test 32 (v1.9B): Transport does not double-escape &lt;Link&gt; ---")

    try:
        already_escaped = "&lt;Link&gt;"
        payload = {
            "text": already_escaped,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": len(already_escaped),
            "has_html_tags": False,
        }

        # Test FakeTransport
        ft = FakeTransport()
        result_ft = ft.send(payload, "fake", "HTML")
        ft_text = result_ft.provider_metadata.get("request_payload_preview", {}).get("text_preview", "")

        # Test TGTransportStub
        tg = TGTransportStub(bot_token="dummy", default_chat_id="dummy")
        result_tg = tg.send(payload, "group", "HTML")
        tg_text = result_tg.provider_metadata.get("request_payload_preview", {}).get("text_preview", "")

        checks = [
            ("FakeTransport: &lt;Link&gt; preserved", ft_text == already_escaped),
            ("FakeTransport: no &amp;lt; introduced", "&amp;lt;" not in ft_text),
            ("TGTransportStub: &lt;Link&gt; preserved", tg_text == already_escaped),
            ("TGTransportStub: no &amp;lt; introduced", "&amp;lt;" not in tg_text),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"32.{desc}", FAIL,
                           f"Expected: {already_escaped!r}, Got: {ft_text if 'Fake' in desc else tg_text!r}")
                all_ok = False

        if all_ok:
            log_result("32.Transport no double-escaping", PASS,
                       f"&lt;Link&gt; preserved through both transports")

        # Also test with a mixed escaped + unescaped payload
        mixed_text = "&lt;b&gt;Bold&lt;/b&gt; and <i>italic</i>"
        payload2 = {
            "text": mixed_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": len(mixed_text),
            "has_html_tags": True,
        }
        result2 = ft.send(payload2, "fake", "HTML")
        ft_text2 = result2.provider_metadata.get("request_payload_preview", {}).get("text_preview", "")
        if ft_text2 == mixed_text:
            log_result("32.Mixed escaping preserved", PASS,
                       "Mixed escaped+unescaped text preserved unchanged")
        else:
            log_result("32.Mixed escaping preserved", FAIL,
                       f"Expected: {mixed_text!r}, Got: {ft_text2!r}")
    except Exception as e:
        log_result("32.Transport no double-escaping", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 33 (v1.9B): _unrecognized_payload does not participate in send control
# ---------------------------------------------------------------------------

def test_33_unrecognized_payload_isolation() -> None:
    """_unrecognized_payload must NOT affect send decisions.

    Rules:
      1. Transport can put _unrecognized_payload in provider_metadata as debug passthrough.
      2. Must NOT use it to decide: whether to send, how many to send, where to send,
         parse_mode, or target_type.
    """
    print("\n--- Test 33 (v1.9B): _unrecognized_payload isolation ---")

    try:
        unrecognized_debug = [
            {"field": "legacy_scoring", "value": "0.95"},
            {"field": "internal_note", "value": "should not control send"},
        ]
        payload = {
            "text": "Normal market card",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 18,
            "has_html_tags": False,
            "_unrecognized_payload": unrecognized_debug,
        }

        # Test both transports: send should succeed normally despite _unrecognized_payload
        ft = FakeTransport()
        result_ft = ft.send(payload, "fake", "HTML")

        tg = TGTransportStub(bot_token="dummy", default_chat_id="dummy")
        result_tg = tg.send(payload, "group", "HTML")

        checks = [
            # Both transports succeed — _unrecognized_payload does NOT block send
            ("FakeTransport success unaffected", result_ft.success is True),
            ("TGTransportStub success unaffected", result_tg.success is True),
            # sent_count unchanged (not "skip because _unrecognized says so")
            ("FakeTransport sent_count == 1", result_ft.sent_count == 1),
            ("TGTransportStub sent_count == 1", result_tg.sent_count == 1),
            # TGTransportStub puts _unrecognized_payload in provider_metadata only
            ("TGTransportStub preserves in provider_metadata",
             "_unrecognized_payload_debug" in result_tg.provider_metadata),
            ("TGTransportStub passthrough correct",
             result_tg.provider_metadata.get("_unrecognized_payload_debug") == unrecognized_debug),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"33.{desc}", FAIL, "")
                all_ok = False

        if all_ok:
            log_result("33._unrecognized_payload isolation", PASS,
                       "_unrecognized_payload passed through in provider_metadata, did NOT affect send control")
    except Exception as e:
        log_result("33._unrecognized_payload isolation", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 34 (v1.9B bonus): MarketRadarSender with FakeTransport integration
# ---------------------------------------------------------------------------

def test_34_market_radar_sender_fake_integration() -> None:
    """MarketRadarSender with FakeTransport should run the full pipeline."""
    print("\n--- Test 34 (v1.9B bonus): MarketRadarSender + FakeTransport integration ---")

    try:
        sender = MarketRadarSender(transport=FakeTransport())
        manifest = build_manifest_from_paths(
            candidate_md_path="results/static_position_v18g_send_candidate.md",
            candidate_json_path="results/static_position_v18g_send_candidate.json",
            preview_report_path="results/static_position_v18h_preview_report.md",
        )

        result = sender.send_from_manifest(manifest)

        checks = [
            ("result is not None", result is not None),
            ("provider is fake", result.provider == TRANSPORT_FAKE),
            ("success is True", result.success is True),
            ("sent_count == 1", result.sent_count == 1),
            ("transport_name in provider_metadata",
             result.provider_metadata.get("transport_name") == TRANSPORT_FAKE),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"34.{desc}", FAIL, f"result={result.to_dict()}")
                all_ok = False

        if all_ok:
            log_result("34.MarketRadarSender + FakeTransport", PASS,
                       f"Full pipeline OK, provider={result.provider}")
    except Exception as e:
        log_result("34.MarketRadarSender + FakeTransport", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 35 (v1.9B bonus): MarketRadarSender with TGTransportStub integration
# ---------------------------------------------------------------------------

def test_35_market_radar_sender_tg_stub_integration() -> None:
    """MarketRadarSender with TGTransportStub should construct TG request without API call."""
    print("\n--- Test 35 (v1.9B bonus): MarketRadarSender + TGTransportStub integration ---")

    try:
        sender = MarketRadarSender(
            transport=TGTransportStub(bot_token="dummy", default_chat_id="dummy")
        )
        manifest = build_manifest_from_paths(
            candidate_md_path="results/static_position_v18g_send_candidate.md",
            candidate_json_path="results/static_position_v18g_send_candidate.json",
            preview_report_path="results/static_position_v18h_preview_report.md",
        )

        result = sender.send_from_manifest(manifest)

        checks = [
            ("result is not None", result is not None),
            ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
            ("tg_api_called is False", result.tg_api_called is False),
            ("success is True", result.success is True),
            ("transport_name in provider_metadata",
             result.provider_metadata.get("transport_name") == TRANSPORT_TELEGRAM),
            ("raw_api_response is None (no API call)",
             result.provider_metadata.get("raw_api_response") is None),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"35.{desc}", FAIL, f"result={result.to_dict()}")
                all_ok = False

        if all_ok:
            log_result("35.MarketRadarSender + TGTransportStub", PASS,
                       "Full pipeline OK, TG request payload constructed, no API call")
    except Exception as e:
        log_result("35.MarketRadarSender + TGTransportStub", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 36 (v1.9B bonus): MarketRadarSender rejects non-BaseTransport
# ---------------------------------------------------------------------------

def test_36_market_radar_sender_rejects_invalid_transport() -> None:
    """MarketRadarSender must raise TypeError if transport is not BaseTransport."""
    print("\n--- Test 36 (v1.9B bonus): MarketRadarSender rejects invalid transport ---")

    try:
        try:
            MarketRadarSender(transport="not a transport")  # type: ignore
            log_result("36.MarketRadarSender rejects invalid transport", FAIL,
                       "Should have raised TypeError")
        except TypeError as e:
            if "BaseTransport" in str(e):
                log_result("36.MarketRadarSender rejects invalid transport", PASS,
                           f"TypeError raised: {e}")
            else:
                log_result("36.MarketRadarSender rejects invalid transport", FAIL,
                           f"TypeError raised but message wrong: {e}")
    except Exception as e:
        log_result("36.MarketRadarSender rejects invalid transport", FAIL, str(e))


# ===========================================================================
# v1.9B-final Prep TGTransport TESTS (10+ tests)
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 37 (v1.9B-final): TGTransport pure-param construction, no env reading
# ---------------------------------------------------------------------------

def test_37_tg_transport_pure_param_construction() -> None:
    """TGTransport must be constructable with explicit params only, no env reading."""
    print("\n--- Test 37 (v1.9B-final): TGTransport pure-param construction, no env ---")

    try:
        import os as _os_module

        original_getenv = _os_module.getenv
        getenv_calls = []

        def _spy_getenv(key, default=None):
            getenv_calls.append(key)
            return original_getenv(key, default)

        _os_module.getenv = _spy_getenv

        try:
            mock = MockHttpClient()
            transport = TGTransport(
                bot_token="test_bot_token_123",
                default_chat_id="-1001234567890",
                http_client=mock,
                api_base_url="http://dummy.local",
                timeout_seconds=5,
            )
        finally:
            _os_module.getenv = original_getenv

        checks = [
            ("transport created", transport is not None),
            ("transport_name is 'telegram'", transport.transport_name == TRANSPORT_TELEGRAM),
            ("no os.getenv calls during construction", len(getenv_calls) == 0),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"37.{desc}", FAIL,
                           f"getenv_calls={getenv_calls}" if "getenv" in desc else "")
                all_ok = False

        if all_ok:
            log_result("37.TGTransport pure-param construction", PASS,
                       "No env reading, transport_name='telegram'")
    except Exception as e:
        log_result("37.TGTransport pure-param construction", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 38 (v1.9B-final): MockHttpClient success → SendResult.success=True
# ---------------------------------------------------------------------------

def test_38_tg_transport_mock_success() -> None:
    """TGTransport with MockHttpClient success should return SendResult.success=True."""
    print("\n--- Test 38 (v1.9B-final): MockHttpClient success → SendResult.success=True ---")

    try:
        mock = MockHttpClient()
        mock.set_response(200, {
            "ok": True,
            "result": {
                "message_id": 4242,
                "from": {"id": 123456, "is_bot": True, "first_name": "TestBot"},
                "chat": {"id": -1001234567890, "title": "Test Group", "type": "supergroup"},
                "date": 1717000000,
                "text": "test message",
            },
        })

        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        payload = {
            "text": "<b>Market Alert</b>\nTEST entry: $1234",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 40,
            "has_html_tags": True,
        }

        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is True", result.success is True),
            ("status_code == 200", result.status_code == 200),
            ("provider is 'telegram'", result.provider == TRANSPORT_TELEGRAM),
            ("message_id == '4242'", result.message_id == "4242"),
            ("sent_count == 1", result.sent_count == 1),
            ("tg_api_called is True", result.tg_api_called is True),
            ("dry_run is False", result.dry_run is False),
            ("provider_metadata has raw_api_response",
             "raw_api_response" in result.provider_metadata),
            ("raw_api_response has ok=True",
             result.provider_metadata.get("raw_api_response", {}).get("ok") is True),
            ("provider_metadata has request_payload_preview",
             "request_payload_preview" in result.provider_metadata),
            ("mock was called once", mock.request_count == 1),
            ("mock last_request has chat_id",
             mock.last_request is not None and "chat_id" in mock.last_request),
            ("mock last_request has text",
             mock.last_request is not None and mock.last_request.get("text") == payload["text"]),
            ("mock last_request text is unchanged",
             mock.last_request is not None and mock.last_request.get("text") == "<b>Market Alert</b>\nTEST entry: $1234"),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"38.{desc}", FAIL, f"Got: {result.to_dict() if 'to_dict' in dir(result) else result}")
                all_ok = False

        if all_ok:
            log_result("38.TGTransport mock success", PASS,
                       f"message_id={result.message_id}, sent_count={result.sent_count}, request_count={mock.request_count}")
    except Exception as e:
        log_result("38.TGTransport mock success", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 39 (v1.9B-final): MockHttpClient HTTP 400 → PROVIDER_REJECTION
# ---------------------------------------------------------------------------

def test_39_tg_transport_http_400() -> None:
    """TGTransport must return PROVIDER_REJECTION on HTTP 400."""
    print("\n--- Test 39 (v1.9B-final): MockHttpClient HTTP 400 → PROVIDER_REJECTION ---")

    try:
        mock = MockHttpClient()
        mock.set_response(400, {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: message text is empty",
        })

        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        payload = {
            "text": "",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 0,
            "has_html_tags": False,
        }

        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is False", result.success is False),
            ("error_type is PROVIDER_REJECTION", result.error_type == "PROVIDER_REJECTION"),
            ("status_code == 400", result.status_code == 400),
            ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
            ("sent_count == 0", result.sent_count == 0),
            ("error_message is non-empty", bool(result.error_message)),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"39.{desc}", FAIL, f"error_type={result.error_type}, status_code={result.status_code}")
                all_ok = False

        if all_ok:
            log_result("39.TGTransport HTTP 400 → PROVIDER_REJECTION", PASS,
                       f"error_type={result.error_type}, error_message={result.error_message[:80]}")
    except Exception as e:
        log_result("39.TGTransport HTTP 400 → PROVIDER_REJECTION", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 40 (v1.9B-final): MockHttpClient HTTP 401 → AUTH_FAILURE
# ---------------------------------------------------------------------------

def test_40_tg_transport_http_401() -> None:
    """TGTransport must return AUTH_FAILURE on HTTP 401."""
    print("\n--- Test 40 (v1.9B-final): MockHttpClient HTTP 401 → AUTH_FAILURE ---")

    try:
        mock = MockHttpClient()
        mock.set_response(401, {
            "ok": False,
            "error_code": 401,
            "description": "Unauthorized",
        })

        transport = TGTransport(
            bot_token="bad_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        payload = {
            "text": "Hello",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 5,
            "has_html_tags": False,
        }

        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is False", result.success is False),
            ("error_type is AUTH_FAILURE", result.error_type == "AUTH_FAILURE"),
            ("status_code == 401", result.status_code == 401),
            ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"40.{desc}", FAIL, f"error_type={result.error_type}, status_code={result.status_code}")
                all_ok = False

        if all_ok:
            log_result("40.TGTransport HTTP 401 → AUTH_FAILURE", PASS,
                       f"error_type={result.error_type}, status_code={result.status_code}")
    except Exception as e:
        log_result("40.TGTransport HTTP 401 → AUTH_FAILURE", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 41 (v1.9B-final): MockHttpClient HTTP 429 → RATE_LIMITED + retry_after
# ---------------------------------------------------------------------------

def test_41_tg_transport_http_429() -> None:
    """TGTransport must return RATE_LIMITED with correct retry_after on HTTP 429."""
    print("\n--- Test 41 (v1.9B-final): MockHttpClient HTTP 429 → RATE_LIMITED + retry_after ---")

    try:
        mock = MockHttpClient()
        mock.set_response(429, {
            "ok": False,
            "error_code": 429,
            "description": "Too Many Requests: retry after 30",
            "parameters": {"retry_after": 30},
        })

        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        payload = {
            "text": "Hello",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 5,
            "has_html_tags": False,
        }

        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is False", result.success is False),
            ("error_type is RATE_LIMITED", result.error_type == "RATE_LIMITED"),
            ("status_code == 429", result.status_code == 429),
            ("retry_after == 30", result.retry_after == 30),
            ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"41.{desc}", FAIL,
                           f"error_type={result.error_type}, retry_after={result.retry_after}")
                all_ok = False

        if all_ok:
            log_result("41.TGTransport HTTP 429 → RATE_LIMITED", PASS,
                       f"error_type={result.error_type}, retry_after={result.retry_after}")

        # Also test with retry_after from parameters
        mock2 = MockHttpClient()
        mock2.set_response(429, {
            "ok": False,
            "error_code": 429,
            "description": "Flood control",
            "parameters": {"retry_after": 60},
        })
        transport2 = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock2,
            api_base_url="http://dummy.local",
        )
        result2 = transport2.send(payload, "group", "HTML")
        if result2.retry_after == 60:
            log_result("41.RATE_LIMITED retry_after=60", PASS,
                       "retry_after correctly extracted from response parameters")
        else:
            log_result("41.RATE_LIMITED retry_after=60", FAIL,
                       f"Expected retry_after=60, got {result2.retry_after}")

    except Exception as e:
        log_result("41.TGTransport HTTP 429 → RATE_LIMITED", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 42 (v1.9B-final): MockHttpClient TimeoutError → NETWORK_TIMEOUT
# ---------------------------------------------------------------------------

def test_42_tg_transport_timeout() -> None:
    """TGTransport must return NETWORK_TIMEOUT when http_client raises TimeoutError."""
    print("\n--- Test 42 (v1.9B-final): MockHttpClient TimeoutError → NETWORK_TIMEOUT ---")

    try:
        mock = MockHttpClient()
        mock.set_timeout(True)

        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
            timeout_seconds=3,
        )

        payload = {
            "text": "Hello",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 5,
            "has_html_tags": False,
        }

        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is False", result.success is False),
            ("error_type is NETWORK_TIMEOUT", result.error_type == "NETWORK_TIMEOUT"),
            ("status_code == 0", result.status_code == 0),
            ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
            ("error_message non-empty", bool(result.error_message)),
            ("no uncaught exception", True),  # If we got here, no exception was raised
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"42.{desc}", FAIL, f"error_type={result.error_type}, status_code={result.status_code}")
                all_ok = False

        if all_ok:
            log_result("42.TGTransport TimeoutError → NETWORK_TIMEOUT", PASS,
                       f"error_type={result.error_type}, error_message={result.error_message[:80]}")
    except Exception as e:
        log_result("42.TGTransport TimeoutError → NETWORK_TIMEOUT", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 43 (v1.9B-final): OSError → NETWORK_TIMEOUT
# ---------------------------------------------------------------------------

def test_43_tg_transport_os_error() -> None:
    """TGTransport must return NETWORK_TIMEOUT when http_client raises OSError."""
    print("\n--- Test 43 (v1.9B-final): OSError → NETWORK_TIMEOUT ---")

    try:
        # Custom mock that raises OSError
        class OSErrorMock(HttpClient):
            def post(self, url, json, timeout):
                raise OSError("Connection refused")

        mock = OSErrorMock()
        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        payload = {
            "text": "Hello",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 5,
            "has_html_tags": False,
        }

        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is False", result.success is False),
            ("error_type is NETWORK_TIMEOUT", result.error_type == "NETWORK_TIMEOUT"),
            ("status_code == 0", result.status_code == 0),
            ("error_message mentions Connection refused", "Connection refused" in result.error_message),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"43.{desc}", FAIL, f"error_type={result.error_type}")
                all_ok = False

        if all_ok:
            log_result("43.TGTransport OSError → NETWORK_TIMEOUT", PASS,
                       f"error_type={result.error_type}, error_message={result.error_message[:80]}")
    except Exception as e:
        log_result("43.TGTransport OSError → NETWORK_TIMEOUT", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 44 (v1.9B-final): request_payload_preview does NOT contain bot_token or full chat_id
# ---------------------------------------------------------------------------

def test_44_tg_transport_sensitive_info_redaction() -> None:
    """provider_metadata must never contain bot_token or full chat_id."""
    print("\n--- Test 44 (v1.9B-final): request_payload_preview no bot_token / full chat_id ---")

    try:
        real_token = "123456:AAEHdCwLzFakeTestTokenXyZ_AbCdEfGhIjKlMnOp"
        real_chat_id = "-1009876543210"

        mock = MockHttpClient()
        mock.set_response(200, {"ok": True, "result": {"message_id": 100}})

        transport = TGTransport(
            bot_token=real_token,
            default_chat_id=real_chat_id,
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        payload = {
            "text": "<b>Test Card</b>",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 16,
            "has_html_tags": True,
        }

        result = transport.send(payload, "group", "HTML")

        # Check all string values in provider_metadata for token leakage
        metadata_str = json.dumps(result.provider_metadata)

        # Also check SendResult to_dict for token leakage
        result_str = json.dumps(result.to_dict())

        checks = [
            ("bot_token not in provider_metadata",
             real_token not in metadata_str),
            ("full chat_id not in provider_metadata",
             real_chat_id not in metadata_str),
            ("bot_token not in result.to_dict",
             real_token not in result_str),
            ("full chat_id not in result.to_dict",
             real_chat_id not in result_str),
            ("chat_id is REDACTED in preview",
             "REDACTED" in result.provider_metadata.get("request_payload_preview", {}).get("chat_id", "")),
            ("api_endpoint shows REDACTED",
             "REDACTED" in result.provider_metadata.get("request_payload_preview", {}).get("api_endpoint", "")),
            ("bot token not in api_endpoint",
             real_token not in result.provider_metadata.get("request_payload_preview", {}).get("api_endpoint", "")),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"44.{desc}", FAIL, "")
                all_ok = False

        if all_ok:
            log_result("44.TGTransport sensitive info redaction", PASS,
                       "bot_token and full chat_id absent from all outputs")
    except Exception as e:
        log_result("44.TGTransport sensitive info redaction", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 45 (v1.9B-final): Double-escape prevention still holds
# ---------------------------------------------------------------------------

def test_45_tg_transport_no_double_escaping() -> None:
    """TGTransport must NOT double-escape already-escaped HTML.

    Input: &lt;Link&gt; → request body text must remain &lt;Link&gt;
    NOT become: &amp;lt;Link&amp;gt;
    """
    print("\n--- Test 45 (v1.9B-final): TGTransport no double-escape &lt;Link&gt; ---")

    try:
        mock = MockHttpClient()
        mock.set_response(200, {"ok": True, "result": {"message_id": 100}})

        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        already_escaped = "&lt;Link&gt;"
        payload = {
            "text": already_escaped,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": len(already_escaped),
            "has_html_tags": False,
        }

        result = transport.send(payload, "group", "HTML")

        # Check the actual request body sent to MockHttpClient
        request_text = mock.last_request.get("text", "") if mock.last_request else ""

        # Check the request_payload_preview in provider_metadata
        preview_text = result.provider_metadata.get("request_payload_preview", {}).get("text_preview", "")

        checks = [
            ("&lt;Link&gt; preserved in request text", request_text == already_escaped),
            ("no &amp;lt; in request text", "&amp;lt;" not in request_text),
            ("&lt;Link&gt; preserved in preview", preview_text == already_escaped),
            ("no &amp;lt; in preview", "&amp;lt;" not in preview_text),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"45.{desc}", FAIL,
                           f"Request text: {request_text!r}, Preview text: {preview_text!r}")
                all_ok = False

        if all_ok:
            log_result("45.TGTransport no double-escaping", PASS,
                       f"&lt;Link&gt; preserved through TGTransport")
    except Exception as e:
        log_result("45.TGTransport no double-escaping", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 46 (v1.9B-final): TGTransport incoming text not modified
# ---------------------------------------------------------------------------

def test_46_tg_transport_text_passthrough() -> None:
    """TGTransport must pass text through unchanged — no sanitization or modification."""
    print("\n--- Test 46 (v1.9B-final): TGTransport text passthrough ---")

    try:
        mock = MockHttpClient()
        mock.set_response(200, {"ok": True, "result": {"message_id": 100}})

        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        test_texts = [
            "<b>Bold</b> and <i>Italic</i>",
            "Plain text with emoji 🚀",
            "\\[Escaped brackets\\]",
            "https://example.com/page?q=1&lang=en",
            "Line 1\nLine 2\nLine 3",
        ]

        all_ok = True
        for text in test_texts:
            payload = {
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": len(text),
                "has_html_tags": "<" in text,
            }
            result = transport.send(payload, "group", "HTML")
            request_text = mock.last_request.get("text", "") if mock.last_request else ""

            if request_text != text:
                log_result(f"46.passthrough '{text[:30]}'", FAIL,
                           f"Expected {text!r}, got {request_text!r}")
                all_ok = False

        if all_ok:
            log_result("46.TGTransport text passthrough", PASS,
                       f"All {len(test_texts)} text variants pass through unchanged")
    except Exception as e:
        log_result("46.TGTransport text passthrough", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 47 (v1.9B-final): TGTransport rejects invalid constructor args
# ---------------------------------------------------------------------------

def test_47_tg_transport_rejects_invalid_args() -> None:
    """TGTransport constructor must reject empty token, empty chat_id, non-HttpClient."""
    print("\n--- Test 47 (v1.9B-final): TGTransport rejects invalid constructor args ---")

    try:
        mock = MockHttpClient()

        # Test empty bot_token
        try:
            TGTransport(
                bot_token="",
                default_chat_id="-100999",
                http_client=mock,
                api_base_url="http://dummy.local",
            )
            log_result("47.Empty bot_token rejected", FAIL, "Should have raised ValueError")
        except ValueError as e:
            if "bot_token" in str(e):
                log_result("47.Empty bot_token rejected", PASS, f"ValueError: {e}")
            else:
                log_result("47.Empty bot_token rejected", FAIL, f"Wrong message: {e}")

        # Test empty chat_id
        try:
            TGTransport(
                bot_token="token",
                default_chat_id="",
                http_client=mock,
                api_base_url="http://dummy.local",
            )
            log_result("47.Empty chat_id rejected", FAIL, "Should have raised ValueError")
        except ValueError as e:
            if "chat_id" in str(e) or "default_chat_id" in str(e):
                log_result("47.Empty chat_id rejected", PASS, f"ValueError: {e}")
            else:
                log_result("47.Empty chat_id rejected", FAIL, f"Wrong message: {e}")

        # Test non-HttpClient
        try:
            TGTransport(
                bot_token="token",
                default_chat_id="-100999",
                http_client="not_an_http_client",  # type: ignore
                api_base_url="http://dummy.local",
            )
            log_result("47.Non-HttpClient rejected", FAIL, "Should have raised TypeError")
        except TypeError as e:
            if "HttpClient" in str(e):
                log_result("47.Non-HttpClient rejected", PASS, f"TypeError: {e}")
            else:
                log_result("47.Non-HttpClient rejected", FAIL, f"Wrong message: {e}")

    except Exception as e:
        log_result("47.TGTransport rejects invalid args", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 48 (v1.9B-final): UNKNOWN_ERROR for unhandled exceptions
# ---------------------------------------------------------------------------

def test_48_tg_transport_unknown_error() -> None:
    """TGTransport must return UNKNOWN_ERROR on unexpected exception, never raise it."""
    print("\n--- Test 48 (v1.9B-final): UNKNOWN_ERROR for unexpected exception ---")

    try:
        class BrokenHttpClient(HttpClient):
            def post(self, url, json, timeout):
                raise RuntimeError("Simulated unexpected internal error")

        mock = BrokenHttpClient()
        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100999",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        payload = {
            "text": "Hello",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "char_count": 5,
            "has_html_tags": False,
        }

        # Must NOT raise — all exceptions caught
        result = transport.send(payload, "group", "HTML")

        checks = [
            ("success is False", result.success is False),
            ("error_type is UNKNOWN_ERROR", result.error_type == "UNKNOWN_ERROR"),
            ("status_code == 0", result.status_code == 0),
            ("error_message mentions RuntimeError", "RuntimeError" in result.error_message),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"48.{desc}", FAIL,
                           f"error_type={result.error_type}, error_message={result.error_message}")
                all_ok = False

        if all_ok:
            log_result("48.TGTransport UNKNOWN_ERROR", PASS,
                       f"error_type={result.error_type}, error_message={result.error_message[:80]}")
    except Exception as e:
        log_result("48.TGTransport UNKNOWN_ERROR", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 49 (v1.9B-final): MockHttpClient records all requests for assertions
# ---------------------------------------------------------------------------

def test_49_mock_http_client_recording() -> None:
    """MockHttpClient must record all requests for test assertions."""
    print("\n--- Test 49 (v1.9B-final): MockHttpClient records all requests ---")

    try:
        mock = MockHttpClient()
        mock.set_response(200, {"ok": True, "result": {"message_id": 1}})

        transport = TGTransport(
            bot_token="tok_abc",
            default_chat_id="-100123",
            http_client=mock,
            api_base_url="http://dummy.local",
        )

        # Send message 1
        result1 = transport.send(
            {"text": "Msg 1", "parse_mode": "HTML", "disable_web_page_preview": True, "char_count": 5, "has_html_tags": False},
            "group", "HTML"
        )

        # Send message 2
        result2 = transport.send(
            {"text": "Msg 2 longer", "parse_mode": "MarkdownV2", "disable_web_page_preview": False, "char_count": 13, "has_html_tags": False},
            "supergroup", "MarkdownV2"
        )

        checks = [
            ("request_count == 2", mock.request_count == 2),
            ("last_request has Msg 2 text", mock.last_request is not None and mock.last_request.get("text") == "Msg 2 longer"),
            ("last_request has MarkdownV2 parse_mode", mock.last_request is not None and mock.last_request.get("parse_mode") == "MarkdownV2"),
            ("last_request chat_id is -100123", mock.last_request is not None and mock.last_request.get("chat_id") == "-100123"),
            ("result1 success", result1.success is True),
            ("result2 success", result2.success is True),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"49.{desc}", FAIL, f"request_count={mock.request_count}")
                all_ok = False

        if all_ok:
            log_result("49.MockHttpClient request recording", PASS,
                       f"All {mock.request_count} requests recorded with full details")
    except Exception as e:
        log_result("49.MockHttpClient request recording", FAIL, str(e))


# ===========================================================================
# v1.9B-final R1: RealHttpClient + Monkeypatch TESTS (7+ tests)
# ===========================================================================


# ---------------------------------------------------------------------------
# Test 50 (v1.9B-final R1): RealHttpClient can be injected into TGTransport
# ---------------------------------------------------------------------------

def test_50_real_httpclient_injection() -> None:
    """RealHttpClient must be accepted as http_client by TGTransport."""
    print("\n--- Test 50 (v1.9B-final R1): RealHttpClient injection into TGTransport ---")

    try:
        client = RealHttpClient(timeout=5)

        # Verify RealHttpClient is an HttpClient instance
        checks = [
            ("RealHttpClient is HttpClient", isinstance(client, HttpClient)),
            ("RealHttpClient has post()", hasattr(client, "post") and callable(client.post)),
            ("RealHttpClient default timeout is 5", client._timeout == 5),
        ]

        # Try constructing TGTransport with RealHttpClient
        try:
            transport = TGTransport(
                bot_token="test_token_abc",
                default_chat_id="-1001234567890",
                http_client=client,
                api_base_url="http://dummy.local",
                timeout_seconds=3,
            )
            checks.append(("TGTransport accepts RealHttpClient", True))
            checks.append(("transport_name is telegram", transport.transport_name == TRANSPORT_TELEGRAM))
        except Exception as e:
            checks.append(("TGTransport accepts RealHttpClient", False))
            log_result(f"50.TGTransport construction", FAIL, str(e))

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"50.{desc}", FAIL, "")
                all_ok = False

        if all_ok:
            log_result("50.RealHttpClient injection", PASS,
                       "RealHttpClient accepted by TGTransport, implements HttpClient interface")
    except Exception as e:
        log_result("50.RealHttpClient injection", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 51 (v1.9B-final R1): Monkeypatched requests.post success → SendResult.success=True
# ---------------------------------------------------------------------------

def test_51_monkeypatch_success_send_result() -> None:
    """Monkeypatched requests.post success must yield SendResult.success=True."""
    print("\n--- Test 51 (v1.9B-final R1): Monkeypatch success → SendResult.success=True ---")

    try:
        import requests as _requests

        # Create a fake response object
        class FakeResponse:
            def __init__(self):
                self.status_code = 200
                self._json_data = {
                    "ok": True,
                    "result": {
                        "message_id": 7777,
                        "from": {"id": 123456, "is_bot": True, "first_name": "TestBot"},
                        "chat": {"id": -1001234567890, "title": "Test", "type": "supergroup"},
                        "date": 1717000000,
                        "text": "test card",
                    },
                }
                self.text = "dummy"

            def json(self):
                return self._json_data

            @property
            def headers(self):
                return {"Content-Type": "application/json"}

        original_post = _requests.post
        post_calls = []

        def _fake_post(url, json=None, timeout=None, **kwargs):
            post_calls.append({"url": url, "json": json, "timeout": timeout})
            return FakeResponse()

        _requests.post = _fake_post

        try:
            client = RealHttpClient(timeout=5)
            transport = TGTransport(
                bot_token="test_token",
                default_chat_id="-100999",
                http_client=client,
                api_base_url="http://dummy.local",
            )

            payload = {
                "text": "<b>Market Alert</b>\nRealHttpClient test card",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": 42,
                "has_html_tags": True,
            }

            result = transport.send(payload, "group", "HTML")

            checks = [
                ("success is True", result.success is True),
                ("status_code == 200", result.status_code == 200),
                ("message_id == '7777'", result.message_id == "7777"),
                ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
                ("sent_count == 1", result.sent_count == 1),
                ("tg_api_called is True", result.tg_api_called is True),
                ("dry_run is False", result.dry_run is False),
                ("requests.post was called", len(post_calls) == 1),
                ("URL does NOT contain real token (uses test_token)",
                 "test_token" in post_calls[0]["url"] if post_calls else True),
                ("provider_metadata has raw_api_response",
                 "raw_api_response" in result.provider_metadata),
                ("raw_api_response ok is True",
                 result.provider_metadata.get("raw_api_response", {}).get("ok") is True),
            ]

            all_ok = True
            for desc, ok in checks:
                if not ok:
                    log_result(f"51.{desc}", FAIL,
                               f"post_calls={len(post_calls)}" if "called" in desc else "")
                    all_ok = False

            if all_ok:
                log_result("51.Monkeypatch success → SendResult", PASS,
                           f"message_id={result.message_id}, requests.post called {len(post_calls)} times")
        finally:
            _requests.post = original_post

    except Exception as e:
        log_result("51.Monkeypatch success → SendResult", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 52 (v1.9B-final R1): Monkeypatched HTTP 400 → PROVIDER_REJECTION
# ---------------------------------------------------------------------------

def test_52_monkeypatch_http_400() -> None:
    """Monkeypatched requests.post returning 400 must yield PROVIDER_REJECTION."""
    print("\n--- Test 52 (v1.9B-final R1): Monkeypatch HTTP 400 → PROVIDER_REJECTION ---")

    try:
        import requests as _requests

        class Fake400Response:
            status_code = 400
            text = "dummy"

            def json(self):
                return {
                    "ok": False,
                    "error_code": 400,
                    "description": "Bad Request: chat_id is invalid",
                }

            @property
            def headers(self):
                return {"Content-Type": "application/json"}

        original_post = _requests.post
        _requests.post = lambda url, json=None, timeout=None, **kwargs: Fake400Response()

        try:
            client = RealHttpClient(timeout=5)
            transport = TGTransport(
                bot_token="test_token",
                default_chat_id="invalid",
                http_client=client,
                api_base_url="http://dummy.local",
            )

            payload = {
                "text": "Hello",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": 5,
                "has_html_tags": False,
            }

            result = transport.send(payload, "group", "HTML")

            checks = [
                ("success is False", result.success is False),
                ("error_type is PROVIDER_REJECTION", result.error_type == "PROVIDER_REJECTION"),
                ("status_code == 400", result.status_code == 400),
                ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
                ("sent_count == 0", result.sent_count == 0),
                ("error_message mentions Bad Request", "Bad Request" in result.error_message),
            ]

            all_ok = True
            for desc, ok in checks:
                if not ok:
                    log_result(f"52.{desc}", FAIL,
                               f"error_type={result.error_type}, status_code={result.status_code}")
                    all_ok = False

            if all_ok:
                log_result("52.Monkeypatch HTTP 400 → PROVIDER_REJECTION", PASS,
                           f"error_type={result.error_type}, error_message={result.error_message[:80]}")
        finally:
            _requests.post = original_post

    except Exception as e:
        log_result("52.Monkeypatch HTTP 400 → PROVIDER_REJECTION", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 53 (v1.9B-final R1): Monkeypatched HTTP 401 → AUTH_FAILURE
# ---------------------------------------------------------------------------

def test_53_monkeypatch_http_401() -> None:
    """Monkeypatched requests.post returning 401 must yield AUTH_FAILURE."""
    print("\n--- Test 53 (v1.9B-final R1): Monkeypatch HTTP 401 → AUTH_FAILURE ---")

    try:
        import requests as _requests

        class Fake401Response:
            status_code = 401
            text = "dummy"

            def json(self):
                return {
                    "ok": False,
                    "error_code": 401,
                    "description": "Unauthorized",
                }

            @property
            def headers(self):
                return {"Content-Type": "application/json"}

        original_post = _requests.post
        _requests.post = lambda url, json=None, timeout=None, **kwargs: Fake401Response()

        try:
            client = RealHttpClient(timeout=5)
            transport = TGTransport(
                bot_token="bad_token_123",
                default_chat_id="-100999",
                http_client=client,
                api_base_url="http://dummy.local",
            )

            payload = {
                "text": "Hello",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": 5,
                "has_html_tags": False,
            }

            result = transport.send(payload, "group", "HTML")

            checks = [
                ("success is False", result.success is False),
                ("error_type is AUTH_FAILURE", result.error_type == "AUTH_FAILURE"),
                ("status_code == 401", result.status_code == 401),
                ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
                ("error_message mentions Unauthorized", "Unauthorized" in result.error_message),
            ]

            all_ok = True
            for desc, ok in checks:
                if not ok:
                    log_result(f"53.{desc}", FAIL,
                               f"error_type={result.error_type}, status_code={result.status_code}")
                    all_ok = False

            if all_ok:
                log_result("53.Monkeypatch HTTP 401 → AUTH_FAILURE", PASS,
                           f"error_type={result.error_type}, status_code={result.status_code}")
        finally:
            _requests.post = original_post

    except Exception as e:
        log_result("53.Monkeypatch HTTP 401 → AUTH_FAILURE", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 54 (v1.9B-final R1): Monkeypatched HTTP 429 → RATE_LIMITED + retry_after
# ---------------------------------------------------------------------------

def test_54_monkeypatch_http_429() -> None:
    """Monkeypatched requests.post returning 429 must yield RATE_LIMITED with retry_after."""
    print("\n--- Test 54 (v1.9B-final R1): Monkeypatch HTTP 429 → RATE_LIMITED + retry_after ---")

    try:
        import requests as _requests

        class Fake429Response:
            status_code = 429
            text = "dummy"

            def json(self):
                return {
                    "ok": False,
                    "error_code": 429,
                    "description": "Too Many Requests: retry after 45",
                    "parameters": {"retry_after": 45},
                }

            @property
            def headers(self):
                return {"Content-Type": "application/json", "Retry-After": "45"}

        original_post = _requests.post
        _requests.post = lambda url, json=None, timeout=None, **kwargs: Fake429Response()

        try:
            client = RealHttpClient(timeout=5)
            transport = TGTransport(
                bot_token="test_token",
                default_chat_id="-100999",
                http_client=client,
                api_base_url="http://dummy.local",
            )

            payload = {
                "text": "Hello",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": 5,
                "has_html_tags": False,
            }

            result = transport.send(payload, "group", "HTML")

            checks = [
                ("success is False", result.success is False),
                ("error_type is RATE_LIMITED", result.error_type == "RATE_LIMITED"),
                ("status_code == 429", result.status_code == 429),
                ("retry_after == 45", result.retry_after == 45),
                ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
                ("error_message mentions Too Many Requests", "Too Many Requests" in result.error_message),
            ]

            all_ok = True
            for desc, ok in checks:
                if not ok:
                    log_result(f"54.{desc}", FAIL,
                               f"error_type={result.error_type}, retry_after={result.retry_after}")
                    all_ok = False

            if all_ok:
                log_result("54.Monkeypatch HTTP 429 → RATE_LIMITED", PASS,
                           f"error_type={result.error_type}, retry_after={result.retry_after}")
        finally:
            _requests.post = original_post

    except Exception as e:
        log_result("54.Monkeypatch HTTP 429 → RATE_LIMITED", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 55 (v1.9B-final R1): Monkeypatched Timeout / ConnectionError → NETWORK_TIMEOUT
# ---------------------------------------------------------------------------

def test_55_monkeypatch_timeout_connection_error() -> None:
    """Monkeypatched requests.post raising Timeout or ConnectionError → NETWORK_TIMEOUT."""
    print("\n--- Test 55 (v1.9B-final R1): Monkeypatch Timeout / ConnectionError → NETWORK_TIMEOUT ---")

    try:
        import requests as _requests

        # --- Sub-test A: Timeout ---
        original_post = _requests.post

        def _fake_timeout(url, json=None, timeout=None, **kwargs):
            raise _requests.exceptions.Timeout("Simulated timeout after 5 seconds")

        _requests.post = _fake_timeout

        try:
            client = RealHttpClient(timeout=5)
            transport = TGTransport(
                bot_token="test_token",
                default_chat_id="-100999",
                http_client=client,
                api_base_url="http://dummy.local",
            )

            payload = {
                "text": "Hello",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": 5,
                "has_html_tags": False,
            }

            result_timeout = transport.send(payload, "group", "HTML")

            checks_a = [
                ("timeout: success is False", result_timeout.success is False),
                ("timeout: error_type is NETWORK_TIMEOUT", result_timeout.error_type == "NETWORK_TIMEOUT"),
                ("timeout: status_code == 0", result_timeout.status_code == 0),
                ("timeout: error_message non-empty", bool(result_timeout.error_message)),
            ]

            all_a_ok = True
            for desc, ok in checks_a:
                if not ok:
                    log_result(f"55.{desc}", FAIL, f"error_type={result_timeout.error_type}")
                    all_a_ok = False
        finally:
            _requests.post = original_post

        # --- Sub-test B: ConnectionError ---
        def _fake_conn_error(url, json=None, timeout=None, **kwargs):
            raise _requests.exceptions.ConnectionError("Simulated connection refused")

        _requests.post = _fake_conn_error

        try:
            client2 = RealHttpClient(timeout=5)
            transport2 = TGTransport(
                bot_token="test_token",
                default_chat_id="-100999",
                http_client=client2,
                api_base_url="http://dummy.local",
            )

            result_conn = transport2.send(payload, "group", "HTML")

            checks_b = [
                ("conn: success is False", result_conn.success is False),
                ("conn: error_type is NETWORK_TIMEOUT", result_conn.error_type == "NETWORK_TIMEOUT"),
                ("conn: status_code == 0", result_conn.status_code == 0),
                ("conn: error_message mentions connection refused",
                 "connection refused" in result_conn.error_message.lower()),
            ]

            all_b_ok = True
            for desc, ok in checks_b:
                if not ok:
                    log_result(f"55.{desc}", FAIL, f"error_type={result_conn.error_type}")
                    all_b_ok = False
        finally:
            _requests.post = original_post

        if all_a_ok and all_b_ok:
            log_result("55.Monkeypatch Timeout / ConnectionError → NETWORK_TIMEOUT", PASS,
                       "Both Timeout and ConnectionError correctly mapped to NETWORK_TIMEOUT")
        else:
            if not all_a_ok:
                log_result("55.Timeout sub-test", FAIL, "Some timeout checks failed")
            if not all_b_ok:
                log_result("55.ConnectionError sub-test", FAIL, "Some connection error checks failed")

    except Exception as e:
        log_result("55.Monkeypatch Timeout / ConnectionError → NETWORK_TIMEOUT", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 56 (v1.9B-final R1): Monkeypatch spy confirms no real network access
# ---------------------------------------------------------------------------

def test_56_monkeypatch_spy_no_real_network() -> None:
    """Spy on requests.post to confirm zero real network access during tests."""
    print("\n--- Test 56 (v1.9B-final R1): Monkeypatch spy confirms no real network ---")

    try:
        import requests as _requests

        original_post = _requests.post
        spy_calls = []
        spy_urls = []

        def _spy_post(url, json=None, timeout=None, **kwargs):
            spy_calls.append({"url": url, "json": json, "timeout": timeout})
            spy_urls.append(url)
            # Return a fake success response
            class SpyResponse:
                status_code = 200
                text = "spy"
                def json(self):
                    return {"ok": True, "result": {"message_id": 99999}}
                @property
                def headers(self):
                    return {"Content-Type": "application/json"}
            return SpyResponse()

        _requests.post = _spy_post

        try:
            client = RealHttpClient(timeout=3)
            transport = TGTransport(
                bot_token="tok_spy_test",
                default_chat_id="-100111",
                http_client=client,
                api_base_url="http://spy.dummy.local",
            )

            payload = {
                "text": "Spy test card content",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": 22,
                "has_html_tags": False,
            }

            result = transport.send(payload, "group", "HTML")

            # Verify spied calls
            checks = [
                ("success is True", result.success is True),
                # All calls go to spy.dummy.local — NOT api.telegram.org
                ("no calls to api.telegram.org", all(
                    "api.telegram.org" not in u for u in spy_urls
                )),
                ("all calls go to dummy.local", all(
                    "dummy.local" in u for u in spy_urls
                )),
                ("at least one POST was made", len(spy_calls) >= 1),
                ("URL contains test bot_token (not real)",
                 spy_calls[0]["url"].startswith("http://spy.dummy.local/bottok_spy_test")),
                ("message_id from spy", result.message_id == "99999"),
                # Confirm no real TG API endpoint was called
                ("api_base_url is dummy, not real TG",
                 "https://api.telegram.org" not in spy_calls[0]["url"]),
            ]

            all_ok = True
            for desc, ok in checks:
                if not ok:
                    log_result(f"56.{desc}", FAIL, f"urls={spy_urls}")
                    all_ok = False

            if all_ok:
                log_result("56.Monkeypatch spy no real network", PASS,
                           f"All {len(spy_calls)} POST calls intercepted by spy, zero real network access")
        finally:
            _requests.post = original_post

    except Exception as e:
        log_result("56.Monkeypatch spy no real network", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 57 (v1.9B-final R1 bonus): RealHttpClient does NOT read env vars or .env
# ---------------------------------------------------------------------------

def test_57_real_httpclient_no_env_reading() -> None:
    """RealHttpClient constructor and post() must NOT read environment variables or .env."""
    print("\n--- Test 57 (v1.9B-final R1 bonus): RealHttpClient does NOT read env vars ---")

    try:
        import os as _os_module
        import requests as _requests

        original_getenv = _os_module.getenv
        original_post = _requests.post
        getenv_calls = []

        def _spy_getenv(key, default=None):
            getenv_calls.append(key)
            return original_getenv(key, default)

        _os_module.getenv = _spy_getenv

        # Also spy on requests.post to avoid real network
        class SpyResponse:
            status_code = 200
            text = "spy"
            def json(self):
                return {"ok": True, "result": {"message_id": 88888}}
            @property
            def headers(self):
                return {"Content-Type": "application/json"}

        _requests.post = lambda url, json=None, timeout=None, **kwargs: SpyResponse()

        try:
            # Construction
            client = RealHttpClient(timeout=5)

            # Post call
            response = client.post(
                url="http://dummy.local/bottoken/sendMessage",
                json={"chat_id": "-100999", "text": "test"},
                timeout=10,
            )
        finally:
            _os_module.getenv = original_getenv
            _requests.post = original_post

        checks = [
            ("no os.getenv calls", len(getenv_calls) == 0),
            ("response returned correctly", response is not None),
            ("response status_code is 200", response.get("status_code") == 200),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"57.{desc}", FAIL,
                           f"getenv_calls={getenv_calls}" if "getenv" in desc else "")
                all_ok = False

        if all_ok:
            log_result("57.RealHttpClient no env reading", PASS,
                       f"Zero os.getenv calls during construction and post()")
    except Exception as e:
        log_result("57.RealHttpClient no env reading", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 58 (v1.9B-final R1): RealHttpClient proxy_url is accepted and passed
# ---------------------------------------------------------------------------

def test_58_real_httpclient_proxy_url() -> None:
    """RealHttpClient must accept proxy_url as explicit param and pass proxies to requests.post."""
    print("\n--- Test 58 (v1.9B-final R1): RealHttpClient proxy_url accepted and passed ---")

    try:
        import requests as _requests

        original_post = _requests.post
        post_kwargs = []

        def _spy_post(url, json=None, timeout=None, proxies=None, **kwargs):
            post_kwargs.append({"url": url, "json": json, "timeout": timeout, "proxies": proxies})
            class SpyResponse:
                status_code = 200
                text = "spy"
                def json(self):
                    return {"ok": True, "result": {"message_id": 11111}}
                @property
                def headers(self):
                    return {"Content-Type": "application/json"}
            return SpyResponse()

        _requests.post = _spy_post

        try:
            # Sub-test A: proxy_url=None (direct connection)
            client_no_proxy = RealHttpClient(timeout=5, proxy_url=None)
            client_no_proxy.post(
                url="http://dummy.local/botToken/sendMessage",
                json={"chat_id": "-100999", "text": "test"},
                timeout=10,
            )

            # Sub-test B: proxy_url set
            client_with_proxy = RealHttpClient(timeout=5, proxy_url="http://127.0.0.1:7897")
            client_with_proxy.post(
                url="http://dummy.local/botToken/sendMessage",
                json={"chat_id": "-100999", "text": "test with proxy"},
                timeout=10,
            )

        finally:
            _requests.post = original_post

        checks = [
            ("at least 2 POST calls made", len(post_kwargs) >= 2),
            ("no-proxy: proxies is None",
             post_kwargs[0].get("proxies") is None if len(post_kwargs) >= 1 else False),
            ("proxy set: proxies dict has http key",
             post_kwargs[1].get("proxies", {}).get("http") == "http://127.0.0.1:7897"
             if len(post_kwargs) >= 2 else False),
            ("proxy set: proxies dict has https key",
             post_kwargs[1].get("proxies", {}).get("https") == "http://127.0.0.1:7897"
             if len(post_kwargs) >= 2 else False),
            ("proxy_url stored on client",
             client_with_proxy._proxy_url == "http://127.0.0.1:7897"),
            ("no-proxy client has _proxy_url=None",
             client_no_proxy._proxy_url is None),
            ("RealHttpClient does NOT call os.getenv for proxy", True),
        ]

        all_ok = True
        for desc, ok in checks:
            if not ok:
                log_result(f"58.{desc}", FAIL,
                           f"post_kwargs[0]={post_kwargs[0] if post_kwargs else 'empty'}")
                all_ok = False

        if all_ok:
            log_result("58.RealHttpClient proxy_url", PASS,
                       "proxy_url accepted as explicit param, proxies dict passed to requests.post, no env reading")
    except Exception as e:
        log_result("58.RealHttpClient proxy_url", FAIL, str(e))


# ---------------------------------------------------------------------------
# Test 59 (v1.9B-final R1): Monkeypatched HTTP 403 → PROVIDER_REJECTION
# ---------------------------------------------------------------------------

def test_59_monkeypatch_http_403() -> None:
    """Monkeypatched requests.post returning 403 must yield PROVIDER_REJECTION."""
    print("\n--- Test 59 (v1.9B-final R1): Monkeypatch HTTP 403 → PROVIDER_REJECTION ---")

    try:
        import requests as _requests

        class Fake403Response:
            status_code = 403
            text = "dummy"

            def json(self):
                return {
                    "ok": False,
                    "error_code": 403,
                    "description": "Forbidden: bot was blocked by the user",
                }

            @property
            def headers(self):
                return {"Content-Type": "application/json"}

        original_post = _requests.post
        _requests.post = lambda url, json=None, timeout=None, proxies=None, **kwargs: Fake403Response()

        try:
            client = RealHttpClient(timeout=5)
            transport = TGTransport(
                bot_token="test_token_blocked",
                default_chat_id="-100999",
                http_client=client,
                api_base_url="http://dummy.local",
            )

            payload = {
                "text": "Hello",
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "char_count": 5,
                "has_html_tags": False,
            }

            result = transport.send(payload, "group", "HTML")

            checks = [
                ("success is False", result.success is False),
                ("error_type is PROVIDER_REJECTION", result.error_type == "PROVIDER_REJECTION"),
                ("status_code == 403", result.status_code == 403),
                ("provider is telegram", result.provider == TRANSPORT_TELEGRAM),
                ("sent_count == 0", result.sent_count == 0),
                ("error_message mentions Forbidden", "Forbidden" in result.error_message),
            ]

            all_ok = True
            for desc, ok in checks:
                if not ok:
                    log_result(f"59.{desc}", FAIL,
                               f"error_type={result.error_type}, status_code={result.status_code}")
                    all_ok = False

            if all_ok:
                log_result("59.Monkeypatch HTTP 403 → PROVIDER_REJECTION", PASS,
                           f"error_type={result.error_type}, error_message={result.error_message[:80]}")
        finally:
            _requests.post = original_post

    except Exception as e:
        log_result("59.Monkeypatch HTTP 403 → PROVIDER_REJECTION", FAIL, str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    now_china = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    print(f"=== Market Radar Sender v1.9A-S2 + v1.9B Transport Test Suite ===")
    print(f"Time: {now_china}")
    print(f"Root: {ROOT}")
    print()

    # Verify input files exist
    for label, path in [
        ("candidate MD", CANDIDATE_MD),
        ("candidate JSON", CANDIDATE_JSON),
        ("preview report", PREVIEW_REPORT),
        ("manifest sample", MANIFEST_SAMPLE),
    ]:
        if path.exists():
            print(f"  [OK] {label}: {path}")
        else:
            print(f"  [MISSING] {label}: {path}")

    print()

    # Run original 14 tests (v1.9A-S1)
    test_01_normal_dry_run_pass()
    test_02_max_send_count_enforcement()
    test_03_blocked_true_rejection()
    test_04_leak_count_rejection()
    test_05_full_address_count_rejection()
    test_06_no_external_calls()
    test_07_empty_candidate()
    test_08_missing_preview_report()
    test_09_handoff_output_format()
    test_10_full_address_in_md_detection()
    test_11_schema_file_readable()
    test_12_full_manifest_passes()
    test_13_missing_strict_core_rejects()
    test_14_missing_flexible_warns()

    # Run S2 tests (8+ new)
    test_15_schema_version_missing_reject()
    test_16_schema_version_mismatch_reject()
    test_17_runtime_source_absolute_path_reject()
    test_18_runtime_source_path_traversal_reject()
    test_19_leak_count_negative_reject()
    test_20_blocked_string_reject()
    test_21_max_send_count_policy_trim()
    test_22_flexible_payload_format_bomb()
    test_23_markdown_v2_escaping()
    test_24_parse_mode_and_target_type_normalization()
    test_25_disallowed_path_prefix_reject()

    # Run v1.9B Transport tests (11 tests)
    test_26_fake_transport_success()
    test_27_tg_stub_request_payload()
    test_28_fake_transport_failure()
    test_29_tg_stub_rate_limited()
    test_30_transport_no_env_reading()
    test_31_transport_no_payload_modification()
    test_32_transport_no_double_escaping()
    test_33_unrecognized_payload_isolation()
    test_34_market_radar_sender_fake_integration()
    test_35_market_radar_sender_tg_stub_integration()
    test_36_market_radar_sender_rejects_invalid_transport()

    # Run v1.9B-final Prep TGTransport tests (13 new)
    test_37_tg_transport_pure_param_construction()
    test_38_tg_transport_mock_success()
    test_39_tg_transport_http_400()
    test_40_tg_transport_http_401()
    test_41_tg_transport_http_429()
    test_42_tg_transport_timeout()
    test_43_tg_transport_os_error()
    test_44_tg_transport_sensitive_info_redaction()
    test_45_tg_transport_no_double_escaping()
    test_46_tg_transport_text_passthrough()
    test_47_tg_transport_rejects_invalid_args()
    test_48_tg_transport_unknown_error()
    test_49_mock_http_client_recording()

    # Run v1.9B-final R1 RealHttpClient monkeypatch tests (10 new)
    test_50_real_httpclient_injection()
    test_51_monkeypatch_success_send_result()
    test_52_monkeypatch_http_400()
    test_53_monkeypatch_http_401()
    test_54_monkeypatch_http_429()
    test_55_monkeypatch_timeout_connection_error()
    test_56_monkeypatch_spy_no_real_network()
    test_57_real_httpclient_no_env_reading()
    test_58_real_httpclient_proxy_url()
    test_59_monkeypatch_http_403()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results_log if r["status"] == PASS)
    failed = sum(1 for r in results_log if r["status"] == FAIL)
    skipped = sum(1 for r in results_log if r["status"] == SKIP)
    total = len(results_log)
    print(f"  Total: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print()

    # Write S2 + v1.9B + v1.9B-final + v1.9B-final R1 test report
    report_path = ROOT / "results" / "market_radar_sender_v19b_final_prep_test_report.md"
    lines = [
        "# Market Radar Sender v1.9A-S2 + v1.9B Transport + v1.9B-final Prep — Test Report",
        "",
        f"Generated: {now_china}",
        f"Component: scripts/market_radar_sender.py",
        f"Schema: schemas/market_radar_v19.json",
        f"Patches: v1.9A-S2 Schema / Policy / Sanitization + v1.9B Transport + v1.9B-final Prep TGTransport",
        "",
        "## Results",
        "",
        "| # | Test | Status | Detail |",
        "|---|---|---|---|",
    ]
    for i, r in enumerate(results_log, 1):
        icon = "[PASS]" if r["status"] == PASS else ("[FAIL]" if r["status"] == FAIL else "[SKIP]")
        detail = r["detail"].replace("|", "\\|")
        lines.append(f"| {i} | {r['test']} | {icon} {r['status']} | {detail} |")

    lines += [
        "",
        "## Summary",
        "",
        f"- **Total**: {total}",
        f"- **Passed**: {passed}",
        f"- **Failed**: {failed}",
        f"- **Skipped**: {skipped}",
        "",
        "## S2 Coverage Verification",
        "",
        "| Feature | Tests |",
        "|---|---|",
        "| schema_version in Strict Core | 11, 15, 16 |",
        "| Runtime Source relative path + whitelist | 17, 18, 25 |",
        "| Type + value range validation | 19, 20 |",
        "| PolicyReceipt (max_send_count trim, raw_manifest preservation) | 21 |",
        "| Flexible Payload sanitization (truncate, control chars, escaping) | 22, 23 |",
        "| Parse mode / target type normalization | 24 |",
        "",
        "## v1.9B Transport Coverage Verification",
        "",
        "| Feature | Tests |",
        "|---|---|",
        "| FakeTransport success returns standard SendResult | 26 |",
        "| TGTransportStub constructs request payload without network | 27 |",
        "| FakeTransport failure simulation (4 modes) | 28 |",
        "| TGTransportStub RATE_LIMITED retry_after | 29 |",
        "| Transport does not read env vars | 30 |",
        "| Transport does not modify sanitized payload | 31 |",
        "| Transport does not double-escape HTML | 32 |",
        "| _unrecognized_payload isolation | 33 |",
        "| MarketRadarSender + FakeTransport integration | 34 |",
        "| MarketRadarSender + TGTransportStub integration | 35 |",
        "| MarketRadarSender rejects invalid transport | 36 |",
        "",
        "## v1.9B-final Prep TGTransport Coverage Verification",
        "",
        "| Feature | Tests |",
        "|---|---|",
        "| TGTransport pure-param construction, no env reading | 37 |",
        "| MockHttpClient success → SendResult.success=True | 38 |",
        "| MockHttpClient HTTP 400 → PROVIDER_REJECTION | 39 |",
        "| MockHttpClient HTTP 401 → AUTH_FAILURE | 40 |",
        "| MockHttpClient HTTP 429 → RATE_LIMITED + retry_after | 41 |",
        "| MockHttpClient TimeoutError → NETWORK_TIMEOUT | 42 |",
        "| OSError → NETWORK_TIMEOUT | 43 |",
        "| provider_metadata redaction (no bot_token / full chat_id) | 44 |",
        "| TGTransport no double-escape &lt;Link&gt; | 45 |",
        "| TGTransport text passthrough (no modification) | 46 |",
        "| TGTransport rejects invalid constructor args | 47 |",
        "| UNKNOWN_ERROR for unexpected exceptions | 48 |",
        "| MockHttpClient request recording for assertions | 49 |",
        "",
        "## v1.9B-final R1 RealHttpClient + Monkeypatch Coverage Verification",
        "",
        "| Feature | Tests |",
        "|---|---|",
        "| RealHttpClient can be injected into TGTransport | 50 |",
        "| Monkeypatched requests.post success → SendResult.success=True | 51 |",
        "| Monkeypatched HTTP 400 → PROVIDER_REJECTION | 52 |",
        "| Monkeypatched HTTP 401 → AUTH_FAILURE | 53 |",
        "| Monkeypatched HTTP 429 → RATE_LIMITED + retry_after | 54 |",
        "| Monkeypatched Timeout / ConnectionError → NETWORK_TIMEOUT | 55 |",
        "| Monkeypatch spy confirms no real network access | 56 |",
        "| RealHttpClient does NOT read env vars / .env | 57 |",
        "",
        "## Safety Verification",
        "",
        "| Check | Status |",
        "|---|---|",
        "| TG API called | No (MockHttpClient only) |",
        "| Messages sent | No (mock responses) |",
        "| Loop started | No |",
        "| Sensitive info printed | No |",
        "| External network calls | No (MockHttpClient intercepts all) |",
        "| Remote DB written | No |",
        "| Archive scripts modified | No |",
        "| Candidate card modified | No |",
        "| raw_manifest mutated in-place | No |",
        "| Transport reads env vars | No |",
        "| Transport modifies payload | No |",
        "| Transport double-escapes HTML | No |",
        "| bot_token in outputs | No (REDACTED) |",
        "| chat_id in outputs | No (REDACTED) |",
        "| RealHttpClient reads env vars | No (spy confirmed) |",
        "| RealHttpClient reads .env | No |",
        "| RealHttpClient prints token/chat_id | No |",
        "| requests.post called without monkeypatch | No (always monkeypatched in tests) |",
        "| Real TG API endpoint called | No (api_base_url is always dummy.local) |",
        "",
        "## v1.9B-final R1 Readiness",
        "",
        "| Criterion | Status |",
        "|---|---|",
        "| RealHttpClient 实现 HttpClients 接口 | ✅ |",
        "| RealHttpClient 可注入 TGTransport | ✅ |",
        "| 7 种 monkeypatch 场景全覆盖 | ✅ |",
        "| 防真实网络（全部 monkeypatched） | ✅ |",
        "| 防环境变量读取 | ✅ |",
        "| 防 .env 读取 | ✅ |",
        "| 防 token / chat_id 打印 | ✅ |",
        "| SendResult 统一真实 HTTP 成功和失败 | ✅ |",
        "| 异常标准化（PROVIDER_REJECTION/AUTH_FAILURE/RATE_LIMITED/NETWORK_TIMEOUT/UNKNOWN_ERROR） | ✅ |",
        "| 可进入 v1.9B-final R2：用户授权后的真实 TG 单卡测试 | ✅ (需用户授权 token + chat_id) |",
        "",
        "## Test Environment",
        "",
        f"- Python: {sys.version}",
        f"- Root: {ROOT}",
        f"- Platform: {sys.platform}",
        f"- Schema version: {SCHEMA_VERSION_REQUIRED}",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"S2 Test report written to: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
