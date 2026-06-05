# Market Radar v1.12-N — Local Master Dry-Run Orchestrator Report

**Generated**: 2026-06-05 04:13:19 UTC+8
**Version**: v1.12-N
**Run ID**: 20260605_022952
**Status**: PASSED

---

## 概述

本报告证明 v112N local master dry-run orchestrator 成功顺序执行了
全部 8 个 pipeline 步骤，形成完整 dry-run 闭环：

```
5 类固定卡片 → 13 统一信封 → 13 gate 决策 → 9 eligible + 4 blocked
    → 9 canonical state entries → 9/9 reblocked on replay
    → idempotency verified + deterministic clock confirmed
```

本任务未连接外部 API、未发送 TG、未启动 daemon/loop/cron。
所有数据来自本地 fixture 和前置步骤产物。

---

## Pipeline 步骤执行结果

| # | Step | Status | Duration (s) | Exit | Key Metrics |
|---|------|--------|-------------|------|-------------|
| 1 | v1.12-E All Fixed Card Local Pipeline | ✅ passed | 0.1 | 0 | card_type_count=5, missing_count=0, partial_count=4 |
| 2 | v1.12-F Whale Position Local Enrichment | ✅ passed | 0.1 | 0 | blocked_signal_count=2, public_card_count=6, valid_signal_count=6 |
| 3 | v1.12-G Multi-Asset Sync Local Correlation | ✅ passed | 0.1 | 0 | blocked_signal_count=3, public_card_count=5, valid_signal_count=5 |
| 4 | v1.12-H Unified Signal Envelope | ✅ passed | 0.1 | 0 | all_envelopes_valid=True, total_envelopes=13, unique_card_types=5 |
| 5 | v1.12-I Dedupe + Cooldown Gate (v112m deterministic clock) | ✅ passed | 0.1 | 0 | blocked_cooldown_count=2, blocked_dedupe_count=2, decision_count=13 |
| 6 | v1.12-J Eligible Signal Pack + State Dry-run | ✅ passed | 0.1 | 0 | blocked_signal_count=4, eligible_signal_count=9 |
| 7 | v1.12-L Canonical State Key Hardening | ✅ passed | 0.1 | 0 | canonical_state_all_match=True, canonical_state_entry_count=9 |
| 8 | v1.12-K State Replay + Idempotency (canonical path) | ✅ passed | 0.1 | 0 | first_pass_eligible_reblocked_count=9, idempotency_passed=True, unexpected_repass_signal_ids=[] |

**Steps**: 8/8 passed

---

## 核心指标汇总

| 指标 | 值 | 来源 |
|------|-----|------|
| version | v1.12-N | master |
| status | passed | master |
| fixed_card_types_total | 5 | v112E |
| signal_envelope_count | 13 | v112H |
| gate_decision_count | 13 | v112I |
| eligible_signal_count | 9 | v112J |
| blocked_signal_count | 4 | v112J |
| canonical_state_entry_count | 9 | v112L |
| first_pass_eligible_reblocked | 9 | v112K |
| unexpected_repass_signal_ids | [] | v112K |
| idempotency_passed | True | v112K |
| deterministic_clock | True | v112I (v112M) |
| evaluated_at | 2026-06-04T22:30:00+08:00 | v112I (v112M) |
| time_dependent_test_risk | False | v112I (v112M) |
| debug_leak_count | 0 | master |
| secret_leak_count | 0 | master |

---

## 每步输入/输出文件

### v1.12-E All Fixed Card Local Pipeline

- **Script**: `scripts/run_market_radar_v112e_all_fixed_card_local_pipeline.py`
- **Status**: passed
- **Duration**: 0.11s

**Expected output files**:
- ✅ `results/market_radar_v112e_all_fixed_card_local_pipeline_result.json`
- ✅ `runs/market_radar/v112e_all_fixed_card_local_pipeline.md`
- ✅ `runs/market_radar/v112e_all_fixed_card_local_pipeline_handoff.md`

### v1.12-F Whale Position Local Enrichment

- **Script**: `scripts/run_market_radar_v112f_whale_position_local_enrichment.py`
- **Status**: passed
- **Duration**: 0.08s

**Expected output files**:
- ✅ `results/market_radar_v112f_whale_position_local_enrichment_result.json`
- ✅ `runs/market_radar/v112f_whale_position_local_enrichment.md`
- ✅ `runs/market_radar/v112f_whale_position_local_enrichment_handoff.md`

