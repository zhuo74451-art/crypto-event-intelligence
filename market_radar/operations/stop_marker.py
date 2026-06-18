"""Stop marker support.

A stop marker is a file whose presence signals a running operation
to stop at the next safe checkpoint.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class StopMarker:
    """File-based stop marker for graceful operation termination."""

    def __init__(self, marker_path: str | Path):
        self._path = Path(marker_path)

    def set(self) -> None:
        """Create the stop marker."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("stop", encoding="utf-8")

    def clear(self) -> None:
        """Remove the stop marker."""
        try:
            if self._path.exists():
                os.unlink(self._path)
        except OSError:
            pass

    @property
    def is_set(self) -> bool:
        return self._path.exists()

    def check(self) -> bool:
        """Check and return True if stop requested."""
        return self.is_set
