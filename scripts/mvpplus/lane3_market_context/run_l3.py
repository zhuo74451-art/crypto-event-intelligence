#!/usr/bin/env python3
"""L3 CLI: Run Market Context Provider and output results."""
import sys, json
sys.path.insert(0, ".")
from market_radar.l3_market_context.market_context_provider import run

result = run()
data = {
    "run_id": result.run_id,
    "contexts": [c.as_dict() for c in result.contexts],
    "source_health": [h.as_dict() for h in result.source_health],
    "total_succeeded": result.total_succeeded,
    "total_failed": result.total_failed,
}

print(json.dumps(data, indent=2))
for ctx in result.contexts:
    d = ctx.as_dict()
    print(f"  {d['symbol']:5s} ${d['price']:>8,.2f} 24h:{d.get('price_change_24h_pct')} OI:{d.get('open_interest')} fund:{d.get('funding_rate')}")
sys.exit(0 if result.total_failed == 0 else 1)
