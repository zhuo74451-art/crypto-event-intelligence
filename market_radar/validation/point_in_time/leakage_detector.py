"""
Leakage detector — detects various forms of information leakage in validation data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..contracts.event import ValidationEvent
from ..contracts.errors import (
    FutureInformationLeakError,
    RevisionLeakError,
    GroupSplitLeakError,
    SourceDependenceLeakError,
    TargetInFeaturesError,
    LabelNotMatureError,
)


class LeakageDetector:
    """Detects information leakage in validation datasets and experiments."""

    MIN_LABEL_MATURITY_SAMPLES = 10

    def check_feature_time_before_prediction(
        self,
        feature_time: datetime,
        prediction_time: datetime,
        feature_name: str = "",
    ) -> None:
        """Check that a feature's time is before or at the prediction time."""
        if feature_time > prediction_time:
            raise FutureInformationLeakError(
                detail=(
                    f"Feature '{feature_name}' has timestamp {feature_time} "
                    f"which is after prediction time {prediction_time}"
                ),
                object_id=feature_name,
                min_fix="Ensure all features are computed from data available before prediction",
            )

    def check_no_post_event_price(
        self,
        price_timestamp: datetime,
        event_time: datetime,
        event_id: str = "",
    ) -> None:
        """Check that price data does not come from after the event."""
        if price_timestamp > event_time:
            raise FutureInformationLeakError(
                detail=(
                    f"Post-event price used for event {event_id}: "
                    f"price at {price_timestamp}, event at {event_time}"
                ),
                object_id=event_id,
                min_fix="Use only pre-event price data for features",
            )

    def check_label_maturity(
        self,
        label_time: datetime,
        prediction_time: datetime,
        label_name: str = "",
    ) -> None:
        """Check that label was not observable at prediction time."""
        if label_time <= prediction_time:
            raise LabelNotMatureError(
                detail=(
                    f"Label '{label_name}' was observable at {label_time} "
                    f"which is before or at prediction time {prediction_time}"
                ),
                object_id=label_name,
                min_fix="Ensure labels are only observable after the prediction horizon",
            )

    def check_no_target_in_features(
        self,
        feature_names: list[str],
        target_name: str,
    ) -> None:
        """Check that the target field is not present in features."""
        if target_name in feature_names:
            raise TargetInFeaturesError(
                detail=f"Target field '{target_name}' found in feature set",
                object_id=target_name,
                min_fix=f"Remove '{target_name}' from feature set",
            )

    def check_group_split(
        self,
        event: ValidationEvent,
        train_clusters: set[str],
        test_clusters: set[str],
    ) -> None:
        """Check that an event cluster does not span train and test sets."""
        cluster_id = event.identity.event_cluster_id
        if cluster_id in train_clusters and cluster_id in test_clusters:
            raise GroupSplitLeakError(
                detail=(
                    f"Event cluster {cluster_id} appears in both "
                    f"train and test sets"
                ),
                object_id=cluster_id,
                min_fix="Ensure event clusters do not cross train/test boundaries",
            )

    def check_source_dependence(
        self,
        event: ValidationEvent,
        train_groups: set[str],
        test_groups: set[str],
    ) -> None:
        """Check that source dependence groups don't cross splits."""
        group = event.identity.source_dependence_group
        if group in train_groups and group in test_groups:
            raise SourceDependenceLeakError(
                detail=(
                    f"Source dependence group {group} appears in both "
                    f"train and test sets"
                ),
                object_id=group,
                min_fix="Ensure source dependence groups don't cross split boundaries",
            )

    def check_revision_value(
        self,
        revision_value: Optional[str],
        original_value: str,
        as_of_time: datetime,
    ) -> None:
        """Check that a revised value isn't used as if it were available at prediction time."""
        if revision_value is not None and revision_value != original_value:
            raise RevisionLeakError(
                detail=(
                    f"Revised value '{revision_value}' differs from "
                    f"original '{original_value}' — using revision would leak information"
                ),
                object_id="",
                min_fix="Use original release values for features, not later revisions",
            )

    def check_no_full_sample_normalization(
        self,
        statistics_time: datetime,
        prediction_time: datetime,
        stat_name: str = "",
    ) -> None:
        """Check that dataset-wide statistics aren't computed using future data."""
        if statistics_time > prediction_time:
            raise FutureInformationLeakError(
                detail=(
                    f"Statistic '{stat_name}' uses data up to {statistics_time} "
                    f"which exceeds prediction time {prediction_time}"
                ),
                object_id=stat_name,
                min_fix="Compute statistics using only data available before prediction time",
            )

    def check_benchmark_not_switched(
        self,
        original_benchmark: str,
        current_benchmark: str,
        experiment_id: str = "",
    ) -> None:
        """Check that the benchmark hasn't been switched after seeing results."""
        if original_benchmark != current_benchmark:
            raise FutureInformationLeakError(
                detail=(
                    f"Benchmark switched from '{original_benchmark}' "
                    f"to '{current_benchmark}' in experiment {experiment_id}"
                ),
                object_id=experiment_id,
                min_fix="Freeze benchmark selection before experiment starts",
            )
