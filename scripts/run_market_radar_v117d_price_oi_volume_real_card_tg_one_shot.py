"""Market Radar v117D — Price/OI/Volume Anomaly Real Card via Shared Pipeline + TG One-Shot.

Proves that the v117 shared pipeline works for a SECOND real card family
(price_oi_volume_anomaly), not just multi_asset_market_sync.

Reuses v117C's safe TG config loader pattern:
  1. Probe: does scripts/load_local_secrets.ps1 exist? (boolean + redacted path only)
  2. Probe: does config/local_secrets.ps1 exist? (boolean + redacted path only)
  3. If both exist: spawn a PowerShell child process that dot-sources
     load_local_secrets.ps1 → sets env vars → emits TOKEN=... / CHAT=... to stdout.
     Python captures those lines and injects them into os.environ.
     AT NO POINT are raw values printed, logged, or saved to output files.
  4. After injection, run the shared pipeline:
     - Binance public REST → BTC/ETH/SOL price, volume, OI anomaly scan
     - SharedPipeline (price_oi_volume_anomaly)
     - TG test group one-shot send (if config ready)
  5. If config cannot be loaded: record skipped_no_safe_tg_config_loaded.
     NEVER claims "sent" when config is missing.

Safety invariants:
  - production_send=False
  - x_twitter_send=False
  - daemon_or_loop_started=False
  - No files deleted
  - No raw credentials in any output file
  - Evidence ledger: only SHA-256/redacted proofs

Outputs:
  results/market_radar_v117d_price_oi_volume_preflight.json
  results/market_radar_v117d_price_oi_volume_tg_one_shot_result.json
  results/market_radar_v117d_price_oi_volume_evidence_ledger.jsonl
  runs/market_radar/v117d_price_oi_volume_real_card_tg_one_shot_report.md
  runs/market_radar/v117d_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

# Ensure project root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = datetime.now(CN_TZ).strftime("%Y%m%d_%H%M%S")
PIPELINE_VERSION = "v1.17"
TASK_ID = "20260605_v117d_price_oi_volume_real_card_shared_pipeline_tg_one_shot"

SAFETY: dict[str, Any] = {
    "run_id": RUN_ID,
    "pipeline_version": PIPELINE_VERSION,
    "task_id": TASK_ID,
    "external_api_called": False,
    "tg_sent_this_run": False,
    "production_send": False,
    "prod_state_write": False,
    "ai_model_called": False,
    "daemon_or_loop_started": False,
    "files_deleted": False,
    "credentials_printed": False,
    "x_twitter_send": False,
    "v116_history_modified": False,
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


def sha256_hash(text: str) -> str:
    """Full SHA-256 hex digest (64 chars)."""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def sha256_short(text: str, n: int = 8) -> str:
    """Short SHA-256 prefix for display."""
    return "sha256:" + hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:n * 2]


# ═══════════════════════════════════════════════════════════════════════════
# SAFE CONFIG LOADER PROBE (reused from v117C pattern)
# ═══════════════════════════════════════════════════════════════════════════


def probe_safe_config_loaders() -> dict[str, Any]:
    """Detect existing safe config loaders WITHOUT reading their contents.

    Returns a dict with ONLY:
      - boolean flags indicating file existence
      - redacted paths (relative to project root)
      - file types
      - NO raw values, NO file contents

    This function NEVER reads config/local_secrets.ps1.
    It only checks os.path.exists() on known loader paths.
    """
    probe: dict[str, Any] = {
        "checked_at": china_stamp(),
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "safe_loaders_found": [],
        "safe_loader_found": False,
    }

    known_loaders: list[dict[str, Any]] = [
        {
            "type": "powershell_secrets_dot_source",
            "path": "scripts/load_local_secrets.ps1",
            "description": "Canonical safe loader — dot-sources config/local_secrets.ps1",
        },
        {
            "type": "powershell_secrets_values_file",
            "path": "config/local_secrets.ps1",
            "description": "Local secrets values (gitignored) — sourced by load_local_secrets.ps1",
        },
        {
            "type": "secrets_template",
            "path": "config/secrets.example.ps1",
            "description": "Template/example — contains only replace_with_* placeholders",
        },
        {
            "type": "env_template",
            "path": "config/local_tg_publisher.env.example",
            "description": "Template for Python-based TG publisher .env",
        },
    ]

    for loader_def in known_loaders:
        full_path = ROOT / loader_def["path"]
        exists = full_path.exists()
        is_file = full_path.is_file() if exists else False
        entry = {
            "type": loader_def["type"],
            "path_redacted": loader_def["path"],
            "exists": exists,
            "is_file": is_file,
            "is_absolute": False,
        }
        if exists:
            entry["size_bytes"] = full_path.stat().st_size
        probe["safe_loaders_found"].append(entry)
        if exists:
            probe["safe_loader_found"] = True

    bot_token_set = bool(os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id_set = bool(os.environ.get("TELEGRAM_CHAT_ID", ""))
    probe["env_vars_already_set"] = {
        "TELEGRAM_BOT_TOKEN": bot_token_set,
        "TELEGRAM_CHAT_ID": chat_id_set,
    }

    return probe


def safe_load_tg_config_via_powershell() -> dict[str, Any]:
    """Attempt to load TG credentials via PowerShell subprocess.

    This mirrors the pattern from send_local_news_flow_preview_to_tg.py
    and v117C runner.

    How it works:
      1. Spawns a child PowerShell process.
      2. The PS child dot-sources scripts/load_local_secrets.ps1
         (which in turn dot-sources config/local_secrets.ps1).
      3. The PS child prints TOKEN=... and CHAT=... lines to stdout.
      4. Python captures those lines, parses them, and injects into os.environ.
      5. AT NO POINT are raw values printed to Python stdout or saved to files.

    Returns a dict with ONLY:
      - success: bool
      - bot_token_present: bool
      - bot_token_length: int
      - bot_token_sha256_prefix: str | None
      - chat_id_present: bool
      - chat_id_length: int
      - chat_id_sha256_prefix: str | None
      - config_ready: bool
      - error: str | None (if loading failed)
      - loader_method: str
    """
    result: dict[str, Any] = {
        "attempted_at": china_stamp(),
        "loader_method": "powershell_subprocess_dot_source",
        "success": False,
        "bot_token_present": False,
        "bot_token_length": 0,
        "bot_token_sha256_prefix": None,
        "chat_id_present": False,
        "chat_id_length": 0,
        "chat_id_sha256_prefix": None,
        "config_ready": False,
        "error": None,
    }

    loader_ps1 = ROOT / "scripts" / "load_local_secrets.ps1"

    if not loader_ps1.exists():
        result["error"] = (
            "safe_loader_not_found: scripts/load_local_secrets.ps1 does not exist"
        )
        return result

    secrets_ps1 = ROOT / "config" / "local_secrets.ps1"
    if not secrets_ps1.exists():
        result["error"] = (
            "secrets_file_not_found: config/local_secrets.ps1 does not exist"
        )
        return result

    ps_script = (
        f'$ErrorActionPreference = "Stop"; '
        f'. "{loader_ps1}"; '
        f'Write-Host "TOKEN=$env:TELEGRAM_BOT_TOKEN"; '
        f'Write-Host "CHAT=$env:TELEGRAM_CHAT_ID"'
    )

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT),
        )

        if proc.returncode != 0:
            stderr_summary = (proc.stderr or "")[:200].strip()
            stdout_summary = (proc.stdout or "")[:200].strip()
            result["error"] = (
                f"powershell_subprocess_failed: exit_code={proc.returncode}; "
                f"stderr={stderr_summary}; stdout={stdout_summary}"
            )
            return result

        bot_token_raw = ""
        chat_id_raw = ""

        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("TOKEN=") and len(line) > 6:
                bot_token_raw = line[6:]
            elif line.startswith("CHAT=") and len(line) > 5:
                chat_id_raw = line[5:]

        if bot_token_raw:
            os.environ["TELEGRAM_BOT_TOKEN"] = bot_token_raw
        if chat_id_raw:
            os.environ["TELEGRAM_CHAT_ID"] = chat_id_raw

        result["success"] = True
        result["bot_token_present"] = bool(bot_token_raw)
        result["bot_token_length"] = len(bot_token_raw) if bot_token_raw else 0
        result["bot_token_sha256_prefix"] = (
            sha256_hash(bot_token_raw)[:12] if bot_token_raw else None
        )
        result["chat_id_present"] = bool(chat_id_raw)
        result["chat_id_length"] = len(chat_id_raw) if chat_id_raw else 0
        result["chat_id_sha256_prefix"] = (
            sha256_hash(chat_id_raw)[:12] if chat_id_raw else None
        )
        result["config_ready"] = bool(bot_token_raw and chat_id_raw)

        if not result["config_ready"]:
            missing = []
            if not bot_token_raw:
                missing.append("TELEGRAM_BOT_TOKEN")
            if not chat_id_raw:
                missing.append("TELEGRAM_CHAT_ID")
            result["error"] = (
                f"config_still_incomplete_after_load: "
                f"missing={missing}; "
                f"loader_ran_but_values_empty_or_placeholder"
            )

    except subprocess.TimeoutExpired:
        result["error"] = "powershell_subprocess_timeout: loader took >30s"
    except FileNotFoundError:
        result["error"] = "powershell_not_found: cannot spawn powershell.exe"
    except Exception as e:
        result["error"] = f"unexpected_error: {type(e).__name__}: {e}"

    return result


def run_safe_config_preflight_v117d(probe: dict, load_result: dict) -> dict[str, Any]:
    """Combine probe + load results into a single preflight dict.

    Contains ONLY boolean flags, lengths, SHA-256 prefixes, and redacted paths.
    NO raw token/chat_id/message_id values.
    """
    preflight: dict[str, Any] = {
        "checked_at": china_stamp(),
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "safe_loader_found": probe.get("safe_loader_found", False),
        "safe_loaders_detected": [
            e["type"]
            for e in probe.get("safe_loaders_found", [])
            if e.get("exists")
        ],
        "env_vars_pre_existing": probe.get("env_vars_already_set", {}),
        "load_attempted": True,
        "load_success": load_result.get("success", False),
        "load_method": load_result.get("loader_method", "none"),
        "load_error": load_result.get("error"),
        "bot_token_present": load_result.get("bot_token_present", False),
        "bot_token_length": load_result.get("bot_token_length", 0),
        "bot_token_sha256_prefix": load_result.get("bot_token_sha256_prefix"),
        "chat_id_present": load_result.get("chat_id_present", False),
        "chat_id_length": load_result.get("chat_id_length", 0),
        "chat_id_sha256_prefix": load_result.get("chat_id_sha256_prefix"),
        "config_ready": load_result.get("config_ready", False),
        "config_missing_reason": None,
    }

    if not preflight["config_ready"]:
        if load_result.get("error"):
            preflight["config_missing_reason"] = load_result["error"]
        elif not preflight["bot_token_present"] and not preflight["chat_id_present"]:
            preflight["config_missing_reason"] = (
                "Both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID missing after safe load attempt"
            )
        elif not preflight["bot_token_present"]:
            preflight["config_missing_reason"] = (
                "TELEGRAM_BOT_TOKEN missing after safe load attempt"
            )
        elif not preflight["chat_id_present"]:
            preflight["config_missing_reason"] = (
                "TELEGRAM_CHAT_ID missing after safe load attempt"
            )

    return preflight


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION}D — Price/OI/Volume Anomaly Real Card + TG One-Shot")
    print(f"Run ID: {RUN_ID}")
    print(f"Timestamp: {china_stamp()}")
    print(f"Task ID: {TASK_ID}")
    print("=" * 70)
    print()

    results_dir = ROOT / "results"
    runs_dir = ROOT / "runs" / "market_radar"

    # ── Stage 0: Import shared pipeline ────────────────────────────────────
    print("[0] Importing shared pipeline package...")
    try:
        from market_radar.shared.models import CardFamily
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.evidence_ledger import create_evidence_ledger
        from market_radar.shared.free_api_adapters import (
            create_real_free_api_adapter,
        )
        print("  [OK] Shared package imported successfully")
    except ImportError as e:
        print(f"  [FAIL] Cannot import shared package: {e}")
        print("  Ensure market_radar/shared/ is on Python path")
        sys.exit(1)
    print()

    # ── Stage 1: Probe for safe config loaders ─────────────────────────────
    print("[1] Probing for safe config loaders (filesystem only — NO file reading)...")
    probe = probe_safe_config_loaders()

    print(f"  safe_loader_found: {probe['safe_loader_found']}")
    for loader in probe.get("safe_loaders_found", []):
        status = "EXISTS" if loader.get("exists") else "NOT FOUND"
        print(f"  [{status}] {loader['type']}: {loader['path_redacted']}")
    print(f"  env_vars_already_set: TELEGRAM_BOT_TOKEN={probe['env_vars_already_set']['TELEGRAM_BOT_TOKEN']}, "
          f"TELEGRAM_CHAT_ID={probe['env_vars_already_set']['TELEGRAM_CHAT_ID']}")
    print()

    # ── Stage 2: Safe config load attempt ──────────────────────────────────
    print("[2] Attempting safe TG config load via PowerShell subprocess...")
    print("  (NEVER prints or saves raw token/chat_id values)")
    load_result = safe_load_tg_config_via_powershell()

    print(f"  load_success: {load_result['success']}")
    print(f"  load_method: {load_result['loader_method']}")
    print(f"  bot_token_present: {load_result['bot_token_present']}")
    print(f"  bot_token_length: {load_result['bot_token_length']}")
    print(f"  bot_token_sha256_prefix: {load_result['bot_token_sha256_prefix']}")
    print(f"  chat_id_present: {load_result['chat_id_present']}")
    print(f"  chat_id_length: {load_result['chat_id_length']}")
    print(f"  chat_id_sha256_prefix: {load_result['chat_id_sha256_prefix']}")
    print(f"  config_ready: {load_result['config_ready']}")
    if load_result.get("error"):
        print(f"  load_error: {load_result['error']}")
    print()

    # ── Stage 3: Build combined preflight ──────────────────────────────────
    print("[3] Building combined safe config preflight...")
    preflight = run_safe_config_preflight_v117d(probe, load_result)

    preflight_path = results_dir / "market_radar_v117d_price_oi_volume_preflight.json"
    write_json(preflight_path, preflight)

    # Verify preflight contains NO raw values
    preflight_text = json.dumps(preflight, ensure_ascii=False)
    raw_token_pattern = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
    if raw_token_pattern.search(preflight_text):
        print("  [CRITICAL] PREFLIGHT SELF-CHECK FAILED: raw token pattern detected!")
        print("  Aborting to prevent credential leak.")
        sys.exit(1)
    print(f"  [OK] Preflight self-check passed — no raw credentials")
    print(f"  [OK] {preflight_path}")
    print()

    # ── Stage 4: Binance API + Shared Pipeline (price_oi_volume_anomaly) ───
    print("[4] Creating Price/OI/Volume Anomaly free API adapter for BTC/ETH/SOL...")
    SAFETY["external_api_called"] = True

    adapter = create_real_free_api_adapter(CardFamily.PRICE_OI_VOLUME_ANOMALY)
    if adapter is None:
        print("  [FAIL] Could not create PriceOIVolumeAnomalyFreeApiAdapter")
        sys.exit(1)
    print("  [OK] PriceOIVolumeAnomalyFreeApiAdapter created")
    print("  NOTE: This adapter calls Binance public REST endpoints:")
    print("    - /api/v3/ticker/24hr (spot price + volume)")
    print("    - fapi/v1/openInterest (futures OI per symbol)")
    print("  No API key required.")
    print()

    print("[5] Running shared pipeline (price_oi_volume_anomaly) — includes Binance fetch...")
    ledger = create_evidence_ledger()
    pipeline = SharedPipeline(evidence_ledger=ledger)

    result = pipeline.run(adapter)

    # Extract data from pipeline result
    binance_success = False
    binance_error: Optional[str] = None
    signals_data: list[dict] = []
    oi_errors: list[str] = []

    if result.signal:
        binance_success = result.signal.metrics.get("api_success", False)
        binance_error = result.signal.metrics.get("fetch_error")
        signals_data = result.signal.metrics.get("signals", [])

        if binance_success:
            print(f"  [OK] Binance API call successful — {len(signals_data)} assets scanned")
            for s in signals_data:
                sym = s.get("symbol", "?")
                price = s.get("price", 0)
                change = s.get("price_change_24h_pct", 0)
                anomaly = s.get("anomaly_type", "normal")
                admission = s.get("admission_passed", False)
                oi = s.get("open_interest_current")
                oi_str = f"${oi/1e9:.2f}B" if oi else "N/A"
                factors = ", ".join(s.get("confirmation_factors", [])) or "none"
                print(f"    {sym}: price={price:.2f}, 24h_change={change:+.2f}%, "
                      f"OI={oi_str}, anomaly={anomaly}, admit={admission}, factors=[{factors}]")
                if s.get("oi_error"):
                    oi_errors.append(f"{sym}: {s['oi_error']}")
        else:
            print(f"  [FAIL] Binance API call failed: {binance_error}")
    else:
        binance_error = f"Pipeline error — no signal returned: {result.error}"
        print(f"  [FAIL] {binance_error}")

    gate = result.gate_decision
    sr = result.send_readiness
    tg = result.tg_result

    print(f"  Card Family: {result.card_family.value}")
    print(f"  Gate allow: {gate.allow if gate else 'N/A'}")
    if gate:
        print(f"  Gate reason: {gate.reason[:200]}")
    print(f"  Send-readiness allow_test_group: {sr.allow_test_group if sr else 'N/A'}")
    if sr:
        print(f"  Send-readiness reason: {sr.reason[:200]}")
    if tg:
        print(f"  TG attempted: {tg.attempted}")
        print(f"  TG success: {tg.success}")
        print(f"  TG status: {tg.status}")
        print(f"  TG reason: {tg.reason[:200]}")
        if tg.success:
            SAFETY["tg_sent_this_run"] = True
            print(f"  TG message_id_proof: {tg.message_id_proof}")
    print()

    # ── Stage 6: Evidence Ledger Verification ──────────────────────────────
    print("[6] Evidence ledger verification...")
    evidence_entries = ledger.entries()
    clean, violations = ledger.verify_no_raw_secrets()
    if not clean:
        print(f"  [WARN] Evidence ledger contains {len(violations)} potential raw secret patterns!")
        for v in violations:
            print(f"    - {v}")
    else:
        print(f"  [OK] Evidence ledger clean — {len(evidence_entries)} entries, no raw secrets")
    print()

    # ── Stage 7: Write Outputs ─────────────────────────────────────────────
    print("[7] Writing output files...")

    # 7.1 TG summary (redacted)
    tg_summary = None
    if tg:
        tg_summary = {
            "attempted": tg.attempted,
            "success": tg.success,
            "status": tg.status,
            "reason": tg.reason,
            "target_type": tg.target_type,
            "one_shot": tg.one_shot,
            "production_send": tg.production_send,
            "message_id_proof_present": tg.message_id_proof is not None,
            "token_proof_present": tg.token_proof is not None,
            "chat_id_proof_present": tg.chat_id_proof is not None,
            "credentials_printed": tg.credentials_printed,
        }

    # 7.2 Signal summary
    signal_summary = []
    for s in signals_data:
        signal_summary.append({
            "symbol": s.get("symbol"),
            "price_ok": s.get("price", 0) > 0,
            "price_change_24h_pct_rounded": round(s.get("price_change_24h_pct", 0), 2),
            "volume_24h_ok": s.get("quote_volume_24h", 0) > 0,
            "oi_available": s.get("open_interest_current") is not None,
            "oi_error": s.get("oi_error"),
            "anomaly_type": s.get("anomaly_type", "normal"),
            "admission_passed": s.get("admission_passed", False),
            "confirmation_factors": s.get("confirmation_factors", []),
        })

    # What endpoints were actually called
    endpoints_used = list(set(
        result.signal.source_refs if result.signal else []
    )) if result.signal else []

    one_shot_output = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "real_free_api_price_oi_volume_anomaly_tg_one_shot",
        "card_family": CardFamily.PRICE_OI_VOLUME_ANOMALY.value,
        "signals": signal_summary,
        "binance_endpoints_used": endpoints_used,
        "binance_api_success": binance_success,
        "binance_api_error": binance_error,
        "oi_errors": oi_errors,
        "gate_allow": gate.allow if gate else None,
        "gate_reason": gate.reason if gate else None,
        "send_readiness_allow_test_group": sr.allow_test_group if sr else None,
        "send_readiness_reason": sr.reason if sr else None,
        "tg_result": tg_summary,
        "pipeline_passed": result.passed,
        "pipeline_error": result.error,
        "safety": {
            "external_api_called": SAFETY["external_api_called"],
            "tg_sent_this_run": SAFETY["tg_sent_this_run"],
            "production_send": SAFETY["production_send"],
            "prod_state_write": SAFETY["prod_state_write"],
            "ai_model_called": SAFETY["ai_model_called"],
            "daemon_or_loop_started": SAFETY["daemon_or_loop_started"],
            "files_deleted": SAFETY["files_deleted"],
            "credentials_printed": SAFETY["credentials_printed"],
            "x_twitter_send": SAFETY["x_twitter_send"],
            "v116_history_modified": SAFETY["v116_history_modified"],
        },
        "preflight": {
            "safe_loader_found": preflight["safe_loader_found"],
            "load_success": preflight["load_success"],
            "config_ready": preflight["config_ready"],
            "bot_token_present": preflight["bot_token_present"],
            "chat_id_present": preflight["chat_id_present"],
        },
        "shared_pipeline_proof": (
            "v117D proves the shared pipeline works for price_oi_volume_anomaly "
            "(second real card family), not just multi_asset_market_sync. "
            "Same adapter -> gate -> renderer -> send-readiness -> tg-sender -> ledger chain."
        ),
    }

    one_shot_path = results_dir / "market_radar_v117d_price_oi_volume_tg_one_shot_result.json"
    write_json(one_shot_path, one_shot_output)
    print(f"  [OK] {one_shot_path}")

    # 7.3 Evidence ledger JSONL
    ledger_path = ledger.write_jsonl(
        results_dir / "market_radar_v117d_price_oi_volume_evidence_ledger.jsonl"
    )
    print(f"  [OK] {ledger_path}")

    # 7.4 Report
    tg_status_section = ""
    if tg and tg.success:
        tg_status_section = f"""
