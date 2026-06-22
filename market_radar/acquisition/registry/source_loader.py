from __future__ import annotations

import os
from typing import Any

from ..contracts.source import SourceContract


class SourceLoader:
    """Loads SourceContract instances from YAML files or dicts."""

    @staticmethod
    def load_from_yaml(path: str) -> list[SourceContract]:
        """Read a YAML file and parse each source entry into a SourceContract."""
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "PyYAML is required to load YAML sources. "
                "Install it with: pip install PyYAML"
            )

        with open(path, "r", encoding="utf-8") as fh:
            data: Any = yaml.safe_load(fh)

        if not isinstance(data, list):
            raise ValueError(f"Expected a list of source dicts in YAML file, got {type(data).__name__}")

        return SourceLoader.load_from_dicts(data)

    @staticmethod
    def load_default_registry() -> list[SourceContract]:
        """Load sources from the bundled default_sources.yaml file.

        Searches relative to this file's directory, then from the project
        root relative path market_radar/acquisition/registry/default_sources.yaml.
        """
        candidates: list[str] = []

        # Relative to this file's directory
        this_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(this_dir, "default_sources.yaml"))

        # Also try from a potential project root (two levels up from registry)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(this_dir)))
        candidates.append(
            os.path.join(
                project_root,
                "market_radar",
                "acquisition",
                "registry",
                "default_sources.yaml",
            )
        )

        # Try additional common location: one level up from registry into acquisition
        candidates.append(
            os.path.join(os.path.dirname(this_dir), "registry", "default_sources.yaml")
        )

        for candidate in candidates:
            if os.path.isfile(candidate):
                return SourceLoader.load_from_yaml(candidate)

        raise FileNotFoundError(
            f"default_sources.yaml not found. Tried: {candidates}"
        )

    @staticmethod
    def load_from_dicts(dicts: list[dict]) -> list[SourceContract]:
        """Parse a list of dictionaries into SourceContract instances."""
        return [SourceContract.from_dict(d) for d in dicts]
