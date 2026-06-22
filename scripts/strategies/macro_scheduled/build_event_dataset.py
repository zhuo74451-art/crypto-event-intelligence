"""Build synthetic event dataset from fixtures."""
import json, sys
from pathlib import Path

FIXTURE_DIR = Path("fixtures/strategies/macro_scheduled")
OUTPUT_DIR = Path("research/datasets/macro_scheduled")
OUTPUT_FILE = OUTPUT_DIR / "macro_scheduled_events_v1.json"

EVENT_FAMILIES = {
    "cpi": {"count": 50, "type": "cpi_headline"},
    "nfp": {"count": 50, "type": "nonfarm_payrolls"},
    "pce": {"count": 35, "type": "core_pce"},
    "fomc": {"count": 40, "type": "fomc_rate_decision"},
}


def build():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events = []
    # Load synthetic fixtures
    if FIXTURE_DIR.exists():
        for f in FIXTURE_DIR.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        events.extend(data)
                    else:
                        events.append(data)
            except (json.JSONDecodeError, IOError):
                pass
    # Count by family
    from collections import Counter
    families = Counter(e.get("release_family", "unknown") for e in events)
    report = {
        "total_events": len(events),
        "by_family": dict(families),
        "synthetic": True,
        "note": "Synthetic dataset for V1 testing. No real market data."
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"events": events, "report": report}, f, indent=2)
    print(f"Dataset: {len(events)} events -> {OUTPUT_FILE}")
    for fam, count in families.most_common():
        print(f"  {fam}: {count}")


if __name__ == "__main__":
    build()
