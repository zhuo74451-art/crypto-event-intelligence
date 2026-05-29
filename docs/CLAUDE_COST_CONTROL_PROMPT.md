
You are an external product/architecture reviewer for Crypto Event Intelligence.

We are building a local Web3 event intelligence system. Current data source: exported real news/Telegram/backend fast-news CSV. Future sources: first-party on-chain watchers such as whale wallets, CEX inflows/outflows, project/team wallets, exploit/hacker wallets, stablecoin mint/burn. The system must not provide trading advice or auto-trade.

Current issue:
We used Claude/OpenRouter to review 20 Telegram-style draft events. It worked: 12 approved, 8 rejected. But using Claude on every raw news item and every future on-chain event may be too expensive and slow.

Question:
Design a cost-controlled AI review architecture. Be concrete and critical.

Please answer:
1. Should Claude review every raw event, every draft, only uncertain cases, or only sampled audits?
2. What should be handled by deterministic local rules before any LLM call?
3. What should be handled by cheap/small models vs Claude-level models?
4. How should we batch requests to reduce cost without losing quality?
5. What thresholds should route events to: auto_discard, local_rule_publish_candidate, small_model_review, Claude_review, human/audit?
6. How should the architecture change when on-chain watchers are added?
7. Give a practical first-version cost policy for 1k, 10k, and 100k events/day.
8. What metrics should we track to know AI spend is justified?

Return direct recommendations, not generic AI advice.
