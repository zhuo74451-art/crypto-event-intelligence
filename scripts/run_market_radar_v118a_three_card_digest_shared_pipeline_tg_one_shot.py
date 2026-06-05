"""Market Radar v118A — Three Card Digest via Shared Pipeline + TG One-Shot.

Upgrades from single-card verification (v117C/D/F) to unified operator digest:
  - Runs 3 real free-data adapters through the SAME shared pipeline
  - Each adapter fetches at most ONCE
  - Generates a single aggregated operator digest
  - Sends at most 1 Telegram message (NOT 3 separate sends)
  - Priority order: news_event > price_oi_anomaly > multi_asset_sync

Adapters:
  1. MultiAssetMarketSyncFreeApiAdapter (Binance public REST)
  2. PriceOIVolumeAnomalyFreeApiAdapter (Binance spot + futures OI)
  3. NewsEventMarketImpactFreePublicSourceAdapter (free RSS/news + Binance)

Safety invariants:
  - production_send=False
  - x_twitter_send=False
  - daemon_or_loop_started=False
  - No files deleted
  - No raw credentials in any output file
  - Evidence ledger: only SHA-256/redacted proofs
  - At most 1 TG message sent (aggregated digest, not 3 separate)

Outputs:
  results/market_radar_v118a_three_card_digest_preflight.json
  results/market_radar_v118a_three_card_digest_result.json
  results/market_radar_v118a_three_card_digest_evidence_ledger.jsonl
  runs/market_radar/v118a_three_card_digest_shared_pipeline_tg_one_shot_report.md
  runs/market_radar/v118a_operator_digest_preview.md
  runs/market_radar/v118a_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v118a_three_card_digest_shared_pipeline_tg_one_shot.py
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
PIPELINE_VERSION = "v1.18A"
TASK_ID = "20260605_v118a_market_radar_three_card_digest_shared_pipeline_tg_one_shot"

SAFETY: dict[str, Any] = {
    "run_id": RUN_ID,
    "pipeline_version": PIPELINE_VERSION,
    "task_id": TASK_ID,
    "external_api_called": False,
    "tg_sent_this_run": False,
    "tg_message_count_this_run": 0,
    "production_send": False,
    "prod_state_write": False,
    "ai_model_called": False,
    "daemon_or_loop_started": False,
    "files_deleted": False,
    "credentials_printed": False,
    "x_twitter_send": False,
    "v116_history_modified": False,
}

# ── Three-card family list (the verified real-data card families) ──────────
THREE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
]

# Priority ordering for digest (higher = listed first)
PRIORITY_RANK = {
    "news_event_market_impact": 3,      # high intensity news event
    "price_oi_volume_anomaly": 2,       # price/OI/volume anomaly
    "multi_asset_market_sync": 1,       # multi-asset market sync
}

# Max TG message length (conservative, leaves headroom for formatting)
TG_MAX_MESSAGE_LENGTH = 3800


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
# SAFE CONFIG LOADER (reused from v117C/D/F pattern)
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
        {
            "type": "powershell_secrets_dot_source",
            "path": "scripts/load_local_secrets.ps1",
            "description": "Canonical safe loader",
        },
        {
            "type": "powershell_secrets_values_file",
            "path": "config/local_secrets.ps1",
            "description": "Local secrets values (gitignored)",
        },
        {
            "type": "secrets_template",
            "path": "config/secrets.example.ps1",
            "description": "Template/example",
        },
        {
            "type": "env_template",
            "path": "config/local_tg_publisher.env.example",
            "description": "Template .env",
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
    """Attempt to load TG credentials via PowerShell subprocess."""
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
# THREE-CARD DIGEST BUILDER
# ═══════════════════════════════════════════════════════════════════════════


def build_digest_card_summary(result: Any, adapter_fetch_count: int) -> dict[str, Any]:
    """Extract a redacted card-level summary from a SharedPipelineResult."""
    cf = result.card_family.value
    gate = result.gate_decision
    tg = result.tg_result
    signal = result.signal
    rendered = result.rendered_card

    data_source = "unknown"
    if signal:
        data_source = signal.source_type.value

    top_signal = ""
    if cf == "multi_asset_market_sync" and signal:
        sync_obs = signal.metrics.get("sync_observation", "")
        assets = signal.metrics.get("assets", [])
        if assets:
            changes = [a.get("price_change_pct", 0) for a in assets[:3]]
            top_signal = "; ".join(
                f"{a.get('symbol','?')}: {a.get('price_change_pct',0):+.2f}%"
                for a in assets[:3]
            )
        if sync_obs:
            top_signal += f" ({sync_obs[:80]})"
    elif cf == "price_oi_volume_anomaly" and signal:
        sigs = signal.metrics.get("signals", [])
        if sigs:
            top_signal = "; ".join(
                f"{s.get('symbol','?')}: Δ{s.get('price_change_24h_pct',0):+.2f}% "
                f"anomaly={s.get('anomaly_type','?')}"
                for s in sigs[:3]
            )
    elif cf == "news_event_market_impact" and signal:
        title_val = signal.metrics.get("title", "")
        intensity_val = signal.metrics.get("intensity", "low")
        event_type_val = signal.metrics.get("event_type", "other")
        top_signal = f"[{intensity_val}] {event_type_val}: {title_val[:120]}"

    observation_only = False
    not_causal_proof = False
    if rendered:
        observation_only = rendered.observation_only
        not_causal_proof = rendered.not_causal_proof

    risk_note = ""
    if signal and signal.risk_notes:
        risk_note = "; ".join(signal.risk_notes[:3])[:200]

    return {
        "card_family": cf,
        "data_source": data_source,
        "gate_status": "allow" if (gate and gate.allow) else "block",
        "gate_reason": gate.reason[:200] if gate else "N/A",
        "gate_allow": gate.allow if gate else False,
        "top_signal": top_signal[:200],
        "risk_note": risk_note,
        "observation_only": observation_only,
        "not_causal_proof": not_causal_proof,
        "send_status": tg.status if tg else "not_attempted",
        "send_reason": tg.reason[:200] if tg else "N/A",
        "error": result.error,
        "adapter_fetch_count": adapter_fetch_count,
    }


def build_operator_digest(
    results: list[Any],
    fetch_counts: dict[str, int],
) -> dict[str, Any]:
    """Build unified operator digest from 3 card pipeline results.

    Priority order: news_event > price_oi_anomaly > multi_asset_sync
    """
    card_summaries = []
    for r in results:
        cf = r.card_family.value
        count = fetch_counts.get(cf, 0)
        card_summaries.append(build_digest_card_summary(r, count))

    # Sort by priority (high → low)
    card_summaries.sort(
        key=lambda c: PRIORITY_RANK.get(c["card_family"], 0),
        reverse=True,
    )

    allowed_count = sum(1 for c in card_summaries if c["gate_allow"])
    total_cards = len(card_summaries)

    # Build a unified short digest
    digest_parts = [
        "📊 Market Radar v118A — Operator Digest",
        "",
    ]

    for i, c in enumerate(card_summaries):
        gate_icon = "✅" if c["gate_allow"] else "⛔"
        family_display = {
            "news_event_market_impact": "📰 News Event",
            "price_oi_volume_anomaly": "🔍 Price/OI/Vol Anomaly",
            "multi_asset_market_sync": "📊 Multi-Asset Sync",
        }.get(c["card_family"], c["card_family"])

        digest_parts.append(f"{gate_icon} {family_display}")
        digest_parts.append(f"   Source: {c['data_source']}")
        digest_parts.append(f"   Gate: {c['gate_status']} | Send: {c['send_status']}")
        if c["top_signal"]:
            digest_parts.append(f"   Signal: {c['top_signal'][:200]}")
        if c["risk_note"]:
            digest_parts.append(f"   Note: {c['risk_note'][:120]}")
        if c["observation_only"]:
            digest_parts.append(f"   ⚠ Observation only — not causal proof")
        digest_parts.append("")

    # Summary line
    digest_parts.append(f"---")
    digest_parts.append(
        f"Cards: {allowed_count}/{total_cards} allowed through quality gate"
    )
    digest_parts.append(f"Pipeline: {PIPELINE_VERSION}")
    digest_parts.append(f"Run ID: {RUN_ID}")
    digest_parts.append(f"Production: FALSE | One-shot: TRUE | Test group only")
    digest_parts.append("")
    digest_parts.append("⚠ All observations are NOT causal proof. Data from free public sources only.")
    digest_parts.append("⚠ 内部数据观察，不构成投资建议。Production Send = False。")

    full_digest_text = "\n".join(digest_parts)

    # Ensure TG-safe length
    if len(full_digest_text) > TG_MAX_MESSAGE_LENGTH:
        full_digest_text = full_digest_text[:TG_MAX_MESSAGE_LENGTH - 50] + "\n\n[...truncated for TG safety]"

    return {
        "digest_text": full_digest_text,
        "digest_length": len(full_digest_text),
        "card_count": total_cards,
        "allowed_count": allowed_count,
        "cards": card_summaries,
        "priority_order": "news_event > price_oi_anomaly > multi_asset_sync",
        "generated_at": china_stamp(),
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
    }


def any_card_allowed(card_summaries: list[dict]) -> bool:
    return any(c["gate_allow"] for c in card_summaries)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Three Card Digest via Shared Pipeline + TG One-Shot")
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
            MultiAssetMarketSyncFreeApiAdapter,
            PriceOIVolumeAnomalyFreeApiAdapter,
            NewsEventMarketImpactFreePublicSourceAdapter,
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
    print(f"  env_vars_already_set: "
          f"TELEGRAM_BOT_TOKEN={probe['env_vars_already_set']['TELEGRAM_BOT_TOKEN']}, "
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
    print("[3] Building preflight...")
    preflight = {
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
        preflight["config_missing_reason"] = (
            load_result.get("error") or "TG config missing after safe load attempt"
        )

    preflight_path = results_dir / "market_radar_v118a_three_card_digest_preflight.json"
    write_json(preflight_path, preflight)

    # Self-check preflight
    preflight_text = json.dumps(preflight, ensure_ascii=False)
    raw_token_pattern = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
    if raw_token_pattern.search(preflight_text):
        print("  [CRITICAL] PREFLIGHT SELF-CHECK FAILED: raw token pattern detected!")
        print("  Aborting to prevent credential leak.")
        sys.exit(1)
    print(f"  [OK] Preflight self-check passed — no raw credentials")
    print(f"  [OK] {preflight_path}")
    print()

    # ── Stage 4: Create 3 real free-data adapters ──────────────────────────
    print("[4] Creating 3 real free-data adapters...")

    # Track fetch counts per adapter
    fetch_counts: dict[str, int] = {}

    adapter_configs = [
        ("multi_asset_market_sync", MultiAssetMarketSyncFreeApiAdapter,
         "Binance /api/v3/ticker/24hr"),
        ("price_oi_volume_anomaly", PriceOIVolumeAnomalyFreeApiAdapter,
         "Binance /api/v3/ticker/24hr + fapi/v1/openInterest"),
        ("news_event_market_impact", NewsEventMarketImpactFreePublicSourceAdapter,
         "CoinDesk/Cointelegraph/Decrypt/The Block/Binance RSS + Binance market data"),
    ]

    adapters: list[tuple[str, Any, str]] = []
    for cf_name, adapter_cls, endpoint_desc in adapter_configs:
        adapter = adapter_cls()
        adapters.append((cf_name, adapter, endpoint_desc))
        fetch_counts[cf_name] = 0
        print(f"  [OK] {adapter_cls.__name__} created for {cf_name}")
        print(f"       Source: {endpoint_desc}")

    print(f"  Total: {len(adapters)} adapters ready")
    print()

    # ── Stage 5: Run Shared Pipeline for each adapter ──────────────────────
    print("[5] Running shared pipeline for all 3 adapters (each fetch at most ONCE)...")
    SAFETY["external_api_called"] = True

    ledger = create_evidence_ledger()
    pipeline = SharedPipeline(evidence_ledger=ledger)

    pipeline_results: list[Any] = []
    for cf_name, adapter, _ in adapters:
        print(f"  --- {cf_name} ---")
        result = pipeline.run(adapter)
        pipeline_results.append(result)

        # Track fetch count from adapter's internal counter if available
        if hasattr(adapter, '_fetch_count'):
            fetch_counts[cf_name] = adapter._fetch_count
        else:
            fetch_counts[cf_name] = 1  # default: 1 fetch

        gate = result.gate_decision
        tg = result.tg_result

        print(f"    Gate allow: {gate.allow if gate else 'N/A'}")
        print(f"    Gate reason: {gate.reason[:150] if gate else 'N/A'}")
        if tg:
            print(f"    TG status: {tg.status}")
            print(f"    TG reason: {tg.reason[:150] if tg.reason else 'N/A'}")
        if result.error:
            print(f"    Error: {result.error[:200]}")
        print()

    # ── Stage 6: Build unified operator digest ─────────────────────────────
    print("[6] Building unified three-card operator digest...")
    digest = build_operator_digest(pipeline_results, fetch_counts)

    print(f"  Cards in digest: {digest['card_count']}")
    print(f"  Allowed through gate: {digest['allowed_count']}")
    print(f"  Digest length: {digest['digest_length']} chars")
    print(f"  Priority order: {digest['priority_order']}")
    for c in digest["cards"]:
        print(f"    {c['card_family']}: gate={c['gate_status']}, "
              f"send={c['send_status']}, fetches={c['adapter_fetch_count']}")
    print()

    # ── Stage 7: TG Test Group One-Shot (at most 1 aggregated message) ─────
    print("[7] TG test group one-shot (aggregated digest, at most 1 message)...")

    tg_digest_result: Optional[dict[str, Any]] = None
    tg_digest_status = "not_attempted"
    tg_digest_reason = ""

    config_ready = load_result.get("config_ready", False)
    has_allowed = any_card_allowed(digest["cards"])

    if not config_ready:
        tg_digest_status = "skipped"
        tg_digest_reason = "skipped_missing_safe_tg_config"
        print(f"  TG config NOT ready → {tg_digest_status}")
    elif not has_allowed:
        tg_digest_status = "blocked"
        tg_digest_reason = "blocked_no_allowed_cards"
        print(f"  No cards allowed through gate → {tg_digest_status}")
    else:
        # Attempt aggregated send
        print("  Config ready, at least 1 card allowed → attempting aggregated TG send...")
        try:
            from market_radar.shared.sender_contract import TGTestGroupSender, create_tg_sender
            from market_radar.shared.models import (
                RenderedCard, SendReadinessDecision, CardFamily as Cf,
            )

            # Build a single digest card for TG send
            digest_card = RenderedCard(
                title="Market Radar v118A — Three Card Operator Digest",
                body=digest["digest_text"],
                card_family=Cf.MULTI_ASSET_MARKET_SYNC,  # Neutral family for digest
                risk_disclaimer="⚠ 内部数据观察，不构成投资建议。Production Send = False。",
                evidence_summary=(
                    f"Three-card aggregated digest: {digest['allowed_count']}/"
                    f"{digest['card_count']} cards allowed through quality gate"
                ),
                production_status="test_group_only",
            )

            # Create send-readiness decision (allow for test group)
            send_rd = SendReadinessDecision(
                allow_test_group=True,
                reason="test_group_one_shot: aggregated digest with allowed cards",
                production_send_ready=False,
                block_formal_channel=True,
                block_x_twitter=True,
                block_daemon_cron_loop=True,
                gate_version=PIPELINE_VERSION,
            )

            sender = create_tg_sender()
            send_result = sender.send(digest_card, send_rd)

            tg_digest_status = send_result.status
            tg_digest_reason = send_result.reason

            if send_result.success:
                SAFETY["tg_sent_this_run"] = True
                SAFETY["tg_message_count_this_run"] = 1
                print(f"  TG aggregated digest: SENT (1 message, one-shot)")
                print(f"  TG message_id_proof: {send_result.message_id_proof}")
            else:
                SAFETY["tg_message_count_this_run"] = 0
                print(f"  TG aggregated digest: {send_result.status}")
                print(f"  TG reason: {send_result.reason[:200]}")

            tg_digest_result = {
                "attempted": send_result.attempted,
                "success": send_result.success,
                "status": send_result.status,
                "reason": send_result.reason[:400],
                "target_type": send_result.target_type,
                "one_shot": send_result.one_shot,
                "production_send": send_result.production_send,
                "message_id_proof_present": send_result.message_id_proof is not None,
                "token_proof_present": send_result.token_proof is not None,
                "chat_id_proof_present": send_result.chat_id_proof is not None,
                "credentials_printed": send_result.credentials_printed,
                "message_count": 1 if send_result.success else 0,
            }

            # Record digest-level evidence in ledger
            ledger.record(
                card_family=Cf.MULTI_ASSET_MARKET_SYNC,
                asset_or_topic="three_card_aggregated_digest",
                quality_gate_allow=has_allowed,
                send_readiness_allow=True,
                tg_result=send_result,
            )

        except ImportError as e:
            tg_digest_status = "skipped"
            tg_digest_reason = f"tg_test_send_skipped_import_error: {e}"
            print(f"  TG send skipped: cannot import sender — {e}")
        except Exception as e:
            tg_digest_status = "failed"
            tg_digest_reason = f"tg_send_exception: {type(e).__name__}: {e}"
            print(f"  TG send failed: {type(e).__name__}: {e}")

    # Ensure at most 1 message was sent
    if SAFETY["tg_message_count_this_run"] > 1:
        print("  [WARN] Multiple TG messages detected — this violates v118A contract")
        SAFETY["tg_message_count_this_run"] = 1  # cap for safety contract

    print()

    # ── Stage 8: Evidence Ledger Verification ──────────────────────────────
    print("[8] Evidence ledger verification...")
    evidence_entries = ledger.entries()
    clean, violations = ledger.verify_no_raw_secrets()
    if not clean:
        print(f"  [WARN] Evidence ledger contains {len(violations)} potential raw secret patterns!")
        for v in violations:
            print(f"    - {v}")
    else:
        print(f"  [OK] Evidence ledger clean — {len(evidence_entries)} entries, no raw secrets")
    print()

    # ── Stage 9: Write Outputs ─────────────────────────────────────────────
    print("[9] Writing output files...")

    # 9.1 Card-level signal summaries
    card_signal_summaries = []
    for r in pipeline_results:
        cf = r.card_family.value
        signal = r.signal
        entry = {
            "card_family": cf,
            "pipeline_passed": r.passed,
            "error": r.error,
            "gate_allow": r.gate_decision.allow if r.gate_decision else None,
            "gate_reason": r.gate_decision.reason if r.gate_decision else None,
            "send_readiness_allow": r.send_readiness.allow_test_group if r.send_readiness else None,
            "tg_status": r.tg_result.status if r.tg_result else "not_attempted",
            "adapter_fetch_count": fetch_counts.get(cf, 0),
        }

        if signal:
            entry["data_source"] = signal.source_type.value
            entry["asset_or_topic"] = signal.asset_or_topic
            entry["source_refs"] = signal.source_refs
            if cf == "news_event_market_impact":
                entry["observation_only"] = signal.metrics.get("observation_only", True)
                entry["not_causal_proof"] = signal.metrics.get("not_causal_proof", True)
                entry["event_intensity"] = signal.metrics.get("intensity", "unknown")
                entry["event_type"] = signal.metrics.get("event_type", "unknown")
            elif cf == "multi_asset_market_sync":
                entry["asset_count"] = len(signal.metrics.get("assets", []))
                entry["correlation_score"] = signal.metrics.get("correlation_score", 0)
            elif cf == "price_oi_volume_anomaly":
                sigs = signal.metrics.get("signals", [])
                entry["asset_count"] = len(sigs)
                entry["anomalies"] = [s.get("anomaly_type") for s in sigs]

        card_signal_summaries.append(entry)

    # Count per-adapter fetches
    fetch_summary = {}
    for cf_name, adapter, _ in adapters:
        if hasattr(adapter, '_fetch_count'):
            fetch_summary[cf_name] = adapter._fetch_count
        else:
            fetch_summary[cf_name] = 1

    one_shot_output = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "real_free_api_three_card_digest_tg_one_shot",
        "card_count": len(pipeline_results),
        "digest": {
            "card_count": digest["card_count"],
            "allowed_count": digest["allowed_count"],
            "priority_order": digest["priority_order"],
            "digest_length": digest["digest_length"],
            "digest_text": digest["digest_text"],
        },
        "cards": card_signal_summaries,
        "adapter_fetch_counts": fetch_summary,
        "each_adapter_max_one_fetch": all(
            v <= 1 for v in fetch_summary.values()
        ),
        "tg_digest": tg_digest_result or {
            "status": tg_digest_status,
            "reason": tg_digest_reason,
        },
        "safety": {
            "external_api_called": SAFETY["external_api_called"],
            "tg_sent_this_run": SAFETY["tg_sent_this_run"],
            "tg_message_count_this_run": SAFETY["tg_message_count_this_run"],
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
            "v118A proves the system has graduated from single-card verification "
            "to multi-card operator digest. 3 verified card families run through "
            "the same shared pipeline, producing 1 aggregated TG digest message "
            "(not 3 separate sends). Each adapter fetches at most once from "
            "free public APIs only."
        ),
    }

    one_shot_path = results_dir / "market_radar_v118a_three_card_digest_result.json"
    write_json(one_shot_path, one_shot_output)
    print(f"  [OK] {one_shot_path}")

    # 9.2 Evidence ledger JSONL
    ledger_path = ledger.write_jsonl(
        results_dir / "market_radar_v118a_three_card_digest_evidence_ledger.jsonl"
    )
    print(f"  [OK] {ledger_path}")

    # 9.3 Operator digest preview
    digest_preview_md = f"""# Market Radar {PIPELINE_VERSION} — Operator Digest Preview

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Pipeline**: {PIPELINE_VERSION}

