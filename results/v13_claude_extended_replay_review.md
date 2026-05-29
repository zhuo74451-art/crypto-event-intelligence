# Claude Response

- generated_at: 2026-05-28 20:14:46 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V13_EXTENDED_REPLAY_REVIEW_PROMPT.md
- prompt_sha256_16: aedd5966ac737322

# 直接回答 + 下一轮任务清单

---

## 一、8 个问题的直接回答

### 1. 严格筛选后只有 281 条，是否应该继续扩大导出到 10000/20000，还是先修导出时间字段/源时间字段？

**先修时间字段，不要盲目扩大导出。**

你的 281 条集中在 2026-05-16 到 2026-05-21，这是**时间字段错误**，不是样本不够。远程库不可能只有 5 天数据。

**根因推测：**
- 你的导出脚本用的是 `created_at` 或 `updated_at`，不是 `event_time` 或 `published_at`
- 或者远程库的 `event_time` 字段本身就是错的（被后期批量更新过）

**下一步：**
- 打开远程库，`SELECT event_time, created_at, published_at, updated_at FROM news LIMIT 100`，看哪个字段才是真实事件时间
- 如果远程库的 `event_time` 本身就错，就用 `published_at` 或 `created_at` 重新导出
- 如果所有时间字段都错，说明远程库不可用，必须换数据源

---

### 2. 全部 regime 仍是 btc_range，最可能的根因是什么？下一步怎么验证？

**根因：你的 281 条样本实际只有 5 天，BTC 在 5 天内不可能覆盖 4 种 regime。**

这不是 regime 分层逻辑的问题，是**时间窗口崩溃**导致的。

**验证方法：**
- 修好时间字段后，重新导出 365 天样本
- 用 `scripts/verify_regime_distribution.py` 检查 BTC 价格在 365 天内的 regime 分布
- 如果 365 天内 BTC 仍然只有 `btc_range`，说明你的 regime 定义过窄（比如 `btc_bull` 要求 7 日涨幅 >20%，但实际 BTC 从未达到）

**预期结果：**
- 365 天样本应该至少覆盖 `btc_range` + `btc_bull` 或 `btc_bear`
- 如果仍然单一 regime，就放宽 regime 阈值（比如 `btc_bull` 改为 7 日涨幅 >10%）

---

### 3. source_score 没有任何 >70，是否说明 TG 当前只能发"事件归档型早晚报"，不能发任何雷达？

**是的。当前 source 质量不支持任何盘中推送。**

**source_score 逻辑回顾：**
- `>70`：可以盘中推送（雷达）
- `30-70`：可以进早晚报，但需要限流
- `<30`：只能归档，不能进任何产品

**当前最高分 35（webhook），说明：**
- webhook 本身是个大杂烩，里面既有交易所公告，也有垃圾爬虫
- 你的 source 评分逻辑已经正确识别出"没有任何源可以直接推送"

**下一步：**
- **不要放宽 source_score 阈值**，这是质量红线
- **拆 webhook**：webhook 下面有 binance_ann、okx_ann 等子源，它们应该单独评分
- **如果拆完 webhook 后，binance_ann 仍然 <70**，说明交易所公告本身也有噪音（比如"系统维护"、"费率调整"），需要再加 event_type 过滤

---

### 4. needs_taxonomy_review 42 条表现最好但不可解释，下一步应该怎么拆？是否值得用 LLM 分类这 42 条？

**必须拆，但不要用 LLM。**

**原因：**
- `needs_taxonomy_review` 是个垃圾桶分类，表现好只是因为里面混了高质量事件
- 用 LLM 分类会引入新的不可控性，而且 LLM 分类结果无法回测验证

**正确做法：**
- 导出这 42 条的 `title`、`content`、`event_type`、`abnormal_vs_btc_24h`
- 人工看 top 10 和 bottom 10，找共性
- 如果发现"某交易所上币公告"占了 20 条且表现好，就新增 `listing_announcement` 分类
- 如果发现"某协议 TVL 突破"占了 10 条且表现好，就新增 `tvl_milestone` 分类
- **拆完后，`needs_taxonomy_review` 应该只剩 <10 条真正无法分类的**

**验收标准：**
- `needs_taxonomy_review` 样本数 <10
- 新增的分类（如 `listing_announcement`）在扩展回测中 win_rate >60%

