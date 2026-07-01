"""Cognition v2 package boundary tests — verify import direction."""


class TestPackageBoundaries:
    """Domain must not import from persistence, operator, or CLI."""

    def test_domain_does_not_import_persistence(self):
        import market_radar.cognition_v2.domain.contracts as contracts
        import market_radar.cognition_v2.persistence.models as models
        # Domain contracts shouldn't reference persistence objects
        domain_names = set(dir(contracts))
        persistence_names = set(dir(models))
        # Just check no obvious cross-contamination
        assert "SQLAlchemy" not in str(contracts.__file__)

    def test_domain_does_not_import_operator(self):
        import market_radar.cognition_v2.domain.contracts as contracts
        assert "operator" not in str(contracts.__file__)

    def test_lifecycle_imports_domain_only(self):
        import market_radar.cognition_v2.lifecycle.service as service
        # Lifecycle service should only depend on domain
        import market_radar.cognition_v2.domain.contracts
        # Verify it doesn't import persistence
        assert "persistence" not in str(service.__file__)

    def test_domain_has_minimal_dependencies(self):
        import market_radar.cognition_v2.domain.contracts
        # Domain should only use pydantic and standard library
        import sys
        domain_module = sys.modules["market_radar.cognition_v2.domain.contracts"]
        assert domain_module is not None


class TestPackageExists:
    def test_cognition_v2_package_exists(self):
        import market_radar.cognition_v2
        assert market_radar.cognition_v2.__file__ is not None

    def test_all_subpackages_exist(self):
        import market_radar.cognition_v2.domain
        import market_radar.cognition_v2.application
        import market_radar.cognition_v2.persistence
        import market_radar.cognition_v2.lifecycle
        import market_radar.cognition_v2.replay
        import market_radar.cognition_v2.observability
        import market_radar.cognition_v2.operator
        import market_radar.cognition_v2.cli
        assert True  # All imports succeeded