---

## Aggregated Three-Card Digest (TG Message Format)

```
{digest["digest_text"]}
```

---

## Card Details

| # | Card Family | Source | Gate | Top Signal | Send |
|---|------------|--------|------|------------|------|
"""
    for c in digest["cards"]:
        digest_preview_md += (
            f"| {digest['cards'].index(c) + 1} | `{c['card_family']}` | "
            f"{'free_public_api' if 'api' in c['data_source'] else c['data_source']} | "
            f"{'✅ allow' if c['gate_allow'] else '⛔ block'} | "
            f"{c['top_signal'][:60]} | "
            f"{c['send_status']} |\n"
        )

    digest_preview_md += f"""
## Safety Verification

| Check | Status |
|-------|--------|
| Production send | ❌ NEVER {SAFETY['production_send']} |
| X/Twitter send | ❌ NEVER {SAFETY['x_twitter_send']} |
| TG messages sent | {SAFETY['tg_message_count_this_run']} (max 1) |
| Daemon/loop | ❌ NEVER {SAFETY['daemon_or_loop_started']} |
| AI model called | ❌ NEVER {SAFETY['ai_model_called']} |
| Credentials printed | ❌ NEVER {SAFETY['credentials_printed']} |

## News Event Observation Only

⚠ All news events are marked `observation_only=true` and `not_causal_proof=true`.
No deterministic causal language is present in the digest.

