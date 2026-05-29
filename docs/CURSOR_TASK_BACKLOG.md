# Cursor Task Backlog

Cursor handoff is file-based. Generate the current handoff prompt with:

```powershell
python scripts/generate_cursor_prompt.py
```

Current handoff file:

```text
docs/CURSOR_NEXT_PROMPT.md
```

## Pending Tasks

1. Review whether `project_business/payment_adoption` rows such as Revolut crypto card should stay in review or be discarded.
2. Check whether BTC macro/policy rows should be a separate queue from single-asset market-moving events.
3. Inspect `primary_asset_symbol` blank rows in `data/event_candidates_v06_publish_review_queue.csv` and decide whether they should be discarded or treated as market-wide.
4. Review unsupported assets such as HYPE, ONDO, WLD and decide which ones deserve `unsupported_research` review even though they cannot enter Binance backtest.
5. Identify recurring Web3 project aliases still missing from `data/entity_dictionary.csv`.
6. Find rows where long scraped webpage footer text caused false entity/event matches.
7. Flag opinion/analysis articles that should be research-only rather than publish candidates.
8. Decide whether BTC miner equity / AI data-center stories should be in the main crypto event stream.
9. Decide whether crypto enforcement/fraud stories should be `hack_security` or a separate `legal_enforcement` L1 type.
10. Inspect protocol incident rows such as Curvance/Echo/eBTC and decide whether `protocol_incident` should stay under `hack_security` or become its own L1 bucket later.
11. Review all time fields using China time as the human-facing standard: `*_china` for review, `*_utc` for API/math. Flag any row where the title/source implies US local time but the CSV time is timezone-naive.
12. Review `source_timezone_assumption=default_china` rows and decide whether source-specific timezone rules should be added to `data/source_timezone_rules.csv`.
13. Check whether `macro` should have a separate TG stream from asset-specific event intelligence.
14. Review whether `other` event_type rows in the backtest are explainable or should be split into new L1/L2 event types.
15. Read `results/v043_stratified_selection_diagnostics.md` and identify whether scarce event types can be improved without relaxing macro/other caps.
16. Read `results/v043_selection_vs_v06_relevance_audit.md` and identify which old v043 selected rows should not be trusted under v0.6 relevance scoring.
17. Read `results/v06_filtered_mature_sample_preview.md` and evaluate whether it is a safer candidate set for a future v0.6-filtered backtest branch.
18. Read `results/v06_filtered_preview_asset_attribution_audit.md` and propose concrete fixes for high-risk asset attribution rows.
19. Read `results/v06_clean_low_risk_preview.md` and use it only as a sanity-check subset, not as statistical evidence.
20. Read `results/v06_asset_attribution_fix_plan.md` and convert obvious fixes into rule/dictionary changes only when they do not change product direction.
21. Read `results/v06_entity_rule_review_packet.md` and propose concrete dictionary/rule changes for Hyperliquid/HYPE, multi-chain regulatory flow, and protocol exploit primary-asset policy. Do not auto-fix Echo/Monad/eBTC rows before direction approval.
22. Read `docs/CLAUDE_DECISION_REVIEW.md`; do not implement pending Claude recommendations until they are accepted into `docs/DECISIONS.md`.

## Completed From Cursor Review

- Added Curvance, RUNE, Polymarket, Tornado Cash, Base, Kevin Warsh, ZachXBT, and Citi to `data/entity_dictionary.csv`.
- Added `tornado cash` to hack/exploit detection.
- Added common Chinese long/short wording to whale-position detection.
- Confirmed `cand_00419` is now `regulation_macro/bitcoin_reserve_policy`, not `hack_security`.
- Confirmed Bitwise HYPE rows now route to `human_review` + `unsupported_research` without fake Binance symbols.
- Added protocol incident soft-signal handling for abnormal/paused protocol market notices.
- Kept `auto_publish` disabled by downgrading high-score rows to `human_review`.
- Standardized human-facing time fields to China time and added time provenance auditing.

## Current Non-Blocking Focus

- Explain why v043 stratified selection only produced 37/50 rows.
- Treat v043 mature50 backtest as a historical baseline until v0.6-filtered sampling is approved.
- Use `data/event_candidates_v06_filtered_mature_review_auto50_preview.csv` only as a preview; do not overwrite v043 backtest outputs.
- Do not run a clean v0.6-filtered backtest until high-risk asset attribution rows are fixed or excluded.
- The current clean low-risk subset has only 18 rows and is too small for event-type conclusions.
- Use `results/v06_asset_attribution_fix_plan.md` as the current asset attribution repair queue.
- Protocol exploit primary-asset policy is unresolved; do not auto-fix Echo/Monad/eBTC rows before Claude/product direction approval.
- Use `results/v06_entity_rule_review_packet.md` as the current entity-policy review queue.
- Use `docs/CLAUDE_DECISION_REVIEW.md` to track Claude advice; only `docs/DECISIONS.md` is implementation authority.
- Improve scarce event-type classification before relaxing macro/other caps.
- Keep `auto_publish` disabled.
- Do not touch TG automation.
- Do not provide trading advice.
