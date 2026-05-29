# Crypto Event Intelligence 项目交接说明

本文档用于把项目交给另一个 GPT / DeepSeek / Claude 继续推进。请先完整阅读，再执行任何修改。

## 1. 项目位置

项目根目录：

```text
C:\Users\PC\Desktop\Projects\事件情报系统
```

常用工作目录必须切到这里：

```powershell
cd C:\Users\PC\Desktop\Projects\事件情报系统
```

不要误用：

```text
C:\Users\PC\Desktop\群自动化
```

那个目录不是当前主项目。

## 2. 项目目标

我们在做的是一个 Web3 / Crypto 事件情报系统。

目标不是交易机器人，不自动下单，不生成买入/卖出/做多/做空建议，而是：

1. 把快讯、链上监控、巨鲸仓位、资金费率、OI、成交量、清算风险等信息统一成结构化情报。
2. 对信息做过滤、聚合、去重、解释。
3. 生成用户能在 Telegram 群里快速读懂的情报卡片。
4. 用历史价格和回测验证哪些事件/信号真的有用。

一句话：

```text
把杂乱 Web3 信息流变成可验证、可解释、低噪音的市场情报系统。
```

## 3. 重要边界

必须遵守：

1. 不接 Notion。
2. 不自动下单。
3. 不生成任何明确交易方向信号。
4. 不做交易建议。
5. 不做完整交易系统。
6. 不做 Web 页面。
7. 不把 API Key、Telegram Token、服务器密码写入代码、日志、README 或 Git。
8. 密钥只从本地 `config/local_secrets.ps1` 或临时环境变量读取。
9. 输出文案必须强调：仅作市场结构与链上情报观察，不构成任何交易建议。

## 4. 当前系统已经做到什么

### 4.1 历史快讯回测链路

已经实现：

```text
raw_news_export_template.csv
→ import_raw_news_to_event_candidates.py
→ event_candidates_review.csv
→ build_events_from_review.py
→ events_raw_50.csv
→ backfill_event_prices.py
→ validate_backfill_results.py
→ analyze_event_returns.py
```

能力：

- 读取历史快讯。
- 自动识别候选资产和事件类型。
- 构建事件样本。
- 从 Binance 回填价格。
- 计算 BTC / ETH benchmark 下的 abnormal return。
- 输出质量报告和回测汇总。

### 4.2 真实快讯导入

已经能从真实数据源导出 200/500 条快讯并做候选生成、自动建议、mature filter、auto50 回测。

相关脚本包括：

```text
scripts/run_v04_real_200_candidate_pipeline.py
scripts/suggest_review_decisions.py
scripts/filter_mature_candidates.py
scripts/build_stratified_auto_review.py
scripts/run_v043_older_mature50_backtest.py
```

### 4.3 Telegram 发布链路

已经能把生成的卡片发到 Telegram 群。

本地密钥文件：

```text
config/local_secrets.ps1
```

注意：

- 不要打印这个文件内容。
- 不要把 token 写进任何代码或文档。
- 发送脚本会从本地 secrets 读取 Telegram Bot Token 和 Chat ID。

### 4.4 市场状态与衍生品数据

已经实现：

- Binance 价格。
- 1h / 24h 成交量。
- OI 持仓变化。
- 资金费率。
- 90 日历史分位。
- 市场状态第一屏摘要。

相关脚本：

```text
scripts/build_market_state_snapshot.py
scripts/market/build_derivatives_history_percentiles.py
scripts/market/generate_percentile_alerts.py
scripts/reporting/generate_market_state_summary.py
```

当前策略：

- 不再使用“中性 / 偏高 / 偏低”这种主观绝对标签。
- 资金费率使用历史分位表达。
- Hyperliquid 资金费率展示 `/8h + 年化`。

### 4.5 Hyperliquid / 巨鲸 / 清算相关

已实现：

```text
scripts/hyperliquid/fetch_market_meta.py
scripts/hyperliquid/generate_market_meta_card.py
scripts/hyperliquid/generate_liquidation_wall.py
scripts/aggregate_hyperliquid_snapshot_with_baseline.py
```

