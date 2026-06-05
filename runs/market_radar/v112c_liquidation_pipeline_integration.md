# Market Radar v1.12-C — Liquidation Pipeline 集成报告

**Generated**: 2026-06-04 22:15:32 UTC+8
**Version**: v1.12-C
**Mode**: liquidation_pipeline_integration

---

## 本轮目标

推进 v1.12-C：把 `liquidation_pressure` 从「孤立本地适配层」接入
Market Radar 固定卡片矩阵与统一门控 pipeline。

## v1.12-B 已完成事实

- liquidation snapshot normalize（`LiquidationSnapshot` 数据类）
- liquidation pressure detect（`detect_liquidation_pressure` 函数）
- liquidation public card render（`render_liquidation_pressure_card`）
- 3 张 public preview（BTC long / ETH short / SOL two-sided）
- validate_liquidation_signal 验证函数
- 5 条 fixture snapshots（3 valid + 2 invalid）
- readiness 声明从 missing → partial

## 为什么必须接入统一 pipeline

v1.12-B 的 `liquidation_pressure` 信号虽然已生成，但没有进入 v1.12-A 的
固定卡片类型矩阵（card type registry）和门控流程。具体表现为：

1. **Registry readiness 仍为 missing** — registry 是 hardcoded 的，
   没有动态读取 v112b 的 adapter 状态。
2. **信号未经过 v112a schema 校验** — v112b 使用自己的数据类，但
   v112a registry 定义了独立于实现的 `required_fields` / `admission_rules` / `block_rules`。
3. **卡片渲染路径不一致** — v112b 和 v112a 各自实现了 `render_*_public`，
   需要统一经过 registry 的 `render_public_preview` 路径。
4. **Debug leak check 未统一** — v112b 和 v112a 使用不同的 forbidden terms list。

本轮 v1.12-C 解决以上所有问题。

---

## liquidation_pressure pipeline 处理统计

| 指标 | 值 |
|------|-----|
| 总快照数 | 5 |
| 有效信号数 | 3 |
| 公开卡片数 | 3 |
| 被阻止数 | 2 |
| Mock send ready | 3 |
| Live ready | 0 |
| Real TG sent | false |
| External API | false |

---

## 3 张 Liquidation Public Preview 摘要

### Preview #1
- **标题**: 🟠 清算压力预警｜BTC 多头拥挤
- **一句话**: 一句话：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

```
🟠 清算压力预警｜BTC 多头拥挤

一句话：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

● 清算密集区：$63,500.00
● 多头待清算：$18.50M
● 空头待清算：$3.20M
● 杠杆集中区间：价格 $63,500 附近
● 风险等级：HIGH

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)

💡 触发原因：BTC 下方多头清算压力升高，近1h 多头清算 $18.50M，下方清算密集区 $0.00，若价格继续回落可能放大短线波动。

⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。
```

### Preview #2
- **标题**: 🟠 清算压力预警｜ETH 空头拥挤
- **一句话**: 一句话：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

```
🟠 清算压力预警｜ETH 空头拥挤

一句话：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

● 清算密集区：$3,050.00
● 多头待清算：$4.20M
● 空头待清算：$22.00M
● 杠杆集中区间：价格 $3,050 附近
● 风险等级：HIGH

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ETH) / [DexScreener](https://dexscreener.com/search?q=ETH)

💡 触发原因：ETH 上方空头清算压力升高，近1h 空头清算 $22.00M，上方清算密集区 $0.00，若价格上行可能引发空头踩踏。

⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。
```

### Preview #3
- **标题**: 🔴 清算压力预警｜SOL 拥挤
- **一句话**: 一句话：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

```
🔴 清算压力预警｜SOL 拥挤

一句话：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

● 清算密集区：$142.50
● 多头待清算：$28.00M
● 空头待清算：$31.00M
● 杠杆集中区间：价格 $142 附近
● 风险等级：CRITICAL

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=SOL) / [DexScreener](https://dexscreener.com/search?q=SOL)

💡 触发原因：SOL 上下方均存在清算密集区，下方多头清算 $0.00，上方空头清算 $0.00，双向波动风险升高。

⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。
```

---

## Fixed Card Matrix 更新前后对比

### 更新前（v112a 默认）

| # | Card Type | Readiness |
|---|-----------|-----------|
| 1 | `price_oi_volume_anomaly` | ✅ ready |
| 2 | `whale_position_alert` | ⚠️ partial |
| 3 | `liquidation_pressure` | ❌ missing |
| 4 | `multi_asset_market_sync` | ⚠️ partial |
| 5 | `news_event_market_impact` | ❌ missing |

**Ready**: 1, **Partial**: 2, **Missing**: 2

### 更新后（v112c 动态 readiness）

| # | Card Type | Readiness |
|---|-----------|-----------|
| 1 | `liquidation_pressure` | ⚠️ partial |
| 2 | `multi_asset_market_sync` | ⚠️ partial |
| 3 | `news_event_market_impact` | ❌ missing |
| 4 | `price_oi_volume_anomaly` | ✅ ready |
| 5 | `whale_position_alert` | ⚠️ partial |

