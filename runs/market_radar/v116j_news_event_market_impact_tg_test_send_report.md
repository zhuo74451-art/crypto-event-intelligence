# Market Radar v1.16-J — News Event Market Impact TG Test Send Report

**Generated**: 2026-06-05T13:25:22.839600+08:00
**Task ID**: 20260605_v116j_news_event_market_impact_real_free_public_source_tg_test_send_one_shot
**Run ID**: 20260605_124925

⚠️ **声明**: 本报告所有卡片均为“事件影响观察”，
不构成事件→行情的因果证明。事件抽取使用规则逻辑。

---

## Executive Summary

| Field | Value |
|-------|-------|
| card_family | `news_event_market_impact` |
| audit_result | **real_free_public_source_tg_test_sent** |
| real_public_source_called | **True** |
| real_external_api_called | **True** |
| sources_succeeded | **1/5** |
| events_admitted | **2/7** |
| TG test sent | **True** |
| secret_preflight_passed | **True** |

---

## Safe Secret Preflight

| Check | Result |
|-------|--------|
| preflight_run | True |
| telegram_bot_token_present | True |
| telegram_chat_id_present | True |
| preflight_passed | True |
| values_printed | False |
| values_logged | False |

---

## News Sources

- **CoinDesk**: empty, 0 articles
- **Cointelegraph**: empty, 0 articles
- **Decrypt**: empty, 0 articles
- **The Block**: empty, 0 articles
- **Binance Announcements**: ok, 80 articles

---

## Events Extracted and Gate Results

### Event 1: Introducing Genius Terminal (GENIUS) on Binance HODLer Airdrops! Earn GENIUS With Retroactive BNB Si

- **Source**: Binance Announcements
- **URL**: https://www.binance.com/en/support/announcement/275505
- **Assets**: BNB
- **Event Type**: airdrop
- **Intensity**: medium
- **Attribution**: indirect
- **Admission**: BLOCKED ()
- **Quality Gate**: BLOCKED
- **Send-Readiness**: BLOCKED
- **TG Send**: BLOCKED (gate_not_passed)

### Event 2: Wallet Maintenance for Ethereum Network (ETH) - 2026-05-21

- **Source**: Binance Announcements
- **URL**: https://www.binance.com/en/support/announcement/274402
- **Assets**: ETH
- **Event Type**: outage
- **Intensity**: low
- **Attribution**: indirect
- **Admission**: BLOCKED (indirect_attribution_non_macro)
- **Quality Gate**: BLOCKED
- **Send-Readiness**: BLOCKED
- **TG Send**: BLOCKED (gate_not_passed)

### Event 3: Solayer (LAYER) Airdrop Continues: Fourth Binance HODLer Airdrops Announced – Earn LAYER With Retroa

- **Source**: Binance Announcements
- **URL**: https://www.binance.com/en/support/announcement/249268
- **Assets**: BNB
- **Event Type**: airdrop
- **Intensity**: medium
- **Attribution**: indirect
- **Admission**: BLOCKED ()
- **Quality Gate**: BLOCKED
- **Send-Readiness**: BLOCKED
- **TG Send**: BLOCKED (gate_not_passed)

### Event 4: Introducing Avantis (AVNT) on Binance HODLer Airdrops! Earn AVNT With Retroactive BNB Simple Earn Su

- **Source**: Binance Announcements
- **URL**: https://www.binance.com/en/support/announcement/248527
- **Assets**: BNB
- **Event Type**: airdrop
- **Intensity**: medium
- **Attribution**: indirect
- **Admission**: BLOCKED ()
- **Quality Gate**: BLOCKED
- **Send-Readiness**: BLOCKED
- **TG Send**: BLOCKED (gate_not_passed)

### Event 5: MyShell (SHELL) Airdrop Continues: Second Binance HODLer Airdrops Announced – Earn SHELL With Retroa

- **Source**: Binance Announcements
- **URL**: https://www.binance.com/en/support/announcement/245906
- **Assets**: BNB
- **Event Type**: regulatory
- **Intensity**: medium
- **Attribution**: indirect
- **Admission**: PASS (None)
- **Quality Gate**: PASS
- **Send-Readiness**: PASS
- **TG Send**: SENT ()

### Event 6: Solayer (LAYER) Airdrop Continues: Third Binance HODLer Airdrops Announced – Earn LAYER With Retroac

- **Source**: Binance Announcements
- **URL**: https://www.binance.com/en/support/announcement/245082
- **Assets**: BNB
- **Event Type**: airdrop
- **Intensity**: medium
- **Attribution**: indirect
- **Admission**: BLOCKED ()
- **Quality Gate**: BLOCKED
- **Send-Readiness**: BLOCKED
- **TG Send**: BLOCKED (gate_not_passed)

### Event 7: Solayer (LAYER) Airdrop Continues: Second Binance HODLer Airdrops Announced – Earn LAYER With Retroa

- **Source**: Binance Announcements
- **URL**: https://www.binance.com/en/support/announcement/238891
- **Assets**: BNB
- **Event Type**: regulatory
- **Intensity**: medium
- **Attribution**: indirect
- **Admission**: PASS (None)
- **Quality Gate**: PASS
- **Send-Readiness**: PASS
- **TG Send**: SENT ()

---

## Safety Confirmation

| Constraint | Status |
|------------|--------|
| secret_preflight_run | True |
| real_public_source_called | True |
| real_external_api_called | True |
| fixture_only | False |
| production_send_ready | False |
| prod_state_write | False |
| ai_model_called | False |
| credentials_printed | False |
| daemon_or_loop_started | False |
| files_deleted | False |
| news_full_text_saved | False |
| TG target is test group | True |
| one_shot (not loop) | True |
| risk disclaimer present | True |
| no false causality | True |

---

## Conclusion

**Audit result**: `real_free_public_source_tg_test_sent`

TG test group send **SUCCEEDED**. News event card(s) delivered to test group (one-shot).
Redacted message proof: sha256:9dc6abc967dad3e2