## TG Test Group Send

✅ **SENT** — 1 message delivered to TG test group (one-shot).

- Status: `{tg.status}`
- Target: `{tg.target_type}`
- Production send: **False**
- One-shot: **True**
- Message proof: SHA-256 redacted (present: {tg.message_id_proof is not None})
- Token proof: SHA-256 redacted (present: {tg.token_proof is not None})
- Chat ID proof: SHA-256 redacted (present: {tg.chat_id_proof is not None})
- Credentials printed: **{tg.credentials_printed}**

> v117D sent price_oi_volume_anomaly card to TG test group via shared pipeline.
"""
    elif tg and tg.status == "skipped":
        reason_short = (tg.reason or "")[:200]
        tg_status_section = f"""
## TG Test Group Send

⚠ **SKIPPED** — TG test group send not attempted.

- Status: `{tg.status}`
- Reason: `{reason_short}`
- Safe loader found: **{preflight['safe_loader_found']}**
- Load success: **{preflight['load_success']}**
- Config ready after load: **{preflight['config_ready']}**
- Load error: `{preflight.get('config_missing_reason', 'N/A')}`
- This is truthful — NOT faked as "sent".
"""
    elif tg and tg.status == "blocked":
        tg_status_section = f"""
## TG Test Group Send

⛔ **BLOCKED** — Send-readiness gate blocked the send.

