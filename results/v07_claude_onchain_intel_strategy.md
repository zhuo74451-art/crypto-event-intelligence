# Claude Response

- generated_at: 2026-05-27 17:29:47 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V07_ONCHAIN_INTEL_PROMPT.md
- prompt_sha256_16: 1f54327ec4edd3b1

# Crypto Event Intelligence v0.7 Direction Check - Brutal Assessment

## Current State: You Have a News Aggregator, Not Intelligence

Your pipeline is a **cleaned RSS feed with price correlation**. That's table stakes, not a product. Every fund intern can set up Google Alerts + CoinGecko API.

Real intelligence = **information asymmetry before it hits Twitter**. You need:
- Early warning (not news reaction)
- Non-public signals (on-chain, not articles)
- Structural changes (not price moves)

---

## 1. First-Hand Intelligence Sources Priority (v0.7)

| Priority | Source | Why | Signal Type |
|----------|--------|-----|-------------|
| **P0** | Watched address movements | Whales/treasuries move before announcements | Transfer events >$1M |
| **P0** | Stablecoin mint/burn (USDT/USDC) | Liquidity inflow = market structure change | Mint >$50M, Burn >$100M |
| **P1** | Major DEX pool liquidity changes | Exit liquidity drying up = risk signal | >20% depth change, top 50 pairs |
| **P1** | Protocol treasury outflows | Team selling, runway issues, or strategic moves | >10% treasury, known protocol addresses |
| **P2** | CEX netflow (aggregated) | Smart money entering/exiting | >$100M net 24h, per asset |

**Skip for v0.7:**
- Individual DEX trades (too noisy)
- Mempool monitoring (expensive infra)
- Social sentiment (you already have news)
- NFT metrics (different product)

---

## 2. High Value But Too Expensive/Noisy for v0.7

| Source | Why Valuable | Why Not Now |
|--------|--------------|-------------|
| Hyperliquid open interest by address | Whale positioning | Need to build position tracking DB, attribution hard |
| Smart contract deployment patterns | New scams/forks early | 10K+ deploys/day, need ML classifier |
| Cross-chain bridge flows | Capital rotation signals | 8+ chains, complex normalization |
| Validator/staking changes | Network security shifts | Slow-moving, not actionable short-term |
| GitHub commit velocity | Development momentum | Already covered by news, lagging indicator |
| Options flow (Deribit) | Sophisticated positioning | Need options pricing model, complex |

---

## 3. MVP Scope for v0.7 (3-7 Days)

### Acceptance Criteria

```
MUST HAVE:
□ 15-25 watched addresses (whales, treasuries, known entities)
□ USDT/USDC mint/burn monitoring (Ethereum mainnet only)
□ Top 20 Uniswap V3 pools liquidity depth tracking (4h snapshots)
□ SQLite schema: first_hand_events table joining existing event pipeline
□ Deterministic filters: no alert if <$1M value or <10% change
□ 1 backtest: "Did this alert happen before related news/price move?"
□ CSV export: event_id, source_type, entity, metric, threshold, timestamp
□ 5 test cases with known historical events (FTX collapse, USDC depeg, etc.)

NICE TO HAVE:
□ CEX netflow (CryptoQuant API or Glassnode free tier)
□ Etherscan API rate limiting + caching
□ Telegram draft generation for on-chain events

EXPLICITLY NOT:
✗ Real-time streaming (4h batch is fine)
✗ Multi-chain (Ethereum only)
✗ Attribution/labeling unknown addresses
✗ Predictive models
✗ UI/dashboard
```

---

## 4. Data Model for First-Hand Alerts

### Schema: `first_hand_events`

