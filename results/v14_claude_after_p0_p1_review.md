# Claude Response

- generated_at: 2026-05-28 22:45:55 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: 6acb13e743c1bc96

# Crypto Event Intelligence v14 下一批修正任务（P0/P1/P2）

---

## P0：首屏致命缺陷

### P0-1：首屏缺少"为什么今天要看"

**问题**：
当前首屏罗列了市场状态、ETF、日历因素，但**没有告诉用户今天为什么要看这份报告**。用户打开 TG 第一眼应该看到"今天有什么异常"，而不是一堆中性数据。

**修正方案**：
在首屏最上方增加一行"今日市场异常摘要"，只在满足以下任一条件时出现：
- BTC/ETH 24h 涨跌幅绝对值 >5%
- BTC/ETH 资金费率绝对值 >0.03%（年化 >32%）
- BTC ETF 净流入/出 >5 亿美元
- 日历因素命中月末/季末/FOMC 前 3 天
- 今日最值得关注事件 ≥2 条且最高分 ≥8 分

如果都不满足，这一行显示"今日市场无显著异常，常规监控"。

**任务**：
- 输入：`results/v14_market_state_snapshot.csv`、`results/v14_etf_plain_summary.md`、`results/v14_prioritized_events.csv`、日历因素 JSON
- 输出：`results/v14_market_alert_headline.txt`（单行文本）
- 脚本：`scripts/reporting/generate_alert_headline.py`
- 验收：用 2024-12-01（BTC 跌 5%）、2024-05-27（ETF 流出 7.33 亿）、2024-03-15（无异常）三天数据测试，前两天必须有明确异常提示，第三天显示"无显著异常"。

---

### P0-2：ETF 集中度变化没有解释

**问题**：
首屏显示"IBIT:72.0:+14.3pp"，普通用户不知道这意味着什么，也不知道 14.3pp 是好是坏。

**修正方案**：
在 ETF 集中度后面增加一句解释：
- 如果 IBIT 份额增加 >10pp 且 GBTC 份额下降，说明"资金从老基金流向新基金，正常轮动"
- 如果 IBIT 份额增加 >10pp 且 GBTC 份额也增加，说明"新资金集中流入头部基金，市场偏好明确"
- 如果 IBIT 份额下降 >5pp，说明"头部基金份额被稀释，需关注资金分散风险"

**任务**：
- 输入：`results/v14_etf_plain_summary.md`（需增加前一日集中度数据）
- 输出：`results/v14_etf_concentration_interpretation.txt`（单行解释）
- 脚本：修改 `scripts/reporting/generate_etf_summary.py`，增加集中度变化解释逻辑
- 验收：用 2024-05-27 数据测试，IBIT +14.3pp、GBTC +1.9pp、FBTC -9.1pp，应输出"新资金集中流入头部基金，市场偏好明确；FBTC 份额大幅下降，可能有赎回压力"。

---

## P1：事件筛选与解释

### P1-1：HYPE 静态大仓位仍可能进"今日最值得关注"

**问题**：
你已经把 HYPE 静态大仓位降权到 5 分，但如果今天只有 3 条事件（DOGE 10 分、HYPE 5 分、HOME 4 分），HYPE 仍会进"今日最值得关注"（因为你设定的是 top 3）。这不合理，因为静态大仓位本身不是"今日"事件。

**修正方案**：
"今日最值得关注"改为**动态筛选**：
- 分数 ≥8 分：无条件进入
- 分数 6-7 分：如果事件类型是 `market_structure`、`funding_rate_extreme`、`cex_netflow_extreme`、`token_unlock`（当日解锁），则进入
- 分数 ≤5 分：不进入"今日最值得关注"，归入"其他动态"

这样 HYPE 静态大仓位（5 分）会被自动排除，除非它同时触发了其他高分事件。

