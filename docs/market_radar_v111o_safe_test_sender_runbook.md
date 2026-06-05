# Market Radar — Safe Test Sender Runbook (v1.11-O)

**Version**: v1.11-O
**Status**: MVP 主体闭环完成，ARB 是唯一测试群候选，ETH 暂缓
**Last updated**: 2026-06-04

---

## 当前状态

- Market Radar MVP 主体闭环完成：信号值门、同资产冷却门、发送前总门、信任门均已上线并通过验证。
- ARB H6-07 已通过全部 8 层内容/目标校验（v1.11-L → v1.11-N），是唯一测试群发送候选。
- ETH 两张卡片暂缓 — 不进入发送 readiness。
- v1.11-N 的 SafeTelegramTestSender 因运行时缺少 `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` 被 Gate 9 安全阻断。
- 正式频道继续冻结 — 不做任何生产发送。

---

## 为什么不能把 token/chat_id 写入项目文件

1. **项目文件会被 git 追踪**：一旦 token 进入仓库历史，即使后续删除，历史记录中仍然存在。
2. **多人协作风险**：项目文件可能被分享、推送、或通过其他渠道泄漏。
3. **CI/CD 环境**：项目文件中的凭证会被 CI 系统和日志记录。
4. **审计不可追溯**：写入文件的凭证无法区分谁在使用 — 运行时环境变量可以配合日志记录调用来源。

**规则：凭证只允许在用户本机运行环境中临时设置，严禁写入任何项目文件。**

---

## 为什么不能在工单中要求用户贴 token

1. **工单系统可能有日志**：AI Relay Desk、GPT 工单、执行日志都可能记录输入内容。
2. **中间代理风险**：工单在多个执行层之间传递 — 任何一层都可能记录或泄露。
3. **安全性降级**：要求贴 token 等同于把凭证当作明文传输，违背最小暴露原则。
4. **不可撤销**：一旦 token 进入工单系统，无法确保所有副本已删除。

**规则：工单中不应包含任何凭证。执行端不得读取、打印、保存凭证。**

---

## 凭证只允许在用户本机运行环境中临时设置

设置方式（PowerShell）：

```powershell
# 仅为当前 PowerShell 会话设置（关闭终端后消失）
$env:TELEGRAM_BOT_TOKEN = "your_bot_token_here"
$env:TELEGRAM_CHAT_ID = "your_test_channel_chat_id_here"
```

或通过系统环境变量（持久设置）：

```powershell
[System.Environment]::SetEnvironmentVariable('TELEGRAM_BOT_TOKEN', 'your_bot_token_here', 'User')
[System.Environment]::SetEnvironmentVariable('TELEGRAM_CHAT_ID', 'your_test_channel_chat_id_here', 'User')
```

**注意**：
- `TELEGRAM_CHAT_ID` 必须指向**测试频道**（test channel），不是正式频道。
- 正式频道的 chat_id 不应被设置或使用。
- 执行完成后可以通过 `Remove-Item Env:TELEGRAM_BOT_TOKEN` 清除临时变量。

---

## 执行端不得读取、打印、保存凭证

- **不得读取** `.env` 文件或任何本地配置文件中的凭证。
- **不得打印** token 或 chat_id 到 stdout、stderr、日志文件。
- **不得保存** token 或 chat_id 到 JSON、Markdown、或其他输出文件。
- **只能检查** 凭证是否存在（布尔值）— 不能输出实际值。
- **不要求** 用户在交互式提示中输入凭证（不使用 Read-Host / input()）。
- **不调用** Telegram API 仅为了验证 token（Token 正确性由实际发送验证）。

---

## 正式频道继续冻结

以下目标类型被硬编码阻止：

- `formal_channel`
- `official_channel`
- `prod`
- `production`
- `main_channel`

**只允许 `test_channel` → `market_radar_test_channel`。**

---

## 真实发送流程

### 发送前 — 运行 readiness 检查

```powershell
python scripts/check_market_radar_sender_runtime_v111o.py
```

这将输出 readiness 结果而不泄露任何凭证值。

### 真实发送（仅限测试群）

```powershell
python scripts/run_market_radar_v111n_safe_single_arb_test_send.py
```

安全保证：
- 只发送 ARB H6-07（ETH 被硬阻止）
- 只发送到测试频道（正式频道被硬阻止）
- 最多发送 1 张卡片
- 不读取 .env
- 不使用交互式输入
- 不打印/保存凭证值
- 凭证缺失时安全阻断（不崩溃）

### 发送后 — 运行复盘 stub

```powershell
python scripts/run_market_radar_v111o_post_send_review_stub.py
```

生成包含以下内容的 review packet skeleton：
- message_id
- signal_id
- asset
- payload_hash
- public_card preview
- checklist: Markdown 渲染、链接预览、移动端可读性、免责声明、是否像交易建议

---

## 安全检查清单

运行发送前确保：

- [ ] TELEGRAM_BOT_TOKEN 已在运行环境中设置
- [ ] TELEGRAM_CHAT_ID 指向测试频道（非正式频道）
- [ ] token/chat_id 未写入任何项目文件
- [ ] token/chat_id 未出现在 git status 中
- [ ] 已运行 `check_market_radar_sender_runtime_v111o.py` 确认 readiness
- [ ] 正式频道目标仍被冻结

---

## 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| `missing_runtime_test_channel_credentials` | 环境变量未设置 | 在 PowerShell 中设置 `$env:TELEGRAM_BOT_TOKEN` 和 `$env:TELEGRAM_CHAT_ID` |
| `eth_blocked` | 尝试发送 ETH 卡片 | ETH 暂缓 — 只发 ARB H6-07 |
| `formal_channel_blocked` | 尝试发送到正式频道 | 将 chat_id 改为测试频道 |
| `debug_terms_in_payload` | 卡片内容包含内部调试术语 | 检查 public_card 文本 — 不应包含 gate/内部术语 |

---

## 版本历史

| Version | Date | Change |
|---------|------|--------|
| v1.11-O | 2026-06-04 | Safe test sender runbook — credential policy, readiness check, send flow |