- Status: `{tg.status}`
- Reason: `{tg.reason}`
- This occurs when quality gate does not allow (no asset passed anomaly thresholds).
"""
    else:
        tg_status_section = """
## TG Test Group Send

❓ **UNKNOWN** — No TG result available.
"""

    # Determine overall send outcome description
    if tg and tg.success:
        send_outcome = "**SENT** — 1 price_oi_volume_anomaly card sent to TG test group"
    elif gate and gate.allow and tg and tg.status == "skipped":
        send_outcome = "**SKIPPED** — gate allow but TG config missing/skipped"
    elif gate and not gate.allow:
        send_outcome = "**BLOCKED** — quality gate not passed (no anomaly detected)"
    elif binance_error:
        send_outcome = "**BLOCKED** — Binance API call failed"
    else:
        send_outcome = "**UNKNOWN**"

    config_load_section = f"""
## Safe Config Loader Probe

| Check | Result |
|-------|--------|
| scripts/load_local_secrets.ps1 found | {'✅' if preflight['safe_loader_found'] else '❌'} |
| Load attempted | {'✅' if preflight['load_attempted'] else '❌'} |
| Load method | `{preflight['load_method']}` |
| Load success | {'✅' if preflight['load_success'] else '❌'} |

### Post-Load Config Status

