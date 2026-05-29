# 角色

你继续作为这个项目的外部产品负责人 + 量化研究负责人。请用中文回答，直接挑错，不要迎合。

# 我们刚完成的改动

根据你上一轮建议，我们没有继续做盘中雷达，而是把系统改成：

1. Composer 五阶段评分：
   - Stage 1：交易相关性 `trading_relevance_score`
   - Stage 2：结构化质量 `structuring_score`
   - Stage 3：市场归因质量 `attribution_score`
   - Stage 4：历史置信度 `historical_confidence_score`
   - Stage 5：用户可读性 `readability_score`
   - 汇总：`composer_final_score`
   - 路由提示：`composer_route_hint`

2. Publisher 决策：
   - `block`
   - `digest`
   - `interrupt`
   - Publisher 已读取 Composer 结果，且受 Composer 阻断约束。

3. ETF/基金流过滤继续收紧：
   - 单纯 `inflow` 不再算 ETF/基金流。
   - 标题必须有明确 `ETF/fund/filing/issuer` 语境。

4. active exploit 继续要求：
   - 明确 hack/exploit/drain/breach 上下文。
   - 金额解析靠近安全事件上下文。
   - 来源分达标。

# 当前历史样本复跑结果

输入：

- 历史回测样本：281 条
- 文件：`results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv`

Composer 输出：

- `data/v14_composer_scores.csv`
- `results/v14_composer_scores_report.md`
- 输入 281 条
- digest_candidate：18 条
- interrupt_candidate：0 条
- review：23 条
- block：240 条

Publisher 输出：

- `data/v14_publish_policy_candidates.csv`
- `results/v14_publish_policy_report.md`
- 最新 digest：1 条
- interrupt：0 条
- block：280 条

摘要预览：

- `results/v14_digest_preview.md`
- 安全事件 0 条
- ETF/基金流 1 条

补充更新：

- 已新增 `scripts/split_flow_event_subtypes.py`
- Flow 类 57 条拆分结果：
  - ETF specific：48 条
  - CEX netflow：1 条
  - unclear：8 条
- 已增强 `scripts/verify_exploit_amounts.py`
  - 新增 `affected_protocol_hint`
  - 新增 `stolen_assets_detected`
  - 新增 `affected_tradable_asset`
  - 新增 `asset_attribution_confidence`
- 因标题/协议无法证明 ADA/AAVE/BNB 是真正受影响可交易资产，active exploit urgent eligible 从 4 条降为 0 条。

# 仍然暴露的问题

1. Composer digest_candidate 里仍有一些资产归因不确定的内容，比如 ETF 宏观新闻被错误归因到 ADA/AAVE/BNB。
2. 历史置信度 `historical_confidence_score` 目前偏低，但总分还能很高，因为其他阶段满分太多。
3. Publisher 最终只剩 5 条，可能很保守，但也可能终于接近真实可用。
4. `event_subtype=etf_or_fund_flow` 仍可能混入“基金/ETF新闻”和“交易所资金流”两类不同东西。
5. `exploit_or_theft` 仍可能把协议受害资产、攻击所在链、文章中提到的主币混在一起，资产归因不够可靠。
6. 目前没有真正把 pre-event price-in 和 regime filter 变成硬门槛，只是扣分。
7. 目前没有“历史相似事件匹配”，只有 event_subtype 聚合统计。
8. 当前 Telegram 摘要仍可能展示“发布分”，但用户不一定理解。

# 需要你输出

请你继续按工程落地角度给下一轮修改意见，越具体越好：

1. Composer 五阶段的权重和硬门槛怎么改？
2. 哪些字段应该变成硬阻断，而不是扣分？
3. ETF/基金流和 CEX/交易所流入流出应该怎么拆？
4. active exploit 的资产归因应该怎么设计？受害协议、被盗资产、受影响可交易币种分别怎么存？
5. pre-event price-in 和 regime filter 应该如何进入 Publisher？
6. historical similarity 应该用什么最小可行方法实现，不要空谈 embedding。
7. Telegram 摘要里是否应该展示分数？如果不展示，展示什么？
8. 下一轮应该先改哪 5 件事，按优先级排序。
9. 哪些当前成果你认为应该删除或降级？
10. 你认为现在能不能把摘要发到 TG？如果能，发什么；如果不能，还差什么？

请用中文，结论优先，具体到字段/脚本/规则级别。
