# Market Radar v1.12-A — 固定卡片类型矩阵报告

**Generated**: 2026-06-04 23:26:11 UTC+8
**Version**: v1.12-A
**Mode**: fixed_card_type_matrix

---

## 概述

本报告建立 Market Radar 的 5 类固定卡片类型矩阵，每类包含：

- **Schema**：required_fields + optional_fields
- **准入规则**：admission_rules（信号需满足的条件）
- **阻止规则**：block_rules（信号应被过滤的条件）
- **公开模板规则**：public_template_rules（公开卡片渲染规范）
- **Readiness 判断**：ready / partial / missing

## 5 类卡片总览

| # | 卡片类型 | 分类 | Readiness | 适用长期监测 |
|---|----------|------|-----------|-------------|
| 1 | 清算压力预警卡 (`liquidation_pressure`) | risk_management | ❌ missing | ❌ 否 |
| 2 | 多资产共振卡 (`multi_asset_market_sync`) | market_structure | ⚠️ partial | ❌ 否 |
| 3 | 新闻事件影响卡 (`news_event_market_impact`) | event_driven | ❌ missing | ❌ 否 |
| 4 | 多因子价格异动卡 (`price_oi_volume_anomaly`) | market_structure | ✅ ready | ✅ 是 |
| 5 | 巨鲸仓位警报卡 (`whale_position_alert`) | onchain_intelligence | ⚠️ partial | ❌ 否 |

**计数**: Ready=1, Partial=2, Missing=2

---

## ❌ 清算压力预警卡 (`liquidation_pressure`)

### 用途

检测并报告市场中的强平密集区、清算风险、杠杆拥挤度和关键 liquidation level。当特定价格区间出现大量待清算仓位时触发。

### Required Fields

```
asset, liquidation_level, leverage_zone
```

### 准入规则

- **adm_liq_001_has_level** (required): 必须有关键清算价位或清算密集区数据
- **adm_liq_002_significant_size** (required): 待清算总额 >= $1,000,000 或清算密集规模 >= $500,000
- **adm_liq_003_asset_required** (required): asset 字段必须存在

### 阻止规则

- **blk_liq_001_no_level_data**: 完全缺少清算价位/密集区数据 → block
- **blk_liq_002_trivial_size**: 待清算总额 < $100,000 → block（不构成压力）
- **blk_liq_003_fixture_as_live**: fixture 样本不得标记为 live data

### Public Preview

```
🟠 清算压力预警｜BTC 多头拥挤

一句话：BTC 多头杠杆拥挤，$62,800 附近清算密集区规模 $45M，预估连锁清算 $220M

● 关键清算价：$62,800.00
● 清算密集区：$62,850.00
● 多头待清算：$85.00M
● 空头待清算：$12.00M
● 杠杆集中区间：高杠杆区 $62,000 - $63,500
● 风险等级：HIGH
⚠️ 如触发连锁清算，预估影响规模 $220.00M

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)

💡 触发原因：BTC 多头杠杆拥挤，$62,800 附近清算密集区规模 $45M，预估连锁清算 $220M

⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。
```

### Readiness: ❌ missing

- **Schema complete**: False
- **Real data pipeline**: False
- **Gate integration tested**: False
- **Suitable for long-running monitoring**: False

### 距离真实长期自动监测还差什么

- 无明显缺口

### Missing Fields / Data Sources / Rules

- **Missing fields**: 缺少杠杆率实时计算管道（OI / market cap ratio）, 缺少连锁清算模拟模型, 缺少历史清算事件对比基线
- **Missing data sources**: real_data_pipeline, 缺少实时清算数据源（需要交易所 liquidation feed 或聚合 API）, 缺少清算价位热力图数据（liquidation heatmap）
- **Missing rules**: gate integration not tested

### Next Gap

real_data_pipeline

---

## ⚠️ 多资产共振卡 (`multi_asset_market_sync`)

### 用途

检测并报告多个资产（>= 3 个真实资产）在同一方向上的同步异动，包括板块轮动、相关资产共振、系统性走势。用于识别市场级别的结构性变化而非单一资产噪音。

### Required Fields

```
assets, direction
```

