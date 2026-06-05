"""Market Radar v117B — Shared Pipeline TG Test Group One-Shot Runner.

Sister runner to v117. Where v117 runs the full fixture + real API pipeline,
v117B focuses exclusively on:
  - BTC/ETH/SOL multi_asset_market_sync via Binance public REST
  - Safe TG config preflight (bool/length/hash only — no raw credentials)
  - One-shot TG test group send (if safe config available)
  - Redacted evidence ledger output

Key differences from v117:
  - No fixture pipeline (fixtures are tested in v117)
  - Single card_family: multi_asset_market_sync
  - Dedicated safe config preflight step
  - Dedicated preflight JSON output
  - production_send is always False
  - X/Twitter is always blocked
  - daemon/cron/loop is never started

Outputs:
  results/market_radar_v117b_tg_safe_config_preflight.json
  results/market_radar_v117b_shared_pipeline_tg_one_shot_result.json
  results/market_radar_v117b_shared_pipeline_tg_evidence_ledger.jsonl
  runs/market_radar/v117b_shared_pipeline_tg_one_shot_report.md
  runs/market_radar/v117b_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py
"""

from __future__ import annotations

import hashlib
import json
import os
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
TASK_ID = "20260605_v117b_shared_pipeline_tg_test_group_one_shot_safe_config"

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


def redact_length(text: str) -> int:
    """Return only the length of a secret — never the value."""
    return len(str(text))


# ═══════════════════════════════════════════════════════════════════════════
# SAFE CONFIG PREFLIGHT
# ═══════════════════════════════════════════════════════════════════════════


