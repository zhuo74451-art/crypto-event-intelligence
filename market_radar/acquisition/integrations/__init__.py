from __future__ import annotations

from .changedetection_client_contract import (
    ChangedetectionClientProtocol,
    ChangedetectionWatchContract,
    ChangedetectionEventAdapter,
    FakeChangedetectionClient,
)

from .archivebox_client_contract import (
    ArchiveClientProtocol,
    ArchiveRequest,
    ArchiveReceipt,
    ArchiveFailure,
    FakeArchiveBoxClient,
)

from .apprise_client_contract import (
    NotificationClientProtocol,
    NotificationEnvelope,
    DryRunNotificationClient,
    RedactionHelper,
)

__all__ = [
    # changedetection
    "ChangedetectionClientProtocol",
    "ChangedetectionWatchContract",
    "ChangedetectionEventAdapter",
    "FakeChangedetectionClient",
    # archivebox
    "ArchiveClientProtocol",
    "ArchiveRequest",
    "ArchiveReceipt",
    "ArchiveFailure",
    "FakeArchiveBoxClient",
    # apprise
    "NotificationClientProtocol",
    "NotificationEnvelope",
    "DryRunNotificationClient",
    "RedactionHelper",
]
