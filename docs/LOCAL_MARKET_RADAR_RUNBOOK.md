# Local Market Radar Runbook

v09 市场雷达 → 本地长期运行 → Telegram 发布。

---

## 架构

```text
config/local_secrets.ps1          (密钥，不提交 Git)
        ↓
. .\config\local_secrets.ps1      (设置环境变量)
        ↓
scripts/run_v09_market_radar_cycle.py  (Python 主循环)
    ├── run_v07_first_hand_watchers.py     (Hyperliquid + Etherscan 监控)
    ├── route_tg_items_by_severity.py      (事件路由)
    ├── watch_binance_long_short_ratios.py (多空比)
    ├── build_v11_signal_policy.py         (信号策略)
    ├── build_tg_market_radar_board.py     (构建雷达板)
    ├── send_tg_market_radar_board.py      (发送 TG)
    └── ... (12 quality report 步骤)
        ↓
logs/local_market_radar_loop.log   (日志)
runtime/local_market_radar_loop.pid (PID)
```

---

## 0. 一次性设置

```powershell
# 切到项目目录
cd C:\Users\PC\Desktop\Projects\事件情报系统

# 确认密钥文件存在（不打印内容）
Test-Path config\local_secrets.ps1
# 应返回 True

# 确认必需脚本存在
Test-Path scripts\run_v09_market_radar_cycle.py
# 应返回 True
```

如果 `config\local_secrets.ps1` 不存在：
```powershell
copy config\secrets.example.ps1 config\local_secrets.ps1
# 编辑 config\local_secrets.ps1 填入真实 token 和 chat_id
```

---

## 1. 单次运行

### 1.1 预览模式（不发 TG，安全）

```powershell
.\scripts\run_local_market_radar_once.ps1
```

自定义参数：
```powershell
.\scripts\run_local_market_radar_once.ps1 -Hours 12 -LimitAlerts 50
```

### 1.2 真实发送到 TG

`-Send` 会自动检测 `TELEGRAM_CHAT_ID` 或 `TELEGRAM_PUBLISH_CHAT_IDS`，哪个有值用哪个。

```powershell
# 确认密钥已设置
. .\config\local_secrets.ps1

# 发送（自动检测 chat_id 变量名）
.\scripts\run_local_market_radar_once.ps1 -Send

# 如果 local_secrets.ps1 用的是 TELEGRAM_PUBLISH_CHAT_IDS，显式指定：
.\scripts\run_local_market_radar_once.ps1 -Send -ChatIdEnv TELEGRAM_PUBLISH_CHAT_IDS
```

---

## 2. 长期运行

### 2.1 预览模式（后台运行，不发 TG）

```powershell
.\scripts\start_local_market_radar_loop.ps1
```

### 2.2 真实发送到 TG

```powershell
.\scripts\start_local_market_radar_loop.ps1 -Send
```

自定义间隔（默认 3600 秒 = 1 小时）：
```powershell
.\scripts\start_local_market_radar_loop.ps1 -Send -IntervalSeconds 1800
```

---

## 3. 查看状态

```powershell
.\scripts\status_local_market_radar_loop.ps1
```

---

## 4. 停止

```powershell
.\scripts\stop_local_market_radar_loop.ps1
```

如果 PID 文件丢失但进程仍在运行：
```powershell
# 查找 PowerShell 子进程
Get-Process powershell* | Select-Object Id, StartTime

# 手动停止（替换 <PID>）
Stop-Process -Id <PID> -Force
```

---

## 5. 查看日志

```powershell
# 单次运行日志
Get-Content logs\local_market_radar_once.log -Tail 30

# 长期运行日志（最后 30 行）
Get-Content logs\local_market_radar_loop.log -Tail 30

# 实时跟踪
Get-Content logs\local_market_radar_loop.log -Wait -Tail 10

# 只看出错行
Select-String -Path logs\local_market_radar_loop.log -Pattern "ERROR|FATAL|exit=[^0]"
```

---

## 6. 停止后重启

```powershell
# 停止
.\scripts\stop_local_market_radar_loop.ps1

# 确认已停
.\scripts\status_local_market_radar_loop.ps1

# 重启
.\scripts\start_local_market_radar_loop.ps1 -Send
```

---

## 7. 生成的文件

| 文件 | 说明 |
|------|------|
| `results/v09_market_radar_cycle_summary.csv` | 周期运行摘要 |
| `results/v09_tg_market_radar_board.md` | 雷达板 Markdown 预览 |
| `results/v09_tg_market_radar_board_summary.csv` | 雷达板统计 |
| `results/v09_tg_market_radar_send_summary.csv` | 发送记录 |
| `data/tg_market_radar_boards.csv` | 板面数据 |
| `data/tg_drafts_v09_routed.csv` | 路由后草稿 |
| `logs/local_market_radar_loop.log` | 长期运行日志 |
| `logs/local_market_radar_once.log` | 单次运行日志 |
| `runtime/local_market_radar_loop.pid` | PID 文件 |

---

## 8. 风险边界

| 项目 | 边界 |
|------|------|
| **运行位置** | 本地 Windows 电脑，不是服务器 |
| **服务器连接** | **只读**。读取 Hyperliquid 公开 API、Binance 公开 API、Etherscan（如有 key）。不写服务器数据库、不重启服务 |
| **TG 发送** | 默认 **不发**。需要 `-Send` 开关 |
| **密钥** | 只在 `config/local_secrets.ps1` 中，已 `.gitignore`，不写入日志 |
| **频率限制** | 默认每 3600 秒（1 小时）一轮 |
| **后台运行** | PowerShell 后台进程，非 Windows 服务 |
| **开机自启** | **不会**。需手动启动 |
| **交易建议** | 每条消息含"不构成任何交易建议"免责声明 |
| **LLM 费用** | v09 radar cycle 内部可能调用 Claude/OpenRouter（`--ai-review` 等步骤需确认），**但默认循环不含 `--ai-review` 参数，不会调用** |

---

## 9. 故障排查

### 发送失败
```powershell
# 检查 token 是否设置
. .\config\local_secrets.ps1
python -c "import os; print('Token set:', bool(os.environ.get('TELEGRAM_BOT_TOKEN')))"

# 测试单条发送
python scripts/test_local_tg_send.py --send
```

### 循环不执行
```powershell
# 检查 PID
.\scripts\status_local_market_radar_loop.ps1

# 如果显示 NOT RUNNING，重新启动
.\scripts\start_local_market_radar_loop.ps1 -Send
```

### Hyperliquid 数据无更新
```powershell
# 检查 API key
. .\config\local_secrets.ps1
python -c "import os; print('Etherscan key set:', bool(os.environ.get('ETHERSCAN_API_KEY')))"
```
