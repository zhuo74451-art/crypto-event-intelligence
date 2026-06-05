# Market Radar v1.8G Manual Approval Preview After Liquidation Hotfix

生成时间：2026-06-04 01:37:48 UTC+8
执行端：Claude Code Executor
executor_lane：market_radar

## 1. 当前状态
- 是否已发送 TG：否
- 是否调用 Telegram API：否
- 是否等待用户确认：是
- liquidation distance hotfix 是否完成：是

## 2. 候选卡正文

<b>🚀 主力仓位雷达｜HYPE 多头大户浮盈</b>

【HYPE 大额仓位地址｜HYPE 多头】当前持仓约 1.00亿美元

▫️ 持仓规模：1.00亿美元
▫️ 持仓数量：1.4百万枚 HYPE
▫️ 均价：38.68美元
▫️ 当前盈亏：4669.85万美元（+87.5%）
▫️ 当前价格：72.51美元
▫️ 清算价：54.93美元
▫️ 距清算：24.3%
▫️ 入场价校验：38.6755 → 偏差 0.0002% → pass
▫️ 清算距离校验：显示 24.3% → 推算 24.3% → 偏差 0.0000% → pass

🔥 注：该地址为 Hyperliquid 上大规模持仓地址，当前卡片仅展示其 HYPE 多头。

📌 地址：0x082e...ca88

Hyperliquid 查看：https://app.hyperliquid.xyz/

⚠️ 仅供观察，不构成交易建议。

## 3. 关键修复确认
- 当前价格：72.51美元
- 清算价：54.93美元
- 修复前距清算：0.2%（错误 — ratio 被错误 /100）
- 修复后距清算：24.3%（正确 — 移除多余 /100）
- 是否仍显示 0.2%：否
- liquidation_distance_consistency_status：pass

## 4. 发送闸门摘要
- recommended_to_send 数量：1
- 推荐卡片：0x082e...ca88 HYPE 多头
- PnL/side：多头 + 正浮盈 → 无符号冲突
- entry_price：38.68美元，deviation=0.0002%，status=pass
- liquidation_distance：24.3%，deviation=0.0000%，status=pass
- 禁用词：0（forbidden_terms_count=0）
- 完整地址：0 个完整地址（仅短地址 0x082e...ca88）
- should_send_now：false
- requires_user_confirmation：true

## 5. 用户需要确认
用户必须明确回复以下二选一：

A. 确认发送这 1 张测试卡
B. 不发送，继续修改

## 6. 安全边界
- 是否发送 TG：否
- 是否调用 Telegram API：否
- 是否启动后台任务：否
- 是否调用付费接口：否
- 是否写服务器：否
- 是否写远程数据库：否
- 是否输出敏感凭据：否
