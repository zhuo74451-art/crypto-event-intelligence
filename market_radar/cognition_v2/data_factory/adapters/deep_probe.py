"""Deep probe — inspect actual records from each working adapter."""
from __future__ import annotations

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../.."))

from market_radar.cognition_v2.data_factory.adapters.registry import ADAPTER_REGISTRY


def deep_probe():
    results = {}

    for name in ["sec-edgar", "cisa-alerts", "kraken-status", "nvd-nist", 
                  "binance-public", "coinbase-public", "github-security-advisories"]:
        adapter = ADAPTER_REGISTRY.get(name)
        if not adapter:
            continue

        print(f"\n=== {name} ===")
        try:
            start = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end = datetime(2024, 6, 30, tzinfo=timezone.utc)
            
            records, next_token = adapter.fetch_page(
                source_id=name,
                start_time=start,
                end_time=end,
                page_size=3,
                page_token=None,
            )
            
            print(f"Records: {len(records)}, next_token: {next_token}")
            
            for r in records[:3]:
                print(f"\n  intake_id: {r.intake_id}")
                print(f"  source_url: {r.source_url[:100]}")
                print(f"  retrieved_at: {r.retrieved_at}")
                print(f"  raw_body[:300]: {r.raw_body[:300]}")
                
                # Try to extract timestamps
                if name == "sec-edgar":
                    # SEC EDGAR feeds have <updated> timestamps
                    import re
                    date_m = re.search(r'Date: (.*?)$', r.raw_body, re.MULTILINE)
                    if date_m:
                        print(f"  EXTRACTED_DATE: {date_m.group(1)}")
                
                if name == "nvd-nist":
                    import re
                    pub_m = re.search(r'Published: (.*?)$', r.raw_body, re.MULTILINE)
                    if pub_m:
                        print(f"  EXTRACTED_PUBLISHED: {pub_m.group(1)}")
                
                if name == "cisa-alerts":
                    # CISA records from KEV may not have individual timestamps in raw_body
                    pass
                    
            results[name] = {
                "count": len(records),
                "sample_urls": [r.source_url for r in records[:3]],
                "sample_bodies": [r.raw_body[:200] for r in records[:3]],
            }
            
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {str(e)[:150]}")
            results[name] = {"count": 0, "error": str(e)[:150]}

    return results

if __name__ == "__main__":
    deep_probe()
