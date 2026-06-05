# Market Radar v116N — 10-Minute Demo Sequence

**Generated**: 2026-06-05 14:11:49 UTC+8
**Total Time**: 10 minutes

> 本顺序面向项目 Owner / 非技术用户，重点在于「展示边界、说清红线、给决策路径」。

---

## Segment 1: 看 One-Pager 红线 (1 min)

**打开**: `runs/market_radar/v116n_one_pager_acceptance_summary.md`

**说清楚 3 件事**：
1. Production Readiness: **0/5 — NOT FOR LIVE USE**
2. TG test group sends ≠ production sends
3. No daemon, no cron, no loop — 全部 one-shot

**关键句**：「这是我们目前最诚实的状态 — 能做什么，不能做什么，都写在这一页。」

---

## Segment 2: Five-Card 状态矩阵 (2 min)

**展示**：五类卡片一览表

| Card Family | Status | Meaning |
|-------------|--------|---------|
| Whale Position Alert | `blocked_manual_evidence` | 管道就绪，需人工链上证据 |
| Multi-Asset Market Sync | `real_free_api_tg_test_sent` | ✅ 已真实验证 |
| Price/OI/Volume Anomaly | `real_free_api_tg_test_sent` | ✅ 已真实验证 |
| Liquidation Pressure | `blocked_gate_not_passed` | 管道就绪，等波动 |
| News Event Market Impact | `real_free_public_source_tg_test_sent` | ✅ 已真实验证 |

**关键句**：「五类卡片的设计管道全部验证完毕，3 类已走通全链路到 TG test group。剩下 2 类的阻塞是可解释的设计决定，不是 bug。」

---

## Segment 3: Multi-Asset Market Sync (2 min)

**展示内容**：
- 数据来源：Binance 公开 API（BTCUSDT, ETHUSDT, SOLUSDT），无需 API Key
- 检测结果：市场同步下行风险，score=59.8, direction=down
- 门禁状态：quality_gate PASSED, send_readiness PASSED, secret_preflight PASSED
- TG 发送：1 张卡片 → test group
- 消息证明：`sha256:4fbb9cf6972a100c`

**关键句**：「这是最早完成的真实 E2E 卡片，证明了从公开 API 到 TG test group 的全链路可以跑通。」

---

## Segment 4: Price/OI/Volume Anomaly (2 min)

**展示内容**：
- 数据来源：Binance 公开 API（BTCUSDT, ETHUSDT, SOLUSDT）
- 信号情况：2/3 资产通过入场门禁
  - ETH: -4.44% → admitted ✅
  - SOL: -5.46% → admitted ✅
  - BTC: -2.24% → correctly rejected (gate working)
- TG 发送：2 张卡片（ETH, SOL）→ test group

**关键句**：「注意 BTC 被门禁拒绝了 — 这不是 bug，而是 gate 正确的行为。价格变化不够大，就不过。这和 liquidation pressure 的 gate block 是同一个设计逻辑。」

---

## Segment 5: News Event Market Impact (1.5 min)

**展示内容**：
- 数据来源：Binance 公开 RSS + REST，5 sources attempted, 1 succeeded
- 80 articles fetched → 7 events extracted → 2 admitted
- TG 发送：2 张卡片 → test group

### ⚠️ 强调：不是因果证明

**必须明确说出来**：「这个卡片展示的是事件和价格的相关性观察，NOT 因果证明。
一篇新闻提到 BTC 涨了，不代表新闻导致了涨。可能有其他因素。
所有 TG 消息都已标注这个风险声明。
**不要将这些卡片当作交易信号。**」

---

## Segment 6: Liquidation & Whale 正常阻断解释 (1.5 min)

### Liquidation Pressure — 正常 Gate Block

- 展示：3/3 assets fetched, 3/3 signals generated, **0/3 admitted**
- 解释：「Gate 在 calm market 下正确阻断了所有信号。这不是 bug。
  liquidation_pressure 是事件触发型卡片 — 它的价值在高波动市场。
  我们现在不是在 calm market 硬发一张没意义的卡片，而是在等正确的时机。」
- 明确：「**不建议降低 gate 阈值。** 降低阈值等于架空了 gate 设计。」

### Whale Position Alert — 正常 Manual Evidence Block

- 展示：Fixture E2E passed, 4/4 addresses workflow-ready, **evidence workbook empty**
- 解释：「免费公开 API 无法回答『这个地址是谁的』。
  这不是技术问题，是信息问题。
  我们需要人工确认这 4 个地址的归属（交易所、做市商、鲸鱼等）。
  在没有证据的情况下生成卡片，比不发更糟。」
- 明确：「**不建议绕过 manual evidence。** 虚假证据 = 不可靠卡片。」

---

## Demo Wrap-Up

**结束时三句话**：

1. 「Market Radar 的核心管道已经验证 — 5/5 fixture, 3/5 real E2E TG test sent。」
2. 「剩下的 2/5 是设计上的阻塞，不是失败 — 人工证据和等待波动都是正确的做法。」
3. 「下一步由你决定 — A 接受里程碑进入路线图，B 先补 whale 证据，还是 C 等波动 rerun liquidation。」
