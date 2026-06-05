# Market Radar v1.8H 单卡 TG 群发送报告

生成时间：2026-06-04 11:01:00 UTC+8
executor_lane: 1
project_label: market_radar
task_id: 20260604_105425.r03
status: done
result_source: claude_code_executor

## 用户授权摘要

| 项目 | 值 |
|---|---|
| approved_by | user |
| approval_text | "可以发，tg群无所谓" |
| allow_external_send | true |
| allow_tg_group | true |
| allow_tg_channel | false |
| max_send_count | 1 |
| allow_loop | false |
| allow_daemon | false |
| allow_paid_api | false |

## 执行命令

```bash
# Step 1: Chat type verification
python scripts/v18h_verify_chat_type.py
# Result: supergroup (TG群) confirmed

# Step 2: Single card send
python scripts/v18h_single_card_tg_send.py
# Result: sent_count=1, message_id=2174, status=done
```

## 输入文件

| 文件 | 状态 |
|---|---|
| results/static_position_v18g_send_candidate.md | ✅ 存在 |
| results/static_position_v18g_send_candidate.json | ✅ 存在 |
| results/static_position_v18h_preview_report.md | ✅ 存在 |

## 发送目标类型

- **Chat type**: supergroup（TG 群）
- Chat ID: 已脱敏，未打印

## 发送详情

- **sent_count**: 1
- **message_id**: 2174
- **telegram API 调用次数**: 2（getChat 验证 + sendMessage）
- **发送内容**: HYPE 主力仓位雷达卡（319 chars）

### 发送内容摘要

```
<b>🚀 主力仓位雷达｜HYPE 多头大户浮盈</b>

【HYPE 大额仓位地址｜HYPE 多头】当前持仓约 1.00亿美元

持仓规模：1.00亿美元 | 均价：38.68美元
当前盈亏：+4669.85万美元（+87.5%）
清算价：54.93美元 | 距清算：24.3%

地址：0x082e...ca88（短地址，无完整钱包地址）
⚠️ 仅供观察，不构成交易建议。
```

## 安全边界确认

| 检查项 | 状态 |
|---|---|
| 是否发送超过 1 条 | ❌ 否（sent_count=1） |
| 是否发送 TG 频道 | ❌ 否（verified supergroup） |
| 是否启动 loop | ❌ 否 |
| 是否启动 daemon | ❌ 否 |
| 是否创建定时任务 | ❌ 否 |
| 是否调用付费 API | ❌ 否（仅 Telegram Bot API） |
| 是否打印 token / chat_id / API key / cookie / 密码 | ❌ 否 |
| 是否写远程 DB / 生产环境 DB | ❌ 否 |
| 是否删除重要文件 | ❌ 否 |
| 是否回写 article lane | ❌ 否 |
| 是否自动接入后续播报 | ❌ 否 |
| 是否修改候选卡正文 | ❌ 否（原文发送，无修改） |

## 未完成项 / 风险

- 无。任务按规格完成。本次仅发送 1 张测试卡验证 TG 群发送通道。
- 临时脚本 `scripts/v18h_single_card_tg_send.py` 和 `scripts/v18h_verify_chat_type.py` 可保留供后续复用或删除。

## 下一步建议：v1.8I 发送后复盘

1. 确认 message_id=2174 的消息在 TG 群中显示正常（格式、链接、可读性）
2. 收集群内反馈（如有）
3. 评估是否需要在 v1.9 中加入更多卡类型或自动化规则
4. 确认 TG 群发送闸门（gate）是否需要在 v1.9 中进一步收紧
5. 建议保持 `max_send_count=1` 的单卡控制策略直到手动确认无误

---

*报告由 claude_code_executor (lane 1) 自动生成，时间 2026-06-04 11:01 UTC+8*
