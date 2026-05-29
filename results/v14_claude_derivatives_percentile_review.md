# Claude Response

- generated_at: 2026-05-28 23:01:02 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: 4c0f56d7399455e8

# 外部复审意见 v14 - 历史分位接入后

## 一、当前首屏密度评估

**结论：确实太密，建议删除以下 2 行：**

### 删除建议

1. **删除**："多头集中：SOL/XRP/DOGE 多头账户或仓位占比较高，若价格反向波动，需警惕集中平仓。"
   - **原因**：这是持仓结构细节，不是当日核心变化，应该放早晚报"市场结构"章节
   - 如果真的极端（如 long ratio >85% 且 funding >0.1%），应该单独成为"今日最值得关注"条目，而不是挤在首屏

2. **删除**："集中度解释：资金份额集中到头部基金，市场偏好明确；FBTC 份额明显下降，可能存在相对赎回或资金转移压力。"
   - **原因**：这是 ETF 内部结构分析，不是流量本身。用户看到 "-7.33 亿美元（90日分位 98.9%，极端）" 已经足够做决策
   - 份额变化应该放早晚报 ETF 章节详细展开

### 保留但微调

- **"结构解读"** 这行保留，但改为：
  ```
  • 结构解读：价格回调 + 持仓增加 = 新仓进场（可能抄底，也可能空头加仓）
  ```
  更简洁，去掉"说明"这种冗余词。

---

## 二、历史分位进入首屏的合理性

### 当前问题

你把 **所有分位数** 都塞进首屏了，这不对。分位数应该 **按触发条件分层**：

| 指标 | 首屏条件 | 早晚报显示 | 盘中雷达触发 |
|------|---------|-----------|------------|
| **资金费率分位** | ≥85% 或 ≤15% | 始终显示 | ≥90% 或 ≤10% |
| **OI 24h 变化分位** | ≥80% 或 ≤20% | 始终显示 | ≥85% 或 ≤15% |
| **OI 水平分位** | 不进首屏 | 始终显示 | ≥95%（历史极值） |
| **ETF 流量分位** | ≥90% 或 ≤10% | 始终显示 | ≥95% 或 ≤5% |

### 具体修改

**首屏应该改成：**

```text
• 资金费率：BTC 0.0100%（中性，90日分位 71.5%）；ETH 0.0016%（中性，90日分位 35.9%）
• 持仓异常：ETH 24h 变化分位 79.9%（接近极端）
```

**不要显示：**
- BTC OI 变化分位 55.2%（平庸，无信息量）
- 任何资产的 OI 水平分位（这是慢变量，不是当日信号）

---

## 三、SOL/XRP funding 分位 90%+ 的处理

### 当前问题

**应该进入"今日最值得关注"**，但你缺少 **价格确认**。

### 进入条件（三选一）

1. **funding 分位 ≥90%** + **24h 涨幅 >5%** → "多头过热，警惕回调"
2. **funding 分位 ≥90%** + **24h 跌幅 >3%** → "多头被套，可能加速平仓"
3. **funding 分位 ≥90%** + **OI 24h 变化分位 ≥80%** → "多头集中加仓，极端情绪"

### 示例输出

```text
• 今日最值得关注：
  - SOL 资金费率 90日分位 90.7%，24h +6.2%，多头过热，警惕回调
  - XRP 资金费率 90日分位 91.1%，24h -4.1%，多头被套，可能加速平仓
```

### 盘中雷达触发

- **funding 分位 ≥95%** + **1h 跌幅 >2%** → 立即推送："[XRP] 多头费率极端 + 价格下跌，警惕踩踏"

---

## 四、ETH OI 变化分位 79.9% vs 水平分位 38.3% 的解释

### 当前问题

你直接并列显示，用户会困惑："变化大但水平低，到底是多还是少？"

### 正确解释逻辑

```python
if oi_change_percentile >= 80 and oi_level_percentile < 50:
    interpretation = "持仓快速增加，但绝对水平仍低于历史中位数，说明是从低位反弹"
elif oi_change_percentile >= 80 and oi_level_percentile >= 70:
    interpretation = "持仓快速增加且已处高位，市场过度拥挤"
elif oi_change_percentile <= 20 and oi_level_percentile >= 70:
    interpretation = "持仓快速下降但仍处高位，可能是获利了结"
```

### 首屏显示建议

```text
• 持仓异常：ETH 24h 变化分位 79.9%（快速增加），但水平分位 38.3%（从低位反弹）
```

**不要让用户自己推理，直接给结论。**

---

## 五、ETH ETF 数据源替代方案

### 方案对比

| 数据源 | 成本 | 延迟 | 可靠性 | 建议 |
|--------|------|------|--------|------|
| **Farside（当前）** | 免费 | T+1 | 被 Cloudflare 拦截 | ❌ 放弃 |
| **SoSoValue** | 免费 | T+1 | 国内可访问，但可能反爬 | ✅ 优先尝试 |
| **The Block** | 免费（需注册） | T+1 | 稳定，但可能限流 | ✅ 备选 |
| **CoinGlass API** | $49/月 | 实时 | 稳定 | ⚠️ 如果免费源都失败再考虑 |
| **手动录入** | 人工 | T+1 | 100% | ❌ 不可持续 |

