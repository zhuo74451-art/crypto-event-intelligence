# Market Radar v1.12-P — Live Source Readiness Audit Report

**Generated**: 2026-06-05 04:13:18 UTC+8
**Version**: v1.12-p
**Run ID**: 20260605_022952
**Task ID**: 20260605_022952.r03
**Status**: PASSED

---

## 1. 审计目标

v112P Live Source Readiness Audit 的目标是：在本地固定卡片矩阵 (v112A→v112N)
和发送预览包 (v112O) 连续通过后，**不接任何 live API**，对 5 类固定卡片的
未来真实数据源接入做好完整准备度审计。

回答的问题：

- 每类卡片未来需要哪些 live source？
- 需要哪些字段？是否需要 API key / 付费接口 / WebSocket / daemon？
- 是否能先做 one-shot live candidate experiment？
- 哪一类最适合作为下一阶段第一个低风险 live-like 实验对象？

---

## 2. 上游验证：v112N / v112O 状态

### v112N Master Dry-Run

| 检查项 | 状态 |
|--------|------|
| status_passed | ✅ |
| dry_run_only | ✅ |
| eligible_signal_count_9 | ✅ |
| idempotency_passed | ✅ |
| real_tg_sent_false | ✅ |
| external_api_called_false | ✅ |

**v112N 结论**: ✅ 通过

### v112O Send Preview Pack

| 检查项 | 状态 |
|--------|------|
| status_passed | ✅ |
| send_preview_pack_ready | ✅ |
| preview_card_count_9 | ✅ |
| dry_run_only | ✅ |
| real_tg_sent_false | ✅ |
| external_api_called_false | ✅ |

**v112O 结论**: ✅ 通过

---

## 3. 5 类卡片 Live Source Readiness 总览

| Card Type | Preview Cards | Score | Level | One-Shot | Credential | Paid API | Daemon |
|-----------|--------------|-------|-------|----------|------------|----------|--------|
| price_oi_volume_anomaly | 0 | 15/18 | high | ✅ | ✅ 不需要 | ✅ 不需要 | ✅ 不需要 |
| whale_position_alert | 2 | 16/18 | high | ✅ | ✅ 不需要 | ✅ 不需要 | ✅ 不需要 |
| liquidation_pressure | 2 | 15/18 | high | ✅ | ⚠️ 需要 | ✅ 不需要 | ✅ 不需要 |
| multi_asset_market_sync | 3 | 18/18 | high | ✅ | ✅ 不需要 | ✅ 不需要 | ✅ 不需要 |
| news_event_market_impact | 2 | 10/18 | medium | ✅ | ⚠️ 需要 | ⚠️ 可能需要 | ✅ 不需要 |

---

## 4. 各类卡片详细审计

### 4.1 行情异动 (Price/OI/Volume Anomaly) (`price_oi_volume_anomaly`)

**Readiness Score**: 15/18 (HIGH)

#### Required Live Sources

| Source | Data | Cost | Credential |
|--------|------|------|------------|
| CoinGecko Public API | price | free | none |
| CoinCap Public API | price (fallback) | free | none |
| Coinglass Public / Free Tier | open_interest | free_tier | api_key_free |
| Exchange Public REST (Binance/Bybit/OKX) | volume | free | none |

#### Required Fields

`asset_symbol, current_price, price_change_1h_pct, price_change_24h_pct, open_interest, oi_change_1h_pct, oi_change_24h_pct, volume_24h, volume_change_pct, observation_timestamp`

#### Scoring Breakdown

| Dimension | Score |
|-----------|-------|
| local_artifact_complete | 1/2 |
| has_preview_cards | 0/2 |
| live_source_likely_free | 2/2 |
| no_credential_required | 2/2 |
| no_daemon_required | 2/2 |
| one_shot_possible | 2/2 |
| data_fields_simple | 2/2 |
| easy_fallback | 2/2 |
| no_production_write_risk | 2/2 |

#### Failure Modes

