# Market Radar v1.13-B — Degraded Whale Preview Quality Gate Report

**Generated at**: 2026-06-05T05:56:53.317404+08:00
**Version**: v113B
**Status**: passed

## Summary

- **Input preview cards loaded**: 10
- **Quality decisions generated**: 10
- **operator_preview_ready**: 10
- **review_only**: 0
- **blocked**: 0

## Safety Invariants

- eligible_for_real_send_count: **0**
- real_send_candidate_count: **0**
- tg_send_allowed_count: **0**
- prod_state_write: **False**
- external_api_called: **False**
- credentials_read: **False**
- daemon_started: **False**
- watcher_started: **False**
- files_deleted: **False**

## Decision Distribution

| Decision | Count |
|----------|-------|
| operator_preview_ready | 10 |
| review_only | 0 |
| blocked | 0 |
| **Total** | **10** |

## Label Confidence Distribution

| Confidence | Count |
|------------|-------|
| low | 2 |
| medium | 8 |

## Gate Check Results

| Gate | Pass | Fail |
|------|------|------|
| safety_routing_gate | 10 | 0 |
| degraded_disclosure_gate | 10 | 0 |
| label_confidence_gate | 10 | 0 |
| misleading_wording_gate | 10 | 0 |
| preview_usability_gate | 10 | 0 |

## Warning Distribution

| Warning | Count |
|---------|-------|
| 标签置信度不足 | 10 |
| 单次快照，暂无法计算仓位变化 | 10 |
| 使用本地观察时间，非 HyperLiquid 服务端时间 | 10 |
| 清算价格不可用 | 7 |

## Blocking Reasons Distribution

No blocking reasons — all cards passed quality gates.

## Per-Card Decision Details

### Card 0: ETH — Matrixport Related
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 1: WLD — loraclexyz
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 2: TON — loraclexyz
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 3: NEAR — loraclexyz
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 4: HYPE — loraclexyz
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 5: ASTER — loraclexyz
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 6: ZEC — loraclexyz
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 7: XMR — loraclexyz
- **Decision**: `operator_preview_ready`
- **Label confidence**: `medium`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 8: HYPE — Unknown HYPE Whale
- **Decision**: `operator_preview_ready`
- **Label confidence**: `low`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

### Card 9: BTC — Unknown Hyperliquid Whale
- **Decision**: `operator_preview_ready`
- **Label confidence**: `low`
- **Gate checks**:
  - ✅ safety_routing_gate: pass
  - ✅ degraded_disclosure_gate: pass
  - ✅ label_confidence_gate: pass
  - ✅ misleading_wording_gate: pass
  - ✅ preview_usability_gate: pass

## Missing Warning Analysis

- Cards with null liquidation_price: 7
- Of those, missing '清算价格不可用' warning: 0
- Cards with delta unavailable: 10
- Cards with local timestamp: 10

## Eligibility Check Summary

- all_degraded_disclosures_checked: **True**
- label_confidence_checked: **True**
- misleading_wording_checked: **True**

## Next Steps

- **Recommended next step**: v113c_degraded_whale_operator_review_pack_local_only
- ✅ `operator_preview_ready_count > 0`: proceed to v113C degraded whale operator review pack (local-only)

---
*Report generated at 2026-06-05T05:56:53.317404+08:00*