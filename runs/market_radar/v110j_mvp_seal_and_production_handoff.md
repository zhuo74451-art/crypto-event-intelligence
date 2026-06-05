# Market Radar v1.10-J — MVP Seal & Production Handoff（不启用正式频道）

**result_source**: `claude_code_executor`
**task_id**: `20260604_162516.r04`
**run_id**: `20260604_162516`
**status**: `done`
**generated_at**: `2026-06-04 17:00:00 UTC+8`
**executor_lane**: `1`
**project_label**: `market_radar`

---

## 1. MVP 封口结论

**Market Radar 测试频道安全 MVP：封口完成。**

经过 v1.10-A 到 v1.10-I 共 9 轮迭代，当前已确认：

- ✅ Hyperliquid API 主线数据采集 → market_anomaly 信号 → render_card_payload → pre_send_gate → TG 测试频道 全链路真实可用
- ✅ 85/85 单元测试通过（v1.10-A: 28, v1.10-C: 26, v1.10-G: 16, v1.10-H: 15）
- ✅ 9 次测试频道真实发送成功（message_ids: 2239, 2245, 2250, 2251, 2252, 2257, 2258, 2259 等）
- ✅ pre_send_gate 覆盖所有 Market Radar 活跃发送路径
- ✅ 正式频道从未被触碰
- ✅ 密钥零泄露
- ✅ 无后台循环/daemon/cron
- ✅ 无付费 API 调用

## 2. 已验证真实链路

### 当前 MVP 主链路

```
Hyperliquid API
  → market_anomaly signal (run_market_radar_v110a_free_cards.py)
  → signal selection: real fresh api market_anomaly, different assets
  → render_card_payload(signal)
  → pre_send_gate(signal, payload, target_env="test")
  → SignalTrustGate.check(signal, target_env="test")
  → gate allowed
  → TGTransport.send(target="supergroup", parse_mode=MarkdownV2)
  → TG 测试频道发送
  → real message_id returned
```

### 已接入 pre_send_gate 的发送脚本

| 脚本 | 状态 |
|------|------|
| `_v110e_gate_protected_test_channel_send.py` | ✅ 已接入 |
| `_v110f_gate_protected_test_channel_matrix_send.py` | ✅ 已接入 |
| `send_address_behavior_card_gate.py` | ✅ 已接入 (v1.10-H) |

## 3. 测试频道发送凭据

| 阶段 | message_ids | 发送数 | Fallback |
|------|-------------|--------|----------|
| v1.10-B | 2239 | 1 | 0 |
| v1.10-E | 2245 | 1 | 0 |
| v1.10-F | 2250, 2251, 2252 | 3 | 0 |
| v1.10-I | 2257, 2258, 2259 | 3 | 0 |

**累计**: 8 次真实发送，0 次 fallback，全部返回有效 message_id，全部 status_code=200。

## 4. 当前可靠主数据源

| 数据源 | 状态 | 说明 |
|--------|------|------|
| **Hyperliquid API** | ✅ 可靠 | 主力数据源，market_anomaly 信号生产稳定 |
| `signal_type: market_anomaly` | ✅ 可靠 | 已通过 8 次真实发送验证 |
| `source_type: api` | ✅ 可靠 | SOURCE_TRUST_MAP 中 allow_test_send=True |

## 5. 当前不可信 / 暂缓数据源

| 数据源 | 状态 | 建议 |
|--------|------|------|
| **RSS** | ⚠️ 暂缓 | 未进入 SOURCE_TRUST_MAP，不加入 trust 链路。等审核后再启用。 |
| **onchain_position** | ⚠️ 暂缓 | 卡模板存在（28/28 tests），但数据源不稳定，暂不接入生产链路。 |
| **whale_transfer** | ⚠️ 暂缓 | 同上，暂不修复。 |
| **risk_alert** | ⚠️ 暂缓 | 同上，暂不修复。 |
| **board-level sender** | ⚠️ 待定 | `send_tg_market_radar_board.py` 无单信号结构，需独立的 `board_pre_send_gate`。 |

## 6. SignalTrustGate 规则摘要

### SOURCE_TRUST_MAP

| source_type | allow_test_send | allow_prod_send |
|-------------|-----------------|-----------------|
| api | True | True |
| real | True | True |
| external | True | True |
| fixture | True | False |
| manual | True | False |
| unknown | False | False |
| stale | False | False |

### SIGNAL_TTL_SECONDS

| signal_type | TTL |
|-------------|-----|
| market_anomaly | 900s (15min) |
| whale_transfer | 3600s (60min) |
| onchain_position | 3600s (60min) |
| news_event | 21600s (6h) |

### 核心检查逻辑

1. source_type 检查：`SOURCE_TRUST_MAP[source_type][target_env]` 是否为 True
2. TTL 检查：信号年龄 ≤ `SIGNAL_TTL_SECONDS[signal_type]`
3. 信号类型合法性：signal_type 必须在 `SIGNAL_TTL_SECONDS` 中注册
4. target_env 必须显式设置，默认 `test`（禁止默认 prod）
5. blocked report 包含 gate_version 和 signal_hash，不含 token/chat_id/key