```sql
CREATE TABLE first_hand_events (
    event_id TEXT PRIMARY KEY,  -- fh_<source>_<timestamp>_<hash>
    event_type TEXT NOT NULL,   -- 'address_transfer', 'stablecoin_mint', 'dex_liquidity'
    source TEXT NOT NULL,       -- 'etherscan', 'uniswap_v3', 'tether_treasury'
    
    -- Core event data
    blockchain TEXT DEFAULT 'ethereum',
    block_number INTEGER,
    tx_hash TEXT,
    timestamp INTEGER NOT NULL,
    
    -- Entities involved
    primary_address TEXT,       -- The watched address
    counterparty_address TEXT,
    token_symbol TEXT,
    token_address TEXT,
    
    -- Metrics
    amount_usd REAL,
    amount_native REAL,
    metric_type TEXT,           -- 'transfer_out', 'mint', 'liquidity_depth'
    metric_value REAL,
    metric_change_pct REAL,
    
    -- Enrichment
    address_label TEXT,         -- 'Binance Hot Wallet', 'Tether Treasury'
    risk_category TEXT,         -- 'whale_movement', 'liquidity_risk', 'supply_change'
    
    -- Pipeline integration
    relevance_score REAL,       -- 0-1, deterministic rules
    needs_review BOOLEAN DEFAULT 0,
    approved BOOLEAN DEFAULT 0,
    draft_text TEXT,
    
    -- Backtest join keys
    related_news_ids TEXT,      -- JSON array of news event_ids within 48h
    price_impact_24h REAL,      -- BTC/ETH return if applicable
    
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_fh_timestamp ON first_hand_events(timestamp);
CREATE INDEX idx_fh_type ON first_hand_events(event_type);
CREATE INDEX idx_fh_address ON first_hand_events(primary_address);
CREATE INDEX idx_fh_approved ON first_hand_events(approved);
```

### Join to Existing Pipeline

```python
# Unified event view
SELECT 
    'news' as source_category,
    event_id,
    timestamp,
    relevance_score,
    approved
FROM news_events
WHERE approved = 1

UNION ALL

SELECT 
    'first_hand' as source_category,
    event_id,
    timestamp,
    relevance_score,
    approved
FROM first_hand_events
WHERE approved = 1

ORDER BY timestamp DESC;
```

---

## 5. Start With: Watched Addresses + Stablecoin Supply

### Why This Order:

1. **Watched addresses** (P0)
   - Lowest infrastructure cost (Etherscan API free tier: 5 calls/sec)
   - Highest signal-to-noise (you choose what to watch)
   - Proven alpha: FTX wallets moved before collapse

2. **Stablecoin mint/burn** (P0)
   - 3 addresses to monitor (Tether, Circle, Binance USD)
   - Direct market structure signal
   - Easy to backtest against BTC price

3. **DEX liquidity** (P1)
   - Uniswap V3 subgraph is free
   - 20 pools = manageable
   - Leading indicator for "rug pull" or exit liquidity

**Skip for v0.7:**
- Hyperliquid: Need to build position tracking first
- CEX market structure: Requires paid data feeds
- Protocol metrics: Too slow-moving

---

## 6. Avoiding On-Chain Noise: Deterministic Filters

### Filter Pipeline (Before Any Model/Claude)

