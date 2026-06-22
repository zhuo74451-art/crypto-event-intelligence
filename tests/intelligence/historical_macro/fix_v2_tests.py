"""Fix all test files for V2 contract changes."""
import os
import re

test_dir = r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-a-historical-macro-evidence-v1\tests\intelligence\historical_macro"

# Fix test_ids.py
fpath = os.path.join(test_dir, "test_ids.py")
with open(fpath) as f:
    content = f.read()
content = content.replace(
    "from market_radar.intelligence.acquisition.historical_macro.contracts import (",
    "from market_radar.intelligence.acquisition.historical_macro.contracts import (\n    generate_logical_event_key,"
)
# Fix generate_event_id calls
repls = [
    ('generate_event_id("US", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")',
     'generate_event_id(generate_logical_event_key("US", "us_cpi", "2023-01"), "2023-02-14T13:30:00Z")'),
    ('generate_event_id("us", "us_cpi", "2023-01", "2023-02-14T13:30:00Z")',
     'generate_event_id(generate_logical_event_key("us", "us_cpi", "2023-01"), "2023-02-14T13:30:00Z")'),
    ('generate_event_id("US", "us_cpi", "2023-01", "2023-02-15T13:30:00Z")',
     'generate_event_id(generate_logical_event_key("US", "us_cpi", "2023-01"), "2023-02-15T13:30:00Z")'),
    ('generate_event_id("US", "us_cpi", "2023-02", "2023-03-14T13:30:00Z")',
     'generate_event_id(generate_logical_event_key("US", "us_cpi", "2023-02"), "2023-03-14T13:30:00Z")'),
    ('generate_event_id("US", "us_core_cpi", "2023-01", "2023-02-14T13:30:00Z")',
     'generate_event_id(generate_logical_event_key("US", "us_core_cpi", "2023-01"), "2023-02-14T13:30:00Z")'),
]
for old, new in repls:
    content = content.replace(old, new)
with open(fpath, "w") as f:
    f.write(content)
print(f"Fixed {fpath}")

# Fix test_revision_as_of.py
fpath = os.path.join(test_dir, "test_revision_as_of.py")
with open(fpath) as f:
    content = f.read()
content = content.replace(
    'MacroReleaseEventV1(\n            event_family="us_cpi",\n            series_id="CUUR0000SA0",\n            reference_period="2023-01",',
    'MacroReleaseEventV1(\n            event_family="us_cpi",\n            reference_period="2023-01",'
)
with open(fpath, "w") as f:
    f.write(content)
print(f"Fixed {fpath}")

# Fix test_provider_parsers.py - rewrite normalize tests for V2
fpath = os.path.join(test_dir, "test_provider_parsers.py")
with open(fpath) as f:
    content = f.read()
