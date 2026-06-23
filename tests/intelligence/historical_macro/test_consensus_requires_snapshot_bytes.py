"""Test: consensus requires exact article URL with snapshot proof, not generic homepages."""
import json
import os

CONSENSUS_PATH = "data/intelligence/historical_macro/normalized/macro_consensus_observations_v1.jsonl"

GENERIC_PATTERNS = [
    ".com/economy/",
    ".com/markets/",
    "forexfactory.com/calendar",
    "bloomberg.com/economics",
    "reuters.com/economy",
    "wsj.com/economy",
    "cnbc.com/economy",
]


class TestConsensusRequiresSnapshotBytes:
    def test_no_generic_media_homepages(self):
        if not os.path.exists(CONSENSUS_PATH) or os.path.getsize(CONSENSUS_PATH) == 0:
            return
        with open(CONSENSUS_PATH) as f:
            obs = [json.loads(l) for l in f if l.strip()]
        bad = []
        for o in obs:
            url = o.get("source_url", "")
            if any(p in url for p in GENERIC_PATTERNS):
                bad.append(o.get("consensus_observation_id", ""))
        assert len(bad) == 0, f"{len(bad)} generic homepage URLs in consensus: {bad[:3]}"

    def test_each_consensus_has_content_hash(self):
        if not os.path.exists(CONSENSUS_PATH) or os.path.getsize(CONSENSUS_PATH) == 0:
            return
        with open(CONSENSUS_PATH) as f:
            obs = [json.loads(l) for l in f if l.strip()]
        missing = [o.get("consensus_observation_id", "") for o in obs if not o.get("content_hash")]
        assert len(missing) == 0, f"{len(missing)} consensus without content_hash"

    def test_each_consensus_published_before_release(self):
        if not os.path.exists(CONSENSUS_PATH) or os.path.getsize(CONSENSUS_PATH) == 0:
            return
        from market_radar.intelligence.acquisition.historical_macro.contracts import utc_parse
        ev_path = "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"
        events = {}
        if os.path.exists(ev_path) and os.path.getsize(ev_path) > 0:
            with open(ev_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    e = json.loads(line)
                    events[e["event_id"]] = e.get("actual_release_at_utc", "")
        with open(CONSENSUS_PATH) as f:
            obs = [json.loads(l) for l in f if l.strip()]
        post = []
        for o in obs:
            eid = o.get("event_id", "")
            pub = o.get("published_at_utc", "")
            release = events.get(eid, "")
            if pub and release:
                try:
                    if utc_parse(pub) >= utc_parse(release):
                        post.append(o.get("consensus_observation_id", ""))
                except (ValueError, TypeError):
                    post.append(o.get("consensus_observation_id", ""))
        assert len(post) == 0, f"{len(post)} post-release consensus in formal dataset"