```python
# filters.py

def filter_address_transfer(event):
    """Deterministic rules for address movements"""
    
    # Rule 1: Minimum value
    if event['amount_usd'] < 1_000_000:
        return None, "below_threshold"
    
    # Rule 2: Known spam tokens
    SPAM_TOKENS = ['HEX', 'SHIB', ...]  # maintain list
    if event['token_symbol'] in SPAM_TOKENS:
        return None, "spam_token"
    
    # Rule 3: Internal exchange movements (hot->cold wallet)
    if is_same_entity(event['from'], event['to']):
        return None, "internal_transfer"
    
    # Rule 4: Circular wash trading pattern
    if event['from'] in recent_counterparties(event['to'], hours=24):
        return None, "circular"
    
    # Rule 5: Watched address must be involved
    if not (event['from'] in WATCHLIST or event['to'] in WATCHLIST):
        return None, "not_watched"
    
    # Passed filters
    return event, "pass"


def filter_stablecoin_event(event):
    """Mint/burn filters"""
    
    # Rule 1: Minimum size
    if event['event_type'] == 'mint' and event['amount_usd'] < 50_000_000:
        return None, "small_mint"
    if event['event_type'] == 'burn' and event['amount_usd'] < 100_000_000:
        return None, "small_burn"
    
    # Rule 2: Only from known treasuries
    TREASURY_ADDRESSES = {
        '0x5754284f345afc66a98fbb0a0afe71e0f007b949': 'Tether Treasury',
        '0x55fe002aeff02f77364de339a1292923a15844b8': 'Circle USDC',
    }
    if event['from'] not in TREASURY_ADDRESSES:
        return None, "unknown_issuer"
    
    return event, "pass"


def filter_dex_liquidity(event):
    """Pool depth changes"""
    
    # Rule 1: Minimum pool size
    if event['total_liquidity_usd'] < 10_000_000:
        return None, "small_pool"
    
    # Rule 2: Minimum change
    if abs(event['change_pct']) < 20:
        return None, "small_change"
    
    # Rule 3: Top pairs only
    TOP_PAIRS = [
        'WETH/USDC', 'WETH/USDT', 'WBTC/WETH',
        # ... top 20
    ]
    if event['pair'] not in TOP_PAIRS:
        return None, "not_top_pair"
    
    return event, "pass"
```

### Noise Reduction Stats Target

```
Raw on-chain events:     100,000/day
After deterministic:     50-200/day
After deduplication:     20-80/day
Needs Claude review:     5-15/day
Approved for publish:    2-8/day
```

---

## 7. Local Rules vs Claude Judgment

### Local Deterministic Rules (No Cost, No Latency)

| Rule Type | Examples |
|-----------|----------|
| **Threshold filters** | Amount >$1M, change >20%, top 50 entities |
| **Whitelist/blacklist** | Known spam tokens, internal transfers |
| **Time-based** | Dedupe same address within 4h |
| **Structural** | Circular transfers, same-entity moves |
| **Category assignment** | If from_treasury → 'supply_change' |

### Claude Judgment (Only for Uncertain + High Value)

```python
def needs_claude_review(event):
    """When to escalate to Claude"""
    
    # High value + unknown context
    if (event['amount_usd'] > 10_000_000 and 
        event['address_label'] is None):
        return True, "large_unknown_address"
    
    # Unusual pattern
    if (event['metric_change_pct'] > 50 and
        event['event_type'] == 'dex_liquidity'):
        return True, "extreme_liquidity_change"
    
    # Multiple concurrent signals
    related_events = get_related_events(event, window_hours=2)
    if len(related_events) >= 3:
        return True, "cluster_event"
    
    # Conflicting signals
    if has_contradictory_news(event):
        return True, "needs_context"
    
    return False, None


# Claude prompt for review
CLAUDE_REVIEW_PROMPT = """
You are reviewing a first-hand on-chain event for a crypto intelligence feed.

Event: {event_summary}
Recent related news: {related_news}
Historical context: {address_history}

Questions:
1. Is this event significant enough to alert? (yes/no/uncertain)
2. What is the likely reason for this movement?
3. Risk level: low/medium/high
4. Suggested alert text (2 sentences, factual, no speculation)

Output JSON only.
"""
```

### Cost Control

```
Target: <$5/day Claude API costs for v0.7

Assumptions:
- 10 events/day need review
- 2K tokens per review (input + output)
- Claude Sonnet: $3 per 1M input tokens, $15 per 1M output

Cost: 10 * 2K * $9/1M = $0.18/day ✓
```

---

## 8. First 20 Watchlist Targets by Category

### Watched Addresses (15 addresses)

