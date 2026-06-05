# Market Radar v1.16-K — Next Real E2E Candidate Decision (post v116J)

**Generated**: 2026-06-05 13:37:33 UTC+8
**Version**: v1.16-K

---

## Context

After v116E (multi_asset_market_sync), v116G (price_oi_volume_anomaly), v116I (liquidation_pressure real API + gate blocked), and v116J (news_event_market_impact real public source + TG test sent), the five-card real E2E coverage status is now:

- ✅ **3/5 real API/public source + TG test sent**
  - `multi_asset_market_sync` — v116E
  - `price_oi_volume_anomaly` — v116G (ETH, SOL)
  - `news_event_market_impact` — v116J (2 cards)
- ⚠ **1/5 real API attempted but gate blocked**
  - `liquidation_pressure` — v116I (calm market, 0/3 admitted)
- ⛔ **1/5 manual evidence blocked**
  - `whale_position_alert` — manual evidence required
- ❌ **0/5 production send ready**

## Decision Framework

With 3/5 card families at real E2E + TG test sent, the remaining 2 families each have clear, well-understood blockers. The decision is not about which card to push next — it is about whether to proceed with packaging/deliverables or attempt to force progress on blocked families.

### Three Directions Compared

#### Direction A: Force liquidation_pressure re-run

- **Status**: v116I successfully fetched 3/3 assets via Binance REST,
  generated 3 signals, but 0/3 admitted (calm market gate)
- **Option**: Lower admission threshold to force 1+ signals through
- **Verdict**: ❌ NOT RECOMMENDED
- **Why**:
  - Gate correctly identified calm market — lowering threshold degrades trust
  - Would generate low-quality cards with no real liquidation signal
  - Undermines the entire quality gate design
  - Better to wait for real volatility → gate naturally opens
- **Recommendation**: Mark as `future_volatility_rerun`

#### Direction B: Force whale_position_alert unblock

- **Status**: 4 addresses have empty fields in operator workbook
- **Option**: Attempt to automate address verification or use mock data
- **Verdict**: ❌ NOT RECOMMENDED
- **Why**:
  - Real on-chain attribution cannot be automated via free APIs
  - Using mock/fabricated evidence would make cards worthless
  - Manual evidence is a hard requirement for this card type
- **Recommendation**: Open `manual_evidence_collection` task, do not auto-push

#### Direction C: v116L Milestone Packaging (RECOMMENDED)

- **Status**: 3/5 real E2E + TG test sent, clear audit trail v116A-K
- **Option**: Aggregate all v116A-K outputs into a single reviewable milestone
- **Verdict**: ✅ RECOMMENDED
- **Why**:
  - 3 card families have real, verifiable TG test send evidence
  - liquidation gate correctly blocked in calm market (validated design)
  - whale blocker is well-documented and understood
  - User can review milestone → make informed decision on next phase
  - Higher value than forcing progress on blocked families

## Recommendation

### 🥇 **v116L_market_radar_real_e2e_milestone_pack_local_only**

**Reasoning**: 当前已有 3/5 类卡片完成真实 E2E TG 测试发送（multi_asset_market_sync, price_oi_volume_anomaly, news_event_market_impact），liquidation_pressure 在真实 calm market 下被正确阻断（gate 行为符合设计意图），whale_position_alert 需要人工补证。此时做可交付成果包价值更高：汇总 v116 系列全部成果，生成可验收的 里程碑文档，让用户确认当前进度后再决定下一步投入方向。

### `liquidation_pressure`

- **Status**: real_api_attempted_but_gate_blocked
- **Recommendation**: 保留为事件触发型卡片，标记为 future volatility rerun
- **Rationale**: v116I 已证明数据管道可运行（3/3 assets fetched, signals generated），gate 在 calm market 下正确阻断 0/3 信号通过。不应降低阈值来制造发送成功 — 这会削弱 gate 的信任度。应在市场波动增大时（OI delta 突破阈值、funding rate 极端值、L/S ratio 显著偏移）重新运行。
- **Next Action**: 标记为 future_volatility_rerun，不主动降低 gate 阈值

### `whale_position_alert`

- **Status**: blocked_manual_evidence
- **Recommendation**: 开 manual evidence unblock 工单，不让执行端自动硬推
- **Rationale**: whale_position_alert 必须依赖真实链上地址归因数据，无法通过免费 API 自动获取。4 个地址在 operator workbook 中字段为空。不应绕过人工证据 来模拟 real E2E。
- **Next Action**: 创建 manual evidence collection 任务（v115O preflight scope），等待人工补证

### 📦 Finalization Packaging

- **Status**: recommended_next_step
- **Recommendation**: v116L — Market Radar v116 系列真实 E2E 里程碑汇总包
- **Rationale**: 当前 3 类真实 TG 测试发送 + 1 类真实 API 正确阻断 + 1 类人工证据阻塞，状态清晰、可验证。此时做里程碑包价值最高：(1) 汇总所有 v116A-K 产出；(2) 生成用户可验收的五类卡片审计和 TG evidence ledger；(3) 明确标记 liquidation 为 future rerun、whale 为 manual evidence task；(4) 为下一阶段（production readiness、data pipeline hardening）提供清晰的起点。
- **Next Action**: 创建 v116L 里程碑汇总包：聚合 v116A-K 全部 JSON/JSONL/MD/CSV 产出，生成单一可验收的里程碑文档，包含 five-card 覆盖矩阵、TG evidence ledger、next-step 路线图、未完成项和风险列表。

## Recommended Implementation Sequence

| # | Action | Card Family | Version | Status |
|---|--------|-------------|---------|--------|
| - | `multi_asset_market_sync` | MAMS | v116E | ✅ Real API + TG sent |
| - | `price_oi_volume_anomaly` | POVA | v116G | ✅ Real API + TG sent (ETH/SOL) |
| - | `news_event_market_impact` | NEMI | v116J | ✅ Real public source + TG sent |
| - | `liquidation_pressure` | LIPR | v116I | ⚠ Gate blocked (future rerun) |
| - | `whale_position_alert` | WPA | v116A+ | ⛔ Manual evidence blocked |
| 1 | **v116L Milestone Pack** | ALL | v116L | 📦 NEXT: aggregate deliverables |
| 2 | Manual evidence task | WPA | v115O+ | ⏳ After milestone review |
| 3 | Volatility rerun trigger | LIPR | v116I+ | 🔄 Wait for market signal |

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| User wants production send now | Medium | Milestone pack clearly states 0/5 production ready; TG test group only |
| liquidation gate too conservative | Low | Gate design validated as correct in calm market; thresholds configurable |
| whale evidence never collected | Medium | Explicit manual evidence task created; not auto-pushed |
| Milestone pack scope creep | Low | v116L scope is aggregation only — no new API/TG calls |
