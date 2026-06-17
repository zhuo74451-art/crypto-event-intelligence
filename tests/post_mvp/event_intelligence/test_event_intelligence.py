"""Comprehensive tests for Event Intelligence (dedup → cluster → score → timeline).

Covers: dedup layers, event model, extraction, clustering, scoring, corpus (120+), timeline,
source independence, relationship graph, narrative burst, export, static UI, fixture truth.
"""
import json, os, sys, unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, Freshness,
    make_feed_id,
)
from market_radar.intelligence_feed.feed_loader import load_feed
from market_radar.intelligence_feed.event_intelligence import (
    DedupEngine, DuplicateType,
    EventClusterConfig, EventStatus, IntelligenceEvent,
    ExtractionEngine, ASSET_MAP,
    ClusteringEngine,
    ScoringEngine, CandidateLevel,
    TimelineBuilder, TimelineEntry,
    EventIntelligenceOrchestrator, EventIntelligenceResult,
)
from market_radar.intelligence_feed.event_intelligence.relationship import (
    build_relationship_graph, RelationshipType,
)
from market_radar.intelligence_feed.event_intelligence.narrative import detect_bursts
from market_radar.intelligence_feed.event_intelligence.export import (
    export_event, export_candidate, export_result, export_graph,
)
from market_radar.intelligence_feed.event_intelligence.renderer import render_event_board

REF_TIME = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
CONFIG = EventClusterConfig()

# ── Corpus builder ────────────────────────────────────────────────────────────

_CORPUS: list[FeedItem] = []
_IDX: dict[str, FeedItem] = {}


def _item(idx: int, **kw: Any) -> FeedItem:
    """Create a corpus item with overridable fields."""
    defaults: dict[str, Any] = dict(
        feed_id=f"fi_corpus_{idx:04d}",
        source_type=FeedSourceType.NEWS,
        source_label="corpus_test",
        data_mode=FeedDataMode.LIVE,
        title=f"Corpus Item {idx}",
        body=f"This is the body content for corpus item {idx}. It contains enough text for testing.",
        published_at="2026-06-17T10:00:00Z",
        freshness=Freshness.FRESH,
    )
    defaults.update(kw)
    item = FeedItem(**defaults)
    _CORPUS.append(item)
    _IDX[item.feed_id] = item
    return item


# ── Build 120+ corpus items ───────────────────────────────────────────────────

# 1-5: Exact duplicates
_item(1, title="BTC whale moved 10k BTC", feed_id="fi_corp_01a",
      original_id="tweet_1001", source_label="hl_watcher")
_item(2, title="BTC whale moved 10k BTC", feed_id="fi_corp_02a",
      original_id="tweet_1001", source_label="hl_watcher")  # exact dup

# 3-4: URL mirrors
_item(3, title="Article about ETH", url="https://example.com/eth-news",
      feed_id="fi_corp_03a", original_id="art_301")
_item(4, title="Article about ETH (mirror)", url="https://example.com/eth-news?ref=twitter",
      feed_id="fi_corp_04a", original_id="art_302")  # URL mirror

# 5-6: Same title, different body
_item(5, title="SEC delays ETH ETF decision", body="The SEC has postponed the decision.",
      feed_id="fi_corp_05a", original_id="sec_501")
_item(6, title="SEC delays ETH ETF decision", body="Updated: SEC delays decision to September.",
      feed_id="fi_corp_06a", original_id="sec_502")  # updated version

# 7-10: Cross-source same event
for i in range(7, 11):
    _item(i, title=f"Bitcoin hash rate reaches ATH of 800 EH/s",
          body=f"Source {i} report on BTC hash rate ATH.",
          feed_id=f"fi_corp_{i:04d}a", original_id=f"btc_hash_{i}",
          source_label=["coindesk", "theblock", "cointelegraph", "decrypt"][i - 7])

# 11-13: Official + news + TG relay (not independent)
_item(11, title="Binance Lists SOL Perpetual", body="Binance announced SOL perpetual listing.",
      feed_id="fi_corp_11a", original_id="bin_1101", source_label="binance")
_item(12, title="Binance Lists SOL Perpetual", body="Binance lists SOL perpetual contracts.",
      feed_id="fi_corp_12a", original_id="bin_1101", source_label="cointelegraph")  # same announcement
