"""Bootstrap engine — dependency-aware resampling for confidence intervals.

Methods:
- event_cluster_bootstrap: resample event dependency groups (recommended)
- block_bootstrap: resample time blocks
- stratified_event_family_bootstrap: resample stratified by event family
"""

import random
from statistics import mean, median, stdev
from typing import Any, Optional

from .contracts import StatisticalEvidenceV1
from .dependency_graph import DependencyGraph


class BootstrapEngine:
    """Dependency-aware bootstrap resampling."""

    def __init__(self, records, dep_graph=None, random_seed=42):
        self.records = records
        self.dep_graph = dep_graph or DependencyGraph()
        self.random_seed = random_seed

    def event_cluster_bootstrap(self, metric_fn, resamples=1000,
                                confidence_level=0.95, strategy_id="", strategy_version=""):
        """Bootstrap by resampling event dependency groups."""
        random.seed(self.random_seed)
        groups = self.dep_graph.get_event_dependency_groups()
        if not groups:
            groups = [[i] for i in range(len(self.records))]
        group_ids = list(range(len(groups)))

        stats = []
        for _ in range(resamples):
            sampled = []
            for gid in random.choices(group_ids, k=len(group_ids)):
                sampled.extend(groups[gid])
            val = metric_fn([self.records[i] for i in sampled])
            stats.append(val)

        return self._compute_ci(stats, confidence_level, len(self.records),
                                resamples, "event_cluster_bootstrap",
                                strategy_id, strategy_version)

    def block_bootstrap(self, metric_fn, block_size=20, resamples=1000,
                        confidence_level=0.95, strategy_id="", strategy_version=""):
        """Bootstrap by resampling time-ordered blocks."""
        random.seed(self.random_seed)
        n = len(self.records)
        n_blocks = max(1, n // block_size)
        block_ids = list(range(n_blocks))

        stats = []
        for _ in range(resamples):
            sampled = []
            for bid in random.choices(block_ids, k=n_blocks):
                start = bid * block_size
                end = min(start + block_size, n)
                sampled.extend(range(start, end))
            val = metric_fn([self.records[i] for i in sampled])
            stats.append(val)

        return self._compute_ci(stats, confidence_level, len(self.records),
                                resamples, "block_bootstrap",
                                strategy_id, strategy_version)

    def stratified_event_family_bootstrap(self, metric_fn, resamples=1000,
                                          confidence_level=0.95, strategy_id="", strategy_version=""):
        """Bootstrap stratified by event family."""
        random.seed(self.random_seed)
        families = {}
        for i, rec in enumerate(self.records):
            fam = rec.get("event_family", "unknown")
            families.setdefault(fam, []).append(i)

        stats = []
        for _ in range(resamples):
            sampled = []
            for fam, indices in families.items():
                k = len(indices)
                sampled.extend(random.choices(indices, k=k))
            val = metric_fn([self.records[i] for i in sampled])
            stats.append(val)

        return self._compute_ci(stats, confidence_level, len(self.records),
                                resamples, "stratified_event_family_bootstrap",
                                strategy_id, strategy_version)

    def _compute_ci(self, stats, confidence_level, sample_count,
                    resamples, method, strategy_id, strategy_version):
        """Compute confidence interval from bootstrap statistics."""
        stats_sorted = sorted(stats)
        lower_idx = int((1 - confidence_level) / 2 * len(stats_sorted))
        upper_idx = int((1 + confidence_level) / 2 * len(stats_sorted))
        lower_idx = max(0, lower_idx)
        upper_idx = min(len(stats_sorted) - 1, upper_idx)

        ci = {
            "lower": stats_sorted[lower_idx],
            "upper": stats_sorted[upper_idx],
            "mean": mean(stats),
            "median": median(stats),
            "std": stdev(stats) if len(stats) > 1 else 0.0,
        }

        return StatisticalEvidenceV1(
            evidence_id=f"boot_{strategy_id[:8]}_{method[:8]}",
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            bootstrap_resamples=resamples,
            bootstrap_ci=ci,
            bootstrap_method=method,
            sufficient_sample=sample_count >= 30,
        )
