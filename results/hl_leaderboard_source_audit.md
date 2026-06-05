# Hyperliquid Leaderboard Source Audit

Date: 2026-06-01

## Sources

| source | type | free | needs_auth | get_address | get_pnl | get_asset | get_rank | MVP | risk |
|--------|------|------|------------|-------------|---------|-----------|----------|-----|------|
| Official SDK Info API | official | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | — | No leaderboard endpoint |
| HL app leaderboard page | frontend_public | ✅ | ❌ | partial | ✅ | ❌ | ✅ | ⚠️ risky | Needs DOM parsing, breaks on UI change |
| HyperInsight TG channel | third_party | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | **Yes** | Manual extraction, time-bound |
| ASXN / hypurrscan | third_party | partial | ❌ | partial | partial | ✅ | ✅ | maybe | Site TOS check needed |
| Nansen / Dune | third_party | paid | ✅ | ✅ | ✅ | ✅ | ✅ | later | $ cost, not MVP |

## Recommended for MVP

**HyperInsight TG channel + our own position snapshots.**

- HyperInsight: already parsed 20 messages with entity/address/rank/asset labels
- Position snapshots: 4 addresses with full position history
- Combined: ~4 unique addresses, all with HYPE positions

## What We Can Do Now

1. Monitor HyperInsight channel daily for new leaderboard-style messages
2. Extract new addresses and labels from each message batch
3. Add to entity_profiles.sqlite with source=hyperinsight
4. Track address appearance over time for confidence scoring

## What We Cannot Do (without new sources)

- Real-time leaderboard rankings
- PnL leaderboard
- Volume leaderboard
- Multi-asset address discovery at scale

## Conclusion

Current Address Universe is sufficient to show individual address behavior cards.
It is NOT sufficient for cross-sectional whale/large trader multi-direction ratio.
For that we need either leaderboard API access or 20+ manually tracked addresses.