**任务**：
- 输入：`results/v14_prioritized_events.csv`
- 输出：`results/v14_today_focus_events.csv`（只包含"今日最值得关注"的事件）、`results/v14_other_events.csv`（其他动态）
- 脚本：修改 `scripts/events/prioritize_events.py`，增加动态筛选逻辑
- 验收：用当前数据测试，HYPE 5 分应进入"其他动态"，不进入"今日最值得关注"；用模拟数据（HYPE 触发 funding_rate_extreme 且 7 分）测试，应进入"今日最值得关注"。

---

### P1-2：ETH ETF 必须补，但不要重复造轮子

**问题**：
当前只有 BTC 现货 ETF，但 ETH ETF 也有净流入/出数据（虽然规模小得多）。如果 ETH ETF 某天流出 1 亿美元（对 ETH 来说是大事），你现在会漏掉。

**修正方案**：
复用 BTC ETF 的脚本和逻辑，只需：
1. 在 `data/etf/` 下增加 `eth_etf_flows.csv`（格式同 `btc_etf_flows.csv`）
2. 修改 `scripts/reporting/generate_etf_summary.py`，增加一个循环，同时处理 BTC 和 ETH
3. 在首屏 ETF 摘要中，如果 ETH ETF 净流入/出绝对值 >5000 万美元，也显示一行

**任务**：
- 输入：手动创建 `data/etf/eth_etf_flows.csv`（至少包含 2024-05-20 到 2024-05-27 的数据，可以从 CoinGlass 或 SoSoValue 爬取）
- 输出：`results/v14_etf_plain_summary.md` 增加 ETH ETF 一行（如果满足阈值）
- 脚本：修改 `scripts/reporting/generate_etf_summary.py`
- 验收：用 2024-05-27 数据测试，如果 ETH ETF 净流出 >5000 万美元，首屏应显示"ETH 现货 ETF：27 May 2026 净流 -X 亿美元（90日分位 Y%）"。

---

## P2：历史数据与盘中雷达

### P2-1：历史数据优先级

**当前缺失的历史数据**：
1. CEX netflow baseline（用于判断"今天的 netflow 是不是异常"）
2. Hyperliquid 24h/7d baseline（用于判断"今天的交易量/持仓是不是异常"）
3. OI/volume 历史分位（用于判断"今天的持仓/交易量在过去 90 天处于什么位置"）
4. 资金费率历史分位（用于判断"今天的资金费率在过去 90 天处于什么位置"）
5. 更多真实快讯回测（用于验证事件优先级打分是否合理）

**优先级排序**：
1. **P2-1a：资金费率历史分位**（最高优先级）
   - 原因：资金费率是唯一能实时反映多空情绪的指标，且数据获取成本低（Coinglass API 免费）
   - 任务：爬取 BTC/ETH/SOL 过去 90 天的 8 小时资金费率，计算每日分位数，存入 `data/funding_rate/funding_rate_percentiles.csv`
   - 验收：用 2024-05-27 数据测试，BTC 资金费率 0.0100% 应对应历史分位 ~50%（中性），如果某天资金费率 0.05% 应对应 >95%（极端做多）

2. **P2-1b：OI 历史分位**（次高优先级）
   - 原因：持仓量变化是市场结构的核心指标，且你已经有 `v14_market_state_snapshot.csv` 包含 OI 数据
   - 任务：爬取 BTC/ETH/SOL 过去 90 天的 OI，计算每日分位数，存入 `data/oi/oi_percentiles.csv`
   - 验收：用 2024-05-27 数据测试，BTC OI 变化 +2.34% 应对应历史分位 ~60%（略高于中位数）

3. **P2-1c：CEX netflow baseline**（第三优先级）
   - 原因：CEX netflow 是资金流向的直接证据，但数据获取成本高（需要链上数据或付费 API）
   - 任务：如果有免费数据源（如 CryptoQuant 免费层），爬取 BTC/ETH 过去 30 天的 CEX netflow，计算每日分位数，存入 `data/cex_netflow/netflow_percentiles.csv`；如果没有免费数据源，暂时跳过
   - 验收：用 2024-05-27 数据测试，如果 BTC netflow 流出 1 万枚，应对应历史分位 >90%（异常流出）