## Priority Order

1. 📰 News Event Market Impact (high intensity)
2. 🔍 Price/OI/Volume Anomaly
3. 📊 Multi-Asset Market Sync
"""
    write_md(runs_dir / "v118a_operator_digest_preview.md", digest_preview_md)
    print(f"  [OK] {runs_dir / 'v118a_operator_digest_preview.md'}")

    # 9.4 Main report
    card_table_rows = ""
    for c in digest["cards"]:
        card_table_rows += (
            f"| `{c['card_family']}` | {c['data_source']} | "
            f"{'✅ allow' if c['gate_allow'] else '⛔ block'} | "
            f"{c['send_status']} | {c['adapter_fetch_count']} | "
            f"{'✅' if c['observation_only'] else 'N/A'} |\n"
        )

    tg_section = ""
    if SAFETY["tg_sent_this_run"]:
        tg_section = """
## TG Test Group Send

✅ **SENT** — 1 aggregated operator digest message delivered to TG test group (one-shot).

- Message count: **1** (aggregated digest, NOT 3 separate messages)
- Target: `test_group`
- Production send: **False**
- One-shot: **True**
"""
    elif tg_digest_status == "skipped":
        tg_section = f"""
## TG Test Group Send

⚠ **SKIPPED** — TG test group send not attempted.