- ⚠️ rate_limit: free API tier may throttle at >30 req/min
- ⚠️ data_gap: OI data may lag 5-15 minutes behind price
- ⚠️ exchange_availability: single exchange may pause API during maintenance
- ⚠️ asset_coverage: some altcoins may not have OI data on free tier

#### Fallback Strategy

- 🔄 use CoinCap as price fallback if CoinGecko rate-limited
- 🔄 use Binance public /ticker as volume fallback if Coinglass unavailable
- 🔄 skip OI field if unavailable; note in card as 'OI data temporarily unavailable'
- 🔄 use spot-only metrics as degraded mode for assets without derivatives data

#### 建议

> FIRST CANDIDATE: price_oi_volume_anomaly scored highest (15/18). 0 preview cards exist. All sources free, no credentials, one-shot feasible. v112Q should plan a local one-shot experiment first.

### 4.2 巨鲸仓位警报 (Whale Position Alert) (`whale_position_alert`)

**Readiness Score**: 16/18 (HIGH)

#### Required Live Sources

| Source | Data | Cost | Credential |
|--------|------|------|------------|
| HyperLiquid Public API | position_data | free | none |
| CoinGecko Public API | current_price | free | none |
| Wallet Label DB (local or public) | address_labels | free | none |

#### Required Fields

`wallet_address, address_label, asset_symbol, position_direction, position_size_usd, leverage, entry_price, current_price, unrealized_pnl, liquidation_price, liquidation_distance_pct, observation_timestamp`

#### Scoring Breakdown

| Dimension | Score |
|-----------|-------|
| local_artifact_complete | 2/2 |
| has_preview_cards | 2/2 |
| live_source_likely_free | 2/2 |
| no_credential_required | 2/2 |
| no_daemon_required | 2/2 |
| one_shot_possible | 2/2 |
| data_fields_simple | 1/2 |
| easy_fallback | 1/2 |
| no_production_write_risk | 2/2 |

#### Failure Modes

- ⚠️ rate_limit: HyperLiquid API has burst limits
- ⚠️ label_staleness: address labels may be outdated or incorrect
- ⚠️ position_closure: position may close between pull and review
- ⚠️ data_quality: leverage/entry_price may differ from actual due to partial closes

#### Fallback Strategy

- 🔄 degrade to 'unknown whale' label if address DB unavailable
- 🔄 use CoinGecko price as fallback if HL price feed differs >2%
- 🔄 skip win_rate/historical if label data missing
- 🔄 flag 'position may have changed since observation' in card

#### 建议

> FIRST CANDIDATE: whale_position_alert scored highest (16/18). 2 preview cards exist. All sources free, no credentials, one-shot feasible. v112Q should plan a local one-shot experiment first.

### 4.3 清算压力 (Liquidation Pressure) (`liquidation_pressure`)

**Readiness Score**: 15/18 (HIGH)

#### Required Live Sources

| Source | Data | Cost | Credential |
|--------|------|------|------------|
| Coinglass Liquidation API (free tier) | liquidation_data | free_tier | api_key_free |
| Exchange Public REST (Binance/Bybit) | oi_and_volume | free | none |
| CoinGecko Public API | current_price | free | none |

#### Required Fields

`asset_symbol, current_price, liquidation_long_1h_usd, liquidation_short_1h_usd, liquidation_long_24h_usd, liquidation_short_24h_usd, open_interest, volume_24h, observation_window_hours, observation_timestamp`

#### Scoring Breakdown

| Dimension | Score |
|-----------|-------|
| local_artifact_complete | 2/2 |
| has_preview_cards | 2/2 |
| live_source_likely_free | 1/2 |
| no_credential_required | 1/2 |
| no_daemon_required | 2/2 |
| one_shot_possible | 2/2 |
| data_fields_simple | 2/2 |
| easy_fallback | 1/2 |
| no_production_write_risk | 2/2 |

#### Failure Modes

