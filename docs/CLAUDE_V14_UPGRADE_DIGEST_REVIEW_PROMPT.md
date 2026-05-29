# Crypto Event Intelligence v14 Upgrade Digest Review

你继续以外部产品负责人 + 量化研究负责人视角审查。请直接批评，不要迎合，完整中文。

## 当前目标

我们要把历史快讯、链上监控、资金流、巨鲸仓位、安全事件等转成结构化事件，做历史回测和质量闸门，只把高质量、可解释、可复盘的市场情报发 Telegram 群。不是交易机器人，不给买卖建议。

## 按你上一轮意见已继续修改

1. 新增短周期 price-in：
   - 脚本：`scripts/build_v14_short_price_in.py`
   - 公开 Binance 1m K线，补事件发布前 5m / 15m / 1h 的价格异动。
   - 结果：281 条里 pass 276，price-in block 5，missing 0。

2. PreFilter 接入短周期 price-in：
   - 脚本：`scripts/build_v14_prefilter.py`
   - 结果：281 条里 passed 172，blocked 109。

3. 新增升级事件分类：
   - 脚本：`scripts/classify_v14_upgrade_events.py`
   - `upgrade_or_fork` 共 30 条：
     - digest 3
     - background 1
     - block 26
   - 规则：只放明确主网/硬分叉/共识升级/有标题时间锚点/Top chain asset 的内容；SDK/工具升级只作为 background。

4. Publisher 接入升级事件专属路由：
   - 脚本：`scripts/apply_v14_publish_policy.py`
   - 结果：
     - digest 4
     - interrupt 0
     - block 277

5. Digest preview 支持升级事件并去重：
   - 脚本：`scripts/build_v14_digest_preview.py`
   - 最终摘要：
     - security_rows 0
     - fund_flow_rows 0
     - upgrade_rows 2

## 当前 TG 摘要效果

```text
🧭 市场情报摘要测试版
时间：2026-05-28 21:21:08 UTC+8

本摘要只展示已过质量闸门的候选事件；未通过来源分、金额语境或资产一致性检查的内容不展示。

🧱 主网/协议升级
1. XRPL Validators Face Upgrade Deadline Ahead of Amendment …｜资产 XRP｜类型 hard_fork_or_consensus_upgrade｜事件提醒
2. BNBAgent SDK已上线BSC主网，为AI代理在链上的规模化落地提供核心基础设施｜资产 BNB｜类型 sdk_or_tooling_update｜事件提醒

🔎 阅读方式：优先看事件是否有明确来源、金额和上下文；相对BTC仅用于复盘观察，不代表结论。
⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。
```

## 我们现在的疑问

1. 这版把 0 条可发修到 2 条摘要，是正确放开，还是又把弱背景内容放进来了？
2. BNB SDK 这种“工具升级/生态建设”是否应该从摘要里移除，只进早报背景或归档？
3. XRPL upgrade 这类重复新闻，当前按 asset+upgrade_type 去重是否够，还是需要 event cluster / canonical event id？
4. 短周期 price-in 的 5m>1%、15m>2%、1h>3% 阈值是否合理？不同币种是否要按波动率自适应？
5. Active exploit 仍然 0 条，下一步到底应该先修数据源过滤、协议 token 字典，还是接外部安全源？
6. ETF/Fund flow 只剩 3 条，下一步应该做日频 ETF 晚报聚合，还是先暂停该类？
7. TG 卡片还缺什么字段才对用户有价值？例如历史参考、价格状态、来源等级、事件时间锚点。
8. 接下来请按优先级给出最具体的 5 个修改任务，最好精确到脚本级别。