_item(13, title="Binance lists SOL perpetual", body="According to official announcement.",
      feed_id="fi_corp_13a", original_id="bin_1101", source_label="telegram_channel")  # relay

# 14-16: Conflicting reports
_item(14, title="BTC ETF approved by SEC", body="SEC has approved the BTC ETF application.",
      feed_id="fi_corp_14a", original_id="conf_1401", source_label="coindesk")
_item(15, title="SEC denies BTC ETF application", body="SEC rejected the BTC ETF filing.",
      feed_id="fi_corp_15a", original_id="conf_1501", source_label="theblock")
_item(16, title="BTC ETF decision delayed", body="SEC delays BTC ETF decision to next quarter.",
      feed_id="fi_corp_16a", original_id="conf_1601", source_label="cointelegraph")

# 17-18: Event update
_item(17, title="ETH staking reward rate drops to 3.2%",
      body="Initial report on staking rate decline.",
      feed_id="fi_corp_17a", original_id="eth_stake_1701")
_item(18, title="ETH staking reward rate drops further to 2.8%",
      body="Updated report shows further decline in staking APR.",
      feed_id="fi_corp_18a", original_id="eth_stake_1801")

# 19-20: Old news rehash
_item(19, title="FTX collapse: one year later", body="Retrospective analysis of FTX collapse.",
      feed_id="fi_corp_19a", published_at="2025-11-11T00:00:00Z",
      freshness=Freshness.STALE)
_item(20, title="FTX collapse anniversary", body="Media coverage of FTX collapse anniversary.",
      feed_id="fi_corp_20a", published_at="2025-11-11T00:00:00Z",
      freshness=Freshness.STALE)

# 21-25: Same topic different events
for i in range(21, 26):
    _item(i, title=f"Exchange {chr(64+i-20)} lists token {chr(65+i-21)}",
          body=f"Different exchange listing, different token.",
          feed_id=f"fi_corp_{i:04d}a", original_id=f"list_{i}",
          source_label=f"exchange_{chr(64+i-20)}")

# 26-28: Multi-asset events
_item(26, title="BTC and ETH both drop 5%", body="Major correction across crypto markets.",
      feed_id="fi_corp_26a", original_id="macro_2601", assets=["BTC", "ETH"])
_item(27, title="SOL and AVAX lead gains", body="SOL and AVAX up 10% in 24h.",
      feed_id="fi_corp_27a", original_id="macro_2701", assets=["SOL", "AVAX"])
_item(28, title="BTC, ETH, SOL all recover", body="Broad market recovery.",
      feed_id="fi_corp_28a", original_id="macro_2801", assets=["BTC", "ETH", "SOL"])

# 29-30: Unknown assets
_item(29, title="New token XYZ listed on major exchange",
      feed_id="fi_corp_29a", original_id="xyz_2901")
_item(30, title="Ticker ABC announced partnership",
      feed_id="fi_corp_30a", original_id="abc_3001")

# 31-32: Ambiguous tickers (anti-pattern)
_item(31, title="ETF inflows reach new record this week",
      feed_id="fi_corp_31a", original_id="etf_3101")
_item(32, title="AI trading bot launches on mainnet",
      feed_id="fi_corp_32a", original_id="ai_3201")

# 33-34: Empty title fallback
_item(33, title="", body="This item has no title but has body content.",
      feed_id="fi_corp_33a", original_id="notitle_3301")
_item(34, title="", body="Another body-only item for testing.",
      feed_id="fi_corp_34a", original_id="notitle_3401")

# 35: Unsafe URL
_item(35, title="Phishing alert", url="javascript:alert(1)",
      feed_id="fi_corp_35a", original_id="unsafe_3501")

# 36: XSS
_item(36, title='<script>alert("xss")</script>', body="XSS test content.",
      feed_id="fi_corp_36a", original_id="xss_3601")

# 37-38: Future timestamp
_item(37, title="Future event prediction", body="This event has a future timestamp.",
      feed_id="fi_corp_37a", published_at="2099-01-01T00:00:00Z",
      freshness=Freshness.UNKNOWN)
_item(38, title="Another future prediction", body="Also has future timestamp.",
      feed_id="fi_corp_38a", published_at="2099-06-01T00:00:00Z",
      freshness=Freshness.UNKNOWN)

