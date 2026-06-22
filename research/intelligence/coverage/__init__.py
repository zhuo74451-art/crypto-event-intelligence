"""Research Intelligence coverage package."""

from research.intelligence.coverage.domain_catalog import build_domain_catalog

# CoverageEvaluator is a stub — will be implemented in a future iteration.
# It is imported here so callers can rely on the package-level export.

class CoverageEvaluator:
    """Evaluates research coverage across domains.

    This is a placeholder that will be expanded in a future iteration.
    """
    def evaluate(self) -> dict[str, object]:
        """Return a stub evaluation result."""
        return {"status": "not_yet_implemented"}


__all__ = ["CoverageEvaluator", "build_domain_catalog"]
