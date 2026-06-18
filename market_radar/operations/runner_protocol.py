"""Generic RunnerProtocol with callable injection.

Defines the contract for runnable operations tasks.
No business domain coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol


class RunnerProtocol(Protocol):
    """Protocol that any runnable operation must satisfy."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute one operation cycle.

        Args:
            context: Run context with keys like 'run_id', 'config', 'state'.

        Returns:
            Result dict with at least a 'status' key ('ok' | 'failed' | 'stopped').
        """
        ...


@dataclass
class InjectedRunner:
    """Wraps a callable so it conforms to RunnerProtocol via injection."""

    label: str
    fn: Callable[[dict[str, Any]], dict[str, Any]]

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.fn(context)
        except Exception as e:
            return {"status": "failed", "error": f"{type(e).__name__}: {e}"}


@dataclass
class RunResult:
    """Standard ops run result."""
    run_id: str
    runner_label: str
    status: str  # 'ok' | 'failed' | 'stopped'
    summary: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