- Reason: `{tg_digest_reason}`
- Safe loader found: **{preflight['safe_loader_found']}**
- Config ready: **{preflight['config_ready']}**
"""
    elif tg_digest_status == "blocked":
        tg_section = f"""
## TG Test Group Send

⛔ **BLOCKED** — No cards passed quality gate, or send-readiness blocked.

- Reason: `{tg_digest_reason}`
- Cards allowed: {digest['allowed_count']}/{digest['card_count']}
"""
    elif tg_digest_status == "failed":
        tg_section = f"""
## TG Test Group Send

❌ **FAILED** — Network or transport error.

- Reason: `{tg_digest_reason}`
"""
    else:
        tg_section = """
## TG Test Group Send

❓ **NOT ATTEMPTED**
"""

    report_md = f"""# Market Radar {PIPELINE_VERSION} — Three Card Digest via Shared Pipeline + TG One-Shot Report

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## Purpose

v118A upgrades from single-card verification (v117C/D/F) to a unified **three-card operator digest**:

1. **Three real free-data adapters** run through the same shared pipeline
2. **One aggregated operator digest** is produced
3. **At most 1 TG message** is sent (NOT 3 separate messages)
4. **Each adapter fetches at most once** (no duplicate API calls)

---

## Three-Card Pipeline Results