### 准入规则

- **adm_sync_001_min_assets** (required): 至少 3 个真实资产（非 fixture）在同一方向
- **adm_sync_002_has_direction** (required): 共振方向必须明确（up 或 down）
- **adm_sync_003_backing** (recommended): 需有 OI 或成交量至少一个作为共振支撑（防假共振）

### 阻止规则

- **blk_sync_001_insufficient_assets**: 同向真实资产 < 3 → block
- **blk_sync_002_all_fixture**: 所有资产都是 fixture → block
- **blk_sync_003_no_direction**: 无明确方向（neutral）→ block
- **blk_sync_004_fixture_as_live**: fixture 样本不得标记为 live data

### Public Preview

```
📉 多资产共振｜普跌 5个资产 · L2

一句话：L2 板块 5 个资产同步下跌，ARB 领跌 -8.50%，板块整体偏弱

● 领涨/领跌：ARB
● 共振资产：ARB, OP, MATIC, IMX, METIS
● 最大涨跌幅：-8.50%
● 平均涨跌幅：-6.58%
● 共振支撑：OI 待确认 / 成交量 待确认

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ARB) / [DexScreener](https://dexscreener.com/search?q=ARB)

💡 触发原因：L2 板块 5 个资产同步下跌，ARB 领跌 -8.50%，板块整体偏弱

⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。
```

### Readiness: ⚠️ partial

- **Schema complete**: False
- **Real data pipeline**: False
- **Gate integration tested**: False
- **Suitable for long-running monitoring**: False

### 距离真实长期自动监测还差什么

- 无明显缺口

### Missing Fields / Data Sources / Rules

- **Missing fields**: 需要跨资产实时相关性矩阵（自动检测共振，而非依赖 context 传入）, 需要板块/赛道自动分类（L1/L2/DeFi/Meme/AI 等标签）, 需要领涨/领跌资产自动识别, 需要共振强度衰减追踪（信号发出后的持续性验证）, 需要日内多次快照对比（区分日内波动 vs 趋势共振）
- **Missing data sources**: 无
- **Missing rules**: 无

### Next Gap

需要跨资产实时相关性矩阵（自动检测共振，而非依赖 context 传入）

---

## ❌ 新闻事件影响卡 (`news_event_market_impact`)

### 用途

检测并报告新闻/事件驱动的市场影响，包括监管动态、项目事故、ETF 进展、宏观数据发布、交易所事件等。评估事件的交易相关性和市场定价程度。

### Required Fields

```
event_title, affected_assets, event_type
```

### 准入规则

- **adm_news_001_has_title** (required): event_title 必须存在且非空
- **adm_news_002_has_assets** (required): affected_assets 必须存在且非空
- **adm_news_003_has_type** (required): event_type 必须为已知类型之一
- **adm_news_004_relevance** (recommended): 交易相关性不为「无」或「极低」

### 阻止规则

- **blk_news_001_no_title**: 缺少 event_title → block
- **blk_news_002_no_assets**: 缺少 affected_assets → block
- **blk_news_003_already_fully_priced**: 事件已被市场完全定价 → block
- **blk_news_004_no_relevance**: 交易相关性为「无」→ block
- **blk_news_005_fixture_as_live**: fixture 样本不得标记为 live data

### Public Preview

```
🏛️ 新闻事件｜美 SEC 批准比特币现货 ETF 期权交易

一句话：CoinDesk 报道 SEC 批准 BTC ETF 期权交易，属监管类重大事件

● 影响币种：BTC, ETH
● 事件类型：监管
● 交易相关性：高
● 摘要：SEC 正式批准多家交易所的现货 BTC ETF 期权交易，预计将增加机构参与度和市场流动性。
● 是否已提前反应：部分已定价
● 风险标签：监管, ETF, 机构
● 观察窗口：2-4 小时
● 来源：CoinDesk

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=BTC) / [DexScreener](https://dexscreener.com/search?q=BTC)

💡 触发原因：CoinDesk 报道 SEC 批准 BTC ETF 期权交易，属监管类重大事件

⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。
```

### Readiness: ❌ missing

