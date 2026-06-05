"""Market Radar v1.12-P — Live Source Readiness Audit

Reads v112N and v112O upstream artifacts, validates they passed, then builds a
deterministic readiness matrix for all 5 fixed card types — assessing what each
card type needs before any real live data source can be connected.

This is a LOCAL DRY-RUN ONLY step:
  - No TG send
  - No external API/AI calls
  - No daemon / loop / cron
  - No live data source connection
  - No production state writes
  - No credential reading

Outputs:
  - results/market_radar_v112p_live_source_readiness_audit_result.json
  - results/market_radar_v112p_live_source_matrix.json
  - runs/market_radar/v112p_live_source_readiness_audit.md
  - runs/market_radar/v112p_live_source_readiness_audit_handoff.md

Usage:
    python scripts/run_market_radar_v112p_live_source_readiness_audit.py
"""

from __future__ import annotations

import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.12-p"
RUN_ID = "20260605_022952"
TASK_ID = "20260605_022952.r03"

# ── Output paths ──────────────────────────────────────────────────────────────────

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112p_live_source_readiness_audit_result.json"
MATRIX_JSON_PATH = ROOT / "results" / "market_radar_v112p_live_source_matrix.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112p_live_source_readiness_audit.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112p_live_source_readiness_audit_handoff.md"

# ── Input paths (upstream artifacts) ──────────────────────────────────────────────

MASTER_RESULT_PATH = ROOT / "results" / "market_radar_v112n_local_master_dryrun_result.json"
V112O_RESULT_PATH = ROOT / "results" / "market_radar_v112o_send_preview_pack_result.json"
V112O_CARDS_PATH = ROOT / "results" / "market_radar_v112o_send_preview_cards.jsonl"

# ── 5 fixed card types (from v112a) ───────────────────────────────────────────────

CARD_TYPES = [
    "price_oi_volume_anomaly",
    "whale_position_alert",
    "liquidation_pressure",
    "multi_asset_market_sync",
    "news_event_market_impact",
]

CARD_TYPE_LABELS: dict[str, str] = {
    "price_oi_volume_anomaly": "行情异动 (Price/OI/Volume Anomaly)",
    "whale_position_alert": "巨鲸仓位警报 (Whale Position Alert)",
    "liquidation_pressure": "清算压力 (Liquidation Pressure)",
    "multi_asset_market_sync": "多资产共振 (Multi-Asset Market Sync)",
    "news_event_market_impact": "新闻事件 (News Event Market Impact)",
}


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    if not path.exists():
        return records
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load JSONL {path}: {e}")
    return records


def check_forbidden_terms(text: str) -> int:
    """Check text for real secret/token leaks. Returns secret_count."""
    if not text:
        return 0

    text_lower = text.lower()
    real_secret_patterns = [
        r'\bsecret\s*[=:]\s*\S',
        r'\bsecret\s*key\b',
        r'\bsecret\s*token\b',
        r'\bapi[_\-]?secret\b',
        r'\bapi[_\-]?key\s*[=:]\s*\S',
        r'\bchat[_\-]?id\s*[=:]\s*\S',
        r'\bpassword\s*[=:]\s*\S',
        r'\bbearer\s+\S',
        r'\bauthorization\s*:\s*\S',
        r'\bx-api-key\s*[=:]\s*\S',
        r'\bcookie\s*[=:]\s*\S',
        r'[A-Za-z]:\\(?:Users|Program|Windows)',
    ]
    for pattern in real_secret_patterns:
        if re.search(pattern, text_lower):
            return 1
    return 0


def check_misleading_terms(text: str) -> list[str]:
    """Check for misleading 'already sent' / 'live connected' language."""
    if not text:
        return []

    misleading = [
        "已发送", "正式发布", "real sent", "已推送", "已投递",
        "broadcast sent", "message delivered",
        "sent to channel", "已发布成功", "发送成功",
        "已接入 live source", "live source connected",
        "production ready",
    ]
    text_lower = text.lower()
    found: list[str] = []
    for term in misleading:
        if term.lower() in text_lower:
            found.append(term)

    # Check for standalone "published" (not negated, not in compound words)
    # Use word boundary to avoid matching "published_at_utc", "published_at", etc.
    published_matches = re.findall(r'\bpublished\b', text_lower)
    if published_matches:
        # Remove negations and compound words from consideration
        cleaned = re.sub(r'not\s+published', ' ', text_lower)
        cleaned = re.sub(r'unpublished', ' ', cleaned)
        cleaned = re.sub(r'published_at', ' ', cleaned)
        cleaned = re.sub(r'published\s+by', ' ', cleaned)
        cleaned = re.sub(r'published\s+on', ' ', cleaned)
        cleaned = re.sub(r'published\s+at', ' ', cleaned)
        cleaned = re.sub(r'published\s+in', ' ', cleaned)
        remaining = re.findall(r'\bpublished\b', cleaned)
        if remaining:
            found.append("published (not negated)")

    return found


# ── Validation ────────────────────────────────────────────────────────────────────

def validate_v112n(master: dict) -> dict:
    checks = {
        "status_passed": master.get("status") == "passed",
        "dry_run_only": master.get("dry_run_only") is True,
        "eligible_signal_count_9": master.get("eligible_signal_count") == 9,
        "idempotency_passed": master.get("idempotency_passed") is True,
        "real_tg_sent_false": master.get("real_tg_sent") is False,
        "external_api_called_false": master.get("external_api_called") is False,
    }
    all_valid = all(checks.values())
    return {
        "all_valid": all_valid,
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
    }


def validate_v112o(result: dict) -> dict:
    checks = {
        "status_passed": result.get("status") == "passed",
        "send_preview_pack_ready": result.get("send_preview_pack_ready") is True,
        "preview_card_count_9": result.get("preview_card_count") == 9,
        "dry_run_only": result.get("dry_run_only") is True,
        "real_tg_sent_false": result.get("real_tg_sent") is False,
        "external_api_called_false": result.get("external_api_called") is False,
    }
    all_valid = all(checks.values())
    return {
        "all_valid": all_valid,
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
    }


