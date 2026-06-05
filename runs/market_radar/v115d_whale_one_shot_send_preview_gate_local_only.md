# v115D Whale One-Shot Send Preview Gate — Local Only

**Generated:** 2026-06-05T07:05:11.230361+08:00
**Stage:** v115d_whale_one_shot_send_preview_gate_local_only
**Input Stage:** v115C (TG test copy templates) + v115B (send preview gate policy)

---

## 1. Purpose

This is a **local-only one-shot send preview gate** step. It reads v115C TG test
copy templates and generates one-shot send preview records with full payload hash,
no-repeat key, cooldown key, and gate decisions.

**ALL previews are BLOCKED** because high confidence labels = 0. No real send
candidate is generated. No TG send occurs.

---

## 2. Inputs

| Input | Source |
|-------|--------|
| TG test copy templates | v115C (4 templates) |
| Send preview gate policy | v115B |
| Label confidence routing policy | v115B |
| Rollback/cooldown policy | v115B |

---

## 3. Preview Records Summary

| Preview ID | Address | Label | Confidence | Delta | Gate | Block Reasons |
|------------|---------|-------|-----------|-------|------|---------------|
| `v115d_pvw_001` | `0x082e843a431a...` | Unknown HYPE Whale | **low** | size_changed | ❌ BLOCKED | LABEL_CONFIDENCE_BELOW_HIGH, OPERATOR_APPROVAL_MISSING, TG_SEND_DISABLED_BY_DEFAULT, ... (7 total) |
| `v115d_pvw_002` | `0x50b309f78e77...` | Unknown Hyperliquid Whale | **low** | closed_position | ❌ BLOCKED | LABEL_CONFIDENCE_BELOW_HIGH, OPERATOR_APPROVAL_MISSING, TG_SEND_DISABLED_BY_DEFAULT, ... (7 total) |
| `v115d_pvw_003` | `0x6c8512516ce5...` | Matrixport Related | **medium** | unchanged | ❌ BLOCKED | LABEL_CONFIDENCE_BELOW_HIGH, OPERATOR_APPROVAL_MISSING, TG_SEND_DISABLED_BY_DEFAULT, ... (5 total) |
| `v115d_pvw_004` | `0x8def9f50456c...` | loraclexyz | **medium** | size_changed | ❌ BLOCKED | LABEL_CONFIDENCE_BELOW_HIGH, OPERATOR_APPROVAL_MISSING, TG_SEND_DISABLED_BY_DEFAULT, ... (5 total) |


---

## 4. Payload Hash & Keys

| Preview ID | Payload Hash | No-Repeat Key | Cooldown Key |
|------------|-------------|---------------|--------------|
| `v115d_pvw_001` | `e64301d040c11b2c...` | `0x082e843a431aef031264dc232693dd710aedca88_HYPE_long_size_ch...` | `0x082e843a431aef031264dc232693dd710aedca88_HYPE_20...` |
| `v115d_pvw_002` | `a8e637e9dc0c9858...` | `0x50b309f78e774a756a2230e1769729094cac9f20_BTC_short_closed_...` | `0x50b309f78e774a756a2230e1769729094cac9f20_BTC_202...` |
| `v115d_pvw_003` | `af7f2c63507ee96c...` | `0x6c8512516ce5669d35113a11ca8b8de322fd84f6_ETH_long_unchange...` | `0x6c8512516ce5669d35113a11ca8b8de322fd84f6_ETH_202...` |
| `v115d_pvw_004` | `4f83318b1e6884ee...` | `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae_ZEC_long_size_cha...` | `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae_ZEC_202...` |


**All payload hashes are SHA-256 of:** `copy_text + address + asset + delta_type + scope`

**No-repeat key format:** `{address}_{asset}_{side}_{delta_type}_{date}`

**Cooldown key format:** `{address}_{asset}_{date}`

---

## 5. Gate Decision Block Reasons (per preview)

All 4 previews are blocked with at least:
- `LABEL_CONFIDENCE_BELOW_HIGH`
- `OPERATOR_APPROVAL_MISSING`
- `TG_SEND_DISABLED_BY_DEFAULT`
- `NOT_SEND_READY`

Low confidence / unknown whale previews additionally include:
- `UNKNOWN_WHALE_NOT_SENDABLE`
- `LABEL_UPGRADE_REQUIRED`

---

## 6. Result Summary

| Metric | Value |
|--------|-------|
| Input templates | 4 |
| Preview records | 4 |
| Gate decisions | 4 |
| sendable_previews | ❌ `0` |
| blocked_previews | 🛑 `4` |
| unique_payload_hashes | `4` |
| duplicate_payload_hashes | `0` |
| send_ready | ❌ `False` |
| tg_test_group_ready | ❌ `False` |
| local_review_ready | ✅ `True` |

---

## 7. Safety Invariants

| Invariant | Status |
|-----------|--------|
| external_api_called | ✅ `False` |
| ai_model_called | ✅ `False` |
| credentials_read | ✅ `False` |
| tg_sent | ✅ `False` |
| prod_state_write | ✅ `False` |
| daemon_started | ✅ `False` |
| watcher_started | ✅ `False` |
| files_deleted | ✅ `False` |
| real_send_candidate_generated | ✅ `False` |

---

## 8. Explicit NOT Declarations

This stage is explicitly **NOT**:

- ❌ A TG send
- ❌ Send-ready for production
- ❌ TG-test-group-ready
- ❌ A trading signal
- ❌ Financial advice
- ❌ Production state
- ❌ A real send candidate

This stage **IS**:

- ✅ One-shot send preview gate generation (local only)
- ✅ Full payload hash, no-repeat key, cooldown key computation
- ✅ Gate decision with explicit block reasons
- ✅ Fully guarded with safety invariants
- ✅ Traceable, verifiable, reproducible

---

## 9. Output Files

| File | Path |
|------|------|
| Preview Records JSONL | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v115d_whale_one_shot_send_preview_records.jsonl` |
| Gate Decisions JSONL | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl` |
| Result JSON | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v115d_whale_one_shot_send_preview_gate_result.json` |
| Report MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115d_whale_one_shot_send_preview_gate_local_only.md` |
| Handoff MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115d_whale_one_shot_send_preview_gate_local_only_handoff.md` |

---

*This report is for local operator review only. No external communication intended.*
