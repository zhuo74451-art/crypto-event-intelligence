# External AI Review Packet v1

> 用于把仓库交给其他 AI 或研究者做独立、批判性的第二轮审阅。

## 1. Project Summary

Crypto Event Intelligence 是一个证据型加密事件研究系统。它保存事件事实和来源语境，将来源输出标准化为 Observation，通过确定性规则过滤噪音，把相关 Observation 合并为事件级 Signal，并记录可审计的价格反应。

它不是交易机器人、收益承诺系统或已经完成的因果归因引擎。当前正确定位是：**research baseline，尚非 production system。**

## 2. Key Evidence Entry Points

| File | Purpose |
|------|---------|
| `README.md` | 项目定位、边界和运行入口 |
| `docs/PROJECT_OVERVIEW.md` | 问题定义、设计选择和成熟度 |
| `docs/ARCHITECTURE.md` | 当前对象流、模块边界和去重层级 |
| `docs/PROJECT_STATUS.md` | 组件状态表 |
| `research/week1_raw_research_dataset_v1.json` | 统一原始研究数据集 |
| `docs/research/week1_raw_research_dataset_v1.md` | 数据集说明 |
| `docs/audits/week1_raw_research_dataset_v1_release_evidence.md` | 实现侧发布证据矩阵，不是第三方审计 |
| `docs/releases/week1_raw_research_dataset_v1_release.md` | 发布范围和限制 |
| `docs/roadmap/NEXT_PHASE_PLAN_V1.md` | 后续 Phase 0–5 路线图 |

## 3. Verified Facts

- 5 个事件样本、6 条样本关联、5 个唯一价格观察。
- `w1_003` 与 `w1_004` 是两个不同事件，但共享同一 BTC 同时点价格观察。
- HYPE 使用 Hyperliquid 15m Candle，signed lag 为 -120 秒。
- BTC/ETH 使用 Binance 1m Kline，当前样本 lag 为 0 秒。
- Manifest、Price Dataset、Unified Dataset 三个仓库 validator 通过。
- 文档 validator 通过；执行端报告全仓 233 项测试通过。
- Network 输出没有 fixture source。
- Dataset builder 只读取本地 JSON，连续构建产物 byte-identical。
- 数据集没有归因置信度、因果评分或交易行动字段。

这些事实不代表研究方法已经被独立验证。

## 4. Facts, Design Choices, Inferences, Hypotheses

### Facts

- 当前五条样本的 `event_time_utc` 均为空，t0 使用 `broadcast_time_utc`。
- Hyperliquid 和 Binance Provider 都是公开只读接口。
- Hyperliquid 支持多个 Candle 周期，包括 1m 和 15m。
- Week 1 选择 HYPE 15m 是为了覆盖历史日期，不是因为接口只支持 15m。
- `w1_003` 与 `w1_004` 的观察资产和播报时间一致，因此共享同一价格观察键。

### Design Choices

- 原始字段与标准化字段并存，标准化值不覆盖原始事实。
- 真实事件时间缺失时，以 broadcast_time 作为可审计 t0。
- HYPE 采用 15m `nearest_candle_open`，最大绝对偏差 450 秒。
- BTC/ETH 采用 1m `first_after_target`，最大偏差 120 秒。
- Abnormal return 当前定义为资产收益减去 BTC 或 ETH 基准收益。
- Network 失败返回 unavailable/error，不静默回退 fixture。
- 相同市场观察可以复用，但不同事件样本保持独立。

### Inferences

以下判断尚未被充分验证：

- broadcast_time 足够接近信息真正进入市场的时点。
- 当前 max-lag 阈值适合所有事件类型。
- BTC/ETH 双基准足以表达市场共同波动。
- 当前 Noise Gate 不会系统性偏爱或漏掉某类事件。
- 当前事件 dedup key 能处理复杂更新、反转和父子事件。

### Unverified Hypotheses

- 五条样本足以暴露归因协议的主要结构问题。
- 当前数据模型可以自然扩展到 30–50 条分层样本。
- Price observation dedup 不会丢失归因所需的事件差异。
- 可以建立一个不依赖事后解释的归因置信度协议。

## 5. Questions External Reviewers Should Attack

1. broadcast_time 会引入哪些延迟、选择偏差和信息泄漏？
2. 未来事件分类应按主体、机制、资产暴露还是预期冲击组织？
3. source quality、staleness、tradable asset、pump risk 等规则会产生哪些系统性误判？
4. 错误合并和错误拆分，哪一种对研究结论危害更大？
5. 简单减 BTC/ETH 的 abnormal return 是否过于粗糙？
6. 什么资产应以 BTC、ETH、板块指数或自身历史波动为基准？
7. 同时多个事件共享一条价格路径时，哪些情况必须判定无法归因？
8. 如何记录宏观、清算、其他新闻、流动性和市场结构干扰？
9. 时间接近性、来源可靠性、资产特异性、机制一致性和替代解释应如何进入归因置信度？
10. 如何预注册规则，避免看完价格后再选择最有利叙事？
11. 时间对齐、样本选择、窗口选择和人工标签中有哪些 look-ahead 风险？
12. 哪些模块是漂亮工程，但没有足够研究信息增量？
13. 在不继续堆代码的前提下，什么最小实验可以推翻或支持当前设计？

## 6. Required Output from Reviewing AI

审阅结果必须：

- 不复述仓库文档。
- 区分 bug、方法论缺陷、产品缺陷和证据不足。
- 标注 P0/P1/P2，并为每个 P0 给出证据或可复现实验。
- 不把相关性写成因果。
- 指出可以删除的过度设计。
- 指出目前不能回答的问题。
- 给出下一阶段最小验证方案，而不是直接扩功能。

## 7. Copyable Chinese Review Prompt

> 请作为严格的加密事件研究系统审计者，审查本仓库的 `main` 分支以及 PR #2 的审计历史。
>
> 项目定位是加密事件事实整理、噪音过滤、价格反应回填与后续归因研究的证据型系统，不是交易系统。
>
> 先阅读 `README.md`、`docs/PROJECT_OVERVIEW.md`、`docs/ARCHITECTURE.md`、`docs/PROJECT_STATUS.md`、`research/week1_raw_research_dataset_v1.json`、发布证据和路线图。
>
> 然后：
> 1. 区分 bug、方法论缺陷、产品缺陷和证据不足。
> 2. 标记 P0/P1/P2，并为每个 P0 给出可复现实验。
> 3. 指出哪些部分是漂亮工程但研究价值有限。
> 4. 检查 broadcast_time、价格窗口、benchmark 和人工选样中的数据泄漏或事后偏差。
> 5. 判断当前 5/6/5 数据结构是否适合归因研究。
> 6. 指出哪些结论必须保持证据不足。
> 7. 给出下一阶段最小验证方案，不要假设归因已经实现。