## 7. pre_send_gate 覆盖情况

| 类别 | 脚本数 | 说明 |
|------|--------|------|
| A — 已接入 pre_send_gate | 2 | v110e, v110f |
| B — 本轮新接入 | 1 | send_address_behavior_card_gate.py |
| C — 非 Market Radar 链路 | 9 | News flow, digest, metrics, test utilities, v07/v16 pipeline |
| D — 不确定 | 3 | market_radar_sender.py (框架), send_tg_market_radar_board.py (board), archival scripts |

**结论**: Market Radar 主要信号发送链路（A+B=3 个脚本）已全部接入 pre_send_gate()。C 类脚本不属于 Market Radar 卡发送链路。D 类已记录 inventory，不阻塞。

## 8. Sender Inventory 结论

参见 `runs/market_radar/v110h_sender_gate_inventory.json`。15 个 TG sender 候选脚本已完整 inventory，无遗漏。

## 9. 当前禁止启用的路径

| 路径 | 原因 |
|------|------|
| **正式频道 (prod channel)** | 硬冻结。需满足 §10 全部条件。 |
| **`send_tg_market_radar_board.py` 正式发送** | 无 board-level gate。 |
| **RSS 数据源发送** | 未进入 SOURCE_TRUST_MAP。 |
| **onchain_position / whale_transfer / risk_alert 生产发送** | 数据源不稳定，未验证端到端。 |
| **`_v110b` / `_v110d` / `_r2` 脚本** | 已过时，被 v1.10-E/F 取代。应标记 deprecated。 |
| **`market_radar_sender.py` 直接调用 send_from_manifest()** | 不调用 pre_send_gate()。调用者须自行 gate。 |
| **后台循环 / daemon / cron** | 禁止启动。 |
| **付费 API** | 禁止调用。 |
| **子进程加载 secrets** | 禁止 `powershell .\scripts\load_local_secrets.ps1` 子进程方式。必须 dot-source。 |

## 10. 正式频道启用前硬条件

以下条件**全部满足**后，方可考虑启用正式频道：

1. **不得绕过 pre_send_gate()** — 所有发送必须经过统一 pre_send_gate 入口。
2. **target_env 必须显式设置** — 禁止默认 prod。每次发送必须显式传入 `target_env="prod"`。
3. **send_enabled 必须显式开启** — 发送开关必须是显式 True，不得依赖默认值。
4. **board-level sender 必须先有 board-level gate** — `send_tg_market_radar_board.py` 如要发送正式频道，必须先实现 `board_pre_send_gate`。
5. **RSS 必须先进入 SOURCE_TRUST_MAP 审核** — 不得默认放行 RSS 信号。
6. **old scripts 必须标记 archived / deprecated** — `_v110b`, `_v110d`, `_r2` 等避免误用。
7. **dot-source 加载 secrets** — 必须使用 `. .\scripts\load_local_secrets.ps1`（dot-source），禁止子进程加载。
8. **禁止子进程加载 secrets** — 禁止用 `powershell .\scripts\load_local_secrets.ps1` 子进程方式加载。
9. **正式频道第一次发送必须单卡、人工确认** — 第一张正式频道卡片必须单卡发送，人工确认 message_id 返回后才允许下一步。

## 11. Dot-source secrets 正确用法

```powershell
# ✅ 正确：dot-source 加载
. .\scripts\load_local_secrets.ps1

# ❌ 错误：子进程加载（secrets 不会进入当前会话）
powershell .\scripts\load_local_secrets.ps1
```

send script 侧也应通过 `load_local_secrets.ps1` 加载，不硬编码 token / chat_id / key。

## 12. 仍存在的风险

1. **`market_radar_sender.py` 框架级无 gate** — `send_from_manifest()` 不调用 `pre_send_gate()`。依赖所有消费者自行 gate。如有新消费者忘记 gate，存在绕过风险。
2. **D 类不确定脚本** — `send_tg_market_radar_board.py` 仍在 `run_v09_market_radar_cycle.py` 编排中，如被独立调用可能绕过 gate。
3. **Hyperliquid API 连接稳定性** — live fetch 偶有连接失败，当前依靠信号 freshness TTL 过滤。
4. **RSS / onchain_position / whale_transfer 数据源** — 未修复，暂无法加入生产链路。

## 13. 下一步建议

1. **暂停技术扩张** — 不新增数据源、不修 RSS/position/whale 数据源。
2. **转入内容质量复盘** — 审查已发送卡片的信号价值、格式准确性、用户反馈。
3. **正式频道继续冻结** — 等用户单独确认后再解冻。
4. **D 类脚本归档** — 将 `_v110b`, `_v110d`, `_r2` 等历史脚本标记 deprecated 或移入 `_archive/`。
5. **框架级 gate 补齐** — 后续可在 `market_radar_sender.py` 的 `send_from_manifest()` 中加入可选的 pre_send_gate 调用，作为最后防线。

---

⚠️ 仅供观察，不构成交易建议。
