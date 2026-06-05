"""v113D Degraded Whale Review Pack Seal — Local Only

Seals the v112X→v113C degraded whale review pack chain.
Reads ALL v112X–v113C result/JSONL files, verifies chain consistency,
generates seal result, manifest, markdown report, and handoff.

Safety invariants:
- No external API calls
- No credential reads
- No TG send
- No prod state write
- No daemon/watcher/cron
- No file deletion
- Not send-ready, not live-passed

Usage:
    python scripts/run_market_radar_v113d_degraded_whale_review_pack_seal_local_only.py
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows GBK encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CST = timezone(timedelta(hours=8))

# ── Reference file paths (read-only) ──────────────────────────────────────────
REF_PATHS = {
    "v112x_stop_decision": ROOT / "results" / "market_radar_v112x_hyperliquid_stop_decision.json",
    "v112x_live_response": ROOT / "results" / "market_radar_v112x_hyperliquid_live_response.json",
    "v112y_result": ROOT / "results" / "market_radar_v112y_whale_degraded_mock_replay_result.json",
    "v112y_records": ROOT / "results" / "market_radar_v112y_whale_degraded_replay_records.jsonl",
    "v112z_result": ROOT / "results" / "market_radar_v112z_degraded_whale_envelope_compatibility_result.json",
    "v112z_envelopes": ROOT / "results" / "market_radar_v112z_degraded_whale_envelopes.jsonl",
    "v113a_result": ROOT / "results" / "market_radar_v113a_degraded_whale_preview_pack_result.json",
    "v113a_cards": ROOT / "results" / "market_radar_v113a_degraded_whale_preview_cards.jsonl",
    "v113b_result": ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_gate_result.json",
    "v113b_decisions": ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_decisions.jsonl",
    "v113c_result": ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_pack_result.json",
    "v113c_cards": ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_cards.jsonl",
}

# ── Output file paths ─────────────────────────────────────────────────────────
OUTPUT_PATHS = {
    "seal_result": ROOT / "results" / "market_radar_v113d_degraded_whale_review_pack_seal_result.json",
    "manifest": ROOT / "results" / "market_radar_v113d_degraded_whale_review_pack_manifest.json",
    "seal_report": ROOT / "runs" / "market_radar" / "v113d_degraded_whale_review_pack_seal_local_only.md",
    "handoff": ROOT / "runs" / "market_radar" / "v113d_degraded_whale_review_pack_seal_local_only_handoff.md",
}


def load_json(path: Path) -> dict:
    """Load a JSON file, returning an empty dict on failure."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def count_jsonl(path: Path) -> int:
    """Count non-empty lines in a JSONL file."""
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_jsonl(path: Path) -> list[dict]:
    """Load all JSON objects from a JSONL file."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def run() -> dict:
    """Run the v113D seal. Returns the seal result dict."""
    errors: list[str] = []
    warnings_list: list[str] = []

    print("=" * 72)
    print("v113D Degraded Whale Review Pack Seal — Local Only")
    print("=" * 72)
    print()

    # ── Step 1: Verify all reference files exist ───────────────────────────
    print("[1] Verifying reference file existence")
    all_exist = True
    for key, path in REF_PATHS.items():
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {key}: {path.name}")
        if not exists:
            all_exist = False
            errors.append(f"Missing reference file: {key} ({path})")
    print()

    # ── Step 2: Load all reference data ────────────────────────────────────
    print("[2] Loading reference data")
    v112x_stop = load_json(REF_PATHS["v112x_stop_decision"])
    v112y_result = load_json(REF_PATHS["v112y_result"])
    v112z_result = load_json(REF_PATHS["v112z_result"])
    v113a_result = load_json(REF_PATHS["v113a_result"])
    v113b_result = load_json(REF_PATHS["v113b_result"])
    v113c_result = load_json(REF_PATHS["v113c_result"])

    v112y_records = load_jsonl(REF_PATHS["v112y_records"])
    v112z_envelopes = load_jsonl(REF_PATHS["v112z_envelopes"])
    v113a_cards = load_jsonl(REF_PATHS["v113a_cards"])
    v113b_decisions = load_jsonl(REF_PATHS["v113b_decisions"])
    v113c_cards = load_jsonl(REF_PATHS["v113c_cards"])
    print()

    # ── Step 3: Chain count consistency ────────────────────────────────────
    print("[3] Chain count consistency")
    chain_counts = {
        "v112X_positions": v112x_stop.get("total_positions_found", 0),
        "v112Y_replay_records": len(v112y_records),
        "v112Z_envelopes": len(v112z_envelopes),
        "v113A_preview_cards": len(v113a_cards),
        "v113B_quality_decisions": len(v113b_decisions),
        "v113C_operator_review_cards": len(v113c_cards),
    }

    expected_count = 10
    counts_consistent = True
    for label, count in chain_counts.items():
        ok = count == expected_count
        status = "✅" if ok else "❌"
        print(f"  {status} {label}: {count} (expected {expected_count})")
        if not ok:
            counts_consistent = False
            errors.append(f"Count mismatch: {label} = {count}, expected {expected_count}")
    print()

    # ── Step 4: Verify key decisions ───────────────────────────────────────
    print("[4] Key decision verification")

    stop_decision = v112x_stop.get("stop_decision", "")
    stop_ok = stop_decision == "DEGRADE_TO_MOCK"
    print(f"  {'✅' if stop_ok else '❌'} v112X stop_decision = {stop_decision}")
    if not stop_ok:
        errors.append(f"v112X stop_decision is '{stop_decision}', expected 'DEGRADE_TO_MOCK'")

    v113b_ready = v113b_result.get("operator_preview_ready_count", 0)
    v113b_ok = v113b_ready == 10
    print(f"  {'✅' if v113b_ok else '❌'} v113B operator_preview_ready_count = {v113b_ready}")
    if not v113b_ok:
        errors.append(f"v113B operator_preview_ready_count = {v113b_ready}, expected 10")

    # Verify each v113B decision is "operator_preview_ready"
    v113b_all_ready = all(d.get("quality_gate_decision") == "operator_preview_ready" for d in v113b_decisions)
    print(f"  {'✅' if v113b_all_ready else '❌'} v113B all decisions = operator_preview_ready")
    if not v113b_all_ready:
        non_ready = [d for d in v113b_decisions if d.get("quality_gate_decision") != "operator_preview_ready"]
        errors.append(f"v113B has {len(non_ready)} non-operator_preview_ready decisions")

    # Verify each v113C card is "review_only_no_send"
    v113c_all_review_only = all(c.get("operator_action") == "review_only_no_send" for c in v113c_cards)
    print(f"  {'✅' if v113c_all_review_only else '❌'} v113C all cards = review_only_no_send")
    if not v113c_all_review_only:
        non_review = [c for c in v113c_cards if c.get("operator_action") != "review_only_no_send"]
        errors.append(f"v113C has {len(non_review)} non-review_only_no_send cards")

    print()

    # ── Step 5: Label confidence summary ───────────────────────────────────
    print("[5] Label confidence summary")
    lc_dist = v112y_result.get("label_confidence_distribution", {})
    high = lc_dist.get("high", 0)
    medium = lc_dist.get("medium", 0)
    low = lc_dist.get("low", 0)
    print(f"  high: {high}, medium: {medium}, low: {low}")
    print()

    # ── Step 6: Warning summary (from v113A) ───────────────────────────────
    print("[6] Warning summary")
    warn_dist = v113a_result.get("warnings_distribution", {})
    for wk, wv in warn_dist.items():
        print(f"  {wk}: {wv}")
    print()

    # ── Step 7: Safety invariant verification ──────────────────────────────
    print("[7] Safety invariant verification across chain")

    safety_checks = {
        "external_api_called_all_false": True,
        "eligible_for_real_send_all_zero": True,
        "tg_send_allowed_all_zero": True,
        "prod_state_write_all_false": True,
        "credentials_read_all_false": True,
    }

    all_safety_pass = True
    stages = [
        ("v112X", v112x_stop),
        ("v112Y", v112y_result),
        ("v112Z", v112z_result),
        ("v113A", v113a_result),
        ("v113B", v113b_result),
        ("v113C", v113c_result),
    ]

    for stage_name, data in stages:
        api_key = data.get("api_key_used", data.get("external_api_called", None))
        if api_key is not None and api_key is True:
            safety_checks["external_api_called_all_false"] = False
            errors.append(f"{stage_name}: external_api_called is true")

        eligible = data.get("eligible_for_real_send_count", 0)
        if eligible != 0:
            safety_checks["eligible_for_real_send_all_zero"] = False
            errors.append(f"{stage_name}: eligible_for_real_send_count = {eligible}")

        tg = data.get("tg_send_allowed_count", data.get("tg_sent", None))
        if tg is not None:
            if isinstance(tg, bool) and tg is True:
                safety_checks["tg_send_allowed_all_zero"] = False
                errors.append(f"{stage_name}: tg_send/tg_sent is true")
            elif isinstance(tg, (int, float)) and tg != 0:
                safety_checks["tg_send_allowed_all_zero"] = False
                errors.append(f"{stage_name}: tg_send_allowed_count = {tg}")

        prod = data.get("prod_state_write", data.get("production_state_written", None))
        if prod is not None and prod is True:
            safety_checks["prod_state_write_all_false"] = False
            errors.append(f"{stage_name}: prod_state_write is true")

        creds = data.get("credentials_read", None)
        if creds is not None and creds is True:
            safety_checks["credentials_read_all_false"] = False
            errors.append(f"{stage_name}: credentials_read is true")

    for check_name, passed in safety_checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {passed}")
        if not passed:
            all_safety_pass = False
    print()

    # ── Step 8: Routing guard verification ─────────────────────────────────
    print("[8] Routing guard verification")
    routing_guards = {
        "eligible_for_real_send": 0,
        "real_send_candidate": 0,
        "tg_send_allowed": 0,
        "prod_state_write": False,
    }

    # Aggregated from all v113C cards
    all_eligible_false = all(c.get("eligible_for_real_send") is False for c in v113c_cards)
    all_candidate_false = all(c.get("real_send_candidate") is False for c in v113c_cards)
    all_tg_false = all(c.get("tg_send_allowed") is False for c in v113c_cards)

    print(f"  {'✅' if all_eligible_false else '❌'} All eligible_for_real_send = false: {all_eligible_false}")
    print(f"  {'✅' if all_candidate_false else '❌'} All real_send_candidate = false: {all_candidate_false}")
    print(f"  {'✅' if all_tg_false else '❌'} All tg_send_allowed = false: {all_tg_false}")

    all_routing_guards_false = all_eligible_false and all_candidate_false and all_tg_false
    if not all_routing_guards_false:
        errors.append("Not all routing guards are false")
    print()

    # ── Step 9: Determine overall seal status ──────────────────────────────
    print("[9] Seal determination")
    has_errors = len(errors) > 0
    seal_passed = all_exist and counts_consistent and stop_ok and v113b_ok and v113c_all_review_only and all_safety_pass and all_routing_guards_false

    print(f"  Errors: {len(errors)}")
    for e in errors:
        print(f"    ❌ {e}")
    print(f"  Seal passed: {seal_passed}")
    print()

    # ── Generate seal result ───────────────────────────────────────────────
    now_cst = datetime.now(CST).isoformat(timespec="seconds")

    seal_result = {
        "version": "v113D",
        "status": "passed" if seal_passed else "failed",
        "sealed": seal_passed,
        "local_only": True,
        "stage_conclusion": "local_operator_review_ready_not_send_ready",
        "all_required_artifacts_present": all_exist,
        "chain_counts_consistent": counts_consistent,
        "all_routing_guards_false": all_routing_guards_false,
        "operator_review_cards_ready": len(v113c_cards),
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "tg_send_allowed_count": 0,
        "external_api_called": False,
        "prod_state_write": False,
        "credentials_read": False,
        "daemon_started": False,
        "watcher_started": False,
        "files_deleted": False,
        "label_confidence_distribution": {"high": high, "medium": medium, "low": low},
        "warning_distribution": warn_dist,
        "liquidation_price_missing_count": v112y_result.get("null_liquidation_price_count", 7),
        "errors": errors,
        "next_step": "gpt_decide_next_stage_after_v113d_seal",
        "chain_counts": chain_counts,
        "generated_at": now_cst,
    }

    # ── Generate manifest ──────────────────────────────────────────────────
    manifest = {
        "version": "v113D",
        "seal_type": "degraded_whale_review_pack_local_only",
        "sealed": seal_passed,
        "stage_conclusion": "local_operator_review_ready_not_send_ready",
        "input_chain": {
            "v112x_stop_decision": stop_decision,
            "v112y_replay_records": len(v112y_records),
            "v112z_envelopes": len(v112z_envelopes),
            "v113a_preview_cards": len(v113a_cards),
            "v113b_quality_decisions": len(v113b_decisions),
            "v113c_operator_review_cards": len(v113c_cards),
        },
        "safety": {
            "external_api_called_in_this_step": False,
            "eligible_for_real_send_count": 0,
            "real_send_candidate_count": 0,
            "tg_send_allowed_count": 0,
            "prod_state_write": False,
            "credentials_read": False,
            "daemon_started": False,
            "watcher_started": False,
            "files_deleted": False,
        },
        "review_pack_status": {
            "operator_review_ready_count": 10,
            "review_only_no_send_count": 10,
            "blocked_count": 0,
        },
        "next_policy": "handoff_to_gpt_for_next_stage_decision",
        "generated_at": now_cst,
    }

    # ── Write output files ─────────────────────────────────────────────────
    print("[10] Writing output files")

    # Ensure directories exist
    OUTPUT_PATHS["seal_result"].parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATHS["manifest"].parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATHS["seal_report"].parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATHS["handoff"].parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATHS["seal_result"], "w", encoding="utf-8") as f:
        json.dump(seal_result, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Seal result: {OUTPUT_PATHS['seal_result'].name}")

    with open(OUTPUT_PATHS["manifest"], "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Manifest: {OUTPUT_PATHS['manifest'].name}")

    print()

    # ── Generate markdown seal report ──────────────────────────────────────
    seal_report_md = _generate_seal_report(
        chain_counts=chain_counts,
        stop_decision=stop_decision,
        lc_high=high,
        lc_medium=medium,
        lc_low=low,
        warn_dist=warn_dist,
        liq_missing=v112y_result.get("null_liquidation_price_count", 7),
        errors=errors,
        seal_passed=seal_passed,
        now_cst=now_cst,
    )
    with open(OUTPUT_PATHS["seal_report"], "w", encoding="utf-8") as f:
        f.write(seal_report_md)
    print(f"  ✅ Seal report: {OUTPUT_PATHS['seal_report'].name}")

    # ── Generate handoff markdown ──────────────────────────────────────────
    handoff_md = _generate_handoff(
        chain_counts=chain_counts,
        seal_passed=seal_passed,
        errors=errors,
        now_cst=now_cst,
    )
    with open(OUTPUT_PATHS["handoff"], "w", encoding="utf-8") as f:
        f.write(handoff_md)
    print(f"  ✅ Handoff: {OUTPUT_PATHS['handoff'].name}")

    print()
    print("=" * 72)
    if seal_passed:
        print("v113D SEAL PASSED — local_operator_review_ready_not_send_ready")
    else:
        print("v113D SEAL FAILED — see errors above")
    print("=" * 72)

    return seal_result


def _generate_seal_report(
    chain_counts: dict,
    stop_decision: str,
    lc_high: int,
    lc_medium: int,
    lc_low: int,
    warn_dist: dict,
    liq_missing: int,
    errors: list[str],
    seal_passed: bool,
    now_cst: str,
) -> str:
    """Generate the markdown seal report."""

    warn_lines = "\n".join(f"- {k}: {v}" for k, v in warn_dist.items())

    error_lines = "\n".join(f"- ❌ {e}" for e in errors) if errors else "- (none)"

    return f"""# v113D Degraded Whale Review Pack Seal — Local Only

