# v11 数据质量优先升级验收报告

- 生成时间：2026-06-01 13:29:50 UTC+8
- 总状态：warning

## 已完成的 Claude P0 要求

- Source Registry：pass，注册源 12 个，live 5 个，shadow 7 个。
- Source Adapter 校验：pass，校验行数 20，失败 0。
- Source Effectiveness：已评估 10 类来源；无 live 证据 7，live 样本不足 3。
- Event Type Performance Matrix：40 个组合，样本不足组合 36。
- Non-Benchmark Alt Matrix：56 个组合，用于减少 BTC/macro benchmark 污染。
- Signal Decay Curve：36 个组合，样本不足组合 32。
- False Positive Analysis：3 个组合，待降噪/补样本分组 3。
- v11 Signal Policy：62 条路由策略，已把历史样本、false-positive 和冷却倍率转为机器可读策略。
- Shadow Mode：当前 shadow 事件 0 条，未证明来源继续进入影子管道。
- Evidence Snippets：3 条，已可用于替换黑箱分数和空泛解读。
- LLM 用量追踪：调用 17 次，估算成本 $1.446432。

## 当前不能夸大的地方

- 多数来源仍然缺少足够 live outcome，不能基于当前样本断言“有效”。
- 历史样本仍受 BTC/macro 污染影响，event_type 层面的表现需要继续拆分和补样本。
- TG 摘要已改为证据驱动，但证据本身还是早期样本，必须显示样本不足提醒。

## 下一步执行顺序

1. 将证据片段进一步接入盘中雷达卡片的逐条证据层，减少黑箱文案。
2. 对 shadow 来源继续累积历史 outcome，满足样本门槛后再转 live。
3. 扩大历史回测样本，优先补非 BTC/macro 的单资产事件，降低 benchmark 污染。
4. 用 false_positive_analysis 的结果反向更新路由阈值和冷却窗口。
