# Market Radar MVP v119C — 已知限制 & 下一阶段建议

**生成时间**: 2026-06-05T19:00:16+08:00
**Run ID**: 20260605_190016
**版本**: v119C MVP seal (based on v119B)

**状态**: local-only / no-send / not production-ready
**telegram_send**: false | **x_twitter_send**: false | **production_send**: false

---

## ⚠️ 已知限制 (Known Limits)

### 1. news freshness 是规则启发式
- freshness 分类基于标题关键词和来源名称的规则匹配
- 不是基于实际发布时间戳的精确判断
- 可能存在误判（把旧文章标为 fresh，或把新文章标为 stale）
- 操作员仍需查看原文发布日期确认时效性

### 2. price/OI watch 是观察，不是交易建议
- mild_watch 分层是规则驱动的启发式判断
- 轻度异常升级为 watch 只表示"值得关注"
- 不代表价格将朝任何方向变动
- **不可作为交易依据**

### 3. liquidation 仍受真实市场条件限制
- 使用本地 fixture 数据，非实时链上数据
- 平静市场期 gate 正确阻止 → 无输出
- 需要高波动市场窗口才能触发
- 不能保证在每次 liquidation 事件时都能捕获

### 4. whale 仍需人工证据
- 地址归属没有自动化验证方案
- 免费公开 API 无法提供地址归属信息
- 需操作员手动完成 v116N whale evidence workbook
- 在人工证据完成前，whale_position_alert 始终为 manual_required

### 5. dashboard 是本地静态 HTML
- 不是动态 Web 应用
- 没有实时数据推送或自动刷新
- 需要手动运行 runner 后重新打开
- 数据是运行时刻的快照，不会自动更新

### 6. one-shot 需要手动运行
- 没有 daemon/cron/loop 自动刷新
- 操作员需要手动执行 python 命令
- 没有 UI 界面触发运行
- 每次运行需要 10-20 秒网络请求时间

### 7. 数据源限制
- 仅使用 Binance 免费公开 REST API（有速率限制）
- 新闻源为免费 RSS（CoinDesk/Cointelegraph/Decrypt/The Block）
- liquidation 和 whale 使用本地 fixture（模拟数据）
- 没有付费数据源、没有 WebSocket 实时流、没有机构级 feed

### 8. 无 operator review log
- 操作员观察结果需要手动记录
- 没有内置的观察日志或历史记录功能
- 无法回顾之前的决策和执行

---

## 📋 下一阶段建议 (只列候选，不执行)

以下为下一阶段候选方向，**本轮 v119C 不执行任何一项**。
是否执行、何时执行需单独决策。

### 候选 1: manual whale evidence intake
- 操作员完成 v116N whale evidence workbook
- 包含链上地址归属验证证据
- 完成后 whale_position_alert 可能从 manual_required 升级
- **不自动执行此步骤 — 需操作员人工完成**

### 候选 2: 多日手动稳定性记录
- 连续多日手动运行 one-shot 并记录结果
- 观察信号稳定性和变化模式
- 收集足够数据以评估系统可靠性
- **不自动执行 — 需操作员持续手动操作**

### 候选 3: dashboard 历史对比
- 保存多日 snapshot 以便对比
- 添加历史数据查看功能
- 可能需要将静态 HTML 升级为简单应用
- **不自动执行 — 需额外开发工作**

### 候选 4: operator review log
- 添加操作员观察记录功能
- 记录每次查看的决策和备注
- 可能需要本地存储（JSON/SQLite）
- **不自动执行 — 需额外开发工作**

### 候选 5: TG test-group optional send
- 在有明确工单授权且 lane 权限允许时
- 可向 TG 测试群发送观察卡片
- 必须在明确工单中授权，不可自动触发
- **不自动执行 — 需单独工单授权**

---

## 🚫 明确不要做的事

- ❌ 不要自动启动 recurring/daemon/cron
- ❌ 不要降低 liquidation threshold
- ❌ 不要绕过 whale manual evidence
- ❌ 不要把 production readiness 改成 true
- ❌ 不要新增策略信号
- ❌ 不要改 gate 阈值
- ❌ 不要自动发 TG/X/Twitter
- ❌ 不要调用 AI/model API

---

**Production Readiness: false / 0/5 — NOT FOR LIVE USE**