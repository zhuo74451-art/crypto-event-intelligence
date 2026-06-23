"""Chronological splitter — time-series-aware split with purge and embargo.
Implements fixed-time split, expanding & rolling walk-forward, purge/embargo.
All splits preserve time order. No random shuffling.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from .contracts import SplitManifestV1, WalkforwardFoldV1, SplitMethod


def _utc_parse(ts):
    ts_clean = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_clean)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_utc(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _hash_id(prefix, *parts):
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{prefix}_{h}"


def _event_time(rec):
    return _utc_parse(rec.get("event_time_utc", "2020-01-01T00:00:00Z"))


class ChronologicalSplitter:
    """Creates time-ordered splits with purge and embargo."""

    def __init__(self, purge_hours=24, embargo_days=7):
        self.purge_hours = purge_hours
        self.embargo_days = embargo_days

    def fixed_time_split(self, records, train_end="2018-12-31T23:59:59Z",
                         validation_end="2022-12-31T23:59:59Z", dataset_id=""):
        """Fixed chronological split: train / validation / holdout."""
        train_te = _utc_parse(train_end)
        val_te = _utc_parse(validation_end)
        train_idx, val_idx, holdout_idx = [], [], []
        for i, rec in enumerate(records):
            et = _event_time(rec)
            if et <= train_te:
                train_idx.append(i)
            elif et <= val_te:
                val_idx.append(i)
            else:
                holdout_idx.append(i)
        manifest = SplitManifestV1(
            split_manifest_id=_hash_id("sp", dataset_id, "fixed"),
            dataset_id=dataset_id,
            split_method=SplitMethod.FIXED_TIME.value,
            train_start=records[train_idx[0]].get("event_time_utc","") if train_idx else "",
            train_end=train_end,
            validation_start=records[val_idx[0]].get("event_time_utc","") if val_idx else "",
            validation_end=validation_end,
            holdout_start=records[holdout_idx[0]].get("event_time_utc","") if holdout_idx else "",
            holdout_end=records[holdout_idx[-1]].get("event_time_utc","") if holdout_idx else "",
            purge_window=f"{self.purge_hours}h",
            embargo_window=f"{self.embargo_days}d",
        )
        return train_idx, val_idx, holdout_idx, manifest

    def expanding_walkforward(self, records, initial_train_years=5,
                              test_years=1, dataset_id=""):
        """Expanding window walk-forward."""
        if not records:
            return [], {}
        sorted_records = sorted(enumerate(records), key=lambda x: _event_time(x[1]))
        all_times = [_event_time(r) for _, r in sorted_records]
        start_time = all_times[0]
        end_time = all_times[-1]
        train_start = start_time
        current_train_end = start_time + timedelta(days=initial_train_years * 365)
        test_duration = timedelta(days=test_years * 365)
        folds = []
        fold_data = {}
        fold_idx = 0
        while current_train_end + test_duration * 2 < end_time:
            val_start = current_train_end
            val_end = current_train_end + test_duration
            test_start_t = val_end
            test_end_t = val_end + test_duration
            purge_start = test_start_t - timedelta(hours=self.purge_hours)
            purge_end = test_end_t + timedelta(hours=self.purge_hours)
            embargo_start_v = test_start_t
            embargo_end_v = test_end_t + timedelta(days=self.embargo_days)
            train_i = [idx for idx, et in zip([r[0] for r in sorted_records], all_times)
                       if train_start <= et <= current_train_end
                       and not (purge_start <= et <= purge_end or embargo_start_v <= et <= embargo_end_v)]
            val_i = [idx for idx, et in zip([r[0] for r in sorted_records], all_times)
                     if val_start < et <= val_end]
            test_i = [idx for idx, et in zip([r[0] for r in sorted_records], all_times)
                      if test_start_t < et <= test_end_t]
            if len(test_i) < 3:
                current_train_end += test_duration
                fold_idx += 1
                continue
            fold_id = _hash_id("wf", dataset_id, str(fold_idx))
            fold = WalkforwardFoldV1(
                fold_id=fold_id, fold_index=fold_idx,
                train_start=_format_utc(train_start),
                train_end=_format_utc(current_train_end),
                validation_start=_format_utc(val_start),
                validation_end=_format_utc(val_end),
                test_start=_format_utc(test_start_t),
                test_end=_format_utc(test_end_t),
                purge_start=_format_utc(purge_start),
                purge_end=_format_utc(purge_end),
                embargo_start=_format_utc(embargo_start_v),
                embargo_end=_format_utc(embargo_end_v),
                train_count=len(train_i), validation_count=len(val_i), test_count=len(test_i),
            )
            folds.append(fold)
            fold_data[fold_id] = {"train": train_i, "val": val_i, "test": test_i}
            current_train_end += test_duration
            fold_idx += 1
        return folds, fold_data

    def rolling_walkforward(self, records, train_window_years=5,
                            test_years=1, dataset_id=""):
        """Rolling (fixed-size) window walk-forward."""
        if not records:
            return [], {}
        sorted_records = sorted(enumerate(records), key=lambda x: _event_time(x[1]))
        all_times = [_event_time(r) for _, r in sorted_records]
        end_time = all_times[-1]
        test_duration = timedelta(days=test_years * 365)
        train_window = timedelta(days=train_window_years * 365)
        folds = []
        fold_data = {}
        fold_idx = 0
        current_test_end = end_time
        while True:
            current_test_start = current_test_end - test_duration
            current_train_end = current_test_start
            current_train_start = current_train_end - train_window
            if current_train_start < all_times[0]:
                break
            purge_start = current_test_start - timedelta(hours=self.purge_hours)
            purge_end = current_test_end + timedelta(hours=self.purge_hours)
            embargo_start_v = current_test_start
            embargo_end_v = current_test_end + timedelta(days=self.embargo_days)
            train_i = [idx for idx, et in zip([r[0] for r in sorted_records], all_times)
                       if current_train_start <= et <= current_train_end
                       and not (purge_start <= et <= purge_end or embargo_start_v <= et <= embargo_end_v)]
            test_i = [idx for idx, et in zip([r[0] for r in sorted_records], all_times)
                      if current_test_start < et <= current_test_end]
            if len(test_i) < 3:
                current_test_end -= test_duration
                fold_idx += 1
                continue
            val_start = current_train_end - test_duration
            val_end = current_train_end
            fold_id = _hash_id("wf-roll", dataset_id, str(fold_idx))
            fold = WalkforwardFoldV1(
                fold_id=fold_id, fold_index=fold_idx,
                train_start=_format_utc(current_train_start),
                train_end=_format_utc(current_train_end),
                validation_start=_format_utc(val_start),
                validation_end=_format_utc(val_end),
                test_start=_format_utc(current_test_start),
                test_end=_format_utc(current_test_end),
                purge_start=_format_utc(purge_start),
                purge_end=_format_utc(purge_end),
                embargo_start=_format_utc(embargo_start_v),
                embargo_end=_format_utc(embargo_end_v),
                train_count=len(train_i), validation_count=0, test_count=len(test_i),
            )
            folds.append(fold)
            fold_data[fold_id] = {"train": train_i, "test": test_i}
            current_test_end -= test_duration
            fold_idx += 1
        folds.reverse()
        return folds, fold_data

    def purge_embargo_filter(self, records, split_indices, other_indices):
        """Filter out records whose windows overlap with other split."""
        blocked = set()
        for si in split_indices:
            s_time = _event_time(records[si])
            for oi in other_indices:
                o_time = _event_time(records[oi])
                diff = abs((s_time - o_time).total_seconds()) / 3600
                if diff < self.purge_hours:
                    blocked.add(si)
                    break
        kept = [i for i in split_indices if i not in blocked]
        removed = [i for i in split_indices if i in blocked]
        return kept, removed