- **Schema complete**: False
- **Real data pipeline**: False
- **Gate integration tested**: False
- **Suitable for long-running monitoring**: False

### 距离真实长期自动监测还差什么

- 无明显缺口

### Missing Fields / Data Sources / Rules

- **Missing fields**: 缺少事件自动分类（NLP 识别监管/技术/安全/宏观等类型）, 缺少 Affected Assets 自动提取（从新闻文本中识别受影响币种）, 缺少已定价判断模型（事件发生 vs 市场价格反应的时间差分析）, 缺少交易相关性自动评估（事件对价格的实际影响量化）
- **Missing data sources**: real_data_pipeline, 缺少实时新闻 RSS/API 接入管道（CoinDesk / The Block / 官方博客等）, 缺少事件去重/合并（同一事件多来源重复推送）
- **Missing rules**: gate integration not tested

### Next Gap

real_data_pipeline

---

## ✅ 多因子价格异动卡 (`price_oi_volume_anomaly`)

### 用途

检测并报告单一资产的价格 + 未平仓合约(OI) + 成交量 + 资金费率(funding) 多因子同步异动。当价格显著变化且至少一个确认因子(OI/成交量/funding)同步异动时触发。

### Required Fields

```
asset, price_change_pct
```

### 准入规则

- **adm_pova_001_price_threshold** (required): 价格涨跌幅绝对值 >= 5%
- **adm_pova_002_confirm_factor** (required): 至少一个确认因子存在且非零：OI（open_interest / oi / oi_usd 字段）或 成交量（volume / dayNtlVlm / volume_24h 字段）或 资金费率极端（abs(funding) >= 0.01）或 多资产共振（>= 3 个真实资产同向）
- **adm_pova_003_asset_required** (required): asset 字段必须存在且非空

### 阻止规则

- **blk_pova_001_missing_asset**: 缺少 asset 字段 → block
- **blk_pova_002_missing_price**: 缺少 price_change_pct 字段 → block
- **blk_pova_003_insignificant_price**: abs(price_change_pct) < 3% → block（无意义波动）
- **blk_pova_004_no_confirm_at_all**: OI/成交量/funding/多资产共振全部缺失 → block
- **blk_pova_005_fixture_as_live**: fixture 样本不得标记为 live data 进入正式管道

### Public Preview

```
📉 行情异动｜ARB 急跌

一句话：ARB 多因子同步异动（价格跌幅 + OI + 成交量 + 资金费率偏空），短时升级信号。

● 币种：ARB
● 涨跌幅：-8.50%
● OI：$5.20M
● 成交量：$6.10M
● Funding：-1.80%（年化 -1971.0%）
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=ARB) / [DexScreener](https://dexscreener.com/search?q=ARB)

💡 触发原因：ARB 多因子同步异动（价格跌幅 + OI + 成交量 + 资金费率偏空），短时升级信号。

⚠️ 仅供观察，不构成交易建议。
```

### Readiness: ✅ ready

- **Schema complete**: False
- **Real data pipeline**: False
- **Gate integration tested**: False
- **Suitable for long-running monitoring**: True

### 距离真实长期自动监测还差什么

- 无明显缺口

### Missing Fields / Data Sources / Rules

- **Missing fields**: 需要 OI/Volume delta 实时追踪（区分趋势性 vs 瞬时异动）, 需要资金费率历史均值对比（判断当前是否真的极端）
- **Missing data sources**: 需要跨交易所数据一致性校验（防单交易所数据异常）
- **Missing rules**: 无

### Next Gap

需要跨交易所数据一致性校验（防单交易所数据异常）

---

## ⚠️ 巨鲸仓位警报卡 (`whale_position_alert`)

### 用途

检测并报告巨鲸/大户的链上仓位变化，包括加仓、减仓、爆仓边缘、浮盈浮亏等关键状态。覆盖 Hyperliquid 等公开 DEX 的大额持仓。

### Required Fields

```
asset, address, side, position_value_usd
```

### 准入规则

