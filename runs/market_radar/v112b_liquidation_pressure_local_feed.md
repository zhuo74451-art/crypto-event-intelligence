# Market Radar v1.12-B — 清算压力本地数据适配层报告

**Generated**: 2026-06-04 22:03:05 UTC+8
**Version**: v1.12-B
**Mode**: liquidation_pressure_local_feed

---

## 本轮目标

推进 v1.12-B：把 `liquidation_pressure` 从 **missing** 推进到 **partial**。

本轮只做「本地清算数据适配层 + 规范化 schema + 稳定 public card 输出」。
不接 Coinglass 付费 API，不调用外部 API，不做 WebSocket，不做 daemon。

目标是让后续无论接 Coinglass、交易所 liquidation feed，还是本地快照文件，
都能走同一套输入结构和卡片输出链路。

---

## 为什么不接付费 API

Coinglass 清算数据 API 为付费产品。本轮不调用任何付费 API，所有数据均来自
本地 fixture 样本 (`data_mode: fixture`)。适配层的设计使得后续接入任何
数据源（免费 API、交易所公开 WebSocket、本地 CSV 快照）都只需实现同一套
`normalize_liquidation_snapshot()` 接口。

---

## liquidation_pressure 从 missing → partial 的依据

| 维度 | v1.12-A (missing) | v1.12-B (partial) |
|------|-------------------|-------------------|
| Schema 完整 | ✅ | ✅ |
| 准入/阻止规则 | ✅ | ✅ |
| 公开模板 | ✅ | ✅ |
| Fixture 样本 | ✅ | ✅ (5 样本) |
| 数据适配层 | ❌ | ✅ normalize + detect + render + validate |
| Public card 输出 | ❌ (模板未实例化) | ✅ 3 张 valid card |
| 真实数据管道 | ❌ | ❌ (仍缺失) |
| Gate 集成测试 | ❌ | ❌ (留待后续) |

**结论**: 适配层就绪，card 渲染就绪，规则引擎就绪。仅缺真实数据源 → **partial**。

---

## 样本处理统计

| 指标 | 值 |
|------|-----|
| 总快照数 | 5 |
| 生成信号数 | 3 |
| 公开卡片数 | 3 |
| 被阻止数 | 2 |
| 数据模式 | all_fixture |
| TG 发送 | false |
| 外部 API 调用 | false |

---

## Valid Public Previews (3 张)

### Preview #1

```
⚠️ 清算压力｜BTC

一句话：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

● 当前价格：$63,500.00
● 近 1h 多头清算：$18.50M
● 近 1h 空头清算：$3.20M
● 近 24h 多头清算：$125.00M
● 近 24h 空头清算：$28.00M
● 未平仓合约：$18.50B
● 24h 成交量：$42.00B
● 观察窗口：1-4 小时

💡 触发原因：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

⚠️ 仅供观察，不构成交易建议。
```

### Preview #2

```
⚠️ 清算压力｜ETH

一句话：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

● 当前价格：$3,050.00
● 近 1h 多头清算：$4.20M
● 近 1h 空头清算：$22.00M
● 近 24h 多头清算：$38.00M
● 近 24h 空头清算：$145.00M
● 未平仓合约：$8.20B
● 24h 成交量：$18.50B
● 观察窗口：1-4 小时

💡 触发原因：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

⚠️ 仅供观察，不构成交易建议。
```

### Preview #3

```
⚠️ 清算压力｜SOL

一句话：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

● 当前价格：$142.50
● 近 1h 多头清算：$28.00M
● 近 1h 空头清算：$31.00M
● 近 24h 多头清算：$185.00M
● 近 24h 空头清算：$210.00M
● 未平仓合约：$2.10B
● 24h 成交量：$5.80B
● 观察窗口：2-6 小时

💡 触发原因：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

⚠️ 仅供观察，不构成交易建议。
```

## Blocked 样本 (2 个)

| # | Sample ID | Asset | Block Reason |
|---|-----------|-------|-------------|
| 1 | `liq_v112b_fixture_004_invalid_missing_asset` | (empty) | 缺少 asset 字段 |
| 2 | `liq_v112b_fixture_005_invalid_zero_liquidation` | DOGE | 清算金额全部为 0，无有效数据 |

---

## 仍然缺什么才能长期自动监测

1. **实时清算数据源** — 当前全部为 fixture 样本，没有真实市场数据。
   需要接入 Coinglass API（付费）、交易所 liquidation feed（免费但需 WebSocket）、
   或定期拉取的本地快照文件。
2. **Gate 集成** — 清算压力信号需要通过 SignalValueGate、CooldownGate、
   PreSendGate 等 gate 管道后才能进入真实发送流程。
3. **清算热力图数据** — 当前 cluster 数据为手工构造，实际需要清算价位
   热力图 API 提供精确的 liquidation level 分布。
4. **历史基线对比** — 需要历史清算数据来判断当前清算压力是否异常，
   而非仅依赖固定阈值。
5. **多资产并发监测** — 当前为单资产处理，长期需要同时对多个资产运行
   清算压力检测。

---

## 下一步最高优先级建议

1. **接入免费清算数据源** — 调研 Binance/Bybit/OKX 等交易所的公开
   liquidation WebSocket feed，通过 v112b 适配层 normalize 后进入
   监测管道。这是从 partial → ready 的关键一步。
2. **Gate 集成测试** — 将 v112b 信号接入现有 gate 管道
   (SignalValueGate → CooldownGate → PreSendGate)，验证
   liquidation_pressure 信号能通过全部 gate 检查。
3. **对接 v112a registry** — 在 card_type_registry 中更新
   liquidation_pressure 的 readiness 判断逻辑，使其能读取
   v112b 的 adapter 输出。

---

## 执行约束确认

| 约束 | 状态 |
|------|------|
| TG 发送 | ❌ 未发送 |
| 外部 API 调用 | ❌ 未调用 |
| 付费 API | ❌ 未调用 |
| Daemon/Loop/Cron | ❌ 未启动 |
| Token/Key/Cookie 读取 | ❌ 未读取 |
| 文件删除 | ❌ 未删除 |