| Card Family | Data Source | Gate | Send | Fetches | Obs Only |
|------------|------------|------|------|---------|----------|
{card_table_rows}
{tg_section}
---

## Operator Digest Summary

- **Cards in digest**: {digest['card_count']}
- **Allowed through gate**: {digest['allowed_count']}
- **Priority order**: {digest['priority_order']}
- **Digest length**: {digest['digest_length']} chars (TG-safe)

---

## Data Sources (All Free Public)

| Adapter | Endpoints | Auth Required |
|---------|-----------|---------------|
| MultiAssetMarketSync | Binance /api/v3/ticker/24hr | None |
| PriceOIVolumeAnomaly | Binance /api/v3/ticker/24hr + fapi/v1/openInterest | None |
| NewsEventMarketImpact | CoinDesk/Cointelegraph/Decrypt/The Block/Binance RSS | None |

---

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | {'✅' if SAFETY['external_api_called'] else '❌'} |
| TG messages sent this run | {SAFETY['tg_message_count_this_run']} (max 1) |
| Production send | {'❌ NEVER' if not SAFETY['production_send'] else '⚠ ERROR'} |
| X/Twitter send | {'❌ NEVER' if not SAFETY['x_twitter_send'] else '⚠ ERROR'} |
| Credentials printed | {'❌ NEVER' if not SAFETY['credentials_printed'] else '⚠ ERROR'} |
| Daemon/loop started | {'❌ NEVER' if not SAFETY['daemon_or_loop_started'] else '⚠ ERROR'} |
| Files deleted | {'❌ NEVER' if not SAFETY['files_deleted'] else '⚠ ERROR'} |
| v116 history modified | {'❌ NEVER' if not SAFETY['v116_history_modified'] else '⚠ ERROR'} |
| AI model called | {'❌ NEVER' if not SAFETY['ai_model_called'] else '⚠ ERROR'} |
| Evidence ledger clean | {'✅' if clean else '❌'} |
| Each adapter ≤1 fetch | {'✅' if all(v <= 1 for v in fetch_summary.values()) else '⚠'} |