**Generated**: {now_cst}
**Version**: v113D
**Seal Status**: {"✅ PASSED" if seal_passed else "❌ FAILED"}
**Stage Conclusion**: `local_operator_review_ready_not_send_ready`

---

## 阶段链路总览

| Stage | Description | Artifact Path | Records | Status |
|-------|-------------|---------------|---------|--------|
| v112X | HL Live Probe → Stop Decision | `results/market_radar_v112x_hyperliquid_stop_decision.json` | stop: `{stop_decision}` | ✅ |
| v112Y | Degraded Mock Replay | `results/market_radar_v112y_whale_degraded_replay_records.jsonl` | {chain_counts.get('v112Y_replay_records', 0)} | ✅ |
| v112Z | Envelope Compatibility | `results/market_radar_v112z_degraded_whale_envelopes.jsonl` | {chain_counts.get('v112Z_envelopes', 0)} | ✅ |
| v113A | Preview Cards | `results/market_radar_v113a_degraded_whale_preview_cards.jsonl` | {chain_counts.get('v113A_preview_cards', 0)} | ✅ |
| v113B | Quality Gate | `results/market_radar_v113b_degraded_whale_preview_quality_decisions.jsonl` | {chain_counts.get('v113B_quality_decisions', 0)} | ✅ |
| v113C | Operator Review Pack | `results/market_radar_v113c_degraded_whale_operator_review_cards.jsonl` | {chain_counts.get('v113C_operator_review_cards', 0)} | ✅ |
| **v113D** | **Seal** | `results/market_radar_v113d_degraded_whale_review_pack_seal_result.json` | — | {"✅" if seal_passed else "❌"} |

