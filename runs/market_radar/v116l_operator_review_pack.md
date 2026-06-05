# Market Radar v116L — Operator Review Pack

> **面向用户验收的运营复核包**

**Generated**: 2026-06-05 13:56:06 UTC+8
**Milestone**: v116L
**Source Range**: v116A-v116K

---

## 当前已能演示什么

✅ **三类卡片已完成真实 E2E TG 测试发送**：

1. **Multi-Asset Market Sync (v116E)**
   - 使用 Binance 公开 API（无需 API Key），采集 BTC/ETH/SOL 三资产数据
   - 成功检测到市场同步下行风险（score=59.8）
   - 完整通过 quality gate + send readiness + secret preflight
   - 已通过 TG test group one-shot 发送 1 张卡片
   - 消息证明（脱敏）：`sha256:4fbb9cf6972a100c`

2. **Price/OI/Volume Anomaly (v116G)**
   - 使用 Binance 公开 API 采集三资产价格/持仓量/交易量数据
   - 2/3 资产通过入场门禁（ETH -4.44%, SOL -5.46%）
   - BTC 被入场门禁正确拒绝（price_chg=-2.24%, OI 数据缺失）
   - 已通过 TG test group one-shot 发送 2 张卡片
   - 消息证明（脱敏）：`sha256:3045ad039274b9fc` (ETH), `sha256:1070a982af22fe71` (SOL)

3. **News Event Market Impact (v116J)**
   - 使用 Binance 公开 RSS + REST（无需 API Key），采集 80 篇文章
   - 7 个事件被提取，2 个通过门禁
   - 完整通过 quality gate + send readiness + secret preflight
   - 已通过 TG test group one-shot 发送 2 张卡片
   - 消息证明（脱敏）：`sha256:9d1ef11e7923e54a`, `sha256:9dc6abc967dad3e2`
   - ⚠️ 所有卡片携带风险声明：**事件影响观察，不构成因果证明**

✅ **五类卡片的 Fixture E2E 全部通过**
- 意味着所有五类卡片的算法管道、门禁逻辑、格式化流程均已验证

---

## 不能被误解成什么

❌ **不是 production send ready**
- 0/5 类卡片达到生产发送就绪状态
- TG 发送仅限 test group，不可用于生产频道
- 所有卡片为 one-shot 发送，不存在 daemon/loop/定时任务

❌ **不是完整的产品**
- 这是真实 E2E 里程碑交付包，证明核心管道在真实数据下工作
- 到产品级系统还有空间：持久化、监控、运维、用户自定义等

❌ **不是 5/5 完成**
- 只有 3/5 类卡片完成了真实 TG 测试发送
- liquidation_pressure 被 gate 正确阻断（calm market）
- whale_position_alert 需要人工链上证据

---

## 三类已验证卡片的证据

### 证据链

| 卡片类型 | 数据源 | API Type | TG 消息数 | 消息证明（脱敏） | 来源任务 |
|----------|--------|----------|-----------|------------------|----------|
| Multi-Asset Market Sync | Binance 公开 API | Free REST | 1 | `sha256:4fbb9cf6972a100c` | v116E |
| Price/OI/Volume Anomaly | Binance 公开 API | Free REST | 2 | `sha256:3045ad039274b9fc`, `sha256:1070a982af22fe71` | v116G |
| News Event Market Impact | Binance RSS + REST | Free RSS | 2 | `sha256:9d1ef11e7923e54a`, `sha256:9dc6abc967dad3e2` | v116J |

### 验证方式

- 所有消息证明为 SHA-256 脱敏指纹，可在 TG test group 中按消息内容复算验证
- TG evidence index (v116L) 包含完整脱敏索引，共 5 条记录
- 无 raw token、raw chat_id、raw message_id 出现在任何输出中

---

## 两类未完成卡片的真实阻塞

### Liquidation Pressure — `blocked_gate_not_passed`

- **阻塞原因**：当前市场处于 calm market 状态，平仓压力门禁所有信号均未通过
- **数据集**：v116I 成功通过 Binance 公开 REST 获取 BTC/ETH/SOL 数据
- **信号生成**：3/3 资产成功生成信号
- **信号准入**：0/3 通过（gate 正确工作）
- **已完成的工作**：
  - Binance 公开 REST 数据管道验证通过（3/3 assets fetched）
  - 信号处理管道验证通过（3/3 signals generated）
  - Gate 机制验证通过（在 calm market 下正确阻断）

### Whale Position Alert — `blocked_manual_evidence`

- **阻塞原因**：Operator workbook 中 4 个地址的字段均为空
- **已完成的工作**：
  - Fixture E2E 管道验证通过（4/4 地址 workflow-ready）
  - Router、门禁、格式化流程均验证通过
- **缺失**：真实链上地址归因证据（无法通过免费 API 自动获取）

---

## 为什么 liquidation 不应降 gate

1. **Gate 行为正确**：在 calm market 下正确阻断 0/3 信号，这证明了门禁系统的有效性
2. **降低阈值会削弱信任度**：如果人为降低阈值来制造"成功"，整个 quality gate 设计将被架空
3. **liquidation_pressure 是事件触发型卡片**：
   - 它的价值在于高波动市场时的预警，而非低信号环境下的"为了发送而发送"
   - 不应为了凑"5/5 完成"而破坏卡片类型的本质
4. **数据管道已验证**：3/3 assets fetched + 3/3 signals generated 证明管道可运行
5. **正确做法**：等待市场波动增大时（OI delta 突破阈值、funding rate 极端值、L/S ratio 显著偏移）重新 one-shot 运行

---

## 为什么 whale 需要人工 evidence workbook

1. **链上地址归因无法自动化**：
   - 免费 API（Binance/Etherscan/Solscan 公开接口）不提供地址归因信息
   - 链上数据只能显示交易，不能自动判断"谁"在执行交易
2. **虚假证据比没有证据更糟**：
   - 如果使用 mock 或推测数据填充 workbook，卡片将无实际价值
   - whale_position_alert 的信任度取决于证据的真实性
3. **人工证据是最低可行路径**：
   - Operator 需要完成地址归属验证（v115O preflight 范围）
   - 完成后可重新运行 v115R submission validator + v115Q fixture E2E gate
4. **不应绕过**：任何自动化尝试都会导致低质量、不可靠的卡片输出

---

## 下一步人工复核建议

1. **复核 TG test group 中的实际消息**：
   - 使用消息证明指纹（SHA-256）在 test group 中确认 5 条消息的内容
   - 检查消息格式、数据准确性、风险声明是否存在

2. **复核 acceptance matrix**：
   - 确认五类卡片的状态与理解一致
   - 确认 0/5 production send ready 是正确的

3. **决定 liquidation_pressure 下一步**：
   - 确认是否同意将 liquidation 标记为 `future_volatility_rerun`
   - 讨论高波动 rerun 的触发条件和时机

4. **决定 whale_position_alert 下一步**：
   - 是否启动 manual evidence collection 任务
   - 如果需要，指定 operator 和 completion criteria

5. **决定是否启动 Gemini 审计** (P1)：
   - 让 Gemini 审计 operator pack 的可读性、风险边界和产品展示效果
   - 在进入 production readiness 阶段前完成独立审查