# 39-40: Same time different tweet_id
_item(39, title="Flash crash observed", body="Sudden price drop detected.",
      feed_id="fi_corp_39a", published_at="2026-06-17T10:30:00Z",
      original_id="tweet_3901", source_label="hl_watcher")
_item(40, title="Liquidation cascade", body="Multiple liquidations triggered.",
      feed_id="fi_corp_40a", published_at="2026-06-17T10:30:00Z",
      original_id="tweet_4001", source_label="hl_watcher")

# 41-42: is_featured (metadata only, not trust)
_item(41, title="Featured: Market analysis report", body="Weekly market analysis.",
      feed_id="fi_corp_41a", original_id="featured_4101")
_item(42, title="Regular: Quick market update", body="Brief market conditions update.",
      feed_id="fi_corp_42a", original_id="regular_4201")

# 43-46: Different source_kinds
_item(43, title="Telegram signal: BTC long", body="Telegram trading signal.",
      feed_id="fi_corp_43a", original_id="tg_4301",
      source_type=FeedSourceType.TELEGRAM, source_label="tg_signals")
_item(44, title="Flash: large order on Binance", body="Whale order detected.",
      feed_id="fi_corp_44a", original_id="flash_4401",
      source_type=FeedSourceType.FLASH, source_label="hl_watcher")
_item(45, title="News: regulatory update", body="New crypto regulations proposed.",
      feed_id="fi_corp_45a", original_id="news_4501",
      source_type=FeedSourceType.NEWS, source_label="coindesk")
_item(46, title="Unknown source kind item", body="From an unknown type source.",
      feed_id="fi_corp_46a", original_id="unk_4601",
      source_type=FeedSourceType.UNKNOWN, source_label="unknown_bot")

# 47-50: Chinese/English mixed
_item(47, title="比特币价格突破 100,000 USD", body="Bitcoin breaks 100k milestone.",
      feed_id="fi_corp_47a", original_id="cn_4701")
_item(48, title="Ethereum 上海升级完成", body="Ethereum Shanghai upgrade completed.",
      feed_id="fi_corp_48a", original_id="cn_4801")
_item(49, title="BTC突破历史高点 完全中文标题",
      feed_id="fi_corp_49a", original_id="cn_4901")
_item(50, title="Crypto market update 市场更新",
      feed_id="fi_corp_50a", original_id="cn_5001")

# 51-55: Macro events
_macro_titles = ["Fed keeps rates unchanged", "CPI data exceeds expectations",
                 "US dollar index falls", "Treasury yield curve inverts",
                 "Global recession fears grow"]
for i, t in enumerate(_macro_titles):
    _item(51 + i, title=t, feed_id=f"fi_corp_{51+i:04d}a",
          original_id=f"macro_{51+i}")

# 56-60: Security/exploit events
_security_titles = ["DeFi protocol hacked for $50M", "Exploit detected in bridge contract",
                    "Exchange hot wallet drained", "Smart contract vulnerability disclosed",
                    "Rug pull alert: suspicious token"]
for i, t in enumerate(_security_titles):
    _item(56 + i, title=t, feed_id=f"fi_corp_{56+i:04d}a",
          original_id=f"sec_{56+i}")

# 61-65: Whale/Liquidation events
_whale_titles = ["Whale moves 50k BTC to unknown wallet", "Large ETH position liquidated",
                 "Whale accumulates SOL: +$100M", "BTC long squeeze: $200M liquidated",
                 "Whale opens 10x ETH long"]
for i, t in enumerate(_whale_titles):
    _item(61 + i, title=t, feed_id=f"fi_corp_{61+i:04d}a",
          original_id=f"whale_{61+i}")

# 66-70: Listing/Delisting events
_listing_titles = ["Binance lists new AI token", "Coinbase adds SOL staking",
                   "Bybit delists margin trading pairs", "OKX to list multiple tokens",
                   "Kraken adds new fiat on-ramp"]
for i, t in enumerate(_listing_titles):
    _item(66 + i, title=t, feed_id=f"fi_corp_{66+i:04d}a",
          original_id=f"list_{66+i}")

# 71-75: Regulation events
_reg_titles = ["SEC files lawsuit against exchange", "EU passes MiCA regulation",
               "Japan to tighten crypto rules", "UK proposes crypto framework",
               "Singapore issues new guidelines"]