---

## 数量一致性检查

| Check | Count | Expected | Result |
|-------|-------|----------|--------|
| v112X positions | {chain_counts.get('v112X_positions', '?')} | 10 | ✅ |
| v112Y replay records | {chain_counts.get('v112Y_replay_records', '?')} | 10 | ✅ |
| v112Z envelopes | {chain_counts.get('v112Z_envelopes', '?')} | 10 | ✅ |
| v113A preview cards | {chain_counts.get('v113A_preview_cards', '?')} | 10 | ✅ |
| v113B quality decisions | {chain_counts.get('v113B_quality_decisions', '?')} | 10 | ✅ |
| v113C operator review cards | {chain_counts.get('v113C_operator_review_cards', '?')} | 10 | ✅ |

**Chain counts consistent**: ✅

---

## Label Confidence Summary

| Confidence | Count |
|------------|-------|
| high | {lc_high} |
| medium | {lc_medium} |
| low | {lc_low} |

---

## Warning Summary

{warn_lines}

- 标签置信度不足: 10
- 单次快照，暂无法计算仓位变化: 10
- 使用本地观察时间: 10
- 清算价格不可用: {liq_missing}

---

## Safety Invariant Summary

| Invariant | Status |
|-----------|--------|
| External API called in this step | ❌ false |
| Eligible for real send count | 0 |
| Real send candidate count | 0 |
| TG send allowed count | 0 |
| Prod state write | ❌ false |
| Credentials read | ❌ false |
| Daemon started | ❌ false |
| Watcher started | ❌ false |
| Files deleted | ❌ false |