4. **P2-1d：Hyperliquid baseline**（第四优先级）
   - 原因：Hyperliquid 数据只对小币种有意义（BTC/ETH 主要在 Binance/Bybit），且你已经有 `select_focus_assets.py` 过滤掉了 HYPE
   - 任务：暂时不做，等有明确需求（如某个小币种在 Hyperliquid 交易量占比 >50%）再补

5. **P2-1e：更多真实快讯回测**（最低优先级）
   - 原因：回测是验证逻辑，不是生产数据；当前优先级是"先把实时监控跑起来"
   - 任务：每周五人工回测一次，记录"本周漏掉的重要事件"和"本周误报的低价值事件"，更新 `config/event_priority_rules.yaml`

---

### P2-2：盘中雷达 vs 早午晚报

**盘中雷达（实时推送，延迟 <5 分钟）**：
- 资金费率突破 ±0.05%（年化 ±54%）
- BTC/ETH 5 分钟涨跌幅 >2%
- CEX netflow 单小时流入/出 >5000 BTC 或 5 万 ETH
- 大额清算（单笔 >500 万美元）
- 链上大额转账（>1000 BTC 或 1 万 ETH 转入交易所）

**早午晚报（定时推送，延迟可接受）**：
- 市场状态首屏（BTC/ETH 24h 涨跌幅、持仓变化、资金费率）
- ETF 净流入/出（每日收盘后更新）
- 日历因素（月末/季末/FOMC）
- 今日最值得关注事件（基于过去 24 小时数据）
- 价格-持仓四象限分析

**任务**：
- 输入：当前所有指标
- 输出：`config/alert_routing.yaml`（定义哪些指标进盘中雷达，哪些进早午晚报）
- 脚本：无需新脚本，只需配置文件
- 验收：人工审查配置文件，确保盘中雷达只包含"需要立即响应"的指标，早午晚报包含"需要每日回顾"的指标。

---

## 总结：下一批任务清单

| 优先级 | 任务 | 输入 | 输出 | 验收标准 |
|--------|------|------|------|----------|
| P0-1 | 首屏增加"今日市场异常摘要" | 市场状态、ETF、事件、日历 | `v14_market_alert_headline.txt` | 用 3 天数据测试，异常日有明确提示，正常日显示"无显著异常" |
| P0-2 | ETF 集中度变化增加解释 | ETF 摘要 | `v14_etf_concentration_interpretation.txt` | 用 2024-05-27 数据测试，输出符合逻辑的解释 |
| P1-1 | "今日最值得关注"改为动态筛选 | 事件优先级 CSV | `v14_today_focus_events.csv` | HYPE 5 分进"其他动态"，HYPE 7 分+市场结构进"今日最值得关注" |
| P1-2 | 补充 ETH ETF 数据 | `eth_etf_flows.csv` | ETF 摘要增加 ETH 一行 | 用 2024-05-27 数据测试，ETH ETF 流出 >5000 万显示 |
| P2-1a | 爬取资金费率历史分位 | Coinglass API | `funding_rate_percentiles.csv` | BTC 0.0100% 对应 ~50%，0.05% 对应 >95% |
| P2-1b | 爬取 OI 历史分位 | Coinglass API | `oi_percentiles.csv` | BTC OI +2.34% 对应 ~60% |
| P2-2 | 定义盘中雷达 vs 早午晚报 | 当前所有指标 | `alert_routing.yaml` | 人工审查，确保分类合理 |

**下周一优先做 P0-1 和 P1-1，这两个直接影响用户体验。P2 任务可以并行做，但不阻塞 P0/P1。**
