# v115O Whale Workbook Preflight Report

**Generated**: 2026-06-05T09:10:22.927479+08:00

## Executive Summary

- **Total addresses checked**: 4
- **Preflight ready**: 0
- **Preflight blocked**: 4
- **Ready for gate rerun**: 0

## ⚠️ Critical Finding

**ALL 4 addresses are currently PREFLIGHT BLOCKED.**

The v115F workbook (`runs/market_radar/v115f_whale_address_audit_operator_workbook.csv`) is empty — 
all operator-managed evidence fields are blank. No address has any completed evidence.

### What This Means

- **Gate rerun is NOT permitted**: Do NOT run v115G → v115L → v115H → v115M until preflight passes.
- **TG test group is NOT accessible**: No address can enter TG test group in the current state.
- **Label upgrade is NOT possible**: All addresses lack the required evidence for any confidence upgrade.
- **Operator action required**: Fill v115F workbook fields for each address, then rerun v115O preflight.

## Required Operator Workflow

1. Open `runs/market_radar/v115f_whale_address_audit_operator_workbook.csv`
2. Fill ALL required fields for each address (see evidence collection kit at `C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115o_whale_operator_evidence_collection_kit.md`)
3. Run preflight: `python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py`
4. If preflight passes (all addresses `preflight_ready=true`), proceed to gates:
   - `python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py`
   - `python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py`
   - `python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py`
   - `python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py`

## Per-Address Preflight Results

| Address | Label | Confidence | Preflight Ready | Gate Rerun | Missing Fields |
|---------|-------|------------|-----------------|------------|----------------|
| 0x082e843a... | Unknown HYPE Whale | low | **False** | **False** | 10 |
| 0x50b309f7... | Unknown Hyperliquid Whale | low | **False** | **False** | 10 |
| 0x6c851251... | Matrixport Related | medium | **False** | **False** | 10 |
| 0x8def9f50... | loraclexyz | medium | **False** | **False** | 10 |

### Unknown HYPE Whale (`0x082e843a...`)

- **Confidence**: low
- **Action Type**: manual_attribution_required
- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**

#### Missing Required Fields (10)

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Recommended Next Step

Operator must fill ALL missing workbook fields (10 missing) in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before re-running preflight. Do NOT rerun gates until preflight passes.

### Unknown Hyperliquid Whale (`0x50b309f7...`)

- **Confidence**: low
- **Action Type**: manual_attribution_required
- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**

#### Missing Required Fields (10)

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Recommended Next Step

Operator must fill ALL missing workbook fields (10 missing) in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before re-running preflight. Do NOT rerun gates until preflight passes.

### Matrixport Related (`0x6c851251...`)

- **Confidence**: medium
- **Action Type**: corroboration_required
- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**

#### Missing Required Fields (10)

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Recommended Next Step

Operator must fill ALL missing workbook fields (10 missing) in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before re-running preflight. Do NOT rerun gates until preflight passes.

### loraclexyz (`0x8def9f50...`)

- **Confidence**: medium
- **Action Type**: corroboration_required
- **Preflight Ready**: **False**
- **Ready for Gate Rerun**: **False**

#### Missing Required Fields (10)

- `trusted_source_label_value`
- `trusted_source_url_or_note`
- `second_source_label_value`
- `second_source_url_or_note`
- `activity_pattern_note`
- `operator_confirmed_label`
- `operator_confidence_assessment`
- `reviewer`
- `reviewed_at`
- `ready_for_upgrade`

#### Recommended Next Step

Operator must fill ALL missing workbook fields (10 missing) in C:\Users\PC\Desktop\Projects\事件情报系统\runs\market_radar\v115f_whale_address_audit_operator_workbook.csv before re-running preflight. Do NOT rerun gates until preflight passes.
