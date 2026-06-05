#!/usr/bin/env python3
"""
v114D Whale Delta Review Pack Seal — Local Only
=================================================
Seals the v114C operator review pack by verifying the full chain:
  v114A baseline → v114B second probe delta → v114C operator review pack → v114D seal

Invariants (enforced):
  - No external API calls
  - No API key / credentials read
  - No TG send
  - No production state write
  - No daemon / watcher / loop
  - No file deletion
  - All routing guards false
  - Stage conclusion: local_delta_review_ready_not_send_ready
"""

import json
import os
import sys
import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v114A inputs (read-only)
V114A_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot_result.json")
V114A_POSITIONS = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_positions.jsonl")

# v114B inputs (read-only)
V114B_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_delta_compare_result.json")
V114B_DELTAS = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_position_deltas.jsonl")

# v114C inputs (read-only)
V114C_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_pack_result.json")
V114C_CARDS = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl")

# v114D outputs
OUT_SEAL_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114d_whale_delta_review_pack_seal_result.json")
OUT_MANIFEST = os.path.join(RESULTS_DIR, "market_radar_v114d_whale_delta_review_pack_manifest.json")
OUT_REPORT = os.path.join(RUNS_DIR, "v114d_whale_delta_review_pack_seal_local_only.md")
OUT_HANDOFF = os.path.join(RUNS_DIR, "v114d_whale_delta_review_pack_seal_local_only_handoff.md")

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants
EXTERNAL_API_CALLED = False
CREDENTIALS_READ = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
TG_SENT = False
PROD_STATE_WRITE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.datetime.now(TZ_SHANGHAI).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_jsonl(path) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Step 1: Load all chain inputs
# ---------------------------------------------------------------------------
def load_all_inputs():
    """Load v114A, v114B, v114C results and records."""
    errors = []

    # v114A
    if not os.path.exists(V114A_RESULT):
        errors.append(f"v114A result not found: {V114A_RESULT}")
    if not os.path.exists(V114A_POSITIONS):
        errors.append(f"v114A positions not found: {V114A_POSITIONS}")

    # v114B
    if not os.path.exists(V114B_RESULT):
        errors.append(f"v114B result not found: {V114B_RESULT}")
    if not os.path.exists(V114B_DELTAS):
        errors.append(f"v114B deltas not found: {V114B_DELTAS}")

    # v114C
    if not os.path.exists(V114C_RESULT):
        errors.append(f"v114C result not found: {V114C_RESULT}")
    if not os.path.exists(V114C_CARDS):
        errors.append(f"v114C cards not found: {V114C_CARDS}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    v114a_result = load_json(V114A_RESULT)
    v114a_positions = load_jsonl(V114A_POSITIONS)
    v114b_result = load_json(V114B_RESULT)
    v114b_deltas = load_jsonl(V114B_DELTAS)
    v114c_result = load_json(V114C_RESULT)
    v114c_cards = load_jsonl(V114C_CARDS)

    print(f"  v114A: {len(v114a_positions)} baseline positions")
    print(f"  v114B: {len(v114b_deltas)} delta records")
    print(f"  v114C: {len(v114c_cards)} operator review cards")

    return (v114a_result, v114a_positions,
            v114b_result, v114b_deltas,
            v114c_result, v114c_cards)


# ---------------------------------------------------------------------------
# Step 2: Validate chain counts
# ---------------------------------------------------------------------------
def validate_chain_counts(v114a_result, v114a_positions,
                          v114b_result, v114b_deltas,
                          v114c_result, v114c_cards):
    """Verify all chain counts are consistent (10 each)."""
    checks = []
    all_pass = True

    checks.append(("v114A baseline records = 10",
                   len(v114a_positions) == 10,
                   f"got {len(v114a_positions)}"))
    checks.append(("v114A result baseline_records_written = 10",
                   v114a_result.get("baseline_records_written") == 10,
                   f"got {v114a_result.get('baseline_records_written')}"))
    checks.append(("v114B delta records = 10",
                   len(v114b_deltas) == 10,
                   f"got {len(v114b_deltas)}"))
    checks.append(("v114B result delta_records_written = 10",
                   v114b_result.get("delta_records_written") == 10,
                   f"got {v114b_result.get('delta_records_written')}"))
    checks.append(("v114C operator review cards = 10",
                   len(v114c_cards) == 10,
                   f"got {len(v114c_cards)}"))
    checks.append(("v114C result operator_review_cards_written = 10",
                   v114c_result.get("operator_review_cards_written") == 10,
                   f"got {v114c_result.get('operator_review_cards_written')}"))

    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
            print(f"  [{status}] {name} ({detail})")
        else:
            print(f"  [{status}] {name}")

    return all_pass


# ---------------------------------------------------------------------------
# Step 3: Validate delta summary
# ---------------------------------------------------------------------------
def validate_delta_summary(v114b_deltas, v114c_cards):
    """Verify delta type distribution matches expected values."""
    # Count from v114B deltas
    b_closed = sum(1 for d in v114b_deltas if d.get("delta_type") == "closed_position")
    b_changed = sum(1 for d in v114b_deltas if d.get("delta_type") == "size_changed")
    b_unchanged = sum(1 for d in v114b_deltas if d.get("delta_type") == "unchanged")
    b_new = sum(1 for d in v114b_deltas if d.get("delta_type") == "new_position")

    # Count from v114C cards
    c_closed = sum(1 for c in v114c_cards if c.get("delta_type") == "closed_position")
    c_changed = sum(1 for c in v114c_cards if c.get("delta_type") == "size_changed")
    c_unchanged = sum(1 for c in v114c_cards if c.get("delta_type") == "unchanged")
    c_new = sum(1 for c in v114c_cards if c.get("delta_type") == "new_position")

    checks = [
        ("closed_position = 1 (v114B)", b_closed == 1, f"got {b_closed}"),
        ("size_changed = 5 (v114B)", b_changed == 5, f"got {b_changed}"),
        ("unchanged = 4 (v114B)", b_unchanged == 4, f"got {b_unchanged}"),
        ("new_position = 0 (v114B)", b_new == 0, f"got {b_new}"),
        ("v114B<->v114C closed_position consistent", b_closed == c_closed, f"{b_closed} vs {c_closed}"),
        ("v114B<->v114C size_changed consistent", b_changed == c_changed, f"{b_changed} vs {c_changed}"),
        ("v114B<->v114C unchanged consistent", b_unchanged == c_unchanged, f"{b_unchanged} vs {c_unchanged}"),
        ("v114B<->v114C new_position consistent", b_new == c_new, f"{b_new} vs {c_new}"),
    ]

    all_pass = True
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
            print(f"  [{status}] {name} ({detail})")
        else:
            print(f"  [{status}] {name}")

    return all_pass, {
        "closed_position": b_closed,
        "size_changed": b_changed,
        "unchanged": b_unchanged,
        "new_position": b_new,
    }


# ---------------------------------------------------------------------------
# Step 4: Validate attention summary
# ---------------------------------------------------------------------------
def validate_attention_summary(v114c_cards):
    """Verify operator attention level distribution."""
    high = sum(1 for c in v114c_cards if c.get("operator_attention_level") == "high")
    medium = sum(1 for c in v114c_cards if c.get("operator_attention_level") == "medium")
    low = sum(1 for c in v114c_cards if c.get("operator_attention_level") == "low")

    checks = [
        ("high = 1", high == 1, f"got {high}"),
        ("medium = 5", medium == 5, f"got {medium}"),
        ("low = 4", low == 4, f"got {low}"),
    ]

    all_pass = True
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
            print(f"  [{status}] {name} ({detail})")
        else:
            print(f"  [{status}] {name}")

    return all_pass, {"high": high, "medium": medium, "low": low}


# ---------------------------------------------------------------------------
# Step 5: Validate BTC short closed_position
# ---------------------------------------------------------------------------
def validate_btc_closed_position(v114c_cards):
    """Verify the BTC short closed_position is correctly classified."""
    btc_cards = [
        c for c in v114c_cards
        if c.get("delta_type") == "closed_position"
        and c.get("asset") == "BTC"
        and c.get("side") == "short"
    ]

    if not btc_cards:
        print("  [FAIL] No BTC short closed_position found in v114C cards!")
        return False, None

    c = btc_cards[0]
    checks = [
        ("asset = BTC", c.get("asset") == "BTC", f"got {c.get('asset')}"),
        ("side = short", c.get("side") == "short", f"got {c.get('side')}"),
        ("delta_type = closed_position", c.get("delta_type") == "closed_position",
         f"got {c.get('delta_type')}"),
        ("operator_attention_level = high", c.get("operator_attention_level") == "high",
         f"got {c.get('operator_attention_level')}"),
        ("not written as error", "error" not in c.get("review_summary", "").lower(),
         "contains 'error' in review_summary"),
        ("local_review_only = true", c.get("local_review_only") is True,
         f"got {c.get('local_review_only')}"),
        ("operator_action = review_only_no_send",
         c.get("operator_action") == "review_only_no_send",
         f"got {c.get('operator_action')}"),
        ("eligible_for_real_send = false",
         c.get("eligible_for_real_send") is False,
         f"got {c.get('eligible_for_real_send')}"),
        ("tg_send_allowed = false",
         c.get("tg_send_allowed") is False,
         f"got {c.get('tg_send_allowed')}"),
        ("prod_state_write = false",
         c.get("prod_state_write") is False,
         f"got {c.get('prod_state_write')}"),
    ]

    all_pass = True
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
            print(f"  [{status}] {name} ({detail})")
        else:
            print(f"  [{status}] {name}")

    return all_pass, btc_cards[0]


# ---------------------------------------------------------------------------
# Step 6: Validate all routing guards
# ---------------------------------------------------------------------------
def validate_routing_guards(v114c_cards):
    """Verify all review cards have routing guards set to false."""
    all_pass = True

    for i, c in enumerate(v114c_cards):
        prefix = f"card[{i}] ({c.get('asset','?')} {c.get('delta_type','?')})"

        checks = [
            ("local_review_only=true", c.get("local_review_only") is True),
            ("operator_action=review_only_no_send",
             c.get("operator_action") == "review_only_no_send"),
            ("eligible_for_real_send=false", c.get("eligible_for_real_send") is False),
            ("tg_send_allowed=false", c.get("tg_send_allowed") is False),
            ("prod_state_write=false", c.get("prod_state_write") is False),
            ("real_send_candidate=false", c.get("real_send_candidate") is False),
        ]

        for name, ok in checks:
            if not ok:
                all_pass = False
                print(f"  [FAIL] {prefix}: {name} — got {c.get(name.split('=')[0])}")

    if all_pass:
        print(f"  [PASS] All {len(v114c_cards)} cards: routing guards false")
    return all_pass


# ---------------------------------------------------------------------------
# Step 7: Generate seal result JSON
# ---------------------------------------------------------------------------
def generate_seal_result(delta_summary, attention_summary, btc_verified, routing_ok,
                         v114a_result, v114b_result, v114c_result):
    """Generate the v114D seal result JSON."""
    result = {
        "version": "v114D",
        "status": "passed",
        "sealed": True,
        "local_only": True,
        "stage_conclusion": "local_delta_review_ready_not_send_ready",
        "all_required_artifacts_present": True,
        "chain_counts_consistent": True,
        "btc_closed_position_verified": btc_verified,
        "all_routing_guards_false": routing_ok,
        "operator_review_cards_ready": v114c_result.get("operator_review_cards_written", 10),
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "tg_send_allowed_count": 0,
        "external_api_called": EXTERNAL_API_CALLED,
        "prod_state_write": PROD_STATE_WRITE,
        "credentials_read": CREDENTIALS_READ,
        "daemon_started": DAEMON_STARTED,
        "watcher_started": WATCHER_STARTED,
        "files_deleted": FILES_DELETED,
        "known_data_consistency_note_preserved": True,
        "next_step": "gpt_decide_next_stage_after_v114d_seal",
        "generated_at": now_iso(),
    }
    save_json(OUT_SEAL_RESULT, result)
    return result


# ---------------------------------------------------------------------------
# Step 8: Generate manifest JSON
# ---------------------------------------------------------------------------
def generate_manifest(delta_summary, attention_summary):
    """Generate the v114D manifest JSON."""
    manifest = {
        "version": "v114D",
        "seal_type": "whale_delta_review_pack_local_only",
        "sealed": True,
        "stage_conclusion": "local_delta_review_ready_not_send_ready",
        "input_chain": {
            "v114a_baseline_records": 10,
            "v114b_delta_records": 10,
            "v114c_operator_review_cards": 10,
        },
        "delta_summary": delta_summary,
        "attention_summary": attention_summary,
        "key_event": {
            "asset": "BTC",
            "side": "short",
            "delta_type": "closed_position",
            "operator_attention_level": "high",
            "not_error": True,
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
        "next_policy": "handoff_to_gpt_for_next_stage_decision",
        "generated_at": now_iso(),
    }
    save_json(OUT_MANIFEST, manifest)
    return manifest


# ---------------------------------------------------------------------------
# Step 9: Generate markdown seal report
# ---------------------------------------------------------------------------
def generate_markdown_report(seal_result, delta_summary, attention_summary,
                             btc_card, v114a_result, v114b_result, v114c_result):
    """Generate the v114D markdown seal report."""

    btc_section = ""
    if btc_card:
        btc_section = f"""### BTC Short Closed Position — Sealed

| 字段 | 值 |
|------|-----|
| 地址 | `{btc_card['address']}` |
| 标签 | {btc_card.get('label', '?')} |
| 标签置信度 | {btc_card.get('label_confidence', '?')} |
| 资产 | {btc_card['asset']} |
| 方向 | {btc_card['side']} |
| 基线仓位大小 | {btc_card.get('baseline_size', 0):,.2f} |
| 当前仓位大小 | {btc_card.get('current_size', 0)} |
| 变化量 | {btc_card.get('size_delta', 0):+,.2f} |
| 操作员关注级别 | **{btc_card.get('operator_attention_level', '?')}** |
| 审查摘要 | {btc_card.get('review_summary', '')} |

**Seal 结论：** BTC short closed_position 已确认并封版。
- 不是错误 — 仓位在两轮探针之间消失是预期行为
- high operator attention — 已正确标记
- 路由守卫全部保持 false
"""

    report = f"""# v114D Whale Delta Review Pack Seal — Local Only

**Generated:** {seal_result['generated_at']}
**Status:** {seal_result['status']}
**Version:** v114D
**Sealed:** ✅ True

---

## 目的 (Purpose)

对 v114A → v114B → v114C 全链路进行本地封版验收，确认所有产物完整性、
数量一致性、BTC short closed_position 正确分类、以及所有路由守卫保持 false。

---

## 阶段链路总览

| 阶段 | 版本 | 产物 | 记录数 | 状态 |
|------|------|------|--------|------|
| Baseline Snapshot | v114A | `results/market_radar_v114a_whale_position_baseline_snapshot_result.json` | 10 | ✅ passed |
| Second Probe Delta Compare | v114B | `results/market_radar_v114b_whale_delta_compare_result.json` | 10 | ✅ passed |
| Operator Review Pack | v114C | `results/market_radar_v114c_whale_delta_operator_review_pack_result.json` | 10 | ✅ passed |
| **Seal** | **v114D** | `results/market_radar_v114d_whale_delta_review_pack_seal_result.json` | — | ✅ passed |

---

## 数量一致性检查

| 检查项 | 期望 | 实际 | 结果 |
|--------|------|------|------|
| v114A baseline records | 10 | {v114a_result.get('baseline_records_written', '?')} | ✅ |
| v114B delta records | 10 | {v114b_result.get('delta_records_written', '?')} | ✅ |
| v114C operator review cards | 10 | {v114c_result.get('operator_review_cards_written', '?')} | ✅ |
| Chain counts consistent | yes | yes | ✅ |

---

## Delta Summary

| Delta Type | Count |
|------------|-------|
| closed_position | {delta_summary['closed_position']} |
| size_changed | {delta_summary['size_changed']} |
| unchanged | {delta_summary['unchanged']} |
| new_position | {delta_summary['new_position']} |
| **Total** | **{sum(delta_summary.values())}** |

---

## Attention Summary

| Attention Level | Count |
|-----------------|-------|
| 🔴 High | {attention_summary['high']} |
| 🟡 Medium | {attention_summary['medium']} |
| 🟢 Low | {attention_summary['low']} |
| **Total** | **{sum(attention_summary.values())}** |

---

## Key Event

{btc_section}

---

## Label Confidence Summary

| Level | Count | Notes |
|-------|-------|-------|
| High | 0 | 无高置信度标签 |
| Medium | 8 | loraclexyz (7) + Matrixport Related (1) |
| Low | 2 | Unknown Hyperliquid Whale + Unknown HYPE Whale |

---

## Known Data Consistency Note

**v113D historical count mismatch exists：**
v113D legacy test 有 `total_positions_found=9` vs v114A baseline=10。
这是已知历史字段不一致（v112X 同一批数据的不同快照时点造成）。
本轮 v114D 不修改旧 seal。
不影响 v114B/v114C/v114D delta review pack。

---

## Safety Invariant Summary

| Invariant | Status |
|-----------|--------|
| external_api_called_in_this_step | ✅ False |
| eligible_for_real_send_count=0 | ✅ 0 |
| real_send_candidate_count=0 | ✅ 0 |
| tg_send_allowed_count=0 | ✅ 0 |
| prod_state_write | ✅ False |
| credentials_read | ✅ False |
| daemon_started | ✅ False |
| watcher_started | ✅ False |
| files_deleted | ✅ False |
| All routing guards false | ✅ ({v114c_result.get('operator_review_cards_written', 10)}/10 cards) |

---

## Per-Card Routing Guard Verification

所有 {v114c_result.get('operator_review_cards_written', 10)} 张 operator review cards 已验证：

| Guard | Value | All Cards |
|-------|-------|-----------|
| local_review_only | true | ✅ |
| operator_action | review_only_no_send | ✅ |
| eligible_for_real_send | false | ✅ |
| real_send_candidate | false | ✅ |
| tg_send_allowed | false | ✅ |
| prod_state_write | false | ✅ |

---

## 明确结论

| 结论 | 状态 |
|------|------|
| **local_delta_review_ready** | ✅ 确认 |
| **not_tg_send_ready** | ✅ 确认 |
| **not_prod_state_ready** | ✅ 确认 |
| **not_real_send_candidate** | ✅ 确认 |
| **not_live_passed** | ✅ 确认 |
| **not_send_ready** | ✅ 确认 |

---

## 下一步建议

本阶段 seal 完成。**不自动进入发送。**

交给 GPT 判断下一阶段：
- `gpt_decide_next_stage_after_v114d_seal`
- 可能的下一阶段：v115 策略修订、TG 路由决策、标签置信度升级等

---

## 输出文件

| 文件 | 路径 |
|------|------|
| Seal Result JSON | `{OUT_SEAL_RESULT}` |
| Manifest JSON | `{OUT_MANIFEST}` |
| Seal Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |

---

*本 seal report 仅用于本地运营审阅。不构成交易建议，不自动发送。*
"""
    save_text(OUT_REPORT, report)


# ---------------------------------------------------------------------------
# Step 10: Generate handoff
# ---------------------------------------------------------------------------
def generate_handoff(seal_result, delta_summary, attention_summary, btc_card,
                     v114a_result, v114b_result, v114c_result):
    """Generate the v114D handoff markdown."""
    btc_section = ""
    if btc_card:
        btc_section = f"""- Address: `{btc_card['address']}`
- Label: {btc_card.get('label', '?')} (confidence: {btc_card.get('label_confidence', '?')})
- Asset: {btc_card['asset']}, Side: {btc_card['side']}
- Baseline size: {btc_card.get('baseline_size', 0):,.2f}
- Classification: **closed_position** with **high_operator_attention**
- Not written as error — correctly recognized as expected behavior
"""

    handoff = f"""# v114D Handoff — Whale Delta Review Pack Seal Local Only

**Generated:** {seal_result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only

---

## What was done

1. Loaded v114A baseline ({v114a_result.get('baseline_records_written', '?')} positions), v114B delta compare ({v114b_result.get('delta_records_written', '?')} deltas), and v114C operator review pack ({v114c_result.get('operator_review_cards_written', '?')} cards).
2. Validated chain count consistency: 10 → 10 → 10.
3. Validated delta summary: closed_position=1, size_changed=5, unchanged=4, new_position=0.
4. Validated attention summary: high=1, medium=5, low=4.
5. Verified BTC short closed_position: high attention, not written as error, all guards false.
6. Verified all {v114c_result.get('operator_review_cards_written', '?')} review cards have routing guards false.
7. Generated seal result, manifest, markdown report, and handoff.
8. Stage conclusion: **local_delta_review_ready_not_send_ready**.

## Chain Counts

| Stage | Count | Source |
|-------|-------|--------|
| v114A baseline | 10 | `market_radar_v114a_whale_position_baseline_snapshot_result.json` |
| v114B deltas | 10 | `market_radar_v114b_whale_delta_compare_result.json` |
| v114C cards | 10 | `market_radar_v114c_whale_delta_operator_review_pack_result.json` |

## Delta Summary

| Type | Count |
|------|-------|
| closed_position | {delta_summary['closed_position']} |
| size_changed | {delta_summary['size_changed']} |
| unchanged | {delta_summary['unchanged']} |
| new_position | {delta_summary['new_position']} |

## Attention Summary

| Level | Count |
|-------|-------|
| High | {attention_summary['high']} |
| Medium | {attention_summary['medium']} |
| Low | {attention_summary['low']} |

## BTC Short Closed Position — Seal Status

{btc_section}
## Seal Conclusion

| Item | Status |
|------|--------|
| local_delta_review_ready | ✅ |
| not_tg_send_ready | ✅ |
| not_prod_state_ready | ✅ |
| not_real_send_candidate | ✅ |
| not_live_passed | ✅ |
| not_send_ready | ✅ |
| sealed | ✅ |
| local_only | ✅ |

## Safety Invariants Confirmed

- `external_api_called_in_this_step=false`
- `eligible_for_real_send_count=0`
- `real_send_candidate_count=0`
- `tg_send_allowed_count=0`
- `prod_state_write=false`
- `credentials_read=false`
- `daemon_started=false`
- `watcher_started=false`
- `files_deleted=false`
- All {v114c_result.get('operator_review_cards_written', '?')} routing guards verified false

## Known Data Consistency Note

v113D legacy test has `total_positions_found=9` vs v114A baseline=10.
This is a known historical field inconsistency (different snapshot timing from same v112X data).
Not modified in this step. Does not affect v114B/v114C/v114D delta review pack.

## This Stage Is NOT

- Production state
- Send-ready
- TG-eligible
- A trading signal
- A position recommendation
- Ready for external consumption
- Live passed
- Send ready

## This Stage IS

- A local-only seal on the v114A→v114B→v114C chain
- Input for the next stage (gpt_decide_next_stage_after_v114d_seal)
- Fully guarded with safety invariants
- Traceable, verifiable, reproducible

## Next Step

**gpt_decide_next_stage_after_v114d_seal**

The seal is complete. Do NOT auto-advance to TG send or production.
The next executor must decide:
1. Whether to upgrade label confidence
2. Whether to route to TG test group
3. Whether to start v115 strategy revision

---

*This handoff is for the next stage decision-maker. No action required now.*
"""
    save_text(OUT_HANDOFF, handoff)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v114D Whale Delta Review Pack Seal — Local Only")
    print("=" * 70)

    # Step 1: Load all chain inputs
    print("\n[1/9] Loading v114A/v114B/v114C chain inputs...")
    (v114a_result, v114a_positions,
     v114b_result, v114b_deltas,
     v114c_result, v114c_cards) = load_all_inputs()

    # Step 2: Validate chain counts
    print("\n[2/9] Validating chain counts...")
    chain_ok = validate_chain_counts(
        v114a_result, v114a_positions,
        v114b_result, v114b_deltas,
        v114c_result, v114c_cards)
    if not chain_ok:
        print("ERROR: Chain count validation FAILED.")
        sys.exit(1)

    # Step 3: Validate delta summary
    print("\n[3/9] Validating delta summary...")
    delta_ok, delta_summary = validate_delta_summary(v114b_deltas, v114c_cards)
    if not delta_ok:
        print("ERROR: Delta summary validation FAILED.")
        sys.exit(1)

    # Step 4: Validate attention summary
    print("\n[4/9] Validating attention summary...")
    attention_ok, attention_summary = validate_attention_summary(v114c_cards)
    if not attention_ok:
        print("ERROR: Attention summary validation FAILED.")
        sys.exit(1)

    # Step 5: Validate BTC short closed_position
    print("\n[5/9] Validating BTC short closed_position...")
    btc_ok, btc_card = validate_btc_closed_position(v114c_cards)
    if not btc_ok:
        print("ERROR: BTC closed_position validation FAILED.")
        sys.exit(1)

    # Step 6: Validate all routing guards
    print("\n[6/9] Validating all routing guards...")
    routing_ok = validate_routing_guards(v114c_cards)
    if not routing_ok:
        print("ERROR: Routing guard validation FAILED.")
        sys.exit(1)

    # Step 7: Generate seal result JSON
    print("\n[7/9] Generating seal result JSON...")
    seal_result = generate_seal_result(
        delta_summary, attention_summary, btc_ok, routing_ok,
        v114a_result, v114b_result, v114c_result)
    print(f"  Seal result -> {OUT_SEAL_RESULT}")

    # Step 8: Generate manifest JSON
    print("\n[8/9] Generating manifest JSON...")
    manifest = generate_manifest(delta_summary, attention_summary)
    print(f"  Manifest -> {OUT_MANIFEST}")

    # Step 9: Generate markdown report and handoff
    print("\n[9/9] Generating markdown report and handoff...")
    generate_markdown_report(
        seal_result, delta_summary, attention_summary, btc_card,
        v114a_result, v114b_result, v114c_result)
    print(f"  Seal report -> {OUT_REPORT}")

    generate_handoff(
        seal_result, delta_summary, attention_summary, btc_card,
        v114a_result, v114b_result, v114c_result)
    print(f"  Handoff -> {OUT_HANDOFF}")

    # Final summary
    print("\n" + "=" * 70)
    print("v114D SEAL COMPLETE")
    print(f"  Stage conclusion: {seal_result['stage_conclusion']}")
    print(f"  Chain: 10 -> 10 -> 10 [OK]")
    print(f"  Delta: closed={delta_summary['closed_position']}, "
          f"changed={delta_summary['size_changed']}, "
          f"unchanged={delta_summary['unchanged']}, "
          f"new={delta_summary['new_position']}")
    print(f"  Attention: high={attention_summary['high']}, "
          f"medium={attention_summary['medium']}, "
          f"low={attention_summary['low']}")
    print(f"  BTC closed_position sealed: {btc_ok} [OK]")
    print(f"  All routing guards: {routing_ok} [OK]")
    print(f"  External API called: {EXTERNAL_API_CALLED} [OK]")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
