# Market Radar v1.10-J — 只读安全清单

**result_source**: `claude_code_executor`
**task_id**: `20260604_162516.r04`
**run_id**: `20260604_162516`
**generated_at**: `2026-06-04 17:00:00 UTC+8`

---

## 当前可用脚本（安全使用）

### 测试（不发送）
| 脚本 | 说明 |
|------|------|
| `python scripts/test_market_radar_card_router_v110a.py` | Card Router 测试 (28/28) |
| `python scripts/test_market_radar_signal_trust_gate_v110c.py` | SignalTrustGate 测试 (26/26) |
| `python scripts/test_market_radar_pre_send_gate_v110g.py` | pre_send_gate 测试 (16/16) |
| `python scripts/test_market_radar_sender_gate_coverage_v110h.py` | Sender Gate Coverage 测试 (15/15) |

### 本地运行（dry-run，不发送）
| 脚本 | 说明 |
|------|------|
| `python scripts/run_market_radar_v110a_free_cards.py` | 采集 free signal + 卡渲染（不发送 TG） |

### 安全组件（导入使用，不直接运行）
| 脚本 | 说明 |
|------|------|
| `scripts/market_radar_card_router.py` | Card Router 核心逻辑 |
| `scripts/market_radar_signal_trust_gate.py` | SignalTrustGate 核心逻辑 |
| `scripts/market_radar_pre_send_gate.py` | pre_send_gate 通用接口 |
| `scripts/market_radar_sender.py` | Sender 框架（调用者须自行 gate） |
| `scripts/market_radar_tg_formatting.py` | TG 格式化工具 |
| `scripts/market_radar_signal_merge.py` | 信号合并逻辑 |

---

## 当前禁止脚本（不要运行）

| 脚本 | 原因 |
|------|------|
| `_v110b_real_tg_single_card_send.py` | 已过时，使用 SignalTrustGate 直调而非 pre_send_gate() |
| `_v110d_prod_dry_run_signal_gate.py` | 已过时，dry-run only，不应再作为 active sender |
| `_r2_real_tg_send.py` | 已过时，内含 redacted tokens |
| `start_local_market_radar_loop.ps1` | 禁止启动后台循环 |
| `run_v09_market_radar_cycle.py` | 旧版编排，可能触发 board-level 发送 |
| `send_tg_market_radar_board.py` | Board-level 发送，无 board-level gate |
| `run_local_tg_publisher.py` | v16 pipeline，非 Market Radar 链路 |

---

## 当前测试频道发送命令

### 允许的发送命令（测试频道 only，target_env=test）

```powershell
# 保密加载
. .\scripts\load_local_secrets.ps1

# 单卡测试频道发送
python scripts\_v110e_gate_protected_test_channel_send.py

# 矩阵测试频道发送（最多 3-5 张）
python scripts\_v110f_gate_protected_test_channel_matrix_send.py
```

### 发送前检查顺序

1. ✅ secrets 通过 dot-source 加载：`. .\scripts\load_local_secrets.ps1`
2. ✅ 确认 target_env="test"（非 prod）
3. ✅ 确认 max_send_count ≤ 5
4. ✅ 确认 85/85 测试仍通过
5. ✅ 确认 pre_send_gate() 正常导入
6. ✅ 发送后验证 message_id 有效
7. ✅ 确认 fallback_used == 0

---

## 当前不得执行的命令

| 命令 | 原因 |
|------|------|
| `python scripts\_v110*.py --target-env prod` | 禁止正式频道 |
| `. .\scripts\load_local_secrets.ps1; python scripts\send_tg_market_radar_board.py` | Board 发送无 gate |
| `powershell .\scripts\load_local_secrets.ps1; python ...` | 禁止子进程加载 secrets |
| `Start-Process python ...` | 禁止子进程（secrets 隔离） |
| `python scripts\run_v09_market_radar_cycle.py` | 旧版编排 |
| `.\start_local_market_radar_loop.ps1` | 禁止后台循环 |
| `.\start_local_tg_publisher.ps1` | 禁止后台循环 |

---

## 密钥加载注意事项

1. **必须 dot-source** — 使用 `. .\scripts\load_local_secrets.ps1`（点+空格+路径）
2. **禁止子进程** — 禁止 `powershell .\scripts\load_local_secrets.ps1` 或 `Start-Process powershell`
3. **禁止硬编码** — 不得在 Python 脚本中 hardcode token / chat_id / key
4. **禁止打印** — 不得 print / log / 保存 token / chat_id / key
5. **禁止提交** — 不得 git add / commit 任何含 secrets 的文件
6. **禁止环境变量外泄** — 不在 handoff / inventory / result 中包含 token 等敏感字段

---

## 发送前检查顺序

1. 加载 secrets（dot-source only）
2. 确认 target_env="test"
3. 确认 max_send_count ≤ 5
4. 运行全量测试：`python scripts/test_market_radar_pre_send_gate_v110g.py` 等四组
5. 确认 85/85 仍通过
6. 确认 pre_send_gate 导入正常
7. 执行发送
8. 验证 message_id 有效（非空、非 fake）
9. 确认 status_code == 200
10. 确认 fallback_used == 0
11. 确认未触及正式频道

---

## 失败时停止条件

| 条件 | 动作 |
|------|------|
| 任一测试失败 | 停止，排查后重新运行全量测试 |
| gate blocked > 0 | 停止发送，记录 blocked_reason |
| status_code ≠ 200 | 停止，检查网络和 TG 连接 |
| fallback_used > 0 | 停止，检查 MarkdownV2 转义 |
| message_id 为空或 fake | 停止，检查 TG API 响应 |
| target_env ≠ test | 立即停止，不得继续 |
| 密钥泄露检测触发 | 立即停止，排查输出 |
| 后台循环被启动 | 立即停止，kill 进程 |

---

⚠️ 仅供观察，不构成交易建议。