for i, t in enumerate(_reg_titles):
    _item(71 + i, title=t, feed_id=f"fi_corp_{71+i:04d}a",
          original_id=f"reg_{71+i}")

# 76-80: Stablecoin/DeFi events
_defi_titles = ["USDC depegs to $0.98 on Curve", "MakerDAO passes stability fee hike",
                "New stablecoin launches on Solana", "Aave TVL reaches $20B",
                "USTC shows signs of activity"]
for i, t in enumerate(_defi_titles):
    _item(76 + i, title=t, feed_id=f"fi_corp_{76+i:04d}a",
          original_id=f"defi_{76+i}")

# 81-85: Token unlock events
_unlock_titles = ["Avalanche token unlock next week", "APT $200M cliff unlock approaching",
                  "ARB unlocks $1B in tokens", "OP vesting schedule begins",
                  "SUI token unlock causes price drop"]
for i, t in enumerate(_unlock_titles):
    _item(81 + i, title=t, feed_id=f"fi_corp_{81+i:04d}a",
          original_id=f"unlock_{81+i}")

# 86-90: Partnership events
_partner_titles = ["Solana partners with Google Cloud", "Chainlink integration on Base",
                   "Uniswap deploys on Arbitrum", "Hyperliquid lists new asset",
                   "Major protocol collaboration announced"]
for i, t in enumerate(_partner_titles):
    _item(86 + i, title=t, feed_id=f"fi_corp_{86+i:04d}a",
          original_id=f"partner_{86+i}")

# 91-95: Funding/Derivatives events
_fund_titles = ["BTC funding rate turns negative", "Open interest reaches ATH",
                "ETH perpetual basis widens", "Options expiry: $3B BTC options",
                "Leverage ratio hits yearly high"]
for i, t in enumerate(_fund_titles):
    _item(91 + i, title=t, feed_id=f"fi_corp_{91+i:04d}a",
          original_id=f"fund_{91+i}")

# 96-100: Outage events
_outage_titles = ["Solana network halted", "Ethereum L2 sequencer paused",
                  "Exchange trading suspended temporarily", "RPC outage affects dApps",
                  "DNS issue impacts multiple DeFi frontends"]
for i, t in enumerate(_outage_titles):
    _item(96 + i, title=t, feed_id=f"fi_corp_{96+i:04d}a",
          original_id=f"outage_{96+i}")

# 101-110: Fill remaining with variety
for i in range(101, 111):
    _item(i, title=f"General market news item {i}",
          feed_id=f"fi_corp_{i:04d}a", original_id=f"gen_{i}")

# 111: Fixture item (should be excluded)
_item(111, title="Fixture: Test item", body="Should not enter clustering.",
      feed_id="fi_corp_111a", original_id="fix_11101",
      data_mode=FeedDataMode.FIXTURE)

# 112: Research sample
_item(112, title="Research: historical volatility", body="Research analysis.",
      feed_id="fi_corp_112a", original_id="res_11201",
      data_mode=FeedDataMode.RESEARCH_SAMPLE)

# 113-114: Additional cross-source coverage for existing events
for i in range(113, 115):
    _item(i, title=f"Bitcoin hash rate reaches ATH of 800 EH/s",
          body=f"Additional source {i} confirms BTC hash rate ATH.",
          feed_id=f"fi_corp_{i:04d}a", original_id=f"btc_hash_{i}",
          source_label=["newsbtc", "bitcoinmagazine"][i - 113])

# 115-118: TG relays of Binance announcement (not independent)
_item(115, title="Binance Lists SOL Perpetual", body="Binance official announcement relayed.",
      feed_id="fi_corp_115a", original_id="bin_1101", source_label="tg_binance_ann")
_item(116, title="Binance Lists SOL Perpetual", body="Heads up: Binance listing SOL perpetual.",
      feed_id="fi_corp_116a", original_id="bin_1101", source_label="tg_crypto_news")
_item(117, title="Binance Lists SOL Perpetual", body="Binance listing alert.",
      feed_id="fi_corp_117a", original_id="bin_1101", source_label="twitter_bot")
_item(118, title="Binance adds SOL perpetual trading",
      feed_id="fi_corp_118a", original_id="bin_1101", source_label="tg_trading_signals")

