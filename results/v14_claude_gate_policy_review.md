# Claude Response

- generated_at: 2026-05-28 21:09:31 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V14_GATE_POLICY_REVIEW_PROMPT.md
- prompt_sha256_16: 957bbc5b8aba699f

# 外部产品负责人 + 量化研究负责人视角的直接批评

## 1. 这轮改动的真实进度评估

### 真正的进步（约40%）
- **Flow subtype 拆分**：这是对的。ETF申赎、机构披露、CEX netflow、宏观新闻确实是完全不同的信号类型，混在一起就是垃圾。
- **Exploit 资产归因重构**：victim_protocol / stolen_assets / affected_tradable_assets 的三层分离是正确的结构化思路。
- **PreFilter 硬阻断**：benchmark asset、missing tradable asset 这些是应该做的基础卫生。
- **Composer 删除加权平均**：这是真进步，加权平均就是自欺欺人。

### 伪进步或新问题（约60%）
- **ETF/Fund filter 过严导致 57→3**：这不是进步，这是矫枉过正。你把"ETF 宏观新闻"全部砍掉，但实际上"贝莱德 CEO 说比特币 ETF 超预期"这种新闻在 2024 年 1-3 月确实会引发价格异动。你应该拆分成"ETF 申赎数据"（需要严格）和"ETF 高管发言/监管动态"（可以放宽但标注为宏观背景）。
- **Composer gate 过的 20 条被 Publisher 全部 block**：这说明你的 Composer 和 Publisher 逻辑冲突。Composer 说"这 20 条有交易相关性、有归因、有历史置信"，Publisher 说"但我不发这些 subtype"。这是流程设计失败，不是质量控制成功。
- **HistoricalMatcher 用同批数据自举**：这是典型的过拟合陷阱。你用 281 条的历史表现来判断这 281 条该不该发，这是循环论证。
- **PreFilter 只用 6h pre-event abnormal**：6 小时太长了，很多事件在 6 小时前根本没有价格信号。你应该用 5min/15min/1h 三档，而不是只用 6h 凑合。

### 根本问题未解决
你仍然在用"事件分类 + 打分 + 门槛"的框架，但没有回答核心问题：
- **这个系统的信息优势来源是什么？** 如果只是转发 Binance 快讯，用户为什么不直接看 Binance？
- **历史回测的 1h/4h abnormal 能否预测未来？** 你没有做 out-of-sample 验证，所有逻辑都是 in-sample 拟合。
- **事件发布的时效性如何保证？** 你没有 source_delay、event_to_publish_delay 字段，可能在发布"3 小时前的旧闻"。

---

## 2. 281 条全 block 是否合理？

### 不合理，但原因复杂

**281 条全 block 说明三个问题之一：**
1. 数据源质量太差（最可能）
2. 门槛设置错误（次可能）
3. 产品定位错误（需警惕）

### 应该先放开哪一类？

**优先级 1：`upgrade_or_fork` 中的主网升级**
- 标准：L1/L2 主网升级 + 明确升级时间 + 社区关注度高（Twitter/Discord 有讨论）
- 例如：Ethereum Dencun 升级、Arbitrum Stylus 上线
- 为什么：这类事件有明确的时间锚点，用户需要提前知道，历史上确实会引发价格波动（即使方向不确定）
- 发布策略：提前 24h 发"即将升级"，升级完成后发"升级已完成"，标注为"事件提醒"而非"交易信号"

**优先级 2：`exploit` 中的大额盗币（>$10M）且受影响资产明确**
- 标准：stolen_amount > $10M + primary_tradable_asset 存在 + primary_asset_confidence > 60%
- 例如：Ronin Bridge 被盗 $600M（影响 AXS/RON）
- 为什么：大额盗币确实会引发恐慌性抛售，即使资产归因不完美，用户也需要知道
- 发布策略：标注"受影响资产可能包括 X，但归因置信度仅 Y%，请谨慎判断"

