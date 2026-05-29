# v0.8.1 Token Unlock Calendar Quality Report

- status: ready
- calendar_rows: 500
- real_rows: 500
- sample_rows: 0
- upcoming_30d_rows: 495
- large_unlock_rows: 3

## Blocking Issues

- real_rows below target: 500 / 20
- invalid_time_rows: 0
- unsupported_symbol_rows: 0
- missing_amount_rows: 8
- missing_source_rows: 0
- require_symbol_map: false
- require_amount_usd: false

## Preview

| unlock_id | asset | time | amount_usd | source | flags |
|---|---|---|---:|---|---|
| cmc_unlock_tao_0c05d74f408085 | TAO | 2025-11-11T00:00:00Z | 28042287.81 | coinmarketcap_token_unlocks | not_in_symbol_map,past_unlock_time |
| cmc_unlock_rex_f094992258fbc8 | REX | 2026-02-18T00:00:00Z | 593.23 | coinmarketcap_token_unlocks | not_in_symbol_map,past_unlock_time |
| cmc_unlock_drift_3eb947c186982a | DRIFT | 2026-04-16T00:00:00Z | 388383.6 | coinmarketcap_token_unlocks | not_in_symbol_map,past_unlock_time |
| cmc_unlock_ucbi_ba94e66ba686eb | UCBI | 2026-05-16T00:00:00Z | 4239095.76 | coinmarketcap_token_unlocks | not_in_symbol_map,past_unlock_time |
| cmc_unlock_epiko_cbbd425dceccc0 | EPIKO | 2026-05-20T00:00:00Z | 35593.86 | coinmarketcap_token_unlocks | not_in_symbol_map,past_unlock_time |
| cmc_unlock_numi_96f2846859e2da | NUMI | 2026-05-28T07:00:00Z | 142562.84 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_meme_e3f1517cddc916 | MEME | 2026-05-28T07:30:00Z | 5087.95 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_enf_2c405a8a4017b9 | ENF | 2026-05-28T08:00:00Z | 353.27 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_tac_fe64813b51c6c2 | TAC | 2026-05-28T08:00:00Z | 131064.96 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_zkwasm_4882feaa9c40fa | ZKWASM | 2026-05-28T08:00:00Z | 97.43 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_ovl_2b29e90a411d11 | OVL | 2026-05-28T08:30:00Z | 290.34 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_celb_b8e2fcda8fc4e7 | CELB | 2026-05-28T09:00:00Z | 353979.42 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_goated_780a65d83911f0 | GOATED | 2026-05-28T09:00:00Z | 3181.72 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_init_2de42316623eba | INIT | 2026-05-28T09:00:00Z | 2221.69 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_adix_52f05e6d0fe472 | ADIX | 2026-05-28T10:00:00Z | 44.41 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_baby_a5210bf0be01d1 | BABY | 2026-05-28T10:00:00Z | 34729.3 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_blue_5217e667912b26 | BLUE | 2026-05-28T10:00:00Z | 955.67 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_bric_a7c85a6bc23d74 | BRIC | 2026-05-28T10:00:00Z | 61.78 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_cookie_3d61cb76ce5c88 | COOKIE | 2026-05-28T10:00:00Z | 5437.28 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_delabs_e26227391c74fa | DELABS | 2026-05-28T10:00:00Z | 87714.09 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_hvlo_48084120ff04e2 | HVLO | 2026-05-28T10:00:00Z | 603.93 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_ika_d585e033329f30 | IKA | 2026-05-28T10:00:00Z | 627606.02 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_in_e192294a647bd3 | IN | 2026-05-28T10:00:00Z | 64973.55 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_rwainc_c5ba241864ca39 | RWAINC | 2026-05-28T10:00:00Z | 1220.41 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_svsa_0e690290401ce8 | SVSA | 2026-05-28T10:00:00Z | 1267.36 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_taker_8d761a2490e2d7 | TAKER | 2026-05-28T10:00:00Z | 16.25 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_bdxn_3b4128da1457d4 | BDXN | 2026-05-28T10:05:00Z | 84.9 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_odos_1d4ea917a4feba | ODOS | 2026-05-28T10:20:00Z | 5623.18 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_acn_1ea27133d0a621 | ACN | 2026-05-28T11:00:00Z | 3536.4 | coinmarketcap_token_unlocks | not_in_symbol_map |
| cmc_unlock_bmt_d6b94856d86d95 | BMT | 2026-05-28T11:00:00Z | 10138.89 | coinmarketcap_token_unlocks | not_in_symbol_map |

## Rule

Only real, sourced unlock rows should drive Telegram or backtest candidates. Sample rows are allowed for pipeline tests only.
