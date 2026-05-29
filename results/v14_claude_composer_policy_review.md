# Claude Response

- generated_at: 2026-05-28 20:59:19 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V14_COMPOSER_POLICY_REVIEW_PROMPT.md
- prompt_sha256_16: fa275c1ff9148d3e

# 外部产品负责人 + 量化研究负责人意见

## 直接结论

**现在不能发到 TG。** 你们做了很多工程，但核心问题没解决：**你们还在用 LLM 打分系统伪装成交易信号系统**。281 条历史样本最后只剩 1 条 ETF 流入，0 条安全事件，这不是"保守"，这是**系统性失败**。

---

## 1. Composer 五阶段权重和硬门槛

### 当前问题
- 5 个阶段各 20 分，最后加权平均，这是**典型的学术评分思维**，不是交易决策思维
- `historical_confidence_score` 低但总分高，说明其他阶段在**掩盖核心问题**

### 具体改法

```python
# 删除加权平均，改为门槛制
HARD_GATES = {
    'trading_relevance_score': 15,  # 不到 15 分直接 block
    'attribution_score': 12,        # 资产归因不到 12 分直接 block
    'historical_confidence_score': 10,  # 历史置信度不到 10 分直接 block
}

# structuring_score 和 readability_score 只影响 digest vs interrupt
ROUTING_LOGIC = {
    'interrupt': 'structuring_score >= 15 AND readability_score >= 15',
    'digest': 'structuring_score >= 10 OR readability_score >= 10',
}
```

**删除 `composer_final_score`**，改为：
- `composer_gate_passed`: bool
- `composer_block_reason`: str (哪个门槛没过)
- `composer_route_hint`: 'interrupt' | 'digest' | 'review'

---

## 2. 哪些字段应该变成硬阻断

### 立即变硬阻断

```python
HARD_BLOCKS = {
    # 价格前置
    'pre_event_price_move_5min': lambda x: abs(x) > 0.02,  # 2% 已动直接 block
    'pre_event_volume_spike': lambda x: x > 3.0,           # 3 倍量已爆直接 block
    
    # 市场状态
    'regime_filter_block': lambda x: x == True,            # 极端行情直接 block
    'market_hours_block': lambda x: x == True,             # 非交易时段直接 block
    
    # 资产归因
    'affected_tradable_asset': lambda x: x is None or x == '',  # 无可交易资产直接 block
    'asset_attribution_confidence': lambda x: x < 0.6,     # 归因置信度 < 60% 直接 block
    
    # 来源质量
    'source_tier': lambda x: x > 2,                        # Tier 3+ 来源直接 block (除非多来源确认)
    'multi_source_confirmed': lambda x: x == False and source_tier > 1,
}
```

**关键**：这些字段应该在 **Composer Stage 1 之前** 就执行，不是打分，是**预过滤**。

---

## 3. ETF/基金流和 CEX 流入流出怎么拆

### 当前混乱
- `event_subtype=etf_or_fund_flow` 里混了：
  - ETF 申购赎回（影响现货需求）
  - 基金持仓披露（已知信息）
  - 交易所净流入（链上数据）
  - 宏观 ETF 新闻（无直接交易信号）

### 具体拆法

```python
# 删除 etf_or_fund_flow，拆成 4 个独立 subtype
EVENT_SUBTYPES = {
    'etf_creation_redemption': {
        'keywords': ['creation', 'redemption', 'inflow', 'outflow'],
        'required_context': ['ETF', 'shares', 'AUM'],
        'excluded': ['filed', 'approved', 'launched'],  # 排除新闻
        'asset_source': 'ETF underlying asset',
    },
    
    'institutional_disclosure': {
        'keywords': ['13F', 'filing', 'disclosed', 'holdings'],
        'required_context': ['fund', 'institution', 'quarter'],
        'default_action': 'block',  # 披露类默认 block，除非异常大
    },
    
    'cex_netflow': {
        'keywords': ['exchange', 'wallet', 'transferred', 'moved'],
        'required_context': ['blockchain', 'address', 'transaction'],
        'data_source': 'on-chain',
    },
    
    'etf_macro_news': {
        'keywords': ['ETF', 'approved', 'filed', 'launched'],
        'default_action': 'block',  # 宏观新闻默认 block
    }
}
```

**重新跑 `split_flow_event_subtypes.py`**，输出 4 列：
- `refined_subtype`
- `flow_direction` (inflow/outflow/neutral)
- `data_source` (on-chain/filing/news)
- `subtype_confidence`

