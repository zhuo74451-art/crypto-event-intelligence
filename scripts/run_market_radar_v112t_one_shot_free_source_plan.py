#!/usr/bin/env python3
"""
run_market_radar_v112t_one_shot_free_source_plan.py
====================================================
v112T one-shot free source plan with stop conditions.

Plan-only runner. Defines free source candidates, field mapping,
three-state stop conditions (CONTINUE/ABORT/DEGRADE_TO_MOCK),
LiveSourceResponse schema, and LiveToMockAdapter spec.

NO live HTTP requests. NO API keys. NO TG send. NO daemon.
NO production state writes.

Generates:
  results/market_radar_v112t_one_shot_free_source_plan_result.json
  runs/market_radar/v112t_one_shot_free_source_plan.md
  runs/market_radar/v112t_one_shot_free_source_plan_handoff.md
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone, timedelta

# ASCII-safe markers for Windows GBK console
OK_MARK = "[OK]"
FAIL_MARK = "[FAIL]"
WARN_MARK = "[WARN]"

# ── Project root ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

# ── Paths ─────────────────────────────────────────────────────────────────
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
SCHEMAS_DIR = os.path.join(PROJECT_DIR, "schemas")
DOCS_DIR = os.path.join(PROJECT_DIR, "docs")
RUNS_DIR = os.path.join(PROJECT_DIR, "runs", "market_radar")

# Input files
V112S_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112s_mock_gate_preview_integration_result.json")
V112S_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v112s_mock_gate_decisions.jsonl")
V112S_PREVIEW_CARDS = os.path.join(RESULTS_DIR, "market_radar_v112s_mock_preview_cards.jsonl")
V112Q_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112q_multi_asset_noise_aware_plan_result.json")
V112P_MATRIX = os.path.join(RESULTS_DIR, "market_radar_v112p_live_source_matrix.json")
V112Q_THRESHOLDS = os.path.join(CONFIG_DIR, "market_radar_v112q_multi_asset_thresholds.json")

# Output files
V112T_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112t_one_shot_free_source_plan_result.json")
V112T_RUN_REPORT = os.path.join(RUNS_DIR, "v112t_one_shot_free_source_plan.md")
V112T_HANDOFF = os.path.join(RUNS_DIR, "v112t_one_shot_free_source_plan_handoff.md")

# Config/schema/doc files that must exist
REQUIRED_ARTIFACTS = {
    "free_source_mapping": os.path.join(CONFIG_DIR, "market_radar_v112t_free_source_mapping.json"),
    "stop_conditions": os.path.join(CONFIG_DIR, "market_radar_v112t_stop_conditions.json"),
    "live_source_response_schema": os.path.join(SCHEMAS_DIR, "market_radar_v112t_live_source_response_schema.json"),
    "live_to_mock_adapter_spec": os.path.join(SCHEMAS_DIR, "market_radar_v112t_live_to_mock_adapter_spec.md"),
    "free_source_plan_doc": os.path.join(DOCS_DIR, "market_radar_v112t_free_source_plan.md"),
}

TZ = timezone(timedelta(hours=8))  # UTC+8


# ── Helpers ───────────────────────────────────────────────────────────────

def load_json(path, label="file"):
    """Load a JSON file, returning (data, error)."""
    if not os.path.exists(path):
        return None, f"{label} not found at {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"{label} JSON parse error: {e}"
    except Exception as e:
        return None, f"{label} read error: {e}"


def file_exists(path, label="file"):
    """Check file existence."""
    exists = os.path.exists(path)
    if not exists:
        return False, f"{label} MISSING: {path}"
    return True, f"{label} FOUND: {path}"


def timestamp():
    """Current ISO-8601 timestamp in UTC+8."""
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def now_iso():
    """Current ISO-8601 timestamp."""
    return datetime.now(TZ).isoformat()


# ── Upstream validation ───────────────────────────────────────────────────

def validate_v112s(v112s):
    """Validate v112S result meets v112T prerequisites."""
    issues = []

    checks = {
        "status": "passed",
        "gate_preview_integration_passed": True,
        "real_send_candidate_count": 0,
        "eligible_for_real_send_count": 0,
        "state_write_performed": False,
        "real_live_api_called": False,
        "real_tg_sent": False,
    }

    for key, expected in checks.items():
        actual = v112s.get(key)
        if actual != expected:
            issues.append(f"v112S.{key}: expected={expected}, got={actual}")

    return len(issues) == 0, issues


def validate_v112q(v112q):
    """Validate v112Q result meets v112T prerequisites."""
    issues = []

    checks = {
        "status": "passed",
        "stricter_thresholds_ready": True,
    }

    for key, expected in checks.items():
        actual = v112q.get(key)
        if actual != expected:
            issues.append(f"v112Q.{key}: expected={expected}, got={actual}")

    return len(issues) == 0, issues


def validate_artifacts():
    """Check all required v112T artifact files exist."""
    results = {}
    all_ok = True
    for name, path in REQUIRED_ARTIFACTS.items():
        ok, msg = file_exists(path, name)
        results[name] = {"exists": ok, "path": path}
        if not ok:
            all_ok = False
    return all_ok, results


# ── Stop conditions validation ────────────────────────────────────────────

def validate_stop_conditions(stop_config):
    """Validate that stop_conditions JSON has all required decision modes and rules."""
    issues = []

    decisions = stop_config.get("stop_conditions", {})
    required_modes = ["ABORT", "DEGRADE_TO_MOCK", "CONTINUE"]

    for mode in required_modes:
        if mode not in decisions:
            issues.append(f"Missing stop_conditions.{mode}")
            continue
        rules = decisions[mode].get("rules", [])
        if not rules:
            issues.append(f"stop_conditions.{mode}.rules is empty")

    # Check ABORT has specific conditions
    abort_rules = decisions.get("ABORT", {}).get("rules", [])
    abort_ids = {r["id"] for r in abort_rules}
    required_abort = [
        "ABORT_HTTP_NON_2XX", "ABORT_HTTP_429", "ABORT_REQUEST_TIMEOUT",
        "ABORT_TOTAL_DURATION", "ABORT_JSON_PARSE_FAILURE", "ABORT_SCHEMA_MISMATCH",
        "ABORT_PRICE_DIVERGENCE", "ABORT_TIMESTAMP_SKEW", "ABORT_REQUIRED_FIELDS_MISSING"
    ]
    for rid in required_abort:
        if rid not in abort_ids:
            issues.append(f"Missing ABORT rule: {rid}")

    # Check DEGRADE has specific conditions
    degrade_rules = decisions.get("DEGRADE_TO_MOCK", {}).get("rules", [])
    degrade_ids = {r["id"] for r in degrade_rules}
    required_degrade = [
        "DEGRADE_PARTIAL_ASSET_FAILURE", "DEGRADE_OPTIONAL_FIELDS_MISSING",
        "DEGRADE_THRESHOLD_BOUNDARY", "DEGRADE_SOURCE_FRESHNESS",
        "DEGRADE_MULTI_SOURCE_UNCERTAIN"
    ]
    for rid in required_degrade:
        if rid not in degrade_ids:
            issues.append(f"Missing DEGRADE rule: {rid}")

    # Check CONTINUE has eligible_for_real_send=false
    continue_rules = decisions.get("CONTINUE", {}).get("rules", [])
    has_eligible_false = any(
        "eligible_for_real_send" in r.get("condition", "").lower() or
        "CONTINUE_ELIGIBLE_FALSE" == r.get("id", "")
        for r in continue_rules
    )
    if not has_eligible_false:
        issues.append("CONTINUE missing eligible_for_real_send=false rule")

    return len(issues) == 0, issues


# ── Schema validation ─────────────────────────────────────────────────────

def validate_live_source_schema(schema):
    """Validate LiveSourceResponse schema has required fields."""
    issues = []

    required_top = schema.get("required", [])
    required_fields = {"source_name", "fetched_at", "request_mode", "assets", "validation_status", "stop_decision"}
    missing_top = required_fields - set(required_top)
    if missing_top:
        issues.append(f"Schema missing top-level required fields: {missing_top}")

    # Check eligible_for_real_send is const: false
    eligible = (
        schema.get("properties", {})
        .get("eligible_for_real_send", {})
    )
    if eligible.get("const") is not False:
        issues.append("eligible_for_real_send must be const: false in schema")

    # Check asset required fields
    asset_props = (
        schema.get("properties", {})
        .get("assets", {})
        .get("items", {})
        .get("properties", {})
    )
    asset_required = (
        schema.get("properties", {})
        .get("assets", {})
        .get("items", {})
        .get("required", [])
    )
    required_asset_fields = {"asset_id", "symbol", "price_usd", "price_change_pct", "last_updated_at"}
    missing_asset = required_asset_fields - set(asset_required)
    if missing_asset:
        issues.append(f"Asset schema missing required fields: {missing_asset}")

    # Check nullable fields
    nullable_fields = ["open_interest_change_pct", "source_latency_ms"]
    for nf in nullable_fields:
        if nf in asset_props:
            if not asset_props[nf].get("nullable", False):
                issues.append(f"Asset field {nf} should be nullable")

    # Check request_mode enum
    request_mode = (
        schema.get("properties", {})
        .get("request_mode", {})
        .get("enum", [])
    )
    if "planned_one_shot" not in request_mode:
        issues.append("request_mode enum missing planned_one_shot")

    # Check stop_decision enum
    stop_decision = (
        schema.get("properties", {})
        .get("stop_decision", {})
        .get("enum", [])
    )
    required_decisions = {"CONTINUE", "ABORT", "DEGRADE_TO_MOCK"}
    if not required_decisions.issubset(set(stop_decision)):
        issues.append(f"stop_decision enum missing: {required_decisions - set(stop_decision)}")

    return len(issues) == 0, issues


# ── Run report generation ─────────────────────────────────────────────────

def generate_run_report(result, upstream, artifacts, stop_ok, schema_ok):
    """Generate the run report markdown."""
    lines = []
    lines.append("# v112T One-Shot Free Source Plan — Run Report")
    lines.append("")
    lines.append(f"**Generated**: {timestamp()}")
    lines.append(f"**Status**: {result['status']}")
    lines.append("")
    lines.append("## Upstream Validation")
    lines.append("")
    lines.append("| Check | Status |")
    lines.append("|-------|--------|")
    for check, status in upstream.items():
        marker = "[PASS]" if status else "[FAIL]"
        lines.append(f"| {check} | {marker} |")
    lines.append("")
    lines.append("## Artifact Validation")
    lines.append("")
    lines.append("| Artifact | Exists |")
    lines.append("|----------|--------|")
    for name, info in artifacts.items():
        marker = "[PASS]" if info["exists"] else "[FAIL]"
        lines.append(f"| {name} | {marker} |")
    lines.append("")
    lines.append("## Stop Conditions Validation")
    lines.append("")
    lines.append(f"- {'[PASS]' if stop_ok else '[FAIL]'} All required stop condition rules present")
    lines.append("")
    lines.append("## Schema Validation")
    lines.append("")
    lines.append(f"- {'[PASS]' if schema_ok else '[FAIL]'} LiveSourceResponse schema valid")
    lines.append("")
    lines.append("## Result Summary")
    lines.append("")
    for key in [
        "version", "status", "dry_run_only", "plan_only", "live_ready",
        "real_live_api_called", "real_tg_sent", "external_api_called",
        "external_ai_called", "daemon_started", "files_deleted",
        "candidate_card_type", "free_source_plan_ready", "stop_conditions_ready",
        "field_mapping_ready", "live_source_response_schema_ready",
        "live_to_mock_adapter_spec_ready", "real_send_ready",
        "production_state_write_ready", "v112u_requires_user_confirmation",
        "recommended_next_step"
    ]:
        val = result.get(key)
        lines.append(f"- **{key}**: `{val}`")
    lines.append("")
    lines.append("## Decision Modes")
    lines.append("")
    for mode in result.get("decision_modes", []):
        lines.append(f"- {mode}")
    lines.append("")
    lines.append("## Safety Constraints")
    lines.append("")
    lines.append("- [PASS] No live API requests made")
    lines.append("- [PASS] No API keys read or output")
    lines.append("- [PASS] No Telegram messages sent")
    lines.append("- [PASS] No production state written")
    lines.append("- [PASS] No daemon/cron/background process started")
    lines.append("- [PASS] No external AI API called")
    lines.append("- [PASS] No files deleted")
    lines.append("")
    return "\n".join(lines)


def generate_handoff(result):
    """Generate the handoff markdown."""
    lines = []
    lines.append("# v112T One-Shot Free Source Plan — Handoff")
    lines.append("")
    lines.append(f"**Generated**: {timestamp()}")
    lines.append(f"**Version**: {result['version']}")
    lines.append(f"**Status**: {result['status']}")
    lines.append("")
    lines.append("## What Was Done")
    lines.append("")
    lines.append("- Defined free data source candidates: CoinGecko Public REST (primary), CoinCap Public REST (fallback)")
    lines.append("- Defined complete field mapping: raw source → normalized → v112Q threshold")
    lines.append("- Defined three-state stop conditions: CONTINUE / ABORT / DEGRADE_TO_MOCK")
    lines.append("- Created LiveSourceResponse JSON Schema for normalized live data")
    lines.append("- Created LiveToMockAdapter conversion spec (live → v112R mock input)")
    lines.append("- Defined rate limit / timeout / fallback strategy")
    lines.append("- Created v112T runner and test scripts")
    lines.append("- Validated upstream v112S and v112Q status")
    lines.append("")
    lines.append("## What Was NOT Done (by design)")
    lines.append("")
    lines.append("- [NOT_DONE] No live HTTP requests to CoinGecko or CoinCap")
    lines.append("- [NOT_DONE] No live fetcher written")
    lines.append("- [NOT_DONE] No API keys read or output")
    lines.append("- [NOT_DONE] No Telegram messages sent")
    lines.append("- [NOT_DONE] No production state written")
    lines.append("- [NOT_DONE] No daemon, cron, or background process started")
    lines.append("- [NOT_DONE] No external AI API called")
    lines.append("- [NOT_DONE] No files deleted")
    lines.append("")
    lines.append("## Files Generated")
    lines.append("")
    lines.append("| File | Type |")
    lines.append("|------|------|")
    lines.append("| `config/market_radar_v112t_free_source_mapping.json` | Config |")
    lines.append("| `config/market_radar_v112t_stop_conditions.json` | Config |")
    lines.append("| `schemas/market_radar_v112t_live_source_response_schema.json` | Schema |")
    lines.append("| `schemas/market_radar_v112t_live_to_mock_adapter_spec.md` | Spec |")
    lines.append("| `docs/market_radar_v112t_free_source_plan.md` | Documentation |")
    lines.append("| `scripts/run_market_radar_v112t_one_shot_free_source_plan.py` | Runner |")
    lines.append("| `scripts/test_market_radar_v112t_plan_validation.py` | Test |")
    lines.append("| `results/market_radar_v112t_one_shot_free_source_plan_result.json` | Result |")
    lines.append("| `runs/market_radar/v112t_one_shot_free_source_plan.md` | Run Report |")
    lines.append("| `runs/market_radar/v112t_one_shot_free_source_plan_handoff.md` | Handoff |")
    lines.append("")
    lines.append("## Next Step")
    lines.append("")
    lines.append(f"**{result['recommended_next_step']}**")
    lines.append("")
    lines.append("v112U requires explicit user confirmation before making any real HTTP requests.")
    lines.append("The user must acknowledge:")
    lines.append("")
    lines.append("1. Real HTTP requests will be made to api.coingecko.com and api.coincap.io")
    lines.append("2. Free-tier rate limits apply")
    lines.append("3. No Telegram messages will be sent")
    lines.append("4. No production state will be written")
    lines.append("")
    lines.append("## Safety Affirmation")
    lines.append("")
    lines.append("- `real_live_api_called`: **false**")
    lines.append("- `real_tg_sent`: **false**")
    lines.append("- `external_api_called`: **false**")
    lines.append("- `external_ai_called`: **false**")
    lines.append("- `daemon_started`: **false**")
    lines.append("- `files_deleted`: **false**")
    lines.append("- `eligible_for_real_send`: **false** (policy constraint)")
    lines.append("")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    run_start = timestamp()
    errors = []
    warnings = []

    print("=" * 70)
    print("v112T One-Shot Free Source Plan Runner")
    print(f"Run start: {run_start}")
    print("=" * 70)

    # ── Step 1: Validate upstream state ───────────────────────────────────
    print("\n[1/6] Validating upstream state...")

    upstream_checks = {}

    # v112S
    v112s, v112s_err = load_json(V112S_RESULT, "v112S result")
    if v112s_err:
        errors.append(f"v112S load error: {v112s_err}")
        v112s_ok = False
        v112s_issues = [v112s_err]
    else:
        v112s_ok, v112s_issues = validate_v112s(v112s)
    upstream_checks["v112S status == passed"] = v112s.get("status") == "passed" if v112s else False
    upstream_checks["v112S gate_preview_integration_passed"] = v112s.get("gate_preview_integration_passed") == True if v112s else False
    upstream_checks["v112S real_send_candidate_count == 0"] = v112s.get("real_send_candidate_count") == 0 if v112s else False
    upstream_checks["v112S eligible_for_real_send_count == 0"] = v112s.get("eligible_for_real_send_count") == 0 if v112s else False
    upstream_checks["v112S state_write_performed == false"] = v112s.get("state_write_performed") == False if v112s else False
    upstream_checks["v112S real_live_api_called == false"] = v112s.get("real_live_api_called") == False if v112s else False
    upstream_checks["v112S real_tg_sent == false"] = v112s.get("real_tg_sent") == False if v112s else False

    # v112Q
    v112q, v112q_err = load_json(V112Q_RESULT, "v112Q result")
    if v112q_err:
        errors.append(f"v112Q load error: {v112q_err}")
        v112q_ok = False
    else:
        v112q_ok, v112q_issues = validate_v112q(v112q)
    upstream_checks["v112Q status == passed"] = v112q.get("status") == "passed" if v112q else False
    upstream_checks["v112Q stricter_thresholds_ready == true"] = v112q.get("stricter_thresholds_ready") == True if v112q else False

    all_upstream_ok = all(upstream_checks.values())

    if v112s_issues:
        for issue in v112s_issues:
            print(f"  {WARN_MARK} {issue}")
            warnings.append(issue)
    print(f"  v112S valid: {v112s_ok}")
    print(f"  v112Q valid: {v112q_ok}")
    print(f"  Upstream OK: {all_upstream_ok}")

    # ── Step 2: Validate artifacts ────────────────────────────────────────
    print("\n[2/6] Validating v112T artifacts...")
    artifacts_ok, artifact_results = validate_artifacts()
    for name, info in artifact_results.items():
        marker = OK_MARK if info["exists"] else FAIL_MARK
        print(f"  {marker} {name}")
    if not artifacts_ok:
        missing = [n for n, i in artifact_results.items() if not i["exists"]]
        errors.append(f"Missing artifacts: {missing}")
    print(f"  Artifacts OK: {artifacts_ok}")

    # ── Step 3: Validate stop conditions config ───────────────────────────
    print("\n[3/6] Validating stop conditions...")
    stop_config, stop_err = load_json(REQUIRED_ARTIFACTS["stop_conditions"], "stop_conditions")
    if stop_err:
        errors.append(f"Stop conditions load error: {stop_err}")
        stop_ok = False
    else:
        stop_ok, stop_issues = validate_stop_conditions(stop_config)
        for issue in stop_issues:
            print(f"  {WARN_MARK} {issue}")
            warnings.append(issue)
    print(f"  Stop conditions OK: {stop_ok}")

    # ── Step 4: Validate LiveSourceResponse schema ────────────────────────
    print("\n[4/6] Validating LiveSourceResponse schema...")
    schema, schema_err = load_json(REQUIRED_ARTIFACTS["live_source_response_schema"], "live_source_schema")
    if schema_err:
        errors.append(f"Schema load error: {schema_err}")
        schema_ok = False
    else:
        schema_ok, schema_issues = validate_live_source_schema(schema)
        for issue in schema_issues:
            print(f"  {WARN_MARK} {issue}")
            warnings.append(issue)
    print(f"  Schema OK: {schema_ok}")

    # ── Step 5: Validate field mapping config ─────────────────────────────
    print("\n[5/6] Validating field mapping config...")
    mapping, mapping_err = load_json(REQUIRED_ARTIFACTS["free_source_mapping"], "free_source_mapping")
    if mapping_err:
        errors.append(f"Field mapping load error: {mapping_err}")
        mapping_ok = False
    else:
        # Basic validation
        mapping_issues = []
        if mapping.get("candidate_card_type") != "multi_asset_market_sync":
            mapping_issues.append("candidate_card_type is not multi_asset_market_sync")
        sources = mapping.get("sources", {})
        if "primary" not in sources:
            mapping_issues.append("Missing primary source")
        if "fallback" not in sources:
            mapping_issues.append("Missing fallback source")
        forbidden = mapping.get("sources", {}).get("forbidden_sources", [])
        forbidden_names = [f["source"] for f in forbidden]
        required_forbidden = ["CoinGecko Pro", "CoinMarketCap", "Glassnode"]
        for rf in required_forbidden:
            if not any(rf in fn for fn in forbidden_names):
                mapping_issues.append(f"Missing forbidden source: {rf}")
        if "field_mapping" not in mapping:
            mapping_issues.append("Missing field_mapping section")
        else:
            fm = mapping["field_mapping"]
            if "coingecko_to_normalized" not in fm:
                mapping_issues.append("Missing coingecko_to_normalized mapping")
            if "coincap_to_normalized" not in fm:
                mapping_issues.append("Missing coincap_to_normalized mapping")
            if "normalized_to_v112q_threshold" not in fm:
                mapping_issues.append("Missing normalized_to_v112q_threshold mapping")

        mapping_ok = len(mapping_issues) == 0
        for issue in mapping_issues:
            print(f"  {WARN_MARK} {issue}")
            warnings.append(issue)
    print(f"  Field mapping OK: {mapping_ok}")

    # ── Step 6: Generate result ───────────────────────────────────────────
    print("\n[6/6] Generating result files...")

    overall_ok = all_upstream_ok and artifacts_ok and stop_ok and schema_ok and mapping_ok

    result = {
        "version": "v1.12-t",
        "status": "passed" if overall_ok else "partial",
        "dry_run_only": True,
        "plan_only": True,
        "live_ready": False,
        "real_live_api_called": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "candidate_card_type": "multi_asset_market_sync",
        "free_source_plan_ready": mapping_ok,
        "stop_conditions_ready": stop_ok,
        "field_mapping_ready": mapping_ok,
        "live_source_response_schema_ready": schema_ok,
        "live_to_mock_adapter_spec_ready": artifact_results.get("live_to_mock_adapter_spec", {}).get("exists", False),
        "decision_modes": ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"],
        "real_send_ready": False,
        "production_state_write_ready": False,
        "v112u_requires_user_confirmation": True,
        "recommended_next_step": "v112u_one_shot_free_source_dry_run_requires_user_confirmation",
        "upstream_validated": all_upstream_ok,
        "artifacts_validated": artifacts_ok,
        "stop_conditions_validated": stop_ok,
        "schema_validated": schema_ok,
        "field_mapping_validated": mapping_ok,
        "errors": errors,
        "warnings": warnings,
        "generated_at": timestamp(),
    }

    # Write result JSON
    os.makedirs(os.path.dirname(V112T_RESULT), exist_ok=True)
    with open(V112T_RESULT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  [PASS] Result: {V112T_RESULT}")

    # Write run report
    os.makedirs(os.path.dirname(V112T_RUN_REPORT), exist_ok=True)
    run_report = generate_run_report(result, upstream_checks, artifact_results, stop_ok, schema_ok)
    with open(V112T_RUN_REPORT, "w", encoding="utf-8") as f:
        f.write(run_report)
    print(f"  [PASS] Run report: {V112T_RUN_REPORT}")

    # Write handoff
    handoff = generate_handoff(result)
    with open(V112T_HANDOFF, "w", encoding="utf-8") as f:
        f.write(handoff)
    print(f"  [PASS] Handoff: {V112T_HANDOFF}")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Status:              {result['status']}")
    print(f"  Plan only:           {result['plan_only']}")
    print(f"  Live API called:     {result['real_live_api_called']}")
    print(f"  TG sent:             {result['real_tg_sent']}")
    print(f"  Free source plan:    {result['free_source_plan_ready']}")
    print(f"  Stop conditions:     {result['stop_conditions_ready']}")
    print(f"  Field mapping:       {result['field_mapping_ready']}")
    print(f"  Schema ready:        {result['live_source_response_schema_ready']}")
    print(f"  Adapter spec:        {result['live_to_mock_adapter_spec_ready']}")
    print(f"  Real send ready:     {result['real_send_ready']}")
    print(f"  v112U needs confirm: {result['v112u_requires_user_confirmation']}")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    [ERROR] {e}")
    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    [WARN] {w}")
    print(f"\n  Next: {result['recommended_next_step']}")
    print("=" * 70)

    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