- ⚠️ coinglass_key_expired: free API key requires periodic renewal
- ⚠️ data_lag: Coinglass liquidation data may be 5-30 minutes delayed
- ⚠️ exchange_limited: free tier may only cover top exchanges/assets
- ⚠️ sparse_markets: low-liquidity assets may have no meaningful liquidation data

#### Fallback Strategy

- 🔄 use exchange public OI + volume as degraded proxy for liquidation pressure
- 🔄 skip cluster/heatmap if Coinglass premium data unavailable
- 🔄 flag 'liquidation data from free tier; may miss tail exchanges'
- 🔄 fallback to Binance-only liquidation data if aggregator unavailable

#### 建议

> FIRST CANDIDATE: liquidation_pressure scored highest (15/18). 2 preview cards exist. All sources free, no credentials, one-shot feasible. v112Q should plan a local one-shot experiment first.

### 4.4 多资产共振 (Multi-Asset Market Sync) (`multi_asset_market_sync`)

**Readiness Score**: 18/18 (HIGH)

#### Required Live Sources

| Source | Data | Cost | Credential |
|--------|------|------|------------|
| CoinGecko Public API | multi_asset_price | free | none |
| CoinCap Public API | price_fallback | free | none |
| Exchange Public REST | oi_and_volume | free | none |

#### Required Fields

`asset_symbols_list, sync_type, direction, price_changes_pct_list, observation_window_minutes, avg_price_change_pct, avg_volume_change_pct, avg_oi_change_pct, sync_score, sector_label, total_liquidation_usd, observation_timestamp`

#### Scoring Breakdown

| Dimension | Score |
|-----------|-------|
| local_artifact_complete | 2/2 |
| has_preview_cards | 2/2 |
| live_source_likely_free | 2/2 |
| no_credential_required | 2/2 |
| no_daemon_required | 2/2 |
| one_shot_possible | 2/2 |
| data_fields_simple | 2/2 |
| easy_fallback | 2/2 |
| no_production_write_risk | 2/2 |

#### Failure Modes

- ⚠️ rate_limit: pulling N assets simultaneously may hit free tier limit
- ⚠️ sector_misclassification: sector labels may drift over time
- ⚠️ false_sync: short-window correlation may be noise, not signal
- ⚠️ data_consistency: different sources may timestamp differently

#### Fallback Strategy

- 🔄 reduce asset count to top-5 if rate-limited
- 🔄 use CoinCap bulk endpoint for single-call multi-asset price
- 🔄 skip sector label if classification data unavailable
- 🔄 flag 'correlation may be spurious in short window' in card

#### 建议

> FIRST CANDIDATE: multi_asset_market_sync scored highest (18/18). 3 preview cards exist. All sources free, no credentials, one-shot feasible. v112Q should plan a local one-shot experiment first.

### 4.5 新闻事件 (News Event Market Impact) (`news_event_market_impact`)

**Readiness Score**: 10/18 (MEDIUM)

#### Required Live Sources

| Source | Data | Cost | Credential |
|--------|------|------|------------|
| CryptoPanic News API (free tier) | news_headlines | free_tier | api_key_free |
| Twitter/X API (free tier) | crypto_tweets | free_tier | api_key |
| RSS feeds (CoinDesk, TheBlock, Decrypt) | articles | free | none |
| CoinGecko Public API | price_impact | free | none |

#### Required Fields

`event_title, event_category, market_impact_direction, affected_assets, source_name, source_url, published_at_utc, trading_relevance, is_priced_in, observation_timestamp`

#### Scoring Breakdown

| Dimension | Score |
|-----------|-------|
| local_artifact_complete | 2/2 |
| has_preview_cards | 2/2 |
| live_source_likely_free | 0/2 |
| no_credential_required | 0/2 |
| no_daemon_required | 2/2 |
| one_shot_possible | 1/2 |
| data_fields_simple | 0/2 |
| easy_fallback | 1/2 |
| no_production_write_risk | 2/2 |