现状：

- 能抓 Hyperliquid 官方公开 market meta。
- 能监控部分 Hyperliquid 大户仓位。
- 能计算监控地址的近清算距离。
- 能生成“近爆仓墙”文件。

重要修正：

Claude 指出，当前所谓“清算墙”只能代表“已监控地址清算风险”，不能代表全市场清算墙。

因此后续必须区分：

```text
监控地址清算风险：来自我们 watchlist 的 Hyperliquid 大户。
全市场清算密集区：需要 Coinglass / Glassnode 等第三方数据源。
```

不要再把少数监控地址的清算价叫成“全市场清算墙”。

## 5. 当前关键输出文件

常用结果：

```text
results/v15_tg_evening_digest_split_sections.md
results/v15_hyperliquid_market_meta_card.md
results/v15_hyperliquid_liquidation_wall.md
results/v15_hyperliquid_snapshot_card.md
results/v14_market_state_first_screen.md
results/v15_percentile_alerts.json
```

项目状态：

```text
docs/PROJECT_STATE.md
docs/PROJECT_DASHBOARD.md
docs/COMMAND_REGISTRY.md
docs/ARTIFACT_MANIFEST.md
docs/CLAUDE_RESPONSE_INDEX.md
docs/CLAUDE_DECISION_REVIEW.md
```

Claude 最新意见：

```text
results/v15_claude_liquidation_whale_onchain_review.md
```

## 6. 当前质量状态

最近一次校验通过：

```text
results/project_os_validation_summary.csv
results/command_registry_summary.csv
results/artifact_manifest_summary.csv
```

状态：

```text
Project OS validation: pass
Command registry: pass
Artifact manifest: pass
```

## 7. Claude 最新核心意见

Claude 对当前系统的判断：

```text
方向大体正确，但最大问题是信息组织和数据口径。
```

三个关键问题：

1. **不能用少数监控地址代表全市场清算墙。**
   - 当前只能叫“监控地址清算风险”。
   - 全市场清算墙需要接 Coinglass / Glassnode 等第三方热力图。

2. **系统还在按数据源组织信息，而不是按资产/事件组织信息。**
   - 用户看到 BTC 巨鲸、BTC 链上转账、BTC 快讯、BTC 资金费率异常时，不知道是同一件事还是多件事。
   - 需要事件聚合引擎，把同一资产、同一时间窗口的多信号合成“资产动态卡”。

3. **回测不能只看事件后收益。**
   - 必须检查信号发出前是否已经 price-in。
   - 必须按市场状态分组。
   - 必须验证组合信号，而不是单独信号。

## 8. 下一阶段优先级

下一阶段不要继续只堆新卡片。优先做底层结构：

### P0：信号标准化层

新增统一信号表：

```text
data/raw_signals.csv
```

或 SQLite 表：

```text
raw_signals
```

建议字段：

```text
signal_id
source_type
source_name
timestamp_utc
timestamp_china
asset
signal_category
direction
magnitude
confidence
is_first_hand
latency_seconds
raw_data
created_at
```

来源要覆盖：

- 快讯 news
- Hyperliquid 大户仓位 whale_position
- 监控地址清算风险 monitored_liquidation_risk
- Binance 市场状态 market
- 稳定币/链上转账 onchain_flow

### P1：事件聚合引擎

新增：

```text
scripts/aggregate_signals_to_events.py
data/aggregated_events.csv
```

聚合规则：

- 同一资产。
- 30 分钟窗口。
- 多个信号合并。
- 一手信号权重高于二手快讯。
- 重复快讯只作为补充证据，不重复发群。

建议字段：

```text
event_id
asset
event_start_time
event_end_time
signal_ids
signal_count
first_hand_count
overall_strength
overall_confidence
novelty_score
event_type
urgency
card_type
sent_to_telegram
created_at
```

### P2：TG 资产动态卡

新增：

```text
scripts/render_asset_event_cards.py
results/v16_asset_event_cards.md
```

目标：

把同一资产在短时间内的多个信号合成一张卡，而不是分别推送。

示例结构：

