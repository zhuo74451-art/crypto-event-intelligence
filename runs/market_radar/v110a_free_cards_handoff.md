# Market Radar v1.10-A R2 Handoff Report

生成时间：2026-06-04 15:16 UTC+8

## R2-F1 Final Wire｜TG 安全渲染路径接入

状态：✅ 完成

---

## 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/market_radar_card_router.py` | 更新 | 新增 `render_card_payload()` 函数，接入 `render_tg_safe_text()` 安全渲染路径（~40 行新增） |
| `scripts/run_market_radar_v110a_free_cards.py` | 更新 | 卡片渲染改用 `render_card_payload()`，run summary 输出真实 MarkdownV2 兜底计数；manifest 新增兜底统计字段 |
| `scripts/test_market_radar_card_router_v110a.py` | 更新 | 新增 5 项测试覆盖 render_card_payload（~160 行新增） |
| `runs/market_radar/v110a_free_cards_handoff.md` | 更新 | 本文件 |

---

## 安全渲染接入方式

### 方案选择：方案 A — `render_card_payload()`

在 `card_router` 中新增 `render_card_payload(signal, prefer_markdown=True) -> dict`，它是 `render_card()` 的安全包装层：

```
render_card(signal) → raw_text
    ↓
render_tg_safe_text(raw_text, prefer_markdown=True) → safe_payload
    ↓
return {text, parse_mode, fallback_used, warnings, card_type}
```

调用链：`render_card_payload()` → `render_card()` → `render_tg_safe_text()`

### render_card_payload() 实现

```python
def render_card_payload(signal: dict, prefer_markdown: bool = True) -> dict:
    """渲染卡片并返回 TG 安全发送 payload。
    
    返回格式：
    {
        "text": "...",              # MarkdownV2 已转义或纯文本兜底
        "parse_mode": "MarkdownV2" | None,
        "fallback_used": bool,
        "warnings": [...],
        "card_type": "onchain_position" | ...
    }
    """
    card_type = signal.get("signal_type") or classify_signal_type(signal)
    try:
        card_text = render_card(signal)
    except Exception:
        card_text = render_error_card(...)
        card_type = "error"
    safe = render_tg_safe_text(card_text, prefer_markdown=prefer_markdown)
    safe["card_type"] = card_type
    return safe
```

### 保留原 render_card()

原 `render_card()` 返回 `str` 不变，向后兼容旧测试和调试用途。

---

## parse_mode 传递方式

真实 TG 发送时应使用 `render_card_payload()` 返回的字段：

```python
payload = render_card_payload(signal)
# TG send:
#   text = payload["text"]
#   parse_mode = payload["parse_mode"]  # "MarkdownV2" 或 None
#   if payload["fallback_used"]:
#       log.warning(f"MarkdownV2 fallback for {payload['card_type']}")
```

TG sender 应：
1. 取 `payload["text"]` 作为消息文本
2. 取 `payload["parse_mode"]` 作为 TG API `parse_mode` 参数
3. 检查 `payload["fallback_used"]` 决定是否记录降级事件

---

## fallback_used 统计方式

在 `run_market_radar_v110a_free_cards.py` 中：

```python
# 每条卡片通过 render_card_payload() 渲染
for s in signals_of_type:
    payload = render_card_payload(s)
    card_payloads.append(payload)
    ...

# 统计 fallback
mdv2_fallback_count = sum(1 for p in card_payloads if p.get("fallback_used"))
```

run summary 输出：
```
MarkdownV2兜底：{mdv2_fallback_count} 条
```

Run manifest 中也包含 `MarkdownV2 兜底次数` 字段。

---

## 测试命令

```bash
# 运行全部测试（28 项）
python scripts/test_market_radar_card_router_v110a.py

# 运行主脚本（--no-live 仅 fixture）
python scripts/run_market_radar_v110a_free_cards.py --no-live

# 运行主脚本（含真实外网数据）
python scripts/run_market_radar_v110a_free_cards.py
```

---

## 测试结果

**28/28 passed, 0 failed**

### 新增 R2-F1 Final Wire 测试（5 项）：

| 测试名称 | 覆盖范围 | 结果 |
|----------|---------|------|
| `test_render_card_payload_normal` | 5 类卡片正常返回 parse_mode=MarkdownV2, fallback_used=False, text 非空, card_type 正确 | 5/5 ✅ |
| `test_render_card_payload_fallback_on_exception` | monkeypatch escape_markdown_v2 异常 → fallback_used=True, parse_mode=None, text clean, warnings 填充 | 6/6 ✅ |
| `test_render_card_payload_all_5_types` | 5 类卡片均可生成有效 safe payload | 5/5 ✅ |
| `test_render_card_payload_combo` | Combo Card 可生成 safe payload | 5/5 ✅ |
| `test_render_card_payload_prefer_markdown_false` | prefer_markdown=False → parse_mode=None, fallback_used=False | 3/3 ✅ |

### 全部 28 项测试：

- 原有 10 项（分类、渲染、脱敏、降级等）✅
- R2 新增 11 项（humanize、escape、combo、manifest 等）✅
- R2-F1 安全闸 2 项 ✅
- R2-F1 Final Wire 5 项 ✅

---

## 验收标准对照

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 测试通过 | ✅ | 28/28 passed |
| 实际卡片输出路径已接入 render_tg_safe_text() | ✅ | `render_card_payload()` → `render_card()` → `render_tg_safe_text()` |
| 真实发送前可拿到 text + parse_mode + fallback_used | ✅ | payload dict 包含所有必需字段 |
| run summary 有 MarkdownV2 兜底计数 | ✅ | 动态统计，本轮 0 条 |
| card_router 不再只有裸 escape_markdown_v2 保护 | ✅ | 所有卡片路径通过 render_tg_safe_text() |
| handoff 写清楚 TG 发送时应使用哪个 payload 字段 | ✅ | 见「parse_mode 传递方式」章节 |

---

## 合规检查

| 项目 | 状态 |
|------|------|
| 是否调用付费 API | 否 |
| 是否读取密钥 | 否 |
| 是否真实发送 TG | 否 |
| 是否启动后台循环 | 否 |
| 是否扩展新数据源 | 否 |
| 是否删除重要文件 | 否 |
| 是否新增数据库/RAG | 否 |
| 是否接入 Etherscan / Whale Alert | 否 |

---

## 已知问题（延续）

1. **Hyperliquid 持仓地址**：配置的示例地址未返回真实持仓数据，需真实活跃地址。
2. **风险预警阈值**：当前市场未触发极端阈值，风险预警卡使用 fixture。
3. **Shadow Context**：按工单暂未实现。

---

## 下一步

本轮 R2-F1 Final Wire 已完成。`render_tg_safe_text()` 已接入所有卡片输出路径。

下一步可直接推进 **真实 TG 群单卡测试**：
- 优先发送 `market_anomaly` 卡片
- 使用真实数据
- `parse_mode="MarkdownV2"` 正常发送
- 失败自动 fallback 为纯文本（`parse_mode=None`）
- TG sender 应使用 `render_card_payload(signal)` 获取 safe payload