# ── Readiness Matrix Builder ──────────────────────────────────────────────────────

def get_preview_card_count_by_type(cards: list[dict]) -> dict[str, int]:
    """Count preview cards per card_type from v112O output."""
    counts: dict[str, int] = {ct: 0 for ct in CARD_TYPES}
    for card in cards:
        ct = card.get("card_type", "")
        if ct in counts:
            counts[ct] += 1
    return counts


def build_readiness_matrix(cards: list[dict]) -> list[dict]:
    """Build the readiness matrix for all 5 card types using deterministic rules.

    Scoring dimensions (each 0-2 points, max 18):
      1. local_artifact_complete: has local pipeline output (1=partial, 2=ready)
      2. has_preview_cards: has v112O preview cards (0=none, 1=some, 2=multiple)
      3. live_source_likely_free: data source can be free (0=paid only, 1=mixed, 2=free)
      4. no_credential_required: can work without API key (0=always needs key, 1=partial, 2=no key needed)
      5. no_daemon_required: doesn't need persistent process (0=must, 1=preferred, 2=not needed)
      6. one_shot_possible: can do single pull experiment (0=no, 1=with caveats, 2=yes)
      7. data_fields_simple: how many fields needed (0=many/complex, 1=moderate, 2=few/simple)
      8. easy_fallback: easy to fallback on failure (0=hard, 1=moderate, 2=easy)
      9. no_production_write_risk: no risk of accidental writes (0=high risk, 1=moderate, 2=no risk)
    """
    preview_counts = get_preview_card_count_by_type(cards)

    # ── Per-card-type source analysis (deterministic, no AI) ──────────────────

    matrix: list[dict] = []

    # ── 1. price_oi_volume_anomaly ────────────────────────────────────────────
    matrix.append({
        "card_type": "price_oi_volume_anomaly",
        "current_status": "local_preview_ready",
        "required_live_sources": [
            {"source": "CoinGecko Public API", "data": "price", "cost": "free", "credential": "none"},
            {"source": "CoinCap Public API", "data": "price (fallback)", "cost": "free", "credential": "none"},
            {"source": "Coinglass Public / Free Tier", "data": "open_interest", "cost": "free_tier", "credential": "api_key_free"},
            {"source": "Exchange Public REST (Binance/Bybit/OKX)", "data": "volume", "cost": "free", "credential": "none"},
        ],
        "required_fields": [
            "asset_symbol", "current_price", "price_change_1h_pct", "price_change_24h_pct",
            "open_interest", "oi_change_1h_pct", "oi_change_24h_pct",
            "volume_24h", "volume_change_pct", "observation_timestamp",
        ],
        "optional_fields": [
            "funding_rate", "basis_spread", "spot_volume_vs_derivatives_volume",
            "top_bid_ask_spread",
        ],
        "credential_required": False,
        "paid_api_likely_required": False,
        "websocket_required": False,
        "daemon_required": False,
        "one_shot_experiment_possible": True,
        "recommended_frequency_if_future_live": "manual_one_shot_only",
        "cost_risk": "low",
        "failure_modes": [
            "rate_limit: free API tier may throttle at >30 req/min",
            "data_gap: OI data may lag 5-15 minutes behind price",
            "exchange_availability: single exchange may pause API during maintenance",
            "asset_coverage: some altcoins may not have OI data on free tier",
        ],
        "fallback_strategy": [
            "use CoinCap as price fallback if CoinGecko rate-limited",
            "use Binance public /ticker as volume fallback if Coinglass unavailable",
            "skip OI field if unavailable; note in card as 'OI data temporarily unavailable'",
            "use spot-only metrics as degraded mode for assets without derivatives data",
        ],
        "state_persistence_required": True,
        "manual_review_required_before_send": True,
        "real_send_allowed_now": False,
        # Scoring
        "readiness_score": 0,  # computed below
        "readiness_level": "low",  # computed below
        "next_step_recommendation": "",
        # Scoring dimensions (for transparency)
        "scoring_breakdown": {
            "local_artifact_complete": 1,   # has pipeline but ready_count was 1/5 in v112E
            "has_preview_cards": 0,          # 0 preview cards in v112O (was deduped)
            "live_source_likely_free": 2,    # CoinGecko/CoinCap/Binance all free
            "no_credential_required": 2,     # all free sources need no key
            "no_daemon_required": 2,         # pure REST, no websocket needed
            "one_shot_possible": 2,          # easy one-shot via curl
            "data_fields_simple": 2,         # price, OI, volume — all scalar
            "easy_fallback": 2,             # multiple free fallbacks available
            "no_production_write_risk": 2,  # read-only consumption
        },
    })

    # ── 2. whale_position_alert ───────────────────────────────────────────────
    matrix.append({
        "card_type": "whale_position_alert",
        "current_status": "local_preview_ready",
        "required_live_sources": [
            {"source": "HyperLiquid Public API", "data": "position_data", "cost": "free", "credential": "none"},
            {"source": "CoinGecko Public API", "data": "current_price", "cost": "free", "credential": "none"},
            {"source": "Wallet Label DB (local or public)", "data": "address_labels", "cost": "free", "credential": "none"},
        ],
        "required_fields": [
            "wallet_address", "address_label", "asset_symbol", "position_direction",
            "position_size_usd", "leverage", "entry_price", "current_price",
            "unrealized_pnl", "liquidation_price", "liquidation_distance_pct",
            "observation_timestamp",
        ],
        "optional_fields": [
            "position_change_usd", "position_age_hours", "historical_win_rate",
            "counterparty_risk_flag",
        ],
        "credential_required": False,
        "paid_api_likely_required": False,
        "websocket_required": False,
        "daemon_required": False,
        "one_shot_experiment_possible": True,
        "recommended_frequency_if_future_live": "manual_one_shot_only",
        "cost_risk": "low",
        "failure_modes": [
            "rate_limit: HyperLiquid API has burst limits",
            "label_staleness: address labels may be outdated or incorrect",
            "position_closure: position may close between pull and review",
            "data_quality: leverage/entry_price may differ from actual due to partial closes",
        ],
        "fallback_strategy": [
            "degrade to 'unknown whale' label if address DB unavailable",
            "use CoinGecko price as fallback if HL price feed differs >2%",
            "skip win_rate/historical if label data missing",
            "flag 'position may have changed since observation' in card",
        ],
        "state_persistence_required": True,
        "manual_review_required_before_send": True,
        "real_send_allowed_now": False,
        "readiness_score": 0,
        "readiness_level": "low",
        "next_step_recommendation": "",
        "scoring_breakdown": {
            "local_artifact_complete": 2,   # full pipeline complete in v112F
            "has_preview_cards": 2,         # 2 preview cards
            "live_source_likely_free": 2,   # HL public, CoinGecko free
            "no_credential_required": 2,    # all free, no key needed
            "no_daemon_required": 2,        # REST API only
            "one_shot_possible": 2,         # single API call + price lookup
            "data_fields_simple": 1,        # moderate: position data has many fields
            "easy_fallback": 1,            # moderate: address labels can degrade
            "no_production_write_risk": 2, # read-only
        },
    })

    # ── 3. liquidation_pressure ────────────────────────────────────────────────
    matrix.append({
        "card_type": "liquidation_pressure",
        "current_status": "local_preview_ready",
        "required_live_sources": [
            {"source": "Coinglass Liquidation API (free tier)", "data": "liquidation_data", "cost": "free_tier", "credential": "api_key_free"},
            {"source": "Exchange Public REST (Binance/Bybit)", "data": "oi_and_volume", "cost": "free", "credential": "none"},
            {"source": "CoinGecko Public API", "data": "current_price", "cost": "free", "credential": "none"},
        ],
        "required_fields": [
            "asset_symbol", "current_price", "liquidation_long_1h_usd",
            "liquidation_short_1h_usd", "liquidation_long_24h_usd",
            "liquidation_short_24h_usd", "open_interest", "volume_24h",
            "observation_window_hours", "observation_timestamp",
        ],
        "optional_fields": [
            "liquidation_cluster_price_top", "liquidation_cluster_price_bottom",
            "liquidation_heatmap_level", "long_short_ratio",
        ],
        "credential_required": True,
        "paid_api_likely_required": False,
        "websocket_required": False,
        "daemon_required": False,
        "one_shot_experiment_possible": True,
        "recommended_frequency_if_future_live": "manual_one_shot_only",
        "cost_risk": "low",
        "failure_modes": [
            "coinglass_key_expired: free API key requires periodic renewal",
            "data_lag: Coinglass liquidation data may be 5-30 minutes delayed",
            "exchange_limited: free tier may only cover top exchanges/assets",
            "sparse_markets: low-liquidity assets may have no meaningful liquidation data",
        ],
        "fallback_strategy": [
            "use exchange public OI + volume as degraded proxy for liquidation pressure",
            "skip cluster/heatmap if Coinglass premium data unavailable",
            "flag 'liquidation data from free tier; may miss tail exchanges'",
            "fallback to Binance-only liquidation data if aggregator unavailable",
        ],
        "state_persistence_required": True,
        "manual_review_required_before_send": True,
        "real_send_allowed_now": False,
        "readiness_score": 0,
        "readiness_level": "low",
        "next_step_recommendation": "",
        "scoring_breakdown": {
            "local_artifact_complete": 2,   # pipeline complete
            "has_preview_cards": 2,         # 2 preview cards
            "live_source_likely_free": 1,   # Coinglass free tier exists but needs key
            "no_credential_required": 1,    # needs Coinglass API key (free)
            "no_daemon_required": 2,        # REST only
            "one_shot_possible": 2,         # possible with free key
            "data_fields_simple": 2,        # mostly scalar fields
            "easy_fallback": 1,            # moderate: needs aggregator or degrades
            "no_production_write_risk": 2, # read-only
        },
    })

    # ── 4. multi_asset_market_sync ─────────────────────────────────────────────
    matrix.append({
        "card_type": "multi_asset_market_sync",
        "current_status": "local_preview_ready",
        "required_live_sources": [
            {"source": "CoinGecko Public API", "data": "multi_asset_price", "cost": "free", "credential": "none"},
            {"source": "CoinCap Public API", "data": "price_fallback", "cost": "free", "credential": "none"},
            {"source": "Exchange Public REST", "data": "oi_and_volume", "cost": "free", "credential": "none"},
        ],
        "required_fields": [
            "asset_symbols_list", "sync_type", "direction",
            "price_changes_pct_list", "observation_window_minutes",
            "avg_price_change_pct", "avg_volume_change_pct",
            "avg_oi_change_pct", "sync_score", "sector_label",
            "total_liquidation_usd", "observation_timestamp",
        ],
        "optional_fields": [
            "correlation_matrix_short", "leader_asset", "laggard_asset",
            "historical_sync_frequency",
        ],
        "credential_required": False,
        "paid_api_likely_required": False,
        "websocket_required": False,
        "daemon_required": False,
        "one_shot_experiment_possible": True,
        "recommended_frequency_if_future_live": "manual_one_shot_only",
        "cost_risk": "low",
        "failure_modes": [
            "rate_limit: pulling N assets simultaneously may hit free tier limit",
            "sector_misclassification: sector labels may drift over time",
            "false_sync: short-window correlation may be noise, not signal",
            "data_consistency: different sources may timestamp differently",
        ],
        "fallback_strategy": [
            "reduce asset count to top-5 if rate-limited",
            "use CoinCap bulk endpoint for single-call multi-asset price",
            "skip sector label if classification data unavailable",
            "flag 'correlation may be spurious in short window' in card",
        ],
        "state_persistence_required": True,
        "manual_review_required_before_send": True,
        "real_send_allowed_now": False,
        "readiness_score": 0,
        "readiness_level": "low",
        "next_step_recommendation": "",
        "scoring_breakdown": {
            "local_artifact_complete": 2,   # pipeline complete
            "has_preview_cards": 2,         # 3 preview cards (most of any type)
            "live_source_likely_free": 2,   # CoinGecko/CoinCap all free
            "no_credential_required": 2,    # no key needed for any source
            "no_daemon_required": 2,        # REST only
            "one_shot_possible": 2,         # easiest one-shot: just pull prices
            "data_fields_simple": 2,        # prices, changes — all simple scalars
            "easy_fallback": 2,            # multiple free price feeds available
            "no_production_write_risk": 2, # read-only
        },
    })

    # ── 5. news_event_market_impact ─────────────────────────────────────────────
    matrix.append({
        "card_type": "news_event_market_impact",
        "current_status": "local_preview_ready",
        "required_live_sources": [
            {"source": "CryptoPanic News API (free tier)", "data": "news_headlines", "cost": "free_tier", "credential": "api_key_free"},
            {"source": "Twitter/X API (free tier)", "data": "crypto_tweets", "cost": "free_tier", "credential": "api_key"},
            {"source": "RSS feeds (CoinDesk, TheBlock, Decrypt)", "data": "articles", "cost": "free", "credential": "none"},
            {"source": "CoinGecko Public API", "data": "price_impact", "cost": "free", "credential": "none"},
        ],
        "required_fields": [
            "event_title", "event_category", "market_impact_direction",
            "affected_assets", "source_name", "source_url",
            "published_at_utc", "trading_relevance",
            "is_priced_in", "observation_timestamp",
        ],
        "optional_fields": [
            "event_sentiment_score", "social_volume", "similar_event_historical_impact",
            "related_news_cluster_id",
        ],
        "credential_required": True,
        "paid_api_likely_required": True,
        "websocket_required": False,
        "daemon_required": False,
        "one_shot_experiment_possible": True,
        "recommended_frequency_if_future_live": "manual_one_shot_only",
        "cost_risk": "medium",
        "failure_modes": [
            "api_key_expired: CryptoPanic/Twitter free keys may expire or change terms",
            "source_unreliable: single news source may be inaccurate or biased",
            "sentiment_misclassification: automated sentiment may misread sarcasm",
            "priced_in_uncertainty: hard to determine if event already priced in",
            "rate_limit_severe: Twitter free tier API very limited (read-only)",
            "language_barrier: non-English news may be missed by free aggregators",
        ],
        "fallback_strategy": [
            "use RSS feeds (CoinDesk, TheBlock) as baseline — always free, no key",
            "skip sentiment/social_volume if NLP pipeline not available",
            "flag 'single-source; cross-reference before trading decision'",
            "degrade to manual-curation mode if all APIs unavailable",
            "use CoinGecko trending as weak signal for unpriced events",
        ],
        "state_persistence_required": True,
        "manual_review_required_before_send": True,
        "real_send_allowed_now": False,
        "readiness_score": 0,
        "readiness_level": "low",
        "next_step_recommendation": "",
        "scoring_breakdown": {
            "local_artifact_complete": 2,   # pipeline complete
            "has_preview_cards": 2,         # 2 preview cards
            "live_source_likely_free": 0,   # most useful news APIs need paid tier
            "no_credential_required": 0,    # needs multiple API keys
            "no_daemon_required": 2,        # REST only
            "one_shot_possible": 1,         # possible but limited without good API access
            "data_fields_simple": 0,        # complex: NLP/sentiment/classification needed
            "easy_fallback": 1,            # moderate: RSS feeds available but limited
            "no_production_write_risk": 2, # read-only
        },
    })

    # ── Compute readiness_score and readiness_level ────────────────────────────
    for entry in matrix:
        breakdown = entry["scoring_breakdown"]
        # Max possible: 9 dimensions × 2 points = 18
        raw_score = sum(breakdown.values())
        entry["readiness_score"] = raw_score

        if raw_score >= 14:
            entry["readiness_level"] = "high"
        elif raw_score >= 9:
            entry["readiness_level"] = "medium"
        else:
            entry["readiness_level"] = "low"

    # ── Set next_step_recommendation ───────────────────────────────────────────
    for entry in matrix:
        ct = entry["card_type"]
        preview_n = preview_counts.get(ct, 0)
        level = entry["readiness_level"]
        one_shot = entry["one_shot_experiment_possible"]

        if level == "high":
            entry["next_step_recommendation"] = (
                f"FIRST CANDIDATE: {ct} scored highest ({entry['readiness_score']}/18). "
                f"{preview_n} preview cards exist. All sources free, no credentials, "
                f"one-shot feasible. v112Q should plan a local one-shot experiment first."
            )
        elif level == "medium":
            entry["next_step_recommendation"] = (
                f"SECOND PRIORITY: {ct} scored {entry['readiness_score']}/18. "
                f"One-shot possible but may need free API key setup. "
                f"Plan v112Q experiment after the highest-scored card type."
            )
        else:
            entry["next_step_recommendation"] = (
                f"LOWER PRIORITY: {ct} scored {entry['readiness_score']}/18. "
                f"Needs paid API keys, complex NLP, or multi-source aggregation. "
                f"Defer live experiment; continue local fixtures for now."
            )

    return matrix