#### Failure Modes

- ⚠️ api_key_expired: CryptoPanic/Twitter free keys may expire or change terms
- ⚠️ source_unreliable: single news source may be inaccurate or biased
- ⚠️ sentiment_misclassification: automated sentiment may misread sarcasm
- ⚠️ priced_in_uncertainty: hard to determine if event already priced in
- ⚠️ rate_limit_severe: Twitter free tier API very limited (read-only)
- ⚠️ language_barrier: non-English news may be missed by free aggregators

#### Fallback Strategy

- 🔄 use RSS feeds (CoinDesk, TheBlock) as baseline — always free, no key
- 🔄 skip sentiment/social_volume if NLP pipeline not available
- 🔄 flag 'single-source; cross-reference before trading decision'
- 🔄 degrade to manual-curation mode if all APIs unavailable
- 🔄 use CoinGecko trending as weak signal for unpriced events

#### 建议

> SECOND PRIORITY: news_event_market_impact scored 10/18. One-shot possible but may need free API key setup. Plan v112Q experiment after the highest-scored card type.

---

## 5. 推荐首个 Live-Like One-Shot 实验对象

### 🏆 推荐：`multi_asset_market_sync`

**理由**：

- Readiness Score: **18/18** (最高分)
- Readiness Level: **HIGH**
- Preview Cards: **3** 条
- One-Shot 可行: **✅ 是**
- 需要凭证: **❌ 不需要**
- 需要付费 API: **❌ 不需要**
- 需要 Daemon: **❌ 不需要**

**数据源全部免费、无需 API Key、纯 REST 调用、字段简单、失败易降级。**

建议 v112Q 阶段仅做 **one-shot 计划**，在本地用 Python 脚本模拟一次
live-like 数据拉取（用 CoinGecko/CoinCap 免费 API），验证：

1. 数据字段是否完整覆盖 required_fields
2. 响应延迟是否在可接受范围（< 5s）
3. 免费 API 的 rate limit 是否影响批量拉取
4. 数据格式是否与现有 preview card 结构兼容

⚠️ **v112Q 只做计划，不执行 live 拉取。** 当前阶段仍为 dry-run。

---

## 6. 为什么现在仍不能真实发送

| 原因 | 说明 |
|------|------|
| 无 live 数据源 | 所有数据来自本地 fixture，未经真实 API 验证 |
| 无数据新鲜度保证 | 本地 fixture 时间戳是硬编码的模拟数据 |
| 无 API 可靠性测试 | 未测试 rate limit、超时、数据格式变化等边界情况 |
| 无生产状态写入 | 所有 state 都是 dry-run，未建立生产状态持久化 |
| 无人工审阅流程 | 当前没有审阅界面或人工确认流程 |
| 无回调/告警 | 发送失败、数据异常等情况无处理机制 |
| TG 发送未经 live source 端到端测试 | v112O 仅为本地预览包 |

---

## 7. 安全边界确认

| 约束 | 状态 |
|------|------|
| dry_run_only | true |
| live_ready | false |
| real_tg_sent | false |
| real_send_ready | false |
| production_state_write_ready | false |
| external_api_called | false |
| external_ai_called | false |
| daemon_started | false |
| files_deleted | false |
| debug_leak_count | 0 |
| secret_leak_count | 0 |
| manual_review_required_before_send | true |

---

## 8. 下一步建议

1. **v112Q — One-Shot Live-Like Candidate Plan**: 针对推荐 card type
   (`multi_asset_market_sync`) 制定详细的 one-shot 实验计划，
   只做计划文档，不执行 live 拉取。

2. v112R — 如果 v112Q 计划通过审查，可在隔离环境中执行首次
   one-shot live-like 实验（仅拉取，不发送）。

3. 低优先级 card type（news_event_market_impact）继续使用本地 fixture，
   待高优先级类型验证通过后再考虑接入。

---

*Generated by v1.12-p at 2026-06-05 04:13:18 UTC+8*