---

## 4. Active exploit 资产归因设计

### 当前问题
- `affected_tradable_asset` 混了协议代币、被盗资产、提及主币
- ADA/AAVE/BNB 被错误归因是因为**没有分离受害主体和受影响资产**

### 具体设计

```python
# 新增 3 个独立字段
EXPLOIT_ATTRIBUTION = {
    'victim_protocol': str,           # 受害协议名称，如 "Platypus Finance"
    'victim_protocol_token': str,     # 协议代币，如 "PTP"
    'victim_protocol_chain': str,     # 所在链，如 "Avalanche"
    
    'stolen_assets': List[dict],      # 被盗资产列表
    # [{'asset': 'USDC', 'amount': 8500000, 'confidence': 0.9},
    #  {'asset': 'AVAX', 'amount': 50000, 'confidence': 0.7}]
    
    'affected_tradable_assets': List[dict],  # 受影响可交易资产
    # [{'asset': 'PTP', 'impact_type': 'protocol_token', 'confidence': 0.95},
    #  {'asset': 'AVAX', 'impact_type': 'chain_token', 'confidence': 0.6}]
    
    'primary_tradable_asset': str,    # 主要可交易资产（用于路由）
    'primary_asset_confidence': float, # 主资产置信度
}

# 置信度计算规则
CONFIDENCE_RULES = {
    'protocol_token': {
        'title_mention + protocol_name': 0.95,
        'body_mention + protocol_name': 0.8,
        'protocol_name_only': 0.5,
    },
    'stolen_asset': {
        'amount + asset + theft_context': 0.9,
        'amount + asset': 0.6,
        'asset_mention_only': 0.3,
    },
    'chain_token': {
        'chain_name + exploit_context': 0.6,
        'chain_name_only': 0.3,
    }
}
```

**硬规则**：
- `primary_asset_confidence < 0.7` 直接 block
- `impact_type == 'chain_token' AND confidence < 0.8` 直接 block（链代币归因要求更高）
- 如果 `stolen_assets` 和 `affected_tradable_assets` 无交集，降级到 digest

---

## 5. Pre-event price-in 和 regime filter 如何进入 Publisher

### 当前问题
- 这些字段在 Composer 里只是扣分，Publisher 看不到原始值

### 具体改法

```python
# 在 Composer 之前增加 PreFilter 阶段
class PreFilter:
    def __init__(self, price_data, regime_data):
        self.price_data = price_data
        self.regime_data = regime_data
    
    def check(self, event):
        blocks = []
        
        # 价格前置检查
        if event.affected_tradable_asset:
            price_move = self.price_data.get_move_5min(
                asset=event.affected_tradable_asset,
                timestamp=event.event_timestamp
            )
            if abs(price_move) > 0.02:
                blocks.append(f'price_moved_{price_move:.1%}_before_event')
        
        # 市场状态检查
        regime = self.regime_data.get_regime(event.event_timestamp)
        if regime in ['extreme_volatility', 'liquidity_crisis']:
            blocks.append(f'regime_{regime}')
        
        # 交易时段检查
        if not self.is_trading_hours(event.event_timestamp, event.affected_tradable_asset):
            blocks.append('outside_trading_hours')
        
        return {
            'prefilter_passed': len(blocks) == 0,
            'prefilter_blocks': blocks,
        }
```

**流程改为**：
```
Event → PreFilter → (block or pass) → Composer → Publisher
```

Publisher 只看到通过 PreFilter 的事件。

---

## 6. Historical similarity 最小可行方法

### 不要做的
- ❌ 训练 embedding 模型
- ❌ 向量数据库
- ❌ 语义相似度

### 应该做的