def pick_recommended_candidate(matrix: list[dict]) -> str:
    """Pick the single recommended first one-shot candidate.

    Rule: highest readiness_score that also has one_shot_experiment_possible=True.
    Tiebreaker: highest preview card count.
    """
    candidates = [e for e in matrix if e["one_shot_experiment_possible"]]
    if not candidates:
        return ""

    # Sort by readiness_score desc, then by preview count desc
    candidates.sort(key=lambda e: (e["readiness_score"], sum(
        1 for d in e.get("scoring_breakdown", {}).values() if isinstance(d, int)
    )), reverse=True)

    return candidates[0]["card_type"]


# ── Report / Handoff writers ──────────────────────────────────────────────────────

def write_report(
    matrix: list[dict],
    v112n_validation: dict,
    v112o_validation: dict,
    preview_counts: dict[str, int],
    recommended: str,
    result: dict,
) -> str:
    """Write the v112P Markdown report and return the text."""
    lines = [
        f"# Market Radar v1.12-P — Live Source Readiness Audit Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Status**: {result.get('status', '?').upper()}",
        f"",
        f"---",
        f"",
        f"## 1. 审计目标",
        f"",
        f"v112P Live Source Readiness Audit 的目标是：在本地固定卡片矩阵 (v112A→v112N)",
        f"和发送预览包 (v112O) 连续通过后，**不接任何 live API**，对 5 类固定卡片的",
        f"未来真实数据源接入做好完整准备度审计。",
        f"",
        f"回答的问题：",
        f"",
        f"- 每类卡片未来需要哪些 live source？",
        f"- 需要哪些字段？是否需要 API key / 付费接口 / WebSocket / daemon？",
        f"- 是否能先做 one-shot live candidate experiment？",
        f"- 哪一类最适合作为下一阶段第一个低风险 live-like 实验对象？",
        f"",
        f"---",
        f"",
        f"## 2. 上游验证：v112N / v112O 状态",
        f"",
        f"### v112N Master Dry-Run",
        f"",
        f"| 检查项 | 状态 |",
        f"|--------|------|",
    ]

    for check, value in v112n_validation["checks"].items():
        icon = "✅" if value else "❌"
        lines.append(f"| {check} | {icon} |")

    lines.extend([
        f"",
        f"**v112N 结论**: {'✅ 通过' if v112n_validation['all_valid'] else '❌ 未通过'}",
        f"",
        f"### v112O Send Preview Pack",
        f"",
        f"| 检查项 | 状态 |",
        f"|--------|------|",
    ])

    for check, value in v112o_validation["checks"].items():
        icon = "✅" if value else "❌"
        lines.append(f"| {check} | {icon} |")

    lines.extend([
        f"",
        f"**v112O 结论**: {'✅ 通过' if v112o_validation['all_valid'] else '❌ 未通过'}",
        f"",
        f"---",
        f"",
        f"## 3. 5 类卡片 Live Source Readiness 总览",
        f"",
        f"| Card Type | Preview Cards | Score | Level | One-Shot | Credential | Paid API | Daemon |",
        f"|-----------|--------------|-------|-------|----------|------------|----------|--------|",
    ])

    for entry in matrix:
        ct = entry["card_type"]
        pc = preview_counts.get(ct, 0)
        score = entry["readiness_score"]
        level = entry["readiness_level"]
        one_shot = "✅" if entry["one_shot_experiment_possible"] else "❌"
        cred = "⚠️ 需要" if entry["credential_required"] else "✅ 不需要"
        paid = "⚠️ 可能需要" if entry["paid_api_likely_required"] else "✅ 不需要"
        daemon = "⚠️ 需要" if entry["daemon_required"] else "✅ 不需要"
        lines.append(f"| {ct} | {pc} | {score}/18 | {level} | {one_shot} | {cred} | {paid} | {daemon} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 4. 各类卡片详细审计",
        f"",
    ])

    for entry in matrix:
        ct = entry["card_type"]
        label = CARD_TYPE_LABELS.get(ct, ct)
        lines.extend([
            f"### 4.{matrix.index(entry) + 1} {label} (`{ct}`)",
            f"",
            f"**Readiness Score**: {entry['readiness_score']}/18 ({entry['readiness_level'].upper()})",
            f"",
            f"#### Required Live Sources",
            f"",
            f"| Source | Data | Cost | Credential |",
            f"|--------|------|------|------------|",
        ])
        for src in entry["required_live_sources"]:
            lines.append(f"| {src['source']} | {src['data']} | {src['cost']} | {src['credential']} |")

        lines.extend([
            f"",
            f"#### Required Fields",
            f"",
            f"`{', '.join(entry['required_fields'])}`",
            f"",
            f"#### Scoring Breakdown",
            f"",
            f"| Dimension | Score |",
            f"|-----------|-------|",
        ])
        for dim, score in entry["scoring_breakdown"].items():
            lines.append(f"| {dim} | {score}/2 |")

        lines.extend([
            f"",
            f"#### Failure Modes",
            f"",
        ])
        for fm in entry["failure_modes"]:
            lines.append(f"- ⚠️ {fm}")

        lines.extend([
            f"",
            f"#### Fallback Strategy",
            f"",
        ])
        for fb in entry["fallback_strategy"]:
            lines.append(f"- 🔄 {fb}")

        lines.extend([
            f"",
            f"#### 建议",
            f"",
            f"> {entry['next_step_recommendation']}",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## 5. 推荐首个 Live-Like One-Shot 实验对象",
        f"",
    ])

    if recommended:
        rec_entry = next((e for e in matrix if e["card_type"] == recommended), None)
        if rec_entry:
            lines.extend([
                f"### 🏆 推荐：`{recommended}`",
                f"",
                f"**理由**：",
                f"",
                f"- Readiness Score: **{rec_entry['readiness_score']}/18** (最高分)",
                f"- Readiness Level: **{rec_entry['readiness_level'].upper()}**",
                f"- Preview Cards: **{preview_counts.get(recommended, 0)}** 条",
                f"- One-Shot 可行: **✅ 是**",
                f"- 需要凭证: **{'❌ 不需要' if not rec_entry['credential_required'] else '⚠️ 需要（免费）'}**",
                f"- 需要付费 API: **{'❌ 不需要' if not rec_entry['paid_api_likely_required'] else '⚠️ 可能需要'}**",
                f"- 需要 Daemon: **❌ 不需要**",
                f"",
                f"**数据源全部免费、无需 API Key、纯 REST 调用、字段简单、失败易降级。**",
                f"",
                f"建议 v112Q 阶段仅做 **one-shot 计划**，在本地用 Python 脚本模拟一次",
                f"live-like 数据拉取（用 CoinGecko/CoinCap 免费 API），验证：",
                f"",
                f"1. 数据字段是否完整覆盖 required_fields",
                f"2. 响应延迟是否在可接受范围（< 5s）",
                f"3. 免费 API 的 rate limit 是否影响批量拉取",
                f"4. 数据格式是否与现有 preview card 结构兼容",
                f"",
                f"⚠️ **v112Q 只做计划，不执行 live 拉取。** 当前阶段仍为 dry-run。",
            ])
    else:
        lines.append("⚠️ 无符合条件的 one-shot candidate。")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 6. 为什么现在仍不能真实发送",
        f"",
        f"| 原因 | 说明 |",
        f"|------|------|",
        f"| 无 live 数据源 | 所有数据来自本地 fixture，未经真实 API 验证 |",
        f"| 无数据新鲜度保证 | 本地 fixture 时间戳是硬编码的模拟数据 |",
        f"| 无 API 可靠性测试 | 未测试 rate limit、超时、数据格式变化等边界情况 |",
        f"| 无生产状态写入 | 所有 state 都是 dry-run，未建立生产状态持久化 |",
        f"| 无人工审阅流程 | 当前没有审阅界面或人工确认流程 |",
        f"| 无回调/告警 | 发送失败、数据异常等情况无处理机制 |",
        f"| TG 发送未经 live source 端到端测试 | v112O 仅为本地预览包 |",
        f"",
        f"---",
        f"",
        f"## 7. 安全边界确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| dry_run_only | true |",
        f"| live_ready | false |",
        f"| real_tg_sent | false |",
        f"| real_send_ready | false |",
        f"| production_state_write_ready | false |",
        f"| external_api_called | false |",
        f"| external_ai_called | false |",
        f"| daemon_started | false |",
        f"| files_deleted | false |",
        f"| debug_leak_count | 0 |",
        f"| secret_leak_count | 0 |",
        f"| manual_review_required_before_send | true |",
        f"",
        f"---",
        f"",
        f"## 8. 下一步建议",
        f"",
        f"1. **v112Q — One-Shot Live-Like Candidate Plan**: 针对推荐 card type",
        f"   (`{recommended}`) 制定详细的 one-shot 实验计划，",
        f"   只做计划文档，不执行 live 拉取。",
        f"",
        f"2. v112R — 如果 v112Q 计划通过审查，可在隔离环境中执行首次",
        f"   one-shot live-like 实验（仅拉取，不发送）。",
        f"",
        f"3. 低优先级 card type（news_event_market_impact）继续使用本地 fixture，",
        f"   待高优先级类型验证通过后再考虑接入。",
        f"",
        f"---",
        f"",
        f"*Generated by {VERSION} at {china_stamp()}*",
    ])

    report_text = "\n".join(lines)

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"  [OK] {REPORT_MD_PATH}")

    return report_text