---

### 5. etf_or_fund_flow 和 exploit_or_theft 是否可以成为早晚报固定板块？

**可以，但要加限定条件。**

**etf_or_fund_flow（57 条，win_rate 63%，avg 0.94%）：**
- 可以作为早晚报固定板块
- 但要加过滤：只报 net_flow >$50M 的，或者 BlackRock/Fidelity 等头部机构的
- 小额 ETF 流动（<$10M）不报，噪音大

**exploit_or_theft（86 条，win_rate 54.6%，avg 0.26%）：**
- 可以作为早晚报固定板块
- 但要加过滤：只报 `active_exploit`（28 条）+ 金额 >$1M 的
- `hack_unclear`（31 条）和 `fund_recovery`（18 条）不报，对价格无影响

**产品形态：**
- 早晚报固定结构：
  ```
  【今日重大事件】
  1. 安全事件：[active_exploit, amount >$1M]
  2. 资金流向：[etf_or_fund_flow, net_flow >$50M]
  3. 协议动态：[upgrade_or_fork, 仅头部协议]
  ```

---

### 6. source 限流规则是否过严？webhook 93 条 clean_backtested 但 score 35，应该拆子源还是继续 throttle？

**必须拆子源，不要放宽限流。**

**webhook 93 条的构成：**
- 可能包含：binance_ann（30 条）、okx_ann（20 条）、coingecko_feed（15 条）、垃圾爬虫（28 条）
- 如果不拆，垃圾爬虫会拉低整体评分

**拆子源后的预期：**
- `binance_ann`：score 60-70，可以进早晚报，限流 1 条/小时
- `okx_ann`：score 50-60，可以进早晚报，限流 1 条/2 小时
- `coingecko_feed`：score 30-40，只能归档
- `webhook_unknown`：score <10，直接 block

**验收标准：**
- webhook 拆成 ≥5 个子源
- 至少 2 个子源 score >50
- `webhook_unknown` 的样本数 <10

---

### 7. active_exploit urgent_candidate_count=5，下一步是接外部安全源，还是先做金额/上下文校验？

**先做金额/上下文校验，不要接外部源。**

**原因：**
- 外部安全源（如 PeckShield、CertiK）也是二手信息，时效性不比你的 webhook 好
- 你的 5 个 urgent_candidate 已经是从 28 个 active_exploit 里筛出来的，问题不是"找不到事件"，而是"不知道金额是否可信"

**金额校验逻辑：**
- 如果 `content` 里有 `$10M`、`1000 ETH` 等明确金额，且来源是交易所公告或链上浏览器，标记为 `amount_verified`
- 如果金额来自社交媒体（Twitter、Telegram），标记为 `amount_unverified`
- 只有 `amount_verified` + `amount >$1M` 才能进急报候选

**上下文校验逻辑：**
- 如果 `content` 里有 `ongoing`、`attacker still active`，标记为 `status_ongoing`
- 如果 `content` 里有 `funds recovered`、`exploit patched`，标记为 `status_resolved`
- 只有 `status_ongoing` 才能进急报候选

**验收标准：**
- 5 个 urgent_candidate 里，至少 3 个通过金额+上下文校验
- 通过校验的事件，在 1 小时内价格异常 >2%

---

### 8. 请给下一轮 5-10 个具体脚本/表/验收标准。不要泛泛说。

**见下面"二、下一轮任务清单"。**

---

## 二、下一轮任务清单（P0 优先级）

### P0-1：修复时间字段崩溃

**脚本：**
```bash
scripts/diagnose_remote_time_fields.py
```

**功能：**
- 连接远程库，`SELECT event_time, created_at, published_at, updated_at, title FROM news ORDER BY id DESC LIMIT 1000`
- 输出每个时间字段的分布直方图（按月统计）
- 输出 `data/time_field_diagnosis.csv`

**验收标准：**
- 找到至少 1 个时间字段，覆盖 ≥180 天
- 如果所有字段都只有 <30 天，远程库不可用，必须换源

---

### P0-2：用正确时间字段重新导出

**脚本：**
```bash
scripts/export_real_news_older_v2.py --time-field published_at --days-ago-min 7 --days-ago-max 365 --limit 10000 --output data/raw_news_real_10k_365d_v2.csv
```