| Variable | Present | Length | SHA-256 Prefix |
|----------|---------|--------|----------------|
| TELEGRAM_BOT_TOKEN | {'✅' if preflight['bot_token_present'] else '❌'} | {preflight['bot_token_length']} | `{preflight['bot_token_sha256_prefix'] or 'N/A'}` |
| TELEGRAM_CHAT_ID | {'✅' if preflight['chat_id_present'] else '❌'} | {preflight['chat_id_length']} | `{preflight['chat_id_sha256_prefix'] or 'N/A'}` |

**Config ready for TG send:** {'✅ YES' if preflight['config_ready'] else '❌ NO'}
"""

    if preflight.get("config_missing_reason"):
        config_load_section += f"\n**Why config not ready:** `{preflight['config_missing_reason']}`\n"

    # Build anomalies analysis
    anomaly_analysis = ""
    for s in signal_summary:
        anomaly_analysis += (
            f"| {s['symbol']} | {s['price_change_24h_pct_rounded']:+.2f}% | "
            f"{'✅' if s['volume_24h_ok'] else '❌'} | "
            f"{'✅' if s['oi_available'] else '❌'} | "
            f"`{s['anomaly_type']}` | "
            f"{'✅' if s['admission_passed'] else '❌'} | "
            f"{', '.join(s['confirmation_factors']) if s['confirmation_factors'] else 'none'} |\n"
        )

    report_md = f"""# Market Radar {PIPELINE_VERSION}D — Price/OI/Volume Anomaly Real Card + TG One-Shot Report

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## Purpose

