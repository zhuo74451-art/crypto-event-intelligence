# Claude Question Backlog

We collect architecture/product questions here. When the list reaches 20 substantial questions, ask Claude in one batch.

## Current Count: 0 / 20

| # | Area | Question | Status |
|---:|---|---|---|
| 1 | Product | Should TG publishing start with only `auto_publish`, or should `human_review` rows be manually approved into the group from day one? | asked:20260527_163625 |
| 2 | Data | Should market-wide macro/regulation events be published in the same TG stream as single-asset events, or separated into a different section/feed? | asked:20260527_163625 |
| 3 | Benchmark | What is the best practical benchmark for BTC and ETH events before a market basket/TOTAL3 source is available? | asked:20260527_163625 |
| 4 | Product | Should crypto payment/card/adoption stories such as Revolut crypto card be publishable, or should they remain research-only unless tied to a tradable asset? | asked:20260527_163625 |
| 5 | Data | Should unsupported but relevant assets such as HYPE/ONDO/WLD be allowed into publish review even when Binance symbols are missing? | asked:20260527_163625 |
| 6 | Product | Should opinion/analysis pieces from analysts or KOLs ever be publish candidates, or should v0.6 only allow concrete factual events? | asked:20260527_163625 |
| 7 | Data | How aggressive should we be in discarding scraped long-form articles where footer/navigation text pollutes entity extraction? | asked:20260527_163625 |
| 8 | Product | Should BTC miner equity / AI data-center stories be part of the crypto event stream, or separated from token/chain events? | asked:20260527_163625 |
| 9 | Taxonomy | Should enforcement/fraud/Ponzi/legal crime stories be under `hack_security`, `regulation_macro`, or a new `legal_enforcement` L1 type? | asked:20260527_163625 |
| 10 | Product | What should be the minimum standard for `auto_publish` so that the first TG version is useful but does not flood the group with low-confidence events? | asked:20260527_163625 |
| 11 | Ground Truth | How should we obtain ground truth for publish quality: who labels it, what fields are labeled, and how many examples are enough before auto_publish? | asked:20260527_163625 |
| 12 | Ground Truth | With AI provisional labels enabled, what minimum human audit sampling rate is acceptable per batch (for example 20%, 30%, or fixed 10 rows)? | asked:20260527_163625 |
| 13 | Product | Should high-confidence `discard` labels be accepted directly for production filtering, or always require periodic manual overturn checks? | asked:20260527_163625 |
| 14 | QA | Which override policy is better when human review conflicts with AI label: immediate rule update, dictionary update, or deferred batch retraining logic? | asked:20260527_163625 |
| 15 | Ops | Should the v0.6 pipeline block TG draft generation when `manual_review_required_rows_after_run` exceeds a threshold (for example 50)? | asked:20260527_163625 |
| 16 | QA | For `auto_closed_low_risk` rows, what is the minimum required audit pass-rate before they can be trusted in production (for example 90%, 95%, or 98%)? | asked:20260527_163625 |
| 17 | Taxonomy | Should `other_review` remain a sink bucket, or be split into 2-3 explicit classes (`non_crypto`, `weak_relevance`, `insufficient_entity`) to reduce rule ambiguity? | asked:20260527_163625 |
| 18 | Product | Should `research_only` rows ever be promoted to publish candidates after repeated confirmations, or permanently remain outside the publish stream? | asked:20260527_163625 |
| 19 | Data | Should we maintain a source-level reliability score and downweight noisy sources before classification, instead of relying only on row-level rules? | asked:20260527_163625 |
| 20 | Ops | What should be the hard release gate for first TG draft pilot: labeled coverage, manual review backlog, and audit sample pass criteria combined? | asked:20260527_163625 |

## Add Questions Here

Use this format:

```text
| N | Area | Question | open |
```

Do not ask Claude again until we have 20 meaningful architecture or product questions.

| 1 | Data | The older500 replay set is dominated by BTC/macro and has only 1 mature non-BTC single-asset usable sample; should we expand historical export by source/time window, add targeted asset queries, or prioritize first-hand watcher history instead? | asked:v08_claude_user_view_project_review |
| 2 | Benchmark | For BTC-heavy historical replay, is abnormal_vs_eth an acceptable interim benchmark, or should we build a basket benchmark such as TOTAL3/alt basket before reading event_type performance? | asked:v08_claude_user_view_project_review |

## Consultation History

| asked_at | batch_id | question_count | response |
|---|---|---:|---|
| 2026-05-27 16:47:53 UTC+8 | 20260527_163625 | 20 | results\claude_next_response_20260527_163625.md |
| 2026-05-28 12:24:02 UTC+8 | v08_claude_user_view_project_review | 2 | results\v08_claude_user_view_project_review.md |
