"""Scheduler configuration model.

APScheduler is NOT started by default.
All APScheduler integrations require explicit user action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# APScheduler pin: 3.11.x LTS
REQUIRED_APSCHEDULER_VERSION = "3.11"


@dataclass
class SchedulerConfig:
    """Configuration for an APScheduler job store.

    All fields safe defaults.
    Scheduler is disabled until explicitly enabled.
    """

    enabled: bool = False
    job_store_type: str = "sqlalchemy"  # sqlalchemy | memory
    job_store_url: Optional[str] = None  # e.g. sqlite:///ops_scheduler.db
    max_instances: int = 1
    coalesce: bool = True
    misfire_grace_time: int = 60
    default_coalesce: bool = True
    timezone: str = "UTC"

    def validate(self) -> list[str]:
        """Validate scheduler configuration.

        Returns violations (empty = valid).
        Scheduler must be disabled by default.
        """
        violations: list[str] = []

        # Default must be disabled
        if self.enabled:
            violations.append("scheduler must be disabled by default (set enabled=False)")

        if self.max_instances != 1:
            violations.append(f"max_instances must be 1, got {self.max_instances}")

        if not self.coalesce:
            violations.append("coalesce must be enabled")

        if self.misfire_grace_time < 0:
            violations.append("misfire_grace_time must be >= 0")

        if self.job_store_type not in ("sqlalchemy", "memory"):
            violations.append(f"unknown job_store_type: {self.job_store_type}")

        return violations


def check_apscheduler_available() -> bool:
    """Check if APScheduler is installed at the required version.

    Uses ``importlib.metadata`` to verify the installed package matches the
    required version.  Returns ``False`` if the package is missing, the
    version doesn't match, or the metadata cannot be read.
    """
    try:
        from importlib.metadata import version as _pkg_version

        installed = _pkg_version("apscheduler")
        return installed.startswith(REQUIRED_APSCHEDULER_VERSION)
    except (ImportError, ModuleNotFoundError, Exception):
        return False
