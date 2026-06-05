# Market Radar v1.8G Liquidation Distance Hotfix Report

生成时间：2026-06-04 01:35:49 UTC+8
执行端：Claude Code Executor
executor_lane：market_radar

## 1. 根因分析

### 修复前状态
- 候选卡：0x082e...ca88 HYPE 多头
- 当前价格：72.51 美元
- 清算价：54.93 美元
- **卡片显示：距清算 0.2%**（错误）
- 人工计算应为：(72.51 - 54.93) / 72.51 × 100 ≈ 24.2%

### 根因定位
文件：`scripts/generate_static_position_review_v2.py` 第 346 行

```python
# 修复前（错误）：
lines.append(f"▫️ 距清算：{pct_abs(liq_dist/100)}")
# liq_dist = 0.242510 (ratio from CSV)
# pct_abs(0.242510/100) = pct_abs(0.002425) = abs(0.002425)*100 = 0.2%
```

CSV 中 `liquidation_distance_pct` 字段存储的是 **ratio**（0.242510 = 24.2510%），而非百分比。但渲染代码错误地将其再除以 100，导致显示为 0.2%。

### 数据来源验证
- `watch_hyperliquid_positions.py:175`: `abs(mark_px - liquidation_px) / mark_px` → ratio
- CSV 存储值：0.242510（ratio）
- `build_tg_market_radar_board.py:478`: `(current - liq) / current * 100` → 百分比
- 结论：CSV 存储 ratio，其他脚本（`build_raw_signals.py`、`aggregate_hyperliquid_snapshot_with_baseline.py`）均正确乘以 100 显示

### 修复方案
```python
# 修复后（正确）：
lines.append(f"▫️ 距清算：{pct_abs(liq_dist)}")
# pct_abs(0.242510) = abs(0.242510)*100 = 24.3%
```

## 2. 采用公式

### 多头（long）
```
距清算 = (mark_price - liquidation_price) / mark_price × 100
```

### 空头（short）
```
距清算 = (liquidation_price - mark_price) / mark_price × 100
```

### HYPE 多头验证
```
(72.514 - 54.9286) / 72.514 × 100 = 24.3%
```

## 3. 新增：liquidation_distance 一致性校验

### 新增函数
- `compute_implied_liquidation_distance(mark_px, liq_px, side)` — 从 mark_px 和 liq_px 推算清算距离
- `liquidation_edge_case_blocked(mark_px, liq_px, side)` — 检查边界异常

### 新增卡片字段
- `implied_liquidation_distance_pct` — 推算的清算距离（ratio）
- `liquidation_distance_deviation_pct` — 偏差（abs(displayed - implied)）
- `liquidation_distance_consistency_status` — pass/blocked
- `blocked_reasons` — 阻塞原因列表

### 阻塞规则
1. 偏差 > 0.01（1 个百分点 in ratio space）→ blocked，原因 `liquidation_distance_inconsistent`
2. long 且 liquidation_px >= mark_px → blocked，原因 `liquidation_price_above_mark_long`
3. short 且 liquidation_px <= mark_px → blocked，原因 `liquidation_price_below_mark_short`
4. 无清算价的卡片：不参与校验，不显示清算相关信息
5. blocked 卡不能 recommended_to_send

## 4. 所有有清算价卡片的校验结果

| 卡片 | 显示距清算 | 推算距清算 | 偏差% | 状态 |
|---|---|---|---|---|
| 0x082e...ca88 HYPE 多头 | 24.3% | 24.3% | 0.0000% | pass |
| 0x6c85...84f6 ETH 多头 | 24.6% | 24.6% | 0.0000% | pass |
| 0x50b3...9f20 BTC 空头 | 4.5% | 4.5% | 0.0000% | pass |

- 有清算价卡片数量：3
- pass 数量：3
- blocked 数量：0
- 最大偏差：≈0.000%

## 5. 发送候选检查

- recommended_to_send=true 数量：1
- 推荐卡片：0x082e...ca88 HYPE 多头
- 当前价格：72.51 美元
- 清算价：54.93 美元
- **距清算：24.3%**（修复后）
- should_send_now：false
- requires_user_confirmation：true

## 6. 禁用词与安全检查

- 禁用词检查：0（无禁用词）
- 完整地址检查：0 个完整地址出现在 Markdown 正文
- secret scan：leak_count=0, status=pass

## 7. 安全边界

- 是否发送 TG：否
- 是否调用 Telegram API：否
- 是否启动后台循环/定时任务/daemon：否
- 是否调用外部付费接口：否
- 是否写服务器：否
- 是否写远程数据库：否
- 是否输出敏感凭据：否
- 是否做交易相关动作：否

## 8. 修改 / 生成文件

### 修改脚本
- `scripts/generate_static_position_review_v2.py` — 修复清算距离显示 + 新增清算距离一致性校验 + 新增 v18g send prep 生成

### 重新生成的 review_v2 文件
- `results/static_position_cards_review_v2.md`
- `results/static_position_cards_review_v2.csv`
- `results/static_position_cards_review_score_v2.md`
- `results/static_position_cards_review_summary_v2.md`

### 重新生成的 v18g send prep 文件
- `results/static_position_v18g_send_candidate.md`
- `results/static_position_v18g_send_candidate.json`
- `results/static_position_v18g_send_gate_report.md`

### Hotfix 报告
- `runs/market_radar/liquidation_distance_hotfix_20260604_013549.md`

## 9. 结论

✅ **清算距离修复完成，可重新进入人工确认预览**

- 根因：ratio 值错误地除以 100 后再乘以 100
- 修复：移除多余的 /100 除法
- 新增：liquidation_distance 一致性校验机制
- 所有卡片 pass 校验，无 blocked
- 推荐卡片唯一性保持（1 张）
- 所有安全检查通过
