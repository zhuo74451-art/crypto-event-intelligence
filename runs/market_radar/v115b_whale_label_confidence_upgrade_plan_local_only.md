# v115B Whale Label Confidence Upgrade Plan — Local Only

**Generated:** 2026-06-05T06:41:34.875062+08:00
**Status:** passed
**Version:** v115B
**Input Stage:** v115A (send-readiness strategy gate)

---

## 1. Purpose

This is a **local policy design** step, NOT a send step. It translates the
6 blockers identified in v115A into executable local policy packages.

**No external APIs, no TG send, no production state write, no label changes.**

---

## 2. v115A Blockers Recap

The v115A send-readiness strategy gate identified **6 blockers** preventing
TG test group entry:

| # | Blocker ID | Severity | Addressed in v115B |
|---|-----------|----------|--------------------|
| 1 | LABEL_CONFIDENCE_NO_HIGH | HIGH | ✅ Routing policy + upgrade targets |
| 2 | LOW_CONFIDENCE_UNKNOWN_WHALES | HIGH | ✅ Policy denies routing, upgrade targets flagged |
| 3 | REVIEW_ONLY_NO_SEND | HIGH | ⏳ Acknowledged — no promotion yet |
| 4 | TG_COPY_NOT_TESTED | MEDIUM | ✅ TG copy gate policy created |
| 5 | HISTORICAL_COUNT_MISMATCH_NOTE | LOW | 📝 Noted — no action required |
| 6 | NO_SEND_TEMPLATE_GATE | HIGH | ✅ Send preview gate + protections created |

---

## 3. Current Label Confidence Distribution

| Level | Count | Addresses |
|-------|-------|-----------|
| 🔴 High | **0** | — |
| 🟡 Medium | **8** | loraclexyz (7 positions) + Matrixport Related (1 position) |
| 🟠 Low | **2** | Unknown Hyperliquid Whale + Unknown HYPE Whale |

**Key fact:** Zero positions have high-confidence labels. No position can enter
TG test group under current routing policy.

---

## 4. Label Upgrade Targets (4 addresses)

| Address | Label | Confidence | Priority | Positions | Reason |
|---------|-------|-----------|----------|-----------|--------|
| `0x082e843a431aef0312...` | Unknown HYPE Whale | **low** | 🔴 HIGH | 1 | Low-confidence unknown whale. Label confidence must be upgraded before any routing.... |
| `0x50b309f78e774a756a...` | Unknown Hyperliquid Whale | **low** | 🔴 HIGH | 1 | Low-confidence unknown whale with BTC closed_position event. This is the only closed_position in the... |
| `0x6c8512516ce5669d35...` | Matrixport Related | **medium** | 🟡 MEDIUM | 1 | Medium-confidence label with 1 position(s).... |
| `0x8def9f50456c6c4e37...` | loraclexyz | **medium** | 🟡 MEDIUM | 7 | Medium-confidence label with 7 positions across multiple assets.... |


### Priority Rules Applied

- **low-confidence + closed_position → HIGH priority**
  → Unknown Hyperliquid Whale (BTC closed_position, the only closed position in pack)
- **low-confidence unknown whale → HIGH priority**
  → Unknown HYPE Whale (HYPE size_changed)
- **medium-confidence with multiple positions → MEDIUM priority**
  → loraclexyz (7 positions across ZEC, HYPE, TON, WLD, NEAR, XMR, ASTER)
- **medium-confidence single position → MEDIUM priority**
  → Matrixport Related (1 position, ETH unchanged)

---

## 5. Label Confidence Routing Policy

### Routing Rules Summary

| Confidence | Operator Review | TG Test Group | Public Send | Requires |
|-----------|----------------|---------------|-------------|----------|
| **high** | ✅ Allowed | ✅ Allowed | ❌ (future gate) | Send preview gate |
| **medium** | ✅ Allowed | ❌ | ❌ | Label upgrade |
| **low** | ✅ Allowed | ❌ | ❌ | Label upgrade + unknown warning |

### Key Design Decisions

1. **No position may enter TG test group without `label_confidence='high'`.**
   Currently high=0 — this is the primary blocker.

2. **Medium confidence may not enter TG test group.**
   Label upgrade to high is required first.

3. **Low confidence must display 'Unknown Whale' and may not enter TG.**
   Both low-confidence addresses are flagged as HIGH priority upgrade targets.

4. **Even high-confidence labels may not enter public send.**
   Public production send requires an explicit future gate (not designed yet).

5. **All sends require send preview gate passage.**
   Preview pack, no-repeat check, cooldown check, operator approval, and
   user pre-authorization must all pass.

---

## 6. TG Test Copy Gate

### Key Rules

- TG test copy **MUST NOT** reuse operator review copy (`review_summary`)
- TG test copy **must** include `[TEST-ONLY — NOT PRODUCTION]` marker
- TG test copy **must** preserve label confidence level
- Medium/low confidence **must** be explicitly downgraded
- Unknown whales **must not** be presented as confirmed entities
- Banned phrases: 确认, 实锤, 正式信号, 强信号, 可直接发布, 立即发送, etc.

### Required Elements

Every TG test copy must include:
1. `[TEST-ONLY — NOT PRODUCTION]` header
2. Source: HyperLiquid public position info, local delta compare only
3. Not financial advice / not a trading signal
4. Not production state — local review only
5. Label confidence tag
6. Address tag, asset tag, delta summary tag

