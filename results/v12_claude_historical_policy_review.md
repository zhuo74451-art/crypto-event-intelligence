# Claude Response

- generated_at: 2026-05-28 19:14:27 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V12_HISTORICAL_POLICY_REVIEW_PROMPT.md
- prompt_sha256_16: c47d9e6f96280b5d

# Crypto Event Intelligence v12 历史样本与路由策略复审报告

## 一、扩样本与拆 `other` 方向评审

### ✅ 做对的部分
- **从 500 扩到 2000 条历史快讯**：这是正确的，20 条样本根本不够做统计推断
- **标题优先修复 hack_security 污染**：抓住了关键问题，旧案背景词过滤是对的
- **引入 `candidate_event_subtype`**：比直接塞 `other` 好，至少有了二级分类能力

### ❌ 仍然错的部分

**1. 样本窗口设计有问题**
```
当前：UTC 往前 7-180 天
问题：
- 7 天太短，价格还没充分反应
- 180 天太长，跨越了不同市场 regime（牛熊转换、流动性环境变化）
- 应该改成：30-90 天窗口，按月滚动回测
```

**建议修改**：
```python
# data/backtest_window_config.csv
window_id,start_days_ago,end_days_ago,regime_label,min_sample_requirement
w1,90,60,recent_regime,50
w2,120,90,previous_regime,50
w3,150,120,older_regime,30
```

**2. `other` 拆解不彻底**
```
当前问题：
- 候选里 705 条 other（35%）
- 回测里 20 条 other（12%）
- 说明分类规则覆盖率只有 65%
```

**根本原因**：你们在用关键词匹配做分类，而不是结构化字段。

---

## 二、`whale_wallet_position` 强表现验证方案

### 🚨 高度怀疑这是污染数据

**四大污染源分析**：

#### 1. HYPE 污染（最可能）
```
验证方法：
检查这 59 条样本的 asset 分布
如果 >30% 是 HYPE，立即作废这个结论
```

**立即执行脚本**：
```python
# scripts/validate_whale_position_hype_contamination.py
import pandas as pd

backfill = pd.read_csv('data/event_backfill_non_benchmark_alt.csv')
whale = backfill[backfill['event_type'] == 'whale_position']

# 检查 HYPE 占比
hype_count = whale[whale['asset'].str.contains('HYPE', na=False)].shape[0]
hype_ratio = hype_count / len(whale)

# 检查时间分布
whale['published_at'] = pd.to_datetime(whale['published_at'])
time_range = whale['published_at'].max() - whale['published_at'].min()

# 输出验收标准
assert hype_ratio < 0.15, f"HYPE 污染过高: {hype_ratio:.2%}"
assert time_range.days > 60, f"时间跨度不足: {time_range.days} 天"
assert len(whale['asset'].unique()) > 15, "资产多样性不足"
```

#### 2. 价格先动后报道（次可能）
```
验证方法：
检查 event_time 与 price_change_start_time 的时序关系
```

**新增字段到 backfill**：
```csv
# data/event_backfill_non_benchmark_alt.csv 新增列
event_id,asset,event_type,published_at,
price_peak_time_24h,     # 24h 内价格峰值时间
time_to_peak_hours,      # 发布到峰值的小时数
is_price_leading         # TRUE 如果峰值在发布前 2 小时内出现
```

**验收标准**：
```
如果 is_price_leading 比例 >40%，说明是追涨新闻
如果 time_to_peak_hours 中位数 <1，说明价格已经 price-in
```

#### 3. 新闻追涨（次可能）
```
验证方法：
检查同一 asset 在事件前 24h 是否已有其他新闻
```

**新增脚本**：
```python
# scripts/check_news_clustering.py
# 对每条 whale_position 事件
# 查询同 asset 前 24h 是否有 >2 条其他快讯
# 如果有，标记为 news_cluster=TRUE
```

#### 4. 样本选择偏差（最隐蔽）
```
问题：
你们的 "成熟过滤" 要求 72h 后才回测
但 whale_position 可能在 6-12h 就完成价格反应
72h 后的样本可能只是"活下来的幸存者"
```

