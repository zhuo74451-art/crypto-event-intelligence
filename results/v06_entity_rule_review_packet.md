# v0.6 Entity Rule Review Packet

This packet isolates rows where entity detection or primary-asset selection is ambiguous.
It is non-destructive and does not edit candidate files.

## Summary

| review_type | count |
|---|---:|
| protocol_exploit_primary_asset_policy | 5 |
| generic_entity_mismatch | 1 |
| hyperliquid_primary_asset_supported | 1 |
| multi_chain_regulatory_flow | 1 |

## Rows

| candidate_id | review_type | current_asset | suggested_asset | suggested_route | note | title |
|---|---|---|---|---|---|---|
| cand_00117 | protocol_exploit_primary_asset_policy | ETH | ETH | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | Exploit Alert 🚨  According to @dcfgod, @EchoProtocol_ on @monad has been exploited.  The attacker reportedly m |
| cand_00047 | protocol_exploit_primary_asset_policy | ETH | ETH | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | Lookonchain：过去4天内发生3起重大黑客攻击事件 |
| cand_00011 | protocol_exploit_primary_asset_policy | ETH | ETH | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | 黑客攻击Monad Echo协议，损失约7600万美元 |
| cand_00124 | protocol_exploit_primary_asset_policy | BTC | BTC | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad   The hacker minted 1k $eBTC ($76.7M |
| cand_00105 | protocol_exploit_primary_asset_policy | BTC | BTC | alpha_candidate | Exploit rows mix protocol, chain, minted asset, and returned asset; define whether primary asset is affected token, stol | 链上监测：黑客在Monad平台上铸造1000枚EBTC并洗钱 |
| cand_00213 | generic_entity_mismatch | SHIB | SHIB | research_only | Entity mismatch requires dictionary or rule review. | Shiba Inu sees 3b SHIB hit exchanges |
| cand_00029 | hyperliquid_primary_asset_supported | HYPE | HYPE | alpha_candidate | Hyperliquid/HYPE appears to be primary and now has a validated Binance market symbol; review route, not symbol support. | Defillama：Hyperliquid仍维持链上永续合约市场领先地位 |
| cand_00026 | multi_chain_regulatory_flow | TRX |  | macro_policy | Regulatory/sanctions flow across Tron and BNB Chain; avoid single-asset attribution. | 据 Reuters 调查报道，数据分析显示，自 2023 年以来，受制裁影响的伊朗最大加密交易所 Nobitex 已通过 Tron 和 BNB Chain 网络处理了至少 23 亿美元。报道指出，这两个区块链的创始人孙宇 |

## Recommended Next Step

- Do not apply these as automatic fixes yet.
- First decide primary-asset policy for protocol exploits and multi-chain regulatory events.
- Add dictionary/rule changes only when the same pattern repeats.
