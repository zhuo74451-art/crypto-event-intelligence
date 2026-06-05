# v112X Recovery Handoff — For Next Executor

**Version:** v112X-recovery
**Status:** partial_not_live
**Decision:** NOT_EXECUTED_LOCAL_RECOVERY_ONLY
**Generated:** 2026-06-05T04:59:04.397523+08:00

## Purpose of This Handoff

This handoff provides the next executor with everything needed to execute the
**real v112X HyperLiquid one-shot read-only dry-run**. The recovery step has
restored all local contract artifacts but has NOT performed any live work.

## What Was Restored

1. **Recovery Result JSON** → `results/market_radar_v112x_recovery_local_contract_result.json`
   - Status: partial_not_live
   - All safety flags: false (no live work done)
   - All v112W references loaded: true

2. **Stop Decision JSON** → `results/market_radar_v112x_recovery_stop_decision.json`
   - Decision: NOT_EXECUTED_LOCAL_RECOVERY_ONLY
   - Stop conditions NOT evaluated (deferred to real v112X)

3. **Run Report** → `runs/market_radar/v112x_recovery_local_contract.md`
4. **Handoff** → `runs/market_radar/v112x_recovery_local_contract_handoff.md`

## Ready for Real v112X Execution

The following v112W artifacts are loaded and verified:

### Stop Conditions (v1.12-w)
- Decision modes: ['CONTINUE', 'ABORT', 'DEGRADE_TO_MOCK']
- Default decision: ABORT
- ABORT conditions: 11
- DEGRADE conditions: 8
- CONTINUE conditions: 8
- Invariants enforced: eligible_for_real_send always false, no production writes, no TG send, no API key.

### Field Mapping (v1.12-w)
- Planned source: hyperliquid_info_public
- Endpoint: POST https://api.hyperliquid.xyz/info
- Request type: clearinghouseState
- API key required: False
- Authorization header required: False
- Method: True (POST, read-only)
- Required fields: 10
- Optional fields: 6

### Tracked Addresses
  - `0x6c8512516ce5669d35113a11ca8b8de322fd84f6` → Matrixport Related (fund_wallet, medium)
  - `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae` → loraclexyz (high_leverage_trader, medium)
  - `0x082e843a431aef031264dc232693dd710aedca88` → Unknown HYPE Whale (unknown_whale, low)
  - `0x50b309f78e774a756a2230e1769729094cac9f20` → Unknown Hyperliquid Whale (unknown_whale, low)


### Label Quality Audit (v1.12-w)
- Total addresses: 4
- High confidence: 0
- Medium confidence: 2
- Low confidence: 2
- Ready for one-shot plan: True

### Plan Result (v1.12-w)
- Status: passed
- Whale position plan ready: True
- v112X requires user confirmation: True

## What the Next Executor Must Do

### Real v112X One-Shot Dry-Run

1. **Confirm** that the user has explicitly approved the HyperLiquid API call.
2. **Make POST requests** to `https://api.hyperliquid.xyz/info` with:
   ```json
   {"type": "clearinghouseState", "user": "<tracked_address>"}
   ```
   for each of the 4 tracked addresses.
3. **Apply stop conditions** from `config/market_radar_v112w_hyperliquid_stop_conditions.json`.
4. **Apply field mapping** from `config/market_radar_v112w_whale_position_field_mapping.json`.
5. **Apply adapter spec** from `schemas/market_radar_v112w_hl_to_whale_adapter_spec.md`.
6. **Generate v112F-compatible whale events** with all safety invariants enforced.
7. **Write complete AI_RELAY_EXECUTOR_RESULT_V1** to the executor outbox.

### Invariants for Real v112X

- `eligible_for_real_send` MUST remain `false`.
- `data_mode` MUST be `"live_like_planned"` (NOT `"live"`, NOT `"production"`).
- No TG send function may be called.
- No production state file may be written.
- No credentials, keys, or auth tokens may be read or sent.
- The HyperLiquid endpoint is public and free — no API key is needed.

### Stop Condition Flow

1. Check ABORT conditions first. If any match → stop immediately.
2. Check DEGRADE_TO_MOCK conditions. If any match → proceed with degraded quality.
3. If all clear → CONTINUE (but still eligible_for_real_send=false).

## Safety Checklist for Next Executor

- [ ] User has explicitly confirmed the v112X one-shot dry-run.
- [ ] No API keys, tokens, or credentials are read or sent.
- [ ] HyperLiquid request is POST + read-only (no state mutation).
- [ ] Stop conditions are evaluated before any signal generation.
- [ ] eligible_for_real_send is always false.
- [ ] No TG messages are sent.
- [ ] No production state is written.
- [ ] Complete AI_RELAY_EXECUTOR_RESULT_V1 is written to outbox.

## What This Recovery Did NOT Do

- ❌ Did NOT call HyperLiquid API.
- ❌ Did NOT call any external API.
- ❌ Did NOT call any external AI service.
- ❌ Did NOT send Telegram messages.
- ❌ Did NOT write production state.
- ❌ Did NOT start any daemon / cron / loop.
- ❌ Did NOT read any credentials, keys, tokens, or passwords.
- ❌ Did NOT delete any files.
- ❌ Did NOT disguise local recovery as live dry-run passed.