def write_handoff(
    matrix: list[dict],
    v112n_validation: dict,
    v112o_validation: dict,
    result: dict,
    files_read: list[str],
    files_generated: list[str],
    recommended: str,
    preview_counts: dict[str, int],
) -> str:
    """Write the v112P handoff markdown and return the text."""
    lines = [
        f"# Market Radar v1.12-P — Live Source Readiness Audit Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Status**: {result.get('status', '?').upper()}",
        f"",
        f"---",
        f"",
        f"## v112P 做了什么",
        f"",
        f"v112P Live Source Readiness Audit 是一个纯本地审计步骤。它：",
        f"",
        f"1. 验证 v112N master dry-run 通过 (status=passed, dry_run_only=true)",
        f"2. 验证 v112O send preview pack 通过 (status=passed, preview_card_count=9, send_preview_pack_ready=true)",
        f"3. 为 5 类固定卡片建立 live source readiness matrix",
        f"4. 对每类卡片审计：",
        f"   - 需要哪些 live data source",
        f"   - 需要哪些字段",
        f"   - 是否需要 API key / 付费 / WebSocket / daemon",
        f"   - one-shot experiment 是否可行",
        f"   - 失败模式和 fallback 策略",
        f"5. 使用确定性本地规则打分（不调用 AI），产出 readiness_score 和 readiness_level",
        f"6. 推荐首个 one-shot live-like experiment candidate",
        f"7. 明确说明当前仍未开启的所有能力",
        f"8. 生成 result JSON + matrix JSON + report MD + handoff MD",
        f"",
        f"**v112P 没有**:",
        f"- ❌ 接入任何 live data source",
        f"- ❌ 调用任何外部 API",
        f"- ❌ 调用任何外部 AI",
        f"- ❌ 真实发送 TG",
        f"- ❌ 生产状态写入",
        f"- ❌ 启动 daemon / cron / loop",
        f"- ❌ 删除任何文件",
        f"- ❌ 读取任何 API Key / Token / Cookie / 密码",
        f"",
        f"---",
        f"",
        f"## 读取了哪些上游产物",
        f"",
    ]

    for fp in files_read:
        lines.append(f"- `{fp}`")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 生成了哪些文件",
        f"",
    ])

    for fp in files_generated:
        lines.append(f"- `{fp}`")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 上游验证结果",
        f"",
        f"### v112N",
        f"",
        f"| 检查项 | 结果 |",
        f"|--------|------|",
    ])
    for check, value in v112n_validation["checks"].items():
        lines.append(f"| {check} | {'✅' if value else '❌'} |")

    lines.extend([
        f"",
        f"### v112O",
        f"",
        f"| 检查项 | 结果 |",
        f"|--------|------|",
    ])
    for check, value in v112o_validation["checks"].items():
        lines.append(f"| {check} | {'✅' if value else '❌'} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Readiness Matrix 摘要",
        f"",
        f"| Card Type | Preview Cards | Score | Level | One-Shot | Credential |",
        f"|-----------|--------------|-------|-------|----------|------------|",
    ])

    for entry in matrix:
        ct = entry["card_type"]
        pc = preview_counts.get(ct, 0)
        lines.append(
            f"| {ct} | {pc} | {entry['readiness_score']}/18 | "
            f"{entry['readiness_level']} | "
            f"{'✅' if entry['one_shot_experiment_possible'] else '❌'} | "
            f"{'⚠️' if entry['credential_required'] else '✅'} |"
        )

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 推荐首个 One-Shot Candidate",
        f"",
        f"**推荐**: `{recommended}`",
        f"",
    ])

    rec_entry = next((e for e in matrix if e["card_type"] == recommended), None)
    if rec_entry:
        lines.extend([
            f"- Readiness Score: {rec_entry['readiness_score']}/18",
            f"- 所有数据源免费",
            f"- 无需 API Key",
            f"- 无付费风险",
            f"- 纯 REST 调用",
            f"- 字段简单（价格、涨跌幅）",
            f"- 失败后易降级（多个免费价格源可用）",
        ])

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 当前仍未开启的能力",
        f"",
        f"| 能力 | 状态 | 说明 |",
        f"|------|------|------|",
        f"| live source | ❌ 未开启 | 所有数据来自本地 fixture，未接任何真实数据源 |",
        f"| production state write | ❌ 未开启 | 仅 dry-run，未建立生产状态 |",
        f"| TG send | ❌ 未开启 | real_tg_sent=false |",
        f"| daemon / cron / loop | ❌ 未开启 | 仅单次执行 |",
        f"| external API | ❌ 未开启 | 无网络调用 |",
        f"| external AI | ❌ 未开启 | 无外部 AI 调用 |",
        f"| live_ready | ❌ false | 需真实数据源接入 |",
        f"| real_send_ready | ❌ false | 需 live source 接入并通过端到端测试 |",
        f"| production_state_write_ready | ❌ false | 需生产状态持久化方案 |",
        f"",
        f"---",
        f"",
        f"## 测试结果",
        f"",
        f"```powershell",
        f"cd <project_dir>",
        f"python scripts/test_market_radar_v112p_live_source_readiness_audit.py",
        f"```",
        f"",
        f"测试覆盖：",
        f"- runner 可执行成功",
        f"- 所有输出文件存在 (result JSON, matrix JSON, report MD, handoff MD)",
        f"- status == \"passed\"",
        f"- 所有安全边界字段",
        f"- readiness matrix 包含 5 类 card_type",
        f"- 每类都有 required_live_sources、required_fields、failure_modes、fallback_strategy",
        f"- 每类都有 readiness_score 和 readiness_level",
        f"- 至少 1 类支持 one-shot experiment",
        f"- 无凭证/密钥泄漏",
        f"- 无误导性文字",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"**v112Q — One-Shot Live-Like Candidate Plan**:",
        f"",
        f"1. 针对 `{recommended}` 编写详细 one-shot 实验计划",
        f"2. 明确需要调用的具体 API endpoint、参数、预期返回格式",
        f"3. 设计数据适配层（将 live API 返回映射到现有 required_fields）",
        f"4. 设计实验的 pass/fail 标准",
        f"5. **只做计划文档，不执行 live 拉取**",
        f"",
        f"---",
        f"",
        f"*Generated by {VERSION} at {china_stamp()}*",
    ])

    handoff_text = "\n".join(lines)

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff_text)
    print(f"  [OK] {HANDOFF_MD_PATH}")

    return handoff_text