**验证方法**：
```python
# 对比不同成熟窗口的表现
mature_windows = [6, 12, 24, 48, 72]
for window in mature_windows:
    # 重新跑回测
    # 看 win_rate 是否随窗口增加而上升
    # 如果是，说明存在幸存者偏差
```

---

## 三、`other` 拆解具体方案

### 当前 705 条 `other` 应该拆成的子类型

**立即新增到 `event_type` 枚举**：

```python
# config/event_taxonomy_v12.py

NEW_EVENT_TYPES = {
    # 1. 监管与合规（预计占 other 的 25%）
    'regulatory_action': {
        'keywords_title': ['SEC', 'CFTC', '监管', '合规', '诉讼', '起诉', '罚款'],
        'keywords_body': ['regulatory', 'compliance', 'lawsuit', 'settlement'],
        'exclude_if_contains': ['ETF 批准'],  # 这个归 institutional_flow
    },
    
    # 2. 协议经济与代币经济学（预计占 15%）
    'tokenomics_change': {
        'keywords_title': ['销毁', '回购', '通胀率', '排放', 'emission', 'burn'],
        'keywords_body': ['token supply', 'inflation schedule', 'buyback'],
        'must_have_asset': True,
    },
    
    # 3. 生态与合作（预计占 20%）
    'ecosystem_partnership': {
        'keywords_title': ['合作', '集成', '整合', 'partnership', 'integration'],
        'keywords_body': ['collaborate', 'integrate', 'support'],
        'exclude_if_contains': ['收购', '投资'],  # 这个归 project_business
    },
    
    # 4. 技术与产品发布（预计占 15%）
    'product_launch': {
        'keywords_title': ['推出', '发布', '上线', 'launch', 'release', 'debut'],
        'keywords_body': ['new feature', 'mainnet', 'testnet'],
        'must_have_asset': True,
    },
    
    # 5. 社区与治理（预计占 10%）
    'community_governance': {
        'keywords_title': ['提案', '投票', '治理', 'proposal', 'vote', 'governance'],
        'keywords_body': ['community decision', 'DAO vote'],
        'exclude_if_contains': ['质押'],  # 这个归 staking_governance
    },
    
    # 6. 市场情绪与舆论（预计占 10%）
    'market_sentiment': {
        'keywords_title': ['分析师', '预测', '看涨', '看跌', 'analyst', 'prediction'],
        'keywords_body': ['price target', 'forecast', 'outlook'],
        'default_action': 'digest_only',  # 这类不该进实时雷达
    },
    
    # 7. 真正的其他（预计占 5%）
    'uncategorized': {
        'description': '无法归类的剩余项',
    }
}
```

### 验收标准

**执行脚本**：
```bash
python scripts/reclassify_other_with_new_taxonomy.py \
  --input data/event_candidates_real_2000_older_review.csv \
  --output data/event_candidates_real_2000_older_v12_reclassified.csv \
  --report data/other_reclassification_report.csv
```

**验收指标**：
```
1. uncategorized 占比 <10%（当前是 35%）
2. 每个新类型至少有 20 条样本
3. 人工抽查 50 条，准确率 >85%
```

---

## 四、`hack_security` 分类清洗方案

### 当前问题诊断

```
36 条样本，历史表现弱
可能原因：
1. 混入了旧案追踪（"Bitfinex 黑客资金转移"）
2. 混入了制裁新闻（"OFAC 制裁地址"）
3. 混入了协议暂停（"项目方暂停合约"）
4. 真实 exploit 被稀释
```

### 拆解方案

**新增 `hack_security` 的 4 个子类型**：