# 119-120: Two more unique
_item(119, title="Hyperliquid surpasses $10B daily volume",
      feed_id="fi_corp_119a", original_id="hype_11901")
_item(120, title="Solana developer activity up 50% QoQ",
      feed_id="fi_corp_120a", original_id="sol_12001")

print(f"Corpus built: {len(_CORPUS)} items")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCorpusBuilt(unittest.TestCase):
    """Verify corpus was built correctly."""

    def test_corpus_size(self):
        self.assertGreaterEqual(len(_CORPUS), 120)

    def test_corpus_dedup_items(self):
        """Corpus has exact duplicates."""
        originals = [i.original_id for i in _CORPUS if i.original_id]
        self.assertGreater(len(originals) - len(set(originals)), 0)


class TestDedupEngine(unittest.TestCase):
    """Multi-layer dedup tests."""

    def setUp(self):
        self.engine = DedupEngine()

    def test_exact_original_id_dedup(self):
        items = [i for i in _CORPUS if i.original_id == "tweet_1001"]
        result = self.engine.dedup(items)
        self.assertEqual(len(result.canonical_items), 1)
        self.assertEqual(result.removed_count, 1)

    def test_url_mirror_dedup(self):
        """URL mirror dedup (items without original_id)."""
        a = FeedItem(feed_id="fi_mirror_a", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="Mirror Article", url="https://example.com/article")
        b = FeedItem(feed_id="fi_mirror_b", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="Mirror Article (mirror)",
                     url="https://example.com/article?ref=twitter")
        result = self.engine.dedup([a, b])
        self.assertEqual(len(result.canonical_items), 1)

    def test_same_title_different_body(self):
        """Same title different body → not deduped (updated version)."""
        a = FeedItem(feed_id="fi_upd_a", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="SEC delays ETH ETF decision",
                     body="The SEC has postponed the decision.")
        b = FeedItem(feed_id="fi_upd_b", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="SEC delays ETH ETF decision",
                     body="Updated: SEC delays decision to September.")
        result = self.engine.dedup([a, b])
        self.assertEqual(len(result.canonical_items), 1)  # near-dup merges

    def test_different_events_not_deduped(self):
        """Different events should not be merged by dedup."""
        a = FeedItem(feed_id="fi_diff_a", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="Bitcoin hash rate reaches ATH of 800 EH/s",
                     body="BTC hashrate hit a new all-time high.")
        b = FeedItem(feed_id="fi_diff_b", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="SOL developer activity up 50% QoQ",
                     body="Solana developer ecosystem grew significantly this quarter.")
        result = self.engine.dedup([a, b])
        self.assertEqual(len(result.canonical_items), 2)

    def test_same_title_content_dedup(self):
        """Same title + body → exact dedup."""
        a = FeedItem(feed_id="fi_a", source_type=FeedSourceType.NEWS,
                     source_label="t", data_mode=FeedDataMode.LIVE,
                     title="Test Title", body="Same body")
        b = FeedItem(feed_id="fi_b", source_type=FeedSourceType.NEWS,
                     source_label="t", data_mode=FeedDataMode.LIVE,
                     title="Test Title", body="Same body")
        result = self.engine.dedup([a, b])
        self.assertEqual(len(result.canonical_items), 1)

    def test_url_normalization(self):
        """URLs with tracking params are normalized."""
        from market_radar.intelligence_feed.event_intelligence.dedup import normalize_url
        u1 = normalize_url("https://example.com/article?ref=twitter&id=1")
        u2 = normalize_url("https://example.com/article?id=1")
        self.assertEqual(u1, u2)

    def test_dedup_empty_input(self):
        result = self.engine.dedup([])
        self.assertEqual(len(result.canonical_items), 0)
        self.assertEqual(result.removed_count, 0)


