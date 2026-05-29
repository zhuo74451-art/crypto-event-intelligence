# Source Adapter Schema

本文件定义所有一手 watcher、快讯导入器、日历源、衍生品源进入系统时必须输出的最小结构。目标不是做优雅抽象，而是解决当前真实问题：新源接入后字段不一致，后续回测、路由、Telegram 账本和质量评估难以复用。

## 标准输出层级

每个源至少应进入两层之一：

1. `raw_alert`：源自己的原始告警快照，可保留源特有字段。
2. `normalized_event`：统一事件字段，必须能进入回测、路由和账本。

当前 v1.1 优先要求所有源都能产出 `normalized_event`。

## normalized_event 必填字段

| 字段 | 说明 |
|---|---|
| `event_id` | 本地唯一 ID。 |
| `event_time` | UTC ISO 或可解析时间。 |
| `event_time_china` | 中国时间展示字段，格式 `YYYY-MM-DD HH:MM:SS UTC+8`。 |
| `title` | 事件标题，面向人类可读。 |
| `content` | 事件正文或解释。 |
| `source` | 原始来源，例如 `first_hand:hyperliquid_clearinghouse_state`。 |
| `watcher_source` | watcher 内部来源 ID。 |
| `raw_signal_type` | 源内信号类型，例如 `hyperliquid_position_short`。 |
| `asset_symbol` | 主资产。无主资产时填空，但必须给出原因。 |
| `event_type` | 一级事件类型。 |
| `event_type_l2` | 二级事件类型或 subtype。 |
| `direction_hint` | 方向观察，只能是 observe/risk/positive/negative/neutral/discard。 |
| `importance` | 1-5 的人工或规则重要性。 |
| `publish_route` | review/board/interrupt/archive/discard/digest。 |
| `threshold_rule` | 触发阈值，必须可解释。 |
| `metric_value` | 本次触发的主数值。 |
| `raw_json` | 原始 payload JSON。 |

## 推荐字段

| 字段 | 说明 |
|---|---|
| `entity_label` | 相关实体，例如 Binance、loraclexyz、Tether。 |
| `address` | 地址或账户标识。 |
| `tx_hash` | 链上交易哈希。 |
| `amount_native` | 原生数量。 |
| `amount_usd` | USD 规模。 |
| `confidence` | low/medium/high，表示数据源可信度或规则置信度。 |
| `risk_category` | flow/perp_position/security/listing/unlock 等。 |
| `needs_model_review` | 是否需要 LLM 或人工进一步判断。 |
| `model_review_reason` | 为什么需要复核。 |

## 源注册要求

每个源必须在 `data/source_registry.csv` 登记：

- `source_id`
- `source_type`
- `source_family`
- `adapter_script`
- `primary_output`
- `enabled`
- `shadow_mode`
- `latency_target_seconds`
- `cost_level`
- `confidence_level`
- `tg_default_route`
- `evaluation_status`

## 路由原则

1. 新源默认 `shadow_mode=true`。
2. 没有 outcome 样本前，不得直接升级为高频主群源。
3. 静态背景类信息默认 `digest` 或 `archive`。
4. 动仓变化、极端资金流、安全事件才允许进入 `board` 或 `interrupt`。
5. 每个 route 决策必须写入 `tg_radar_decision_log.csv` 或等价账本。

## 验收标准

1. `scripts/validate_source_adapter_outputs.py` 对当前 watcher 输出返回 pass 或 warning，不允许 fail。
2. 新增源前必须先加入 `data/source_registry.csv`。
3. 新增源至少跑 48 小时 shadow mode，产出质量报告后再决定是否发群。
4. 所有时间字段必须统一可转为 UTC 和中国时间。
5. 所有金额字段必须保留原始数量和 USD 估算来源。
