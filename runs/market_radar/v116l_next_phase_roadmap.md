# Market Radar v116L — Next Phase Roadmap

**Generated**: 2026-06-05 13:56:06 UTC+8
**Milestone**: v116L

---

## Priority Roadmap

### P0: v116L 交付包验收

- **目标**：用户确认当前 milestone deliverable 包的内容和状态
- **关键行动项**：
  - [ ] 阅读 operator review pack
  - [ ] 复核 acceptance matrix 中的五类卡片状态
  - [ ] 确认 TG evidence index 中的 5 条脱敏证明
  - [ ] 确认 0/5 生产发送就绪状态的理解
  - [ ] 确认 liquidation 不降 gate、whale 不绕过 manual evidence 的决定
- **验收标准**：用户签字确认 v116L 交付包内容完整、状态准确

### P1: Gemini 审计 operator pack

- **目标**：用 Gemini 独立审计 operator review pack 的质量
- **审计维度**：
  - 可读性：operator 是否能理解当前状态和下一步
  - 风险边界：是否明确区分了 test 和 production、可发布和不可发布
  - 产品展示效果：operator pack 作为用户验收文档是否足够清晰
- **注意事项**：Gemini 审计是辅助性检查，不替代人工判断

### P2: liquidation_pressure 高波动时 one-shot rerun

- **目标**：在市场波动增大时重新运行 liquidation_pressure 真实 API + TG test send
- **触发条件（任一满足即可）**：
  - BTC/ETH/SOL 中任一资产 24h OI delta 超过配置阈值
  - Funding rate 达到极端值（正或负）
  - Long/Short ratio 出现显著偏移
  - 市场整体波动率指标（VIX proxy）超过阈值
- **执行方式**：one-shot，不允许后台常驻/循环/定时
- **安全约束**：不降低 admission threshold，不绕过 quality gate
- **注意事项**：当前 gate 阈值是在设计阶段设定的，如果多次 rerun 仍无法通过，
  可能需要复盘阈值合理性，但不应在市场环境不变时降低

### P3: whale_position_alert manual evidence checklist/workbook

- **目标**：创建人工地址证据收集的 checklist 和 workbook
- **内容**：
  - [ ] 4 个地址的链上基础信息（交易数、余额、首次活跃时间）
  - [ ] 地址标签/归属证据（交易所钱包、做市商、鲸鱼地址等）
  - [ ] 证据来源和验证方式（区块浏览器、标签服务、链上分析工具）
  - [ ] 每个地址的置信度评估
- **完成后**：重新运行 v115R submission validator + v115Q fixture E2E gate
- **注意**：这是人工任务，不可由自动化执行

### P4: 三类已验证卡片抽象 shared adapter/gate/sender

- **目标**：从三类已验证卡片中抽象共享组件，提高代码复用性
- **范围**：
  - 共享 data adapter 接口（Binance REST 调用标准化）
  - 共享 quality gate 接口（门禁逻辑可配置化）
  - 共享 sender 接口（TG 格式化 + 脱敏发送标准化）
- **不启用**：后台常驻、定时任务、循环、生产发送
- **注意事项**：抽象是代码质量优化，不改变功能行为

---

## What NOT to do

| 禁止行为 | 原因 |
|----------|------|
| 启动生产发送 | 0/5 production ready |
| 启动后台常驻/定时/循环 | 系统仍为 one-shot 模式 |
| 降低 liquidation gate 阈值 | 会破坏 gate 信任度 |
| 绕过 whale manual evidence | 会导致低质量/不可靠卡片 |
| 调用付费 API | 当前所有数据源为免费公开 API |
| 发送到 X/Twitter 或生产目标 | lane 1 仅允许 TG test-group 发送 |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| liquidation 市场长期 calm，gate 永远通不过 | Low | Low | Gate threshold 可在复盘后调整，但需有数据支撑 |
| whale 人工证据始终未收集 | Medium | Medium | 明确创建 task + deadline，指定 owner |
| 用户误以为 3/5 意味着接近完成 | Medium | High | Operator pack 明确标注 0/5 production ready |
| 共享 adapter 抽象引入 bug | Low | Medium | 抽象后保持现有测试覆盖，增加 adapter contract test |