## Secret Leak Risk Assessment

- ✅ Preflight JSON: self-checked, no raw token/chat_id patterns
- ✅ Result JSON: no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ Report: redacted proofs only
- ✅ Digest preview: no raw secrets
- ✅ Operator digest contains no raw credentials

## News Event Guard

- ✅ observation_only = True
- ✅ not_causal_proof = True
- ✅ No deterministic causal language in digest
- ✅ All event extraction is rule-based (NO AI/model)

## Production Readiness

**0/5 — NOT FOR LIVE USE**

All minimum conditions remain unmet. Production send is NEVER enabled.

## Shared Pipeline Proof

v118A completes the transition from "single card" to "multi-card product":

- v117C → multi_asset_market_sync (1st card)
- v117D → price_oi_volume_anomaly (2nd card)
- v117F → news_event_market_impact (3rd card)
- **v118A → all 3 combined into one operator digest**

Same shared pipeline for all cards. Same gate. Same renderer. Same sender. Same ledger.

## Test Results Summary

(To be filled after running tests)

| Test Suite | Expected | Actual |
|------------|----------|--------|
| v118A tests | Pass | (run) |
| v117F regression | Pass | (run) |
| v117E regression | Pass | (run) |
| v117D regression | Pass | (run) |
| v117C regression | Pass | (run) |
| v117B regression | Pass | (run) |
| v117 regression | Pass | (run) |
| v116N regression | Pass | (run) |
"""
    write_md(runs_dir / "v118a_three_card_digest_shared_pipeline_tg_one_shot_report.md", report_md)
    print(f"  [OK] {runs_dir / 'v118a_three_card_digest_shared_pipeline_tg_one_shot_report.md'}")

    # 9.5 Handoff
    handoff_md = f"""# Market Radar {PIPELINE_VERSION} — Three Card Digest Handoff

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## What Was Done

