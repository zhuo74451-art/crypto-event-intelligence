# HyperInsight Card Patterns (v1.6E Benchmark)

Source: https://t.me/s/HyperInsight (20 messages sampled).

## Pattern Summary

### 1. Title Format
```
🚀 Hyperliquid 持仓异动｜主力巨鲸大单提醒 🚀
```
- Always uses 🚀 emoji framing
- "持仓异动" not "行为变化" or "数据更新"
- Identifies it as a whale/major position alert

### 2. Identity Line
```
【知名交易员Loracle「 HYPE 空仓 TOP 1」】
```
- Uses 【】 brackets for identity
- Labels trader name + rank + direction
- "空仓 TOP 1" / "多仓 TOP 2" style ranking
- Always Chinese direction: 多单/空单 (never long/short)

### 3. Action Line
```
HYPE 空单 割肉啦！
```
- Casual but specific: 割肉/减持/增持
- Asset name + direction + action
- Exclamation for emphasis

### 4. Data Section
```
HYPE 空单减持 31,001.91 枚，约合 247 万美元
持仓规模：53,059,599.89 美元
均价：45.1 美元
当前盈亏：-20,102,360.15 美元（-75.14%）
当前价：72.90 美元
清算价：119.74 美元
```
- 6-7 data lines with specific numbers
- USD values formatted with commas
- PnL shown as both absolute and percentage
- Liquidation price always included

### 5. Address Line
```
📌 地址：0x...
```
- Full 0x address shown

### 6. Annotation Line
```
🔥 注：Loracle 原名 Laurent Zeimes，Hyperliquid 生态活跃交易员，过往胜率...
```
- Background on WHY this address matters
- Includes historical context
- Not fabricated — based on known trader identity

### 7. Link Line
```
🔗 Hyperliquid 官网查看：https://app.hyperliquid.xyz/
```

## What We Must Learn

✅ DO:
- Strong titles with asset + action
- Identity line with 【】 brackets
- Chinese 多单/空单 (never long/short)
- Specific numbers (size, value, PnL, liquidation price)
- Full address
- Background annotation (🔥 注)
- Hyperliquid link
- Clean formatting, no machine field names

❌ DON'T:
- Machine field names (current_side, buy_ratio, trade_bias_label)
- Generic "行为变化" / "数据更新" titles
- English direction terms (long/short)
- No address
- No annotation/background
- Template filler text ("该消息具备观察价值")
- Trading advice or price predictions

## Our Current Gap

| Dimension | HyperInsight | Our v1.6C | Our v1.6D-2 |
|-----------|-------------|-----------|-------------|
| Title | Asset + Action + 🚀 | Asset + Action | Asset + 人话动作 |
| Identity | 【Trader｜Rank】 | Entity name only | Entity name |
| Direction | 多单/空单 🇨🇳 | long/short | 多单/空单 🇨🇳 |
| Data density | 6-7 specific numbers | 3 evidence lines | 3 evidence lines |
| PnL | ✅ always shown | ❌ not available | ❌ not available |
| Liquidation price | ✅ always shown | ❌ not in card | ❌ not in card |
| Address | ✅ full 0x | ❌ not shown | ❌ not shown |
| Annotation | ✅ trader background | ❌ none | ❌ none |
| Link | ✅ HL app link | ❌ none | ❌ none |
| Benchmark score | ~95 | ~25 | ~82 (v1.6E) |
