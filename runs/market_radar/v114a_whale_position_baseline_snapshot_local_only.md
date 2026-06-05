# v114A Whale Position Baseline Snapshot — Local Only

**Generated:** 2026-06-05T06:01:47.619609+08:00
**Status:** passed
**Version:** v114A

---

## Purpose

This is a **local-only** baseline snapshot of 10 whale positions derived from the
v112X HyperLiquid one-shot live response. It is intentionally:

- **NOT production state**
- **NOT send-ready**
- **NOT eligible for Telegram delivery**

Its sole purpose is to serve as a **comparison baseline** for the next read-only
one-shot probe (v114B), enabling position delta computation.

---

## Input Sources

| Source | File | Status |
|--------|------|--------|
| Live Response | `market_radar_v112x_hyperliquid_live_response.json` | read |
| Stop Decision | `market_radar_v112x_hyperliquid_stop_decision.json` | read |
| Seal Result | `market_radar_v113d_degraded_whale_review_pack_seal_result.json` | read |

### v112X Stop Decision
- **Decision:** `DEGRADE_TO_MOCK`
- **Reason:** degraded label confidence + missing liquidation prices + no previous position history

### v113D Seal
- **Sealed:** `True`
- **Stage Conclusion:** `local_operator_review_ready_not_send_ready`

---

## Baseline Summary

| Metric | Value |
|--------|-------|
| Positions loaded | 10 |
| Baseline records written | 10 |
| Unique addresses | 4 |
| Unique addresses count | 4 |
| Future delta ready | True |

### Label Confidence Distribution

| Level | Count |
|-------|-------|
| High | 0 |
| Medium | 8 |
| Low | 2 |

### Liquidation Price Availability

| Status | Count |
|--------|-------|
| Available | 3 |
| Null / Unavailable | 7 |

---

## Address Summary

### 0x6c8512516ce5669d35113a11ca8b8de322fd84f6
- **Label:** Matrixport Related
- **Label Confidence:** medium
- **Positions:** ETH

### 0x8def9f50456c6c4e37fa5d3d57f108ed23992dae
- **Label:** loraclexyz
- **Label Confidence:** medium
- **Positions:** WLD, TON, NEAR, HYPE, ASTER, ZEC, XMR

### 0x082e843a431aef031264dc232693dd710aedca88
- **Label:** Unknown HYPE Whale
- **Label Confidence:** low
- **Positions:** HYPE

### 0x50b309f78e774a756a2230e1769729094cac9f20
- **Label:** Unknown Hyperliquid Whale
- **Label Confidence:** low
- **Positions:** BTC

## Baseline Positions

| Address | Label | Confidence | Asset | Side | Size | Liquidation Price |
|---------|-------|------------|-------|------|------|-------------------|
| 0x6c851251...fd84f6 | Matrixport Related | medium | ETH | long | 70,796,000.00 | 1365.991167 |
| 0x8def9f50...992dae | loraclexyz | medium | WLD | long | 5,016,032.37 | null |
| 0x8def9f50...992dae | loraclexyz | medium | TON | long | 3,214,680.84 | null |
| 0x8def9f50...992dae | loraclexyz | medium | NEAR | long | 2,048,335.25 | null |
| 0x8def9f50...992dae | loraclexyz | medium | HYPE | long | 8,985,121.56 | null |
| 0x8def9f50...992dae | loraclexyz | medium | ASTER | long | 2,352,761.69 | null |
| 0x8def9f50...992dae | loraclexyz | medium | ZEC | long | 4,496,061.81 | null |
| 0x8def9f50...992dae | loraclexyz | medium | XMR | long | 2,408,324.90 | null |
| 0x082e843a...edca88 | Unknown HYPE Whale | low | HYPE | long | 90,762,645.66 | 55.010805 |
| 0x50b309f7...ac9f20 | Unknown Hyperliquid Whale | low | BTC | short | 14,070,275.76 | 86953.672441 |

---

## Safety Invariants

| Invariant | Value |
|-----------|-------|
| local_baseline_only | True |
| prod_state_write | False |
| eligible_for_real_send_count | 0 |
| tg_send_allowed_count | 0 |
| real_send_candidate_count | 0 |
| external_api_called | False |
| credentials_read | False |
| daemon_started | False |
| watcher_started | False |
| files_deleted | False |

---

## Baseline Limitations

- local baseline only
- not production state
- not send ready
- label confidence may be medium_or_low
- liquidation price may be unavailable

---

## Next Step

**v114B:** Whale second probe delta compare (read-only).
- Must be one-shot, read-only, no API key, no TG, no prod state, no daemon.
- Compares a new read-only probe against this baseline to compute position deltas.

---

## Output Files

| File | Path |
|------|------|
| Positions JSONL | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114a_whale_position_baseline_positions.jsonl` |
| Snapshot JSON | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114a_whale_position_baseline_snapshot.json` |
| Result JSON | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114a_whale_position_baseline_snapshot_result.json` |
| Report MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v114a_whale_position_baseline_snapshot_local_only.md` |
| Handoff MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v114a_whale_position_baseline_snapshot_local_only_handoff.md` |