---

## 7. Send Preview Gate

### Gate Requirements

Before any TG test group send:
1. ✅ One-shot preview pack generated (exact copy + metadata)
2. ✅ No-repeat key checked (dedupe: `{address}_{asset}_{side}_{delta_type}_{date}`)
3. ✅ Cooldown key checked (24h minimum: `{address}_{asset}_{date}`)
4. ✅ Payload hash computed (SHA-256 of copy + address + asset + timestamp)
5. ✅ Operator approval field explicitly set
6. ✅ User pre-authorization confirmed (TG test group only)
7. ✅ Send disabled by default — must be explicitly enabled per send

### After Send

- Record no-repeat key
- Start cooldown timer
- Record payload hash
- Do NOT auto-resend
- Do NOT retry on failure without review

---

## 8. Rollback / Cooldown / No-Repeat

### Rollback
- Manual operator action only — no automated rollback
- Triggered by: incorrect label display, banned phrase, operator error
- Procedure: post retraction → mark rolled_back in local state → document

### No-Repeat (Dedupe)
- Key format: `{address}_{asset}_{side}_{delta_type}_{date}`
- Duplicate payload hash blocking enabled
- Block on duplicate: block send and notify operator

### Cooldown
- Key format: `{address}_{asset}_{date}`
- Minimum window: **24 hours** per address+asset pair
- Cooldown check before every send

### Manual Stop
- Operator may set manual stop at any time
- All sends blocked while stopped
- Preview packs and local review still allowed
- Resume: operator explicitly clears stop flag

### No Daemon / No Loop
- **ABSOLUTE rule**: No daemon, cron, loop, timer, or auto-repeat for TG sending
- All sends are one-shot, operator-initiated, manually gated
- Non-negotiable

---

## 9. Current Conclusion

| Decision | Value | Expected |
|----------|-------|----------|
| **send_ready** | ❌ `false` | `false` ✅ |
| **tg_test_group_ready** | ❌ `false` | `false` ✅ |
| **local_review_ready** | ✅ `true` | `true` ✅ |
| eligible_for_real_send_count | `0` | 0 ✅ |
| real_send_candidate_count | `0` | 0 ✅ |
| tg_send_allowed_count | `0` | 0 ✅ |
| high-confidence labels | `0` | 0 (no change) |
| upgrade targets | `4` | ≥4 ✅ |

**Conclusion:** Policies and upgrade targets are designed and written.
All 6 v115A blockers are addressed by local policy. However, no actual label
upgrade has occurred (that requires external verification not in scope for
this local-only step). Send remains disabled.

---

## 10. Safety Invariant Status

| Invariant | Status |
|-----------|--------|
| external_api_called | ✅ `False` |
| prod_state_write | ✅ `False` |
| tg_sent | ✅ `False` |
| credentials_read | ✅ `False` |
| daemon_started | ✅ `False` |
| watcher_started | ✅ `False` |
| files_deleted | ✅ `False` |
| old results modified | ✅ No (v114A-v115A unchanged) |
| real send candidate generated | ✅ No (0 candidates) |

---

## 11. Explicit NOT Declarations

This stage is explicitly **NOT**:

- ❌ Send-ready
- ❌ TG-test-group-ready
- ❌ A TG send
- ❌ A label confidence upgrade (policies designed, upgrades NOT performed)
- ❌ Production state
- ❌ A trading signal
- ❌ Live-passed
- ❌ Ready for external consumption

This stage **IS**:

- ✅ A local-only policy design step
- ✅ Input for v115C (TG test copy template gate)
- ✅ Fully guarded with safety invariants
- ✅ Traceable, verifiable, reproducible

---

## 12. Next Step

**`v115c_whale_tg_test_copy_template_gate_local_only`**

The next executor should:
1. Design TG test copy templates using the copy gate policy from v115B
2. Generate mock TG copy for each upgrade target
3. Validate copy against banned phrases and required elements
4. Produce first draft of send-ready TG copy (still test-only, not production)

---

## 13. Output Files

| File | Path |
|------|------|
| Routing Policy | `C:\Users\PC\Desktop\Projects\事件情报系统\config\market_radar_v115b_whale_label_confidence_routing_policy.json` |
| TG Copy Gate Policy | `C:\Users\PC\Desktop\Projects\事件情报系统\config\market_radar_v115b_whale_tg_test_copy_gate_policy.json` |
| Send Preview Gate Policy | `C:\Users\PC\Desktop\Projects\事件情报系统\config\market_radar_v115b_whale_send_preview_gate_policy.json` |
| Rollback/Cooldown Policy | `C:\Users\PC\Desktop\Projects\事件情报系统\config\market_radar_v115b_whale_rollback_cooldown_policy.json` |
| Result JSON | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v115b_whale_label_confidence_upgrade_plan_result.json` |
| Upgrade Targets JSONL | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v115b_whale_label_upgrade_targets.jsonl` |
| Report MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115b_whale_label_confidence_upgrade_plan_local_only.md` |
| Handoff MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115b_whale_label_confidence_upgrade_plan_local_only_handoff.md` |

---

*This policy plan report is for local operator review only. No external communication intended.*
