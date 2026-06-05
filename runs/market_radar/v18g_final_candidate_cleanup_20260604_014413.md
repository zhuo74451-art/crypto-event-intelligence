# Market Radar v1.8G Final Candidate Cleanup Report

生成时间：2026-06-04 01:44:13 UTC+8
task_id: 20260604_014224

## 修复内容

### 1. 移除校验行（生成脚本修复）

在 `scripts/generate_static_position_review_v2.py` 的 `generate_v18g_send_prep()` 函数中，
移除了以下两行从 TG 候选卡正文的输出：

```python
# 删除：
f"▫️ 入场价校验：{entry:,.4f} → 偏差 {ep_dev*100:.4f}% → {ep_cons}"
f"▫️ 清算距离校验：显示 {pct_abs(liq_dist)} → 推算 ... → 偏差 {ld_dev*100:.4f}% → {liq_cons}"
```

这些校验信息现在仅保留在 `send_candidate.json` 和 `send_gate_report.md` 中。

### 2. 修复 PnL 正负号（生成脚本修复）

新增 `pnl_money_cn()` 函数，为浮盈值添加显式 `+` 号前缀。
修改前：`当前盈亏：4669.85万美元（+87.5%）`
修改后：`当前盈亏：+4669.85万美元（+87.5%）`

同时修复 `pnl_signed_cn` JSON 字段，确保 JSON 中的 PnL 也携带符号。

### 3. 优化持仓数量显示（生成脚本修复）

修改 `money_coin()` 函数，将"百万枚"单位改为更符合中文习惯的"万枚"层级：
修改前：`持仓数量：1.4百万枚 HYPE`
修改后：`持仓数量：138.0万枚 HYPE`

## 最终候选卡正文

```
<b>🚀 主力仓位雷达｜HYPE 多头大户浮盈</b>

【HYPE 大额仓位地址｜HYPE 多头】当前持仓约 1.00亿美元

▫️ 持仓规模：1.00亿美元
▫️ 持仓数量：138.0万枚 HYPE
▫️ 均价：38.68美元
▫️ 当前盈亏：+4669.85万美元（+87.5%）
▫️ 当前价格：72.51美元
▫️ 清算价：54.93美元
▫️ 距清算：24.3%

🔥 注：该地址为 Hyperliquid 上大规模持仓地址，当前卡片仅展示其 HYPE 多头。

📌 地址：0x082e...ca88

Hyperliquid 查看：https://app.hyperliquid.xyz/

⚠️ 仅供观察，不构成交易建议。
```

## 验收清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | executor_lane = market_radar | ✅ |
| 2 | 当前目录为 事件情报系统 | ✅ |
| 3 | 候选卡正文无"入场价校验" | ✅ |
| 4 | 候选卡正文无"清算距离校验" | ✅ |
| 5 | 候选卡正文无 consistency/deviation/pass | ✅ |
| 6 | 当前盈亏显示 + 号 | ✅ +4669.85万美元 |
| 7 | 距清算仍为 24.3% | ✅ |
| 8 | 无完整地址 | ✅ 仅 0x082e...ca88 |
| 9 | 禁用词为 0 | ✅ forbidden_terms_count=0 |
| 10 | recommended_to_send=true 仅 1 条 | ✅ |
| 11 | should_send_now=false | ✅ |
| 12 | requires_user_confirmation=true | ✅ |
| 13 | secret scan leak_count=0 | ✅ |
| 14 | 未发送 TG | ✅ |
| 15 | 未调用 Telegram API | ✅ |
| 16 | 未启动后台任务 | ✅ |
| 17 | 未调用付费接口 | ✅ |
| 18 | 未写服务器或远程数据库 | ✅ |
