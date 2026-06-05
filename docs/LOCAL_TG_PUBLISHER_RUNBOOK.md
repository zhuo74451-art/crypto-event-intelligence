# Local TG Publisher Runbook

v16 事件卡片 → Telegram Bot 本地发布桥。

---

## 架构

```text
config/local_tg_publisher.env  (密钥)
        ↓
scripts/run_local_tg_publisher.py  (主循环)
        ↓
v16 pipeline (build_raw → aggregate → render)
        ↓
results/v16_asset_event_cards.md  (卡片)
        ↓
parse → dedup (SQLite) → rate limit → TG send
        ↓
logs/local_tg_publisher.log  (日志)
data/local_tg_publisher_state.sqlite  (去重状态)
```

---

## 1. 配置本地 .env

```powershell
# 复制模板
copy config\local_tg_publisher.env.example config\local_tg_publisher.env

# 编辑 config\local_tg_publisher.env，填入真实值：
# TELEGRAM_BOT_TOKEN=123456:ABCdef...   (从 @BotFather 获取)
# TELEGRAM_CHAT_ID=-1001234567890       (先用测试群!)
# PUBLISH_MODE=test
# DRY_RUN=true
```

**不要提交 `config/local_tg_publisher.env` 到 Git！**

---

## 2. 验证配置（dry-run）

```powershell
# 测试发送（不实际发，只打印预览）
python scripts/test_local_tg_send.py

# 发送 1 条真实测试消息
python scripts/test_local_tg_send.py --send
```

确认测试群里收到了消息后再继续。

---

## 3. 运行单个循环（dry-run）

```powershell
# 跑一次完整循环，查看会生成什么卡片
python scripts/run_local_tg_publisher.py --once

# 查看日志
Get-Content logs\local_tg_publisher.log -Tail 30
```

日志会显示每张卡片的内容预览和发送状态。

---

## 4. 启动长期运行

```powershell
# 确认 DRY_RUN=true 在 .env 中
# 启动后台进程
.\scripts\start_local_tg_publisher.ps1

# 查看进程
Get-Process python* | Where-Object { $_.Id -eq (Get-Content runtime\local_tg_publisher.pid) }

# 实时查看日志
Get-Content logs\local_tg_publisher.log -Wait -Tail 10
```

---

## 5. 切换为真实发送

```powershell
# 1. 先停止
.\scripts\stop_local_tg_publisher.ps1

# 2. 编辑 config\local_tg_publisher.env，设置：
#    DRY_RUN=false
#    PUBLISH_MODE=test  (仍然先发测试群)

# 3. 重启
.\scripts\start_local_tg_publisher.ps1
```

**警告：DRY_RUN=false 后消息会真实发送到 TG！**

---

## 6. 停止

```powershell
.\scripts\stop_local_tg_publisher.ps1
```

如果 PID 文件丢失但进程仍在运行：

```powershell
# 查找
Get-Process python* | Select-Object Id, StartTime, CommandLine

# 手动停止（替换 <PID> 为实际进程 ID）
Stop-Process -Id <PID> -Force
```

---

## 7. 查看日志

```powershell
# 最后 30 行
Get-Content logs\local_tg_publisher.log -Tail 30

# 实时跟踪
Get-Content logs\local_tg_publisher.log -Wait -Tail 10

# 只看发送记录
Select-String -Path logs\local_tg_publisher.log -Pattern "SENT|DRYRUN|ERROR"
```

---

## 8. 查看/清空去重状态

```powershell
# 查看已发送记录
python -c "
import sqlite3
conn = sqlite3.connect('data/local_tg_publisher_state.sqlite')
rows = conn.execute('SELECT event_id, sent_at, status, card_title FROM sent_events ORDER BY sent_at DESC LIMIT 20').fetchall()
for r in rows:
    print(f'{r[1]} | {r[2]:8s} | {r[3][:60]}')
conn.close()
"

# 查看周期统计
python -c "
import sqlite3
conn = sqlite3.connect('data/local_tg_publisher_state.sqlite')
rows = conn.execute('SELECT started_at, signals_built, events_agg, cards_sent, cards_skipped, dry_run FROM cycle_log ORDER BY id DESC LIMIT 10').fetchall()
for r in rows:
    mode = 'DRYRUN' if r[5] else 'REAL'
    print(f'{r[0]} | sig={r[1]} ev={r[2]} sent={r[3]} skip={r[4]} {mode}')
conn.close()
"

# 清空去重状态（重置后所有卡片会被重新发送！）
# 先停止 publisher，再删除数据库文件：
# Remove-Item data\local_tg_publisher_state.sqlite
```

---

## 9. 风险边界

| 项目 | 边界 |
|------|------|
| TG 发送 | **默认 DRY_RUN=true，不发送** |
| 频率限制 | 每循环最多 MAX_SEND_PER_CYCLE 条（默认 3） |
| 去重 | SQLite content_hash 去重，同卡片不重复发 |
| 交易建议过滤 | 自动屏蔽含"买入/卖出/做多/做空"等词的消息 |
| 免责声明 | 每条消息自动追加"仅作市场结构观察，不构成交易建议" |
| 密钥 | 只从环境变量/.env 读取，不写入代码/日志 |
| LLM/API 费用 | **不调用任何 LLM 或付费 API** |
| 后台运行 | Windows PowerShell 后台进程，非系统服务 |
| 开机自启 | **不会**自动开机启动 |

---

## 10. 默认不调用 LLM

本发布器纯做本地 CSV → 聚合 → TG 发送，不调用：
- Claude / OpenRouter
- OpenAI
- Gemini
- 任何 LLM API

如果需要 AI 润色后再发，那是后续功能，需要用户单独授权。