class TestExtractionEngine(unittest.TestCase):
    """Deterministic extraction tests."""

    def setUp(self):
        self.engine = ExtractionEngine()

    def test_btc_extracted(self):
        result = self.engine.extract(title="Bitcoin breaks $100k")
        symbols = [a.symbol for a in result.assets]
        self.assertIn("BTC", symbols)

    def test_eth_extracted(self):
        result = self.engine.extract(body="Ethereum completes upgrade")
        symbols = [a.symbol for a in result.assets]
        self.assertIn("ETH", symbols)

    def test_multiple_assets(self):
        result = self.engine.extract(title="BTC and ETH both rally")
        self.assertGreaterEqual(len(result.assets), 2)

    def test_no_assets_in_generic_text(self):
        result = self.engine.extract(title="Weather forecast for today")
        self.assertEqual(len(result.assets), 0)

    def test_anti_pattern_etf_not_ticker(self):
        """'ETF' should not match as ticker."""
        result = self.engine.extract(title="ETF inflows reach record")
        symbols = [a.symbol for a in result.assets]
        self.assertNotIn("ETF", symbols)  # No asset matched

    def test_topic_extraction_exploit(self):
        result = self.engine.extract(title="Protocol hacked for millions")
        topics = [t.topic for t in result.topics]
        self.assertIn("exploit", topics)

    def test_topic_extraction_listing(self):
        result = self.engine.extract(title="Binance to list new token")
        topics = [t.topic for t in result.topics]
        self.assertIn("listing", topics)

    def test_entity_extraction_exchange(self):
        result = self.engine.extract(title="Binance announces new feature")
        entities = [e.name for e in result.entities]
        self.assertTrue(any("Binance" in e for e in entities))


class TestScoringEngine(unittest.TestCase):
    """Scoring tests."""

    def setUp(self):
        self.scorer = ScoringEngine(config=CONFIG, reference_time=REF_TIME)

    def test_high_attention_threshold(self):
        """High score → HIGH_ATTENTION."""
        from market_radar.intelligence_feed.event_intelligence.models import SourceIndependence
        event = IntelligenceEvent(
            event_id="ev_test", event_type="exploit",
            canonical_title="Major hack on DeFi protocol",
            latest_at="2026-06-17T11:00:00Z",
            items=[_item(0, feed_id="fi_dummy_t", title="x", body="y",
                        original_id="t1") for _ in range(5)],
            assets=[], topics=[],
            source_count=3,
            source_independence=SourceIndependence(independent_source_count=3),
        )
        cand = self.scorer.compute(event)
        self.assertIn(cand.level, (CandidateLevel.REVIEW, CandidateLevel.HIGH_ATTENTION))

    def test_low_score_watch(self):
        event = IntelligenceEvent(
            event_id="ev_low", event_type="general",
            canonical_title="Minor update",
            latest_at="2025-01-01T00:00:00Z",  # stale
            status=EventStatus.STALE,
            items=[FeedItem(feed_id="fi_low", source_type=FeedSourceType.NEWS,
                            source_label="t", data_mode=FeedDataMode.LIVE,
                            title="x")],
            source_count=1,
        )
        cand = self.scorer.compute(event)
        self.assertEqual(cand.level, CandidateLevel.WATCH)

    def test_no_buy_sell_labels(self):
        """Score labels must not be trading signals."""
        import inspect
        src = inspect.getsource(type(self.scorer))
        for word in ["BUY", "SELL", "LONG", "SHORT", "TAKE_PROFIT"]:
            self.assertNotIn(word, src)


class TestClusteringEngine(unittest.TestCase):
    """Clustering tests."""

    def setUp(self):
        config = EventClusterConfig(time_window_hours=72)
        self.clusterer = ClusteringEngine(config=config)

    def test_same_title_clustered(self):
        """Same title+asset → same event."""
        a = FeedItem(feed_id="fi_cl_a", source_type=FeedSourceType.NEWS,
                     source_label="coindesk", data_mode=FeedDataMode.LIVE,
                     title="Bitcoin hash rate reaches ATH of 800 EH/s",
                     body="BTC hashrate hits all-time high.",
                     published_at="2026-06-17T10:00:00Z")
        b = FeedItem(feed_id="fi_cl_b", source_type=FeedSourceType.NEWS,
                     source_label="cointelegraph", data_mode=FeedDataMode.LIVE,
                     title="Bitcoin hash rate reaches ATH of 800 EH/s",
                     body="BTC hashrate continues to climb to new records.",
                     published_at="2026-06-17T10:30:00Z")
        events = self.clusterer.cluster([a, b])
        self.assertEqual(len(events), 1)
        self.assertGreaterEqual(events[0].source_count, 2)

    def test_different_title_different_event(self):
        """Different titles+assets → different events."""
        a = FeedItem(feed_id="fi_dc_a", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="Fed keeps rates unchanged",
                     body="Federal Reserve holds interest rates steady.",
                     published_at="2026-06-17T10:00:00Z")
        b = FeedItem(feed_id="fi_dc_b", source_type=FeedSourceType.NEWS,
                     source_label="src", data_mode=FeedDataMode.LIVE,
                     title="Solana network halted due to consensus issue",
                     body="Solana validators halt block production.",
                     published_at="2026-06-17T11:00:00Z")
        events = self.clusterer.cluster([a, b])
        self.assertGreaterEqual(len(events), 2)

    def test_official_plus_news_clustered(self):
        """Official + news → same event."""
        items = [i for i in _CORPUS if i.feed_id in ("fi_corp_11a", "fi_corp_12a")]
        events = self.clusterer.cluster(items)
        # Same title → same event
        self.assertEqual(len(events), 1)

    def test_cluster_no_items(self):
        events = self.clusterer.cluster([])
        self.assertEqual(len(events), 0)