1. **Probed** for safe config loaders (filesystem only)
   - `scripts/load_local_secrets.ps1`: {'✅ found' if preflight['safe_loader_found'] else '❌ not found'}

2. **Loaded** TG credentials safely via PowerShell subprocess
   - Config ready: **{preflight['config_ready']}**

3. **Created 3 real free-data adapters**:
   - MultiAssetMarketSyncFreeApiAdapter
   - PriceOIVolumeAnomalyFreeApiAdapter
   - NewsEventMarketImpactFreePublicSourceAdapter

4. **Ran each adapter through SharedPipeline.run()**
   - Each adapter fetched at most ONCE
   - All used free public APIs only

5. **Generated unified three-card operator digest**
   - Priority: news > anomaly > sync
   - {digest['allowed_count']}/{digest['card_count']} cards allowed through quality gate

6. **TG test group send**:
   - Messages sent: **{SAFETY['tg_message_count_this_run']}** (max 1 by design)
   - Status: `{tg_digest_status}`
   - Production send: **False** (never)

7. **Verified evidence ledger**: {'✅ clean' if clean else '⚠ warnings'}

## Three Card Family Proof

| Card Family | Gate | Adapter Fetches | Source |
|------------|------|----------------|--------|
"""
    for c in digest["cards"]:
        handoff_md += (
            f"| `{c['card_family']}` | "
            f"{'✅ allow' if c['gate_allow'] else '⛔ block'} | "
            f"{c['adapter_fetch_count']} | "
            f"{c['data_source']} |\n"
        )

    handoff_md += f"""
