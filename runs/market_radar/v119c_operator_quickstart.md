# Market Radar MVP v119C — 操作员快速使用说明

**生成时间**: 2026-06-05T19:00:16+08:00
**Run ID**: 20260605_190016
**版本**: v119C MVP seal (based on v119B)
**模式**: local-only / no-send

---

## 1. 手动运行 v119B

在当前项目目录下执行：

```powershell
python scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py
```

这会：
- 从 Binance 公开 REST API 获取实时价格数据（不需要 API Key）
- 从免费 RSS 源获取新闻
- 运行五卡共享管道
- 生成 v119B 所有输出文件
- 不发送 Telegram、不发送 X/Twitter、不写生产状态

**运行时间**：约 10-20 秒（取决于网络）

---

## 2. 打开 Dashboard

用浏览器打开：
```
runs/market_radar/v119b_operator_dashboard.html
```

或在文件管理器中双击该文件。

---

## 3. 每天使用流程

### Step 1: run one-shot
```powershell
python scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py
```

### Step 2: open dashboard
双击 `runs/market_radar/v119b_operator_dashboard.html`

### Step 3: check accept/watch
先看 ✅ Accept（可复盘）和 👀 Watch（观察），再查看原因。

### Step 4: check reject/manual_required reason
reject 通常是 gate 正确阻止（如市场平静期 liquidation 不触发），
manual_required 是需要补充人工证据（如 whale 地址归属验证）。

### Step 5: record observation manually
在本地笔记本或日志中记录观察结果。
不要依赖系统自动记录 — 当前没有 operator review log 功能。

---

## 4. 停止 / 关闭

**无 daemon**：不需要停止任何后台进程。

**无后台进程**：runner 是一次性执行，执行完即退出。

**关掉浏览器即可**：dashboard 是静态 HTML，关闭浏览器标签页即结束。

---

## 5. ⛔ 禁止事项

### 不得当交易建议
本系统是策略值班看板，用于观察市场信号。
**不构成任何投资建议或交易建议。**
所有信号仅供参考，实际决策由操作员自行负责。

### 不得直接正式发布
当前 production readiness = false / 0/5。
telegram_send=false, x_twitter_send=false, production_send=false。
**不得将本系统的输出直接发布到任何生产渠道。**

### 不得绕过 manual evidence
whale_position_alert 要求人工链上地址归属验证。
**不得绕过此要求强行通过 gate。**

### 不得改 production readiness
production readiness 固定为 false / 0/5。
**不得在代码或配置中将其改为 true。**

---

## 6. 问题排查

### Dashboard 空白或数据缺失
重新运行 v119B runner（见第 1 步）。
如果 runner 报错，检查网络连接（Binance API 需要联网）。

### 所有卡都是 reject
检查市场条件 — 平静期很多卡会被正确 reject。
这是正常行为，不是 bug。

### HTML 显示乱码
用现代浏览器（Chrome/Edge/Firefox）打开。
文件编码为 UTF-8。

---

**Production Readiness: false / 0/5 — NOT FOR LIVE USE**