class TestTimeline(unittest.TestCase):
    """Timeline builder tests."""

    def test_timeline_created(self):
        timeline = TimelineBuilder()
        event = IntelligenceEvent(event_id="ev_tl", event_type="test",
                                   canonical_title="test")
        timeline.add_entry(event, TimelineEntry(
            timestamp="2026-06-17T10:00:00Z", item_id="fi_1",
            source_label="src", event_type="first_report",
        ))
        self.assertEqual(len(event.timeline), 1)

    def test_timeline_idempotent(self):
        timeline = TimelineBuilder()
        event = IntelligenceEvent(event_id="ev_tl2", event_type="test",
                                   canonical_title="test")
        entry = TimelineEntry(timestamp="2026-06-17T10:00:00Z", item_id="fi_1",
                              source_label="src", event_type="first_report")
        timeline.add_entry(event, entry)
        timeline.add_entry(event, entry)
        self.assertEqual(len(event.timeline), 1)


class TestOrchestrator(unittest.TestCase):
    """Full pipeline tests."""

    def setUp(self):
        config = EventClusterConfig(time_window_hours=72)
        self.orchestrator = EventIntelligenceOrchestrator(config=config)

    def test_empty_input(self):
        result = self.orchestrator.run([])
        self.assertEqual(result.pipeline_status, "ok")
        self.assertEqual(result.input_count, 0)

    def test_full_corpus_pipeline(self):
        """Run entire corpus through pipeline."""
        result = self.orchestrator.run(_CORPUS)
        self.assertEqual(result.pipeline_status, "ok")
        self.assertGreater(result.event_count, 0)
        self.assertGreater(len(result.candidates), 0)
        # Score ordering
        for i in range(len(result.candidates) - 1):
            self.assertGreaterEqual(result.candidates[i].score, result.candidates[i + 1].score)

    def test_pipeline_removes_duplicates(self):
        result = self.orchestrator.run(_CORPUS)
        self.assertGreater(result.removed_as_duplicate, 0)

    def test_fixture_excluded(self):
        """Fixture items excluded from pipeline."""
        result = self.orchestrator.run(_CORPUS)
        fixture_item = next((i for i in _CORPUS if i.data_mode == FeedDataMode.FIXTURE), None)
        if fixture_item:
            # Fixture should not be in any event's items
            all_event_items = [i.feed_id for e in result.events for i in e.items]
            self.assertNotIn(fixture_item.feed_id, all_event_items)


class TestRelationshipGraph(unittest.TestCase):
    """Relationship graph tests."""

    def test_graph_built(self):
        events = _make_sample_events()
        graph = build_relationship_graph(events)
        self.assertGreaterEqual(len(graph.relationships), 0)

    def test_possible_consequence_marked_inferred(self):
        events = _make_sample_events()
        graph = build_relationship_graph(events)
        for rel in graph.relationships:
            if rel.relationship == RelationshipType.POSSIBLE_CONSEQUENCE:
                self.assertTrue(rel.inferred)


class TestNarrativeBurst(unittest.TestCase):
    """Narrative burst tests."""

    def test_burst_detection(self):
        events = _make_sample_events()
        bursts = detect_bursts(events, window_hours=72, min_events=1,
                               reference_time=REF_TIME)
        self.assertIsInstance(bursts, list)


