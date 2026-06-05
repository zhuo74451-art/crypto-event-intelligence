# v115P Whale Operator Fixture Preflight — Handoff

**Generated**: 2026-06-05T09:12:22+08:00

## Execution Summary

| Metric | Value |
|--------|-------|
| Fixture rows | 4 |
| Fixture preflight records | 4 |
| Fixture preflight decisions | 4 |
| Fixture preflight ready count | 4 |
| Fixture preflight blocked count | 0 |
| Fixture ready for gate rerun count | 4 |
| Low/unknown fixture ready count | 2 |
| Medium fixture ready count | 2 |
| Manual attribution fixture ready count | 2 |
| Corroboration fixture ready count | 2 |
| Real workbook rows | 4 |
| Real workbook modified | False |
| Real label upgrade performed | False |
| Real send candidate generated | False |
| Send ready | False |
| TG test group ready | False |
| TG sent | False |
| Prod state write | False |
| External API called | False |
| Credentials read | False |
| Fixture only | True |
| Next gate command order enforced | True |
| Real workbook byte-identical | True |

## Output Files

| File | Path |
|------|------|
| Fixture workbook CSV | `runs/market_radar/v115p_whale_operator_fixture_filled_workbook.csv` |
| Fixture filled rows JSONL | `results/market_radar_v115p_whale_operator_fixture_filled_workbook_rows.jsonl` |
| Fixture preflight records JSONL | `results/market_radar_v115p_whale_operator_fixture_preflight_records.jsonl` |
| Fixture preflight decisions JSONL | `results/market_radar_v115p_whale_operator_fixture_preflight_decisions.jsonl` |
| Positive path result JSON | `results/market_radar_v115p_whale_operator_fixture_preflight_positive_path_result.json` |
| Operator example MD | `runs/market_radar/v115p_whale_operator_filled_workbook_example.md` |
| Preflight report MD | `runs/market_radar/v115p_whale_operator_fixture_preflight_positive_path_report.md` |
| Handoff MD | `runs/market_radar/v115p_whale_operator_fixture_preflight_positive_path_local_only_handoff.md` |

## Safety Status

- ✅ No real workbook modified
- ✅ No real label upgrade performed
- ✅ No real send candidate generated
- ✅ No TG sent
- ✅ No production state written
- ✅ No external API called
- ✅ No credentials read
- ✅ Fixture only — all evidence values marked TEST_ONLY
- ✅ Gate command order enforced

## Warnings

1. **FIXTURE ONLY.** All evidence values are synthetic TEST_ONLY placeholders.
2. **Do NOT copy fixture values into real workbook.**
3. **Real v115F workbook is still blocked.** Operator must fill with real evidence.
4. **Fixture preflight pass does NOT mean real addresses passed.**
5. **Medium confidence passing preflight does NOT equal TG test group readiness.**