**优先级 3：`etf_creation_redemption` 中的单日大额异常**
- 标准：单日净流入/流出 > $500M + 连续 3 日同向 + 有官方数据源
- 为什么：ETF 流向是少数有"真实资金流"的高质量信号
- 发布策略：每日晚报汇总，不做盘中推送（避免噪音）

**绝对不能放开的：**
- `etf_macro_news`：CEO 发言、分析师观点、监管传闻 → 这些是噪音，不是信号
- `flow_unclear`：连方向都不明确的流向数据 → 垃圾
- `security` 中的"软安全"：钓鱼网站警告、安全提示 → 不是交易相关事件

---

## 3. `upgrade_or_fork` 该不该纳入 digest？

### 应该纳入，但要细分

**必须发的升级类事件（digest）：**
- **硬分叉/主网升级**：有明确区块高度或时间，影响全网共识
  - 例：Ethereum Dencun、Bitcoin Taproot
  - 标准：官方公告 + 明确时间 + 需要节点/矿工行动
- **重大协议升级**：Top 20 DeFi 协议的核心合约升级
  - 例：Uniswap V3 → V4、Aave V2 → V3
  - 标准：TVL > $1B + 合约地址变更 + 有审计报告

**可以发但标注为"背景信息"（interrupt 或早报）：**
- **测试网升级**：主网升级的前置信号
  - 例：Ethereum Sepolia 测试网部署 Dencun
  - 标准：距离主网升级 < 30 天
- **SDK/工具升级**：不影响链上状态，但开发者关注
  - 例：ethers.js v6 发布
  - 标准：GitHub star > 10k + 有 breaking changes

**必须 block 的：**
- **小项目的常规更新**：每周都有的版本迭代
  - 例：某 DEX 前端 UI 优化、某钱包 bug 修复
  - 标准：TVL < $100M 或日活 < 1000
- **"即将升级"的模糊公告**：没有明确时间，只是路线图
  - 例：某 L2 "计划在 Q2 升级"
  - 标准：时间不明确或距离 > 90 天

### 判断标准的量化规则
```python
def should_publish_upgrade(event):
    # 硬分叉/主网升级
    if event.upgrade_type in ['hard_fork', 'mainnet_launch']:
        if event.has_exact_time and event.chain_tvl > 1_000_000_000:
            return 'digest'
    
    # 协议升级
    if event.upgrade_type == 'protocol_upgrade':
        if event.protocol_tvl > 1_000_000_000 and event.contract_address_changed:
            return 'digest'
        elif event.protocol_tvl > 100_000_000:
            return 'interrupt'
    
    # 测试网升级
    if event.upgrade_type == 'testnet_upgrade':
        if event.days_to_mainnet < 30:
            return 'interrupt'
    
    return 'block'
```

---

## 4. Active exploit 0 条 urgent 是否合理？

### 不合理，说明数据源和归因逻辑都有问题

**问题诊断：**

查看你的 `verify_exploit_amounts.py` 输出，28 条 active exploit 中 0 条通过，主要原因：
1. **误分类**：很多"security"事件是软安全话题（钓鱼警告、安全提示）
2. **无法归因**：盗币资产是 USDT/ETH，但受影响的协议 token 没有交易对
3. **金额不明**：快讯只说"被盗"，没有具体金额
4. **时效性差**：事件发生 > 24h 后才被抓取

### 如何修复（不靠人工逐条看）

**Step 1：数据源前置过滤（在抓取时就过滤）**
```python
def is_valid_exploit_source(raw_event):
    # 必须包含金额关键词
    amount_keywords = ['$', 'million', 'M', 'stolen', 'drained', 'exploited']
    if not any(kw in raw_event.title.lower() for kw in amount_keywords):
        return False
    
    # 必须包含协议名称（不是通用安全警告）
    if any(kw in raw_event.title.lower() for kw in ['phishing', 'scam alert', 'warning']):
        return False
    
    # 必须有明确的受害者
    if not extract_protocol_name(raw_event.title):
        return False
    
    return True
```

