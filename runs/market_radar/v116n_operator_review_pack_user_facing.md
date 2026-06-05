# Market Radar v116N — Operator Review Pack (User-Facing)

> **面向非技术用户 / 项目 Owner 的运营复核包**

**Generated**: 2026-06-05 14:11:49 UTC+8
**Overlay Version**: v116N
**Source Milestone**: v116L

---

## 版本号速查表

如果你看到 v116E/G/I/J/K/L/M/N，先查此表：

| Version | What It Did |
|---------|-------------|
| v116E | Multi-Asset Market Sync — real E2E TG test sent |
| v116G | Price/OI/Volume Anomaly — real E2E TG test sent |
| v116I | Liquidation Pressure — real API attempt, gate blocked (calm market) |
| v116J | News Event Market Impact — real E2E TG test sent (public RSS + REST) |
| v116K | Five-card real E2E coverage audit |
| v116L | Real E2E milestone delivery pack aggregation |
| v116M | Gemini audit of v116L operator pack |
| v116N | User acceptance overlay pack (this version) |

---

## 当前已能演示什么

### ✅ 三类卡片已完成真实 E2E TG 测试发送

**1. Multi-Asset Market Sync**
- 使用 Binance 公开 API（无需 API Key），采集 BTC/ETH/SOL 三资产数据
- 成功检测到市场同步下行风险（score=59.8）
- 完整通过 quality gate + send readiness + secret preflight
- 已通过 TG test group one-shot 发送 1 张卡片

**2. Price/OI/Volume Anomaly**
- 使用 Binance 公开 API 采集三资产价格/持仓量/交易量数据
- 2/3 资产通过入场门禁（ETH -4.44%, SOL -5.46%）；BTC 被门禁正确拒绝
- 已通过 TG test group one-shot 发送 2 张卡片

**3. News Event Market Impact**
- 使用 Binance 公开 RSS + REST（无需 API Key），采集 80 篇文章
- 7 个事件被提取，2 个通过门禁
- 已通过 TG test group one-shot 发送 2 张卡片

### ✅ 五类卡片的 Fixture E2E 全部通过
- 意味着所有五类卡片的算法管道、门禁逻辑、格式化流程均已验证

---

## 不能被误解成什么

### ❌ 不是 production send ready
- **0/5** 类卡片达到生产发送就绪状态
- TG 发送仅限 test group，不可用于生产频道
- 所有卡片为 one-shot 发送，不存在 daemon/loop/定时任务

### ❌ 不是完整的产品
- 这是真实 E2E 里程碑交付包，证明核心管道在真实数据下工作
- 到产品级系统还有空间：持久化、监控、运维、用户自定义等

### ❌ 不是 5/5 完成
- 只有 3/5 类卡片完成了真实 TG 测试发送
- 另外 2/5 不是"未完成"而是"有设计的阻塞"（见下）

---

## SHA-256 消息证明说明

文档中出现的 `sha256:xxxxxxxxxxxxxxxx` 是**脱敏后的指纹**，不是要求用户手动复算。
- 它是 TG 消息内容的 SHA-256 哈希前 16 位
- 作用是：在 TG test group 中按相同算法对消息内容取哈希，如果匹配，就证明消息未被篡改
- **你不会看到 raw token、raw chat_id、raw message_id** — 这些都是脱敏的

---

## 三类已验证卡片的证据摘要

| 卡片类型 | 数据源 | API Type | TG 消息数 | 消息证明（脱敏） |
|----------|--------|----------|-----------|------------------|
| Multi-Asset Market Sync | Binance 公开 API | Free REST | 1 | `sha256:4fbb9cf6972a100c` |
| Price/OI/Volume Anomaly | Binance 公开 API | Free REST | 2 | `sha256:3045ad039274b9fc`, `sha256:1070a982af22fe71` |
| News Event Market Impact | Binance RSS + REST | Free RSS | 2 | `sha256:9d1ef11e7923e54a`, `sha256:9dc6abc967dad3e2` |

---

## News Event Market Impact — 重要风险声明

### ⚠️ News Event Market Impact is observation, not causal proof

**事件影响观察，不构成因果证明。**

- News event cards show **correlation between events and price movements**, not causation.
- An article mentioning BTC price movement does not prove the event caused the movement.
- Multiple factors affect price: the observed event is only one of many possible contributors.
- **Do not use these cards as trading signals.** They are informational observations only.
- All news event cards carry this disclaimer in the TG message body.

---

## 两类未完成卡片的真实阻塞

### Liquidation Pressure — Gate 正确阻断（正常，不是故障）

- **阻塞原因**：当前市场处于 calm market 状态，平仓压力门禁所有信号均未通过
- **已完成**：Binance 公开 REST 数据管道验证通过（3/3 assets fetched）
- **已完成**：信号处理管道验证通过（3/3 signals generated）
- **已完成**：Gate 机制验证通过（在 calm market 下正确阻断）
- **下一步**：等待市场波动增大时 one-shot rerun，不降低 gate 阈值

### Whale Position Alert — 需要人工证据（正常，不是故障）

- **阻塞原因**：Operator workbook 中 4 个地址的字段均为空，免费公开 API 无法提供地址归因信息
- **已完成**：Fixture E2E 管道验证通过（4/4 地址 workflow-ready）
- **已完成**：Router、门禁、格式化流程均验证通过
- **下一步**：完成人工地址证据收集（见 whale evidence checklist）

---

## 为什么 liquidation 不应降 gate

1. Gate 行为正确：在 calm market 下正确阻断，证明了门禁系统的有效性
2. 降低阈值会削弱信任度：如果人为降低阈值来制造"成功"，整个 quality gate 设计将被架空
3. liquidation_pressure 是事件触发型卡片：它的价值在于高波动市场时的预警
4. 数据管道已验证：3/3 assets fetched + 3/3 signals generated
5. 正确做法：等待市场波动增大时重新 one-shot 运行

---

## 下一步人工复核建议

1. **复核 TG test group 中的实际消息**：使用指纹在 test group 中确认 5 条消息
2. **复核 acceptance matrix**：确认五类卡片的状态与理解一致
3. **选择 liquidity 下一步**：确认标记为 `future_volatility_rerun` 是否可接受
4. **选择 whale 下一步**：是否启动 manual evidence collection
5. **确认 demo 边界和路线图优先级**：见 decision tree 文档