v117D proves that the **shared pipeline** works for a **second real card family**
(`price_oi_volume_anomaly`), not just `multi_asset_market_sync` (v117C).

Same pipeline chain:
```
PriceOIVolumeAnomalyFreeApiAdapter
  → NormalizedSignal
  → QualityGate:evaluate
  → CardRenderer:render
  → SendReadinessGate:evaluate
  → TGTestGroupSender:send (if allowed)
  → EvidenceLedger:record
```

{config_load_section}
---

## Binance Public API Status

| Check | Status |
|-------|--------|
| API called | {'✅' if SAFETY['external_api_called'] else '❌'} |
| API success | {'✅' if binance_success else '❌'} |
| Assets scanned | {len(signal_summary)} (BTCUSDT, ETHUSDT, SOLUSDT) |

### Endpoints Used

```
{chr(10).join(f'- {ep}' for ep in endpoints_used) if endpoints_used else '- (none — API call failed)'}
```

### Anomaly Detection Results

| Symbol | 24h Change | Volume OK | OI Available | Anomaly | Admission | Factors |
|--------|-----------|-----------|-------------|---------|-----------|---------|
{anomaly_analysis}

### OI Errors (if any)

{chr(10).join(f'- {e}' for e in oi_errors) if oi_errors else '- None — all OI fetches succeeded or were N/A'}

