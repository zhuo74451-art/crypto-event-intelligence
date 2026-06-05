# Hyperliquid Python SDK Capability Audit

Date: 2026-06-01

## SDK: hyperliquid-python-sdk (installed)

Package provides `from hyperliquid.info import Info` and `from hyperliquid.exchange import Exchange`.

### Read-Only Methods (Info class)

| method | SDK | Raw API | Project Has | Recommendation |
|--------|-----|---------|-------------|----------------|
| meta_and_asset_ctxs() | ✅ | ✅ | ✅ fetch_market_meta.py | **Use SDK** (simpler, typed) |
| spot_meta_and_asset_ctxs() | ✅ | ✅ | ❌ | **Use SDK** for spot assets |
| clearinghouse_state(user) | pending | ✅ | ✅ fetch_hl_address_history | **Keep raw** (simpler POST) |
| user_fills(user) | ✅ | ✅ | ✅ fetch_hl_address_history | **Keep raw** (existing) |
| user_funding(user, start, end) | pending | ✅ | ✅ fetch_hl_address_history | **Keep raw** (existing) |
| user_non_funding_ledger(user, start, end) | pending | ✅ | ✅ fetch_hl_address_history | **Keep raw** (existing) |
| open_orders(user) | ✅ | ✅ | ❌ | Not needed for Radar |
| all_mids() | ✅ | ✅ | ❌ | Not needed |
| l2_snapshot(coin) | ✅ | ✅ | ❌ | Not needed |

### Leaderboard / Top Traders

| method | Available | Notes |
|--------|-----------|-------|
| Official SDK leaderboard | ❌ Not in SDK v0.x | No leaderboard method in current Info class |
| Raw API endpoint | ❌ No documented endpoint | metaAndAssetCtxs has no leaderboard data |
| Frontend public page | https://app.hyperliquid.xyz/leaderboard | Requires browser rendering, not API |

### Migration Plan

**Minimal: Replace only meta_and_asset_ctxs() with SDK.**

Current: `urllib.request` raw POST to `https://api.hyperliquid.xyz/info`
SDK: `from hyperliquid.info import Info; info = Info(); info.meta_and_asset_ctxs()`

Benefits:
- Better field typing (markPx, funding, openInterest auto-parsed)
- Error handling built-in
- No change to other scripts

**Keep everything else as-is.** Our raw POST approach for clearinghouseState/userFills/userFunding is working and tested.

### Risk

- SDK version upgrades may change API surface
- Rate limits: SDK uses same public endpoint, no additional risk
- No authentication required for info endpoint