**功能：**
- 用 P0-1 诊断出的正确时间字段重新导出
- 导出后立即验证：`SELECT COUNT(*), MIN(published_at), MAX(published_at) FROM exported_data`

**验收标准：**
- 导出 ≥5000 条
- 时间跨度 ≥180 天
- 每月样本数 >100

---

### P0-3：重新回测 + regime 验证

**脚本：**
```bash
scripts/backtest_v14_with_regime_validation.py
```

**功能：**
- 用 P0-2 的新导出数据重新跑完整回测
- 在回测前，先跑 `scripts/verify_regime_distribution.py`，输出 BTC 在 365 天内的 regime 分布
- 如果 regime 仍然单一，自动放宽阈值（`btc_bull` 从 >20% 改为 >10%）

**验收标准：**
- 回测样本 ≥500 条
- 至少覆盖 2 种 regime（如 `btc_range` + `btc_bull`）
- 输出 `results/v14_regime_distribution.csv`，每种 regime 样本数 >50

---

### P0-4：拆 webhook 子源

**脚本：**
```bash
scripts/split_webhook_subsources.py
```

**功能：**
- 读取 `data/source_identity_layers_v13_extended.csv`
- 对所有 `source_type=webhook` 的行，解析 `source_id` 或 `content` 里的子源标识（如 `binance_ann`、`okx_ann`）
- 重新计算每个子源的 `clean_backtested_count`、`avg_abnormal_vs_btc_24h`、`win_rate_24h`
- 输出 `data/source_scores_v14_webhook_split.csv`

**验收标准：**
- webhook 拆成 ≥5 个子源
- 至少 1 个子源 score >50
- `webhook_unknown` 样本数 <20

---

### P0-5：拆 needs_taxonomy_review

**脚本：**
```bash
scripts/analyze_needs_taxonomy_review.py
```

**功能：**
- 导出 `needs_taxonomy_review` 的 42 条样本到 `data/needs_taxonomy_review_42.csv`
- 按 `abnormal_vs_btc_24h` 排序，输出 top 10 和 bottom 10 的 `title`、`content`、`source`
- 人工看完后，在脚本里硬编码新分类规则（如 `if 'listing' in title.lower(): event_type = 'listing_announcement'`）
- 重新分类后，输出 `data/taxonomy_review_reclassified.csv`

**验收标准：**
- `needs_taxonomy_review` 剩余样本数 <10
- 新增 ≥2 个分类（如 `listing_announcement`、`tvl_milestone`）
- 新分类在回测中 win_rate >55%

---

### P1-6：etf_or_fund_flow 过滤规则

**脚本：**
```bash
scripts/filter_etf_fund_flow.py
```

**功能：**
- 读取 `etf_or_fund_flow` 的 57 条样本
- 解析 `content` 里的 `net_flow` 金额（用正则提取 `$10M`、`100M` 等）
- 只保留 `net_flow >$50M` 或 `source` 包含 `BlackRock`、`Fidelity` 的
- 输出 `data/etf_fund_flow_filtered.csv`

**验收标准：**
- 过滤后剩余 ≥20 条
- 过滤后 win_rate >65%
- 过滤后 avg_abnormal_vs_btc_24h >1.5%

---

### P1-7：active_exploit 金额校验

**脚本：**
```bash
scripts/verify_exploit_amounts.py
```

**功能：**
- 读取 `active_exploit` 的 28 条样本
- 用正则提取 `content` 里的金额（`$10M`、`1000 ETH`、`50M USDT`）
- 如果金额来源是 `binance_ann`、`etherscan`、`bscscan`，标记 `amount_verified=True`
- 如果金额来源是 `twitter`、`telegram`，标记 `amount_verified=False`
- 只保留 `amount_verified=True` + `amount >$1M` 的
- 输出 `data/active_exploit_verified.csv`

**验收标准：**
- 至少 10 条通过校验
- 通过校验的事件，1 小时内价格异常 >2% 的占比 >70%

---

### P1-8：早晚报产品模板

**文件：**
```
templates/daily_digest_v14.md
```