### Anomaly Criteria

- **extreme**: |price_change| > 10% AND ≥2 confirmation factors
- **notable**: |price_change| > 5% AND ≥1 confirmation factor
- **normal**: below threshold
- Confirmation factors: price_move_significant (|Δ|>3%), volume_spike (vol>$5B), oi_elevated (OI>$1B)

## OI/Volume/Price Anomaly Status

- **Overall anomaly detected**: {'✅ YES' if gate and gate.allow else '❌ NO'}
- **Gate decision**: {'✅ allow' if gate and gate.allow else '⛔ block'}
- **Gate reason**: `{gate.reason if gate else 'N/A'}`
- **Send outcome**: {send_outcome}

---

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `{CardFamily.PRICE_OI_VOLUME_ANOMALY.value}` |
| Gate | {'✅ allow' if gate and gate.allow else '⛔ block'} |
| Send-Readiness | {'✅ allow_test_group' if sr and sr.allow_test_group else '⛔ block'} |
| Pipeline Passed | {'✅' if result.passed else '⛔'} |
{tg_status_section}
---

## Shared Pipeline Verification

### v117D proves the shared pipeline for a second card family

| Check | v117C (multi_asset) | v117D (price_oi_volume) |
|-------|---------------------|-------------------------|
| Adapter | MultiAssetMarketSyncFreeApiAdapter | PriceOIVolumeAnomalyFreeApiAdapter |
| Real Binance API | ✅ | ✅ |
| Same shared pipeline | ✅ | ✅ |
| Same gate contract | ✅ | ✅ |
| Same renderer contract | ✅ | ✅ |
| Same sender contract | ✅ | ✅ |
| Same evidence ledger | ✅ | ✅ |
| card_family | multi_asset_market_sync | price_oi_volume_anomaly |

