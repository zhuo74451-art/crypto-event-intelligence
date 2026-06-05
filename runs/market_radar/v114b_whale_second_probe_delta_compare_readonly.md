# v114B Whale Second Probe Delta Compare — Read-Only

**Generated:** 2026-06-05T06:09:20.972923+08:00
**Status:** passed
**Version:** v114B

---

## Purpose

Second read-only HyperLiquid probe compared against v114A local baseline.
Computes position deltas (new / closed / size_changed / unchanged) without
any production writes, TG sends, or daemon processes.

---

## Input Sources

| Source | File | Status |
|--------|------|--------|
| v114A Baseline Snapshot | `market_radar_v114a_whale_position_baseline_snapshot.json` | read |
| v114A Baseline Positions | `market_radar_v114a_whale_position_baseline_positions.jsonl` | read |
| HyperLiquid Public API | `POST api.hyperliquid.xyz/info` | 4/4 success |

---

## Probe Results

| Metric | Value |
|--------|-------|
| Baseline records loaded | 10 |
| Addresses requested | 4 |
| Second probe success | 4 |
| Second probe failure | 0 |
| External API called | True |
| API key used | False |
| Authorization header used | False |
| Credentials read | False |
| Retry count | 0 |

### Requested Addresses

- `0x6c8512516ce5669d35113a11ca8b8de322fd84f6` — Matrixport Related — success — 1 positions
- `0x8def9f50456c6c4e37fa5d3d57f108ed23992dae` — loraclexyz — success — 7 positions
- `0x082e843a431aef031264dc232693dd710aedca88` — Unknown HYPE Whale — success — 1 positions
- `0x50b309f78e774a756a2230e1769729094cac9f20` — Unknown Hyperliquid Whale — success — 0 positions

---

## Delta Summary

| Metric | Value |
|--------|-------|
| Delta records written | 10 |
| New positions | 0 |
| Closed positions | 1 |
| Size changed | 5 |
| Unchanged | 4 |
| Entry price changed | 0 |

### Per-Address Summary

| Address | Total Deltas | New | Closed | Changed | Unchanged |
|---------|-------------|-----|--------|---------|-----------|
| 0x6c851251...fd84f6 | 1 | 0 | 0 | 0 | 1 |
| 0x8def9f50...992dae | 7 | 0 | 0 | 4 | 3 |
| 0x082e843a...edca88 | 1 | 0 | 0 | 1 | 0 |
| 0x50b309f7...ac9f20 | 1 | 0 | 1 | 0 | 0 |

---

## Label Confidence Summary

| Level | Count |
|-------|-------|
| High | 0 |
| Medium | 8 |
| Low | 2 |

**Note:** Label confidence preserved from v114A baseline audit. No confidence upgrades applied.

### Liquidation Price Availability

| Status | Count |
|--------|-------|
| Available | 3 |
| Null / Unavailable | 7 |

---

## Delta Records

| Address | Label | Confidence | Asset | Side | Type | Baseline Size | Current Size | Delta | Entry Price Changed |
|---------|-------|------------|-------|------|------|---------------|--------------|-------|---------------------|
| 0x8def9f50...992dae | loraclexyz | medium | WLD | long | size_changed | 5,016,032.37 | 4,946,543.25 | -69,489.12 | No |
| 0x50b309f7...ac9f20 | Unknown Hyperliquid Whale | low | BTC | short | closed_position | 14,070,275.76 | 0.00 | -14,070,275.76 | No |
| 0x8def9f50...992dae | loraclexyz | medium | TON | long | size_changed | 3,214,680.84 | 3,117,369.73 | -97,311.11 | No |
| 0x6c851251...fd84f6 | Matrixport Related | medium | ETH | long | unchanged | 70,796,000.00 | 70,360,000.00 | -436,000.00 | No |
| 0x8def9f50...992dae | loraclexyz | medium | NEAR | long | unchanged | 2,048,335.25 | 2,029,861.38 | -18,473.87 | No |
| 0x8def9f50...992dae | loraclexyz | medium | ASTER | long | unchanged | 2,352,761.69 | 2,342,259.41 | -10,502.28 | No |
| 0x8def9f50...992dae | loraclexyz | medium | ZEC | long | size_changed | 4,496,061.81 | 4,290,266.40 | -205,795.41 | No |
| 0x082e843a...edca88 | Unknown HYPE Whale | low | HYPE | long | size_changed | 90,762,645.66 | 89,683,452.30 | -1,079,193.36 | No |
| 0x8def9f50...992dae | loraclexyz | medium | HYPE | long | size_changed | 8,985,121.56 | 8,878,285.94 | -106,835.62 | No |
| 0x8def9f50...992dae | loraclexyz | medium | XMR | long | unchanged | 2,408,324.90 | 2,421,168.27 | +12,843.37 | No |

---

## Safety Invariants

| Invariant | Value |
|-----------|-------|
| local_delta_compare_only | True |
| eligible_for_real_send (all records) | False |
| tg_send_allowed (all records) | False |
| prod_state_write | False |
| external_api_called | True |
| api_key_used | False |
| authorization_header_used | False |
| credentials_read | False |
| retry_count | 0 |
| daemon_started | False |
| watcher_started | False |
| files_deleted | False |

---

## Conclusions

- **local_delta_compare_only**: True — this is local comparison only
- **not_tg_send_ready**: All records have `tg_send_allowed=false`
- **not_prod_state_ready**: `prod_state_write=false`
- **not_real_send_candidate**: `eligible_for_real_send_count=0`

### Special Notes

- **0x50b3 BTC position**: Confirmed as closed_position (not an error). Expected behavior when position disappears between probes.

---

## Next Step

**v114C:** Whale delta operator review pack — local-only.
- Review all 10 delta records
- Validate classifications
- Prepare operator review cards
- No TG send, no prod state, no daemon

---

## Output Files

| File | Path |
|------|------|
| Second Probe Live Response | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114b_whale_second_probe_live_response.json` |
| Delta Compare Result | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114b_whale_delta_compare_result.json` |
| Delta Records JSONL | `C:\Users\PC\Desktop\Projects\事件情报系统\results\market_radar_v114b_whale_position_deltas.jsonl` |
| Report MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v114b_whale_second_probe_delta_compare_readonly.md` |
| Handoff MD | `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v114b_whale_second_probe_delta_compare_readonly_handoff.md` |
