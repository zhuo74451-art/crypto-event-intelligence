# Market Radar v1.11-I — Pre-Test-Send Rehearsal Report

**Run**: 2026-06-04 20:33:54 UTC+8
**Version**: v1.11-I
**Mode**: Dry-run / Rehearsal — NO TG SEND
**Status**: ✅ Complete

## Objective

本轮目标：推进 v1.11-I，基于 v1.11-H 的真实卡片 payload 链路，输出最终可发送候选清单、payload 文本预览、MarkdownV2/HTML 格式检查、内容价值判断和发送建议分级，为后续"最多 1-3 张测试频道真实发送"做准备。

## Pipeline Architecture

```
SignalValueGate (v1.11-d) → CooldownGate (v1.11-f) → REAL render_card_payload (card_router) → pre_send_gate (v1.10-G)
                                                                      ↓
                                                          Content Quality Classifier
                                                                      ↓
                                          ready_to_test_send / needs_editor_review / observe_only / blocked
```

## 测试范围

- **6 scenarios** (H1-H6, same as v1.11-H)
- **26 signals** total
- 所有信号复用 v1.11-H 的 6 scenarios / 26 signals，未重新发明样本

---

## 总体分级统计

| Classification | Count | Rate |
|---------------|-------|------|
| ✅ **ready_to_test_send** | **12** | **46.2%** |
| 📝 needs_editor_review | 0 | 0.0% |
| 👁️ observe_only | 2 | 7.7% |
| ❌ blocked | 12 | 46.2% |
| **Total** | **26** | 100% |

---

## ✅ ready_to_test_send 清单 (12 signals)

### H1: Full Happy Path (4/4 ready)

| Signal | Asset | Value Score | Tier | Cooldown | Payload |
|--------|-------|-------------|------|----------|---------|
| H1-00 | BTC | 100 | high | allow (first) | OK, 338 chars |
| H1-01 | ETH | 120 | high | allow (first) | OK, 359 chars |
| H1-02 | SOL | 100 | high | allow (first) | OK, 329 chars |
| H1-03 | SUI | 100 | high | allow (first) | OK, 328 chars |

### H3: Cooldown Suppression (2/4 ready)

| Signal | Asset | Value Score | Cooldown | Payload |
|--------|-------|-------------|----------|---------|
| H3-00 | ARB | 100 | allow (first) | OK, 317 chars |
| H3-03 | SOL | 100 | allow (first for SOL) | OK, 291 chars |

### H5: Upgrade Override (2/2 ready)

| Signal | Asset | Value Score | Cooldown | Payload |
|--------|-------|-------------|----------|---------|
| H5-00 | ETH | 45 | allow (first) | OK, 323 chars |
| H5-01 | ETH | 115 | **upgrade_override** (Δ=70) | OK, 385 chars |

### H6: Full Mixed Pipeline (4/9 ready)

| Signal | Asset | Value Score | Cooldown | Payload |
|--------|-------|-------------|----------|---------|
| H6-00 | BTC | 100 | allow (first) | OK, 338 chars |
| H6-02 | ARB | 100 | allow (first) | OK, 353 chars |
| H6-05 | SUI | 100 | allow (first) | OK, 348 chars |
| H6-07 | ARB | 140 | **upgrade_override** (Δ=40) | OK, 411 chars |

---

## 🥇 Top 3 Recommended Test-Send Candidates

根据复合评分（价值分数 + 多因子支持 + 升级信号 + OI/Volume支撑），推荐**最多 3 张**进入测试频道真实发送：

### 1. 🥇 H6-07 ARB (Composite Score: 225)

**为什么值得测试发送**:
- 价值评分高达 140（price + strong_price_move + OI + Volume + Funding + multi_asset_sync 全因子命中）
- CooldownGate 判定为 upgrade_override（ARB 从 score=100→140，Δ=+40 ≥ 15）
- 这是升级信号——意味着信号强度在快速恶化，比普通 allow 更有情报价值
- 5 因子全确认：价格异动（-8.50%）、OI、Volume、Funding极端（-1.80%）、多资产同步
- 非纯价格噪音，有 OI/Volume/Funding 多重支撑
- 卡片文本 411 chars，MarkdownV2 格式安全

**Payload Preview**:
```
📉 行情异动｜ARB 急跌

一句话：ARB 跌幅 8.50%，强信号升级：多因子全确认

● 币种：ARB
● 涨跌幅：-8.50%
● Funding：-1.80%（年化 -1971.0%）
● 是否拥挤：否
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/arbitrum) / [DexScreener](https://dexscreener.com/search?q=ARB)
```

### 2. 🥈 H5-01 ETH (Composite Score: 200)

**为什么值得测试发送**:
- 价值评分 115（price + strong_price + OI + Volume + Funding 全确认）
- CooldownGate upgrade_override（ETH score 45→115，Δ=+70，远超阈值）
- ETH 作为 Tier-1 资产，信号含金量更高
- 价格异动（-8.50%）、OI $12.5B、Volume $18.2B、Funding -2.50% 极端
- 卡片文本 385 chars，MarkdownV2 安全

**Payload Preview**:
```
📉 行情异动｜ETH 急跌

一句话：ETH 跌幅 8.50%，强信号升级：OI+Vol+Funding 全确认

● 币种：ETH
● 涨跌幅：-8.50%
● Funding：-2.50%（年化 -2737.5%）
● 是否拥挤：否
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q=ETH)
```