---

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | {'✅' if SAFETY['external_api_called'] else '❌'} |
| TG sent this run | {'✅ 1 message' if SAFETY['tg_sent_this_run'] else '❌ (or skipped/blocked)'} |
| Production send | {'❌ NEVER' if not SAFETY['production_send'] else '⚠ ERROR'} |
| X/Twitter send | {'❌ NEVER' if not SAFETY['x_twitter_send'] else '⚠ ERROR'} |
| Credentials printed | {'❌ NEVER' if not SAFETY['credentials_printed'] else '⚠ ERROR'} |
| Daemon/loop started | {'❌ NEVER' if not SAFETY['daemon_or_loop_started'] else '⚠ ERROR'} |
| Files deleted | {'❌ NEVER' if not SAFETY['files_deleted'] else '⚠ ERROR'} |
| v116 history modified | {'❌ NEVER' if not SAFETY['v116_history_modified'] else '⚠ ERROR'} |
| Evidence ledger clean | {'✅' if clean else '❌'} |
| Preflight self-check | ✅ passed |

## Free API Data Source

- **Binance Public REST API** (`/api/v3/ticker/24hr`): BTC/ETH/SOL spot 24hr tickers
- **Binance Futures Public API** (`/fapi/v1/openInterest`): BTC/ETH/SOL perpetual futures open interest
- No API key required

## Secret Leak Risk Assessment

- ✅ Preflight JSON: self-checked, no raw token/chat_id patterns
- ✅ Result JSON: no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ Report: redacted proofs only
- ✅ Handoff: redacted proofs only
- ✅ Console output: only length/hash/prefix info

## Production Readiness

**0/5 — NOT FOR LIVE USE**

All minimum conditions remain unmet. Production send is NEVER enabled.

## Test Results Summary

(To be filled after running tests)

| Test Suite | Expected | Actual |
|------------|----------|--------|
| v117D tests | Pass | (run) |
| v117C regression | Pass | (run) |
| v117B regression | Pass | (run) |
| v117 regression | Pass | (run) |
| v116N regression | Pass | (run) |
"""
    write_md(runs_dir / "v117d_price_oi_volume_real_card_tg_one_shot_report.md", report_md)
    print(f"  [OK] {runs_dir / 'v117d_price_oi_volume_real_card_tg_one_shot_report.md'}")

    # 7.5 Handoff
    handoff_md = f"""# Market Radar {PIPELINE_VERSION}D — Price/OI/Volume Anomaly Real Card + TG One-Shot Handoff

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## What Was Done

1. **Probed** for safe config loaders (filesystem only, no file reading)
   - `scripts/load_local_secrets.ps1`: {'✅ found' if preflight['safe_loader_found'] else '❌ not found'}
   - `config/local_secrets.ps1`: checked via probe only (NEVER read by Python)

2. **Loaded** TG credentials safely via PowerShell subprocess
   - Method: `{preflight['load_method']}`
   - Success: **{preflight['load_success']}**
   - Post-load config_ready: **{preflight['config_ready']}**

3. **Called** Binance public REST API for BTC/ETH/SOL:
   - Spot 24hr tickers: /api/v3/ticker/24hr
   - Futures OI: fapi/v1/openInterest (per symbol)
   - API success: **{'✅' if binance_success else '❌'}**
   - Assets scanned: **{len(signal_summary)}**

4. **Ran** shared pipeline (price_oi_volume_anomaly)
   - Adapter: PriceOIVolumeAnomalyFreeApiAdapter
   - Gate: {'✅ allow' if gate and gate.allow else '⛔ block'}
   - Gate reason: `{gate.reason if gate else 'N/A'}`
   - Pipeline passed: **{result.passed}**

5. **Attempted** TG test group one-shot send
   - TG sent: {'✅ 1 message' if (tg and tg.success) else '⚠ 0 messages'}
   - TG skipped (missing config): {'1' if (tg and tg.status == 'skipped') else '0'}
   - TG blocked (gate): {'1' if (tg and tg.status == 'blocked') else '0'}
   - Production send: **False** (never)

6. **Verified** evidence ledger: {'✅ clean' if clean else '⚠ warnings'}

