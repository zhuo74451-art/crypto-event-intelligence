# Market Radar v116N — User Decision Tree

**Generated**: 2026-06-05 14:11:49 UTC+8
**Overlay Version**: v116N

> 下图帮助你从当前里程碑状态出发，选择下一步行动路径。
> 当前状态：Fixture E2E 5/5 | Real TG Sent 3/5 | Gate Blocked 1/5 | Manual Blocked 1/5 | Production 0/5

---

## Decision Tree

```
START: v116N Milestone Package
│
├─ Q: 你认可当前 demo 边界吗？
│   (3/5 real E2E TG sent, 2/5 with design-justified blocks)
│   │
│   ├─ YES → 【路径 A】接受当前里程碑，进入下一阶段优先级选择
│   │         → 阅读 v116l_next_phase_roadmap.md
│   │         → 讨论 P0-P4 优先级排序
│   │         → 确认下一步执行计划
│   │
│   └─ NO → 回到具体关切：
│       │
│       ├─ 最关心 whale → 【路径 B】
│       │   → 先补人工证据 workbook
│       │   → 阅读 v116n_whale_manual_evidence_checklist.md
│       │   → 完成 4 个地址的归属验证
│       │   → rerun v115R submission validator + v115Q fixture E2E gate
│       │
│       └─ 最关心 liquidation → 【路径 C】
│           → 等待高波动窗口
│           → 不降低 gate 阈值
│           → one-shot rerun when: OI delta > threshold OR
│             funding rate extreme OR L/S ratio shift
│
├─ Q: 你想上线生产吗？
│   │
│   └─ 不管选什么 → 先建立 production readiness gate
│       → 阅读 v116n_production_readiness_checklist.md
│       → 当前 0/5，不允许直接上线
│       → 必须满足 6 个最低条件后才能进入 production send 流程
│
└─ Q: 你只想做作品集 / demo？
    │
    └─ YES → 当前可进入 demo 包整理
        → 阅读 v116n_demo_sequence_10min.md
        → 使用 10 分钟展示顺序进行演示
        → 当前 3/5 类卡片可真实演示
```

---

## 三选项详细说明

### 路径 A：接受当前里程碑，进入优先级选择

- **适合**：你对 3/5 real E2E demo + 2/5 justified blocks 的状态满意
- **下一步**：
  1. 确认 v116L 交付包的内容和状态
  2. 阅读 `v116l_next_phase_roadmap.md` 了解 P0-P4 路线图
  3. 共同排序下一步优先级（adapter abstraction, Gemini audit, etc.）
- **风险**：无 — 这是当前设计路径的延续

### 路径 B：先补 whale manual evidence

- **适合**：Whale position alert 是你的最高优先级卡片
- **下一步**：
  1. 阅读 `v116n_whale_manual_evidence_checklist.md`
  2. 收集 4 个地址的链上归属证据
  3. 填入 operator workbook
  4. 重新运行 v115R submission validator + v115Q fixture E2E gate
- **风险**：人工证据收集可能耗时，取决于地址复杂度

### 路径 C：等待高波动，rerun liquidation

- **适合**：Liquidation pressure 是你的最高优先级，且你愿意等待市场波动
- **触发条件（任一满足）**：
  - BTC/ETH/SOL 中任一资产 24h OI delta 超过配置阈值
  - Funding rate 达到极端值（正或负）
  - Long/Short ratio 出现显著偏移
- **执行方式**：one-shot（不开启 daemon/cron/loop）
- **安全约束**：不降低 admission threshold，不绕过 quality gate
- **风险**：Gate 阈值是设计阶段的设定；如果多次 rerun 仍不通过，需要复盘阈值合理性

---

## 红线规则（适用于所有路径）

| 规则 | 原因 |
|------|------|
| 不允许直接上线生产 | 0/5 production ready |
| 不允许降低 liquidation gate | 会破坏 gate 信任度 |
| 不允许绕过 whale evidence | 虚假证据 = 不可靠卡片 |
| 不允许启用 daemon/cron/loop | 系统为 one-shot 模式 |
| 不允许调用付费 API | 当前数据源均为免费公开 API |