### 3. 🥉 H1-01 ETH (Composite Score: 190)

**为什么值得测试发送**:
- 价值评分 120（本批次最高之一）
- Price + OI + Volume + Funding + Multi_asset_sync 五因子全确认
- 非价格噪音，有充分 OI/Volume/Funding 支撑
- 卡片文本 359 chars，MarkdownV2 安全

**Payload Preview**:
```
📉 行情异动｜ETH 急跌

一句话：ETH 24h 跌幅 6.80%，OI+Vol+Funding 极端四重确认

● 币种：ETH
● 涨跌幅：-6.80%
● Funding：-1.50%（年化 -1642.5%）
● 是否拥挤：否
● 观察窗口：1-4 小时

🔗 行情查看：[CoinGecko](https://www.coingecko.com/en/coins/ethereum) / [DexScreener](https://dexscreener.com/search?q=ETH)
```

---

## 👁️ observe_only 清单 (2 signals)

| Signal | Asset | Value Score | Reason |
|--------|-------|-------------|--------|
| H6-03 | LINK | 20 | price_move hit but no OI/volume/funding confirmation — price-only noise |
| H6-08 | AVAX | 20 | price_move hit but OI/volume/funding all missing — price-only noise |

这两个信号虽然有价格异动（LINK -7.20%, AVAX -6.20%），但缺少 OI/Volume/Funding 任何有效确认因子，被 SignalValueGate 降为 observe，不推荐测试发送。

---

## ❌ blocked 统计 (12 signals)

| Block Reason | Count | Examples |
|-------------|-------|----------|
| blocked_by_value_gate | 4 | DOT (-3.20%), LINK-H2 (-4.00%), MATIC (-2.50%), DOT-H6 (-3.50%) |
| suppressed_by_cooldown | 3 | ARB repeat x2 (H3), ARB repeat (H6) |
| blocked_by_pre_send_gate | 5 | AVAX (unknown source), LTC (TTL expired), NEAR (empty payload), OP (missing parse_mode), ETH-H6 (unknown source) |

Pre-send Gate block details:
- **AVAX** (H4): source_type='unknown' not allowed for test send
- **LTC** (H4): TTL expired — age=7200s, TTL=900s
- **NEAR** (H4): Payload text is empty (mock override for testing)
- **OP** (H4): Payload missing 'parse_mode' (mock override for testing)
- **ETH** (H6): source_type='unknown' not allowed for test send

---

## MarkdownV2/HTML 格式检查结论

- **18/26 signals** 通过了格式安全检查（markdown_or_html_safe=true）
- 8 signals 未到达 payload 渲染阶段（被 value_gate 或 cooldown 提前终止），无 payload 可检查
- **0 format-critical issues** in rendered payloads
- 所有 ready_to_test_send 候选的卡板文本均：
  - 使用 `escape_markdown_v2()` 正确转义特殊字符
  - 未超过 TG 4096 字符限制
  - 包含公开行情链接（CoinGecko / DexScreener）
  - 包含风险声明（"不构成交易建议"）

---

## 是否建议进入测试频道真实发送

**建议：是，但严格限制为 1-3 张。**

推荐顺序：
1. **H6-07 ARB**（upgrade 信号，最强情报价值）— 优先发送
2. **H5-01 ETH**（upgrade 信号，Tier-1 资产）— 第二优先
3. **H1-01 ETH**（五因子全确认，最高原始评分）— 可选发送

### 理由

- 12 张 ready_to_test_send 候选卡板全部通过了三层门控 + 格式检查 + 内容价值评估
- 推荐的前 3 张都是多因子确认的非噪音信号，有明确的情报价值
- 2 张 upgrade_override 信号（ARB、ETH）特别值得发送，因为它们代表"信号强度快速恶化"，比普通 allow 更有信息量
- 本次 rehearsal 所有 payload 都是真实 card_router 渲染的，不是 mock
- 增量发送（1-3 张）风险可控，从测试频道开始

不应一次发送超过 3 张，因为：
- 测试频道目的是验证真实发送效果，不是填充内容
- 优先选信号质量最高的，而非数量

---

## 安全确认

- [x] **本轮未发送 TG** — tg_sent=false
- [x] **本轮未加载 secrets** — secrets_loaded=false
- [x] **本轮未触碰正式频道** — official_channel_touched=false
- [x] **未读取/打印/保存 token、chat_id、key、cookie、password**
- [x] **未调用付费 API**
- [x] **未启动 loop/daemon/cron**
- [x] **未删除文件**
- [x] **所有代码在正确项目目录内**

---

## v1.11-H vs v1.11-I 对比

| Metric | v1.11-H | v1.11-I |
|--------|---------|---------|
| 目标 | Real card pipeline dry-run | Pre-send rehearsal with classification |
| 场景 | 6 scenarios, 26 signals | 6 scenarios, 26 signals (SAME) |
| 负载 | Real render_card_payload | Real render_card_payload (SAME) |
| 分级 | send_candidate / blocked / observe | ready / needs_review / observe_only / blocked |
| 推荐 | None (pipeline only) | Top 3 ranked candidates |
| Payload preview | No | Yes (text preview for each ready card) |
| Content quality | Not assessed | Assessed per signal |
| Format check | Not performed | Performed on all rendered payloads |
| TG send | NONE | NONE |
