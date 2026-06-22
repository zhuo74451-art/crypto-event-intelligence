import pytest, json, os, sys
from datetime import datetime, timezone
from market_radar.acquisition.contracts import *
from market_radar.acquisition.contracts.timestamps import utc_now, FiveTimestamps, TimestampEvidence, TimestampQuality

@pytest.fixture
def sample_timestamps():
    now = utc_now()
    return FiveTimestamps(
        published_at=TimestampEvidence(now, TimestampQuality.EXPLICIT_SOURCE),
        effective_at=TimestampEvidence(now, TimestampQuality.INFERRED_FROM_CONTENT),
        first_seen_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
        retrieved_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
    )

@pytest.fixture
def sample_source_contract():
    return SourceContract(
        source_id="test-source", source_name="Test Source",
        authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
        roles=(SourceRole.AUTHORITATIVE_EVIDENCE,),
        primary_method="http_json_api", enabled=True,
    )
