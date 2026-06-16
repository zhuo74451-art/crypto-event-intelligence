"""Market Radar — Signal Registry (Signal Spine v1).

Persistent storage for Signal objects with deduplication, evidence
appending, confidence updates, status transitions, and history tracking.

Storage priority:
  1. Existing EvidenceLedger patterns (reused for evidence recording)
  2. Local JSON file (stable, readable, no server dependencies)
  3. SQLite (if available)

This registry is NOT a server database — it uses file-based persistence
suitable for one-shot pipeline runs and local development.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from market_radar.shared.models import (
    Observation,
    Signal,
    SignalStatus,
    EvidenceLink,
    NoiseGateResult,
    GateVerdict,
    StatusTransition,
    china_now,
    sha256_short,
    SIGNAL_SPINE_VERSION,
    CardFamily,
    DataSourceType,
)

CN_TZ = timezone(timedelta(hours=8))


class SignalRegistry:
    """Persistent registry for Signal objects.

    Provides CRUD operations, dedup, evidence management, and
    lifecycle transition recording. Uses JSON file for storage.

    Thread-safety: NOT thread-safe. Pipeline is single-threaded.
    """

    def __init__(self, storage_path: Optional[str | Path] = None):
        self._storage_path = Path(storage_path) if storage_path else Path.cwd() / "data" / "signal_registry.json"
        self._signals: dict[str, Signal] = {}
        self._observation_to_signal: dict[str, str] = {}  # obs_id → signal_id
        self._dedup_to_signal: dict[str, str] = {}  # dedup_key → signal_id
        self._loaded = False
        self._dirty = False
        self._load()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load signals from JSON storage."""
        if self._loaded:
            return
        self._loaded = True

        if not self._storage_path.exists():
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            return

        try:
            raw = self._storage_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            for signal_dict in data.get("signals", []):
                signal = self._dict_to_signal(signal_dict)
                self._signals[signal.signal_id] = signal
                # Rebuild indices
                for obs_id in signal.observation_ids:
                    self._observation_to_signal[obs_id] = signal.signal_id
            self._dedup_to_signal = dict(data.get("dedup_map", {}))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If storage is corrupted, start fresh
            self._signals = {}
            self._observation_to_signal = {}
            self._dedup_to_signal = {}
            import warnings
            warnings.warn(f"SignalRegistry: corrupted storage at {self._storage_path}, starting fresh: {e}")

    def save(self) -> None:
        """Persist signals to JSON storage."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "signals": [s.as_dict() for s in self._signals.values()],
            "dedup_map": self._dedup_to_signal,
            "registry_version": SIGNAL_SPINE_VERSION,
            "updated_at": china_now(),
            "signal_count": len(self._signals),
        }
        self._storage_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._dirty = False

    def _signal_to_dict(self, signal: Signal) -> dict:
        return signal.as_dict()

    def _dict_to_signal(self, d: dict) -> Signal:
        """Convert a dict back to a Signal object."""
        # Handle transition_history
        history = []
        for th in d.get("transition_history", []):
            if isinstance(th, dict):
                history.append(StatusTransition(
                    from_status=th["from_status"],
                    to_status=th["to_status"],
                    reason=th.get("reason", ""),
                    timestamp=th.get("timestamp", china_now()),
                    actor=th.get("actor", "unknown"),
                ))

        # Handle evidence
        evidence = []
        for ev in d.get("evidence", []):
            if isinstance(ev, dict):
                evidence.append(EvidenceLink(
                    ref=ev.get("ref", ""),
                    source=ev.get("source", ""),
                    timestamp=ev.get("timestamp", china_now()),
                    description=ev.get("description", ""),
                    ref_type=ev.get("ref_type", "observation"),
                ))

        return Signal(
            signal_id=d["signal_id"],
            title=d.get("title", ""),
            affected_assets=list(d.get("affected_assets", [])),
            event_type=d.get("event_type", "unknown"),
            direction=d.get("direction", "neutral"),
            confidence=float(d.get("confidence", 0.0)),
            trading_relevance=d.get("trading_relevance", "none"),
            news_quality=d.get("news_quality", "unverified"),
            status=d.get("status", SignalStatus.CANDIDATE.value),
            first_seen_at=d.get("first_seen_at", china_now()),
            updated_at=d.get("updated_at", china_now()),
            event_id=d.get("event_id"),
            price_in_state=d.get("price_in_state"),
            confirmation_states=list(d.get("confirmation_states", [])),
            pump_risk=d.get("pump_risk"),
            evidence=evidence,
            observation_ids=list(d.get("observation_ids", [])),
            invalidation_reason=d.get("invalidation_reason"),
            watch_windows=list(d.get("watch_windows", [])),
            renderer_payload=d.get("renderer_payload"),
            transition_history=history,
            card_family=d.get("card_family"),
            source_type=d.get("source_type"),
            pipeline_version=d.get("pipeline_version", SIGNAL_SPINE_VERSION),
        )

    # ── Core CRUD ───────────────────────────────────────────────────────────

    def create_signal(
        self,
        title: str,
        affected_assets: list[str],
        event_type: str,
        direction: str,
        confidence: float,
        observation: Observation,
        gate_results: Optional[list[NoiseGateResult]] = None,
        trading_relevance: str = "medium",
        news_quality: str = "unverified",
        card_family: Optional[CardFamily] = None,
    ) -> Signal:
        """Create a new signal from an observation and gate results.

        Prevents duplicate signal creation: if the observation's dedup_key
        already maps to a signal, returns the existing signal instead.
        """
        # Check for existing signal by dedup_key
        if observation.dedup_key in self._dedup_to_signal:
            existing_id = self._dedup_to_signal[observation.dedup_key]
            existing = self._signals.get(existing_id)
            if existing:
                # Append observation and evidence to existing signal
                self._append_observation_to_signal(existing, observation, gate_results)
                return existing

        # Check for existing signal by observation_id
        if observation.observation_id in self._observation_to_signal:
            existing_id = self._observation_to_signal[observation.observation_id]
            existing = self._signals.get(existing_id)
            if existing:
                return existing

        # Create new signal
        signal_id = str(uuid.uuid4())
        now = china_now()

        # Build evidence from observation
        evidence = list(observation.evidence)

        # Add gate result evidence
        if gate_results:
            for result in gate_results:
                evidence.append(EvidenceLink(
                    ref=sha256_short(f"gate:{result.rule_name}:{result.verdict.value}"),
                    source="deterministic_noise_gate",
                    timestamp=now,
                    description=f"Gate rule '{result.rule_name}': {result.verdict.value} — {result.reason[:100]}",
                    ref_type="observation",
                ))

        # Build renderer payload stub
        renderer_payload = {
            "title": title,
            "signal_id": signal_id,
            "affected_assets": affected_assets,
            "event_type": event_type,
            "direction": direction,
            "confidence": confidence,
            "status": SignalStatus.CANDIDATE.value,
            "first_seen_at": now,
            "pipeline_version": SIGNAL_SPINE_VERSION,
        }

        signal = Signal(
            signal_id=signal_id,
            title=title,
            affected_assets=affected_assets,
            event_type=event_type,
            direction=direction,
            confidence=max(0.0, min(1.0, confidence)),
            trading_relevance=trading_relevance,
            news_quality=news_quality,
            status=SignalStatus.CANDIDATE,
            first_seen_at=now,
            updated_at=now,
            event_id=observation.observation_id[:12],
            evidence=evidence,
            observation_ids=[observation.observation_id],
            card_family=card_family or observation.card_family,
            source_type=observation.source_type,
            renderer_payload=renderer_payload,
        )

        # Record initial transition
        signal.transition_history.append(StatusTransition(
            from_status=SignalStatus.CANDIDATE,
            to_status=SignalStatus.CANDIDATE,
            reason="Signal created from observation",
            timestamp=now,
            actor="orchestrator",
        ))

        self._signals[signal.signal_id] = signal
        self._observation_to_signal[observation.observation_id] = signal.signal_id
        self._dedup_to_signal[observation.dedup_key] = signal.signal_id
        self._dirty = True

        return signal

    def get_signal(self, signal_id: str) -> Optional[Signal]:
        """Retrieve a signal by ID."""
        return self._signals.get(signal_id)

    def get_signal_by_observation(self, observation_id: str) -> Optional[Signal]:
        """Find the signal associated with an observation."""
        signal_id = self._observation_to_signal.get(observation_id)
        if signal_id:
            return self._signals.get(signal_id)
        return None

    def get_signal_by_dedup_key(self, dedup_key: str) -> Optional[Signal]:
        """Find the signal by dedup key."""
        signal_id = self._dedup_to_signal.get(dedup_key)
        if signal_id:
            return self._signals.get(signal_id)
        return None

    def query_signals(
        self,
        status: Optional[SignalStatus | str] = None,
        asset: Optional[str] = None,
        event_type: Optional[str] = None,
        direction: Optional[str] = None,
        min_confidence: float = 0.0,
        max_age_hours: Optional[float] = None,
    ) -> list[Signal]:
        """Query signals by various criteria.

        All filters are optional. Returns matching signals.
        """
        results = list(self._signals.values())

        if status is not None:
            if isinstance(status, str):
                status = SignalStatus(status)
            results = [s for s in results if s.status == status]

        if asset is not None:
            asset_upper = asset.upper()
            results = [
                s for s in results
                if any(a.upper() == asset_upper for a in s.affected_assets)
            ]

        if event_type is not None:
            results = [s for s in results if s.event_type == event_type]

        if direction is not None:
            results = [s for s in results if s.direction == direction]

        if min_confidence > 0.0:
            results = [s for s in results if s.confidence >= min_confidence]

        if max_age_hours is not None:
            from datetime import datetime
            now = datetime.now(CN_TZ)
            filtered = []
            for s in results:
                try:
                    seen = datetime.fromisoformat(s.first_seen_at.replace("Z", "+00:00"))
                    age_h = (now - seen).total_seconds() / 3600
                    if age_h <= max_age_hours:
                        filtered.append(s)
                except (ValueError, TypeError):
                    filtered.append(s)
            results = filtered

        return results

    def all_signals(self) -> list[Signal]:
        """Return all registered signals."""
        return list(self._signals.values())

    # ── Merge & Update ─────────────────────────────────────────────────────

    def _append_observation_to_signal(
        self,
        signal: Signal,
        observation: Observation,
        gate_results: Optional[list[NoiseGateResult]] = None,
    ) -> None:
        """Append new observation data and evidence to an existing signal.

        This is the merge-observation path — does NOT create a new signal.
        """
        now = china_now()

        # Add observation ID if new
        if observation.observation_id not in signal.observation_ids:
            signal.observation_ids.append(observation.observation_id)

        # Add new evidence links (avoiding exact duplicates)
        existing_refs = {e.ref for e in signal.evidence}
        for ev in observation.evidence:
            if ev.ref not in existing_refs:
                signal.evidence.append(ev)
                existing_refs.add(ev.ref)

        # Add gate result evidence
        if gate_results:
            for result in gate_results:
                ref = sha256_short(f"gate:{result.rule_name}:{result.verdict.value}:{now}")
                if ref not in existing_refs:
                    signal.evidence.append(EvidenceLink(
                        ref=ref,
                        source="deterministic_noise_gate",
                        timestamp=now,
                        description=f"Gate rule '{result.rule_name}': {result.verdict.value} (subsequent observation)",
                        ref_type="observation",
                    ))
                    existing_refs.add(ref)

        # Update indices
        self._observation_to_signal[observation.observation_id] = signal.signal_id

        # Update dedup key if new
        if observation.dedup_key not in self._dedup_to_signal:
            self._dedup_to_signal[observation.dedup_key] = signal.signal_id

        signal.updated_at = now
        self._dirty = True

    def append_evidence(self, signal_id: str, evidence: EvidenceLink) -> bool:
        """Append an evidence link to a signal.

        Returns True if found and updated, False if signal not found.
        """
        signal = self._signals.get(signal_id)
        if not signal:
            return False

        signal.evidence.append(evidence)
        signal.updated_at = china_now()
        self._dirty = True
        return True

    def update_confidence(self, signal_id: str, new_confidence: float, reason: str) -> bool:
        """Update a signal's confidence score and record the change.

        Returns True if found and updated, False if signal not found.
        """
        signal = self._signals.get(signal_id)
        if not signal:
            return False

        old_confidence = signal.confidence
        signal.confidence = max(0.0, min(1.0, new_confidence))
        signal.updated_at = china_now()

        # Record as evidence entry
        signal.evidence.append(EvidenceLink(
            ref=sha256_short(f"confidence:{old_confidence}->{new_confidence}:{signal.updated_at}"),
            source="orchestrator",
            timestamp=signal.updated_at,
            description=f"Confidence updated: {old_confidence:.2f} → {new_confidence:.2f}. Reason: {reason[:200]}",
            ref_type="observation",
        ))
        self._dirty = True
        return True

    def transition_status(
        self,
        signal_id: str,
        new_status: SignalStatus,
        reason: str,
        actor: str = "orchestrator",
        invalidation_reason: Optional[str] = None,
    ) -> bool:
        """Transition a signal's lifecycle status.

        Validates the transition before applying. Returns False if
        signal not found. Raises ValueError if transition is illegal.
        """
        signal = self._signals.get(signal_id)
        if not signal:
            return False

        if isinstance(new_status, str):
            new_status = SignalStatus(new_status)

        signal.transition_to(new_status, reason, actor)

        if new_status == SignalStatus.INVALIDATED and invalidation_reason:
            signal.invalidation_reason = invalidation_reason

        signal.updated_at = china_now()
        self._dirty = True
        return True

    def record_invalidation(
        self,
        signal_id: str,
        reason: str,
        invalidation_reason: str,
    ) -> bool:
        """Convenience: transition a signal to invalidated with a reason."""
        return self.transition_status(
            signal_id=signal_id,
            new_status=SignalStatus.INVALIDATED,
            reason=reason,
            actor="orchestrator",
            invalidation_reason=invalidation_reason,
        )

    def get_transition_history(self, signal_id: str) -> list[StatusTransition]:
        """Get the full transition history for a signal."""
        signal = self._signals.get(signal_id)
        if not signal:
            return []
        return list(signal.transition_history)

    # ── Dedup & Query Support ─────────────────────────────────────────────

    def get_dedup_keys(self) -> set[str]:
        """Return all known dedup keys for noise gate synchronization."""
        return set(self._dedup_to_signal.keys())

    def has_observation(self, observation_id: str) -> bool:
        """Check if an observation ID is already registered."""
        return observation_id in self._observation_to_signal

    def has_dedup_key(self, dedup_key: str) -> bool:
        """Check if a dedup key is already known."""
        return dedup_key in self._dedup_to_signal

    def signal_count(self) -> int:
        """Return the total number of registered signals."""
        return len(self._signals)

    def observation_count(self) -> int:
        """Return the number of unique observation→signal mappings."""
        return len(self._observation_to_signal)


def create_signal_registry(storage_path: Optional[str | Path] = None) -> SignalRegistry:
    """Factory: create a SignalRegistry with optional custom storage path."""
    return SignalRegistry(storage_path=storage_path)