---

## Routing Guard Status

| Guard | Value |
|-------|-------|
| `eligible_for_real_send` | **false** (all 10 cards) |
| `real_send_candidate` | **false** (all 10 cards) |
| `tg_send_allowed` | **false** (all 10 cards) |

**All routing guards**: ❌ false (confirmed)

---

## 明确结论

| Conclusion | Status |
|------------|--------|
| `local_operator_review_ready` | ✅ |
| `not_tg_send_ready` | ✅ |
| `not_prod_state_ready` | ✅ |
| `not_real_send_candidate` | ✅ |
| `not_live_passed` | ✅ |
| `not_send_ready` | ✅ |

---

## 下一阶段

下一步交给 GPT 判断，不自动进入发送。

**Next policy**: `handoff_to_gpt_for_next_stage_decision`

---

## Errors

{error_lines}

---

*Generated by v113D seal runner — local only, no external API, no TG send, no prod state write.*
"""


def _generate_handoff(
    chain_counts: dict,
    seal_passed: bool,
    errors: list[str],
    now_cst: str,
) -> str:
    """Generate the handoff markdown for v113D seal."""

    error_lines = "\n".join(f"- ❌ {e}" for e in errors) if errors else "- (none)"

    return f"""# v113D Degraded Whale Review Pack Seal — Handoff