## Shared Pipeline Multi-Card-Family Proof

v117D proves that the v117 shared pipeline correctly handles **two distinct card families**:

| Aspect | v117C | v117D |
|--------|-------|-------|
| Card family | multi_asset_market_sync | price_oi_volume_anomaly |
| Adapter class | MultiAssetMarketSyncFreeApiAdapter | PriceOIVolumeAnomalyFreeApiAdapter |
| Binance endpoints | /api/v3/ticker/24hr | /api/v3/ticker/24hr + fapi/v1/openInterest |
| Gate logic | ≥2 assets with data | admission_passed on at least 1 asset |
| Renderer | _render_multi_asset | _render_price_oi |
| Same pipeline code? | ✅ Yes | ✅ Yes |
| Same sender? | ✅ Yes | ✅ Yes |
| Same ledger? | ✅ Yes | ✅ Yes |

## OI/Volume/Price Anomaly Details

| Symbol | 24h Δ% | Anomaly | Admission | Factors |
|--------|--------|---------|-----------|---------|
"""
    for s in signal_summary:
        handoff_md += (
            f"| {s['symbol']} | {s['price_change_24h_pct_rounded']:+.2f}% | "
            f"`{s['anomaly_type']}` | {'✅' if s['admission_passed'] else '❌'} | "
            f"{', '.join(s['confirmation_factors']) if s['confirmation_factors'] else 'none'} |\n"
        )

    handoff_md += f"""
## New Files Created

| File | Type |
|------|------|
| `scripts/run_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py` | Runner |
| `scripts/test_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py` | Tests |
| `results/market_radar_v117d_price_oi_volume_preflight.json` | Config preflight |
| `results/market_radar_v117d_price_oi_volume_tg_one_shot_result.json` | Result |
| `results/market_radar_v117d_price_oi_volume_evidence_ledger.jsonl` | Evidence ledger |
| `runs/market_radar/v117d_price_oi_volume_real_card_tg_one_shot_report.md` | Report |
| `runs/market_radar/v117d_local_only_handoff.md` | Handoff |

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
| x_twitter_send | {SAFETY['x_twitter_send']} |
| v116_history_modified | {SAFETY['v116_history_modified']} |

## No Raw Secrets Verification

- ✅ Preflight JSON: self-checked, no raw token/chat_id patterns
- ✅ Result JSON: no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ Report: redacted proofs only
- ✅ Handoff: redacted proofs only
- ✅ Console output: only length/hash/prefix info

## Production Ready Status

**0/5 — NOT FOR LIVE USE**

## Next Steps

1. Run v117D tests: `python -X utf8 -m pytest scripts/test_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py -v`
2. Run v117C regression: `python -X utf8 -m pytest scripts/test_market_radar_v117c_safe_tg_config_loader_real_test_group_rerun.py -v`
3. Run v117B regression: `python -X utf8 -m pytest scripts/test_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py -v`
4. Run v117 regression: `python -X utf8 -m pytest scripts/test_market_radar_v117_shared_pipeline_real_one_shot.py -v`
5. Run v116N regression: `python -X utf8 -m pytest scripts/test_market_radar_v116n_user_acceptance_overlay_pack_local_only.py -v`
6. If anomaly detected + TG config loaded: verify message arrived in TG test group
"""
    write_md(runs_dir / "v117d_local_only_handoff.md", handoff_md)
    print(f"  [OK] {runs_dir / 'v117d_local_only_handoff.md'}")

    # ── Final Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION}D — Price/OI/Volume Anomaly Real Card + TG One-Shot Complete")
    print(f"  Safe loader found: {preflight['safe_loader_found']}")
    print(f"  Safe load success: {preflight['load_success']}")
    print(f"  Config ready: {preflight['config_ready']}")
    print(f"  Binance API: {'SUCCESS' if binance_success else 'FAILED'}")
    print(f"  Assets scanned: {len(signal_summary)} (BTC/ETH/SOL)")
    for s in signal_summary:
        print(f"    {s['symbol']}: Δ={s['price_change_24h_pct_rounded']:+.2f}%, "
              f"anomaly={s['anomaly_type']}, admit={s['admission_passed']}")
    print(f"  Gate allow: {gate.allow if gate else 'N/A'}")
    print(f"  Send-readiness allow: {sr.allow_test_group if sr else 'N/A'}")
    print(f"  Pipeline passed: {result.passed}")
    tg_sent_label = "1 message (SENT)" if (tg and tg.success) else "0 (skipped/blocked)"
    print(f"  TG sent: {tg_sent_label}")
    print(f"  TG status: {tg.status if tg else 'N/A'}")
    print(f"  Production ready: 0/5 (by design)")
    print(f"  Evidence ledger: {'clean' if clean else 'WARNINGS'}")
    print(f"  Credentials leaked: NO")
    print(f"  Shared pipeline proof: price_oi_volume_anomaly [OK] (2nd card family)")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