```python
# 基于结构化字段的精确匹配
class HistoricalMatcher:
    def __init__(self, historical_db):
        self.db = historical_db  # 已标注的历史事件
    
    def find_similar(self, event):
        # 精确匹配条件
        matches = self.db.query(
            event_subtype=event.event_subtype,
            affected_tradable_asset=event.affected_tradable_asset,
            magnitude_bucket=self._bucket_magnitude(event.magnitude),
        )
        
        if len(matches) == 0:
            return {'historical_confidence_score': 0, 'similar_events': []}
        
        # 统计历史表现
        stats = {
            'total_similar': len(matches),
            'published_count': sum(m.was_published for m in matches),
            'avg_price_impact_1h': np.mean([m.price_impact_1h for m in matches]),
            'false_positive_rate': sum(m.was_false_positive for m in matches) / len(matches),
        }
        
        # 计算置信度
        confidence = self._calculate_confidence(stats)
        
        return {
            'historical_confidence_score': confidence,
            'similar_events': [m.event_id for m in matches[:3]],
            'historical_stats': stats,
        }
    
    def _bucket_magnitude(self, magnitude):
        # 把金额/流量分桶，避免过度精确匹配
        if magnitude < 1_000_000:
            return 'small'
        elif magnitude < 10_000_000:
            return 'medium'
        elif magnitude < 100_000_000:
            return 'large'
        else:
            return 'xlarge'
    
    def _calculate_confidence(self, stats):
        # 简单规则
        if stats['total_similar'] < 3:
            return 5  # 样本太少，低置信度
        
        if stats['false_positive_rate'] > 0.5:
            return 3  # 历史误报率高
        
        if stats['published_count'] == 0:
            return 0  # 历史从未发布过
        
        # 基于历史发布率和价格影响
        base_score = min(stats['published_count'] / stats['total_similar'] * 20, 15)
        impact_bonus = 5 if abs(stats['avg_price_impact_1h']) > 0.01 else 0
        
        return min(base_score + impact_bonus, 20)
```

**数据需求**：
- 手动标注 50-100 条历史事件
- 字段：`event_id`, `event_subtype`, `affected_tradable_asset`, `magnitude`, `was_published`, `price_impact_1h`, `was_false_positive`
- 存成 SQLite 或 CSV

---

## 7. Telegram 摘要里展示什么

### 不要展示
- ❌ `composer_final_score`（用户不理解）
- ❌ 各阶段分数（太技术）
- ❌ `confidence` 百分比（容易误导）

### 应该展示

```markdown
🚨 **安全事件** | Platypus Finance

**被盗金额**: $8.5M USDC
**受影响资产**: PTP (-15% 预期)
**来源**: PeckShield (Tier 1) + 2 确认

**历史参考**: 
类似事件 5 次，平均 1h 影响 -12%

⚠️ 价格已动 -3% | 🕐 5 分钟前
```

```markdown
📊 **ETF 流入** | Bitcoin Spot ETF

**流入金额**: $127M
**受影响资产**: BTC
**来源**: Farside Investors (Tier 1)

**历史参考**:
类似流入 12 次，平均 1h 影响 +0.8%

✅ 价格未动 | 🕐 2 分钟前
```

**关键**：
- 用 emoji 和标签代替分数
- 展示**可操作信息**（金额、资产、时间）
- 展示**历史参考**（用户自己判断）
- 展示**价格状态**（已动/未动）

---

## 8. 下一轮优先级（Top 5）

### 1. **增加 PreFilter 阶段**（最高优先级）
- 文件：`src/prefilter.py`
- 硬阻断：价格前置、市场状态、交易时段
- 输出：`prefilter_passed`, `prefilter_blocks`
- **为什么优先**：现在 281 条只剩 1 条，说明 Composer 在处理已经无效的事件，PreFilter 能提前拦截 80%

### 2. **拆分 ETF/基金流 subtype**
- 修改：`scripts/split_flow_event_subtypes.py`
- 输出 4 个独立 subtype
- 重新标注 57 条 flow 事件
- **为什么优先**：当前 1 条 digest 可能就是误分类的宏观新闻

### 3. **重构 exploit 资产归因**
- 修改：`scripts/verify_exploit_amounts.py`
- 新增 `victim_protocol`, `stolen_assets`, `affected_tradable_assets`, `primary_tradable_asset`
- 重新跑 active exploit 样本
- **为什么优先**：0 条 exploit 通过是因为资产归因失败，这是核心功能

### 4. **实现 HistoricalMatcher**
- 新建：`src/historical_matcher.py`
- 手动标注 50 条历史事件（从 281 条里挑）
- 字段：`was_published`, `price_impact_1h`, `was_false_positive`
- **为什么优先**：`historical_confidence_score` 现在是空转，需要真实数据支撑

### 5. **Composer 改门槛制**
- 删除加权平均
- 改为 3 个硬门槛 + 路由逻辑
- 输出 `composer_gate_passed`, `composer_block_reason`
- **为什么优先**：现在的打分系统在掩盖问题，门槛制能暴露真实质量

---

## 9. 应该删除或降级的

### 立即删除
1. **`composer_final_score`**：加权平均没有意义，改门槛制
2. **`readability_