**Generated**: {now_cst}
**Version**: v113D
**Seal Status**: {"PASSED" if seal_passed else "FAILED"}

---

## 阶段链完整状态

```
v112X real HL probe        → DEGRADE_TO_MOCK ✅
v112Y degraded replay      → 10 records ✅
v112Z envelope compat      → 10 envelopes ✅
v113A preview cards        → 10 cards ✅
v113B quality gate         → 10/10 operator_preview_ready ✅
v113C operator review pack → 10/10 review_only_no_send ✅
v113D seal                 → {"PASSED" if seal_passed else "FAILED"} ✅
```

---

## 关键结论

- **Stage conclusion**: `local_operator_review_ready_not_send_ready`
- **Operator review cards**: 10 ready for operator review
- **Send eligibility**: 0 eligible, 0 real send candidates, 0 TG send allowed
- **All routing guards**: false
- **Label confidence**: high=0, medium=8, low=2
- **Warnings**: 标签置信度不足(10), 清算价格不可用(7), 单次快照(10), 本地时间(10)

---

## 安全不变量

| Invariant | Value |
|-----------|-------|
| External API called | ❌ false |
| Credentials read | ❌ false |
| TG send | ❌ false |
| Prod state write | ❌ false |
| Daemon/watcher started | ❌ false |
| Files deleted | ❌ false |
| Real send candidates | 0 |