**Ready**: 1, **Partial**: 3, **Missing**: 1

---

## 当前 5 类卡片最新 Readiness

### ⚠️ `liquidation_pressure` — partial

- **Display name**: 清算压力预警卡
- **Category**: risk_management
- **Schema complete**: True
- **Real data pipeline**: False
- **Gate integration tested**: True
- **Remaining gaps**:
  - 缺少实时清算数据源（当前仅 fixture，需接入交易所 liquidation feed 或免费聚合 API）
  - 缺少清算价位热力图数据（liquidation heatmap）
  - 缺少历史清算事件对比基线
  - 缺少多资产并发清算压力监测（当前按单资产处理）
  - gate 集成测试完成（v112c pipeline dry-run），但未接入真实发送流程

### ⚠️ `multi_asset_market_sync` — partial

- **Display name**: 多资产共振卡
- **Category**: market_structure
- **Schema complete**: True
- **Real data pipeline**: True
- **Gate integration tested**: True
- **Remaining gaps**:
  - 需要跨资产实时相关性矩阵（自动检测共振，而非依赖 context 传入）
  - 需要板块/赛道自动分类（L1/L2/DeFi/Meme/AI 等标签）
  - 需要领涨/领跌资产自动识别
  - 需要共振强度衰减追踪（信号发出后的持续性验证）
  - 需要日内多次快照对比（区分日内波动 vs 趋势共振）

### ❌ `news_event_market_impact` — missing

- **Display name**: 新闻事件影响卡
- **Category**: event_driven
- **Schema complete**: True
- **Real data pipeline**: False
- **Gate integration tested**: False
- **Remaining gaps**:
  - 缺少实时新闻 RSS/API 接入管道（CoinDesk / The Block / 官方博客等）
  - 缺少事件自动分类（NLP 识别监管/技术/安全/宏观等类型）
  - 缺少 Affected Assets 自动提取（从新闻文本中识别受影响币种）
  - 缺少已定价判断模型（事件发生 vs 市场价格反应的时间差分析）
  - 缺少事件去重/合并（同一事件多来源重复推送）

### ✅ `price_oi_volume_anomaly` — ready

- **Display name**: 多因子价格异动卡
- **Category**: market_structure
- **Schema complete**: True
- **Real data pipeline**: True
- **Gate integration tested**: True
- **Remaining gaps**:
  - 需要 OI/Volume delta 实时追踪（区分趋势性 vs 瞬时异动）
  - 需要资金费率历史均值对比（判断当前是否真的极端）
  - 需要跨交易所数据一致性校验（防单交易所数据异常）

### ⚠️ `whale_position_alert` — partial

- **Display name**: 巨鲸仓位警报卡
- **Category**: onchain_intelligence
- **Schema complete**: True
- **Real data pipeline**: True
- **Gate integration tested**: True
- **Remaining gaps**:
  - 需要地址标签自动标注（Smart Money / 机构 / 做市商 / 散户）
  - 需要历史仓位变化追踪（同一地址的加减仓序列）
  - 需要多地址聚合分析（关联地址群组检测）
  - 需要爆仓预警实时推送（距清算价 < 5% 时触发）

---

## 当前距离长期自动监测还差什么

### liquidation_pressure（当前: partial）

1. **实时清算数据源** — 当前全部为 fixture 样本，需要接入：
   - 交易所 WebSocket liquidation feed（Binance/Bybit/OKX 公开频道）
   - 或免费清算数据聚合 API（如 Hyblock Capital 部分免费端点）
2. **清算热力图数据** — 需要精确的 liquidation level 分布，
   当前 cluster 数据为手工构造。
3. **历史基线对比** — 需要建立历史清算基准，判断当前压力是否异常。
4. **多资产并发监测** — 同时对多个主流资产运行清算压力检测。

### 整体系统

- **news_event_market_impact** 仍为 missing — 需要新闻 API 接入 + NLP 分类管道
- **multi_asset_market_sync** 的自动检测仍依赖 context 传入，需要自建相关性矩阵
- **whale_position_alert** 的地址标签自动标注尚未实现
- **price_oi_volume_anomaly** 的 OI/Volume delta 实时追踪需要增强

---

## 下一步最高优先级建议

1. **接入免费清算数据源**（liquidation_pressure: partial → ready 的关键）：
   调研 Binance/Bybit/OKX 公开 WebSocket liquidation feed，编写 normalize 适配器。
2. **推进 news_event_market_impact**：接入免费 RSS 源（CoinDesk / The Block），
   实现基本的 event_type 分类和 affected_assets 提取。
3. **增强 multi_asset_market_sync**：自建跨资产实时相关性矩阵，
   从依赖 context → 自动检测。
4. **增强 whale_position_alert**：接入地址标签数据源，实现自动标注。
5. **持续增强 price_oi_volume_anomaly**：OI/Volume delta 追踪 + 跨交易所校验。

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
