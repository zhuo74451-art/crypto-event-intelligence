from __future__ import annotations

from .base import BaseAcquisitionAdapter, AcquisitionAdapterResult
from .rss import RssAdapter
from .sec_edgar import SecEdgarAdapter
from .federal_register import FederalRegisterAdapter
from .federal_reserve import FederalReserveAdapter
from .github_releases import GitHubReleasesAdapter
from .github_security_advisories import GitHubSecurityAdvisoriesAdapter
from .static_html import StaticHtmlAdapter

__all__ = [
    "BaseAcquisitionAdapter",
    "AcquisitionAdapterResult",
    "RssAdapter",
    "SecEdgarAdapter",
    "FederalRegisterAdapter",
    "FederalReserveAdapter",
    "GitHubReleasesAdapter",
    "GitHubSecurityAdvisoriesAdapter",
    "StaticHtmlAdapter",
]
