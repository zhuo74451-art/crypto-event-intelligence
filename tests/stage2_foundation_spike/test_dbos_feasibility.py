"""Test DBOS feasibility classification."""

from experiments.stage2_foundation_spike.dbos_feasibility import (
    DBOS_CLASSIFICATION,
    DBOS_REQUIRES_POSTGRES,
    DBOS_VERSION,
    get_classification,
    comparison,
)


def test_classification_requires_postgres():
    assert DBOS_REQUIRES_POSTGRES is True


def test_classification_constant():
    assert DBOS_CLASSIFICATION == "DBOS_REQUIRES_POSTGRES_AUTHORIZATION"


def test_get_classification_returns_version():
    c = get_classification()
    assert c["version"] == DBOS_VERSION
    assert c["classification"] == DBOS_CLASSIFICATION


def test_comparison_includes_all_dimensions():
    comp = comparison()
    expected_dims = {"guarantees", "custom_code_requirements", "services_required", "status_stop_recovery", "testability", "owner_burden"}
    assert expected_dims.issubset(comp.keys())
    for dim, sides in comp.items():
        assert "DBOS" in sides
        assert "minimal_runtime" in sides