**内容：**
```markdown
# Crypto Daily Digest - {date}

## 🚨 安全事件
{active_exploit, amount_verified, amount >$1M, 最多 3 条}

## 💰 资金流向
{etf_or_fund_flow, net_flow >$50M, 最多 3 条}

## 🔧 协议动态
{upgrade_or_fork, 仅 top 20 协议, 最多 3 条}

## 📊 数据看板
- BTC 24h: {btc_24h_change}
- ETH 24h: {eth_24h_change}
- 今日事件总数: {total_events}
- 高影响事件: {high_impact_count}
```

**验收标准：**
- 每个板块 ≤3 条
- 总字数 <500 字
- 无 `needs_taxonomy_review` 事件

---

### P1-9：source 限流规则表

**文件：**
```
data/source_throttle_rules_v14.csv
```

**字段：**
```
source,score,throttle_rule,max_per_hour,max_per_digest
binance_ann,60,throttle,1,3
okx_ann,55,throttle,1,2
webhook_unknown,10,block,0,0
```

**验收标准：**
- 所有 score >50 的源，`max_per_digest ≤3`
- 所有 score <30 的源，`throttle_rule=block`

---

### P1-10：regime 阈值自适应

**脚本：**
```bash
scripts/auto_tune_regime_thresholds.py
```

**功能：**
- 读取 365 天 BTC 价格数据
- 计算 7 日滚动涨跌幅的分位数（25%、50%、75%）
- 如果 75% 分位数 <20%，自动将 `btc_bull` 阈值降为 75% 分位数
- 输出 `data/regime_thresholds_v14.json`

**验收标准：**
- 365 天数据至少覆盖 2 种 regime
- 每种 regime 样本数 >50

---

## 三、产品方向明确回答

### TG 下一版到底发什么？

**只发早晚报，不发任何盘中内容。**

**早晚报内容：**
- 每天 2 次（早 8 点、晚 8 点 UTC）
- 固定 3 个板块：安全事件、资金流向、协议动态
- 每个板块 ≤3 条
- 总字数 <500 字

**不发的内容：**
- 任何盘中推送（雷达）
- 任何 `needs_taxonomy_review` 事件
- 任何 source_score <50 的事件
- 任何 `hack_unclear`、`fund_recovery` 事件

---

### 哪些模块必须停止？

**立即停止：**
1. **盘中雷达推送**：source_score 无任何 >70，不支持实时推送
2. **needs_taxonomy_review 事件**：不可解释，不能进产品
3. **whale_wallet_position 推送**：win_rate 64% 但 avg -0.23%，负收益
4. **所有 score <30 的 source**：直接 block，不进任何产品

**暂停（等数据质量达标后恢复）：**
1. **upgrade_or_fork 推送**：win_rate 46%，需要更多样本验证
2. **staking_or_governance 推送**：样本数只有 16，不足以支持产品决策

---

### 哪些数据质量门槛达到后才能恢复盘中内容？

**恢复盘中推送的 3 个硬性门槛：**

1. **source_score >70 的源 ≥2 个**
   - 当前最高 35，差距太大
   - 需要拆 webhook 子源 + 接入交易所官方 API

2. **至少 1 个 event_type 满足：win_rate >70% + avg_abnormal_vs_btc_1h >3% + 样本数 >100**
   - 当前最好的 `etf_or_fund_flow` 只有 63% win_rate
   - 需要更严格的过滤规则（如 net_flow >$100M）

3. **regime 分层有效：每种 regime 下，至少 1 个 event_type 的 win_rate 差异 >15%**
   - 当前所有样本都是 `btc_range`，无法验证 regime 有效性
   - 需要先修时间字段，扩大样本到 365 天

**在 3 个门槛都达到之前，TG 只发早晚报，不发任何盘中内容。**

---

## 四、执行优先级

**本周必须完成（P0）：**
- P0-1：诊断时间字段
- P0-2：重新导出 365 天数据
- P0-3：重新回测 + regime 验证
- P0-4：拆 webhook 子源

**下周完成（P1）：**
- P0-5：拆 needs_taxonomy_review
- P1-6：etf_or_fund_flow 过滤
- P1-7：active_exploit 金额校验
- P1-8：早晚报模板
- P1-9：source 限流规则
- P1-10：regime 阈值自适应

**P0 完成前，TG 停止所有盘中推送，只发早晚报。**