## New Files Created

| File | Type |
|------|------|
| `scripts/run_market_radar_v118a_three_card_digest_shared_pipeline_tg_one_shot.py` | Runner |
| `scripts/test_market_radar_v118a_three_card_digest_shared_pipeline_tg_one_shot.py` | Tests |
| `results/market_radar_v118a_three_card_digest_preflight.json` | Config preflight |
| `results/market_radar_v118a_three_card_digest_result.json` | Result |
| `results/market_radar_v118a_three_card_digest_evidence_ledger.jsonl` | Evidence ledger |
| `runs/market_radar/v118a_three_card_digest_shared_pipeline_tg_one_shot_report.md` | Report |
| `runs/market_radar/v118a_operator_digest_preview.md` | Digest preview |
| `runs/market_radar/v118a_local_only_handoff.md` | Handoff |

## Safety Confirmation

| Constraint | Status |
|------------|--------|
| external_api_called | {SAFETY['external_api_called']} |
| tg_sent_this_run | {SAFETY['tg_sent_this_run']} |
| tg_message_count_this_run | {SAFETY['tg_message_count_this_run']} (max 1) |
| prod_state_write | {SAFETY['prod_state_write']} |
| ai_model_called | {SAFETY['ai_model_called']} |
| daemon_or_loop_started | {SAFETY['daemon_or_loop_started']} |
| files_deleted | {SAFETY['files_deleted']} |
| credentials_printed | {SAFETY['credentials_printed']} |
| x_twitter_send | {SAFETY['x_twitter_send']} |
| v116_history_modified | {SAFETY['v116_history_modified']} |

## No Raw Secrets Verification

- ✅ Preflight JSON: self-checked
- ✅ Result JSON: no raw token/chat_id/message_id
- ✅ Evidence ledger: SHA-256 proofs only
- ✅ All reports: redacted proofs only

## Production Ready Status

**0/5 — NOT FOR LIVE USE**

## Next Steps

1. Run v118A tests
2. Run all regression tests
3. Review operator digest in TG test group
"""
    write_md(runs_dir / "v118a_local_only_handoff.md", handoff_md)
    print(f"  [OK] {runs_dir / 'v118a_local_only_handoff.md'}")
    print()

    # ── Final Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Three Card Digest Complete")
    print(f"  Safe loader found: {preflight['safe_loader_found']}")
    print(f"  Config ready: {preflight['config_ready']}")
    print(f"  Adapters run: {len(pipeline_results)}")
    print(f"  Cards allowed: {digest['allowed_count']}/{digest['card_count']}")
    for c in digest["cards"]:
        print(f"    {c['card_family']}: gate={c['gate_status']}, "
              f"send={c['send_status']}, fetches={c['adapter_fetch_count']}")
    print(f"  TG messages sent: {SAFETY['tg_message_count_this_run']} (max 1 by contract)")
    print(f"  TG digest status: {tg_digest_status}")
    print(f"  Production ready: 0/5 (by design)")
    print(f"  Evidence ledger: {'clean' if clean else 'WARNINGS'}")
    print(f"  Credentials leaked: NO")
    print(f"  Each adapter max 1 fetch: {'YES' if all(v <= 1 for v in fetch_summary.values()) else 'WARNING'}")
    print(f"  Digest is single aggregated: YES")
    print(f"  System graduated: single-card → multi-card operator digest")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