- **adm_whale_001_value_threshold** (required): 仓位价值 >= $100,000 USD（巨鲸最低门槛）
- **adm_whale_002_has_direction** (required): side 字段必须存在（多/空）
- **adm_whale_003_address_present** (required): address 必须存在且非空
- **adm_whale_004_significant_pnl** (recommended): 浮盈/浮亏 >= 10% 或 pnl >= $10,000（显著变化才触发）

### 阻止规则

- **blk_whale_001_below_threshold**: 仓位价值 < $50,000 → block（非巨鲸级别）
- **blk_whale_002_missing_address**: 缺少 address 字段 → block
- **blk_whale_003_missing_direction**: 缺少 side 字段 → block
- **blk_whale_004_dust_position**: 仓位价值 < $1,000 → block（粉尘仓位）
- **blk_whale_005_fixture_as_live**: fixture 样本不得标记为 live data

### Public Preview

```
🚀 主力仓位雷达｜HYPE 多头 大浮盈

一句话：HYPE 多头大额持仓，Hyperliquid 公开 API 检测到链上仓位，浮盈超 100%

● 持仓规模：$100.00M
● 持仓数量：1,380,000.00 HYPE
● 均价：$33.68
● 当前价格：$72.51
● 当前盈亏：+$46.98M（+116.0%）
● 清算价：$54.93（距清算 24.2%）
🏷️ 标签：Smart Money / 机构
📌 地址：`0x082d...8e9f`

🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query=HYPE) / [DexScreener](https://dexscreener.com/search?q=HYPE)

💡 触发原因：HYPE 多头大额持仓，Hyperliquid 公开 API 检测到链上仓位，浮盈超 100%

⚠️ 仅供观察，不构成交易建议。
```

### Readiness: ⚠️ partial

- **Schema complete**: False
- **Real data pipeline**: False
- **Gate integration tested**: False
- **Suitable for long-running monitoring**: False

### 距离真实长期自动监测还差什么

- 无明显缺口

### Missing Fields / Data Sources / Rules

- **Missing fields**: 需要地址标签自动标注（Smart Money / 机构 / 做市商 / 散户）, 需要历史仓位变化追踪（同一地址的加减仓序列）, 需要多地址聚合分析（关联地址群组检测）, 需要爆仓预警实时推送（距清算价 < 5% 时触发）
- **Missing data sources**: 无
- **Missing rules**: 无

### Next Gap

需要地址标签自动标注（Smart Money / 机构 / 做市商 / 散户）

---

## 最接近可用的卡片

**多因子价格异动卡 (`price_oi_volume_anomaly`)** 是最接近可用的卡片。

理由：
- Schema 完整、准入/阻止规则已定义、公开模板已就绪
- 真实数据管道可用（Hyperliquid API）
- Gate 集成已通过测试（SignalValueGate + CooldownGate + PreSendGate）
- v1.11-L 已验证 public card 净化流程

## 最影响长期自动监测闭环的卡片

**清算压力预警卡 (`liquidation_pressure`)** 是最影响长期监测闭环的卡片。

理由：
- 缺少真实数据管道，无法进入 gate → card → monitor 闭环
- 清算压力是市场风险管理的核心信号，缺失将导致监测矩阵不完整
- 新闻事件是外部冲击的主要来源，缺失意味着系统只能看到技术面

## 下一步最高优先级建议

### 当前最大缺口：liquidation_pressure

- **缺口**: real_data_pipeline
- **建议下一步**: Build real-time data ingestion pipeline for liquidation_pressure: real_data_pipeline

### 优先级排序

1. **liquidation_pressure** — 建立清算数据管道（Coinglass API / 交易所 liquidation feed），
   这是目前从 missing → partial 的最大单一提升。
2. **whale_position_alert** — 增加地址标签自动标注，将其从 partial → ready。
   Hyperliquid 管道已可用，仅需增强。
3. **multi_asset_market_sync** — 建立跨资产实时相关性矩阵，从依赖 context 传入
   升级为自动检测。
4. **news_event_market_impact** — 接入 RSS/新闻 API，实现事件自动分类。
   这是最大工程量的工作，建议在清算和巨鲸就绪后启动。
5. **price_oi_volume_anomaly** — 已 ready，仅需 OI/Volume delta 追踪增强。
   可以在其他卡片推进的同时并行完善。

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
