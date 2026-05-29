# Claude Review Prompt: v0.7 First-Hand Watcher Server Rollout

你是这个项目的外部技术合伙人和产品负责人。请直接、具体、不迎合地评审当前方向。

项目一句话：

我们在做 Crypto Event Intelligence，不是交易机器人。目标是把二手快讯和一手链上/市场结构信号变成结构化事件，筛掉垃圾，生成可复核的 Telegram 情报流，并保留后续回测验证能力。

当前状态：

- 二手快讯链路已经跑通：真实新闻导出、候选生成、AI/规则筛选、事件构建、Binance 价格回填、BTC/ETH abnormal return、质量检查。
- Telegram 新闻发布器已经在服务器运行，并改成中文富文本卡片。
- v0.7 一手 watcher 已部署到服务器常驻服务：
  - service: `crypto-event-intel-watchers.service`
  - path: `/opt/crypto-event-intel-watchers`
  - interval: 300 秒
  - sources:
    - Ethereum watched address ERC20 transfers
    - USDT/USDC treasury mint/burn
    - Hyperliquid curated large positions
- 新增发送前质量 gate：
  - 按 amount_usd、event_type、raw_signal_type、confidence、strength、trading-advice words 过滤
  - 当前 dry-run 示例：7 条候选中 2 pass、3 warning、2 fail，实际 eligible 5 条
- 扩充 watchlist：
  - 新增 Binance Hot Wallet 20、Bitfinex 2、Kraken 4、Ethereum Foundation main wallet
  - 交易所钱包阈值设为 1000 万美元，避免热钱包常规流水刷屏

关键产品目标：

1. TG 群里不要再发平白、低价值、泛泛新闻。
2. 先把最相关的、对交易研究有帮助的快讯和一手信号发出来。
3. 不能给买入/卖出/做多/做空建议。
4. 用“观察、风险、强度、置信、复核原因”的方式表达。
5. 尽量减少人工工作，但不要让低质量 AI/规则误发污染群。
6. 中长期要能回测：发布后 1h/4h/24h/72h 是否有异常收益、波动或新闻跟随。

请重点回答：

1. 当前 first-hand watcher 的源优先级是否合理？下一批最该接什么源？
2. 现在的质量 gate 是否太松或太严？请给一版更好的 production gate 规则。
3. 交易所热钱包监控如何避免日常流水噪音？是否应该默认只做净流入/净流出聚合，而不是单笔转账？
4. Hyperliquid 大仓位应如何发？哪些仓位应发，哪些应只记录不发？
5. 稳定币 treasury in/out/mint/burn 应如何解释才不误导？
6. 是否应该把一手链上信号和二手新闻放在同一个 TG 群流里，还是分层/分频道/分标签？
7. 目前最大残留风险是什么？请按严重程度排序。
8. 未来 7 天应该做什么，按“必须做 / 应该做 / 不要做”列出来。
9. 哪些功能看起来很酷但现在不该做？
10. 如果你是项目经理，你会如何定义 v0.8 的验收标准？

不要写空泛愿景。请给真实、有取舍、可执行的意见。
