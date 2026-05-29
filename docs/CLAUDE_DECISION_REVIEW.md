# Claude Decision Review

Last updated: 2026-05-29 12:52:20 UTC+8

This queue extracts possible decision/action items from Claude responses. It is a review aid only.

Rules:

- `pending` means not accepted.
- `accepted` requires a matching entry in `docs/DECISIONS.md`.
- `implementation_status=done` requires code/docs/tests to prove the change.
- Do not implement direction-level recommendations directly from this queue.

## Status Counts

| decision_status | count |
|---|---:|
| pending | 778 |

## Scope Counts

| suggested_scope | count |
|---|---:|
| unknown | 391 |
| tg | 111 |
| asset_attribution | 81 |
| qa | 61 |
| data | 57 |
| product | 30 |
| macro_policy | 17 |
| taxonomy | 15 |
| backtest | 15 |

## Pending Preview

| item_id | scope | source | recommendation |
|---|---|---|---|
| `claude_543ac47df43a43a2` | unknown | `results\claude_cost_control_response.md` | **Recommendation: Only uncertain cases after multi-stage filtering** |
| `claude_8270357b7b993ab4` | unknown | `results\claude_cost_control_response.md` | **Must implement before any AI call:** |
| `claude_eb8b4a4727559d57` | macro_policy | `results\claude_cost_control_response.md` | Non-English without translation (if English-only policy) |
| `claude_80c57432ef4b80b7` | unknown | `results\claude_cost_control_response.md` | **Simple binary decisions**: "Does this mention a specific exploit?" "Is this about a token listing?" |
| `claude_13d077fb61555791` | unknown | `results\claude_cost_control_response.md` | **Critical insight:** Small models are 90% as good for structured tasks, 60% as good for judgment calls. Route accordingly. |
| `claude_05babe6363176b24` | unknown | `results\claude_cost_control_response.md` | **Do NOT batch time-sensitive events** (large exploits, major transfers) |
| `claude_e1c146e0117882c3` | unknown | `results\claude_cost_control_response.md` | Separate fast-track queue for high-value events (>$1M, known hacker wallets) |
| `claude_f476a21fabb428c8` | unknown | `results\claude_cost_control_response.md` | Don't batch >200 events - quality degrades, timeouts increase |
| `claude_55cef8ccf8607922` | unknown | `results\claude_cost_control_response.md` | Don't batch mixed languages - context confusion |
| `claude_e177322f836e2d4b` | unknown | `results\claude_cost_control_response.md` | Don't delay critical events for batch efficiency |
| `claude_305f22481a51a8cb` | unknown | `results\claude_cost_control_response.md` | Queue 1 (real-time): High-priority events → immediate small model → Claude if needed |
| `claude_7e5bb4d312104575` | unknown | `results\claude_cost_control_response.md` | └─> Claude Decision |
| `claude_fa195a41d602688f` | tg | `results\claude_cost_control_response.md` | **Volume explosion**: 100x more events than Telegram (every block has transactions) |
| `claude_dcb87e841ec89911` | unknown | `results\claude_cost_control_response.md` | **Structured data**: On-chain events are machine-readable (no NLP needed for extraction) |
| `claude_3e84b940aef26350` | unknown | `results\claude_cost_control_response.md` | **Real-time expectations**: Exploit detection must be <1 min latency |
| `claude_a01fa78835f7f75f` | unknown | `results\claude_cost_control_response.md` | **High signal variance**: 99.9% of transactions are routine, 0.1% are critical |
| `claude_fd4790d0ad68770e` | unknown | `results\claude_cost_control_response.md` | └─> Anomaly Detection: Statistical outliers → PRIORITY_REVIEW |
| `claude_a50016486efbd203` | unknown | `results\claude_cost_control_response.md` | Ambiguous multi-step transactions requiring reasoning |
| `claude_d71519fd121aa6ac` | unknown | `results\claude_cost_control_response.md` | **Critical change:** On-chain watchers should generate **structured alerts**, not raw events. LLMs review alerts, not transactions. |
| `claude_1cd1a8ec3f260947` | tg | `results\claude_cost_control_response.md` | **Cost impact:** With proper filtering, on-chain events should cost LESS per published alert than Telegram scraping (more structured, less noise). |
| `claude_5bb1c9458e70ddb2` | unknown | `results\claude_cost_control_response.md` | Should decrease over time as rules improve |
| `claude_6f8d4dceb9dcabb4` | unknown | `results\claude_cost_control_response.md` | **Human override rate**: % of AI decisions reversed by humans |
| `claude_09385dca5f8eb3e7` | unknown | `results\claude_cost_control_response.md` | **Don't overthink it. Start here:** |
| `claude_b9614cecb40803bc` | unknown | `results\claude_cost_control_response.md` | **Route remainder to Claude** with confidence scoring prompt - 1 day |
| `claude_d58dee70a18d2a86` | qa | `results\claude_next_response_20260527_163346.md` | **Product direction**: Fundamentally sound, but you're over-engineering the quality gates before proving the core value hypothesis. |
