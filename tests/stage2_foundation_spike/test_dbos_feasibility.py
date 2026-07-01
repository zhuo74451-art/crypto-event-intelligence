"""Test the dbos_feasibility module."""

from experiments.stage2_foundation_spike.dbos_feasibility import (
    DBOS_REQUIRES_POSTGRES_AUTHORIZATION,
    get_classification,
    comparison,
)


def test_get_classification_returns_dict_with_version():
    c = get_classification()
    assert isinstance(c, dict)
    assert "version" in c


def test_requires_postgres_is_true():
    c = get_classification()
    assert c.get("requires_postgres") is True


def test_classification_is_dbos_requires_postgres_authorization():
    assert "Postgres" in DBOS_REQUIRES_POSTGRES_AUTHORIZATION


def test_comparison_returns_dict():
    comp = comparison()
    assert isinstance(comp, dict)
    assert len(comp) > 0