**Step 2：资产归因的降级策略（不要一刀切）**
```python
def exploit_asset_attribution(event):
    # 优先级 1：协议有自己的 token 且有交易对
    if event.victim_protocol_token and has_binance_pair(event.victim_protocol_token):
        return {
            'primary_asset': event.victim_protocol_token,
            'confidence': 90,
            'reason': 'protocol_native_token'
        }
    
    # 优先级 2：被盗资产本身可交易（如 ETH/USDT）
    if event.stolen_assets and all(has_binance_pair(a) for a in event.stolen_assets):
        return {
            'primary_asset': event.stolen_assets[0],  # 取金额最大的
            'confidence': 70,
            'reason': 'stolen_asset_tradable'
        }
    
    # 优先级 3：协议所在链的 native token
    if event.victim_protocol_chain:
        chain_token = get_chain_native_token(event.victim_protocol_chain)
        return {
            'primary_asset': chain_token,
            'confidence': 50,
            'reason': 'chain_native_token'
        }
    
    # 无法归因
    return {'primary_asset': None, 'confidence': 0}
```

**Step 3：金额提取的 fallback 逻辑**
```python
def extract_exploit_amount(event):
    # 尝试从标题提取
    amount = extract_amount_from_text(event.title)
    if amount:
        return amount, 'title'
    
    # 尝试从内容提取
    amount = extract_amount_from_text(event.content)
    if amount:
        return amount, 'content'
    
    # 尝试从链上数据推断（如果有 tx_hash）
    if event.tx_hash:
        amount = get_tx_value(event.tx_hash)
        if amount:
            return amount, 'onchain'
    
    # 使用协议 TVL 作为上界估计
    if event.victim_protocol:
        tvl = get_protocol_tvl(event.victim_protocol)
        return tvl * 0.1, 'tvl_estimate'  # 假设最多被盗 10% TVL
    
    return None, 'unknown'
```

**Step 4：时效性检查**
```python
def is_exploit_timely(event):
    event_time = event.published_at
    now = datetime.now()
    delay = (now - event_time).total_seconds() / 3600  # 小时
    
    # 大额盗币（>$50M）可以容忍 24h 延迟
    if event.stolen_amount > 50_000_000:
        return delay < 24
    
    # 中等金额（$10M-$50M）只容忍 6h 延迟
    elif event.stolen_amount > 10_000_000:
        return delay < 6
    
    # 小额盗币（<$10M）只容忍 1h 延迟
    else:
        return delay < 1
```

### 修复后的合理预期
- 28 条 active exploit 中，应该有 **3-5 条**能通过（约 10-20%）
- 通过的应该是：金额 > $10M + 有明确协议 + 资产归因置信度 > 50% + 时效性 < 6h

---

## 5. Flow 类该如何拆成盘中、早报/晚报、只归档？

### 三分法处理策略

| Flow Subtype | 处理方式 | 发布时机 | 标准 | 理由 |
|---|---|---|---|---|
| **etf_creation_redemption** | 晚报汇总 | 每日 20:00 UTC | 单日净流入/流出 > $200M 或连续 3 日同向 | ETF 申赎数据有 T+1 延迟，盘中发没意义 |
| **cex_netflow** | 盘中 alert | 实时（15min 延迟内） | 单次流入/流出 > $50M + 异常倍数 > 3σ | 大额 CEX 流向可能预示抛压或吸筹 |
| **institutional_disclosure** | 早报背景 | 每日 08:00 UTC | 13F 披露、季报、年报 | 机构披露有固定时间表，不适合盘中 |
| **etf_macro_news** | 只归档 | 不发布 | - | CEO 发言、分析师观点是噪音 |
| **flow_unclear** | 只归档 | 不发布 | - | 连方向都不明确的数据无价值 |

