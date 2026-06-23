"""Tests for exact historical values from official release pages V5."""
import json, os

EVENTS = "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"

def load_events():
    if not os.path.exists(EVENTS) or os.path.getsize(EVENTS) == 0: return []
    with open(EVENTS) as f: return [json.loads(l) for l in f if l.strip()]

class TestExactValues:
    def _get(self, family, ref_period):
        for e in load_events():
            if e["event_family"] == family and e["reference_period"] == ref_period: return e
        return None

    def test_jan_2023_core_pce(self):
        e=self._get("us_core_pce","2023-01"); assert e
        assert e["actual_initial"]==0.6; assert e["actual_value_status"]=="verified_initial_from_release"
        assert e["release_time_source_snapshot_id"]; assert e["value_text_anchor"]

    def test_jul_2023_core_pce(self):
        e=self._get("us_core_pce","2023-07"); assert e
        assert e["actual_initial"]==0.2; assert e["actual_value_status"]=="verified_initial_from_release"

    def test_feb_2023_fomc(self):
        e=self._get("us_fomc_rate_decision","2023-02-01"); assert e
        assert e["actual_initial"]==4.625; assert e["actual_value_status"]=="verified_initial_from_release"

    def test_jul_2023_fomc(self):
        e=self._get("us_fomc_rate_decision","2023-07-26"); assert e
        assert e["actual_initial"]==5.375; assert e["actual_value_status"]=="verified_initial_from_release"

class TestSnapshotIntegrity:
    def test_all_events_link_snapshots(self):
        events=load_events(); snap_path="data/intelligence/historical_macro/normalized/macro_source_snapshots_v1.jsonl"
        snaps={}
        if os.path.exists(snap_path) and os.path.getsize(snap_path)>0:
            with open(snap_path) as f:
                for line in f:
                    line=line.strip()
                    if line: s=json.loads(line); snaps[s["snapshot_id"]]=s
        for e in events:
            sid=e.get("release_time_source_snapshot_id","")
            assert sid; assert sid in snaps

    def test_no_placeholder_values(self):
        for e in load_events():
            assert e.get("actual_initial") is not None
            assert e.get("release_time_text_anchor","")
            assert e.get("value_text_anchor","")
            assert e.get("official_document_hash","")