```python
# config/hack_security_subtypes.py

HACK_SUBTYPES = {
    'active_exploit': {
        # 正在发生的攻击
        'keywords_title': ['被攻击', '被盗', '漏洞利用', 'exploited', 'hacked', 'drained'],
        'time_sensitivity': 'realtime',  # 必须 <2h 发出
        'exclude_patterns': ['追回', '已恢复', 'recovered', '2021', '2022', '2023'],
        'action': 'boost',
    },
    
    'security_disclosure': {
        # 漏洞披露但未被利用
        'keywords_title': ['漏洞', '安全更新', 'vulnerability', 'security patch'],
        'keywords_body': ['disclosed', 'patched', 'fixed'],
        'action': 'digest_only',
    },
    
    'fund_recovery': {
        # 旧案追踪、资金追回
        'keywords_title': ['追回', '转移', '冻结', 'recovered', 'frozen', 'moved'],
        'keywords_body': ['2021', '2022', '2023', 'Bitfinex', 'Mt.Gox'],
        'action': 'digest_only',
    },
    
    'regulatory_enforcement': {
        # 制裁、司法行动
        'keywords_title': ['制裁', '起诉', 'OFAC', 'sanctioned', 'indicted'],
        'action': 'collect_more',  # 需要更多样本
    }
}
```

### 验收标准

```python
# scripts/validate_hack_classification.py

# 1. 重新分类 36 条样本
# 2. 只保留 active_exploit 进入回测
# 3. 如果 active_exploit <10 条，标记为样本不足
# 4. 如果 active_exploit 的 win_rate >0.6，才允许 boost
```

---

## 五、`source_type` 三层架构设计

### 当前问题

```
source_type 现在是字符串，例如：
- "Foresight News"
- "Foresight News - 快讯"
- "ForesightNews"

问题：
1. 同一来源有多种写法
2. 无法按来源家族做聚合分析
3. 无法区分快讯 vs 深度文章
```

### 新架构设计

**新增 3 个字段**：

```csv
# data/source_registry.csv（新建主表）
source_id,source_family,source_channel,source_type_legacy,reliability_score,latency_minutes,content_depth
foresight_flash,foresight,flash,Foresight News,0.85,5,low
foresight_article,foresight,article,Foresight News,0.90,30,high
theblock_research,theblock,research,The Block,0.95,60,high
coindesk_news,coindesk,news,CoinDesk,0.80,15,medium
```

**字段说明**：
- `source_id`：唯一标识，snake_case
- `source_family`：来源家族（foresight/theblock/coindesk）
- `source_channel`：内容类型（flash=快讯，news=新闻，research=研究，social=社交）
- `reliability_score`：0-1，历史准确率
- `latency_minutes`：发布到你们抓取的平均延迟
- `content_depth`：low/medium/high，内容深度

**迁移脚本**：

```python
# scripts/migrate_source_type_to_registry.py

import pandas as pd

# 1. 读取所有历史 source_type
legacy_sources = pd.read_csv('data/raw_news_real_2000_older.csv')['source_type'].unique()

# 2. 生成映射表（需要人工审核）
mapping = []
for s in legacy_sources:
    mapping.append({
        'source_type_legacy': s,
        'source_id': None,  # 人工填写
        'source_family': None,
        'source_channel': None,
    })

pd.DataFrame(mapping).to_csv('data/source_migration_todo.csv', index=False)
print("请人工填写 source_migration_todo.csv，然后运行第二阶段")
```

### 验收标准

```
1. source_registry.csv 覆盖所有历史 source_type
2. 每个 source_family 至少有 50 条历史样本
3. 按 source_channel 分组，flash 的 latency_minutes <10
4. 回测时按 source_family 做分层，看不同来源的信号质量
```

---

## 六、Strategy Policy Boost 条件设计

### 当前问题

```
只有 1 个 boost（whale_wallet_position）
但这个可能是污染数据
过于保守会导致系统没有价值
```

### Boost 准入标准（严格版）

**必须同时满足 5 个条件**：