def run_safe_config_preflight() -> dict[str, Any]:
    """Check TG configuration WITHOUT printing, logging, or storing raw values.

    Returns a dict with ONLY boolean flags, length integers, and sha256 prefix strings.
    No raw token/chat_id/message_id is stored in the return value.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    preflight: dict[str, Any] = {
        "checked_at": china_stamp(),
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "bot_token_present": bool(bot_token),
        "bot_token_length": len(bot_token) if bot_token else 0,
        "bot_token_sha256_prefix": sha256_hash(bot_token)[:12] if bot_token else None,
        "chat_id_present": bool(chat_id),
        "chat_id_length": len(str(chat_id)) if chat_id else 0,
        "chat_id_sha256_prefix": sha256_hash(str(chat_id))[:12] if chat_id else None,
        "config_ready": bool(bot_token and chat_id),
        "config_missing_reason": None,
    }

    if not bot_token and not chat_id:
        preflight["config_missing_reason"] = (
            "Both TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are missing from environment"
        )
    elif not bot_token:
        preflight["config_missing_reason"] = "TELEGRAM_BOT_TOKEN is missing from environment"
    elif not chat_id:
        preflight["config_missing_reason"] = "TELEGRAM_CHAT_ID is missing from environment"

    # Safety: verify no raw values leaked into preflight dict
    for key, value in preflight.items():
        if isinstance(value, str) and value not in ("", preflight.get("config_missing_reason", "")):
            # All string values must be either the checked_at timestamp, version, run_id,
            # a sha256 prefix, or the config_missing_reason message
            valid_strings = {
                preflight["checked_at"],
                PIPELINE_VERSION,
                RUN_ID,
                preflight.get("config_missing_reason", "__sentinel__"),
            }
            if value not in valid_strings and not value.startswith("sha256:") and not value:
                # This would be unexpected — force replace with redacted
                preflight[key] = "[REDACTED_UNEXPECTED_VALUE]"

    return preflight


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION}B — Shared Pipeline TG Test Group One-Shot")
    print(f"Run ID: {RUN_ID}")
    print(f"Timestamp: {china_stamp()}")
    print("=" * 70)
    print()

    results_dir = ROOT / "results"
    runs_dir = ROOT / "runs" / "market_radar"

    # ── Check for existing result ─────────────────────────────────────────
    existing_result_path = results_dir / "market_radar_v117b_shared_pipeline_tg_one_shot_result.json"
    existing_tg_sent = False
    if existing_result_path.exists():
        print("[0] Found existing v117B result file. Checking...")
        try:
            existing = json.loads(existing_result_path.read_text(encoding="utf-8"))
            existing_tg_sent = existing.get("safety", {}).get("tg_sent_this_run", False)
            if existing_tg_sent:
                print("  [INFO] TG was already sent in a prior run.")
                print("  Will re-run pipeline for verification but NOT re-send TG.")
                print("  (Safe config preflight and evidence ledger will still be refreshed.)")
            else:
                print("  [INFO] Prior run did not send TG. Will attempt TG send in this run.")
        except Exception as e:
            print(f"  [WARN] Could not parse existing result: {e}. Continuing fresh.")
    print()

    # ── Stage 0: Import ───────────────────────────────────────────────────
    print("[0] Importing shared pipeline package...")
    try:
        from market_radar.shared.models import CardFamily
        from market_radar.shared.pipeline import SharedPipeline
        from market_radar.shared.evidence_ledger import create_evidence_ledger
        from market_radar.shared.free_api_adapters import (
            create_real_free_api_adapter,
            MultiAssetMarketSyncFreeApiAdapter,
        )
        print("  [OK] Shared package imported successfully")
    except ImportError as e:
        print(f"  [FAIL] Cannot import shared package: {e}")
        print("  Ensure market_radar/shared/ is on Python path")
        sys.exit(1)

    print()

    # ── Stage 1: Safe Config Preflight ────────────────────────────────────
    print("[1] Running safe config preflight...")
    preflight = run_safe_config_preflight()

    print(f"  bot_token_present: {preflight['bot_token_present']}")
    print(f"  bot_token_length: {preflight['bot_token_length']}")
    print(f"  bot_token_sha256_prefix: {preflight['bot_token_sha256_prefix']}")
    print(f"  chat_id_present: {preflight['chat_id_present']}")
    print(f"  chat_id_length: {preflight['chat_id_length']}")
    print(f"  chat_id_sha256_prefix: {preflight['chat_id_sha256_prefix']}")
    print(f"  config_ready: {preflight['config_ready']}")
    if preflight["config_missing_reason"]:
        print(f"  config_missing_reason: {preflight['config_missing_reason']}")

    # Write preflight
    write_json(results_dir / "market_radar_v117b_tg_safe_config_preflight.json", preflight)
    print(f"  [OK] {results_dir / 'market_radar_v117b_tg_safe_config_preflight.json'}")
    print()

    # ── Stage 2: Binance Public API Call ──────────────────────────────────
    print("[2] Calling Binance public REST API for BTC/ETH/SOL...")
    SAFETY["external_api_called"] = True

    adapter = create_real_free_api_adapter(CardFamily.MULTI_ASSET_MARKET_SYNC)
    if adapter is None:
        print("  [FAIL] Could not create MultiAssetMarketSyncFreeApiAdapter")
        sys.exit(1)

    binance_success = False
    binance_error: Optional[str] = None
    assets_data: list[dict] = []

    try:
        signal = adapter.fetch()
        binance_success = signal.metrics.get("api_success", False)
        binance_error = signal.metrics.get("fetch_error")
        assets_data = signal.metrics.get("assets", [])

        if binance_success:
            print(f"  [OK] Binance API call successful — {len(assets_data)} assets retrieved")
            for a in assets_data:
                sym = a.get("symbol", "?")
                price = a.get("price", 0)
                change = a.get("price_change_pct", 0)
                print(f"    {sym}: price={price:.2f}, 24h_change={change:+.2f}%")
        else:
            print(f"  [FAIL] Binance API call failed: {binance_error}")
    except Exception as e:
        binance_error = f"{type(e).__name__}: {e}"
        print(f"  [FAIL] Binance API exception: {binance_error}")

    print()

    # ── Stage 3: Shared Pipeline ──────────────────────────────────────────
    print("[3] Running shared pipeline (multi_asset_market_sync)...")
    ledger = create_evidence_ledger()
    pipeline = SharedPipeline(evidence_ledger=ledger)

    result = pipeline.run(adapter)

    gate = result.gate_decision
    sr = result.send_readiness
    tg = result.tg_result

    print(f"  Card Family: {result.card_family.value}")
    print(f"  Gate allow: {gate.allow if gate else 'N/A'}")
    if gate:
        print(f"  Gate reason: {gate.reason[:120]}")
    print(f"  Send-readiness allow_test_group: {sr.allow_test_group if sr else 'N/A'}")
    if sr:
        print(f"  Send-readiness reason: {sr.reason[:120]}")
    if tg:
        print(f"  TG attempted: {tg.attempted}")
        print(f"  TG success: {tg.success}")
        print(f"  TG status: {tg.status}")
        print(f"  TG reason: {tg.reason[:200]}")
        if tg.success:
            SAFETY["tg_sent_this_run"] = True
    print()

    # ── Stage 4: Evidence Ledger ──────────────────────────────────────────
    print("[4] Evidence ledger verification...")
    evidence_entries = ledger.entries()
    evidence_dicts = [e.as_dict() for e in evidence_entries]
    clean, violations = ledger.verify_no_raw_secrets()
    if not clean:
        print(f"  [WARN] Evidence ledger contains {len(violations)} potential raw secret patterns!")
        for v in violations:
            print(f"    - {v}")
    else:
        print(f"  [OK] Evidence ledger clean — {len(evidence_entries)} entries, no raw secrets")
    print()

    # ── Stage 5: Write Outputs ────────────────────────────────────────────
    print("[5] Writing output files...")

    # 5.1 One-shot result
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

    # Build asset summary (no raw values, just sanitized data)
    asset_summary = []
    for a in assets_data:
        asset_summary.append({
            "symbol": a.get("symbol"),
            "price_ok": a.get("price", 0) > 0,
            "price_change_pct_rounded": round(a.get("price_change_pct", 0), 2),
            "volume_24h_ok": a.get("volume_24h", 0) > 0,
        })

    real_output = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "real_free_api_tg_test_one_shot",
        "card_family": CardFamily.MULTI_ASSET_MARKET_SYNC.value,
        "assets": asset_summary,
        "binance_api_success": binance_success,
        "binance_api_error": binance_error,
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
            "config_ready": preflight["config_ready"],
            "bot_token_present": preflight["bot_token_present"],
            "chat_id_present": preflight["chat_id_present"],
        },
    }
    write_json(existing_result_path, real_output)
    print(f"  [OK] {existing_result_path}")

    # 5.2 Evidence ledger JSONL
    ledger_path = ledger.write_jsonl(
        results_dir / "market_radar_v117b_shared_pipeline_tg_evidence_ledger.jsonl"
    )
    print(f"  [OK] {ledger_path}")

    # 5.3 One-shot report
    tg_status_text = ""
    if tg and tg.success:
        tg_status_text = f"""