### v1.12-G Multi-Asset Sync Local Correlation

- **Script**: `scripts/run_market_radar_v112g_multi_asset_sync_local_correlation.py`
- **Status**: passed
- **Duration**: 0.06s

**Expected output files**:
- ✅ `results/market_radar_v112g_multi_asset_sync_local_correlation_result.json`
- ✅ `runs/market_radar/v112g_multi_asset_sync_local_correlation.md`
- ✅ `runs/market_radar/v112g_multi_asset_sync_local_correlation_handoff.md`

### v1.12-H Unified Signal Envelope

- **Script**: `scripts/run_market_radar_v112h_unified_signal_envelope.py`
- **Status**: passed
- **Duration**: 0.11s

**Expected output files**:
- ✅ `results/market_radar_v112h_unified_signal_envelope_result.json`
- ✅ `results/market_radar_v112h_unified_signal_envelopes.jsonl`
- ✅ `runs/market_radar/v112h_unified_signal_envelope.md`
- ✅ `runs/market_radar/v112h_unified_signal_envelope_handoff.md`

### v1.12-I Dedupe + Cooldown Gate (v112m deterministic clock)

- **Script**: `scripts/run_market_radar_v112i_dedupe_cooldown_gate.py`
- **Status**: passed
- **Duration**: 0.08s

**Expected output files**:
- ✅ `results/market_radar_v112i_dedupe_cooldown_gate_result.json`
- ✅ `results/market_radar_v112i_gate_decisions.jsonl`
- ✅ `runs/market_radar/v112i_dedupe_cooldown_gate.md`
- ✅ `runs/market_radar/v112i_dedupe_cooldown_gate_handoff.md`

### v1.12-J Eligible Signal Pack + State Dry-run

- **Script**: `scripts/run_market_radar_v112j_eligible_signal_pack_and_state_dryrun.py`
- **Status**: passed
- **Duration**: 0.08s

**Expected output files**:
- ✅ `results/market_radar_v112j_eligible_signal_pack_result.json`
- ✅ `results/market_radar_v112j_eligible_signals.jsonl`
- ✅ `results/market_radar_v112j_blocked_signals.jsonl`
- ✅ `results/market_radar_v112j_proposed_signal_state.json`
- ✅ `runs/market_radar/v112j_eligible_signal_pack.md`
- ✅ `runs/market_radar/v112j_eligible_signal_pack_handoff.md`

### v1.12-L Canonical State Key Hardening

- **Script**: `scripts/run_market_radar_v112l_canonical_state_key_hardening.py`
- **Status**: passed
- **Duration**: 0.09s

**Expected output files**:
- ✅ `results/market_radar_v112l_canonical_state_key_hardening_result.json`
- ✅ `results/market_radar_v112l_canonical_prior_state.json`
- ✅ `results/market_radar_v112l_state_key_audit.jsonl`
- ✅ `runs/market_radar/v112l_canonical_state_key_hardening.md`
- ✅ `runs/market_radar/v112l_canonical_state_key_hardening_handoff.md`

### v1.12-K State Replay + Idempotency (canonical path)

- **Script**: `scripts/run_market_radar_v112k_state_replay_idempotency.py`
- **Status**: passed
- **Duration**: 0.09s

**Expected output files**:
- ✅ `results/market_radar_v112k_state_replay_idempotency_result.json`
- ✅ `results/market_radar_v112k_replay_gate_decisions.jsonl`
- ✅ `runs/market_radar/v112k_state_replay_idempotency.md`
- ✅ `runs/market_radar/v112k_state_replay_idempotency_handoff.md`

---

## 安全边界确认

| 约束 | 状态 |
|------|------|
| dry_run_only | True |
| live_ready | False |
| real_tg_sent | False |
| external_api_called | False |
| external_ai_called | False |
| daemon_started | False |
| files_deleted | False |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| token/key/cookie read | false |
| ai_relay_desk writes | false |

---

## 是否可进入下一阶段

✅ **PASSED — 可以进入下一阶段。**

所有 8 步全部通过，核心指标与预期一致：
- 5 card types → 13 envelopes → 9 eligible + 4 blocked
- 9 canonical state entries
- 9/9 reblocked on replay (idempotency verified)
- Deterministic clock confirmed
- 0 debug leaks, 0 secret leaks

下一步建议：send preview pack 或 live source readiness audit，二选一。

---

*Generated by v1.12-N at 2026-06-05 04:13:19 UTC+8*