```python
# config/boost_criteria_v12.py

BOOST_CRITERIA = {
    'sample_size': {
        'min_24h': 30,      # 24h 窗口至少 30 个样本
        'min_total': 50,    # 总样本至少 50 个
        'min_assets': 10,   # 至少覆盖 10 个不同资产
    },
    
    'performance': {
        'min_win_rate_24h': 0.65,           # 24h 胜率 >65%
        'min_avg_abnormal_24h': 0.05,       # 平均超额收益 >5%
        'max_max_drawdown_24h': -0.15,      # 最大回撤 <-15%
    },
    
    'stability': {
        'min_win_rate_std': None,           # 胜率标准差（跨时间窗口）
        'max_performance_decay': 0.2,       # 近期 vs 远期表现衰减 <20%
    },
    
    'contamination_check': {
        'max_single_asset_ratio': 0.3,      # 单一资产占比 <30%
        'max_hype_ratio': 0.15,             # HYPE 占比 <15%
        'max_price_leading_ratio': 0.4,     # 价格先动占比 <40%
    },
    
    'regime_robustness': {
        'min_regimes_tested': 2,            # 至少跨 2 个市场 regime
        'min_win_rate_per_regime': 0.55,    # 每个 regime 胜率 >55%
    }
}
```

### Downrank 条件

```python
DOWNRANK_CRITERIA = {
    # 历史表现差
    'poor_performance': {
        'max_win_rate_24h': 0.45,
        'max_avg_abnormal_24h': 0.0,
    },
    
    # 或者样本不足但表现平庸
    'insufficient_mediocre': {
        'max_sample_size': 20,
        'max_win_rate_24h': 0.55,
    }
}
```

### Digest_only 条件

```python
DIGEST_ONLY_CRITERIA = {
    # 1. 市场情绪类（主观预测）
    'event_type': ['market_sentiment', 'analyst_opinion'],
    
    # 2. 旧案追踪
    'event_subtype': ['fund_recovery', 'old_case_update'],
    
    # 3. 低时效性
    'source_channel': ['research', 'weekly_report'],
    
    # 4. 历史表现弱但有信息价值
    'win_rate_24h': (0.45, 0.55),  # 胜率在 45-55% 之间
}
```

### 验收标准

```bash
python scripts/apply_boost_criteria_v12.py \
  --input results/event_type_performance_matrix_non_benchmark_alt.csv \
  --output data/tg_signal_policy_v12.csv \
  --report data/boost_criteria_report.csv

# 验收指标
assert boost_count >= 0, "允许 0 个 boost（如果没有符合条件的）"
assert boost_count <= 5, "最多 5 个 boost（防止过度自信）"
assert digest_only_count >= 10, "至少 10 个类型进 digest_only"
```

---

## 七、Price-in 检查与 Regime 分层接入方案

### Price-in 检查字段设计

**在 `event_backfill` 表新增列**：

```csv
# data/event_backfill_non_benchmark_alt.csv 新增
event_id,asset,event_type,published_at,
price_1h_before,         # 发布前 1h 价格
price_at_publish,        # 发布时价格
price_1h_after,          # 发布后 1h 价格
price_4h_after,          # 发布后 4h 价格
volume_1h_before,        # 发布前 1h 成交量
volume_1h_after,         # 发布后 1h 成交量
is_price_in,             # TRUE 如果发布前 1h 已涨 >3%
is_volume_spike_before,  # TRUE 如果发布前 1h 成交量 >2x 均值
price_in_score           # 0-1，综合 price-in 程度
```

**Price-in Score 计算规则**：

```python
# scripts/calculate_price_in_score.py

def calculate_price_in_score(row):
    score = 0.0
    
    # 1. 价格先动（权重 40%）
    price_change_before = (row['price_at_publish'] - row['price_1h_before']) / row['price_1h_before']
    if price_change_before > 0.03:
        score += 0.4 * min(price_change_before / 0.10, 1.0)
    
    # 2. 成交量先爆（权重 30%）
    if row['is_volume_spike_before']:
        volume_ratio = row['volume_1h_before'] / row['volume_24h_avg']
        score += 0.3 * min(volume_ratio / 3.0, 1.0)
    
    # 3. 发布后反应弱（权重 30%）
    price_change_after = (row['price_1h_after'] - row['price_at_publish']) / row['price_at_publish']
    if price_change_after < 0.02:
        score += 0.3
    
    return min(score, 1.0)
```