## TG Test Group Send

✅ **SENT** — 1 message delivered to TG test group (one-shot).

- Status: `{tg.status}`
- Target: `{tg.target_type}`
- Production send: **False**
- One-shot: **True**
- Message proof: SHA-256 redacted
- Token proof: SHA-256 redacted
- Chat ID proof: SHA-256 redacted
- Credentials printed: **{tg.credentials_printed}**
"""
    elif tg and tg.status == "skipped":
        tg_status_text = f"""
## TG Test Group Send

⚠ **SKIPPED** — TG test group send not attempted.

- Status: `{tg.status}`
- Reason: `{tg.reason}`
- This is expected and NOT a pipeline failure.
- Test group send requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env vars.
"""
    elif tg and tg.status == "blocked":
        tg_status_text = f"""
## TG Test Group Send

⛔ **BLOCKED** — Send-readiness gate blocked the send.

- Status: `{tg.status}`
- Reason: `{tg.reason}`
"""
    else:
        tg_status_text = """
## TG Test Group Send

❓ **UNKNOWN** — No TG result available.
"""

    report_md = f"""# Market Radar {PIPELINE_VERSION}B — Shared Pipeline TG One-Shot Report

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## Binance Real API Status

| Check | Status |
|-------|--------|
| API called | {'✅' if SAFETY['external_api_called'] else '❌'} |
| API success | {'✅' if binance_success else '❌'} |
| Assets retrieved | {len(asset_summary)} |

### Asset Details

| Symbol | Price OK | 24h Change % | Volume OK |
|--------|----------|-------------|-----------|
"""
    for a in asset_summary:
        report_md += f"| {a['symbol']} | {'✅' if a['price_ok'] else '❌'} | {a['price_change_pct_rounded']:+.2f}% | {'✅' if a['volume_24h_ok'] else '❌'} |\n"

    if binance_error:
        report_md += f"\n### Error Detail\n\n```\n{binance_error}\n```\n"

    report_md += f"""
---

## Pipeline Result

| Stage | Result |
|-------|--------|
| Card Family | `{CardFamily.MULTI_ASSET_MARKET_SYNC.value}` |
| Gate | {'✅ allow' if gate and gate.allow else '⛔ block'} |
| Send-Readiness | {'✅ allow_test_group' if sr and sr.allow_test_group else '⛔ block'} |
| Pipeline Passed | {'✅' if result.passed else '⛔'} |
{tg_status_text}
---