```text
⚡ BTC 资产动态｜多信号共振

发生了什么：
• 监控大户 BTC 空仓增加 24%
• BTC 资金费率处于 90 日 98.9% 分位
• 价格 1h +1.8%，OI 1h +4.2%

为什么重要：
• 仓位、费率、价格同时变化，说明当前结构拥挤度上升。

观察点：
• 是否继续接近监控地址清算区
• 是否出现成交量放大或 OI 快速回落

提示：仅作市场结构观察，不构成交易建议。
```

### P3：清算口径修正

把当前“清算墙”相关命名改为：

```text
monitored_liquidation_risk
```

而不是：

```text
liquidation_wall
```

后续如接 Coinglass，再新增：

```text
market_liquidation_heatmap
```

### P4：组合信号规则

新增组合规则：

```text
清算风险 + 价格逼近
清算风险 + 资金费率极端
清算风险 + 巨鲸反向加仓
巨鲸仓位突变 + OI/成交量异动
链上大额流入交易所 + 价格/OI 异动
```

这些组合信号才适合进盘中雷达。

## 9. 建议 GPT / DeepSeek / Claude 分工

### Claude

只用于：

- 顶层架构评审。
- 方向判断。
- 数据源优先级。
- 阈值体系是否合理。
- 做完一个阶段后评审。

不要让 Claude 写小脚本。

### GPT

用于：

- 把 Claude 意见拆成可执行任务。
- 写 DeepSeek 执行提示词。
- 检查 DeepSeek 输出。
- 跑本地验证。
- 做代码审查。
- 必要时兜底修关键 bug。

### DeepSeek

用于：

- 批量写脚本。
- 改字段。
- 做 CSV / SQLite ETL。
- 生成报告。
- 跑命令并输出执行结果。

每次 DeepSeek 完成后必须输出：

```text
1. 修改了哪些文件
2. 新增了哪些文件
3. 运行了哪些命令
4. 生成了哪些结果
5. 哪些失败/没做
6. 自测结果
7. 需要 GPT/Claude 判断的问题
```

## 10. 下一批给 DeepSeek 的任务建议

第一批任务不要太大，建议只做 v16 信号层和聚合层：

```text
任务 1：新增 raw_signals 标准化表生成脚本
任务 2：把当前快讯、Hyperliquid、市场状态、链上转账转换成 raw_signals
任务 3：新增 aggregate_signals_to_events.py
任务 4：生成 aggregated_events.csv
任务 5：新增 render_asset_event_cards.py
任务 6：输出 v16_asset_event_cards.md
任务 7：不要自动发 TG，先本地预览
```

验收标准：

```text
python scripts/build_raw_signals.py
python scripts/aggregate_signals_to_events.py
python scripts/render_asset_event_cards.py
```

应生成：

```text
data/raw_signals.csv
data/aggregated_events.csv
results/v16_asset_event_cards.md
results/v16_signal_aggregation_summary.csv
```

## 11. 注意事项

1. 所有时间统一显示中国时间 UTC+8。
2. 内部可以保留 UTC，但 TG 文案必须是中国时间。
3. Telegram 文案要中文。
4. 不要输出“交易策略：利多/利空”这种直接交易倾向。
5. 可以说“观察点”“结构变化”“风险提示”“置信度”，但不要说“买入/卖出/做多/做空”。
6. 盘中雷达要少而精。
7. 早午晚报可以承载更多背景信息。
8. 静态信息不要反复推送，例如代币解锁、静态大仓位，除非发生新变化。
9. 快讯和一手信号要合并，不能重复刷屏。
10. 每次修改后运行校验：

```powershell
python scripts/build_command_registry.py
python scripts/build_artifact_manifest.py
python scripts/validate_project_os.py
```

## 12. 推荐下一步

如果你是接手 GPT，请下一步直接做：

```text
基于 Claude 的意见，实现 v16 信号标准化层与资产事件聚合层。
先不要接 Coinglass，不要扩新数据源。
先把现有快讯、Hyperliquid、链上和市场状态合并成 raw_signals，再聚合成 asset event cards。
```

完成后，把执行报告交给 GPT 审查。