**使用规则**：

```python
# 在路由策略中
if event['price_in_score'] > 0.6:
    action = 'digest_only'  # 已经 price-in，不发实时
elif event['price_in_score'] > 0.4:
    priority = 'low'  # 降低优先级
```

---

### Regime 分层字段设计

**新建 `market_regime` 表**：

```csv
# data/market_regime_history.csv
date,regime_label,btc_volatility_30d,market_cap_total,btc_dominance,funding_rate_avg,regime_score
2024-01-15,bull_high_vol,0.045,1.8T,0.52,0.015,0.75
2024-02-01,bull_low_vol,0.028,2.1T,0.51,0.008,0.85
2024-03-10,correction,0.065,1.9T,0.54,-0.005,0.35
```

**Regime 分类规则**：

```python
# config/regime_classification.py

REGIME_RULES = {
    'bull_high_vol': {
        'btc_30d_return': (0.15, 1.0),
        'btc_volatility_30d': (0.04, 0.08),
        'funding_rate_avg': (0.01, 0.03),
    },
    'bull_low_vol': {
        'btc_30d_return': (0.10, 0.30),
        'btc_volatility_30d': (0.02, 0.04),
        'funding_rate_avg': (0.005, 0.015),
    },
    'ranging': {
        'btc_30d_return': (-0.05, 0.10),
        'btc_volatility_30d': (0.02, 0.05),
    },
    'correction': {
        'btc_30d_return': (-0.20, 0.0),
        'btc_volatility_30d': (0.05, 0.10),
        'funding_rate_avg': (-0.01, 0.005),
    },
    'bear': {
        'btc_30d_return': (-1.0, -0.15),
        'btc_volatility_30d': (0.03, 0.08),
    }
}
```

**接入回测链路**：

```python
# scripts/backfill_with_regime.py

import pandas as pd

# 1. 读取回测数据
backfill = pd.read_csv('data/event_backfill_non_benchmark_alt.csv')
regime = pd.read_csv('data/market_regime_history.csv')

# 2. 按日期匹配 regime
backfill['date'] = pd.to_datetime(backfill['published_at']).dt.date
backfill = backfill.merge(regime[['date', 'regime_label']], on='date', how='left')

# 3. 按 regime 分组统计
regime_performance = backfill.groupby(['event_type', 'regime_label']).agg({
    'abnormal_return_primary_24h': ['mean', 'std', 'count'],
    'is_profitable_24h': 'mean'
}).reset_index()

regime_performance.to_csv('results/event_performance_by_regime.csv', index=False)
```

### 验收标准

```
1. market_regime_history.csv 覆盖回测窗口所有日期
2. 每个 regime 至少有 30 天样本
3. 回测样本至少跨 2 个不同 regime
4. 输出 event_performance_by_regime.csv，每个 event_type 在每个 regime 的表现
5. 如果某 event_type 在某 regime 胜率 <0.45，标记为 regime_sensitive
```

---

## 八、资产识别优先级方案

### 当前问题

```
missing_asset: 835 / 2000 (42%)
missing_symbol: 876 / 2000 (44%)

问题：
1. 无法回测
2. 无法路由到正确的 TG 频道
3. 无法做资产级别的表现分析
```

### 优先级分层

**Tier 1：必须立即补全（阻塞回测）**

```python
# 条件：
# 1. event_type 在 BOOST 或 PROMISING 列表中
# 2. 且 suggest_include = TRUE
# 3. 且 asset 字段为空

# 执行：
python scripts/extract_tier1_missing_assets.py \
  --input data/event_candidates_real_2000_older_review_suggested.csv \
  --output data/missing_assets_tier1_urgent.csv

# 人工补全后：
# 更新 config/symbol_map.csv
```

**Tier 2：应该补全（提升覆盖率）**

```python
# 条件：
# 1. event_type 在 COLLECT_MORE 列表中
# 2. 且 suggest_include = TRUE
# 3. 且出
