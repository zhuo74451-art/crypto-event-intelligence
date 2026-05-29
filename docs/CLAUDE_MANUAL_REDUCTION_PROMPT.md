# Claude Manual Reduction Prompt

You are acting as a strict Web3-native AI PM/architect.
Do not be polite or generic. Give concrete decisions.

Project: Crypto Event Intelligence (local CSV/SQLite/Python only)

Current state snapshot:
- labeled_rows: 201
- unlabeled_rows: 0
- label_coverage_pct: 100.0
- manual_review_required_rows: 59
- auto_publish: disabled

Hard boundaries:
- No Notion
- No trading integration
- No web app
- No buy/sell/long/short advice

Core question:
We want a Web3-aware AI system, not a human-heavy pipeline.
For each manual-heavy step, decide whether it should remain manual or be automated by AI.

Please output:
1. A hard yes/no decision table for these steps:
   - candidate classification
   - asset attribution
   - event taxonomy
   - timezone/source normalization checks
   - low-risk discard confirmation
   - publish-review approval
2. For each step marked "AI", define:
   - minimum confidence rule
   - mandatory audit sample size
   - rollback trigger
3. A 2-phase migration plan from manual-heavy to AI-heavy:
   - Phase A (this week)
   - Phase B (next 2-4 weeks)
4. The top 5 failure modes specific to Web3 news/event intelligence.
5. The exact gate to allow first TG draft pilot without reintroducing heavy manual review.
