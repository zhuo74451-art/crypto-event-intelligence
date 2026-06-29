"""Shared fixtures for acquisition tests."""
import pytest
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "acquisition"


@pytest.fixture
def sec_sample_bytes():
    path = FIXTURE_DIR / "sec_press_releases_sample.xml"
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def cisa_sample_bytes():
    path = FIXTURE_DIR / "cisa_kev_sample.json"
    with open(path, "rb") as f:
        return f.read()
