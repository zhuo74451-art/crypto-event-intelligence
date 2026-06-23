"""Validation dataset builder — assembles Point-in-Time validation records.

Inputs: Lane A events, Lane B market labels, Lane C replay results,
        Lane C baselines, Lane C abstention records.
Output: ValidationDatasetV1 metadata + JSONL records file.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from .contracts import ValidationDatasetV1


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           datetime.now(timezone.utc).strftime("%f")[:3] + "Z"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:64]


def _make_record_id(event_id: str, strategy_id: str, horizon: str) -> str:
    raw = f"{event_id}|{strategy_id}|{horizon}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


class DatasetBuilder:
    """Assembles a Point-in-Time validation dataset from producer artifacts."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.records: list[dict] = []
        self.event_families: set[str] = set()
        self.date_start: Optional[str] = None
        self.date_end: Optional[str] = None
        self.abstention_count = 0
        self.quality_dist: dict[str, int] = {}
        self.missingness_dist: dict[str, int] = {}

    def add_replay_result(self, record: dict) -> None:
        """Add a single strategy replay result as a validation record."""
        event_id = record.get("event_id", "")
        strategy_id = record.get("strategy_id", "")
        horizon = record.get("time_horizon", "")
        rec_id = _make_record_id(event_id, strategy_id, horizon)

        event_time = record.get("event_time_utc", "")
        if event_time:
            if self.date_start is None or event_time < self.date_start:
                self.date_start = event_time
            if self.date_end is None or event_time > self.date_end:
                self.date_end = event_time

        family = record.get("event_family", "unknown")
        self.event_families.add(family)

        is_abstained = record.get("abstained", False)
        if is_abstained:
            self.abstention_count += 1

        pit_quality = record.get("point_in_time_quality", "unknown")
        self.quality_dist[pit_quality] = self.quality_dist.get(pit_quality, 0) + 1

        vr = {
            "record_id": rec_id,
            "event_id": event_id,
            "event_family": family,
            "event_time_utc": event_time,
            "reference_period": record.get("reference_period", ""),

            "strategy_id": strategy_id,
            "strategy_version": record.get("strategy_version", ""),
            "strategy_state": record.get("strategy_state", ""),
            "time_horizon": horizon,
            "expected_effect": record.get("expected_effect", ""),
            "market_confirmation": record.get("market_confirmation", ""),
            "regime": record.get("regime_context", ""),
            "transmission_state": record.get("transmission_state", ""),

            "point_in_time_quality": pit_quality,
            "consensus_quality": record.get("consensus_quality", ""),
            "market_data_quality": record.get("market_data_quality", ""),

            "abstained": is_abstained,
            "abstention_reasons": record.get("abstention_reasons", []),

            "observed_return": record.get("observed_return"),
            "observed_direction": record.get("observed_direction", ""),
            "label_available_at_utc": record.get("label_available_at_utc", ""),

            "information_cutoff_utc": record.get("information_cutoff_utc", ""),
            "evaluation_cutoff_utc": record.get("evaluation_cutoff_utc", ""),

            "producer_refs": {
                "event_id": event_id,
                "strategy_instance_id": record.get("strategy_instance_id", ""),
                "hypothesis_id": record.get("hypothesis_id", ""),
            },
            "quality_flags": record.get("quality_flags", []),
        }
        self.records.append(vr)

    def add_baseline_result(self, record: dict) -> None:
        """Add a baseline replay result as a validation record (non-strategy)."""
        vr = dict(record)
        vr["record_id"] = _make_record_id(
            record.get("event_id", ""),
            record.get("baseline_id", "baseline"),
            record.get("time_horizon", ""),
        )
        vr["strategy_id"] = record.get("baseline_id", "baseline")
        vr["strategy_version"] = "1.0.0"
        vr["is_baseline"] = True
        self.records.append(vr)

    def add_abstention_record(self, record: dict) -> None:
        """Add an abstention record to the dataset."""
        vr = dict(record)
        vr["record_id"] = _make_record_id(
            record.get("event_id", ""),
            record.get("strategy_id", "abstained"),
            record.get("time_horizon", ""),
        )
        vr["abstained"] = True
        vr["is_abstention_only"] = True
        self.abstention_count += 1
        self.records.append(vr)

    def build(self, dataset_id: str, producer_shas: dict[str, str],
              output_filename: str = "validation_dataset_v1.jsonl") -> ValidationDatasetV1:
        """Build and write the validation dataset."""
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        sha = _sha256_file(output_path)

        dataset = ValidationDatasetV1(
            dataset_id=dataset_id,
            dataset_version="1.0.0",
            generated_at_utc=_utc_now(),
            producer_shas=producer_shas,
            event_count=len(self.records),
            event_families=sorted(list(self.event_families)),
            date_start=self.date_start or "",
            date_end=self.date_end or "",
            feature_cutoff_policy="strict_information_cutoff",
            label_availability_policy="label_after_evaluation_cutoff",
            point_in_time_policy="first_release_only",
            revision_policy="no_future_revisions",
            records_path=output_path,
            records_sha256=sha,
            schema_path="schemas/intelligence/validation/validation_dataset_v1.schema.json",
            quality_distribution=self.quality_dist,
            missingness_distribution=self.missingness_dist,
            abstention_count=self.abstention_count,
            quarantined_count=0,
        )
        return dataset

    def load_records(self, path: str) -> list[dict]:
        """Load validation records from a JSONL file."""
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