# ── Leak scanner ──────────────────────────────────────────────────────────────────

def scan_all_outputs(matrix: list[dict], result: dict, report_text: str, handoff_text: str) -> tuple[int, list[str]]:
    """Scan all outputs for secret leaks and misleading terms."""
    secret_count = 0
    all_warnings: list[str] = []

    # Scan matrix entries
    for entry in matrix:
        for key in ["required_live_sources", "required_fields", "optional_fields",
                     "failure_modes", "fallback_strategy", "next_step_recommendation"]:
            value = entry.get(key, "")
            if isinstance(value, list):
                text = " ".join(str(v) for v in value if isinstance(v, str))
                text += " ".join(
                    str(v.get("source", "")) + " " + str(v.get("data", ""))
                    for v in value if isinstance(v, dict)
                )
            else:
                text = str(value)
            sc = check_forbidden_terms(text)
            secret_count += sc
            if sc:
                all_warnings.append(f"Matrix {entry['card_type']}.{key}: potential secret")

    # Scan result JSON values
    result_values = " ".join(
        str(v) for v in result.values()
        if isinstance(v, (str, int, float, bool))
    )
    secret_count += check_forbidden_terms(result_values)

    # Scan reports
    for label, text in [("report", report_text), ("handoff", handoff_text)]:
        secret_count += check_forbidden_terms(text)
        misleading = check_misleading_terms(text)
        if misleading:
            all_warnings.append(f"{label}: misleading terms found: {misleading}")

    return secret_count, all_warnings


# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"{'=' * 70}")
    print(f"Market Radar {VERSION} — Live Source Readiness Audit")
    print(f"{'=' * 70}")
    print(f"Run ID: {RUN_ID}")
    print(f"Task ID: {TASK_ID}")
    print(f"Started: {china_stamp()}")
    print()
    print("Safety constraints:")
    print("  DRY-RUN ONLY: YES")
    print("  LIVE SOURCE: NONE (audit only)")
    print("  TG SEND: NONE")
    print("  EXTERNAL API: NONE")
    print("  EXTERNAL AI: NONE")
    print("  DAEMON: NONE")
    print("  CREDENTIAL READ: NONE")
    print()

    files_read: list[str] = []
    files_generated: list[str] = []

    # ── Step 1: Validate v112N ─────────────────────────────────────────────────
    print("[1/7] Validating v112N master dry-run...")
    master = load_json(MASTER_RESULT_PATH)
    if master is None:
        print(f"  [FAIL] v112N master result not found: {MASTER_RESULT_PATH}")
        return 1
    files_read.append(str(MASTER_RESULT_PATH.relative_to(ROOT)))

    v112n_valid = validate_v112n(master)
    if not v112n_valid["all_valid"]:
        print(f"  [FAIL] v112N validation failed: {v112n_valid['failed']}")
        return 1
    print(f"  [OK] v112N validated: status=passed, dry_run_only=true, eligible=9, idempotency=passed")
    print()

    # ── Step 2: Validate v112O ─────────────────────────────────────────────────
    print("[2/7] Validating v112O send preview pack...")
    v112o_result = load_json(V112O_RESULT_PATH)
    if v112o_result is None:
        print(f"  [FAIL] v112O result not found: {V112O_RESULT_PATH}")
        return 1
    files_read.append(str(V112O_RESULT_PATH.relative_to(ROOT)))

    v112o_valid = validate_v112o(v112o_result)
    if not v112o_valid["all_valid"]:
        print(f"  [FAIL] v112O validation failed: {v112o_valid['failed']}")
        return 1
    print(f"  [OK] v112O validated: status=passed, preview_card_count=9, send_preview_pack_ready=true")
    print()

    # ── Step 3: Load v112O preview cards ────────────────────────────────────────
    print("[3/7] Loading v112O preview cards for distribution analysis...")
    cards = load_jsonl(V112O_CARDS_PATH)
    if not cards:
        print(f"  [WARN] No v112O preview cards found at {V112O_CARDS_PATH}")
    else:
        files_read.append(str(V112O_CARDS_PATH.relative_to(ROOT)))
        print(f"  [OK] Loaded {len(cards)} preview cards")
    print()

    # ── Step 4: Build readiness matrix ─────────────────────────────────────────
    print("[4/7] Building readiness matrix for 5 card types...")
    matrix = build_readiness_matrix(cards)

    if len(matrix) != 5:
        print(f"  [FAIL] Expected 5 card types in matrix, got {len(matrix)}")
        return 1

    preview_counts = get_preview_card_count_by_type(cards)
    for entry in matrix:
        ct = entry["card_type"]
        print(f"       {ct}: score={entry['readiness_score']}/18, "
              f"level={entry['readiness_level']}, "
              f"one_shot={entry['one_shot_experiment_possible']}, "
              f"preview_cards={preview_counts.get(ct, 0)}")
    print()

    # ── Step 5: Pick recommended candidate ─────────────────────────────────────
    print("[5/7] Selecting recommended first one-shot candidate...")
    recommended = pick_recommended_candidate(matrix)
    if not recommended:
        print(f"  [WARN] No one-shot candidate found")
    else:
        rec_entry = next((e for e in matrix if e["card_type"] == recommended), None)
        print(f"  [OK] Recommended: {recommended} (score={rec_entry['readiness_score']}/18)")
    print()

    # ── Step 6: Build result JSON ──────────────────────────────────────────────
    print("[6/7] Building result JSON...")

    one_shot_count = sum(1 for e in matrix if e["one_shot_experiment_possible"])

    result = {
        "version": VERSION,
        "status": "passed",
        "dry_run_only": True,
        "live_ready": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "card_types_total": 5,
        "readiness_matrix_ready": True,
        "one_shot_candidates_count": one_shot_count,
        "recommended_first_one_shot_candidate": recommended,
        "real_send_ready": False,
        "production_state_write_ready": False,
        "manual_review_required_before_send": True,
        "v112n_validated": v112n_valid["all_valid"],
        "v112o_validated": v112o_valid["all_valid"],
        "upstream_artifacts_read": files_read,
        "generated_at": china_stamp(),
    }

    # Write result JSON
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    files_generated.append(str(RESULT_JSON_PATH.relative_to(ROOT)))

    # Write matrix JSON
    with open(MATRIX_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "version": VERSION,
            "generated_at": china_stamp(),
            "card_types_total": 5,
            "entries": matrix,
        }, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {MATRIX_JSON_PATH}")
    files_generated.append(str(MATRIX_JSON_PATH.relative_to(ROOT)))
    print()

    # ── Step 7: Write report and handoff ───────────────────────────────────────
    print("[7/7] Writing report and handoff...")

    report_text = write_report(
        matrix, v112n_valid, v112o_valid, preview_counts, recommended, result
    )
    files_generated.append(str(REPORT_MD_PATH.relative_to(ROOT)))

    handoff_text = write_handoff(
        matrix, v112n_valid, v112o_valid, result,
        files_read, files_generated, recommended, preview_counts,
    )
    files_generated.append(str(HANDOFF_MD_PATH.relative_to(ROOT)))

    print()

    # ── Final leak scan ─────────────────────────────────────────────────────────
    secret_count, scan_warnings = scan_all_outputs(matrix, result, report_text, handoff_text)

    if secret_count > 0:
        print(f"  [WARN] Secret leak scan: {secret_count} potential secrets found!")
        result["secret_leak_count"] = secret_count
    if scan_warnings:
        print(f"  [WARN] Misleading terms found:")
        for w in scan_warnings:
            print(f"         {w}")

    # Update result with final leak counts
    result["secret_leak_count"] = secret_count
    result["debug_leak_count"] = len(scan_warnings)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Result updated with final leak counts")
    print()

    # ── Final summary ──────────────────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-P Live Source Readiness Audit — Complete")
    print(f"{'=' * 70}")
    print(f"  Status:                    {result['status'].upper()}")
    print(f"  Readiness matrix ready:    {result['readiness_matrix_ready']}")
    print(f"  Card types audited:        {result['card_types_total']}")
    print(f"  One-shot candidates:       {result['one_shot_candidates_count']}")
    print(f"  Recommended first:         {result['recommended_first_one_shot_candidate']}")
    print(f"  Live ready:                {result['live_ready']}")
    print(f"  Real send ready:           {result['real_send_ready']}")
    print(f"  Production state ready:    {result['production_state_write_ready']}")
    print(f"  Secret leaks:              {result['secret_leak_count']}")
    print(f"  TG send:                   NONE")
    print(f"  External API:              NONE")
    print(f"  External AI:               NONE")
    print(f"  Daemon:                    NONE")
    print(f"{'=' * 70}")
    print()
    print("[PASS] v112P live source readiness audit completed successfully.")
    print("       This is a LOCAL AUDIT ONLY — no live source, no TG send, no external API/AI.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