| Category | Count | Examples | Why Watch |
|----------|-------|----------|-----------|
| **Exchange Hot Wallets** | 3 | Binance, Coinbase, OKX main hot | Large outflows = potential sell pressure |
| **Stablecoin Treasuries** | 2 | Tether, Circle | Mint/burn = liquidity changes |
| **Major Protocol Treasuries** | 4 | Uniswap, Aave, Lido, MakerDAO | Treasury moves = governance/strategy |
| **Known Whale Clusters** | 3 | Top 3 BTC holders, Top 3 ETH holders | Whale accumulation/distribution |
| **Bridge Contracts** | 2 | Wormhole, Stargate main | Cross-chain capital flows |
| **Staking Contracts** | 1 | Lido stETH | Validator set changes |

### Stablecoin Monitoring (3 issuers)

- USDT (Tether Treasury)
- USDC (Circle)
- BUSD (Binance-Peg) - if still active

### DEX Pools (20 pairs)

| DEX | Pairs | Why |
|-----|-------|-----|
| **Uniswap V3** | 15 | WETH/USDC, WETH/USDT, WBTC/WETH, major altcoin pairs |
| **Curve** | 5 | 3pool, stETH/ETH, major stablecoin pools |

### Concrete Watchlist (Starter)

```python
# watchlist.py

WATCHED_ADDRESSES = {
    # Exchanges
    '0x28C6c06298d514Db089934071355E5743bf21d60': {
        'label': 'Binance Hot Wallet 1',
        'category': 'cex_hot',
        'alert_threshold_usd': 5_000_000,
    },
    '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549': {
        'label': 'Binance Hot Wallet 2',
        'category': 'cex_hot',
        'alert_threshold_usd': 5_000_000,
    },
    '0x71660c4005BA85c37ccec55d0C4493E66Fe775d3': {
        'label': 'Coinbase Hot Wallet',
        'category': 'cex_hot',
        'alert_threshold_usd': 5_000_000,
    },
    
    # Stablecoin Treasuries
    '0x5754284f345afc66a98fbb0a0afe71e0f007b949': {
        'label': 'Tether Treasury',
        'category': 'stablecoin_issuer',
        'alert_threshold_usd': 50_000_000,
    },
    '0x55fe002aeff02f77364de339a1292923a15844b8': {
        'label': 'Circle USDC Treasury',
        'category': 'stablecoin_issuer',
        'alert_threshold_usd': 50_000_000,
    },
    
    # Protocol Treasuries
    '0x1a9C8182C09F50C8318d769245beA52c32BE35BC': {
        'label': 'Uniswap Treasury',
        'category': 'protocol_treasury',
        'alert_threshold_usd': 2_000_000,
    },
    '0x25F2226B597E8F9514B3F68F00f494cF4f286491': {
        'label': 'Aave Ecosystem Reserve',
        'category': 'protocol_treasury',
        'alert_threshold_usd': 2_000_000,
    },
    '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c': {
        'label': 'Lido Treasury',
        'category': 'protocol_treasury',
        'alert_threshold_usd': 2_000_000,
    },
    '0x9e1585d9CA64243CE43D42f7dD7333190F66Ca09': {
        'label': 'MakerDAO Treasury',
        'category': 'protocol_treasury',
        'alert_threshold_usd': 2_000_000,
    },
    
    # Known Whales (use Etherscan top holders, exclude exchanges)
    '0x00000000219ab540356cBB839Cbe05303d7705Fa': {
        'label': 'ETH2 Deposit Contract',
        'category': 'staking',
        'alert_threshold_usd': 50_000_000,
    },
    # Add 3-5 more whale addresses from Etherscan top 100
    
    # Bridges
    '0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B': {
        'label': 'Wormhole Bridge',
        'category': 'bridge',
        'alert_threshold_usd': 10_000_000,
    },
    '0x296F55F8Fb28E498B858d0BcDA06D955B2Cb3f97': {
        'label': 'Stargate Bridge',
        'category': 'bridge',
        'alert_threshold_usd': 10_000_000,
    },
}

UNISWAP_V3_POOLS = [
    '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640',  # USDC/WETH 0.05%
    '0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8',  # USDC/WETH 0.3%
    '0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36',  # WETH/USDT 0.3%
    # ... add top 20
]
```

