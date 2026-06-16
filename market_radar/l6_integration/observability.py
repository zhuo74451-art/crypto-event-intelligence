"""MVP+ L6 — Observability / Run Logger.

Records structured observability per run:
  - run_id, start/end, duration
  - per-source success/failure counts
  - record counts by type
  - fresh/cached/fixture classification
  - retry counts
  - degraded sources
  - final decision (status)

Secret redaction: all outputs are sha256-proofs or safe summaries.
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_short(text: str, n: int = 8) -> str:
    return "sha256:" + hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:n * 2]


def redact_safe(value: Any) -> str:
    """Redact sensitive values to safe hashes.

    Redacts: addresses starting with 0x, tokens, keys, secrets.
    """
    s = str(value)
    if s.startswith("0x") and len(s) >= 20:
        return f"0x...{s[-6:]}"
    if any(kw in s.lower() for kw in ("key", "secret", "token", "password", "cred")):
        return sha256_short(s)
    return s


@dataclass
class RunObservation:
    """Observability record for a single runner execution."""
    run_id: str
    started_at: str
    completed_at: str = ""
    duration_s: Optional[float] = None

    # Status
    status: str = "running"  # running | completed | degraded | failed

    # Per-source counts
    source_results: dict[str, dict] = field(default_factory=dict)

    # Record counts
    record_counts: dict[str, int] = field(default_factory=dict)

    # Classification
    fresh_count: int = 0
    cached_count: int = 0
    fixture_count: int = 0
    degraded_count: int = 0

    # Retry
    retry_counts: dict[str, int] = field(default_factory=dict)

    # Degraded sources
    degraded_sources: list[str] = field(default_factory=list)

    # Final decision
    final_decision: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def complete(self, status: str, decision: str = ""):
        now = _utc_now()
        self.completed_at = now
        self.status = status
        self.final_decision = decision
        try:
            start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(now.replace("Z", "+00:00"))
            self.duration_s = (end - start).total_seconds()
        except (ValueError, TypeError):
            pass

    def record_source(self, source_name: str, ok: bool, count: int = 0,
                      retries: int = 0, degraded: bool = False):
        self.source_results[source_name] = {
            "ok": ok,
            "count": count,
            "retries": retries,
            "degraded": degraded,
        }
        if retries > 0:
            self.retry_counts[source_name] = retries
        if degraded:
            if source_name not in self.degraded_sources:
                self.degraded_sources.append(source_name)

    def as_dict(self, redact: bool = True) -> dict:
        d = asdict(self)
        if redact:
            for src in d.get("source_results", {}):
                d["source_results"][src] = redact_safe(d["source_results"][src])
        return d


class RunLogger:
    """Persists observability records to JSON files in logs/ directory."""

    def __init__(self, logs_dir: str = "artifacts/logs"):
        self.logs_dir = logs_dir
        self._current: Optional[RunObservation] = None

    def start_run(self, run_id: str) -> RunObservation:
        obs = RunObservation(run_id=run_id, started_at=_utc_now())
        self._current = obs
        return obs

    def complete_run(self, status: str, decision: str = ""):
        if self._current:
            self._current.complete(status, decision)

    def save(self):
        if not self._current:
            return
        os.makedirs(self.logs_dir, exist_ok=True)
        path = os.path.join(self.logs_dir, f"run_{self._current.run_id}.json")
        # Atomic write via tmp
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._current.as_dict(redact=True), f, indent=2, default=str)
        os.replace(tmp, path)
        return path

    @property
    def current(self) -> Optional[RunObservation]:
        return self._current
