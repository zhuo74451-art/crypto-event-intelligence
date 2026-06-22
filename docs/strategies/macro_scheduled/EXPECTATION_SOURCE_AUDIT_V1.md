# EXPECTATION SOURCE AUDIT V1

## Key Finding
No free source provides reliable point-in-time historical consensus data.

## Usable Sources
- BLS: Official CPI/NFP actuals (public domain)
- BEA: Official PCE actuals (public domain)
- FRED: Economic data (free API)
- Federal Reserve: FOMC decisions and statements

## Rejected Sources
- Bloomberg, Reuters: Paid subscription
- Investing.com: Silent consensus revision risk

## Consequence
When expectation unavailable, V1 must output INSUFFICIENT_EXPECTATION.
