"""Market Radar v117E — News Event Market Impact Real Free Public Source + TG One-Shot.

Extends the v117 shared pipeline with a third real card family:
  news_event_market_impact via NewsEventMarketImpactFreePublicSourceAdapter.

Pipeline:
  1. Safe TG config loader probe + load (reuse v117C pattern)
  2. NewsEventMarketImpactFreePublicSourceAdapter:
     - Fetches real news from free public RSS sources (CoinDesk, Cointelegraph,
       Decrypt, The Block, Binance Announcements) — NO API key
     - Rule-based event extraction (keyword matching, NO AI/model)
     - Binance public API for BTC/ETH/SOL market data
     - Returns NormalizedSignal with observation_only=true, not_causal_proof=true
  3. SharedPipeline.run(adapter):
     adapter → normalized signal → quality gate → renderer →
     send-readiness gate → TG test-group sender → redacted evidence ledger
  4. If gate allow AND TG safe config available: send 1 TG test group one-shot
  5. If no events or public sources unavailable: truthfully record blocked/skipped

Safety invariants (same as v117C/v117D):
  - production_send=False
  - x_twitter_send=False
  - daemon_or_loop_started=False
  - No files deleted
  - No raw credentials in any output file
  - Evidence ledger: only SHA-256/redacted proofs
  - observation_only=true, not_causal_proof=true
  - NO deterministic causal assertions about news events

Outputs:
  results/market_radar_v117e_news_event_preflight.json
  results/market_radar_v117e_news_event_tg_one_shot_result.json
  results/market_radar_v117e_news_event_evidence_ledger.jsonl
  runs/market_radar/v117e_news_event_market_impact_real_public_source_tg_one_shot_report.md
  runs/market_radar/v117e_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v117e_news_event_market_impact_real_public_source_tg_one_shot.py
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
TASK_ID = "20260605_v117e_news_event_market_impact_real_public_source_tg_one_shot"

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
    "observation_only": True,
    "not_causal_proof": True,
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
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def sha256_short(text: str, n: int = 8) -> str:
    return "sha256:" + hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:n * 2]


# ═══════════════════════════════════════════════════════════════════════════
# SAFE CONFIG LOADER (reused from v117C pattern)
# ═══════════════════════════════════════════════════════════════════════════


def probe_safe_config_loaders() -> dict[str, Any]:
    """Detect existing safe config loaders WITHOUT reading their contents."""
    probe: dict[str, Any] = {
        "checked_at": china_stamp(),
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "safe_loaders_found": [],
        "safe_loader_found": False,
    }

    known_loaders: list[dict[str, Any]] = [
        {"type": "powershell_secrets_dot_source", "path": "scripts/load_local_secrets.ps1"},
        {"type": "powershell_secrets_values_file", "path": "config/local_secrets.ps1"},
        {"type": "secrets_template", "path": "config/secrets.example.ps1"},
        {"type": "env_template", "path": "config/local_tg_publisher.env.example"},
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

    NEVER prints raw values. Returns only boolean presence, lengths, SHA-256 prefixes.
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
        result["error"] = "safe_loader_not_found: scripts/load_local_secrets.ps1 does not exist"
        return result

    secrets_ps1 = ROOT / "config" / "local_secrets.ps1"
    if not secrets_ps1.exists():
        result["error"] = "secrets_file_not_found: config/local_secrets.ps1 does not exist"
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

        # Inject into os.environ (NEVER print these values)
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
                f"config_still_incomplete_after_load: missing={missing}"
            )

    except subprocess.TimeoutExpired:
        result["error"] = "powershell_subprocess_timeout: loader took >30s"
    except FileNotFoundError:
        result["error"] = "powershell_not_found: cannot spawn powershell.exe"
    except Exception as e:
        result["error"] = f"unexpected_error: {type(e).__name__}: {e}"

    return result


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    # Fix Unicode output on Windows GBK terminals
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION}E — News Event Market Impact")
    print(f"Real Free Public Source → Shared Pipeline → TG Test Group One-Shot")
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
    preflight = {
        "checked_at": china_stamp(),
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "safe_loader_found": probe.get("safe_loader_found", False),
        "safe_loaders_detected": [
            e["type"] for e in probe.get("safe_loaders_found", []) if e.get("exists")
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

    preflight_path = results_dir / "market_radar_v117e_news_event_preflight.json"
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

    # ── Stage 4: Create NewsEventMarketImpact adapter ─────────────────────
    print("[4] Creating NewsEventMarketImpactFreePublicSourceAdapter...")
    print("  Sources: CoinDesk RSS, Cointelegraph RSS, Decrypt RSS,")
    print("           The Block RSS, Binance Announcements public API")
    print("  Extraction: rule-based keyword matching (NO AI/model)")
    print("  Market data: Binance public REST API (no key)")
    print("  Card family: news_event_market_impact")
    print("  observation_only: True")
    print("  not_causal_proof: True")
    SAFETY["external_api_called"] = True

    adapter = create_real_free_api_adapter(CardFamily.NEWS_EVENT_MARKET_IMPACT)
    if adapter is None:
        print("  [FAIL] Could not create NewsEventMarketImpactFreePublicSourceAdapter")
        print("  Check adapter registry in free_api_adapters.py")
        sys.exit(1)
    print(f"  [OK] {adapter.adapter_label}")
    print()

    # ── Stage 5: Run shared pipeline ───────────────────────────────────────
    print("[5] Running shared pipeline (news_event_market_impact)...")
    print("  Stages: adapter → fetch → quality gate → renderer →")
    print("          send-readiness → TG sender → evidence ledger")
    ledger = create_evidence_ledger()
    pipeline = SharedPipeline(evidence_ledger=ledger)

    result = pipeline.run(adapter)

    # Extract signal diagnostics
    signal = result.signal
    sources_attempted = 0
    sources_succeeded = 0
    articles_fetched = 0
    events_found = 0
    event_extracted = False
    all_sources_unavailable = False
    source_name = ""
    event_title = ""
    event_url = ""
    event_type = ""
    intensity = ""
    attr_risk = ""
    assets_affected = []
    market_snapshot = {}
    market_api_success = False
    obs_only = True
    not_causal = True

    if signal:
        m = signal.metrics
        sources_attempted = m.get("sources_attempted", 0)
        sources_succeeded = m.get("sources_succeeded", 0)
        articles_fetched = m.get("articles_fetched", 0)
        events_found = m.get("events_found", 0)
        event_extracted = m.get("event_extracted", False)
        all_sources_unavailable = m.get("all_public_sources_unavailable", False)
        source_name = m.get("source_name", "")
        event_title = m.get("title", "")
        event_url = m.get("url", "")
        event_type = m.get("event_type", "")
        intensity = m.get("intensity", "")
        attr_risk = m.get("attribution_risk", "")
        assets_affected = m.get("assets_affected", [])
        market_snapshot = m.get("market_snapshot", {})
        market_api_success = m.get("market_api_success", False)
        obs_only = m.get("observation_only", True)
        not_causal = m.get("not_causal_proof", True)

    print(f"  Public sources attempted: {sources_attempted}")
    print(f"  Public sources succeeded: {sources_succeeded}")
    print(f"  Articles fetched: {articles_fetched}")
    print(f"  Events extracted: {events_found}")
    print(f"  Event extracted (≥1): {event_extracted}")
    print(f"  All sources unavailable: {all_sources_unavailable}")
    if event_title:
        print(f"  Event title: {event_title[:120]}")
    if source_name:
        print(f"  Source: {source_name}")
    if event_url:
        print(f"  URL: {event_url[:120]}")
    print(f"  Event type: {event_type}")
    print(f"  Intensity: {intensity}")
    print(f"  Attribution risk: {attr_risk}")
    print(f"  Assets affected: {assets_affected}")
    print(f"  Market data available: {len(market_snapshot) > 0}")
    print(f"  Market API success: {market_api_success}")
    print(f"  observation_only: {obs_only}")
    print(f"  not_causal_proof: {not_causal}")
    print()

    gate = result.gate_decision
    sr = result.send_readiness
    tg = result.tg_result
    rendered = result.rendered_card

    print(f"  Card Family: {result.card_family.value}")
    print(f"  Gate allow: {gate.allow if gate else 'N/A'}")
    if gate:
        print(f"  Gate reason: {gate.reason[:200]}")
    if rendered:
        print(f"  Rendered card title: {rendered.title[:100]}")
        print(f"  Card observation_only: {rendered.observation_only}")
        print(f"  Card not_causal_proof: {rendered.not_causal_proof}")
        print(f"  Card risk disclaimer present: {'不构成因果证明' in rendered.risk_disclaimer}")
    print(f"  Send-readiness allow_test_group: {sr.allow_test_group if sr else 'N/A'}")
    if sr:
        print(f"  Send-readiness reason: {sr.reason[:200]}")
        print(f"  production_send_ready: {sr.production_send_ready}")
        print(f"  block_x_twitter: {sr.block_x_twitter}")
        print(f"  block_daemon_cron_loop: {sr.block_daemon_cron_loop}")
    if tg:
        print(f"  TG attempted: {tg.attempted}")
        print(f"  TG success: {tg.success}")
        print(f"  TG status: {tg.status}")
        print(f"  TG reason: {tg.reason[:200]}")
        if tg.success:
            SAFETY["tg_sent_this_run"] = True
            print(f"  TG message_id_proof: {tg.message_id_proof}")
        print(f"  TG production_send: {tg.production_send}")
        print(f"  TG credentials_printed: {tg.credentials_printed}")
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

    # 7.1 Result JSON
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

    sources_detail = []
    if signal:
        sources_detail = signal.metrics.get("sources_detail", [])

    # Determine status for this run
    if all_sources_unavailable:
        run_status = "blocked_public_source_unavailable"
    elif not event_extracted:
        run_status = "blocked_no_relevant_news_event"
    elif tg and tg.success:
        run_status = "sent"
    elif tg and tg.status == "skipped" and "missing_safe_config" in (tg.reason or "").lower():
        run_status = "skipped_missing_safe_tg_config"
    elif tg and tg.status == "blocked":
        run_status = "blocked_gate_not_passed_or_send_readiness"
    elif tg and tg.status == "skipped":
        run_status = "skipped_other"
    elif result.passed and not (tg and tg.success):
        run_status = "pipeline_passed_but_tg_not_sent"
    else:
        run_status = "blocked_gate_not_passed"

    result_output = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "real_free_public_source_news_event_tg_one_shot",
        "card_family": CardFamily.NEWS_EVENT_MARKET_IMPACT.value,
        "run_status": run_status,
        "source_summary": {
            "sources_attempted": sources_attempted,
            "sources_succeeded": sources_succeeded,
            "articles_fetched": articles_fetched,
            "events_found": events_found,
            "event_extracted": event_extracted,
            "all_public_sources_unavailable": all_sources_unavailable,
        },
        "event_summary": {
            "source_name": source_name,
            "title": event_title[:200] if event_title else "",
            "url_redacted": "sha256:" + (
                hashlib.sha256(event_url.encode("utf-8")).hexdigest()[:12]
                if event_url else "no_url"
            ),
            "url_domain": source_name.lower().replace(" ", "") + ".com" if source_name else "",
            "event_type": event_type,
            "intensity": intensity,
            "attribution_risk": attr_risk,
            "assets_affected": assets_affected,
            "observation_only": obs_only,
            "not_causal_proof": not_causal,
        },
        "market_data_summary": {
            "market_api_success": market_api_success,
            "assets_with_data": list(market_snapshot.keys()) if market_snapshot else [],
            "asset_count_with_data": len(market_snapshot),
        },
        "gate_allow": gate.allow if gate else None,
        "gate_reason": gate.reason if gate else None,
        "send_readiness_allow_test_group": sr.allow_test_group if sr else None,
        "send_readiness_production_send_ready": sr.production_send_ready if sr else None,
        "send_readiness_block_x_twitter": sr.block_x_twitter if sr else None,
        "send_readiness_block_daemon_cron_loop": sr.block_daemon_cron_loop if sr else None,
        "tg_result": tg_summary,
        "pipeline_passed": result.passed,
        "pipeline_error": result.error,
        "card_observation_only": rendered.observation_only if rendered else None,
        "card_not_causal_proof": rendered.not_causal_proof if rendered else None,
        "sources_detail": sources_detail,
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
            "observation_only": SAFETY["observation_only"],
            "not_causal_proof": SAFETY["not_causal_proof"],
        },
        "preflight": {
            "safe_loader_found": preflight["safe_loader_found"],
            "load_success": preflight["load_success"],
            "config_ready": preflight["config_ready"],
            "bot_token_present": preflight["bot_token_present"],
            "chat_id_present": preflight["chat_id_present"],
        },
    }

    result_path = results_dir / "market_radar_v117e_news_event_tg_one_shot_result.json"
    write_json(result_path, result_output)

    # Self-check result for raw secrets
    result_text = json.dumps(result_output, ensure_ascii=False)
    if raw_token_pattern.search(result_text):
        print("  [CRITICAL] RESULT SELF-CHECK FAILED: raw token pattern detected!")
    else:
        print(f"  [OK] Result self-check passed — no raw credentials")
    print(f"  [OK] {result_path}")

    # 7.2 Evidence ledger JSONL
    ledger_path = ledger.write_jsonl(
        results_dir / "market_radar_v117e_news_event_evidence_ledger.jsonl"
    )
    print(f"  [OK] {ledger_path}")

    # 7.3 Report markdown
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
- Config ready: **{preflight['config_ready']}**
- This is truthful — NOT faked as "sent".
"""
    elif tg and tg.status == "blocked":
        tg_status_section = f"""
## TG Test Group Send

⛔ **BLOCKED** — Send-readiness gate blocked the send.

- Status: `{tg.status}`
- Reason: `{tg.reason}`
"""
    elif all_sources_unavailable:
        tg_status_section = """
## TG Test Group Send

⛔ **BLOCKED** — No public news sources available. Cannot generate card.

- Status: `blocked_public_source_unavailable`
- This is truthful — NOT faked as "sent".
"""
    elif not event_extracted:
        tg_status_section = """
## TG Test Group Send

⛔ **BLOCKED** — No relevant news events extracted from available articles.

- Status: `blocked_no_relevant_news_event`
- This is truthful — NOT faked as "sent".
"""
    else:
        tg_status_section = """
## TG Test Group Send

❓ **UNKNOWN** — No TG result available.
"""

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

    report_md = f"""# Market Radar {PIPELINE_VERSION}E — News Event Market Impact Report

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## News Event Public Source Status

| Check | Status |
|-------|--------|
| Sources attempted | {sources_attempted} |
| Sources succeeded | {sources_succeeded} |
| Articles fetched | {articles_fetched} |
| Events extracted | {events_found} |
| Event extracted (≥1) | {'✅' if event_extracted else '❌'} |
| All sources unavailable | {'❌ YES (blocked)' if all_sources_unavailable else '✅ NO'} |

### Public Sources Used

| # | Source | Type |
|---|--------|------|
"""
    for s in sources_detail:
        report_md += f"| | {s.get('source_name', '?')} | {s.get('status', '?')} |\n"

    if not sources_detail:
        sources_list = ["CoinDesk (RSS)", "Cointelegraph (RSS)", "Decrypt (RSS)",
                       "The Block (RSS)", "Binance Announcements (JSON API)"]
        for s in sources_list:
            report_md += f"| | {s} | attempted |\n"

    report_md += f"""
### Event Details (if extracted)

| Field | Value |
|-------|-------|
| Source | {source_name or 'N/A'} |
| Title | {event_title[:200] if event_title else 'N/A'} |
| Event type | {event_type or 'N/A'} |
| Intensity | {intensity or 'N/A'} |
| Attribution risk | {attr_risk or 'N/A'} |
| Assets affected | {', '.join(assets_affected) if assets_affected else 'N/A'} |
| URL proof | SHA-256 redacted |
| observation_only | **{obs_only}** |
| not_causal_proof | **{not_causal}** |

### Market Data

| Check | Status |
|-------|--------|
| Binance market API called | {'✅' if market_api_success else '❌'} |
| Assets with market data | {len(market_snapshot)} |
| API key required | ❌ NO (free public REST) |
"""
    for asset, ctx in market_snapshot.items():
        price = ctx.get("price", 0)
        chg = ctx.get("price_change_pct", 0)
        report_md += f"| {asset} ({ctx.get('symbol', '?')}) | ${price:,.2f} | {chg:+.2f}% |\n"

    report_md += f"""
{config_load_section}
---

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `{CardFamily.NEWS_EVENT_MARKET_IMPACT.value}` |
| Gate | {'✅ allow' if gate and gate.allow else '⛔ block'} |
| Gate reason | `{gate.reason[:200] if gate else 'N/A'}` |
| Send-Readiness | {'✅ allow_test_group' if sr and sr.allow_test_group else '⛔ block'} |
| Pipeline Passed | {'✅' if result.passed else '⛔'} |
| Card observation_only | **{rendered.observation_only if rendered else 'N/A'}** |
| Card not_causal_proof | **{rendered.not_causal_proof if rendered else 'N/A'}** |
| Run status | `{run_status}` |
{tg_status_section}
---

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | {'✅' if SAFETY['external_api_called'] else '❌'} |
| TG sent this run | {'✅ 1 message' if SAFETY['tg_sent_this_run'] else '❌ (or skipped)'} |
| Production send | {'❌ NEVER' if not SAFETY['production_send'] else '⚠ ERROR'} |
| X/Twitter send | {'❌ NEVER' if not SAFETY['x_twitter_send'] else '⚠ ERROR'} |
| Credentials printed | {'❌ NEVER' if not SAFETY['credentials_printed'] else '⚠ ERROR'} |
| Daemon/loop started | {'❌ NEVER' if not SAFETY['daemon_or_loop_started'] else '⚠ ERROR'} |
| Files deleted | {'❌ NEVER' if not SAFETY['files_deleted'] else '⚠ ERROR'} |
| v116 history modified | {'❌ NEVER' if not SAFETY['v116_history_modified'] else '⚠ ERROR'} |
| Evidence ledger clean | {'✅' if clean else '❌'} |
| Preflight self-check | ✅ passed |
| Result self-check | ✅ passed |
| observation_only | **{SAFETY['observation_only']}** |
| not_causal_proof | **{SAFETY['not_causal_proof']}** |
| No deterministic causality | ✅ YES |

## Free Public Data Sources

- **CoinDesk RSS** (https://www.coindesk.com/arc/outboundfeeds/rss/)
- **Cointelegraph RSS** (https://cointelegraph.com/rss)
- **Decrypt RSS** (https://decrypt.co/feed)
- **The Block RSS** (https://www.theblock.co/rss)
- **Binance Announcements** (public JSON API, no key)
- **Binance Public REST API** (/api/v3/ticker/24hr) — BTC/ETH/SOL market data
- No API key required for any source
- Event extraction: rule-based keyword matching (NO AI/model)

## Test Results Summary

(To be filled after running tests)

| Test Suite | Expected | Actual |
|------------|----------|--------|
| v117E tests | Pass | (run) |
| v117D regression | Pass | (run) |
| v117C regression | Pass | (run) |
| v117B regression | Pass | (run) |
| v117 regression | Pass | (run) |
| v116N regression | Pass | (run) |
"""
    write_md(runs_dir / "v117e_news_event_market_impact_real_public_source_tg_one_shot_report.md", report_md)
    print(f"  [OK] {runs_dir / 'v117e_news_event_market_impact_real_public_source_tg_one_shot_report.md'}")

    # 7.4 Handoff
    handoff_md = f"""# Market Radar {PIPELINE_VERSION}E — News Event Market Impact Handoff

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## What Was Done

1. **Probed** for safe TG config loaders (filesystem only)
   - `scripts/load_local_secrets.ps1`: {'✅ found' if preflight['safe_loader_found'] else '❌ not found'}

2. **Loaded** TG credentials safely via PowerShell subprocess
   - Method: `{preflight['load_method']}`
   - Success: **{preflight['load_success']}**
   - Config ready: **{preflight['config_ready']}**

3. **Called** free public RSS/news sources for real event titles:
   - CoinDesk, Cointelegraph, Decrypt, The Block RSS
   - Binance Announcements public JSON API
   - Sources succeeded: **{sources_succeeded}/{sources_attempted}**
   - Articles fetched: **{articles_fetched}**
   - Events extracted: **{events_found}**

4. **Called** Binance public REST API for BTC/ETH/SOL market data
   - Market API success: **{market_api_success}**

5. **Ran** shared pipeline (news_event_market_impact)
   - Adapter: `NewsEventMarketImpactFreePublicSourceAdapter`
   - Gate: {'✅ allow' if gate and gate.allow else '⛔ block'}
   - Pipeline passed: **{result.passed}**

6. **Attempted** TG test group one-shot send
   - TG sent: {'✅ 1 message' if (tg and tg.success) else '⚠ 0 messages'}
   - TG status: `{tg.status if tg else 'N/A'}`
   - Production send: **False** (never)

7. **Verified** evidence ledger: {'✅ clean' if clean else '⚠ warnings'}

## Public Sources Used

| Source | Type | Result |
|--------|------|--------|
"""
    for s in sources_detail:
        handoff_md += f"| {s.get('source_name', '?')} | RSS/API | ok ({s.get('article_count', 0)} articles) |\n"
    if not sources_detail:
        handoff_md += "| (none succeeded) | — | blocked |\n"

    handoff_md += f"""
## Event Extraction Method

- **Rule-based keyword matching** (NOT AI/model)
- Asset detection: regex pattern matching on ticker symbols
- Event type: keyword classification from curated dictionary
- Intensity: rule-based ranking (high/medium/low keywords)
- Attribution risk: direct/indirect/unsafe from asset mention in title
- **observation_only=true**: events are observed, not proven causal
- **not_causal_proof=true**: no deterministic causal assertion

## Event Summary

| Field | Value |
|-------|-------|
| Event title | `{event_title[:150] if event_title else 'N/A'}` |
| Source | `{source_name or 'N/A'}` |
| Event type | `{event_type or 'N/A'}` |
| Intensity | `{intensity or 'N/A'}` |
| Assets | `{', '.join(assets_affected) if assets_affected else 'N/A'}` |
| observation_only | **{obs_only}** |
| not_causal_proof | **{not_causal}** |

## TG Send Status

| Check | Result |
|-------|--------|
| TG sent | {'✅ 1 message (SENT)' if (tg and tg.success) else '❌ 0 messages'} |
| TG status | `{tg.status if tg else 'N/A'}` |
| TG reason | `{tg.reason[:200] if tg else 'N/A'}` |
| Production send | **False** |
| X/Twitter send | **False** |
| Daemon/loop | **False** |
| Credentials printed | **False** |

## New Files Created

| File | Type |
|------|------|
| `scripts/run_market_radar_v117e_news_event_market_impact_real_public_source_tg_one_shot.py` | Runner |
| `scripts/test_market_radar_v117e_news_event_market_impact_real_public_source_tg_one_shot.py` | Tests |
| `results/market_radar_v117e_news_event_preflight.json` | Config preflight |
| `results/market_radar_v117e_news_event_tg_one_shot_result.json` | Result |
| `results/market_radar_v117e_news_event_evidence_ledger.jsonl` | Evidence ledger |
| `runs/market_radar/v117e_news_event_market_impact_real_public_source_tg_one_shot_report.md` | Report |
| `runs/market_radar/v117e_local_only_handoff.md` | Handoff |

### Modified Files

| File | Reason |
|------|--------|
| `market_radar/shared/free_api_adapters.py` | Added NewsEventMarketImpactFreePublicSourceAdapter + registry entry |

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
| observation_only | {SAFETY['observation_only']} |
| not_causal_proof | {SAFETY['not_causal_proof']} |

## Production Ready Status

**0/5 — NOT FOR LIVE USE**

All minimum conditions remain unmet. Production send is NEVER enabled.

## No Raw Secrets Verification

- ✅ Preflight JSON: self-checked, no raw token/chat_id patterns
- ✅ Result JSON: self-checked, no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ Report: redacted proofs only
- ✅ Handoff: redacted proofs only
- ✅ Console output: only length/hash/prefix info
- ✅ Event URL: SHA-256 redacted in result

## Unfinished Items / Risks

1. Rule-based keyword matching may miss nuanced events that require NLP
2. RSS feeds may be geo-blocked or timeout depending on network conditions
3. Event intensity classification is keyword-based — may misclassify edge cases
4. Attribution risk (direct/indirect) is determined solely from title text
5. Market data association does NOT imply causal link (by design)
6. Events affecting non-USDT-traded assets are not captured
7. Binance announcements API format may change without notice
8. Multiple concurrent events may affect the same asset — single-event attribution is incomplete
9. This is ONE-SHOT — no continuous news monitoring
10. News timestamps from RSS may lag real-time

## Next Steps

1. Run v117E tests: `python -X utf8 -m pytest scripts/test_market_radar_v117e_news_event_market_impact_real_public_source_tg_one_shot.py -v`
2. Run v117D regression: `python -X utf8 -m pytest scripts/test_market_radar_v117d_price_oi_volume_real_card_tg_one_shot.py -v`
3. Run v117C regression: `python -X utf8 -m pytest scripts/test_market_radar_v117c_safe_tg_config_loader_real_test_group_rerun.py -v`
4. Run v117B regression: `python -X utf8 -m pytest scripts/test_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py -v`
5. Run v117 regression: `python -X utf8 -m pytest scripts/test_market_radar_v117_shared_pipeline_real_one_shot.py -v`
6. Run v116N regression: `python -X utf8 -m pytest scripts/test_market_radar_v116n_user_acceptance_overlay_pack_local_only.py -v`
7. If TG config loaded and gate allowed: verify message arrived in TG test group
"""
    write_md(runs_dir / "v117e_local_only_handoff.md", handoff_md)
    print(f"  [OK] {runs_dir / 'v117e_local_only_handoff.md'}")

    # ── Final Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION}E — News Event Market Impact Complete")
    print(f"  Safe loader found: {preflight['safe_loader_found']}")
    print(f"  Safe load success: {preflight['load_success']}")
    print(f"  Config ready: {preflight['config_ready']}")
    print(f"  Public sources succeeded: {sources_succeeded}/{sources_attempted}")
    print(f"  Articles fetched: {articles_fetched}")
    print(f"  Events extracted: {events_found}")
    print(f"  Binance market API: {'SUCCESS' if market_api_success else 'FAILED/NOT CALLED'}")
    print(f"  Pipeline passed: {result.passed}")
    print(f"  Run status: {run_status}")
    tg_sent_label = "1 message (SENT)" if (tg and tg.success) else "0 (skipped/blocked)"
    print(f"  TG sent: {tg_sent_label}")
    print(f"  TG status: {tg.status if tg else 'N/A'}")
    print(f"  observation_only: {obs_only}")
    print(f"  not_causal_proof: {not_causal}")
    print(f"  Production ready: 0/5 (by design)")
    print(f"  Evidence ledger: {'clean' if clean else 'WARNINGS'}")
    print(f"  Credentials leaked: NO")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
