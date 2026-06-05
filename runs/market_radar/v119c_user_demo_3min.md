# Market Radar MVP v119C — 3 分钟用户演示流程

**生成时间**: 2026-06-05T19:00:16+08:00
**Run ID**: 20260605_190016
**基于版本**: v119B (B-lite quality enhancement)

---

## 演示前准备

1. 确保 v119B runner 已执行过一次（已有结果文件）
2. 打开浏览器（Chrome / Edge / Firefox 均可）
3. 本演示不需要联网、不需要 API Key、不需要外部账号

---

## 演示流程 (约3分钟)

### 第 1 步：打开主看板 (30 秒)

在文件管理器中打开：
```
runs/market_radar/v119b_operator_dashboard.html
```
双击用浏览器打开。

**展示要点**：
- 页面顶部显示"Market Radar 策略值班看板 v119B"
- 可以看到 LIVE DATA、B-LITE 两个标签
- Production Readiness 显示 **false / 0/5**
- Telegram Sent 显示 **false**

### 第 2 步：看顶部中文引导 (30 秒)

页面从上往下滚动，第二个区块是"🧭 30 秒中文引导"：

**展示 5 个问题的中文回答**：
1. **📌 这是什么？** → 策略值班看板，不是自动交易/发布系统
2. **👀 现在怎么看？** → 优先看 accept/watch，再看 reject/manual
3. **🚫 现在能不能发？** → production readiness=false，不能正式发布
4. **📡 数据从哪来？** → Binance 公开 API + 免费 RSS + 本地 fixture
5. **📋 操作员下一步？** → accept → 复盘 / watch → 观察 / reject → 等待 / manual → 补证据

### 第 3 步：看五卡总览 (30 秒)

向下滚动到"⚖️ 操作员决策总览"区域：

**展示当前决策分布**：
- ✅ Accept（可复盘）: 1 个
- 👀 Watch（观察）: 2 个
- ❌ Reject（拒绝）: 1 个
- 🔒 Manual Required（需人工）: 1 个

**解释**：
- accept = 强信号通过 gate，可进入人工复盘（当前仅 multi_asset_market_sync）
- watch = 观察级别，不代表可以发布
- reject = gate 正确阻止，等待市场条件
- manual_required = 需要人工补充链上证据（whale 地址归属）

### 第 4 步：展示 B-lite 分层价值 (30 秒)

向下滚动到"🗂️ 操作员决策表"，找到 `price_oi_volume_anomaly` 行：

**展示要点**：
- **Decision 列显示 "👀 WATCH"**
- **B-lite Tier 列显示 "mild_watch"**
- 这不是 accept，这是观察级别
- B-lite 把原本会被 reject 的轻度异常升级为 mild_watch
- **价值**：从 raw reject → mild watch，操作员能看到"值得关注但不值得行动"的信号
- **约束**：watch ≠ accept，watch ≠ publishable

### 第 5 步：展示 news observation-only (30 秒)

在决策表中找到 `news_event_market_impact` 行：

**展示要点**：
- **Obs Only 列 = True**（仅观察）
- **Not Causal 列 = True**（不是因果证明）
- 展示 freshness_info（fresh/stale/unknown 计数）
- 新闻事件市场影响卡片做的是 observation-only
- 不构成因果证明，不构成交易建议
- 操作员仍需阅读原文核实

### 第 6 步：展示 whale 人工证据要求 (30 秒)

在决策表中找到 `whale_position_alert` 行：

**展示要点**：
- Decision 显示 "🔒 MANUAL REQUIRED"
- Pipeline 显示 "blocked"
- Gate Reason 说明需要人工链上地址归属验证
- 手动证据未提供 → gate 正确阻止
- 这不是 bug，这是设计意图
- 不可绕过人工证据要求

### 第 7 步：总结 — 这是什么，这不是什么 (30 秒)

**这是什么**：
- ✅ 本地策略值班看板 MVP
- ✅ 五类市场信号的统一管道
- ✅ 操作员决策辅助工具
- ✅ 免费公开数据源驱动
- ✅ B-lite 信号质量增强

**这不是什么**：
- ❌ 不是自动交易系统
- ❌ 不是自动发帖/发布系统
- ❌ 不是生产环境就绪的系统
- ❌ 不是 AI/ML 驱动的预测系统
- ❌ 不是机构级数据管道

---

## 演示结束

**Production Readiness: false / 0/5**
**telegram_send=false | x_twitter_send=false | production_send=false**
**daemon_or_loop_started=false**

本次演示展示的是 Market Radar MVP 封版包 v119C，
这是一个 local-only / no-send 的本地策略值班看板。
不可用于生产环境，不可作为交易依据。