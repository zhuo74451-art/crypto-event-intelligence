"""
Baseline models for validation comparison.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Optional

from ..contracts.prediction import PredictionRecord, PredictionSet
from ..contracts.common import Direction, ConfidenceType


class NeutralBaseline:
    """Always predicts no clear direction (flat/unknown)."""

    def predict(
        self,
        events: list[dict[str, Any]],
        as_of_time: datetime,
        fold_id: str = "",
        experiment_id: str = "",
    ) -> PredictionSet:
        predictions = []
        for event in events:
            predictions.append(PredictionRecord(
                prediction_id=f"neutral_{event.get('event_id', '')}",
                experiment_id=experiment_id,
                event_id=event.get("event_id", ""),
                as_of_time=as_of_time,
                horizon=event.get("horizon", "24h"),
                predicted_direction=Direction.UNKNOWN.value,
                confidence_score=0.0,
                confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
                model_id="B1_neutral",
                fold_id=fold_id,
                is_abstained=False,
            ))
        return PredictionSet(
            model_id="B1_neutral",
            experiment_id=experiment_id,
            predictions=predictions,
        )


class RandomBaseline:
    """Predicts with fixed probabilities from training distribution."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._prob_up: float = 0.33
        self._prob_down: float = 0.33
        self._prob_flat: float = 0.34
        self._rng = random.Random(seed)

    def fit(self, train_directions: list[str]) -> None:
        """Fit to training distribution."""
        if not train_directions:
            return
        total = len(train_directions)
        self._prob_up = train_directions.count(Direction.UP.value) / total if train_directions else 0.33
        self._prob_down = train_directions.count(Direction.DOWN.value) / total if train_directions else 0.33
        self._prob_flat = train_directions.count(Direction.FLAT.value) / total if train_directions else 0.34

    def predict(
        self,
        events: list[dict[str, Any]],
        as_of_time: datetime,
        fold_id: str = "",
        experiment_id: str = "",
    ) -> PredictionSet:
        self._rng = random.Random(self.seed)
        predictions = []
        for event in events:
            r = self._rng.random()
            if r < self._prob_up:
                direction = Direction.UP.value
                score = self._prob_up
            elif r < self._prob_up + self._prob_down:
                direction = Direction.DOWN.value
                score = self._prob_down
            else:
                direction = Direction.FLAT.value
                score = self._prob_flat

            predictions.append(PredictionRecord(
                prediction_id=f"random_{event.get('event_id', '')}",
                experiment_id=experiment_id,
                event_id=event.get("event_id", ""),
                as_of_time=as_of_time,
                horizon=event.get("horizon", "24h"),
                predicted_direction=direction,
                confidence_score=score,
                confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
                model_id="B2_random",
                fold_id=fold_id,
                is_abstained=False,
            ))
        return PredictionSet(
            model_id="B2_random",
            experiment_id=experiment_id,
            predictions=predictions,
        )


class EventTypePriorBaseline:
    """Uses historical distribution of event type outcomes."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._type_probs: dict[str, dict[str, float]] = {}

    def fit(self, event_types: list[str], directions: list[str]) -> None:
        """Fit per-type direction probabilities."""
        from collections import Counter

        type_dirs: dict[str, list[str]] = {}
        for et, d in zip(event_types, directions):
            if et not in type_dirs:
                type_dirs[et] = []
            type_dirs[et].append(d)

        for et, dirs in type_dirs.items():
            total = len(dirs)
            self._type_probs[et] = {
                Direction.UP.value: dirs.count(Direction.UP.value) / total,
                Direction.DOWN.value: dirs.count(Direction.DOWN.value) / total,
                Direction.FLAT.value: dirs.count(Direction.FLAT.value) / total,
            }

    def predict(
        self,
        events: list[dict[str, Any]],
        as_of_time: datetime,
        fold_id: str = "",
        experiment_id: str = "",
    ) -> PredictionSet:
        import random

        rng = random.Random(self.seed)
        predictions = []
        for event in enumerate(events):
            pass

        for event in events:
            event_type = event.get("event_type", "unknown")
            probs = self._type_probs.get(event_type, {
                Direction.UP.value: 0.33,
                Direction.DOWN.value: 0.33,
                Direction.FLAT.value: 0.34,
            })
            r = rng.random()
            if r < probs[Direction.UP.value]:
                direction = Direction.UP.value
                score = probs[Direction.UP.value]
            elif r < probs[Direction.UP.value] + probs[Direction.DOWN.value]:
                direction = Direction.DOWN.value
                score = probs[Direction.DOWN.value]
            else:
                direction = Direction.FLAT.value
                score = probs[Direction.FLAT.value]

            predictions.append(PredictionRecord(
                prediction_id=f"event_prior_{event.get('event_id', '')}",
                experiment_id=experiment_id,
                event_id=event.get("event_id", ""),
                as_of_time=as_of_time,
                horizon=event.get("horizon", "24h"),
                predicted_direction=direction,
                confidence_score=score,
                confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
                model_id="B3_event_prior",
                fold_id=fold_id,
                is_abstained=False,
            ))
        return PredictionSet(
            model_id="B3_event_prior",
            experiment_id=experiment_id,
            predictions=predictions,
        )