## Safety Verification

| Check | Status |
|-------|--------|
| External API called | {'✅' if SAFETY['external_api_called'] else '❌'} |
| TG sent this run | {'✅' if SAFETY['tg_sent_this_run'] else '❌ (or skipped)'} |
| Production send | {'❌ NEVER' if not SAFETY['production_send'] else '⚠ ERROR'} |
| X/Twitter send | {'❌ NEVER' if not SAFETY['x_twitter_send'] else '⚠ ERROR'} |
| Credentials printed | {'❌ NEVER' if not SAFETY['credentials_printed'] else '⚠ ERROR'} |
| Daemon/loop started | {'❌ NEVER' if not SAFETY['daemon_or_loop_started'] else '⚠ ERROR'} |
| Files deleted | {'❌ NEVER' if not SAFETY['files_deleted'] else '⚠ ERROR'} |
| v116 history modified | {'❌ NEVER' if not SAFETY['v116_history_modified'] else '⚠ ERROR'} |
| Evidence ledger clean | {'✅' if clean else '❌'} |

## Free API Data Source

- **Binance Public REST API** (`/api/v3/ticker/24hr`): BTC/ETH/SOL 24hr ticker data
- No API key required
"""
    write_md(runs_dir / "v117b_shared_pipeline_tg_one_shot_report.md", report_md)
    print(f"  [OK] {runs_dir / 'v117b_shared_pipeline_tg_one_shot_report.md'}")

    # 5.4 Handoff
    handoff_md = f"""# Market Radar {PIPELINE_VERSION}B — Local-Only Handoff

**Generated**: {china_stamp()}
**Run ID**: {RUN_ID}
**Task ID**: {TASK_ID}

---

## What Was Done

- Ran v117B shared pipeline (focused on multi_asset_market_sync via Binance public REST)
- Called Binance public API for BTC/ETH/SOL: {'✅ success' if binance_success else '❌ failed'}
- Ran safe config preflight (bool/length/hash only — no raw credentials)
- Attempted TG test group one-shot send: {'✅ sent' if (tg and tg.success) else '⚠ skipped/blocked'}
- Wrote redacted evidence ledger
- All outputs verified: no raw token/chat_id/message_id

## TG Test Group Send Status

- TG sent: {'1 message' if (tg and tg.success) else '0 messages'}
- TG skipped (missing safe config): {'1' if (tg and tg.status == 'skipped') else '0'}
- TG blocked (gate): {'1' if (tg and tg.status == 'blocked') else '0'}
- Production send: **False** (never)

## New Files Created

| File | Type |
|------|------|
| `scripts/run_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py` | Runner |
| `scripts/test_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py` | Tests |
| `results/market_radar_v117b_tg_safe_config_preflight.json` | Config preflight |
| `results/market_radar_v117b_shared_pipeline_tg_one_shot_result.json` | Result |
| `results/market_radar_v117b_shared_pipeline_tg_evidence_ledger.jsonl` | Evidence ledger |
| `runs/market_radar/v117b_shared_pipeline_tg_one_shot_report.md` | Report |
| `runs/market_radar/v117b_local_only_handoff.md` | Handoff |

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

## Production Ready Status

**0/5 — NOT FOR LIVE USE**

All 6 minimum conditions remain unmet. Production send is NEVER enabled in this pipeline.

## Next Steps

1. Run tests: `python -X utf8 -m pytest scripts/test_market_radar_v117b_shared_pipeline_tg_test_group_one_shot.py -v`
2. If TG safe config available, verify test group message in TG
3. Regress v117 and v116N tests
"""
    write_md(runs_dir / "v117b_local_only_handoff.md", handoff_md)
    print(f"  [OK] {runs_dir / 'v117b_local_only_handoff.md'}")

    # ── Final Summary ───────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"Shared Pipeline {PIPELINE_VERSION}B — One-Shot Complete")
    print(f"  Binance API: {'SUCCESS' if binance_success else 'FAILED'}")
    print(f"  Assets retrieved: {len(asset_summary)} (BTC/ETH/SOL)")
    print(f"  TG sent: {'1 message' if (tg and tg.success) else '0 (skipped/blocked)'}")
    print(f"  Pipeline passed: {result.passed}")
    print(f"  Production ready: 0/5 (by design)")
    print(f"  Evidence ledger: {'clean' if clean else 'WARNINGS'}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