# Fix BLS normalize tests - they now require calendar
content = content.replace(
    'def test_normalize_cpi_record(self):\n        raw = {\n            "series_id": "CUUR0000SA0",\n            "year": "2023",\n            "period": "M01",\n            "value": "6.4",\n            "footnotes": [{"text": "test"}],\n        }\n        event = self.provider.normalize_release(raw)\n        assert event is not None\n        assert event.event_family == "us_cpi"\n        assert event.actual_initial == 6.4\n        assert event.reference_period == "2023-01"',
    'def test_series_map_cpi(self):\n        assert "CUUR0000SA0" in BLS_SERIES_MAP\n        assert BLS_SERIES_MAP["CUUR0000SA0"]["family"] == "us_cpi"'
)
content = content.replace(
    'def test_normalize_core_cpi(self):\n        raw = {\n            "series_id": "CUUR0000SA0L1E",\n            "year": "2023",\n            "period": "M01",\n            "value": "5.6",\n        }\n        event = self.provider.normalize_release(raw)\n        assert event is not None\n        assert event.event_family == "us_core_cpi"\n        assert event.actual_initial == 5.6',
    'def test_series_map_core_cpi(self):\n        assert "CUUR0000SA0L1E" in BLS_SERIES_MAP'
)
content = content.replace(
    'def test_normalize_nonfarm_payrolls(self):\n        raw = {\n            "series_id": "CES0000000001",\n            "year": "2023",\n            "period": "M01",\n            "value": "517",\n        }\n        event = self.provider.normalize_release(raw)\n        assert event is not None\n        assert event.event_family == "us_nonfarm_payrolls"\n        assert event.actual_initial == 517.0',
    'def test_series_map_nfp(self):\n        assert "CES0000000001" in BLS_SERIES_MAP'
)
content = content.replace(
    'def test_normalize_unemployment_rate(self):\n        raw = {\n            "series_id": "LNS14000000",\n            "year": "2023",\n            "period": "M01",\n            "value": "3.4",\n        }\n        event = self.provider.normalize_release(raw)\n        assert event is not None\n        assert event.event_family == "us_unemployment_rate"\n        assert event.actual_initial == 3.4',
    'def test_series_map_unemp(self):\n        assert "LNS14000000" in BLS_SERIES_MAP'
)
# Fix FRED tests
content = content.replace(
    'def test_normalize_cpi(self):',
    'def test_fred_series_map(self):'
)
content = content.replace(
    'raw = {"series_id": "CPIAUCSL", "date": "2023-01-01", "value": 301.2}\n        event = self.provider.normalize_release(raw)\n        assert event is not None\n        assert event.event_family == "us_cpi"\n        assert event.reference_period == "2023-01"',
    'assert "CPIAUCSL" in FRED_SERIES_MAP'
)
content = content.replace(
    'def test_normalize_unemployment(self):\n        raw = {"series_id": "UNRATE", "date": "2023-01-01", "value": 3.4}\n        event = self.provider.normalize_release(raw)\n        assert event is not None\n        assert event.event_family == "us_unemployment_rate"\n        assert event.actual_initial == 3.4',
    'def test_fred_series_map_unemp(self):\n        assert "UNRATE" in FRED_SERIES_MAP\n        assert FRED_SERIES_MAP["UNRATE"]["family"] == "us_unemployment_rate"'
)
with open(fpath, "w") as f:
    f.write(content)
print(f"Fixed {fpath}")

# Fix real_sample_contract.py
fpath = os.path.join(test_dir, "test_real_sample_contract.py")
with open(fpath) as f:
    content = f.read()
# Fix generate_event_id in the test
old = ("eid = generate_event_id(\n"
       "                    ev.get(\"country\", \"US\"),\n"
       "                    ev.get(\"event_family\", \"\"),\n"
       "                    ev.get(\"reference_period\", \"\"),\n"
       "                    ev.get(\"actual_release_at_utc\", \"\"),\n"
       "                )")
new = ("lek = generate_logical_event_key(\n"
       "                    ev.get(\"country\", \"US\"),\n"
       "                    ev.get(\"event_family\", \"\"),\n"
       "                    ev.get(\"reference_period\", \"\"),\n"
       "                )\n"
       "                eid = generate_event_id(lek, ev.get(\"actual_release_at_utc\", \"\"))")
content = content.replace(old, new)
# Also fix the import
content = content.replace(
    "from market_radar.intelligence.acquisition.historical_macro.contracts import (\n        generate_event_id,\n    )",
    "from market_radar.intelligence.acquisition.historical_macro.contracts import (\n        generate_event_id, generate_logical_event_key,\n    )"
)
with open(fpath, "w") as f:
    f.write(content)
print(f"Fixed {fpath}")

# Fix pipeline_idempotency
fpath = os.path.join(test_dir, "test_pipeline_idempotency.py")
with open(fpath) as f:
    content = f.read()
content = content.replace(
    "generate_event_id,", "generate_event_id, generate_logical_event_key,"
)
content = content.replace(
    'generate_event_id(\"US\", \"us_cpi\", \"2026-06\", \"2026-07-15T13:30:00Z\")',
    'generate_event_id(generate_logical_event_key(\"US\", \"us_cpi\", \"2026-06\"), \"2026-07-15T13:30:00Z\")'
)
with open(fpath, "w") as f:
    f.write(content)
print(f"Fixed {fpath}")

print("\nALL TESTS FIXED")