### 下一步行动

1. **立即尝试 SoSoValue**：
   - URL: `https://sosovalue.xyz/assets/etf/us-eth-spot`
   - 用 Selenium + undetected-chromedriver 绕过反爬
   - 如果成功，替换 Farside

2. **如果 SoSoValue 也失败**：
   - 先 **跳过 ETH ETF**，在早晚报标注："ETH ETF 数据源不稳定，暂时下线"
   - 不要为了凑数据而降低质量

3. **验收标准**：
   - 连续 7 天成功抓取
   - 数据与 Farside 人工核对误差 <2%

---

## 六、下一批脚本级任务

### 任务 1：分位数分层显示逻辑

**目标**：不要把所有分位数都塞进首屏，按触发条件分层。

**输入**：
- `data/funding_rate/funding_rate_percentiles.csv`
- `data/oi/oi_percentiles.csv`
- `data/market/binance_top_symbols_data.csv`（价格涨跌幅）

**输出**：
- `results/v15_percentile_alerts.json`
  ```json
  {
    "frontpage_alerts": [
      {"symbol": "ETH", "type": "oi_change", "percentile": 79.9, "interpretation": "快速增加，但从低位反弹"}
    ],
    "watchlist_alerts": [
      {"symbol": "SOL", "type": "funding", "percentile": 90.7, "price_change_24h": 6.2, "risk": "多头过热"}
    ],
    "radar_triggers": []
  }
  ```

**验收标准**：
- BTC/ETH funding 分位 <85% 时，首屏不显示分位数（只显示费率值）
- SOL funding 分位 90.7% + 24h 涨幅 >5% 时，进入 `watchlist_alerts`
- 任何资产 funding 分位 ≥95% + 1h 跌幅 >2% 时，进入 `radar_triggers`

**脚本路径**：
- `scripts/market/generate_percentile_alerts.py`

---

### 任务 2：OI 变化 + 水平分位联合解释

**目标**：自动生成 "快速增加但从低位反弹" 这类解释，不要让用户看原始分位数困惑。

**输入**：
- `data/oi/oi_percentiles.csv`

**输出**：
- 在 `results/v15_percentile_alerts.json` 中添加 `interpretation` 字段

**逻辑**：
```python
def interpret_oi(change_pct, level_pct):
    if change_pct >= 80:
        if level_pct < 50:
            return "快速增加，从低位反弹"
        elif level_pct >= 70:
            return "快速增加且已处高位，市场拥挤"
        else:
            return "快速增加，接近历史中位数"
    elif change_pct <= 20:
        if level_pct >= 70:
            return "快速下降但仍处高位，可能获利了结"
        else:
            return "快速下降，市场降温"
    else:
        return None  # 不显示
```

**验收标准**：
- ETH OI 变化分位 79.9%、水平分位 38.3% → 输出 "快速增加，从低位反弹"
- 如果 BTC OI 变化分位 55.2%（平庸），不输出任何解释

---

### 任务 3：ETH ETF 数据源切换到 SoSoValue

**目标**：替换 Farside，解决 Cloudflare 拦截问题。

**输入**：
- URL: `https://sosovalue.xyz/assets/etf/us-eth-spot`

**输出**：
- `data/eth_etf_flows_sosovalue.csv`（格式与 Farside 一致）
- `results/v15_eth_etf_source_validation.md`（对比 Farside 历史数据，验证准确性）

**技术要求**：
- 用 `undetected-chromedriver` 绕过反爬
- 如果连续 3 次失败，脚本返回 `status=source_unavailable`，不要崩溃

**验收标准**：
- 成功抓取最近 7 天数据
- 与 Farside 人工核对的历史数据（如 2024-05-20）误差 <2%
- 如果验证失败，在 `command_registry.yaml` 中标注 `eth_etf: disabled`

**脚本路径**：
- `scripts/etf/build_eth_etf_sosovalue.py`

---

### 任务 4：首屏密度优化

**目标**：删除 2 行冗余内容，微调 1 行。

**修改**：
1. 删除 "多头集中：SOL/XRP/DOGE..." 行
2. 删除 "集中度解释：资金份额集中..." 行
3. 修改 "结构解读" 为："价格回调 + 持仓增加 = 新仓进场（可能抄底或空头加仓）"

**验收标准**：
- 首屏总行数 ≤8 行（不含标题）
- 删除的内容出现在早晚报对应章节
- 用 5 个真实用户测试，询问 "看完首屏后 30 秒内能否说出今天最重要的 3 件事"，通过率 ≥80%

---

## 七、优先级排序

1. **P0（本周完成）**：任务 4（首屏优化）、任务 1（分位数分层）
2. **P1（下周完成）**：任务 2（OI 联合解释）
3. **P2（两周内完成）**：任务 3（ETH ETF 换源，如果失败就跳过）

---

## 八、最后提醒

你现在的问题是 **"有了锤子，看什么都是钉子"**：

- 实现了历史分位 → 恨不得所有分位数都显示
- 接入了 ETF 集中度 → 恨不得把所有解释都塞进首屏

**记住：首屏是给用户 30 秒内做决策的，不是展示你实现了多少功能。**

如果一个指标不能直接回答 "今天我该做什么"，就不要放首屏。