---

## 9. Alert Thresholds (First Version)

### Threshold Table

| Event Type | Metric | Threshold | Rationale |
|------------|--------|-----------|-----------|
| **Address Transfer** | USD value | >$1M | Filters out retail, keeps institutional |
| **Address Transfer (Whale)** | USD value | >$5M | Higher bar for known whales (less noisy) |
| **Stablecoin Mint** | USD value | >$50M | Significant liquidity injection |
| **Stablecoin Burn** | USD value | >$100M | Market exit signal (burns rarer than mints) |
| **DEX Liquidity Drop** | % change | >20% decline | Exit liquidity risk |
| **DEX Liquidity Add** | % change | >50% increase | Unusual, potential manipulation |
| **Protocol Treasury Out** | % of total | >10% | Major strategic move or risk |
| **Bridge Flow** | Net 24h | >$100M net | Capital rotation between chains |

### Dynamic Thresholds (v0.8+)

```python
# For v0.7: static thresholds
# For v0.8: percentile-based

def get_dynamic_threshold(event_type, lookback_days=30):
    """
    Calculate threshold as 95th percentile of recent events
    Prevents alert fatigue during high-activity periods
    """
    historical = query_events(event_type, days=lookback_days)
    return np.percentile(historical['amount_usd'], 95)
```

---

## 10. Backtest/Research Loop for First-Hand Alerts

### Validation Framework

```python
# backtest_first_hand.py

def backtest_alert_usefulness(event_type, lookback_days=90):
    """
    Test: Did this alert provide advance warning?
    """
    
    events = load_first_hand_events(event_type, days=lookback_days)
    
    results = []
    for event in events:
        
        # 1. Was there related news within 48h AFTER?
        related_news = find_news_after(
            event['timestamp'], 
            window_hours=48,
            entity=event['primary_address']
        )
        
        # 2. Was there abnormal price movement?
        price_impact = calculate_abnormal_return(
            event['timestamp'],
            asset='BTC',  # or relevant asset
            window_hours=24
        )
        
        # 3. Was this event unique or noisy?
        similar_events = count_similar_events(
            event,
            window_hours=24
        )
        
        results.append({
            'event_id': event['event_id'],
            'had_followup_news': len(related_news) > 0,
            'news_lag_hours': min([n['lag'] for n in related_news]) if related_news else None,
            'price_impact_24h': price_impact,
            'was_unique': similar_events == 1,
            'signal_quality': score_signal_quality(...)
        })
    
    return pd.DataFrame(results)


def score_signal_quality(had_news, news_lag, price_impact, was_unique):
    """
    Signal quality score:
    - High: Alert came before news (lead time >4h) AND price moved
    - Medium: Alert came before news OR price moved
    - Low: No followup news, no price impact
    - Noise: Multiple similar alerts, no impact
    """
    if had_news and news_lag > 4 and abs(price_impact) > 2:
        return 'high'
    elif had_news or abs(price_impact) > 2:
        return 'medium'
    elif not was_unique:
        return 'noise'
    else:
        return 'low'
```

### Acceptance Criteria for v0.7

```
Backtest on 3 known historical events:

1. FTX collapse (Nov 2022)
   □ Watchlist should catch FTX hot wallet outflows 2-5 days before news
   □ Alert should trigger on >$100M outflow
   
2. USDC depeg (Mar 2023)
   □ Should catch Circle treasury activity or stETH/ETH pool changes
   □ Alert 12-24h before mainstream news
   
3. Curve hack (Jul 2023)
   □ Should catch unusual liquidity drain from affected pools
   □ Alert within 1h of exploit (faster than news)

Success = 2/3 events detected with >4h lead time vs news
```

### Research Loop (