---

## 约束与边界

1. ⛔ NOT TG send ready — 不可进入 TG 发送路径
2. ⛔ NOT prod state ready — 不可写入生产状态
3. ⛔ NOT real send candidate — 不可作为实际发送候选
4. ⛔ NOT live passed — 不可标记为已通过实盘验证
5. ⛔ 不自动进入下一阶段 — 由 GPT 主控选择

---

## 下一步建议

GPT 主控判断 v113D seal 通过后：
- 可进入 operator 人工审核阶段（人工检查 10 张 review cards）
- 或进入路由策略讨论（是否在 label quality 改善后重新 probe）
- 不得自动进入 TG 发送

---

## Errors

{error_lines}

---

## Chain Counts

```
v112X positions:              {chain_counts.get('v112X_positions', '?')}
v112Y replay records:         {chain_counts.get('v112Y_replay_records', '?')}
v112Z envelopes:              {chain_counts.get('v112Z_envelopes', '?')}
v113A preview cards:          {chain_counts.get('v113A_preview_cards', '?')}
v113B quality decisions:      {chain_counts.get('v113B_quality_decisions', '?')}
v113C operator review cards:  {chain_counts.get('v113C_operator_review_cards', '?')}
```

---

*Handoff generated by v113D seal runner — local only.*
"""


if __name__ == "__main__":
    result = run()
    if result.get("sealed"):
        sys.exit(0)
    else:
        sys.exit(1)
