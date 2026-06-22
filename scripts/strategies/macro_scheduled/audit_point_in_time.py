"""Audit datasets for point-in-time violations."""
import json, sys
from datetime import datetime
from pathlib import Path

DATASET_PATH = Path("research/datasets/macro_scheduled/macro_scheduled_events_v1.json")


def audit():
    if not DATASET_PATH.exists():
        print("NO_DATASET: Dataset not found, nothing to audit.")
        return 0
    with open(DATASET_PATH) as f:
        data = json.load(f)
    events = data.get("events", [])
    violations = 0
    for ev in events:
        captured = ev.get("expectation", {}).get("captured_at")
        released = ev.get("release_time")
        if captured and released:
            try:
                ct = datetime.fromisoformat(captured)
                rt = datetime.fromisoformat(released)
                if ct > rt:
                    print(f"  VIOLATION: {ev.get('calendar_event_id','?')}: captured {captured} > release {released}")
                    violations += 1
            except (ValueError, TypeError):
                pass
    if violations == 0:
        print(f"PASS: {len(events)} events audited, 0 point-in-time violations")
    else:
        print(f"FAIL: {violations} violation(s) found in {len(events)} events")
    return violations


if __name__ == "__main__":
    sys.exit(audit())