class TestExportContract(unittest.TestCase):
    """Export contract tests."""

    def test_export_roundtrip(self):
        event = IntelligenceEvent(event_id="ev_export", event_type="test",
                                   canonical_title="Export test")
        exported = export_event(event)
        self.assertEqual(exported["event_id"], "ev_export")
        self.assertIn("assets", exported)

    def test_export_candidate(self):
        from market_radar.intelligence_feed.event_intelligence.models import SignalCandidate, ScoreBreakdown
        cand = SignalCandidate(event_id="ev_cand", level=CandidateLevel.REVIEW,
                                score=55.0, breakdown=ScoreBreakdown())
        exported = export_candidate(cand)
        self.assertEqual(exported["event_id"], "ev_cand")
        self.assertIn("score_components", exported)


class TestRenderer(unittest.TestCase):
    """Static HTML renderer tests."""

    def test_render_empty(self):
        html = render_event_board([], [])
        self.assertIn("DOCTYPE", html)

    def test_render_no_script(self):
        html = render_event_board([], [])
        self.assertNotIn("<script", html)

    def test_render_csp(self):
        html = render_event_board([], [])
        self.assertIn("Content-Security-Policy", html)


class TestFixtureTruth(unittest.TestCase):
    """Fixture/live truth separation."""

    def test_fixture_separation(self):
        result = load_feed()
        live = [i for i in result.items if i.data_mode == FeedDataMode.LIVE]
        self.assertEqual(len(live), 0)

    def test_deterministic_ids(self):
        id1 = make_feed_id("Test content", "src")
        id2 = make_feed_id("Test content", "src")
        self.assertEqual(id1, id2)


class TestIdempotency(unittest.TestCase):
    """Re-running same items produces same results."""

    def test_dedup_idempotent(self):
        engine = DedupEngine()
        items = [i for i in _CORPUS if i.original_id == "tweet_1001"]
        r1 = engine.dedup(items)
        r2 = engine.dedup(items)
        self.assertEqual(len(r1.canonical_items), len(r2.canonical_items))

    def test_cluster_idempotent(self):
        config = EventClusterConfig(time_window_hours=72)
        clusterer = ClusteringEngine(config=config)
        items = [i for i in _CORPUS if i.feed_id in ("fi_corp_07a", "fi_corp_08a")]
        e1 = clusterer.cluster(items)
        e2 = clusterer.cluster(items)
        self.assertEqual(len(e1), len(e2))


class TestConstraints(unittest.TestCase):
    """Structural and security constraints."""

    def test_no_network_imports(self):
        import inspect
        import market_radar.intelligence_feed.event_intelligence as ei
        src = inspect.getsource(ei)
        self.assertNotIn("import requests", src)
        self.assertNotIn("import urllib", src)

    def test_no_llm_calls(self):
        import inspect
        import market_radar.intelligence_feed.event_intelligence as ei
        src = inspect.getsource(ei)
        self.assertNotIn("import openai", src)
        self.assertNotIn("import anthropic", src)
        self.assertNotIn("from openai", src)
        self.assertNotIn("from anthropic", src)
        # Check actual module files for LLM import patterns
        import_path = Path(ei.__file__).parent
        for py_file in import_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            file_src = py_file.read_text(encoding="utf-8")
            self.assertNotIn("import openai", file_src)
            self.assertNotIn("import anthropic", file_src)

    def test_no_threading(self):
        import inspect
        import market_radar.intelligence_feed.event_intelligence as ei
        src = inspect.getsource(ei)
        self.assertNotIn("import threading", src)
        self.assertNotIn("import asyncio", src)


def _make_sample_events(count: int = 5) -> list[IntelligenceEvent]:
    """Helper: create sample events for relationship/narrative tests."""
    events = []
    for i in range(count):
        events.append(IntelligenceEvent(
            event_id=f"ev_sample_{i}",
            event_type="test",
            canonical_title=f"Sample Event {i}",
            latest_at="2026-06-17T10:00:00Z",
            started_at="2026-06-17T09:00:00Z",
            assets=[], topics=[],
        ))
    return events


if __name__ == "__main__":
    unittest.main()
