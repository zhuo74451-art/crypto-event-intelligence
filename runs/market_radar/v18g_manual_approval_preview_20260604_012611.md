# Market Radar v1.8G Manual Approval Preview

生成时间：2026-06-04 01:26:11 UTC+8

## 1. 当前状态
- 是否已发送 TG：否
- 是否调用 Telegram API：否
- 是否等待用户确认：是
- 当前阶段：v1.8G 单卡测试发送准备已完成，等待用户人工确认

## 2. 候选卡正文

---

<b>🚀 主力仓位雷达｜HYPE 多头大户浮盈</b>

【HYPE 大额仓位地址｜HYPE 多头】当前持仓约 1.00亿美元

▫️ 持仓规模：1.00亿美元
▫️ 持仓数量：1.4百万枚 HYPE
▫️ 均价：38.68美元
▫️ 当前盈亏：4669.85万美元（+87.5%）
▫️ 当前价格：72.51美元
▫️ 清算价：54.93美元
▫️ 距清算：0.2%

🔥 注：该地址为 Hyperliquid 上大规模持仓地址，当前卡片仅展示其 HYPE 多头。

📌 地址：0x082e...ca88

Hyperliquid 查看：https://app.hyperliquid.xyz/

⚠️ 仅供观察，不构成交易建议。

---

## 3. 发送闸门摘要
- recommended_to_send 数量：1
- 推荐卡片：0x082e...ca88 HYPE 多头（score=100）
- PnL/side：✅ 一致（多头 + 正浮盈，无符号冲突）
- entry_price：✅ 一致（deviation=0.000169%, status=pass）
- 禁用词：✅ 无（forbidden_terms_count=0）
- 完整地址：✅ 无（仅使用短地址 0x082e...ca88）
- 过度定性表达：✅ 无
- 机器术语：✅ 无（machine_terms_count=0）
- should_send_now：false
- requires_user_confirmation：true
- dry_run_only：true

## 4. 用户需要确认

用户必须明确回复以下二选一：

**A. 确认发送这 1 张测试卡**
**B. 不发送，继续修改**

## 5. 安全边界
- 是否发送 TG：否
- 是否调用 Telegram API：否
- 是否启动后台任务：否
- 是否调用付费接口：否
- 是否写服务器：否
- 是否写远程数据库：否
- 是否输出敏感凭据：否
- 是否做交易相关动作：否

## 6. 验收确认
- ✅ 成功生成 manual approval preview
- ✅ 完整展示候选卡正文
- ✅ 明确 should_send_now=false
- ✅ 明确 requires_user_confirmation=true
- ✅ 明确本轮未发送 TG
- ✅ 明确本轮未调用 Telegram API
- ✅ 没有修改候选卡和闸门报告