### 具体实现逻辑

**盘中 alert（cex_netflow）：**
```python
def should_alert_cex_netflow(event):
    # 必须有明确方向
    if event.flow_direction not in ['inflow', 'outflow']:
        return False
    
    # 必须有金额
    if not event.amount_usd or event.amount_usd < 50_000_000:
        return False
    
    # 必须是异常值（相对历史 30 日）
    historical_mean = get_30d_mean_netflow(event.exchange, event.asset)
    historical_std = get_30d_std_netflow(event.exchange, event.asset)
    z_score = (event.amount_usd - historical_mean) / historical_std
    if abs(z_score) < 3:
        return False
    
    # 必须时效性 < 15min
    if event.source_delay_minutes > 15:
        return False
    
    return True
```

**晚报汇总（etf_creation_redemption）：**
```python
def generate_etf_daily_digest(date):
    events = get_etf_events_by_date(date)
    
    # 按资产聚合
    summary = {}
    for event in events:
        asset = event.asset_symbol
        if asset not in summary:
            summary[asset] = {'inflow': 0, 'outflow': 0, 'net': 0}
        
        if event.flow_direction == 'inflow':
            summary[asset]['inflow'] += event.amount_usd
        else:
            summary[asset]['outflow'] += event.amount_usd
        
        summary[asset]['net'] = summary[asset]['inflow'] - summary[asset]['outflow']
    
    # 只发布净流入/流出 > $200M 的资产
    digest_items = []
    for asset, data in summary.items():
        if abs(data['net']) > 200_000_000:
            digest_items.append({
                'asset': asset,
                'net_flow': data['net'],
                'direction': 'inflow' if data['net'] > 0 else 'outflow'
            })
    
    return digest_items
```

**早报背景（institutional_disclosure）：**
```python
def generate_institutional_morning_brief(date):
    # 获取前一日的机构披露
    events = get_institutional_events_by_date(date - timedelta(days=1))
    
    # 只保留 Top 10 机构的披露
    top_institutions = ['BlackRock', 'Grayscale', 'Fidelity', 'ARK', ...]
    filtered = [e for e in events if e.institution in top_institutions]
    
    # 按持仓变化排序
    sorted_events = sorted(filtered, key=lambda e: abs(e.position_change_usd), reverse=True)
    
    return sorted_events[:5]  # 只取 Top 5
```

---

## 6. PreFilter 下一步最小实现应该补什么字段？

### 优先级排序（1 最高，4 最低）

**优先级 1：5min/15min price-in 检测**
- **为什么最重要**：这是判断"事件是否已被市场消化"的核心指标。如果事件发布前 5 分钟价格已经异动 >1%，说明消息已经泄露或被抢跑，再发就是马后炮。
- **实现方式**：
  ```python
  def check_price_in(event):
      asset = event.primary_tradable_asset
      event_time = event.published_at
      
      # 获取事件前 5min/15min/1h 的价格变化
      price_5min_before = get_price(asset, event_time - timedelta(minutes=5))
      price_at_event = get_price(asset, event_time)
      price_change_5min = (price_at_event - price_5min_before) / price_5min_before
      
      # 如果事件前 5min 已经异动 >1%，标记为 price-in
      if abs(price_change_5min) > 0.01:
          return {
              'is_priced_in': True,
              'price_change_5min': price_change_5min,
              'block_reason': 'already_priced_in_5min'
          }
      
      # 同理检查 15min
      price_15min_before = get_price(asset, event_time - timedelta(minutes=15))
      price_change_15min = (price_at_event - price_15min_before) / price_15min_before
      if abs(price_change_15min) > 0.02:
          return {
              'is_priced_in': True,
              'price_change_15min': price_change_15min,
              'block_reason': 'already_priced_in_15min'
          }
      
      return {'is_priced_in': False}
  ```
- **数据
